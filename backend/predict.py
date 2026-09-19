"""El modelo: features -> nota 0-100 explicable.

    d      = preprocessing.build()
    scorer = fit(d, preprocessing.labels(d))
    scored = score_panel(scorer, d)          # una fila por empresa-mes, con nota y explicación

Es un scorecard aditivo, no una caja negra. Cuatro pasos, en este orden:

  1. REFERENCIA   cada feature -> su percentil dentro del histórico de train (congelado).
                  Orientado: después de este paso, en las 17 «más alto = más sano».
  2. PESOS        una logística con w >= 0 por evento; los pesos normalizados se promedian.
                  El signo lo fija FEATURES, no los datos: nunca se aprende «más mora = mejor».
  3. ESCALA       recta que lleva P5 -> 15 y P95 -> 85. Lineal, así la explicación sigue sumando.
  4. EWMA         alpha=0,5 sobre las CONTRIBUCIONES, no sobre la nota: un bache entra a medias,
                  un deterioro de tres meses entra entero, y la descomposición se conserva.

Invariante que sostiene todo el producto:  nota == suma de las contribuciones ec_*.
Las reglas de negocio no sobrescriben la nota; añaden su propio término (ec_regla_*).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from preprocessing import CONTEXT, FEATURES, OOD_CONTEXT, PILLARS, POSITIVE_PREFIX, PRIOR_W, SCORE_FEATURES

ALPHA = 0.5                        # suavizado EWMA de la nota publicada
BANDS = [(0, 35, "riesgo"), (35, 65, "vigilar"), (65, 101, "sano")]
DORMANT_CAP = 30.0                 # sin movimientos en el mes no puede ser «sano»
LIQ_RULE_MONTHS, LIQ_RULE_CAP = 0.5, 64.9   # menos de medio mes de caja propia tampoco
NEUTRAL = 50.0                     # sub-nota de una feature sin dato
MIN_ROWS_PROBA, MIN_AUC_PROBA = 200, 0.60   # no se publica una prob_* que ordena mal
RULE_LABELS = {"regla_inactividad": "Regla: sin movimientos en el mes",
               "regla_liquidez": "Regla: menos de medio mes de caja no es sano",
               "limite_0_100": "Límite de escala 0-100"}


@dataclass
class Scorer:
    """Todo lo aprendido. Es pequeño a propósito: 17 arrays + 17 pesos + 2 números + 2 por evento."""
    features: list[str]
    ref: dict[str, np.ndarray]              # valores de train ordenados, por feature
    bounds: dict[str, tuple[float, float]]  # rango 0,5-99,5 % de train, para marcar OOD
    weights: dict[str, float]               # suman 1
    scale: tuple[float, float] = (0.0, 1.0)  # (a, b): nota = a + b * compuesto
    proba: dict[str, tuple[float, float, float]] = field(default_factory=dict)  # evento -> (a, b, tasa base)
    calibration: dict[str, dict] = field(default_factory=dict)                  # diagnóstico del ajuste
    target: str = "adversa"
    alpha: float = ALPHA


# ---------------------------------------------------------------- 1 · referencia
def _reference(X: pd.DataFrame) -> tuple[dict, dict]:
    ref, bounds = {}, {}
    for f, spec in FEATURES.items():
        v = pd.to_numeric(X.get(f), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna().to_numpy(float)
        if not len(v):
            continue
        # si el cero es lo mejor, los ceros NO entran en la referencia: se resuelven aparte con
        # sub-nota 100 y los positivos se ordenan entre ellos (si no, el primer euro de mora
        # te mandaría al percentil 60 de golpe, porque el 60 % de las filas es cero).
        ref[f] = np.sort(v[v > 0] if spec["zero_best"] and (v > 0).any() else v)
        bounds[f] = (float(np.quantile(v, 0.005)), float(np.quantile(v, 0.995)))
    for c in OOD_CONTEXT:
        v = pd.to_numeric(X.get(c), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(v):
            bounds[c] = (float(v.quantile(0.005)), float(v.quantile(0.995)))
    return ref, bounds


def subscores(sc: Scorer, X: pd.DataFrame) -> pd.DataFrame:
    """Features crudas -> sub-notas 0-100, todas orientadas a «más alto = más sano».

    NaN se propaga: «no tengo el dato» no es «vale cero». Quien decide qué hacer con
    el hueco es contributions(), no este paso.
    """
    out = {}
    for f in sc.features:
        spec, ref = FEATURES[f], sc.ref[f]
        x = pd.to_numeric(X.get(f), errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(float)
        xx = np.nan_to_num(x)
        # percentil medio entre los empates: los valores redondos y muy repetidos
        # (lc_util = 0,30) no se van todos al borde inferior de su bloque
        pct = (np.searchsorted(ref, xx, "left") + np.searchsorted(ref, xx, "right")) / 2 / len(ref) * 100
        s = pct if spec["dir"] > 0 else 100 - pct
        if spec["zero_best"]:
            s = np.where(xx <= 0, 100.0, s)
        out[f] = np.where(np.isnan(x), np.nan, s)
    return pd.DataFrame(out, index=X.index)


# -------------------------------------------------------------------- 2 · pesos
def _fit_logistic(Z: np.ndarray, y: np.ndarray, sign: float = 1.0, l2: float = 1e-3,
                  nonneg: bool = False) -> tuple[np.ndarray, float, bool]:
    """Logística  P(y=1) = sigma(b + sign * Z@w)  por máxima verosimilitud.

    `nonneg` acota w >= 0, que es justo lo que sklearn no sabe hacer y la razón de
    escribir la verosimilitud a mano. Se usa dos veces: con cotas para los pesos del
    score, sin cotas para las probabilidades publicadas.
    """
    n = Z.shape[1]
    p0 = np.r_[np.log(y.mean() / (1 - y.mean())), np.full(n, 0.1)]

    def nll(p):
        z = p[0] + sign * (Z @ p[1:])
        return -np.mean(y * z - np.logaddexp(0, z)) + l2 * (p[1:] ** 2).sum()

    res = minimize(nll, p0, method="L-BFGS-B",
                   bounds=[(None, None)] + [((0, None) if nonneg else (None, None))] * n)
    return res.x[1:], float(res.x[0]), bool(res.success)


def _fit_weights(S: pd.DataFrame, Y: pd.DataFrame, target: str) -> tuple[dict, dict]:
    """Un ajuste por evento; los pesos normalizados se promedian.

    Dos notas, no una: promediar los pesos de la tensión con los de la expansión dejaba
    la caja sin peso (runway 3,4 en tensión, 0,0 en expansión). `target` elige qué cara
    se calibra; las features y la escala son las mismas en las dos.
    """
    pos = [c for c in Y.columns if c.startswith(POSITIVE_PREFIX)]
    cols = {"adversa": [c for c in Y.columns if c not in pos], "expansion": pos}.get(target, list(Y.columns))
    cols = cols or list(Y.columns)

    normed, diag = [], {}
    for col in cols:
        m = Y[col].notna().to_numpy()
        y = Y[col].to_numpy(float)[m]
        if m.sum() < MIN_ROWS_PROBA or not 0 < y.sum() < len(y):
            continue
        Z = S[m].fillna(NEUTRAL).to_numpy() / 100
        Z = Z - Z.mean(0)                       # centrar solo mueve el intercepto; ayuda a converger
        sign = +1.0 if col.startswith(POSITIVE_PREFIX) else -1.0
        w, b, ok = _fit_logistic(Z, y, sign=sign, nonneg=True)
        diag[col] = {"n": int(m.sum()), "event_rate": float(y.mean()), "converged": ok,
                     "coef": dict(zip(S.columns, w.round(4)))}
        if w.sum() > 0:
            # normalizar ANTES de promediar: un evento con más positivos tiene coeficientes
            # más grandes y si no, se comería a los demás. Así cada deterioro cuenta igual.
            normed.append(w / w.sum())
    if not normed:
        return {f: PRIOR_W[f] for f in S.columns}, diag
    return dict(zip(S.columns, np.mean(normed, axis=0))), diag


# ---------------------------------------------------------------------- 3 · fit
def fit(X: pd.DataFrame, y: pd.DataFrame | pd.Series | None = None, target: str = "adversa",
        alpha: float = ALPHA) -> Scorer:
    """Ajusta el scorer. `y` son las etiquetas ya enmascaradas (preprocessing.labels).

    Las sub-notas se calculan UNA vez y se reutilizan en los tres pasos que las necesitan
    (pesos, escala, probabilidades).
    """
    ref, bounds = _reference(X)
    feats = [f for f in SCORE_FEATURES if f in ref]
    sc = Scorer(features=feats, ref=ref, bounds=bounds, weights={}, target=target, alpha=alpha)

    S = subscores(sc, X)                                        # <- una sola vez

    if y is None:
        w = {f: PRIOR_W[f] for f in feats}
    else:
        Y = (y.to_frame() if isinstance(y, pd.Series) else pd.DataFrame(y)).set_axis(X.index)
        if len(Y) != len(X):
            raise ValueError("y debe tener las mismas filas que X")
        w, sc.calibration = _fit_weights(S, Y, target)
    total = sum(w.values())
    sc.weights = {f: v / total for f, v in w.items()}

    # escala publicada: el compuesto crudo se apelotona en el centro (media de 17 percentiles),
    # esta recta lo estira. Solo cuentan las empresas activas, para que las dormidas no arrastren el P5.
    comp = (S.fillna(NEUTRAL).to_numpy() @ np.array([sc.weights[f] for f in feats]))
    active = (pd.to_numeric(X.get("months_since_last_tx"), errors="coerce").fillna(0).to_numpy() == 0
              if "months_since_last_tx" in X else np.ones(len(X), bool))
    p5, p95 = np.percentile(comp[active], [5, 95])
    b = 70.0 / max(p95 - p5, 1e-6)
    sc.scale = (15.0 - b * p5, b)

    # probabilidades: se calibran sobre la nota QUE SE PUBLICA (tras EWMA y reglas), no sobre
    # el compuesto crudo. Si no, la ficha diría una probabilidad de un número que no enseña.
    if y is not None:
        Y = (y.to_frame() if isinstance(y, pd.Series) else pd.DataFrame(y)).set_axis(X.index)
        published = score_panel(sc, X).set_index(["company_id", "month"])["score"]
        key = pd.MultiIndex.from_arrays([X["company_id"], X["month"]])
        sc.proba = _fit_probabilities(published.reindex(key).to_numpy(), Y)
    return sc


def _fit_probabilities(score: np.ndarray, Y: pd.DataFrame) -> dict:
    """Nota -> probabilidad de cada evento. Una logística de UNA variable: la nota.

    No usa las features: dos empresas con la misma nota tienen la misma probabilidad,
    siempre. Y solo se publica si la nota ordena ese evento (AUC >= 0,60): una
    probabilidad bien calibrada en media pero que ordena al revés es peor que ninguna.
    """
    labels = {c: Y[c] for c in Y.columns}
    adverse = [c for c in Y.columns if not c.startswith(POSITIVE_PREFIX)]
    if len(adverse) > 1:
        A = Y[adverse]
        labels["adverso"] = A.max(axis=1).where(A.notna().any(axis=1))   # «algún evento adverso»

    out = {}
    for name, lab in labels.items():
        m = lab.notna().to_numpy() & np.isfinite(score)
        y = lab.to_numpy(float)[m]
        if m.sum() < MIN_ROWS_PROBA or not 0 < y.sum() < len(y):
            continue
        s = score[m] / 100
        sign = +1.0 if name.startswith(POSITIVE_PREFIX) else -1.0
        order = np.mean(s[y == 1] < s[y == 0][:, None]) + 0.5 * np.mean(s[y == 1] == s[y == 0][:, None])
        auc = order if sign < 0 else 1 - order
        if auc < MIN_AUC_PROBA:
            continue
        w, b, _ = _fit_logistic(s.reshape(-1, 1), y, l2=0.0)
        out[name] = (b, float(w[0]), float(y.mean()))
    return out


def event_proba(sc: Scorer, score) -> pd.DataFrame:
    s = np.asarray(score, float) / 100
    return pd.DataFrame({f"prob_{k}": expit(a + b * s) for k, (a, b, _) in sc.proba.items()})


# ------------------------------------------------------------------ 4 · predict
def contributions(sc: Scorer, X: pd.DataFrame) -> pd.DataFrame:
    """Nota de un mes, ya descompuesta. Devuelve s_* (sub-notas), c_* (puntos), cobertura y OOD.

    La línea que sostiene el producto es  C = b*S*W + a*W:  como los pesos suman 1,
    el término independiente se reparte entre features y  sum(C) == nota, al céntimo.
    No es una aproximación tipo SHAP, es una identidad.
    """
    W = np.array([sc.weights[f] for f in sc.features])
    S = subscores(sc, X)
    a, b = sc.scale

    out = pd.DataFrame(index=X.index)
    out["coverage"] = (S.notna().to_numpy() * W).sum(1)      # fracción del peso total con dato
    # el hueco va al centro y NO se renormaliza: si renormalizáramos, una feature que
    # aparece o desaparece movería la nota sin que la empresa se haya movido.
    C = b * S.fillna(NEUTRAL).to_numpy() * W + a * W
    for i, f in enumerate(sc.features):
        out[f"s_{f}"], out[f"c_{f}"] = S[f], C[:, i]

    lin = C.sum(1)
    out["c_limite_0_100"] = np.clip(lin, 0, 100) - lin       # el recorte también es una contribución
    raw = np.clip(lin, 0, 100)
    dormant = pd.to_numeric(X.get("months_since_last_tx"), errors="coerce").fillna(0).to_numpy() > 0
    capped = np.where(dormant, np.minimum(raw, DORMANT_CAP), raw)
    out["c_regla_inactividad"] = capped - raw
    out["score_raw"] = capped

    for p in PILLARS:  # lectura por pilar: aquí SÍ se renormaliza, porque es un indicador, no la nota
        fs = [f for f in sc.features if FEATURES[f]["pilar"] == p]
        num = sum(S[f].fillna(0) * sc.weights[f] * S[f].notna() for f in fs)
        den = sum(sc.weights[f] * S[f].notna() for f in fs)
        out[f"p_{p}"] = num / den.replace(0, np.nan)

    # OOD sobre el valor CRUDO: no cambia la nota, baja la confianza. Es la señal de
    # «esta empresa no se parece a nada de lo que vi al entrenar».
    flags = []
    for f, (lo, hi) in sc.bounds.items():
        v = pd.to_numeric(X.get(f), errors="coerce")
        flags.append(((v < lo) | (v > hi) | np.isinf(v)).astype(float).where(v.notna()).rename(f))
    F = pd.concat(flags, axis=1)
    out["ood_share"] = F.mean(1).fillna(0)
    names = np.array(F.columns)
    out["ood_features"] = [",".join(names[r]) for r in F.fillna(0).to_numpy().astype(bool)]
    return out


def score_panel(sc: Scorer, d: pd.DataFrame) -> pd.DataFrame:
    """Panel completo -> nota publicada por empresa-mes, con su explicación y su confianza."""
    p = d.reset_index(drop=True)
    s = pd.concat([p[["company_id", "group_id", "month"]], contributions(sc, p)], axis=1)
    s["_runway"] = pd.to_numeric(p.get("runway"), errors="coerce")
    s = s.sort_values(["company_id", "month"]).reset_index(drop=True)

    # EWMA sobre las CONTRIBUCIONES. Es lineal, así que suavizar las piezas o la nota da lo
    # mismo — pero suavizando las piezas te quedas con la descomposición del número publicado.
    ccols = [c for c in s.columns if c.startswith("c_")]
    e = s.groupby("company_id")[ccols].transform(lambda x: x.ewm(alpha=sc.alpha, adjust=False).mean())
    for c in ccols:
        s["e" + c] = e[c]
    lin = e.sum(1)

    # regla del prestamista: con menos de medio mes de caja propia la nota no puede ser «sano».
    # min(0, cap - lin) => nunca sube la nota, solo la topa, y queda registrada como contribución.
    short = (s.pop("_runway") < np.log1p(LIQ_RULE_MONTHS)).to_numpy()
    s["ec_regla_liquidez"] = np.where(short, np.minimum(0.0, LIQ_RULE_CAP - lin), 0.0)
    s["score"] = lin + s["ec_regla_liquidez"]
    s["band"] = [band_of(v) for v in s["score"]]

    # tres formas de no saber, multiplicadas: me faltan features x tus valores son raros x te conozco poco
    n = s.groupby("company_id").cumcount() + 1
    s["confidence"] = (s["coverage"] * (1 - s["ood_share"]) * np.minimum(1, n / 6)).clip(0, 1)
    if sc.proba:
        s = pd.concat([s, event_proba(sc, s["score"]).set_axis(s.index)], axis=1)
    return s


def band_of(score: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= score < hi:
            return name
    return "sano"


# --------------------------------------------------------------- explicación
def explain(scored: pd.DataFrame, feats: pd.DataFrame | None, company_id: str, month=None) -> dict:
    """Por qué se movió la nota: el delta del mes, repartido exactamente entre features y reglas."""
    s = scored[scored.company_id == company_id].sort_values("month").reset_index(drop=True)
    if s.empty:
        raise KeyError(company_id)
    i = len(s) - 1 if month is None else int(np.flatnonzero(s.month == pd.Timestamp(month))[0])
    if i == 0:
        return {"month": f"{s.month[0]:%Y-%m}", "prev_month": None, "delta": 0.0, "contributions": [],
                "summary_text": "Primer mes con datos: sin referencia anterior."}

    cur, prev = s.iloc[i], s.iloc[i - 1]
    fr = feats[feats.company_id == company_id].sort_values("month").reset_index(drop=True) if feats is not None else None
    rows = []
    for c in [c for c in s.columns if c.startswith("ec_")]:
        key = c[3:]
        spec = FEATURES.get(key)
        vp = vn = None
        if fr is not None and key in fr.columns:
            vp, vn = fr[key].iloc[i - 1], fr[key].iloc[i]
            vp, vn = (None if pd.isna(vp) else float(vp)), (None if pd.isna(vn) else float(vn))
        label = spec["label"] if spec else RULE_LABELS.get(key, key)
        dp = float(cur[c] - prev[c])
        rows.append({"feature": key, "label": label, "pillar": spec["pilar"] if spec else "regla",
                     "delta_points": round(dp, 2), "value_prev": vp, "value_now": vn,
                     "text": f"{label}: {human(key, vp)} → {human(key, vn)} ({_es(dp, 1, True)} pts)"})

    rows = sorted([r for r in rows if abs(r["delta_points"]) >= 0.05], key=lambda r: -abs(r["delta_points"]))
    delta = float(cur["score"] - prev["score"])
    top = [r for r in rows if np.sign(r["delta_points"]) == np.sign(delta)][:2]
    why = " y ".join(r["label"].lower() for r in top) if top else "cambios menores"
    return {"month": f"{cur.month:%Y-%m}", "prev_month": f"{prev.month:%Y-%m}", "delta": round(delta, 2),
            "contributions": rows,
            "summary_text": f"El score {'sube' if delta > 0 else 'baja'} {_es(abs(delta))} puntos "
                            f"({_es(prev['score'])} → {_es(cur['score'])}), sobre todo por {why}."}


PCT = {"lc_util", "ap_late_share", "ar_late_share", "refund_rate", "transfer_dep", "lost_share",
       "debt_burden", "payroll_cv", "oper_persistence_6m"}
LOG_PCT = {"oper_growth_12m", "growth_vs_12m", "activity_trend", "cust_trend"}


def human(f: str, v) -> str:
    """Valor de una feature en unidades que entiende quien presta el dinero."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "sin dato"
    if f == "runway":                       # log(1 + caja/gasto) con signo -> meses
        m = np.sign(v) * np.expm1(abs(v))
        return f"{_es(m, 1)} meses" if abs(m) < 100 else ">100 meses"
    if f in PCT:
        return f"{_es(100 * v, 0)} %"
    if f in LOG_PCT:
        return f"{_es(100 * (np.exp(v) - 1), 0, True)} %"
    if f == "ap_overdue_ratio":
        return f"{_es(v, 1)} meses de pagos" if v < 100 else ">100 meses"
    if f == "ar_overdue_90_ratio":
        return f"{_es(v, 1)} meses de cobros" if v < 100 else ">100 meses"
    if f == "net_vol_6m":
        return f"{_es(v, 1)}× gasto mensual"
    return _es(v, 2)


def _es(v: float, nd: int = 1, sign: bool = False) -> str:
    """Número en formato es-ES (coma decimal)."""
    return (f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}").replace(".", ",")


# ------------------------------------------------------------------ artefacto
def save(sc: Scorer, path: Path | str) -> None:
    import joblib
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(sc, path)


def load(path: Path | str) -> Scorer:
    import joblib
    return joblib.load(path)


if __name__ == "__main__":
    import preprocessing as pre

    d = pre.build()
    sc = fit(d, pre.labels(d))
    s = score_panel(sc, d)
    print("pesos:", {k: round(v, 3) for k, v in sorted(sc.weights.items(), key=lambda kv: -kv[1])})
    print(f"escala: a={sc.scale[0]:.2f} b={sc.scale[1]:.2f} · probs: {list(sc.proba)}")
    print(s.groupby("band").size().to_string())
    print(explain(s, d, s.company_id.iloc[0])["summary_text"])
