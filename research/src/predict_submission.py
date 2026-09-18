"""Predicción para empresas nuevas (test oculto) con el modelo entrenado (D23).

    uv run python src/predict_submission.py --csv-dir ../test_output --out ../submission
    # sin argumentos: usa los datos de train (sanity check)

Genera:
- scores_monthly.csv: company_id, month, score, band, confidence, coverage, ood_share, pilares
- forecast_latest.csv: company_id, last_month, score, h1..h3 × (q10, q50, q90), trend, alerts
"""
from __future__ import annotations
import argparse, sys, warnings
from pathlib import Path
import joblib
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel as P  # noqa: E402
from features import add_features  # noqa: E402
from evaluate import build_series, EXOG  # noqa: E402
from xray import PILLARS, band_of, alerts_for  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", help="carpeta con los CSV del test (mismo esquema que output/)")
    ap.add_argument("--out", default=str(ROOT / "submission"))
    a = ap.parse_args()
    if a.csv_dir:
        pq = Path(a.out) / "parquet"; pq.mkdir(parents=True, exist_ok=True)
        for f in Path(a.csv_dir).glob("*.csv"):
            pl.read_csv(f, infer_schema_length=100000, try_parse_dates=True).write_parquet(pq / f"{f.stem}.parquet")
        P.DATA = pq  # el panel se construye con los datos nuevos; los tipos de cambio siguen en data/fx
        raw = P.build_panel()
    else:
        raw = pl.read_parquet(ROOT / "data/panel.parquet")
    art = joblib.load(ROOT / "artifacts/xray.joblib")
    scorer, fc = art["scorer"], art["forecaster"]
    feats = add_features(raw).to_pandas()
    scored = scorer.score_panel(feats)  # transform con cuantiles y pesos congelados en train
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cols = ["company_id", "month", "score", "confidence", "coverage", "ood_share", *[f"p_{p}" for p in PILLARS]]
    m = scored[cols].copy()
    m["band"] = m.score.map(band_of)
    m["month"] = m.month.dt.strftime("%Y-%m")
    m.round(3).to_csv(out / "scores_monthly.csv", index=False)
    ser = build_series(scored, feats)
    pred = fc.predict(ser[["unique_id", "ds", "y", *EXOG]])
    last = ser.sort_values("ds").groupby("unique_id").tail(2)
    cur = last.groupby("unique_id").tail(1).set_index("unique_id")
    prv = last.groupby("unique_id").head(1).set_index("unique_id")
    rows = []
    for uid, g in pred.groupby("unique_id"):
        r = cur.loc[uid]
        row = {"company_id": uid, "last_month": r.ds.strftime("%Y-%m"), "score": round(r.y, 2), "band": band_of(r.y),
               "confidence": round(r.confidence, 3), "fallback": bool(g.fallback.any())}
        for _, x in g.iterrows():
            for q in ("q10", "q50", "q90"):
                row[f"h{int(x.h)}_{q}"] = round(x[q], 2)
        d50 = row["h3_q50"] - r.y
        row["trend"] = "mejora" if d50 >= 8 and row["h3_q10"] - r.y > -3 else "deterioro" if d50 <= -8 and row["h3_q90"] - r.y < 3 else "estable"
        drop = float(r.y - prv.loc[uid].y) if prv.loc[uid].ds < r.ds else None
        al = alerts_for(r.y, {q: row[f"h3_{q}"] for q in ("q10", "q50", "q90")}, drop, bool(r.months_since_last_tx > 0))
        row["alerts"] = " | ".join(f"{x['type']}:{x['severity']}" for x in al)
        rows.append(row)
    pd.DataFrame(rows).to_csv(out / "forecast_latest.csv", index=False)
    print(f"{m.company_id.nunique()} empresas, {len(m)} filas empresa-mes -> {out}")


if __name__ == "__main__":
    main()
