"""Construye el panel mensual empresa x mes a partir de transacciones, facturas y saldos.

Importes convertidos a la moneda de la empresa (D03). Las features del score son
ratios adimensionales (features.py), así que la moneda de la empresa no importa.
Las decisiones Dxx están documentadas en research/DECISIONS.md.
"""
from pathlib import Path
import polars as pl
import fx as FX

DATA = Path(__file__).resolve().parents[1] / "data"
PANEL_START = pl.datetime(2024, 9, 1)
LAST_FULL_MONTH = pl.datetime(2026, 8, 1)
SNAPSHOT = pl.datetime(2026, 9, 1)

OPER_IN = ["collection", "bulk_collection", "pos_settlement", "cash_settlement", "cash_settlements"]
PAYROLL = ["salary", "social_security"]
DEBT = ["debt_repayment", "interest_charge"]
NON_OPER = ["investment_deployment", "investment_return"]  # movimientos de tesorería, no de negocio
CASH_TYPES = ["checking", "saving", "investment", "tpv", "expensesPlatform"]
CREDIT_TYPES = ["lineofcredit"]
# Calidad de dato (fase 0 del autoresearch, salida/datos_limpieza.md). Umbrales SIEMPRE en EUR:
# en moneda cruda, 478 de las 491 transacciones > 1e8 son AOA/COP/VND/CLP y no centinelas.
SENTINEL_EUR = 1e8          # importe de generador, no de pyme (13 tx en 7 empresas; 4 saldos de caja)
IMPLAUSIBLE_FLOOR_EUR = 1e5  # suelo del check |caja| > 50·flujo 12m (evita marcar pymes pequeñas con ahorro)


def _products() -> pl.DataFrame:
    bp = pl.read_parquet(DATA / "banking_products.parquet").select("product_id", "company_id", "type", "currency")
    dp = pl.read_parquet(DATA / "debt_products.parquet").select("product_id", "company_id", "type", "currency")
    return pl.concat([bp, dp]).rename({"currency": "pcur"})


def load_transactions() -> pl.DataFrame:
    """Transacciones booked, en moneda de la empresa (D03), marcando las internas (D04)."""
    t = pl.read_parquet(DATA / "transactions.parquet")
    comp = pl.read_parquet(DATA / "companies.parquet").select("company_id", pl.col("currency").alias("ccur"))
    t = t.filter(pl.col("status").is_null() | (pl.col("status") == "booked"))
    t = t.join(_products().select("product_id", "type", "pcur"), on="product_id", how="left").join(comp, on="company_id")
    foreign = pl.col("pcur").is_not_null() & (pl.col("pcur") != pl.col("ccur"))
    t = t.with_columns(month=pl.col("date").dt.truncate("1mo"))
    # tipo real mensual (BCE / currency-api) = unidades de pcur por unidad de ccur
    fxm = _fx_table()
    t = (t.join(fxm.rename({"currency": "pcur", "per_eur": "p_pe"}), on=["month", "pcur"], how="left")
          .join(fxm.rename({"currency": "ccur", "per_eur": "c_pe"}), on=["month", "ccur"], how="left")
          .with_columns(real_fx=pl.col("p_pe") / pl.col("c_pe")))
    # el tipo del dataset se acepta si está a ±10 % del real (98,7 % de los casos); si no (fx=1 o 0), el real (D03)
    ok = (pl.col("exchange_rate") > 0) & ((pl.col("exchange_rate") / pl.col("real_fx") - 1).abs() < 0.10)
    t = t.with_columns(
        fx=pl.when(~foreign).then(1.0).when(ok).then(pl.col("exchange_rate"))
             .otherwise(pl.col("real_fx").fill_null(pl.when(pl.col("exchange_rate") > 0).then(pl.col("exchange_rate")).otherwise(1.0))),
        fx_fixed=foreign & ~ok.fill_null(False),
        is_foreign=foreign)
    t = t.with_columns(amount=pl.col("amount") / pl.col("fx"))
    t = t.with_columns(amount_eur=pl.col("amount") / pl.col("c_pe").fill_null(1.0)).drop("p_pe", "c_pe")
    # transferencias internas: mismo día e importe opuesto entre dos productos de la misma empresa
    k = t.select("transaction_id", "company_id", "product_id", "amount",
                 day=pl.col("date").dt.date(), a=pl.col("amount").abs().round(2))
    pairs = (k.filter(pl.col("amount") > 0)
              .join(k.filter(pl.col("amount") < 0), on=["company_id", "day", "a"], suffix="_n")
              .filter(pl.col("product_id") != pl.col("product_id_n")))
    internal = pl.concat([pairs.select("transaction_id"), pairs.select(pl.col("transaction_id_n").alias("transaction_id"))]).unique()
    # intragrupo: mismo grupo y día, importe opuesto (>100) entre dos empresas distintas del grupo (D04)
    grp = pl.read_parquet(DATA / "companies.parquet").select("company_id", "group_id")
    kg = k.join(grp, on="company_id").filter(pl.col("a") > 100)
    ig = (kg.filter(pl.col("amount") > 0)
            .join(kg.filter(pl.col("amount") < 0), on=["group_id", "day", "a"], suffix="_n")
            .filter(pl.col("company_id") != pl.col("company_id_n")))
    intra = pl.concat([ig.select("transaction_id"), ig.select(pl.col("transaction_id_n").alias("transaction_id"))]).unique()
    return t.with_columns(internal=pl.col("transaction_id").is_in(internal["transaction_id"].implode()),
                          intragroup=pl.col("transaction_id").is_in(intra["transaction_id"].implode()))


def _fx_table() -> pl.DataFrame:
    return pl.from_pandas(FX.load()[["month", "currency", "per_eur"]]).with_columns(pl.col("month").cast(pl.Datetime("us")))


def _tx_monthly(t: pl.DataFrame) -> pl.DataFrame:
    ext = t.filter(~pl.col("internal") & ~pl.col("intragroup") & ~pl.col("category").is_in(NON_OPER).fill_null(False))
    cat, amt = pl.col("category"), pl.col("amount")
    m = ext.group_by("company_id", "month").agg(
        n_tx=pl.len(),
        inflow=amt.filter(amt > 0).sum(),
        outflow=-amt.filter(amt < 0).sum(),
        oper_in=amt.filter(cat.is_in(OPER_IN) & (amt > 0)).sum(),
        transfer_in=amt.filter((cat == "transfer") & (amt > 0)).sum(),
        uncat_in=amt.filter((cat == "-") & (amt > 0)).sum(),
        payroll=-amt.filter(cat.is_in(PAYROLL)).sum(),
        salary=-amt.filter(cat == "salary").sum(),
        social_security=-amt.filter(cat == "social_security").sum(),
        tax=-amt.filter(cat == "tax").sum(),
        debt_service=-amt.filter(cat.is_in(DEBT)).sum(),
        fees=-amt.filter(cat == "fee").sum(),
        refunds=-amt.filter(cat == "collection_refund").sum(),
        foreign_flow=amt.filter(pl.col("is_foreign")).abs().sum(),
        gross_flow=amt.abs().sum(),
        n_fx_fixed=pl.col("fx_fixed").sum(),
    )
    internal = t.filter(pl.col("internal") | pl.col("intragroup")).group_by("company_id", "month").agg(
        internal_flow=pl.col("amount").abs().sum(), intragroup_flow=pl.col("amount").filter(pl.col("intragroup")).abs().sum())
    # centinelas medidos en EUR (A01): solo informativo, no altera flujos ni caja
    sent = t.group_by("company_id", "month").agg(n_sentinel_tx=(pl.col("amount_eur").abs() > SENTINEL_EUR).sum())
    return m.join(internal, on=["company_id", "month"], how="left").join(sent, on=["company_id", "month"], how="left")


def _balances_backward(t: pl.DataFrame, types: list[str], months: pl.DataFrame, name: str) -> pl.DataFrame:
    """Saldo a fin de mes = saldo foto final − flujos posteriores (en moneda de la empresa)."""
    bal = pl.read_parquet(DATA / "balances.parquet")
    prods = _products().filter(pl.col("type").is_in(types)).select("product_id")
    # fx del producto: mediana del aplicado en sus transacciones (ya validado contra el real)
    pfx = t.group_by("product_id").agg(pl.col("fx").median())
    b = (bal.join(prods, on="product_id").join(pfx, on="product_id", how="left")
            .select("product_id", "company_id", (pl.col("balance").fill_null(0) / pl.col("fx").fill_null(1.0)).alias("balance")))
    tx = t.join(prods, on="product_id").group_by("product_id", "month").agg(net=pl.col("amount").sum())
    grid = b.select("product_id", "company_id").join(months, how="cross")
    g = (grid.join(tx, on=["product_id", "month"], how="left").fill_null(0)
             .sort("product_id", "month", descending=[False, True]))
    g = g.with_columns(future=pl.col("net").cum_sum().over("product_id") - pl.col("net"))
    g = g.join(b.select("product_id", "balance"), on="product_id").with_columns(v=pl.col("balance") - pl.col("future"))
    # a céntimos: sin redondear, las cuentas que vuelven a cero quedan en ±1e-13 y cambian el signo de la caja (253 filas)
    return g.group_by("company_id", "month").agg(pl.col("v").sum().round(2).alias(name))


def _sentinel_cash_companies(t: pl.DataFrame) -> pl.Series:
    """Empresas con una transacción o un saldo de caja > SENTINEL_EUR (A01/A02): la caja reconstruida no es fiable."""
    bal = pl.read_parquet(DATA / "balances.parquet")
    prods = _products().filter(pl.col("type").is_in(CASH_TYPES)).select("product_id", "pcur")
    fxm = _fx_table()
    last = fxm.filter(pl.col("month") == fxm["month"].max()).select(pl.col("currency").alias("pcur"), "per_eur")
    b = (bal.join(prods, on="product_id").join(last, on="pcur", how="left")
            .filter((pl.col("balance") / pl.col("per_eur").fill_null(1.0)).abs() > SENTINEL_EUR))
    return pl.concat([b["company_id"], t.filter(pl.col("amount_eur").abs() > SENTINEL_EUR)["company_id"]]).unique()


def _credit_lines(t: pl.DataFrame, months: pl.DataFrame) -> pl.DataFrame:
    """Utilización de líneas de crédito: dispuesto / concedido (D11)."""
    dp = pl.read_parquet(DATA / "debt_products.parquet")
    bal = pl.read_parquet(DATA / "balances.parquet")
    lim = (dp.filter(pl.col("type").is_in(CREDIT_TYPES)).join(bal.select("product_id", "granted"), on="product_id", how="left", suffix="_b")
             .with_columns(limit=pl.coalesce(pl.col("granted_b"), pl.col("granted")).abs())
             .group_by("company_id").agg(pl.col("limit").sum()))
    drawn = _balances_backward(t, CREDIT_TYPES, months, "lc_balance")
    return drawn.join(lim, on="company_id", how="left").with_columns(
        lc_drawn=(-pl.col("lc_balance")).clip(0, None)).select("company_id", "month", "lc_drawn", pl.col("limit").alias("lc_limit"))


def _invoices_monthly(months: pl.DataFrame) -> pl.DataFrame:
    """Disciplina de facturas reconstruida a fecha de cierre de cada mes (D05)."""
    inv = pl.read_parquet(DATA / "invoices.parquet")
    inv = inv.filter(pl.col("status") != "cancel", pl.col("document_type").is_in(["invoice", "invoiceGroup"]))
    lo = pl.datetime(2015, 1, 1)
    inv = inv.filter(pl.col("due_date").is_between(lo, pl.datetime(2027, 12, 31)), pl.col("issuance_date").is_between(lo, SNAPSHOT))
    # impagada en la foto final => impagada en todos los cierres anteriores (payment_date del fichero = due_date)
    unpaid = (pl.col("pending_amount").abs() > 0) & (pl.col("status") != "paid")
    # FX de facturas con la misma regla que las transacciones: tipo del fichero si está a ±10 % del real (D03)
    comp = pl.read_parquet(DATA / "companies.parquet").select("company_id", pl.col("currency").alias("ccur"))
    fxm = _fx_table()
    inv = (inv.join(comp, on="company_id", how="left").with_columns(im=pl.col("issuance_date").dt.truncate("1mo"))
              .join(fxm.rename({"currency": "currency", "per_eur": "p_pe", "month": "im"}), on=["im", "currency"], how="left")
              .join(fxm.rename({"currency": "ccur", "per_eur": "c_pe", "month": "im"}), on=["im", "ccur"], how="left")
              .with_columns(real_fx=pl.col("p_pe") / pl.col("c_pe")))
    same = pl.col("currency") == pl.col("ccur")
    ok = (pl.col("exchange_rate") > 0) & ((pl.col("exchange_rate") / pl.col("real_fx") - 1).abs() < 0.10)
    fxv = (pl.when(same).then(1.0).when(ok).then(pl.col("exchange_rate"))
             .otherwise(pl.col("real_fx").fill_null(pl.when(pl.col("exchange_rate") > 0).then(pl.col("exchange_rate")).otherwise(1.0))))
    inv = inv.with_columns(
        payment_date=pl.when(unpaid | (pl.col("payment_date") > SNAPSHOT)).then(None).otherwise(pl.col("payment_date")),
        side=pl.when(pl.col("amount") > 0).then(pl.lit("ar")).otherwise(pl.lit("ap")),
        abs_amt=pl.col("amount").abs() / fxv,
    )
    rows = []
    for m in months["month"].to_list():
        m_end = pl.Series([m]).dt.offset_by("1mo")[0]
        late_cut = pl.Series([m_end]).dt.offset_by("-15d")[0]
        paid_by = pl.col("payment_date").is_not_null() & (pl.col("payment_date") < m_end)
        # facturas vencidas hace >15 días a cierre de mes: ¿seguían abiertas? (solo las ya emitidas: sin fuga as-of, A07)
        due = inv.filter(pl.col("due_date") < late_cut, pl.col("due_date") >= pl.Series([m]).dt.offset_by("-3mo")[0],
                         pl.col("issuance_date") < m_end)
        a = due.group_by("company_id", "side").agg(late_share=(~paid_by | ((pl.col("payment_date") - pl.col("due_date")).dt.total_days() > 15)).mean())
        # vencido y abierto, solo de facturas con vencimiento en los últimos 12 meses (sin stock eterno)
        o = inv.filter(pl.col("due_date") < m_end, pl.col("issuance_date") < m_end, ~paid_by,
                       pl.col("due_date") >= pl.Series([m_end]).dt.offset_by("-12mo")[0])
        b = o.group_by("company_id", "side").agg(overdue=pl.col("abs_amt").sum(),
                                                  overdue_90=pl.col("abs_amt").filter(pl.col("due_date") < pl.Series([m]).dt.offset_by("-2mo")[0]).sum())
        # concentración de clientes (HHI de facturas AR emitidas en 6 meses)
        ar6 = inv.filter(pl.col("side") == "ar", pl.col("issuance_date") < m_end,
                         pl.col("issuance_date") >= pl.Series([m_end]).dt.offset_by("-6mo")[0], pl.col("counterparty_id").is_not_null())
        h = (ar6.group_by("company_id", "counterparty_id").agg(pl.col("abs_amt").sum())
                .with_columns(sh=pl.col("abs_amt") / pl.col("abs_amt").sum().over("company_id"))
                .group_by("company_id").agg(hhi_ar_6m=(pl.col("sh") ** 2).sum()))
        # dinámica de clientes (D24): amplitud reciente vs anual y facturación de clientes perdidos
        ar12_all = inv.filter(pl.col("side") == "ar", pl.col("issuance_date") < m_end,
                              pl.col("issuance_date") >= pl.Series([m_end]).dt.offset_by("-12mo")[0])
        # cobertura de contraparte del AR (A23): sin ella, HHI y clientes perdidos se calculan sobre una fracción de la cartera
        cov = ar12_all.group_by("company_id").agg(
            ar_id_coverage=pl.col("abs_amt").filter(pl.col("counterparty_id").is_not_null()).sum() / pl.col("abs_amt").sum())
        ar12 = ar12_all.filter(pl.col("counterparty_id").is_not_null())
        rec = pl.col("issuance_date") >= pl.Series([m_end]).dt.offset_by("-3mo")[0]
        cu = ar12.group_by("company_id").agg(
            n_cust_3m=pl.col("counterparty_id").filter(rec).n_unique(), n_cust_12m=pl.col("counterparty_id").n_unique())
        prev = ar12.filter(~rec).group_by("company_id", "counterparty_id").agg(amt=pl.col("abs_amt").sum())
        recent = ar12.filter(rec).select("company_id", "counterparty_id").unique().with_columns(still=pl.lit(True))
        lost = (prev.join(recent, on=["company_id", "counterparty_id"], how="left")
                    .group_by("company_id").agg(n_prev=pl.len(), lost_share=pl.col("amt").filter(pl.col("still").is_null()).sum() / pl.col("amt").sum())
                    .with_columns(lost_share=pl.when(pl.col("n_prev") >= 3).then(pl.col("lost_share"))).drop("n_prev"))
        h = (h.join(cu, on="company_id", how="full", coalesce=True).join(lost, on="company_id", how="full", coalesce=True)
              .join(cov, on="company_id", how="full", coalesce=True))
        ab = a.join(b, on=["company_id", "side"], how="full", coalesce=True)
        ab = ab.pivot(on="side", index="company_id", values=["late_share", "overdue", "overdue_90"])
        rows.append(ab.join(h, on="company_id", how="full", coalesce=True).with_columns(month=pl.lit(m)))
    out = pl.concat(rows, how="diagonal_relaxed")
    iss = inv.with_columns(month=pl.col("issuance_date").dt.truncate("1mo")).group_by("company_id", "month").agg(
        ar_issued=pl.col("abs_amt").filter(pl.col("side") == "ar").sum(),
        ap_issued=pl.col("abs_amt").filter(pl.col("side") == "ap").sum())
    first_inv = inv.group_by("company_id").agg(first_inv=pl.col("issuance_date").min().dt.truncate("1mo"))
    return (out.join(iss, on=["company_id", "month"], how="left").with_columns(pl.col("month").cast(pl.Datetime("us")))
               .join(first_inv, on="company_id", how="left"))


def build_panel() -> pl.DataFrame:
    comp = pl.read_parquet(DATA / "companies.parquet")
    months = pl.DataFrame({"month": pl.datetime_range(PANEL_START, LAST_FULL_MONTH, "1mo", eager=True)})
    t = load_transactions()
    txm = _tx_monthly(t)
    # primer mes: si la primera transacción cae después del día 5, el mes es parcial y se descarta (D06)
    first = t.group_by("company_id").agg(first_date=pl.col("date").min(), last=pl.col("month").max())
    first = first.with_columns(first=pl.when((pl.col("first_date").dt.day() > 5) & (pl.col("first_date") > PANEL_START))
                               .then(pl.col("first_date").dt.truncate("1mo").dt.offset_by("1mo"))
                               .otherwise(pl.col("first_date").dt.truncate("1mo")))
    grid = comp.select("company_id", "group_id").join(months, how="cross").join(first, on="company_id")
    # la rejilla llega hasta el último mes completo aunque la empresa deje de operar (D07)
    # months_since_final_tx: meses desde la ÚLTIMA transacción del dataset (no causal, solo para etiquetas de apagado)
    grid = grid.filter(pl.col("month") >= pl.col("first")).with_columns(
        months_since_final_tx=pl.max_horizontal((pl.col("month").dt.year() * 12 + pl.col("month").dt.month())
                                                - (pl.col("last").dt.year() * 12 + pl.col("last").dt.month()), pl.lit(0)),
    ).drop("first", "first_date", "last")
    inv = _invoices_monthly(months)
    p = (grid.join(txm, on=["company_id", "month"], how="left")
             .join(_balances_backward(t, CASH_TYPES, months, "cash_end"), on=["company_id", "month"], how="left")
             .join(_credit_lines(t, months), on=["company_id", "month"], how="left")
             .join(inv, on=["company_id", "month"], how="left"))
    fxm = _fx_table()
    ccur = comp.select("company_id", pl.col("currency").alias("ccur"))
    p = (p.join(ccur, on="company_id").join(fxm.rename({"currency": "ccur"}), on=["month", "ccur"], how="left")
          .with_columns(to_eur=1.0 / pl.col("per_eur").fill_null(1.0)).drop("per_eur"))
    flow_cols = ["n_fx_fixed", "uncat_in", "intragroup_flow", "n_tx", "inflow", "outflow", "oper_in", "transfer_in", "payroll", "salary", "social_security", "tax", "debt_service", "fees",
                 "refunds", "foreign_flow", "gross_flow", "internal_flow", "n_sentinel_tx"]
    p = p.with_columns([pl.col(c).fill_null(0) for c in flow_cols])
    # inactividad causal (D07): meses consecutivos sin movimientos hasta m (se reinicia al volver a operar)
    # cada racha (run_id) empieza en su mes activo, que ocupa la posición 0; si la serie arranca inactiva (run_id 0) no hay mes activo
    p = p.sort("company_id", "month").with_columns(active=(pl.col("n_tx") > 0).cast(pl.Int32))
    p = p.with_columns(run_id=pl.col("active").cum_sum().over("company_id", order_by="month"))
    p = p.with_columns(months_since_last_tx=pl.when(pl.col("active") == 1).then(0)
                       .otherwise(pl.int_range(0, pl.len()).over(["company_id", "run_id"], order_by="month")
                                  + (pl.col("run_id") == 0).cast(pl.Int64))).drop("active", "run_id")
    # flags de calidad (fase 0, salida/datos_limpieza.md): informativos, ninguna feature los consume todavía
    gf12 = pl.col("gross_flow").rolling_mean(12, min_samples=1).over("company_id", order_by="month")
    ig3 = pl.col("intragroup_flow").rolling_sum(3, min_samples=1).over("company_id", order_by="month")
    gross3 = pl.col("gross_flow").rolling_sum(3, min_samples=1).over("company_id", order_by="month")
    drift = p.group_by("company_id").agg(has_drift=(pl.col("outflow").median() > 0) & (pl.col("cash_end").min() < -pl.col("outflow").median()))
    p = p.join(drift, on="company_id", how="left").with_columns(
        dq_cash_sentinel=pl.col("company_id").is_in(_sentinel_cash_companies(t).implode()),
        dq_cash_implausible=(pl.col("cash_end").abs() * pl.col("to_eur")) > pl.max_horizontal(50 * gf12 * pl.col("to_eur"), pl.lit(IMPLAUSIBLE_FLOOR_EUR)),
        intragroup_share_3m=ig3 / (gross3 + ig3 + 1),
        dq_edge_month=pl.col("month") == LAST_FULL_MONTH,
        has_drift=pl.col("has_drift").fill_null(False),
    )
    erp_ids = pl.read_parquet(DATA / "invoices.parquet")["company_id"].unique().implode()
    p = p.with_columns(has_erp=pl.col("company_id").is_in(erp_ids))
    inv_cols = ["late_share_ar", "late_share_ap", "overdue_ar", "overdue_ap", "overdue_90_ar", "overdue_90_ap"]
    for c in inv_cols:
        if c not in p.columns:
            p = p.with_columns(pl.lit(None, dtype=pl.Float64).alias(c))
    # con ERP y ya con facturas (2 meses tras la primera), ausencia de vencidos = 0; antes, desconocido
    has_inv = pl.col("has_erp") & pl.col("first_inv").is_not_null() & (pl.col("month") >= pl.col("first_inv").dt.offset_by("2mo"))
    p = p.with_columns([pl.when(has_inv).then(pl.col(c).fill_null(0)).otherwise(pl.col(c)).alias(c)
                        for c in ["overdue_ar", "overdue_ap", "overdue_90_ar", "overdue_90_ap"]])
    return p.sort("company_id", "month")


if __name__ == "__main__":
    p = build_panel()
    p.write_parquet(DATA / "panel.parquet")
    print(p.shape)
    print(p.null_count().transpose(include_header=True).filter(pl.col("column_0") > 0))
