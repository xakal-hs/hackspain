"""2x2: ¿las features y los pesos del catálogo a priori son mejores que los del backend?

    uv run python medir.py A        # 17 features + pesos calibrados   (el backend de hoy)
    uv run python medir.py B        # 17 features + pesos del doc
    uv run python medir.py C        # 42 features del doc + pesos del doc
    uv run python medir.py D        # 42 features del doc + pesos calibrados
    uv run python medir.py informe  # junta los cuatro y compara en pareado contra A

Dos cambios van mezclados en «poner los pesos del doc»: features nuevas y pesos fijos.
Con los cuatro brazos se separan, y así una caída se puede atribuir.

La medición no se toca: es `metrics.oof` (fuera de grupo Y fuera del futuro, un scorer por
fold y mes) + `metrics.auc_table` (bootstrap de grupos) + `metrics.compare` (bootstrap
PAREADO contra el brazo A, que es el se que decide).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import catalogo as cat  # noqa: E402
import metrics as met  # noqa: E402
import predict as prd  # noqa: E402
import preprocessing as pre  # noqa: E402

OUT = HERE / "salida"
ARMS = {"A": "17 features · pesos calibrados (backend)",
        "B": "17 features · pesos del doc",
        "C": "42 features del doc · pesos del doc",
        "D": "42 features del doc · pesos calibrados",
        "E": "17 features · mezcla 50/50 de calibrado y doc",
        "F": "17 + 7 features del doc que el brazo D calibró con peso · calibradas",
        "G": "17 + las 2 features del doc que pagan solas · calibradas",
        "H": "17 + payroll_continuity_6m (aísla la nómina)",
        "I": "17 + tax_miss (aísla el IVA, que además es primo del veto)"}
# La cara positiva se calibra aparte (README §4.4): estos dos brazos solo se comparan entre sí.
EXP_ARMS = {"Aexp": "17 features · nota de expansión",
            "Gexp": "17 + 2 features del doc · nota de expansión"}
BLEND = 0.5      # cuánto del doc entra en el brazo E
# Brazo F: lo que el 2x2 dice que hay que quedarse. Son las variables NUEVAS del catálogo a las
# que la logística del brazo D dio peso real (>=2 %), menos `impagos_ausentes`: esa es el veto
# metido en la nota, y el propio doc dice que un veto no debe sumar puntos (explicacion_pesos.md:383).
F_EXTRA = ["tax_miss", "payroll_continuity_6m", "payee_concentration", "lost_accel",
           "cash_end_eur", "burn_rate", "billing_to_cash"]
# Brazo G: de las siete de F, las dos que atacan el punto flojo declarado del backend
# (incumplimiento 0,588). Si el brazo F gana por ellas, G debe conservar la ganancia sin pagar
# el precio de las otras cinco.
G_EXTRA = ["tax_miss", "payroll_continuity_6m"]
# H e I parten G en dos. Son la respuesta a una objeción concreta: `tax_miss` es pariente del
# veto `veto_iva_ausente` (que es un subconjunto suyo: 176 filas de 3.267) y del propio evento
# `impago_iva_6m`, calculado con casi la misma fórmula. Si la ganancia de G vive en I, es en
# buena parte autocorrelación del mismo hecho; si vive en H, es una señal de verdad.
EXTRA = {"F": F_EXTRA, "G": G_EXTRA, "H": ["payroll_continuity_6m"], "I": ["tax_miss"]}
# La única métrica-resumen que se reporta: media del AUC del nivel frente a los cuatro eventos
# ancla. Se reporta, no decide: promediar esconde que un cambio mejore uno y estropee otro.
PM_EVENTS = pre.EVENTS


def _patch(arm: str):
    """Deja `predict` configurado para el brazo. Devuelve el panel ya construido."""
    if arm in ("A", "B", "E"):
        d = pre.build()
        prd.FEATURES, prd.SCORE_FEATURES, prd.PILLARS = pre.FEATURES, pre.SCORE_FEATURES, pre.PILLARS
        W = cat.doc_weights_17() if arm == "B" else None
        if arm == "E":
            # mezcla: los dos vectores normalizados a 1 antes de mezclar, si no la escala de
            # los coeficientes de la logística decidiría la mezcla por accidente.
            doc = cat.doc_weights_17()
            doc = {k: v / sum(doc.values()) for k, v in doc.items()}

            def _blend(S, Y, target, _o=_ORIG_FIT_WEIGHTS):
                w, diag = _o(S, Y, target)
                t = sum(w.values()) or 1.0
                return {f: (1 - BLEND) * w[f] / t + BLEND * doc.get(f, 0.0) for f in w}, diag

            prd._fit_weights = _blend
            prd.PRIOR_W = {f: pre.PRIOR_W.get(f, 1.0) for f in prd.SCORE_FEATURES}
            return d
    elif arm in EXTRA:
        extra = EXTRA[arm]
        d = cat.build()
        prd.FEATURES = {**pre.FEATURES, **{f: cat.CATALOG[f] for f in extra}}
        prd.SCORE_FEATURES = pre.SCORE_FEATURES + extra
        prd.PILLARS = pre.PILLARS + sorted({cat.CATALOG[f]["pilar"] for f in extra})
        W = None
    else:
        d = cat.build()
        prd.FEATURES, prd.SCORE_FEATURES = cat.CATALOG, list(cat.CATALOG)
        prd.PILLARS = cat.CATALOG_PILLARS
        W = cat.catalog_weights() if arm == "C" else None

    if W is None:                                     # pesos calibrados: el fit original
        prd._fit_weights = _ORIG_FIT_WEIGHTS
        prd.PRIOR_W = {f: pre.PRIOR_W.get(f, 1.0) for f in prd.SCORE_FEATURES}
    else:
        # pesos FIJOS del doc: se saltan la logística, pero todo lo demás (percentiles,
        # escala P5/P95, EWMA, probabilidades) sigue siendo idéntico entre brazos.
        prd.PRIOR_W = dict(W)
        prd._fit_weights = lambda S, Y, target: ({f: W.get(f, 0.0) for f in S.columns}, {})
    return d


_ORIG_FIT_WEIGHTS = prd._fit_weights


def run(arm: str) -> None:
    """`XG` -> brazo X calibrado contra la cara positiva (la nota de expansión, README §4.4).

    La nota adversa no vende expansión: si un brazo pierde expansión con pesos adversos, hay que
    ver qué hace con los suyos antes de contarlo como coste.
    """
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    target = "expansion" if arm.endswith("exp") else "adversa"
    d = _patch(arm.removesuffix("exp"))
    d["score_oof"] = met.oof(d, target=target)
    keep = ["company_id", "group_id", "month", "score_oof", "months_since_last_tx", "estres_mes",
            *pre.EVENTS, *[e for e in pre.JUDGES if e in d.columns]]
    d[keep].to_parquet(OUT / f"oof_{arm}.parquet")

    activo = d[d.months_since_last_tx == 0]
    tab = met.auc_table(activo)
    ant = met.anticipation(activo)
    # pesos con los que acaba el brazo, ajustados sobre todo el panel (para diagnosticar)
    sc = prd.fit(d, pre.labels(d))
    res = {"arm": arm, "desc": {**ARMS, **EXP_ARMS}[arm], "n_features": len(prd.SCORE_FEATURES),
           "minutos": round((time.time() - t0) / 60, 1),
           "pm": round(float(tab.loc[[e for e in PM_EVENTS if e in tab.index], "auc"].mean()), 4),
           "auc": tab.round(4).reset_index().to_dict("records"),
           "anticipacion": ant,
           "pesos": {k: round(v, 4) for k, v in sorted(sc.weights.items(), key=lambda kv: -kv[1])},
           "escala": [round(x, 3) for x in sc.scale],
           "cobertura_media": round(float(prd.contributions(sc, d)["coverage"].mean()), 4)}
    (OUT / f"metrics_{arm}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    print(f"[{arm}] PM={res['pm']:.4f} · {res['minutos']} min · cobertura={res['cobertura_media']:.3f}")
    print(met._fmt(tab))
    print("anticipación:", ant)


def informe() -> None:
    have = lambda a: (OUT / f"metrics_{a}.json").exists()                # noqa: E731
    res = {a: json.loads((OUT / f"metrics_{a}.json").read_text()) for a in ARMS if have(a)}
    oofs = {a: pd.read_parquet(OUT / f"oof_{a}.parquet") for a in res}
    base = oofs["A"]
    lines = ["== resumen ==",
             pd.DataFrame([{"brazo": a, "features": r["n_features"], "PM": r["pm"],
                            "cobertura": r["cobertura_media"],
                            **{k: v for k, v in r["anticipacion"].items()
                               if k in ("cobertura", "meses_mediana")}}
                           for a, r in res.items()]).to_string(index=False)]

    auc = pd.DataFrame({a: {r["evento"]: r["auc"] for r in v["auc"]} for a, v in res.items()})
    lines += ["", "== AUC por evento ==", auc.round(3).to_string()]

    for a in [x for x in res if x != "A"]:
        act = lambda df: df[df.months_since_last_tx == 0]            # noqa: E731
        cmp = met.compare(act(base), act(oofs[a]))
        cmp.round(4).reset_index().to_json(OUT / f"pareado_{a}.json", orient="records", indent=1)
        lines += ["", f"== pareado A vs {a} ({ARMS[a]}) ==", met._fmt(cmp)]

    if all(have(a) for a in EXP_ARMS):        # la cara positiva, medida con sus propios pesos
        ea, eg = (pd.read_parquet(OUT / f"oof_{a}.parquet") for a in EXP_ARMS)
        act = lambda df: df[df.months_since_last_tx == 0]                 # noqa: E731
        cmp = met.compare(act(ea), act(eg), events=["expansion_6m", "expansion_3m"])
        cmp.round(4).reset_index().to_json(OUT / "pareado_Gexp.json", orient="records", indent=1)
        lines += ["", "== pareado Aexp vs Gexp (nota de expansión, pesos propios) ==", met._fmt(cmp)]

    txt = "\n".join(lines)
    (OUT / "informe.txt").write_text(txt)
    print(txt)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "informe"
    informe() if arg == "informe" else run(arg)
