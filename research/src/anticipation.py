"""Anticipación del modelo final: origen móvil mensual, out-of-fold (GroupKFold por grupo).

Mide, con las reglas del monitor (xray.alerts_for):
- lead time: meses entre la primera alerta de deterioro y el cruce real a banda "riesgo" (<35) en caídas estructurales,
- precisión de las alertas de deterioro/mejora,
- bache vs caída: tras una caída ≥10 en el score bruto, ¿acierta la clasificación?,
- ruido de alertas: tasa de encendido/apagado.
"""
import json, warnings
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
from evaluate import load, ROOT, EXOG, build_series, fit_scorer
from xray import TrajectoryForecaster, alerts_for

warnings.filterwarnings("ignore")
H = 3
panel = load()
cg = panel.drop_duplicates("company_id").set_index("company_id")["group_id"]
ids = cg.index.to_numpy()
cuts = pd.date_range("2025-09-01", "2026-05-01", freq="MS")
import sys
CACHE = ROOT / "reports/alerts_oof_v5.parquet"
rows = []
truth = []
if "--from-cache" in sys.argv and CACHE.exists():
    # reutiliza las alertas out-of-fold y solo recalcula el score "real" de cada fold (scorer sin la empresa)
    for fold, (tr, va) in enumerate(GroupKFold(5).split(ids, groups=cg.values)):
        tr_ids, va_ids = set(ids[tr]), set(ids[va])
        hist = panel[panel.month <= cuts[-1]]
        scorer = fit_scorer(hist[hist.company_id.isin(tr_ids)], cuts[-1], True)
        s = build_series(scorer.score_panel(panel), panel)
        truth.append(s[s.unique_id.isin(va_ids)][["unique_id", "ds", "y", "score_raw"]])
    A = pd.read_parquet(CACHE)
else:
    for fold, (tr, va) in enumerate(GroupKFold(5).split(ids, groups=cg.values)):
        tr_ids, va_ids = set(ids[tr]), set(ids[va])
        for cut in cuts:
            hist = panel[panel.month <= cut]
            scorer = fit_scorer(hist[hist.company_id.isin(tr_ids)], cut, True)
            s = build_series(scorer.score_panel(panel), panel)
            sh = s[s.ds <= cut]
            fc = TrajectoryForecaster(horizon=H, exog=tuple(EXOG)).fit(sh[sh.unique_id.isin(tr_ids)][["unique_id", "ds", "y", *EXOG]])
            vh = sh[sh.unique_id.isin(va_ids)]
            p = fc.predict(vh[["unique_id", "ds", "y", *EXOG]])
            p3 = p[p.h == H].set_index("unique_id")
            last = vh.sort_values("ds").groupby("unique_id").tail(2)
            cur = last.groupby("unique_id").tail(1).set_index("unique_id")
            prv = last.groupby("unique_id").head(1).set_index("unique_id")
            for uid in p3.index:
                r = cur.loc[uid]
                drop = float(r.y - prv.loc[uid].y) if uid in prv.index and prv.loc[uid].ds < r.ds else None
                al = alerts_for(float(r.y), {"q10": p3.loc[uid, "q10"], "q50": p3.loc[uid, "q50"], "q90": p3.loc[uid, "q90"]},
                                drop, bool(r.months_since_last_tx > 0))
                rows.append({"unique_id": uid, "ds": cut, "y": float(r.y), "q50": p3.loc[uid, "q50"], "drop_raw": drop,
                             "types": ",".join(a["type"] for a in al)})
            if cut == cuts[-1]:
                truth.append(s[s.unique_id.isin(va_ids)][["unique_id", "ds", "y", "score_raw"]])
        print("fold", fold, "ok", flush=True)


    A = pd.DataFrame(rows)
T = pd.concat(truth)  # score "real": el de cada fold (scorer ajustado sin la empresa)
A.to_parquet(CACHE)
f = T.merge(A.drop(columns=["y"], errors="ignore"), on=["unique_id", "ds"], how="left").sort_values(["unique_id", "ds"])
g = f.groupby("unique_id")
f["y_f3"] = g.y.shift(-H)
f["raw_prev"] = g.y.shift(1)
f["raw_f2"] = g.y.shift(-2)
out = {}
ev = f[f.types.notna()]
down_true = (ev.y_f3 - ev.y) <= -15
up_true = (ev.y_f3 - ev.y) >= 15
has = lambda t: ev.types.str.contains(t)
m = ev.y_f3.notna()
out["alert_deterioro_n"] = int(has("deterioro")[m].sum())
out["alert_deterioro_precision"] = float(down_true[m & has("deterioro")].mean()) if (m & has("deterioro")).any() else None
out["alert_deterioro_recall"] = float(has("deterioro")[m & down_true].mean()) if (m & down_true).any() else None
out["alert_mejora_n"] = int(has("mejora")[m].sum())
out["alert_mejora_precision"] = float(up_true[m & has("mejora")].mean()) if (m & has("mejora")).any() else None
out["alert_mejora_recall"] = float(has("mejora")[m & up_true].mean()) if (m & up_true).any() else None
out["base_rate_caida10_3m"] = float(down_true[m].mean())
out["base_rate_subida10_3m"] = float(up_true[m].mean())
# lead time: caídas estructurales = el score termina ≥15 por debajo de su media inicial y cruza a <45
lt = []
for uid, gg in f.groupby("unique_id"):
    gg = gg.set_index("ds")
    if len(gg) < 9 or gg.y.iloc[-1] > gg.y.iloc[:3].mean() - 20:
        continue
    below = gg.index[(gg.y < 35) & (gg.index > cuts[0])]
    if len(below) == 0:
        continue
    t_cross = below[0]
    al = gg.index[gg.types.fillna("").str.contains("deterioro|caida") & (gg.index <= t_cross)]
    lt.append((t_cross.to_period("M") - al[0].to_period("M")).n if len(al) else np.nan)
lt = np.array(lt, float)
out["n_caidas_estructurales"] = int(len(lt))
out["share_alertadas_antes"] = float(np.mean(~np.isnan(lt))) if len(lt) else None
out["lead_time_mediana_meses"] = float(np.nanmedian(lt)) if np.any(~np.isnan(lt)) else None
out["lead_time_hist"] = {str(int(k)): int(v) for k, v in pd.Series(lt[~np.isnan(lt)]).value_counts().sort_index().items()}
# bache vs caída (score publicado): caída ≥10 en el mes; "caída" real si 2 meses después sigue ≥ media caída abajo
e = f[(f.drop_raw <= -10) & f.raw_f2.notna()].copy()
e["caida_real"] = (e.raw_f2 < e.raw_prev + e.drop_raw / 2).astype(int)
e["pred_caida"] = e.types.str.contains("caida").astype(int)
out["n_eventos_bajada"] = int(len(e))
out["share_caida_real"] = float(e.caida_real.mean()) if len(e) else None
out["bache_vs_caida_accuracy"] = float((e.caida_real == e.pred_caida).mean()) if len(e) else None
out["bache_vs_caida_auc"] = float(roc_auc_score(e.caida_real, -(e.q50 - e.y))) if e.caida_real.nunique() > 1 else None
# ruido: alertas de deterioro que se encienden y se apagan al mes siguiente
f["on"] = f.types.fillna("").str.contains("deterioro").astype(int)
g = f.groupby("unique_id").on
flick = (g.shift(1) == 0) & (f.on == 1) & (g.shift(-1) == 0)
out["alert_flicker_rate"] = float(flick[f.on == 1].mean()) if f.on.any() else None
print(json.dumps(out, indent=2, ensure_ascii=False))
(ROOT / "reports/anticipation_v5.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
