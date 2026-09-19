"""Medidas del panel para el documento técnico del score (fase 5).

Complementa a `score_datos.py` (que vuelca el artefacto) con los hechos que el documento afirma sobre el
panel puntuado por ese mismo artefacto: cuantiles del compuesto, neutro publicado, cobertura por feature,
alcance de las reglas (inactividad, liquidez, recorte), bandas, sesgos (ERP, tamaño, empresas nuevas),
sesgo bruta→suavizada de las probabilidades y un ejemplo trabajado de `explain()`.

    cd research && uv run python ../.devin/workflows/autoresearch/documento_medidas.py [--company COMP_xxxx --month 2026-06]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import roc_auc_score

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
sys.path.insert(0, str(RES / "src"))
from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402
from xray import SPEC, BANDS, LIQ_RULE_MONTHS, LIQ_RULE_CAP, explain, band_of  # noqa: E402


def auc(y, s):
    m = pd.notna(y) & pd.notna(s)
    y, s = np.asarray(y)[m], np.asarray(s)[m]
    return round(float(roc_auc_score(y, s)), 3) if len(np.unique(y)) > 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", default=None)
    ap.add_argument("--month", default=None)
    args = ap.parse_args()
    sc = joblib.load(RES / "artifacts" / "xray.joblib")["scorer"]
    panel = add_events(add_features(pl.read_parquet(RES / "data" / "panel.parquet"))).to_pandas()
    s = sc.score_panel(panel)
    p = panel.sort_values(["company_id", "month"]).reset_index(drop=True)
    assert (s[["company_id", "month"]].values == p[["company_id", "month"]].values).all()
    d = pd.concat([p, s.drop(columns=["company_id", "group_id", "month"])], axis=1)
    d["band"] = d.score.map(band_of)
    a, b = sc.scale_
    W = sc.weights_
    out: dict = {"n_filas": len(d), "n_empresas": d.company_id.nunique(), "meses": [str(d.month.min())[:7], str(d.month.max())[:7]]}

    # --- referencias y OOD
    out["ref_size"] = {f: int(len(v)) for f, v in sc.ref_.items()}
    out["bounds"] = {f: [round(float(lo), 3), round(float(hi), 3)] for f, (lo, hi) in sc.bounds_.items()}

    # --- pesos por evento reconstruidos
    cal = sc.calibration_
    rec = {}
    for f in sc.features_:
        parts = {ev: info["coef"][f] / sum(info["coef"].values()) for ev, info in cal.items()}
        rec[f] = {**{k: round(v, 3) for k, v in parts.items()}, "peso": round(float(W[f]), 4),
                  "media": round(float(np.mean(list(parts.values()))), 4)}
    out["pesos_por_evento"] = rec
    out["suma_coef_por_evento"] = {ev: round(sum(info["coef"].values()), 3) for ev, info in cal.items()}
    out["peso_por_pilar"] = {pil: round(sum(W[f] for f in sc.features_ if SPEC[f][0] == pil), 3) for pil in ["liquidez", "rentabilidad", "solvencia", "disciplina", "estabilidad"]}

    # --- compuesto y escala
    comp = sc._composite(p)
    act = pd.to_numeric(p["months_since_last_tx"], errors="coerce").fillna(0).to_numpy() == 0
    out["compuesto_cuantiles_todas"] = [round(float(x), 2) for x in np.percentile(comp, [5, 25, 50, 75, 95])]
    out["compuesto_cuantiles_activas"] = [round(float(x), 2) for x in np.percentile(comp[act], [5, 25, 50, 75, 95])]
    out["escala"] = {"a": round(float(a), 4), "b": round(float(b), 6), "P5_implicito": round((15 - a) / b, 2), "P95_implicito": round((85 - a) / b, 2),
                     "neutro_publicado": round(float(a + 50 * b), 2), "compuesto_para_35": round((35 - a) / b, 2), "compuesto_para_65": round((65 - a) / b, 2),
                     "compuesto_para_0": round(-a / b, 2), "compuesto_para_100": round((100 - a) / b, 2)}
    out["recorrido_max_por_feature"] = {f: round(100 * b * W[f], 1) for f in sc.features_}
    out["contrib_sin_dato"] = {f: round((a + 50 * b) * W[f], 2) for f in sc.features_}

    # --- cobertura
    feats = sc.features_
    out["sin_dato_pct"] = {f: round(100 * float(p[f].isna().mean()), 1) for f in feats}
    out["coverage_media"] = round(float(d.coverage.mean()), 3)
    out["coverage_mediana"] = round(float(d.coverage.median()), 3)
    erp_feats = ["ap_late_share", "ar_late_share", "ap_overdue_ratio", "ar_overdue_90_ratio", "hhi_ar_6m", "cust_trend", "lost_share"]
    out["peso_features_erp"] = round(sum(W[f] for f in erp_feats), 3)
    out["cobertura_max_sin_erp"] = round(1 - sum(W[f] for f in erp_feats), 3)
    out["ood_share_gt0_pct"] = round(100 * float((d.ood_share > 0).mean()), 1)
    out["confidence_mediana"] = round(float(d.confidence.median()), 3)

    # --- reglas
    out["recorte_0_100_filas"] = int((d.c_limite_0_100.abs() > 1e-9).sum())
    dorm = pd.to_numeric(d.months_since_last_tx, errors="coerce").fillna(0) > 0
    out["inactivas"] = {"filas": int(dorm.sum()), "empresas": int(d[dorm].company_id.nunique()),
                        "capadas": int((d.c_regla_inactividad < -1e-9).sum()),
                        "primer_mes_inactivo_publican_gt30_pct": round(100 * float((d[d.months_since_last_tx == 1].score > 30).mean()), 1),
                        "primer_mes_inactivo_max": round(float(d[d.months_since_last_tx == 1].score.max()), 1),
                        "activas_con_arrastre_lt_-0.05": int(((~dorm) & (d.ec_regla_inactividad < -0.05)).sum())}
    short = pd.to_numeric(p.runway, errors="coerce") < np.log1p(LIQ_RULE_MONTHS)
    liq = d.ec_regla_liquidez < -1e-9
    out["regla_liquidez"] = {"umbral_runway": round(float(np.log1p(LIQ_RULE_MONTHS)), 4), "tope": LIQ_RULE_CAP,
                             "filas_con_menos_de_medio_mes": int(short.sum()), "filas_recortadas": int(liq.sum()), "empresas_recortadas": int(d[liq].company_id.nunique()),
                             "recorte_medio": round(float(d.loc[liq, "ec_regla_liquidez"].mean()), 2), "recorte_min": round(float(d.loc[liq, "ec_regla_liquidez"].min()), 2),
                             "sanas_con_menos_de_medio_mes": int((short & (d.band == "sano")).sum())}
    # ¿la regla la sortea la póliza? mc con póliza
    burn = np.maximum(p.out3 / 3, p.out12 / 12) + 1e-9
    avail = (p.lc_limit - p.lc_drawn).clip(lower=0).where(p.lc_limit > 0, 0).fillna(0)
    d["mc"] = (p.cash_end + avail) / burn
    out["sanas_con_mc_lt_0.25"] = int(((d.mc < 0.25) & (d.band == "sano")).sum())
    out["sanas_con_mc_lt_0.5"] = int(((d.mc < 0.5) & (d.band == "sano")).sum())

    # --- exactitud aditiva
    ecs = [c for c in d.columns if c.startswith("ec_")]
    out["max_abs_score_menos_suma_ec"] = float((d.score - d[ecs].sum(axis=1)).abs().max())

    # --- suavizado
    g = d.groupby("company_id")
    dlt = (d.score - g.score.shift(1)).dropna()
    out["delta_mensual_abs_medio"] = round(float(dlt.abs().mean()), 2)
    out["delta_mensual_abs_p95"] = round(float(dlt.abs().quantile(0.95)), 2)
    out["abs_score_menos_raw_medio"] = round(float((d.score - d.score_raw).abs().mean()), 2)
    out["spearman_score_raw"] = round(float(d[["score", "score_raw"]].corr("spearman").iloc[0, 1]), 3)

    # --- bandas
    last = d[d.month == d.month.max()]
    out["ultimo_mes"] = {"mes": str(d.month.max())[:7], "n": len(last), "bandas_pct": {k: round(100 * v, 1) for k, v in last.band.value_counts(normalize=True).items()},
                         "cuantiles_nota": [round(float(x), 1) for x in last.score.quantile([0.05, 0.25, 0.5, 0.75, 0.95])]}
    for m in ["2026-06", "2026-07"]:
        mm = d[d.month == pd.Timestamp(m + "-01")]
        out["ultimo_mes"][f"riesgo_pct_{m}"] = round(100 * float((mm.band == "riesgo").mean()), 1)
    out["bandas_pct_panel"] = {k: round(100 * v, 1) for k, v in d.band.value_counts(normalize=True).items()}
    out["tension_por_banda"] = {k: round(float(v), 3) for k, v in d.groupby("band").tension_6m.mean().items()}
    out["tension_np_por_banda"] = {k: round(float(v), 3) for k, v in d.groupby("band").tension_np_raw_6m.mean().items()}
    out["runway_mediana_por_banda"] = {k: round(float(v), 3) for k, v in d.groupby("band").runway.median().items()}
    riesgo = d.band == "riesgo"
    out["riesgo_y_tension"] = {"riesgo_con_tension": round(float(d.loc[riesgo, "tension_6m"].mean()), 3), "tension_en_riesgo": round(float(riesgo[d.tension_6m == 1].mean()), 3)}
    neg = p.cash_end < 0
    out["caja_rota"] = {"filas": int(neg.sum()), "empresas": int(d[neg].company_id.nunique()), "bandas_pct": {k: round(100 * v, 1) for k, v in d[neg].band.value_counts(normalize=True).items()},
                        "nota_mediana": round(float(d[neg].score.median()), 1), "prob_tension_mediana": round(float(d[neg].prob_tension_6m.median()), 3), "tension_real": round(float(d.loc[neg, "tension_6m"].mean()), 3)}
    # racha ≥3 en negativo
    racha = neg.groupby(d.company_id).apply(lambda x: x.groupby((~x).cumsum()).cumsum()).reset_index(level=0, drop=True) if False else None
    r = neg.astype(int).groupby(d.company_id).transform(lambda x: x.groupby((x == 0).cumsum()).cumsum())
    r3 = r >= 3
    out["caja_rota_racha3"] = {"filas": int(r3.sum()), "empresas": int(d[r3].company_id.nunique()), "bandas_pct": {k: round(100 * v, 1) for k, v in d[r3].band.value_counts(normalize=True).items()},
                               "nota_mediana": round(float(d[r3].score.median()), 1), "tension_real": round(float(d.loc[r3, "tension_6m"].mean()), 3), "prob_tension_mediana": round(float(d[r3].prob_tension_6m.median()), 3)}
    # parpadeo de banda
    prev_band = g.band.shift(1); next_band = g.band.shift(-1)
    chg = (d.band != prev_band) & prev_band.notna()
    out["cambios_banda"] = {"n": int(chg.sum()), "revierten_al_mes_pct": round(100 * float((next_band[chg] == prev_band[chg]).mean()), 1)}

    # --- probabilidades
    out["prob_tabla"] = {k: {str(sv): round(float(1 / (1 + np.exp(-(ia + ib * sv / 100)))), 3) for sv in (10, 35, 65, 90)} for k, (ia, ib, _) in sc.proba_.items()}
    out["prob_rango_panel"] = {c: [round(float(d[c].min()), 3), round(float(d[c].max()), 3)] for c in d.columns if c.startswith("prob_")}
    pr_raw = sc.event_proba(d.score_raw)["prob_tension_6m"].to_numpy()
    out["prob_tension_sesgo_bruta_suavizada"] = {"mae": round(float(np.abs(pr_raw - d.prob_tension_6m).mean()), 3), "p95": round(float(np.quantile(np.abs(pr_raw - d.prob_tension_6m), 0.95)), 3), "max": round(float(np.abs(pr_raw - d.prob_tension_6m).max()), 3)}
    # calibración por decil de tamaño
    lab = d.tension_6m.notna()
    dec = pd.qcut(d.loc[lab, "log_scale"], 10, labels=False, duplicates="drop")
    out["tension_obs_vs_pub_por_decil_tamano"] = {int(k): [round(float(v.tension_6m.mean()), 3), round(float(v.prob_tension_6m.mean()), 3), int(len(v))] for k, v in d[lab].groupby(dec)}
    # deciles de la propia probabilidad
    decp = pd.qcut(d.loc[lab, "prob_tension_6m"], 10, labels=False, duplicates="drop")
    out["tension_obs_vs_pub_por_decil_prob"] = {int(k): [round(float(v.tension_6m.mean()), 3), round(float(v.prob_tension_6m.mean()), 3)] for k, v in d[lab].groupby(decp)}
    # sano con nota pero tensión real
    out["tension_por_banda_publicada_vs_observada"] = {k: [round(float(v.tension_6m.mean()), 3), round(float(v.prob_tension_6m.mean()), 3)] for k, v in d[lab].groupby("band")}

    # --- sesgos
    mature = d.month_idx >= 12
    out["sin_erp_vs_con_erp_maduras"] = {str(k): [round(float(v.score.median()), 1), round(float(v.tension_6m.mean()), 3), int(len(v))] for k, v in d[mature].groupby("has_erp")}
    out["nuevas_vs_maduras"] = {"idx<=2": [round(float(d[d.month_idx <= 2].score.median()), 1), round(float(d.loc[d.month_idx <= 2, "tension_6m"].mean()), 3), round(100 * float((d[d.month_idx <= 2].band == "sano").mean()), 1)],
                                "idx>=13": [round(float(d[d.month_idx >= 13].score.median()), 1), round(float(d.loc[d.month_idx >= 13, "tension_6m"].mean()), 3), round(100 * float((d[d.month_idx >= 13].band == "sano").mean()), 1)]}
    out["spearman_score_log_scale"] = round(float(d[["score", "log_scale"]].corr("spearman").iloc[0, 1]), 3)
    out["spearman_features_log_scale_activas"] = {f: round(float(d.loc[act, [f, "log_scale"]].corr("spearman").iloc[0, 1]), 2) for f in ["runway", "net_vol_6m", "transfer_dep", "payroll_cv", "activity_trend"]}
    out["confianza_lt_0.3"] = {"filas": int((d.confidence < 0.3).sum()), "sanas": int(((d.confidence < 0.3) & (d.band == "sano")).sum())}
    out["implausible"] = {"filas": int(d.dq_cash_implausible.fillna(False).sum()), "sano_pct": round(100 * float((d[d.dq_cash_implausible.fillna(False)].band == "sano").mean()), 1)} if "dq_cash_implausible" in d else None
    # póliza sin usar vs sin póliza
    haslc = p.lc_limit > 0
    out["ec_lc_util"] = {"con_poliza_sin_usar": round(float(d.loc[haslc & (p.lc_drawn <= 0), "ec_lc_util"].mean()), 2), "sin_poliza": round(float(d.loc[~haslc, "ec_lc_util"].mean()), 2), "poliza_agotada_gt0.9": round(float(d.loc[p.lc_util > 0.9, "ec_lc_util"].mean()), 2)}

    # --- baseline mc y AUC univariantes en el panel
    ev = {"tension_6m": -1, "tension_np_raw_6m": -1, "incumplimiento_6m": -1, "caida_6m": -1, "expansion_6m": +1, "entrada_estres_2m": -1}
    out["auc_panel"] = {e: {"score": auc(d[e], sg * d.score), "mc": auc(d[e], sg * d.mc), "runway": auc(d[e], sg * d.runway), "activity_trend": auc(d[e], sg * d.activity_trend), "log_scale": auc(d[e], sg * d.log_scale)} for e, sg in ev.items()}
    out["auc_crudo_direccion"] = {f"{f}~{e}": auc(d[e], d[f]) for f, e in [("net_vol_6m", "tension_6m"), ("lost_share", "tension_6m"), ("runway", "expansion_6m"), ("debt_burden", "incumplimiento_6m"), ("runway", "tension_entrada_6m"), ("runway", "entrada_estres_2m")]}
    # filas etiquetadas por corte (nivel)
    out["etiquetadas_por_corte"] = {c: {e: int(d[(d.month == pd.Timestamp(c)) & d[e].notna()].shape[0]) for e in ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]} for c in ["2025-11-01", "2026-02-01", "2026-05-01"]}
    out["ultimo_mes_con_etiqueta"] = {e: str(d.loc[d[e].notna(), "month"].max())[:7] for e in ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]}
    out["tasa_evento_panel"] = {e: [round(float(d[e].mean()), 4), int(d[e].notna().sum())] for e in ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m", "tension_np_raw_6m", "entrada_estres_2m", "impago_cuota_6m", "churn_6m"]}
    # explain: convergencia sin cambio de feature
    same = (p.refund_rate == g.refund_rate.shift(1))
    out["refund_igual_pero_dec_ge_0.05"] = {"n_igual": int(same.sum()), "mueven": int((same & ((d.ec_refund_rate - g.ec_refund_rate.shift(1)).abs() >= 0.05)).sum())}
    # sticky caducidad
    out["arrastre_caduca_ar_late"] = int((p.ar_late_share.isna() & g.ar_late_share.shift(1).notna()).sum())

    # --- ejemplo trabajado
    if args.company:
        cid, month = args.company, args.month
    else:  # una empresa con ERP, activa, sin OOD, con caída publicada notable en un mes reciente sin reglas
        cand = d[(d.has_erp == True) & (d.month >= pd.Timestamp("2026-03-01")) & (d.ood_share == 0) & (d.months_since_last_tx == 0) & (d.ec_regla_inactividad.abs() < 1e-9) & (d.ec_regla_liquidez.abs() < 1e-9) & (d.coverage > 0.9)].copy()  # noqa: E712
        cand["dlt"] = cand.score - cand.groupby("company_id").score.shift(1)
        cand = cand[(cand.dlt <= -10) & (cand.dlt >= -16)].sort_values("dlt")
        row = cand.iloc[len(cand) // 2]
        cid, month = row.company_id, str(row.month)[:7]
    ex = explain(s, panel, cid, month, scorer=sc)
    cur = d[(d.company_id == cid) & (d.month == pd.Timestamp(month + "-01"))].iloc[0]
    prev = d[(d.company_id == cid) & (d.month == pd.Timestamp(month + "-01") - pd.DateOffset(months=1))].iloc[0]
    detail = []
    for c in ex["contributions"]:
        f = c["feature"]
        detail.append({**c, "sub_prev": None if f not in feats else (None if pd.isna(prev[f"s_{f}"]) else round(float(prev[f"s_{f}"]), 1)),
                       "sub_now": None if f not in feats else (None if pd.isna(cur[f"s_{f}"]) else round(float(cur[f"s_{f}"]), 1)),
                       "c_now": round(float(cur[f"c_{f}"]), 2) if f"c_{f}" in cur else None,
                       "ec_prev": round(float(prev[f"ec_{f}"]), 2), "ec_now": round(float(cur[f"ec_{f}"]), 2)})
    out["ejemplo"] = {"company_id": cid, "group_id": cur.group_id, "month": month, "has_erp": bool(cur.has_erp), "coverage": round(float(cur.coverage), 3), "ood_share": float(cur.ood_share), "confidence": round(float(cur.confidence), 3),
                      "score_prev": round(float(prev.score), 2), "score_now": round(float(cur.score), 2), "raw_prev": round(float(prev.score_raw), 2), "raw_now": round(float(cur.score_raw), 2),
                      "band_prev": prev.band, "band_now": cur.band, "delta": ex["delta"], "summary_text": ex["summary_text"], "suma_contribs": round(sum(c["delta_points"] for c in ex["contributions"]), 2),
                      "probs_now": {c: round(float(cur[c]), 3) for c in d.columns if c.startswith("prob_")}, "mc_now": round(float(cur.mc), 2), "cash_end": float(cur.cash_end), "burn": float(burn[cur.name]),
                      "contribs": detail}
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
