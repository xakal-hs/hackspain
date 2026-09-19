"""API estilo sklearn del sistema X-Ray (v4). Decisiones Dxx en research/DECISIONS.md.

- HealthScorer.fit(X, y=None) / transform(X) / score_panel(panel)
    Score 0-100 = media ponderada de sub-scores por feature (percentiles orientados
    respecto a train, congelados). Si se pasa `y` (evento adverso observable a 6 meses),
    los pesos se calibran con una logística con signo restringido (D12). Explicación
    exacta: score = suma de contribuciones por feature, también tras el suavizado EWMA (D14).
- TrajectoryForecaster.fit(df) / predict(df)
    mlforecast + LightGBM cuantílico (q10/q50/q90), estrategia directa h=1..H, con
    exógenas específicas por horizonte retardadas h meses (conocidas en el origen, D13).
- alerts(...) y apply_scenario(...) para el monitor y el simulador.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy.optimize import minimize
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted
from sklearn.linear_model import LogisticRegression
from mlforecast import MLForecast
from mlforecast.lag_transforms import RollingMean, RollingStd, ExpandingMean, ExponentiallyWeightedMean

# feature -> pilar, dirección económica (+1 más es mejor), si el cero es "lo mejor" (two-part), etiqueta, descripción
SPEC = {
    "runway": ("liquidez", +1, False, "Meses de caja", "log(1+caja/gasto mensual), con signo; gasto = máx(media 3m, media 12m)"),
    "lc_util": ("liquidez", -1, True, "Uso de líneas de crédito", "Dispuesto / límite de las pólizas de crédito"),
    "growth_vs_12m": ("rentabilidad", +1, False, "Tendencia de cobros", "log(entradas medias 3m / entradas medias 12m)"),
    "debt_burden": ("solvencia", -1, True, "Carga de deuda", "Cuotas + intereses / entradas (3m)"),
    "payroll_cv": ("solvencia", -1, False, "Regularidad de nóminas", "Semidesviación a la baja de las nóminas / media (6m): nóminas que faltan o bajan; sin nóminas = no aplica"),
    "ap_late_share": ("disciplina", -1, True, "Pagos tardíos a proveedores", "% facturas recibidas vencidas >15 días sin pagar o pagadas tarde (3m)"),
    "ar_late_share": ("disciplina", -1, True, "Cobros tardíos de clientes", "% facturas emitidas cobradas >15 días tarde o impagadas (3m)"),
    "ap_overdue_ratio": ("disciplina", -1, True, "Deuda vencida con proveedores", "Saldo AP vencido / salidas mensuales"),
    "ar_overdue_90_ratio": ("disciplina", -1, True, "Clientes morosos >60 días", "Saldo AR vencido >60 días / entradas mensuales"),
    "refund_rate": ("disciplina", -1, True, "Devoluciones de cobros", "Devoluciones / cobros operativos (3m)"),
    "activity_trend": ("estabilidad", +1, False, "Tendencia de actividad", "log(movimientos 3m / movimientos medios 12m)"),
    "transfer_dep": ("estabilidad", -1, True, "Dependencia de transferencias", "Entradas por transferencia no operativa / entradas (3m)"),
    "hhi_ar_6m": ("estabilidad", -1, False, "Concentración de clientes", "HHI de facturación a clientes (6m)"),
    "net_vol_6m": ("estabilidad", -1, False, "Volatilidad a la baja", "Semidesviación de los meses con flujo neto negativo / gasto mensual (6m)"),
    "cust_trend": ("estabilidad", +1, False, "Amplitud de clientes", "log(clientes facturados 3m / clientes 12m)"),
    "lost_share": ("estabilidad", -1, True, "Facturación de clientes perdidos", "% de la facturación de hace 3-12 meses de clientes sin facturas en los últimos 3"),
    "oper_persistence_6m": ("estabilidad", +1, False, "Persistencia de cobros", "Meses de los últimos 6 con cobros operativos ≥ 50 % de su mediana anual"),
}
PILLARS = ["liquidez", "rentabilidad", "solvencia", "disciplina", "estabilidad"]
PRIOR_W = {"runway": 3, "lc_util": 1, "growth_vs_12m": 1.5, "debt_burden": 1, "payroll_cv": 0.5,
           "ap_late_share": 1.5, "ar_late_share": 1, "ap_overdue_ratio": 1, "ar_overdue_90_ratio": 0.5, "refund_rate": 0.5,
           "activity_trend": 1.5, "transfer_dep": 0.5, "hhi_ar_6m": 0.5, "net_vol_6m": 0.5, "cust_trend": 1.0, "lost_share": 1.0, "oper_persistence_6m": 1.0}
CONTEXT = ["log_scale", "fx_share", "activity_log"]
BANDS = [(0, 35, "riesgo"), (35, 65, "vigilar"), (65, 101, "sano")]  # ≈ cuartiles de la escala publicada (D17)
DORMANT_CAP = 30.0
POSITIVE_PREFIX = ("positive", "expansion")  # eventos de la cara positiva (nota de expansión)


def band_of(s: float) -> str:
    for lo, hi, name in BANDS:
        if lo <= s < hi:
            return name
    return "sano"


class HealthScorer(BaseEstimator, TransformerMixin):
    def __init__(self, calibrate: bool = True, l2: float = 1.0, weight_floor: float = 0.0,
                 smooth_alpha: float = 0.5, dormant_cap: float = DORMANT_CAP, target: str = "adversa"):
        self.calibrate = calibrate
        self.l2 = l2
        self.weight_floor = weight_floor
        self.smooth_alpha = smooth_alpha
        self.dormant_cap = dormant_cap
        self.target = target  # "adversa" (E1-E3), "expansion" (E4) o "todos": qué eventos calibran los pesos (D32)

    # ---------- ajuste ----------
    def fit(self, X: pd.DataFrame, y: pd.Series | None = None):
        X = X.reindex(columns=list(dict.fromkeys([*X.columns, *SPEC, *CONTEXT])))
        self.ref_, self.bounds_ = {}, {}
        for f, (_, d, zero_best, *_r) in SPEC.items():
            v = X[f].replace([np.inf, -np.inf], np.nan).dropna().astype(float).to_numpy()
            if len(v) == 0:
                continue
            self.ref_[f] = np.sort(v[v > 0] if zero_best and (v > 0).any() else v)
            self.bounds_[f] = (np.quantile(v, 0.005), np.quantile(v, 0.995))
        for c in CONTEXT:
            v = X[c].replace([np.inf, -np.inf], np.nan).dropna().astype(float)
            if len(v):
                self.bounds_[c] = (v.quantile(0.005), v.quantile(0.995))
        self.features_ = [f for f in SPEC if f in self.ref_]
        self.feature_names_in_ = np.array(self.features_)
        w = np.array([PRIOR_W[f] for f in self.features_], float)
        self.calibration_ = None
        if y is not None and self.calibrate:
            # y puede ser una serie (un evento) o un DataFrame (varios): se calibra cada evento por separado y se
            # promedian los pesos normalizados, para que cada tipo de deterioro cuente igual (D12)
            Y = y.to_frame() if isinstance(y, pd.Series) else pd.DataFrame(y)
            if len(Y) != len(X):
                raise ValueError("y debe tener las mismas filas que X")
            Y = Y.set_axis(X.index)
            # dos notas, no una (D32): promediar los pesos de la tensión con los de la expansión diluía la caja
            # (runway 3,4 para tensión, 0,0 para expansión). La nota adversa calibra con E1-E3; la de expansión con E4.
            pos_cols = [c for c in Y.columns if c.startswith(POSITIVE_PREFIX)]
            cal_cols = {"adversa": [c for c in Y.columns if c not in pos_cols], "expansion": pos_cols}.get(self.target, list(Y.columns)) or list(Y.columns)
            ws, self.calibration_ = [], {}
            for col in cal_cols:
                wc, info = self._calibrate(X, Y[col], w, positive=col.startswith(POSITIVE_PREFIX))
                self.calibration_[col] = info
                if wc.sum() > 0:
                    ws.append(wc / wc.sum())
            if ws:
                w = np.mean(ws, axis=0)
        w = np.maximum(w, self.weight_floor * w.sum())
        self.weights_ = dict(zip(self.features_, w / w.sum()))
        # escala publicada: transformación lineal que lleva P5→15 y P95→85 del compuesto en train (D22).
        # Lineal => la explicación sigue siendo exacta (el término constante se reparte según los pesos).
        self.scale_ = (0.0, 1.0)
        comp = self._composite(X)
        act = pd.to_numeric(X["months_since_last_tx"], errors="coerce").fillna(0).to_numpy() == 0 \
            if "months_since_last_tx" in X else np.ones(len(X), bool)
        p5, p95 = np.percentile(comp[act], [5, 95])
        b = 70.0 / max(p95 - p5, 1e-6)
        self.scale_ = (15.0 - b * p5, b)
        # escala absoluta (R02): probabilidad de cada evento a 6 meses en función del score, calibrada en train.
        # No cambia la nota ni su explicación; se publica al lado (prob_*).
        self.proba_ = {}
        if y is not None:
            Y = (y.to_frame() if isinstance(y, pd.Series) else pd.DataFrame(y)).set_axis(X.index)
            score = np.clip(self.scale_[0] + self.scale_[1] * comp, 0, 100)
            labels = {c: Y[c] for c in Y.columns}
            adv = [c for c in Y.columns if not c.startswith(POSITIVE_PREFIX)]
            if len(adv) > 1:  # "algún evento adverso": 1 si alguno ocurre, 0 si todos los observables son 0
                A = Y[adv]
                labels["adverso"] = A.max(axis=1).where(A.notna().any(axis=1))
            for name, lab in labels.items():
                m = lab.notna().to_numpy()
                yy = lab[m].to_numpy().astype(int)
                if m.sum() >= 200 and 0 < yy.sum() < len(yy):
                    lr = LogisticRegression(C=1e6, max_iter=1000).fit(score[m].reshape(-1, 1) / 100, yy)
                    self.proba_[name] = (float(lr.intercept_[0]), float(lr.coef_[0, 0]), float(yy.mean()))
        return self

    def event_proba(self, score) -> pd.DataFrame:
        """Probabilidad de cada evento a 6 meses para un score dado (escala absoluta, R02)."""
        s = np.asarray(score, float) / 100
        return pd.DataFrame({f"prob_{k}": 1 / (1 + np.exp(-(a + b * s))) for k, (a, b, _) in getattr(self, "proba_", {}).items()})

    def _composite(self, X: pd.DataFrame) -> np.ndarray:
        W = np.array([self.weights_[f] for f in self.features_])
        S = np.column_stack([self._sub(f, X[f]).fillna(50.0).to_numpy() for f in self.features_])
        return S @ W

    def _calibrate(self, X: pd.DataFrame, y: pd.Series, w_prior: np.ndarray, positive: bool = False):
        """Logística P(adverso) = σ(b − Σ w_f·s_f/100) con w_f ≥ 0 (o σ(b + Σ w·s) para eventos positivos):
        monotonía económica garantizada, las dos caras del score (D12)."""
        sgn = 1.0 if positive else -1.0
        m = y.notna()
        S = np.column_stack([self._sub(f, X.loc[m, f]).fillna(50).to_numpy() / 100 for f in self.features_])
        t = y[m].to_numpy().astype(float)
        S = S - S.mean(0)

        def nll(p):
            b, w = p[0], p[1:]
            z = b + sgn * (S @ w)
            ll = t * z - np.logaddexp(0, z)
            return -ll.mean() + self.l2 * 1e-3 * (w ** 2).sum()

        p0 = np.r_[np.log(t.mean() / (1 - t.mean())), np.full(len(w_prior), 0.1)]
        res = minimize(nll, p0, method="L-BFGS-B", bounds=[(None, None)] + [(0, None)] * len(w_prior))
        w = res.x[1:]
        info = {"coef": {f: float(v) for f, v in zip(self.features_, w.round(4))}, "n": int(m.sum()),
                "event_rate": float(t.mean()), "converged": bool(res.success)}
        return w, info

    # ---------- sub-scores ----------
    def _sub(self, f: str, v: pd.Series) -> pd.Series:
        _, d, zero_best, *_ = SPEC[f]
        ref = self.ref_[f]
        x = pd.to_numeric(v, errors="coerce").replace([np.inf, -np.inf], np.nan).to_numpy(float)
        xx = np.nan_to_num(x)
        pct = (np.searchsorted(ref, xx, "left") + np.searchsorted(ref, xx, "right")) / 2 / len(ref) * 100
        s = pct if d > 0 else 100 - pct
        if zero_best:  # cero = lo mejor; positivos se ordenan entre sí (continuo en 0+)
            s = np.where(xx <= 0, 100.0, s)
        s = np.where(np.isnan(x), np.nan, s)
        return pd.Series(s, index=v.index)

    # ---------- transformación ----------
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "weights_")
        X = X.reindex(columns=list(dict.fromkeys([*X.columns, *SPEC, *CONTEXT, "months_since_last_tx"])))
        out = pd.DataFrame(index=X.index)
        W = np.array([self.weights_[f] for f in self.features_])
        S = pd.DataFrame({f: self._sub(f, X[f]) for f in self.features_}, index=X.index)
        avail = S.notna().to_numpy()
        out["coverage"] = (avail * W).sum(1)  # fracción del peso total con dato -> confianza
        # sin dato = valor neutro 50 (no se renormaliza): lo que no sabemos tira al centro y no hay saltos
        # cuando una feature aparece o desaparece (D21)
        a, b = getattr(self, "scale_", (0.0, 1.0))
        C = b * S.fillna(50.0).to_numpy() * W + a * W  # Σ = a + b·compuesto
        for i, f in enumerate(self.features_):
            out[f"s_{f}"] = S[f]
            out[f"c_{f}"] = C[:, i]
        lin = C.sum(1)
        out["c_sin_datos"] = 0.0
        out["c_limite_0_100"] = np.clip(lin, 0, 100) - lin
        raw = pd.Series(np.clip(lin, 0, 100), index=X.index)
        # regla de negocio: sin movimientos en el mes no puede ser "sano" (D15)
        dormant = pd.to_numeric(X["months_since_last_tx"], errors="coerce").fillna(0).to_numpy() > 0
        capped = np.where(dormant, np.minimum(raw, self.dormant_cap), raw)
        out["c_regla_inactividad"] = capped - raw
        out["score_raw"] = capped
        for p in PILLARS:
            fs = [f for f in self.features_ if SPEC[f][0] == p]
            num = sum(S[f].fillna(0) * self.weights_[f] * S[f].notna() for f in fs)
            den = sum(self.weights_[f] * S[f].notna() for f in fs)
            out[f"p_{p}"] = num / den.replace(0, np.nan)
        # OOD sobre valores crudos (sin recortar) y contexto (D16)
        flags = []
        for f, (lo, hi) in self.bounds_.items():
            v = pd.to_numeric(X[f], errors="coerce")
            flags.append(((v < lo) | (v > hi) | np.isinf(v)).astype(float).where(v.notna()).rename(f))
        F = pd.concat(flags, axis=1)
        out["ood_share"] = F.mean(1).fillna(0)
        B = F.fillna(0).to_numpy().astype(bool)
        names = np.array(F.columns)
        out["ood_features"] = [",".join(names[b]) for b in B]
        return out

    def get_feature_names_out(self, input_features=None):
        return np.array(["score_raw", "coverage", "ood_share", *[f"s_{f}" for f in self.features_]])

    def score_panel(self, panel: pd.DataFrame) -> pd.DataFrame:
        """transform + suavizado EWMA por empresa. El EWMA es lineal: EWMA(score) = Σ EWMA(contribución),
        así que la explicación sigue siendo exacta tras el suavizado."""
        s = pd.concat([panel[["company_id", "group_id", "month"]].reset_index(drop=True),
                       self.transform(panel.reset_index(drop=True))], axis=1)
        s = s.sort_values(["company_id", "month"]).reset_index(drop=True)
        ccols = [c for c in s.columns if c.startswith("c_")]
        e = s.groupby("company_id")[ccols].transform(lambda x: x.ewm(alpha=self.smooth_alpha, adjust=False).mean())
        for c in ccols:
            s["e" + c] = e[c]  # contribución suavizada: ec_*
        s["score"] = e.sum(1)
        n = s.groupby("company_id").cumcount() + 1
        s["confidence"] = (s["coverage"] * (1 - s["ood_share"]) * np.minimum(1, n / 6)).clip(0, 1)
        if getattr(self, "proba_", None):
            s = pd.concat([s, self.event_proba(s["score"]).set_axis(s.index)], axis=1)
        return s


def explain(scored: pd.DataFrame, feats: pd.DataFrame | None, company_id: str, month=None, scorer: HealthScorer | None = None) -> dict:
    """Δscore publicado entre `month` y el mes anterior, descompuesto exactamente por feature."""
    s = scored[scored.company_id == company_id].sort_values("month").reset_index(drop=True)
    if s.empty:
        raise KeyError(company_id)
    i = len(s) - 1 if month is None else int(np.flatnonzero(s.month == pd.Timestamp(month))[0])
    if i == 0:
        return {"month": str(s.month[i])[:7], "prev_month": None, "delta": 0.0, "contributions": [],
                "summary_text": "Primer mes con datos: sin referencia anterior."}
    cur, prev = s.iloc[i], s.iloc[i - 1]
    fr = None
    if feats is not None:
        fr = feats[feats.company_id == company_id].sort_values("month").reset_index(drop=True)
    contribs = []
    for c in [c for c in s.columns if c.startswith("ec_")]:
        key = c[3:]
        dp = float(cur[c] - prev[c])
        meta = SPEC.get(key)
        label = meta[3] if meta else {"sin_datos": "Sin datos (neutro)", "regla_inactividad": "Regla: sin movimientos", "limite_0_100": "Límite de escala 0-100"}.get(key, key)
        vp = vn = None
        if fr is not None and key in fr.columns:
            vp, vn = fr[key].iloc[i - 1], fr[key].iloc[i]
            vp = None if pd.isna(vp) else float(vp); vn = None if pd.isna(vn) else float(vn)
        contribs.append({"feature": key, "label": label, "pillar": meta[0] if meta else "regla",
                         "delta_points": round(dp, 2), "value_prev": vp, "value_now": vn,
                         "text": f"{label}: {_fmt(vp, f=key)} → {_fmt(vn, f=key)} ({es(dp, 1, True)} pts)"})
    contribs = sorted([c for c in contribs if abs(c["delta_points"]) >= 0.05], key=lambda c: -abs(c["delta_points"]))
    delta = float(cur["score"] - prev["score"])
    top = [c for c in contribs if np.sign(c["delta_points"]) == np.sign(delta)][:2]
    verb = "sube" if delta > 0 else "baja"
    why = " y ".join(c["label"].lower() for c in top) if top else "cambios menores"
    summ = f"El score {verb} {es(abs(delta))} puntos ({es(prev['score'])} → {es(cur['score'])}), sobre todo por {why}."
    return {"month": str(cur.month)[:7], "prev_month": str(prev.month)[:7], "delta": round(delta, 2),
            "contributions": contribs, "summary_text": summ}


PCT = {"lc_util", "ap_late_share", "ar_late_share", "refund_rate", "transfer_dep", "lost_share", "debt_burden", "payroll_cv", "oper_persistence_6m"}


def fmt_feature(f: str, v) -> str:
    """Valor de una feature en unidades legibles para el jurado."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "sin dato"
    if f == "runway":  # log(1 + caja/gasto) con signo -> meses
        m = np.sign(v) * np.expm1(abs(v))
        return f"{es(m, 1)} meses" if abs(m) < 100 else ">100 meses"
    if f in PCT:
        return f"{es(100 * v, 0)} %"
    if f in ("growth_vs_12m", "activity_trend", "cust_trend"):
        return f"{es(100 * (np.exp(v) - 1), 0, True)} %"
    if f == "net_margin_6m":
        return f"{es(100 * v, 0, True)} %"
    if f in ("ap_overdue_ratio", "ar_overdue_90_ratio", "net_vol_6m"):
        return f"{es(v, 1)}× gasto mensual" if f == "net_vol_6m" else f"{es(v, 1)} meses de pagos" if v < 100 else ">100 meses"
    if f == "hhi_ar_6m":
        return f"{es(v, 2)}"
    return es(v, 2)


def _fmt(v, nd: int = 2, f: str | None = None):
    if f is not None:
        return fmt_feature(f, v)
    return "sin dato" if v is None else es(v, nd)


def es(v: float, nd: int = 1, sign: bool = False) -> str:
    """Número en formato es-ES (coma decimal)."""
    s = f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"
    return s.replace(".", ",")


# ---------------------------------------------------------------- forecaster
class TrajectoryForecaster(BaseEstimator):
    """Entrada larga: unique_id, ds, y (+ columnas exógenas contemporáneas). Internamente crea
    c_h{h} = c retardada h meses; el modelo del horizonte h solo ve valores conocidos en el origen."""

    def __init__(self, horizon: int = 3, quantiles=(0.1, 0.5, 0.9), lags=(1, 2, 3, 6), exog: tuple = (),
                 min_history: int = 3, lgb_params: dict | None = None, conformal: bool = True):
        self.conformal = conformal
        self.horizon = horizon
        self.quantiles = quantiles
        self.lags = lags
        self.exog = exog
        self.min_history = min_history
        self.lgb_params = lgb_params

    def _models(self):
        base = dict(n_estimators=250, learning_rate=0.04, num_leaves=15, min_child_samples=40, subsample=0.8,
                    subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, n_jobs=3)
        base.update(self.lgb_params or {})
        return {f"q{int(q * 100)}": lgb.LGBMRegressor(objective="quantile", alpha=q, **base) for q in self.quantiles}

    def _with_h(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values(["unique_id", "ds"])
        cols = {}
        for c in getattr(self, "exog_", self.exog):
            g = df.groupby("unique_id")[c]
            for h in range(1, self.horizon + 1):
                cols[f"{c}_h{h}"] = g.shift(h)
        return pd.concat([df[["unique_id", "ds", "y"]], pd.DataFrame(cols, index=df.index)], axis=1)

    def fit(self, df: pd.DataFrame, y=None):
        """Ajuste + (opcional) calibración conformal de los cuantiles extremos (CQR, D18): se reajusta con las
        series de train cortadas H meses antes, se predicen esos H meses y el cuantil (1−α) de las
        puntuaciones de no-conformidad ensancha (o estrecha) el intervalo por horizonte."""
        self.cqr_ = {h: 0.0 for h in range(1, self.horizon + 1)}
        if self.conformal:
            last = df.ds.max()
            cut = last - pd.DateOffset(months=self.horizon)
            inner = TrajectoryForecaster(**{**self.get_params(), "conformal": False})._fit(df[df.ds <= cut])
            hist = df[df.ds <= cut]
            p = inner.predict(hist).merge(df[["unique_id", "ds", "y"]], on=["unique_id", "ds"])
            lo, hi = f"q{int(self.quantiles[0] * 100)}", f"q{int(self.quantiles[-1] * 100)}"
            alpha = self.quantiles[0] + (1 - self.quantiles[-1])
            for h in range(1, self.horizon + 1):
                ph = p[(p.h == h) & ~p.fallback]
                sc = np.maximum(ph[lo] - ph.y, ph.y - ph[hi])
                n = len(sc)
                if n > 20:
                    self.cqr_[h] = float(np.quantile(sc, min(1, np.ceil((n + 1) * (1 - alpha)) / n)))
        return self._fit(df)

    def _fit(self, df: pd.DataFrame):
        # exógenas sin ningún dato (p.ej. pilar con peso 0) se descartan: LightGBM no admite columnas vacías
        self.exog_ = tuple(c for c in self.exog if c in df.columns and df[c].notna().any())
        d = self._with_h(df)
        self.mlf_ = MLForecast(
            models=self._models(), freq="MS", lags=list(self.lags),
            lag_transforms={1: [RollingMean(3), RollingStd(3), ExpandingMean(), ExponentiallyWeightedMean(0.5)],
                            3: [RollingMean(3)]},
            date_features=["month"])
        kw = {"horizon_feature_templates": [f"{c}_h{{h}}" for c in self.exog_]} if self.exog_ else {}
        self.mlf_.fit(d, static_features=[], max_horizon=self.horizon, dropna=False, **kw)
        # respaldo para historia corta: AR(1) agrupado + cuantiles de residuo por horizonte
        s = df.sort_values(["unique_id", "ds"])
        self.fallback_ = {}
        for h in range(1, self.horizon + 1):
            fy = s.groupby("unique_id")["y"].shift(-h); m = fy.notna()
            a, b = np.polyfit(s.loc[m, "y"], fy[m], 1)
            res = fy[m] - (a * s.loc[m, "y"] + b)
            self.fallback_[h] = (a, b, {q: float(np.quantile(res, q)) for q in self.quantiles})
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        check_is_fitted(self, "mlf_")
        df = df.sort_values(["unique_id", "ds"])
        n = df.groupby("unique_id").size()
        long_ids = n[n >= self.min_history].index
        out = []
        if len(long_ids):
            dl = df[df.unique_id.isin(long_ids)]
            d = self._with_h(dl)
            kw = {}
            if self.exog_:
                last = dl.groupby("unique_id").ds.max()
                ex = list(self.exog_)
                # valor de cada exógena b meses antes del origen T (b = 0..H-1)
                back = {b: dl.groupby("unique_id").nth(-1 - b).set_index("unique_id")[ex].reindex(last.index)
                        for b in range(self.horizon)}
                futs = []
                for k in range(1, self.horizon + 1):
                    fut = pd.DataFrame({"unique_id": last.index, "ds": pd.DatetimeIndex(last.values) + pd.DateOffset(months=k)})
                    cols = {}
                    for j in range(1, self.horizon + 1):
                        b = j - k  # c_h{j} en T+k = c(T+k−j) = c(T−b); desconocida si b < 0 (el modelo k no la usa)
                        for c in ex:
                            cols[f"{c}_h{j}"] = back[b][c].to_numpy(float) if b >= 0 else np.nan
                    futs.append(pd.concat([fut, pd.DataFrame(cols, index=fut.index)], axis=1))
                kw["X_df"] = pd.concat(futs, ignore_index=True)
            p = self.mlf_.predict(h=self.horizon, new_df=d, **kw)
            qcols = [f"q{int(q * 100)}" for q in self.quantiles]
            p[qcols] = np.sort(p[qcols].to_numpy(), axis=1)  # sin cruces de cuantiles
            p["fallback"] = False
            out.append(p)
        short = n[n < self.min_history].index
        if len(short):
            last = df[df.unique_id.isin(short)].groupby("unique_id").agg(ds=("ds", "max"), y=("y", "last"))
            rows = []
            for uid, r in last.iterrows():  # pocas series: bucle simple
                for h in range(1, self.horizon + 1):
                    a, b, rq = self.fallback_[h]
                    base = a * r.y + b
                    rows.append({"unique_id": uid, "ds": r.ds + pd.DateOffset(months=h),
                                 **{f"q{int(q * 100)}": base + rq[q] * 1.5 for q in self.quantiles}, "fallback": True})
            out.append(pd.DataFrame(rows))
        res = pd.concat(out, ignore_index=True)
        qcols = [f"q{int(q * 100)}" for q in self.quantiles]
        res["h"] = res.groupby("unique_id").cumcount() + 1
        adj = res.h.map(getattr(self, "cqr_", {})).fillna(0.0)
        res[qcols[0]] = np.minimum(res[qcols[0]] - adj, res[qcols[1]])
        res[qcols[-1]] = np.maximum(res[qcols[-1]] + adj, res[qcols[1]])
        res[qcols] = res[qcols].clip(0, 100)
        return res


# ---------------------------------------------------------------- alertas (monitor)
ALERT_DELTA = 10.0  # mediana prevista a 3 meses (calibrado OOF: precisión 0,37 vs tasa base 0,16)
DROP_1M = 10.0  # caída del score PUBLICADO en el mes (≈20 pts en bruto): el bruto es ruidoso por diseño


def alerts_for(score_now: float, q: dict, drop_1m: float | None, dormant: bool) -> list[dict]:
    """Reglas del monitor (D17), calibradas out-of-fold: la mediana decide la alerta y el intervalo la severidad.
    q = {q10,q50,q90} del score a 3 meses."""
    if dormant:  # la inactividad explica cualquier caída: no se duplica como bache/caída/deterioro
        return [{"type": "inactividad", "severity": "alta", "text": "Sin movimientos bancarios este mes"}]
    out = []
    d50, d10, d90 = q["q50"] - score_now, q["q10"] - score_now, q["q90"] - score_now
    rng = f"(intervalo 80 %: {es(d10, 1, True)} a {es(d90, 1, True)})"
    if d50 <= -ALERT_DELTA:
        sev = "alta" if (score_now >= 65 or d90 < 0) else "media"  # se tuerce aún pareciendo sana, o intervalo entero abajo
        out.append({"type": "deterioro", "severity": sev, "text": f"Deterioro previsto de {es(abs(d50))} pts a 3 meses {rng}"})
    if d50 >= ALERT_DELTA:
        sev = "alta" if d10 > 0 else "media"
        out.append({"type": "mejora", "severity": sev, "text": f"Mejora prevista de {es(d50)} pts a 3 meses {rng}"})
    if drop_1m is not None and drop_1m <= -DROP_1M:
        recov = q["q50"] - (score_now - drop_1m)  # distancia prevista al nivel previo a la caída
        if recov >= drop_1m / 2:  # se espera recuperar al menos la mitad
            out.append({"type": "bache", "severity": "baja", "text": f"Caída de {es(abs(drop_1m))} pts este mes, se espera recuperación (bache)"})
        else:
            out.append({"type": "caida", "severity": "alta", "text": f"Caída de {es(abs(drop_1m))} pts este mes sin recuperación prevista (caída estructural)"})
    return out
