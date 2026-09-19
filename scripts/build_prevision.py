"""Previsión de tesorería a tres meses para la pestaña «Flujo de caja» del panel de la empresa.

Parte de la foto del 1 de septiembre de 2026 y suma, día a día, lo que ya se sabe que va a pasar:

    caja(d) = caja a cierre de agosto (panel_monthly.cash_end, el mismo número que sirve Supabase)
            + facturas emitidas pendientes que vencen en (1 sep, d]
            − facturas recibidas pendientes que vencen en (1 sep, d]
            − nóminas y seguridad social (mediana de 6 meses, en su día habitual del mes)
            − cuotas de deuda            (mediana de 6 meses, en su día habitual del mes)

Es la fórmula estricta de research/src/proactive.py llevada al día: sin impuestos ni flujos sin factura, que se
midieron peor. Con ese camino marca dos casos:

- rotura: el saldo baja de cero algún día del horizonte. Si un cobro lo devuelve a positivo más tarde, se
  guarda ese cobro: es el hueco de calendario que se cubre con financiación a corto.
- excedente: sin rotura, lo que sobra por encima de un colchón de tres meses de gasto en el peor día.

Guarda también el desglose por categoría bancaria de los últimos 12 meses, que Supabase no tiene. Solo entran
facturas en la moneda de la empresa. Escribe frontend/server/assets/prevision.json (asset de Nitro).

    uv run --no-project --with duckdb --with pandas python scripts/build_prevision.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend" / "data"
PANEL = ROOT / "data" / "processed" / "panel_monthly.csv"
OUT = ROOT / "frontend" / "server" / "assets" / "prevision.json"

SNAPSHOT = pd.Timestamp("2026-09-01")
HORIZON = pd.date_range("2026-09-02", "2026-11-30", freq="D")
MONTHS = ["2026-09", "2026-10", "2026-11"]
CUSHION_MONTHS = 3
# Los casos reales de la demo (frontend/shared/demoCases.ts). COMP_0837 tiene excedente pero no score sano.
DEMO = {"COMP_0835": "excedente", "COMP_0837": "excedente", "COMP_0829": "rotura"}


def recurring_day(tx: pd.DataFrame, cid: str, cats: set[str]) -> int:
    """Día del mes en que sale la mayor parte del importe de esas categorías en los últimos 6 meses."""
    rows = tx[(tx.company_id == cid) & tx.category.isin(cats)]
    if rows.empty:
        return 28
    by_day = rows.groupby(rows.date.dt.day).amount.sum().abs()
    return int(min(by_day.idxmax(), 28))


def main() -> None:
    con = duckdb.connect()
    panel = pd.read_csv(PANEL, parse_dates=["month"])
    comp = con.sql(f"select company_id, currency from '{DATA / 'companies.parquet'}'").df().set_index("company_id")
    last = panel[panel.month == "2026-08-01"].set_index("company_id")
    recent = panel[panel.month >= "2026-03-01"].groupby("company_id")
    med = pd.DataFrame({
        "salary": recent.out_salary.median(),
        "ss": recent.out_social_security.median(),
        "debt": recent.debt_service.median(),
        "spend": (panel.outflow_op + panel.debt_service).groupby(panel.company_id).apply(
            lambda s: s[panel.loc[s.index, "month"] >= "2026-03-01"].median()),
    })

    inv = con.sql(f"""
        select i.company_id, i.counterparty_id, i.due_date::date as due, i.amount > 0 as ar, abs(i.pending_amount) as amt
        from '{DATA / 'invoices.parquet'}' i join '{DATA / 'companies.parquet'}' c using (company_id)
        where i.document_type in ('invoice', 'invoiceGroup') and i.status not in ('cancel', 'paid')
          and abs(i.pending_amount) > 0 and i.currency = c.currency
          and i.issuance_date <= '{SNAPSHOT:%Y-%m-%d}'
          and i.due_date >= '2026-09-02' and i.due_date < '2026-12-01'""").df()
    inv["due"] = pd.to_datetime(inv.due)
    tx = con.sql(f"""
        select company_id, date, amount, category from '{DATA / 'transactions.parquet'}'
        where date >= '2026-03-01' and category in ('salary', 'social_security', 'debt_repayment')""").df()

    # Desglose por categoría bancaria de los últimos 12 meses, con las mismas reglas que scripts/build_panel.py
    # (solo cuentas de banco, importe / exchange_rate, winsorizado a p0,1 / p99,9): así cada mes suma el
    # net_bank de panel_monthly y la tabla cuadra con la caja de Supabase.
    cats = con.sql(f"""
        with t as (
            select t.company_id, date_trunc('month', t.date) as m, coalesce(nullif(t.category, '-'), 'sin_categoria') as cat,
                   case when t.exchange_rate > 0 then t.amount / t.exchange_rate else t.amount end as a
            from '{DATA / 'transactions.parquet'}' t
            where t.product_id in (select product_id from '{DATA / 'banking_products.parquet'}')),
        q as (select quantile_cont(a, 0.001) as lo, quantile_cont(a, 0.999) as hi from t)
        select company_id, strftime(m, '%Y-%m') as month, cat, sum(least(greatest(a, lo), hi)) as amount
        from t, q where m >= '2025-09-01' and m < '2026-09-01' group by all""").df()
    by_company = {cid: {mm: {r.cat: round(float(r.amount), 2) for r in gm.itertuples() if abs(r.amount) >= 0.005}
                        for mm, gm in g.groupby("month")}
                  for cid, g in cats.groupby("company_id")}

    out: dict[str, dict] = {}
    for cid, row in last.iterrows():
        cash0 = float(row.cash_end)
        if pd.isna(cash0) or bool(row.saldo_inconsistente) or cash0 <= 0:
            if cid in by_company:
                out[cid] = {"currency": comp.currency.get(cid, "EUR"), "categories": by_company[cid], "forecast": None}
            continue
        m = med.loc[cid] if cid in med.index else None
        salary, ss, debt, spend = (float(m[k]) if m is not None and pd.notna(m[k]) else 0.0
                                   for k in ("salary", "ss", "debt", "spend"))
        g = inv[inv.company_id == cid]
        events = [(r.due, r.amt if r.ar else -r.amt, "cobro" if r.ar else "pago", r.counterparty_id) for r in g.itertuples()]
        for cats, amount, kind in ((("salary",), salary, "nomina"), (("social_security",), ss, "seguridad_social"),
                                   (("debt_repayment",), debt, "deuda")):
            if amount > 0:
                day = recurring_day(tx, cid, set(cats))
                events += [(pd.Timestamp(f"{mm}-{day:02d}"), -amount, kind, None) for mm in MONTHS]
        ev = pd.DataFrame(events, columns=["day", "amount", "kind", "counterparty"])

        monthly = []
        for mm in MONTHS:
            e = ev[ev.day.dt.strftime("%Y-%m") == mm] if len(ev) else ev
            s = lambda k: round(float(e.loc[e.kind == k, "amount"].sum()), 2) if len(e) else 0.0  # noqa: E731
            monthly.append({"month": mm, "cobros": s("cobro"), "proveedores": s("pago"), "nominas": s("nomina"),
                            "seguridad_social": s("seguridad_social"), "deuda": s("deuda")})

        daily = ev.groupby("day").amount.sum().reindex(HORIZON, fill_value=0.0) if len(ev) else pd.Series(0.0, index=HORIZON)
        path = cash0 + daily.cumsum()
        low_day, low = path.idxmin(), float(path.min())

        rotura = None
        if low < 0:
            first = path[path < 0].index[0]
            after = path[(path.index > first) & (path >= 0)]
            back = after.index[0] if len(after) else None
            # el primer tramo en negativo: mínimo y fechas se leen dentro de él, no en otro hueco posterior
            streak = path[(path.index >= first) & ((path.index < back) if back is not None else True)]
            low_day, low = streak.idxmin(), float(streak.min())
            paid = ev[(ev.day <= first) & (ev.amount < 0)]
            rescue = None
            if back is not None:
                inflow = ev[(ev.day == back) & (ev.kind == "cobro")].sort_values("amount")
                if len(inflow):
                    top = inflow.iloc[-1]
                    rescue = {"date": f"{back:%Y-%m-%d}", "amount": round(float(top.amount), 2),
                              "counterparty": top.counterparty if isinstance(top.counterparty, str) else None, "total_day": round(float(inflow.amount.sum()), 2)}
            rotura = {"from": f"{first:%Y-%m-%d}", "to": f"{back - pd.Timedelta(days=1):%Y-%m-%d}" if back is not None else None,
                      "low": round(low, 2), "low_date": f"{low_day:%Y-%m-%d}", "paid_before": round(float(-paid.amount.sum()), 2),
                      "n_paid_before": int(len(paid)), "rescue": rescue}

        cushion = CUSHION_MONTHS * spend
        surplus = low - cushion
        excedente = ({"amount": round(surplus, 2), "cushion": round(cushion, 2), "monthly_spend": round(spend, 2)}
                     if rotura is None and spend > 0 and surplus >= spend else None)

        out[cid] = {"currency": comp.currency.get(cid, "EUR"), "categories": by_company.get(cid, {}),
                    "forecast": {"cash": round(cash0, 2), "months": monthly, "rotura": rotura, "excedente": excedente}}

    for cid, case in DEMO.items():
        assert (out.get(cid, {}).get("forecast") or {}).get(case), f"{cid} ya no cumple el caso {case}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"snapshot": f"{SNAPSHOT:%Y-%m-%d}", "demo": DEMO, "companies": out},
                              ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    n_r = sum(bool((v["forecast"] or {}).get("rotura")) for v in out.values())
    n_e = sum(bool((v["forecast"] or {}).get("excedente")) for v in out.values())
    print(f"{len(out)} empresas · {n_r} con rotura · {n_e} con excedente · {OUT.stat().st_size / 1024:.0f} KB")
    for cid in DEMO:
        print(cid, json.dumps(out[cid]["forecast"], ensure_ascii=False))


if __name__ == "__main__":
    main()
