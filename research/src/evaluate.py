"""Validación v4: GroupKFold por group_id x cortes temporales, sin fuga.

- El scorer se ajusta con empresas de train y meses <= corte; si calibra pesos, solo usa filas
  cuyo evento a 6 meses ya era observable en el corte (mes <= corte − 6).
- El forecaster (cuantílico) se ajusta con series de train hasta el corte y predice validación con new_df.
Uso: uv run python evaluate.py <tag> [--prior] [--no-exog]
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd, polars as pl
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
from features import add_features
from targets import add_events
from xray import HealthScorer, TrajectoryForecaster

ROOT = Path(__file__).resolve().parents[1]
H, EVENT = 3, 15.0  # movimiento real = 15 pts en la escala publicada (ejemplos del enunciado: 45→65, 82→68)
EVENTS = ["churn_6m", "cash_stress_6m", "decline_6m", "positive_6m"]  # tres adversos + uno positivo (dos caras)
CUTOFFS = [pd.Timestamp("2025-11-01"), pd.Timestamp("2026-02-01"), pd.Timestamp("2026-05-01")]
EXOG_SMALL = ["score_raw", "score_raw_d3", "runway", "activity_trend", "months_since_last_tx", "month_idx"]
STRONG = dict(n_estimators=150, learning_rate=0.04, num_leaves=7, min_child_samples=200, colsample_bytree=0.5, reg_lambda=5.0)
EXOG_FULL = ["score_raw", "p_liquidez", "p_rentabilidad", "p_solvencia", "p_disciplina", "p_estabilidad", "coverage",
        "runway", "growth_vs_12m", "activity_trend", "ap_late_share", "net_margin_6m", "transfer_dep", "lc_util",
        "net_vol_6m", "log_scale", "month_idx", "months_since_last_tx", "score_raw_d3", "runway_d3", "has_erp_f"]
EXOG = EXOG_SMALL  # decisión final (v5b): 6 exógenas; las 21 sobreajustan a h3 (D20)


def load() -> pd.DataFrame:
    return add_events(add_features(pl.read_parquet(ROOT / "data/panel.parquet"))).to_pandas()


def build_series(scored: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """Serie larga para el forecaster: y = score publicado + exógenas contemporáneas."""
    f = feats[["company_id", "month", "runway", "growth_vs_12m", "activity_trend", "ap_late_share", "net_margin_6m",
               "transfer_dep", "lc_util", "net_vol_6m", "log_scale", "month_idx", "months_since_last_tx", "has_erp"]]
    s = scored.merge(f, on=["company_id", "month"], how="left").sort_values(["company_id", "month"])
    g = s.groupby("company_id")
    s["score_raw_d3"] = s["score_raw"] - g["score_raw"].shift(3)
    s["runway_d3"] = s["runway"] - g["runway"].shift(3)
    s["has_erp_f"] = s["has_erp"].astype(float)
    return s.rename(columns={"company_id": "unique_id", "month": "ds", "score": "y"})


def fit_scorer(train_rows: pd.DataFrame, cut: pd.Timestamp, calibrate: bool) -> HealthScorer:
    sc = HealthScorer(calibrate=calibrate)
    if calibrate:
        obs = train_rows.month <= cut - pd.DateOffset(months=6)  # evento ya observado en el corte (sin fuga)
        lab = train_rows[EVENTS].where(obs, axis=0)
        return sc.fit(train_rows, lab)
    return sc.fit(train_rows)


def _auc(y, s):
    m = pd.notna(y) & pd.notna(s)
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    return float(roc_auc_score(y, s)) if len(np.unique(y)) > 1 else None


def run(tag: str, calibrate: bool = True, use_exog: bool = True, exog: list | None = None, lgb_params: dict | None = None) -> dict:
    EXOG = exog if exog is not None else globals()["EXOG"]
    panel = load()
    cg = panel.drop_duplicates("company_id").set_index("company_id")["group_id"]
    ids = cg.index.to_numpy()
    rows, ext_rows, weights = [], [], []
    for fold, (tr, va) in enumerate(GroupKFold(n_splits=5).split(ids, groups=cg.values)):
        tr_ids, va_ids = set(ids[tr]), set(ids[va])
        for cut in CUTOFFS:
            hist = panel[panel.month <= cut]
            scorer = fit_scorer(hist[hist.company_id.isin(tr_ids)], cut, calibrate)
            weights.append(scorer.weights_)
            sc = scorer.score_panel(panel)
            s = build_series(sc, panel)
            s_hist = s[s.ds <= cut]
            train = s_hist[s_hist.unique_id.isin(tr_ids)]
            val_hist = s_hist[s_hist.unique_id.isin(va_ids)]
            fc = TrajectoryForecaster(horizon=H, exog=tuple(EXOG) if use_exog else (), lgb_params=lgb_params).fit(
                train[["unique_id", "ds", "y", *(EXOG if use_exog else [])]])
            pred = fc.predict(val_hist[["unique_id", "ds", "y", *(EXOG if use_exog else [])]])
            fut = s[(s.ds > cut) & (s.ds <= cut + pd.DateOffset(months=H)) & s.unique_id.isin(va_ids)]
            last = val_hist.sort_values("ds").groupby("unique_id").tail(1).set_index("unique_id")
            pr = pred.merge(fut[["unique_id", "ds", "y", "ood_share", "coverage"]], on=["unique_id", "ds"])
            pr["y_last"] = pr.unique_id.map(last["y"])
            pr["raw_last"] = pr.unique_id.map(last["score_raw"])
            pr["n_hist"] = pr.unique_id.map(val_hist.groupby("unique_id").size())
            a_b = {h: fc.fallback_[h][:2] for h in range(1, H + 1)}
            pr["y_ar1"] = [a_b[h][0] * yl + a_b[h][1] for h, yl in zip(pr.h, pr.y_last)]
            pr["fold"], pr["cutoff"] = fold, cut
            rows.append(pr)
            # validez externa del NIVEL: score en el corte vs eventos en los 6 meses siguientes
            at = sc[(sc.month == cut) & sc.company_id.isin(va_ids)][["company_id", "score", "score_raw"]]
            ev = panel[panel.month == cut][["company_id", "adverse_6m", "churn_6m", "cash_stress_6m", "decline_6m",
                                             "positive_6m", "has_erp", "month_idx"]]
            ext_rows.append(at.merge(ev, on="company_id").assign(cutoff=cut))
    res = pd.concat(rows, ignore_index=True)
    ext = pd.concat(ext_rows, ignore_index=True)
    res.to_parquet(ROOT / f"reports/preds_{tag}.parquet")
    out = summarize(res, tag)
    for e in ["adverse_6m", "churn_6m", "cash_stress_6m", "decline_6m"]:
        out[f"auc_level_vs_{e}"] = _auc(ext[e], -ext.score)
    out["auc_level_vs_positive_6m"] = _auc(ext["positive_6m"], ext.score)
    w = pd.DataFrame(weights)
    out["weights_mean"] = w.mean().round(4).to_dict()
    out["weights_std"] = w.std().round(4).to_dict()
    return out


def summarize(res: pd.DataFrame, tag: str) -> dict:
    out = {"tag": tag, "n_series": int(res.groupby(["unique_id", "cutoff"]).ngroups)}
    for h in range(1, H + 1):
        r = res[res.h == h]
        out[f"mae_h{h}"] = float((r.y - r.q50).abs().mean())
        out[f"mae_naive_h{h}"] = float((r.y - r.y_last).abs().mean())
        out[f"mae_ar1_h{h}"] = float((r.y - r.y_ar1).abs().mean())
    r1 = res[res.h == 1]
    out["mae_naive_ewma_h1"] = float((r1.y - (0.5 * r1.y_last + 0.5 * r1.raw_last)).abs().mean())  # arrastre mecánico del EWMA
    r = res[res.h == H].copy()
    out["skill_vs_naive_h3"] = 1 - out["mae_h3"] / out["mae_naive_h3"]
    out["skill_vs_ar1_h3"] = 1 - out["mae_h3"] / out["mae_ar1_h3"]
    # cuantiles: cobertura del intervalo 80 % y pérdida pinball
    for h in range(1, H + 1):
        rh = res[res.h == h]
        out[f"coverage80_h{h}"] = float(((rh.y >= rh.q10) & (rh.y <= rh.q90)).mean())
        out[f"width80_h{h}"] = float((rh.q90 - rh.q10).mean())
    pin = lambda y, q, a: np.mean(np.maximum(a * (y - q), (a - 1) * (y - q)))
    out["pinball_h3"] = float(np.mean([pin(r.y, r[f"q{int(a * 100)}"], a) for a in (0.1, 0.5, 0.9)]))
    d_true, d_hat, d_ar = r.y - r.y_last, r.q50 - r.y_last, r.y_ar1 - r.y_last
    big = d_true.abs() >= EVENT
    out["share_big_moves"] = float(big.mean())
    out["dir_acc_big_moves"] = float((np.sign(d_true[big]) == np.sign(d_hat[big])).mean())
    down, up = (d_true <= -EVENT).astype(int), (d_true >= EVENT).astype(int)
    out["auc_deterioro"], out["auc_deterioro_ar1"] = _auc(down, -d_hat), _auc(down, -d_ar)
    out["auc_mejora"], out["auc_mejora_ar1"] = _auc(up, d_hat), _auc(up, d_ar)
    q = r.y_last >= r.y_last.quantile(0.8)
    out["auc_deterioro_top_quintil"] = _auc(down[q], -d_hat[q])
    out["auc_deterioro_top_quintil_ar1"] = _auc(down[q], -d_ar[q])
    ql = r.y_last <= r.y_last.quantile(0.2)
    out["auc_mejora_bottom_quintil"] = _auc(up[ql], d_hat[ql])
    out["auc_mejora_bottom_quintil_ar1"] = _auc(up[ql], d_ar[ql])
    # precisión en la cola: el 5 % de series con mayor caída/subida prevista (donde se actúa)
    for name, score_m, score_a, ev in [("down", -d_hat, -d_ar, down), ("up", d_hat, d_ar, up)]:
        k = max(1, int(0.05 * len(r)))
        out[f"prec_top5_{name}"] = float(ev.loc[score_m.nlargest(k).index].mean())
        out[f"prec_top5_{name}_ar1"] = float(ev.loc[score_a.nlargest(k).index].mean())
    # "quién está sano": persistencia de la banda sana a 3 meses
    sano = r.y_last >= 65
    out["p_sigue_sano_3m"] = float((r.y[sano] >= 65).mean()) if sano.any() else None
    # alertas (regla del monitor)
    alert_down = d_hat <= -10
    out["alert_down_precision"] = float(down[alert_down].mean()) if alert_down.any() else None
    out["alert_down_recall"] = float(alert_down[down == 1].mean()) if down.any() else None
    alert_up = d_hat >= 10
    out["alert_up_precision"] = float(up[alert_up].mean()) if alert_up.any() else None
    out["alert_up_recall"] = float(alert_up[up == 1].mean()) if up.any() else None
    # segmentos (proxy de OOD / test oculto)
    e = (r.y - r.q50).abs()
    seg = {"historia<6m": r.n_hist < 6, "historia>=12m": r.n_hist >= 12, "ood_share>0": r.ood_share > 0,
           "fallback": r.fallback.astype(bool), "cobertura<0.6": r.coverage < 0.6}
    out["mae_h3_by_segment"] = {k: {"n": int(m.sum()), "mae": float(e[m].mean()) if m.any() else None,
                                    "mae_ar1": float((r.y - r.y_ar1).abs()[m].mean()) if m.any() else None,
                                    "coverage80": float(((r.y >= r.q10) & (r.y <= r.q90))[m].mean()) if m.any() else None}
                                for k, m in seg.items()}
    out["mae_h3_by_cutoff"] = {str(k.date()): float(v) for k, v in r.assign(e=e).groupby("cutoff")["e"].mean().items()}
    return out


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "v4"
    ex = EXOG_SMALL if "--small" in sys.argv else (EXOG_FULL if "--full" in sys.argv else None)
    res = run(tag, calibrate="--prior" not in sys.argv, use_exog="--no-exog" not in sys.argv, exog=ex,
              lgb_params=STRONG if "--strong" in sys.argv else None)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    (ROOT / f"reports/metrics_{tag}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
