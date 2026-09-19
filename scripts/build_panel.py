"""Construye el panel mensual company_id x month a partir de los CSV crudos.

Salidas (data/processed/):
  panel_monthly.csv   una fila por empresa y mes (caja, saldo diario, deuda dinámica, facturas, calidad)
  company_static.csv  una fila por empresa (grupo, cobertura, deuda estática)

Decisiones (ver notebooks/01_eda.ipynb):
  - Solo cuentas de banking_products. Importes convertidos a la moneda de la empresa (importe / exchange_rate)
    y después winsorizados a p0,1 / p99,9.
  - Flujo operativo = todo salvo transfer, investment_* y debt_repayment (líneas aparte).
  - Facturas: positivo = venta, negativo = compra. Vencido calculado históricamente (due_date y payment_date),
    nunca con el status final. Sin facturas => columnas NaN (no 0).
  - Saldo diario reconstruido hacia atrás desde balances.csv (cuentas de banco, |saldo| < 1e8, convertido a moneda empresa).
  - Sep-2026 excluido (mes parcial).
"""
from pathlib import Path
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
OUT = D / "processed"
OUT.mkdir(exist_ok=True)

FIRST, LAST = pd.Period("2024-09", "M"), pd.Period("2026-08", "M")
MONTHS = pd.period_range(FIRST, LAST, freq="M")
NON_OP = {"transfer", "investment_deployment", "investment_return", "debt_repayment"}
END = pd.Timestamp("2026-08-31")


def winsor(s, lo=0.001, hi=0.999):
    return s.clip(*s.quantile([lo, hi]))


def to_company_ccy(amount, rate):
    """importe en moneda de origen -> moneda de la empresa (rate = unidades de origen por unidad de destino)."""
    return np.where(rate > 0, amount / rate.where(rate > 0, 1), amount)


companies = pd.read_csv(D / "companies.csv")
ccur = companies.set_index("company_id").currency
bank = pd.read_csv(D / "banking_products.csv")
pcur = bank.set_index("product_id").currency

# ---------- transacciones ----------
tx = pd.read_csv(D / "transactions.csv",
                 usecols=["company_id", "product_id", "date", "amount", "exchange_rate", "category"],
                 parse_dates=["date"])
tx = tx[tx.product_id.isin(bank.product_id)].copy()
tx["pcur"] = tx.product_id.map(pcur)
tx["ccur"] = tx.company_id.map(ccur)
# tasa mediana por par de monedas (para convertir saldos)
pair_rate = (tx[(tx.pcur != tx.ccur) & (tx.exchange_rate > 0)]
             .groupby(["pcur", "ccur"]).exchange_rate.median())
tx["amount"] = winsor(pd.Series(to_company_ccy(tx.amount, tx.exchange_rate), index=tx.index))
tx["m"] = tx.date.dt.to_period("M")
tx["day"] = tx.date.dt.normalize()
tx["op"] = ~tx.category.isin(NON_OP)

# ---------- saldo diario (ancla = balances.csv) ----------
bal = pd.read_csv(D / "balances.csv")
bal = bal[bal.product_id.isin(bank.product_id) & (bal.balance.abs() < 1e8)].copy()
bal["pcur"] = bal.product_id.map(pcur)
bal["ccur"] = bal.company_id.map(ccur)
same = bal.pcur == bal.ccur
rate = pd.Series([pair_rate.get((a, b), np.nan) for a, b in zip(bal.pcur, bal.ccur)], index=bal.index)
bal["balance_c"] = np.where(same, bal.balance, bal.balance / rate)
anchor = bal.groupby("company_id").balance_c.sum(min_count=1).dropna()

daily_net = tx.groupby(["company_id", "day"]).amount.sum()
tot_all = tx.groupby("company_id").amount.sum()
day_rows = []
for cid, s in daily_net.groupby(level=0):
    if cid not in anchor.index:
        continue
    s = s.droplevel(0)
    idx = pd.date_range(s.index.min(), max(END, s.index.max()), freq="D")
    cum = s.reindex(idx, fill_value=0.0).cumsum()
    lvl = anchor[cid] - (tot_all[cid] - cum)            # saldo a fin de cada día
    lvl = lvl[lvl.index <= END]
    df = pd.DataFrame({"company_id": cid, "m": lvl.index.to_period("M"), "lvl": lvl.values})
    day_rows.append(df)
days = pd.concat(day_rows, ignore_index=True)
g = days.groupby(["company_id", "m"])
bal_m = pd.DataFrame({"cash_end": g.lvl.last(), "cash_min": g.lvl.min(),
                      "days_negative": g.lvl.apply(lambda s: int((s < 0).sum()))}).reset_index()

# ---------- agregación mensual de transacciones ----------
t = tx[tx.m <= LAST]
amt, is_op = t.amount, t.op
parts = {
    "inflow_op": amt.where((amt > 0) & is_op),
    "outflow_op": -amt.where((amt < 0) & is_op),
    "debt_service": -amt.where(t.category == "debt_repayment"),
    "transfer_net": amt.where(t.category == "transfer"),
    "out_salary": -amt.where(t.category == "salary"),
    "out_social_security": -amt.where(t.category == "social_security"),
    "out_tax": -amt.where(t.category == "tax"),
    "out_fin_cost": -amt.where(t.category.isin(["interest_charge", "fee"])),
}
work = t[["company_id", "m"]].assign(net_bank=amt, **parts)
panel = work.groupby(["company_id", "m"]).agg(
    net_bank=("net_bank", "sum"), **{k: (k, "sum") for k in parts}, n_tx=("net_bank", "size")).reset_index()

first_m = panel.groupby("company_id").m.min()
grid = pd.MultiIndex.from_tuples(
    [(c, m) for c, f in first_m.items() for m in MONTHS[MONTHS >= f]], names=["company_id", "m"])
panel = panel.set_index(["company_id", "m"]).reindex(grid).fillna(0).reset_index()
panel["net_op"] = panel.inflow_op - panel.outflow_op
panel = panel.merge(bal_m, on=["company_id", "m"], how="left")
neg = panel.groupby("company_id").cash_end.min() < 0
panel["saldo_inconsistente"] = panel.company_id.map(neg).fillna(False)

# ---------- ventanas de 3 meses ----------
panel = panel.sort_values(["company_id", "m"])
g = panel.groupby("company_id")
for c in ["net_op", "inflow_op", "outflow_op", "debt_service"]:
    panel[c + "_3m"] = g[c].transform(lambda s: s.rolling(3, min_periods=3).sum())
panel["margin_3m"] = panel.net_op_3m / (panel.inflow_op_3m + panel.outflow_op_3m).replace(0, np.nan)
panel["runway_m"] = panel.cash_end / (panel.outflow_op_3m / 3).replace(0, np.nan)
panel["debt_service_ratio_3m"] = panel.debt_service_3m / panel.inflow_op_3m.replace(0, np.nan)
panel["hist_months"] = g.cumcount() + 1
panel["historia_corta"] = panel.hist_months < 6

# ---------- facturas ----------
inv = pd.read_csv(D / "invoices.csv",
                  usecols=["company_id", "document_type", "issuance_date", "due_date", "payment_date",
                           "amount", "exchange_rate", "status"],
                  parse_dates=["issuance_date", "due_date", "payment_date"])
inv = inv[(inv.status != "cancel") & inv.document_type.isin(["invoice", "invoiceGroup"])].copy()
inv["amount"] = winsor(pd.Series(to_company_ccy(inv.amount, inv.exchange_rate), index=inv.index), 0.001, 0.999)
inv["paid"] = inv.status.eq("paid")
has_inv = set(inv.company_id)

# ventas: vencido histórico
sales = inv[inv.amount > 0].copy()
sales["pay_m"] = sales.payment_date.dt.to_period("M").where(sales.paid)
sales["due_m"] = sales.due_date.dt.to_period("M")
sales["iss_m"] = sales.issuance_date.dt.to_period("M")


def by_month(df, col):
    df = df.assign(**{col: df[col].where(df[col] >= FIRST, FIRST)})   # lo anterior a FIRST se acumula en FIRST
    s = df.groupby(["company_id", col]).amount.sum().unstack(fill_value=0)
    return s.reindex(columns=MONTHS, fill_value=0).cumsum(axis=1)


due_c = by_month(sales, "due_m")
late = sales[sales.paid].assign(pm=lambda d: d.pay_m.where(d.pay_m >= d.due_m, d.due_m))
paid_c = by_month(late, "pm").reindex(due_c.index, fill_value=0)
overdue = (due_c - paid_c).clip(lower=0)
issued_3m = (sales.groupby(["company_id", "iss_m"]).amount.sum().unstack(fill_value=0)
             .reindex(columns=MONTHS, fill_value=0).T.rolling(3, min_periods=1).sum().T)
inv_panel = pd.DataFrame({"overdue_amt": overdue.stack(),
                          "sales_3m": issued_3m.reindex(overdue.index, fill_value=0).stack()}).reset_index()
inv_panel.columns = ["company_id", "m", "overdue_amt", "sales_3m"]
inv_panel["pct_vencido"] = (inv_panel.overdue_amt / inv_panel.sales_3m.replace(0, np.nan)).clip(0, 5)
dso = sales[sales.paid].assign(d=lambda d: (d.payment_date - d.issuance_date).dt.days.clip(0, 365))
dso = dso.groupby(["company_id", "pay_m"]).d.mean().rename("dso").reset_index().rename(columns={"pay_m": "m"})
inv_panel = inv_panel.merge(dso, on=["company_id", "m"], how="left")
inv_panel["dso"] = inv_panel.groupby("company_id").dso.transform(lambda s: s.rolling(3, min_periods=1).mean())

# compras: facturas recibidas vencidas sin pagar a fin de mes (histórico)
pay = inv[inv.amount < 0].assign(amount=lambda d: -d.amount)
rows = []
for m in MONTHS:
    eom = m.to_timestamp(how="end").normalize()
    unpaid = ~pay.paid | (pay.payment_date > eom)
    old = pay[unpaid & (pay.due_date <= eom - pd.Timedelta(days=90))]
    recent = old[old.due_date > eom - pd.Timedelta(days=180)]
    r = pd.DataFrame({"payables_overdue90": old.groupby("company_id").amount.sum(),
                      "payables_overdue90_recent": recent.groupby("company_id").amount.sum()})
    r["m"] = m
    rows.append(r.reset_index())
pay_panel = pd.concat(rows, ignore_index=True)

panel = panel.merge(inv_panel[["company_id", "m", "overdue_amt", "sales_3m", "pct_vencido", "dso"]],
                    on=["company_id", "m"], how="left")
panel = panel.merge(pay_panel, on=["company_id", "m"], how="left")
panel["tiene_facturas"] = panel.company_id.isin(has_inv)
panel[["payables_overdue90", "payables_overdue90_recent"]] = panel[["payables_overdue90", "payables_overdue90_recent"]].fillna(0)
sin = ~panel.tiene_facturas
panel.loc[sin, ["overdue_amt", "sales_3m", "pct_vencido", "dso", "payables_overdue90", "payables_overdue90_recent"]] = np.nan

# ---------- estática por empresa ----------
debt = pd.read_csv(D / "debt_products.csv")
d = debt.assign(granted=debt.granted.abs(), outstanding=debt.outstanding.abs())
d = d[d.granted > 0]
d = d.assign(util=(d.outstanding / d.granted).clip(0, 1))
ds = d.groupby("company_id").agg(n_debt_products=("util", "size"), debt_granted=("granted", "sum"),
                                 debt_outstanding=("outstanding", "sum"))
ds["debt_util"] = (ds.debt_outstanding / ds.debt_granted).clip(0, 1)
static = companies.set_index("company_id")[["group_id", "country", "currency", "erp"]].join(ds)
static["tiene_deuda_producto"] = static.n_debt_products.notna()
static["tiene_facturas"] = static.index.isin(has_inv)
static["tiene_erp"] = static.erp.notna()
static["paga_deuda_banco"] = static.index.isin(set(tx[tx.category == "debt_repayment"].company_id))
static["tiene_saldo"] = static.index.isin(anchor.index)
static["meses_historia"] = panel.groupby("company_id").size()
static["saldo_inconsistente"] = static.index.map(neg).fillna(False)
static["cuentas_moneda_distinta"] = static.index.isin(set(tx[tx.pcur != tx.ccur].company_id))

panel["m"] = panel.m.astype(str)
panel = panel.rename(columns={"m": "month"})
panel.to_csv(OUT / "panel_monthly.csv", index=False)
static.reset_index().to_csv(OUT / "company_static.csv", index=False)
print(panel.shape, panel.company_id.nunique(), "empresas |", static.shape)
