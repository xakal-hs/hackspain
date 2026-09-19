"""Genera reports/panel.html: visor autónomo del panel mensual (selector de empresa, gráficos, tabla y eventos).

Uso: python scripts/panel_html.py   (requiere data/processed/panel_monthly.csv y events_candidates.csv)
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data" / "processed"
p = pd.read_csv(D / "panel_monthly.csv").sort_values(["company_id", "month"])
st = pd.read_csv(D / "company_static.csv").set_index("company_id")
ev_path = D / "events_candidates.csv"
ev = pd.read_csv(ev_path) if ev_path.exists() else None
ev_cols = [c for c in ev.columns if c not in ("company_id", "month")] if ev is not None else []

cols = ["inflow_op", "outflow_op", "net_op", "debt_service", "cash_end", "cash_min", "days_negative", "margin_3m",
        "runway_m", "debt_service_ratio_3m", "pct_vencido", "dso", "payables_overdue90_recent", "n_tx", "hist_months"]
months = sorted(p.month.unique())
midx = {m: i for i, m in enumerate(months)}


def clean(a):
    return [None if (v is None or (isinstance(v, float) and not np.isfinite(v))) else round(float(v), 3) for v in a]


data = {}
for cid, g in p.groupby("company_id"):
    row = {"m0": midx[g.month.iloc[0]], "n": len(g)}
    for c in cols:
        row[c] = clean(g[c].tolist())
    if ev is not None:
        e = ev[ev.company_id == cid].set_index("month")
        for c in ev_cols:
            row["e_" + c] = clean(e[c].reindex(g.month).tolist())
    s = st.loc[cid]
    row["s"] = {k: (None if pd.isna(s[k]) else (bool(s[k]) if isinstance(s[k], (bool, np.bool_)) else (float(s[k]) if isinstance(s[k], (int, float, np.floating, np.integer)) else str(s[k]))))
                for k in ["group_id", "currency", "erp", "tiene_facturas", "tiene_deuda_producto", "paga_deuda_banco",
                          "saldo_inconsistente", "cuentas_moneda_distinta", "debt_util", "meses_historia"]}
    data[cid] = row

html = (ROOT / "scripts" / "panel_template.html").read_text()
html = html.replace("__DATA__", json.dumps({"months": months, "cols": cols, "ev": ev_cols, "companies": data}, separators=(",", ":")))
out = ROOT / "reports" / "panel.html"
out.write_text(html)
print(out, f"{out.stat().st_size/1e6:.1f} MB", len(data), "empresas")
