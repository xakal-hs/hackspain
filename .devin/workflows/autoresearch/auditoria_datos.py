"""Auditoría de datos: escanea los parquet crudos y el panel y cuantifica lo raro.

Da la evidencia para que el consejo discuta **qué es suciedad y qué es real** antes de limpiar.
No modifica nada: solo lee y reporta.

    cd research && uv run python ../.devin/workflows/autoresearch/auditoria_datos.py            # markdown
    cd research && uv run python ../.devin/workflows/autoresearch/auditoria_datos.py --json
    cd research && uv run python ../.devin/workflows/autoresearch/auditoria_datos.py --out ../.devin/workflows/autoresearch/salida/auditoria_datos.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import polars as pl

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
DATA = ROOT / "research" / "data"
WINDOW = (pl.date(2024, 9, 1), pl.date(2026, 9, 30))
SENTINEL = 1e8  # en EUR: en moneda cruda 478/491 transacciones > 1e8 son AOA/COP/VND/CLP (fase 0, A01)

import sys  # noqa: E402
sys.path.insert(0, str(ROOT / "research" / "src"))


def _per_eur() -> pl.DataFrame:
    """Unidades por EUR del último mes con tipo real (BCE / currency-api), por moneda."""
    import fx as FX
    f = pl.from_pandas(FX.load()[["month", "currency", "per_eur"]])
    return f.filter(pl.col("month") == f["month"].max()).select("currency", "per_eur")


def _c(d: pl.DataFrame, expr: pl.Expr) -> int:
    try:
        return int(d.select(expr.fill_null(False).sum()).item() or 0)
    except Exception:
        return -1


def auditar() -> list[dict]:
    out: list[dict] = []
    tx = pl.read_parquet(DATA / "transactions.parquet")
    inv = pl.read_parquet(DATA / "invoices.parquet")
    bal = pl.read_parquet(DATA / "balances.parquet")
    comp = pl.read_parquet(DATA / "companies.parquet")
    pan = pl.read_parquet(DATA / "panel.parquet")
    bp = pl.read_parquet(DATA / "banking_products.parquet").select("product_id", "type", pl.col("currency").alias("pcur"))
    dp = pl.read_parquet(DATA / "debt_products.parquet").select("product_id", "type", pl.col("currency").alias("pcur"))
    prods = pl.concat([bp, dp])
    pe = _per_eur().rename({"currency": "pcur"})
    tx = tx.join(prods.select("product_id", "pcur"), on="product_id", how="left").join(pe, on="pcur", how="left") \
           .with_columns(amount_eur=pl.col("amount") / pl.col("per_eur").fill_null(1.0))
    inv = inv.join(pe.rename({"pcur": "currency"}), on="currency", how="left") \
             .with_columns(amount_eur=pl.col("amount") / pl.col("per_eur").fill_null(1.0))
    bal = bal.join(prods, on="product_id", how="left").join(pe, on="pcur", how="left") \
             .with_columns(balance_eur=pl.col("balance") / pl.col("per_eur").fill_null(1.0))
    CASH = ["checking", "saving", "investment", "tpv", "expensesPlatform", "wallet"]

    def add(fuente, check, n, total, nota=""):
        out.append({"fuente": fuente, "check": check, "n": n, "total": total,
                    "pct": round(100 * n / total, 3) if total else None, "nota": nota})

    # --- transactions
    T = tx.height
    add("transactions", "exchange_rate <= 0", _c(tx, pl.col("exchange_rate") <= 0), T, "rompe la conversión de moneda (D03)")
    add("transactions", "|amount| > 1e8 en moneda cruda", _c(tx, pl.col("amount").abs() > SENTINEL), T, "478 son AOA/COP/VND/CLP: moneda, no centinela")
    add("transactions", "|amount| > 1e8 EUR (centinela real)", _c(tx, pl.col("amount_eur").abs() > SENTINEL), T, "importes redondos de generador (1e9, 3e8…)")
    add("transactions", "category '-' o nula", _c(tx, (pl.col("category") == "-") | pl.col("category").is_null()), T, "flujo sin categorizar")
    add("transactions", "value_date año >= 2099", _c(tx, pl.col("value_date").dt.year() >= 2099), T, "fecha imposible")
    add("transactions", "value_date fuera de ventana", _c(tx, (pl.col("value_date") < WINDOW[0]) | (pl.col("value_date") > WINDOW[1])), T, "anterior/posterior al reto")
    add("transactions", "transaction_id duplicado", T - tx["transaction_id"].n_unique(), T, "clave repetida")
    add("transactions", "status 'pending' (fuera del panel)", _c(tx, pl.col("status") == "pending"), T, "excluidas en panel.py:34; parte del hueco de agosto-26")
    add("transactions", "empresas con centinela (EUR)", int(tx.filter(pl.col("amount_eur").abs() > SENTINEL)["company_id"].n_unique()), int(tx["company_id"].n_unique()), "22 en moneda cruda; 7 en EUR")

    # --- invoices
    I = inv.height
    add("invoices", "due_date < issuance_date", _c(inv, pl.col("due_date") < pl.col("issuance_date")), I, "fecha imposible")
    add("invoices", "payment_date < issuance_date", _c(inv, pl.col("payment_date") < pl.col("issuance_date")), I, "fecha imposible")
    add("invoices", "año >= 2100", _c(inv, (pl.col("due_date").dt.year() >= 2100) | (pl.col("issuance_date").dt.year() >= 2100)), I, "p. ej. año 7025")
    add("invoices", "pending_amount != 0 con status 'paid'", _c(inv, (pl.col("pending_amount") != 0) & (pl.col("status") == "paid")), I, "contradicción de estado (D05)")
    add("invoices", "overdue con payment_date == due_date", _c(inv, (pl.col("status") == "overdue") & (pl.col("payment_date") == pl.col("due_date"))), I, "payment_date es alias del vencimiento (D05)")
    add("invoices", "|amount| > 1e8 en moneda cruda", _c(inv, pl.col("amount").abs() > SENTINEL), I, "casi todas COP (COMP_1244, COMP_0629)")
    add("invoices", "|amount| > 1e8 EUR (centinela real)", _c(inv, pl.col("amount_eur").abs() > SENTINEL), I, "3 empresas; 5 facturas tras el filtro del panel")
    add("invoices", "paymentDocument", _c(inv, pl.col("document_type") == "paymentDocument"), I, "base de pagarés/anticipo (fase 4)")
    add("invoices", "issuance_date el día de la foto con hora (2026-09-01 hh:mm:ss)", _c(inv, pl.col("issuance_date") > pl.datetime(2026, 9, 1)), I, "no es futuro: 4 642 más a las 00:00 del mismo día")
    add("invoices", "issuance_date posterior al día de la foto", _c(inv, pl.col("issuance_date") >= pl.datetime(2026, 9, 2)), I, "factura del futuro (fuga as-of)")
    add("invoices", "amount == 0", _c(inv, pl.col("amount") == 0), I, "sin importe: no aporta a ratios")
    add("invoices", "counterparty_id nulo", _c(inv, pl.col("counterparty_id").is_null()), I, "fuera de HHI y lost_share")
    add("invoices", "counterparty_id de 19 chars (número ≥ 100000)", _c(inv, pl.col("counterparty_id").cast(pl.Utf8, strict=False).str.len_chars() == 19), I, "no es ancho variable: son ids reales ≥ 100000")

    # --- balances
    B = bal.height
    add("balances", "|balance| > 1e8 en moneda cruda", _c(bal, pl.col("balance").abs() > SENTINEL), B, "11 son COP/AOA/VND/CLP/XOF")
    add("balances", "|balance| > 1e8 EUR en producto de caja (centinela real)", _c(bal, (pl.col("balance_eur").abs() > SENTINEL) & pl.col("type").is_in(CASH)), B, "COMP_1068 1e11, COMP_0420 −1e9 ×2, COMP_0604 1e9")
    add("balances", "|balance| > 1e8 EUR en préstamo", _c(bal, (pl.col("balance_eur").abs() > SENTINEL) & ~pl.col("type").is_in(CASH).fill_null(True)), B, "COMP_0415 −3e8, COMP_0630 −1,25e8: deuda plausible")
    add("balances", "foto distinta de 2026-09-01", _c(bal, pl.col("date") != pl.date(2026, 9, 1)), B, "aceptado como as-of")

    # --- companies
    C = comp.height
    iso = pl.col("country").cast(pl.Utf8, strict=False).str.contains(r"^[A-Z]{2}$")
    add("companies", "country nulo o no ISO-2", C - _c(comp, iso), C, "82% sin país (AGENTS)")
    add("companies", "ERP en vocabulario de grupo", _c(comp, pl.col("erp").is_null()), C, "crosswalk de vocabularios")

    # --- panel (lo que ve el score)
    P = pan.height
    gf = pl.col("gross_flow") + 1
    pan = pan.sort("company_id", "month").with_columns(
        gf12=pl.col("gross_flow").rolling_mean(12, min_samples=1).over("company_id", order_by="month"))
    add("panel", "|cash_end| > 1e8 en moneda de la empresa", _c(pan, pl.col("cash_end").abs() > SENTINEL), P, "incluye AOA/COP/VND: no es centinela")
    add("panel", "|cash_end·to_eur| > 1e8 (centinela dentro del panel)", _c(pan, (pl.col("cash_end") * pl.col("to_eur")).abs() > SENTINEL), P, "runway/net_vol basura; flag dq_cash_sentinel")
    if "dq_cash_sentinel" in pan.columns:
        add("panel", "filas de empresas con centinela EUR (dq_cash_sentinel)", _c(pan, pl.col("dq_cash_sentinel")), P, f"{pan.filter(pl.col('dq_cash_sentinel'))['company_id'].n_unique()} empresas")
        add("panel", "empresas con deriva de back-cast (has_drift)", _c(pan, pl.col("has_drift")), P, f"{pan.filter(pl.col('has_drift'))['company_id'].n_unique()} empresas; min(caja) < −mediana(pagos)")
        add("panel", "caja implausible en EUR (dq_cash_implausible, suelo 1e5 €)", _c(pan, pl.col("dq_cash_implausible")), P, f"{pan.filter(pl.col('dq_cash_implausible'))['company_id'].n_unique()} empresas")
        add("panel", "AR con cobertura de contraparte < 0.8 (ar_id_coverage)", _c(pan, pl.col("ar_id_coverage") < 0.8), P, "HHI/lost_share sobre una fracción de la cartera")
    add("panel", "caja negativa de magnitud < 0,01 (ceros de coma flotante)", _c(pan, (pl.col("cash_end") < 0) & (pl.col("cash_end") > -0.01)), P, "0 tras redondear a céntimos (panel.py)")
    add("panel", "cash_end implausible (|caja| > 50·flujo 12m, targets.py:90)", _c(pan, pl.col("cash_end").abs() > 50 * (pl.col("gf12") + 1)), P, "sin suelo en EUR: marca pymes pequeñas con ahorro")
    add("panel", "mes dormido con caja (gross_flow = 0 y |caja| > 0)", _c(pan, (pl.col("gross_flow") == 0) & (pl.col("cash_end").abs() > 0)), P, "no es implausible: es inactividad con saldo")
    add("panel", "hueco de un solo mes (activo-inactivo-activo) con months_since_last_tx != 1",
        _c(pan.sort("company_id", "month").with_columns(prev=pl.col("n_tx").shift(1).over("company_id"), nxt=pl.col("n_tx").shift(-1).over("company_id")),
           (pl.col("n_tx") == 0) & (pl.col("prev") > 0) & (pl.col("nxt") > 0) & (pl.col("months_since_last_tx") != 1)), P, "off-by-one corregido (148 antes)")
    add("panel", "meses de inactividad (months_since_last_tx > 0)", _c(pan, pl.col("months_since_last_tx") > 0), P, "no puede puntuar como sano (D07)")
    add("panel", "filas con intragrupo > 20% del bruto", _c(pan, (pl.col("intragroup_flow") / (gf)) > 0.2), P, "cash pooling (R08)")
    add("panel", "empresa-mes duplicado", P - pan.select(["company_id", "month"]).n_unique(), P, "clave repetida")
    add("panel", "fx_share > 0.5 (mitad en divisa)", _c(pan, (pl.col("foreign_flow") / (gf)) > 0.5), P, "moneda dominante distinta")
    add("panel", "empresas intragrupo > 20% en ≥ 80% de sus meses",
        int(pan.with_columns(ig=(pl.col("intragroup_flow") / gf) > 0.2).group_by("company_id").agg(pl.col("ig").mean()).filter(pl.col("ig") >= 0.8).height),
        int(pan["company_id"].n_unique()), "filiales tesoreras / cash pooling estructural (R08)")
    add("panel", "filas de agosto-2026 dormidas", _c(pan, (pl.col("month") == pl.datetime(2026, 8, 1)) & (pl.col("months_since_last_tx") > 0)),
        _c(pan, pl.col("month") == pl.datetime(2026, 8, 1)), "mes de borde (R15): 125 frente a 89 en julio")

    return out


def md(rows: list[dict]) -> str:
    L = ["# Auditoría de datos (anomalías cuantificadas)", "",
         "Fuente: `research/data/*.parquet` (crudos y panel). Esto es **evidencia para el consejo**, no una limpieza.",
         "", "| fuente | check | n | % | nota |", "|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['fuente']} | {r['check']} | {r['n']} | {r['pct']} | {r['nota']} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    rows = auditar()
    txt = json.dumps(rows, ensure_ascii=False, indent=2) if args.json else md(rows)
    if args.out:
        Path(args.out).write_text(txt)
        print(f"escrito {args.out} ({len(rows)} checks)")
    else:
        print(txt)


if __name__ == "__main__":
    main()
