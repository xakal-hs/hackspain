"""¿La nota es relativa o absoluta? Sesgo de tamaño, reparto en poblaciones sanas y escala por probabilidad.

Genera reports/escala.md. Contexto y discusión en REFLEXIONES.md (R1-R4, R9).
    uv run python src/analisis_escala.py
"""
from __future__ import annotations
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import polars as pl
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import EVENTS  # noqa: E402
from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402
from xray import SPEC, HealthScorer  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "escala.md"


def dist(x: pd.Series) -> str:
    return (f"{x.quantile(.1):.0f} | {x.median():.0f} | {x.quantile(.9):.0f} | {(x < 35).mean():.0%} | "
            f"{x.between(35, 65, inclusive='left').mean():.0%} | {(x >= 65).mean():.0%}")


def main() -> None:
    p = add_events(add_features(pl.read_parquet(ROOT / "data/panel.parquet"))).to_pandas().sort_values(["company_id", "month"])
    sc = joblib.load(ROOT / "artifacts/xray.joblib")["scorer"]
    s = sc.score_panel(p)
    p["score"], p["raw"] = s["score"].values, s["score_raw"].values
    q = p[p.months_since_last_tx.fillna(0).eq(0)].copy()
    g = q.groupby("company_id")
    q["burn"] = np.maximum(g.outflow.transform(lambda x: x.rolling(3, 1).mean()),
                           g.outflow.transform(lambda x: x.rolling(12, 1).mean()))
    q["mcaja"] = q.cash_end / q.burn
    L = ["# Escala de la nota: relativa frente a absoluta", "",
         "Generado por `src/analisis_escala.py` con `artifacts/xray.joblib` (v6). Meses activos del train. "
         "Discusión en `REFLEXIONES.md`.", ""]

    # 1. reparto por poblaciones
    neverneg = p.groupby("company_id").cash_end.min().gt(0)
    medm = q.groupby("company_id").mcaja.median()
    sanas = set(medm[medm >= 3].index) & set(neverneg[neverneg].index)
    ts = p[p.company_id.isin(sanas)]
    rel = HealthScorer().fit(ts, ts[EVENTS]).score_panel(ts)
    rel = rel[ts.months_since_last_tx.fillna(0).eq(0).values]
    H = "| Población | P10 | Mediana | P90 | Riesgo (<35) | Vigilar | Sano (≥65) | % de meses |\n|---|---|---|---|---|---|---|---|"
    L += ["## 1. Reparto de la nota según la población", "", H,
          f"| Todos los meses activos | {dist(q.score)} | 100 % |",
          f"| Caja > 0 | {dist(q[q.cash_end > 0].score)} | {(q.cash_end > 0).mean():.0%} |",
          f"| ≥ 3 meses de caja | {dist(q[q.mcaja >= 3].score)} | {(q.mcaja >= 3).mean():.0%} |",
          f"| ≥ 6 meses de caja | {dist(q[q.mcaja >= 6].score)} | {(q.mcaja >= 6).mean():.0%} |",
          f"| {len(sanas)} empresas sanas · regla fija del train | {dist(q[q.company_id.isin(sanas)].score)} | — |",
          f"| {len(sanas)} empresas sanas · regla reajustada solo con ellas | {dist(rel.score)} | — |", ""]

    # 2. tamaño
    q["tam"] = pd.qcut(q.log_scale, 5, labels=["Q1 (pequeñas)", "Q2", "Q3", "Q4", "Q5 (grandes)"])
    t = q.groupby("tam", observed=True).agg(nota=("score", "median"), mcaja=("mcaja", "median"),
                                            cs=("cash_stress_6m", "mean"), de=("decline_6m", "mean"), ch=("churn_6m", "mean"))
    L += ["## 2. Tamaño (volumen en EUR, quintiles)", "",
          f"Spearman nota ~ tamaño: {q[['score', 'log_scale']].corr('spearman').iloc[0, 1]:.2f}", "",
          "| Quintil | Nota mediana | Meses de caja (mediana) | Saldo negativo 6m | Caída de cobros 6m | Apagado 6m |",
          "|---|---|---|---|---|---|"]
    L += [f"| {i} | {r.nota:.0f} | {r.mcaja:.2f} | {r.cs:.1%} | {r.de:.1%} | {r.ch:.1%} |" for i, r in t.iterrows()]
    L += ["", "Features con |Spearman| > 0,2 frente al tamaño:", ""]
    for f in SPEC:
        if f in q:
            r = q[[f, "log_scale"]].corr("spearman").iloc[0, 1]
            if abs(r) > .2:
                L.append(f"- `{f}`: {r:.2f}")
    L.append("")

    # 3. escala por probabilidad
    m = q[["cash_stress_6m", "decline_6m"]].notna().all(1)
    y = (q.loc[m, "cash_stress_6m"].eq(1) | q.loc[m, "decline_6m"].eq(1)).astype(int)
    lr = LogisticRegression().fit(q.loc[m, ["raw"]], y)
    L += ["## 3. Nota → probabilidad de evento adverso (saldo negativo o caída de cobros en 6 meses)", "",
          f"Tasa base: {y.mean():.1%}. Logística de un parámetro sobre la nota sin suavizar.", "",
          "| Nota | " + " | ".join(str(x) for x in (10, 30, 50, 70, 90)) + " |", "|---|---|---|---|---|---|",
          "| P(adverso) | " + " | ".join(f"{lr.predict_proba(pd.DataFrame({'raw': [x]}))[0, 1]:.0%}" for x in (10, 30, 50, 70, 90)) + " |", ""]

    # 4. coherencia caja reconstruida vs flujos
    d = p.copy()
    d["dcash"] = d.groupby("company_id").cash_end.diff()
    d["vol"] = np.maximum(d.inflow, d.outflow)
    mm = d.dcash.notna() & (d.vol > 1000)
    r = ((d.dcash - (d.inflow - d.outflow)).abs() / d.vol)[mm]
    bad = d[mm].assign(bad=r > .5).groupby("company_id").bad.mean()
    L += ["## 4. ¿Cuadra la caja reconstruida con los flujos?", "",
          "Descuadre = |Δcaja − (cobros − pagos)| / max(cobros, pagos), en meses con flujo > 1.000.", "",
          f"- Mediana {r.median():.2f}, P75 {r.quantile(.75):.2f}, P90 {r.quantile(.9):.2f}.",
          f"- Meses con descuadre > 50 % del flujo: {(r > .5).mean():.1%}.",
          f"- Empresas con más de la mitad de sus meses descuadrados: {(bad > .5).mean():.1%}.", ""]
    OUT.write_text("\n".join(L))
    print(OUT.read_text())


if __name__ == "__main__":
    main()
