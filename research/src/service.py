"""Servicio de inferencia X-Ray: entrena (o carga) el modelo final y responde a la API.

    uv run python src/service.py      # entrena con todo el train y guarda artifacts/xray.joblib
"""
from __future__ import annotations
import warnings
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import polars as pl
from features import add_features, DRIVERS
from targets import add_events
from evaluate import EXOG, EVENTS, build_series
from xray import HealthScorer, TrajectoryForecaster, SPEC, PILLARS, explain, alerts_for, band_of, es, fmt_feature

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "xray.joblib"
H = 3

SCENARIO_DRIVERS = [
    {"key": "inflow", "label": "Cobros / entradas", "kind": "mult", "min": 0, "max": 2, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala todas las entradas de caja; la caja acumula la diferencia"},
    {"key": "outflow", "label": "Pagos / salidas", "kind": "mult", "min": 0, "max": 2, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala todas las salidas (incluye nóminas, deuda, impuestos); la caja acumula la diferencia"},
    {"key": "cash_end", "label": "Saldo de caja", "kind": "mult", "min": 0, "max": 3, "step": 0.05, "default": 1, "unit": "×",
     "description": "Shock directo sobre el saldo de caja a fin de mes"},
    {"key": "payroll", "label": "Nóminas y SS", "kind": "mult", "min": 0, "max": 2, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala nóminas y seguridad social (y las salidas en la misma cuantía)"},
    {"key": "debt_service", "label": "Cuotas de deuda", "kind": "mult", "min": 0, "max": 3, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala cuotas e intereses de préstamos (y las salidas en la misma cuantía)"},
    {"key": "lc_drawn", "label": "Póliza de crédito dispuesta", "kind": "mult", "min": 0, "max": 3, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala el importe dispuesto de las líneas de crédito"},
    {"key": "late_share_ap", "label": "Pagos tardíos a proveedores", "kind": "add", "min": -1, "max": 1, "step": 0.05, "default": 0, "unit": "pp",
     "description": "Suma puntos al % de facturas de proveedores pagadas tarde"},
    {"key": "late_share_ar", "label": "Cobros tardíos de clientes", "kind": "add", "min": -1, "max": 1, "step": 0.05, "default": 0, "unit": "pp",
     "description": "Suma puntos al % de facturas de clientes cobradas tarde"},
    {"key": "overdue_ap", "label": "Deuda vencida con proveedores", "kind": "mult", "min": 0, "max": 5, "step": 0.1, "default": 1, "unit": "×",
     "description": "Escala el saldo vencido con proveedores"},
    {"key": "overdue_ar", "label": "Saldo vencido de clientes", "kind": "mult", "min": 0, "max": 5, "step": 0.1, "default": 1, "unit": "×",
     "description": "Escala el saldo vencido de clientes (incluido >60 días)"},
    {"key": "n_tx", "label": "Actividad (nº movimientos)", "kind": "mult", "min": 0, "max": 2, "step": 0.05, "default": 1, "unit": "×",
     "description": "Escala el número de movimientos bancarios"},
    {"key": "refunds", "label": "Devoluciones de cobros", "kind": "mult", "min": 0, "max": 5, "step": 0.1, "default": 1, "unit": "×",
     "description": "Escala las devoluciones de recibos/cobros"},
]


def _panel() -> pl.DataFrame:
    return pl.read_parquet(ROOT / "data/panel.parquet")


def train_and_save() -> dict:
    panel = add_events(add_features(_panel())).to_pandas()
    last = panel.month.max()
    obs = panel.month <= last - pd.DateOffset(months=6)
    scorer = HealthScorer().fit(panel, panel[EVENTS].where(obs, axis=0))
    scored = scorer.score_panel(panel)
    ser = build_series(scored, panel)
    fc = TrajectoryForecaster(horizon=H, exog=tuple(EXOG)).fit(ser[["unique_id", "ds", "y", *EXOG]])
    art = {"scorer": scorer, "forecaster": fc}
    ART.parent.mkdir(exist_ok=True)
    joblib.dump(art, ART)
    return art


class XRayService:
    def __init__(self):
        art = joblib.load(ART) if ART.exists() else train_and_save()
        self.scorer: HealthScorer = art["scorer"]
        self.fc: TrajectoryForecaster = art["forecaster"]
        self.raw = _panel()
        self.feats = add_features(self.raw).to_pandas()
        self.scored = self.scorer.score_panel(self.feats)
        self.series = build_series(self.scored, self.feats)
        self.comp = pl.read_parquet(ROOT / "data/companies.parquet").to_pandas().set_index("company_id")
        self.last_month = self.scored.month.max()
        self.forecast = self.fc.predict(self.series[["unique_id", "ds", "y", *EXOG]])
        self._alert_history = self._compute_alert_history()
        self.summary = self._summary()

    # ------------------------------------------------------------ helpers
    def _fc_for(self, ser: pd.DataFrame) -> pd.DataFrame:
        return self.fc.predict(ser[["unique_id", "ds", "y", *EXOG]])

    def _alerts_at(self, s_company: pd.DataFrame, fc3: dict) -> list[dict]:
        s_company = s_company.sort_values("month")
        cur = s_company.iloc[-1]
        drop = float(cur.score - s_company.iloc[-2].score) if len(s_company) > 1 else None
        dormant = bool(self.feats.loc[(self.feats.company_id == cur.company_id) & (self.feats.month == cur.month), "months_since_last_tx"].gt(0).any()) \
            if "months_since_last_tx" not in s_company else bool(cur.months_since_last_tx > 0)
        return alerts_for(float(cur.score), fc3, drop, dormant)

    def _compute_alert_history(self) -> pd.DataFrame:
        """Alertas mes a mes aplicando el modelo final a la historia truncada en cada mes (in-sample para train)."""
        rows = []
        ser = self.series
        for T in sorted(ser.ds.unique())[5:]:
            sh = ser[ser.ds <= T]
            p = self._fc_for(sh)
            p3 = p[p.h == H].set_index("unique_id")
            lastv = sh.sort_values("ds").groupby("unique_id").tail(2)
            cur = lastv.groupby("unique_id").tail(1).set_index("unique_id")
            prv = lastv.groupby("unique_id").head(1).set_index("unique_id")
            cur = cur[cur.ds == T]
            for uid, r in cur.iterrows():
                if uid not in p3.index:
                    continue
                drop = float(r.y - prv.loc[uid].y) if prv.loc[uid].ds < T else None
                q = {k: float(p3.loc[uid, k]) for k in ("q10", "q50", "q90")}
                for a in alerts_for(float(r.y), q, drop, bool(r.months_since_last_tx > 0)):
                    rows.append({"company_id": uid, "month": T, **a, "score": float(r.y), "delta3_q50": q["q50"] - float(r.y)})
        return pd.DataFrame(rows)

    def _item(self, cid: str) -> dict:
        s = self.scored[self.scored.company_id == cid].sort_values("month")
        cur = s.iloc[-1]
        f = self.forecast[self.forecast.unique_id == cid].sort_values("h")
        f3 = f[f.h == H].iloc[0] if len(f) else None
        d = {k: (float(f3[k]) - float(cur.score)) if f3 is not None else 0.0 for k in ("q10", "q50", "q90")}
        trend = "mejora" if d["q50"] >= 8 and d["q10"] > -3 else "deterioro" if d["q50"] <= -8 and d["q90"] < 3 else "estable"
        al = self._alert_history
        la = al[(al.company_id == cid) & (al.month == cur.month)] if len(al) else al
        top = la.sort_values("severity").iloc[0]["text"] if len(la) else None
        c = self.comp.loc[cid]
        fr = self.feats[(self.feats.company_id == cid)].sort_values("month").iloc[-1]
        return {"company_id": cid, "group_id": c.group_id, "currency": c.currency, "has_erp": bool(fr.has_erp),
                "n_months": int(len(s)), "last_month": str(cur.month)[:7], "score": round(float(cur.score), 2),
                "band": band_of(float(cur.score)), "delta3_q10": round(d["q10"], 2), "delta3_q50": round(d["q50"], 2),
                "delta3_q90": round(d["q90"], 2), "trend": trend, "alert": top,
                "dormant": bool(fr.months_since_last_tx > 0), "confidence": round(float(cur.confidence), 3)}

    def _summary(self) -> list[dict]:
        return [self._item(cid) for cid in sorted(self.scored.company_id.unique())]

    # ------------------------------------------------------------ API
    def companies(self) -> dict:
        return {"companies": self.summary}

    def company(self, cid: str) -> dict:
        if cid not in self.comp.index:
            raise KeyError(cid)
        s = self.scored[self.scored.company_id == cid].sort_values("month")
        fr = self.feats[self.feats.company_id == cid].sort_values("month")
        hist = []
        for (_, r), (_, x) in zip(s.iterrows(), fr.iterrows()):
            hist.append({
                "month": str(r.month)[:7], "score": round(float(r.score), 2), "score_raw": round(float(r.score_raw), 2),
                "pillars": {p: _num(r.get(f"p_{p}")) for p in PILLARS},
                "features": {f: _num(x.get(f)) for f in SPEC},
                "drivers": {d: _num(x.get(d)) for d in DRIVERS},
            })
        fc = self.forecast[self.forecast.unique_id == cid].sort_values("h")
        c = self.comp.loc[cid]
        al = self._alert_history
        alerts = [] if al.empty else [
            {"month": str(a.month)[:7], "type": a.type, "severity": a.severity, "text": a.text}
            for a in al[al.company_id == cid].sort_values("month", ascending=False).itertuples()]
        pw = {p: 0.0 for p in PILLARS}
        for f, w in self.scorer.weights_.items():
            pw[SPEC[f][0]] += float(w)
        return {
            "company": {**self._item(cid), "country": _str(c.country), "erp": _str(c.erp)},
            "history": hist,
            "forecast": [{"month": str(r.ds)[:7], "h": int(r.h), "q10": round(float(r.q10), 2), "q50": round(float(r.q50), 2),
                          "q90": round(float(r.q90), 2)} for r in fc.itertuples()],
            "explanation": explain(self.scored, self.feats, cid, scorer=self.scorer),
            "alerts": alerts,
            "pillar_weights": {k: round(v, 4) for k, v in pw.items()},
            "feature_meta": {f: {"label": m[3], "pillar": m[0], "direction": m[1], "description": m[4],
                                 "weight": round(float(self.scorer.weights_.get(f, 0.0)), 4)} for f, m in SPEC.items()},
        }

    def monitor(self) -> dict:
        al = self._alert_history
        cur = al[al.month == self.last_month] if len(al) else al
        order = {"alta": 0, "media": 1, "baja": 2}
        cur = cur.assign(o=cur.severity.map(order)).sort_values(["o", "delta3_q50"])
        return {"month": str(self.last_month)[:7], "alerts": [
            {"company_id": a.company_id, "month": str(a.month)[:7], "type": a.type, "severity": a.severity, "text": a.text,
             "score": round(a.score, 2), "delta3_q50": round(a.delta3_q50, 2)} for a in cur.itertuples()]}

    # ------------------------------------------------------------ escenarios
    def scenario(self, cid: str, months: int, drivers: dict) -> dict:
        if cid not in self.comp.index:
            raise KeyError(cid)
        raw = self.raw.filter(pl.col("company_id") == cid).sort("month").to_pandas()
        mod = apply_scenario(raw, int(months), drivers)
        f_base = self.feats[self.feats.company_id == cid]
        f_scn = add_features(pl.from_pandas(mod)).to_pandas()
        s_base = self.scored[self.scored.company_id == cid].sort_values("month")
        s_scn = self.scorer.score_panel(f_scn)
        ser_scn = build_series(s_scn, f_scn)
        fc_base = self.forecast[self.forecast.unique_id == cid].sort_values("h")
        fc_scn = self._fc_for(ser_scn).sort_values("h")
        cb, cs = s_base.iloc[-1], s_scn.iloc[-1]
        contribs = []
        for c in [c for c in s_scn.columns if c.startswith("ec_")]:
            key = c[3:]
            d = float(cs[c] - cb[c])
            if abs(d) < 0.05:
                continue
            meta = SPEC.get(key)
            label = meta[3] if meta else {"sin_datos": "Sin datos (neutro)", "regla_inactividad": "Regla: sin movimientos", "limite_0_100": "Límite de escala 0-100"}.get(key, key)
            vb = f_base.sort_values("month").iloc[-1].get(key) if key in f_base else None
            vs = f_scn.iloc[-1].get(key) if key in f_scn else None
            contribs.append({"feature": key, "label": label, "pillar": meta[0] if meta else "regla", "delta_points": round(d, 2),
                             "value_prev": _num(vb), "value_now": _num(vs),
                             "text": f"{label}: {fmt_feature(key, _num(vb))} → {fmt_feature(key, _num(vs))} ({es(d, 1, True)} pts)"})
        contribs.sort(key=lambda c: -abs(c["delta_points"]))
        dn = float(cs.score - cb.score)
        f3 = fc_scn[fc_scn.h == H].iloc[0]
        q = {k: float(f3[k]) for k in ("q10", "q50", "q90")}
        s_scn2 = s_scn.assign(months_since_last_tx=f_scn.months_since_last_tx.values)
        drop = float(cs.score - s_scn.iloc[-2].score) if len(s_scn) > 1 else None
        al_after = alerts_for(float(cs.score), q, drop, bool(s_scn2.iloc[-1].months_since_last_tx > 0))
        top = [c["label"].lower() for c in contribs if np.sign(c["delta_points"]) == np.sign(dn)][:2]
        summ = (f"En el escenario el score del último mes pasa de {es(cb.score)} a {es(cs.score)} ({es(dn, 1, True)} pts)"
                + (f", sobre todo por {' y '.join(top)}." if top else "."))
        ser_fmt = lambda s: [{"month": str(r.month)[:7], "score": round(float(r.score), 2)} for r in s.itertuples()]
        fc_fmt = lambda f: [{"month": str(r.ds)[:7], "h": int(r.h), "q10": round(float(r.q10), 2), "q50": round(float(r.q50), 2),
                             "q90": round(float(r.q90), 2)} for r in f.itertuples()]
        return {"baseline": {"history": ser_fmt(s_base), "forecast": fc_fmt(fc_base)},
                "scenario": {"history": ser_fmt(s_scn), "forecast": fc_fmt(fc_scn)},
                "band_before": band_of(float(cb.score)), "band_after": band_of(float(cs.score)),
                "delta_now": round(dn, 2), "contributions": contribs, "summary_text": summ, "alerts_after": al_after}


def apply_scenario(raw: pd.DataFrame, months: int, drivers: dict) -> pd.DataFrame:
    """Aplica cambios de drivers a los últimos `months` meses del panel bruto de una empresa.
    Los cambios de flujo se acumulan en la caja (una empresa que cobra menos acaba con menos caja)."""
    df = raw.copy().sort_values("month").reset_index(drop=True)
    n = len(df)
    win = np.zeros(n, bool)
    win[max(0, n - months):] = True
    base_in, base_out = df.inflow.copy(), df.outflow.copy()
    m = lambda k: float(drivers.get(k, 1.0))
    a = lambda k: float(drivers.get(k, 0.0))
    for col in ["inflow", "oper_in", "transfer_in"]:
        df.loc[win, col] *= m("inflow")
    for col in ["outflow", "payroll", "debt_service", "tax", "fees"]:
        df.loc[win, col] *= m("outflow")
    for k in ["payroll", "debt_service"]:
        before = df.loc[win, k].copy()
        df.loc[win, k] *= m(k)
        df.loc[win, "outflow"] += df.loc[win, k] - before
    df.loc[win, "refunds"] *= m("refunds")
    df.loc[win, "n_tx"] = (df.loc[win, "n_tx"] * m("n_tx")).round()
    df.loc[win, "lc_drawn"] = df.loc[win, "lc_drawn"] * m("lc_drawn")
    for k in ["overdue_ap"]:
        df.loc[win, k] = df.loc[win, k] * m(k)
    for k in ["overdue_ar", "overdue_90_ar"]:
        df.loc[win, k] = df.loc[win, k] * m("overdue_ar")
    for k in ["late_share_ap", "late_share_ar"]:
        if k in df and a(k) != 0:
            df.loc[win, k] = (df.loc[win, k].fillna(0) + a(k)).clip(0, 1)
    # la caja acumula el cambio de flujo neto del escenario
    dnet = (df.inflow - base_in) - (df.outflow - base_out)
    df["cash_end"] = df["cash_end"] + dnet.cumsum()
    df.loc[win, "cash_end"] *= m("cash_end")
    return df


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) or np.isinf(v) else round(v, 4)


def _str(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)


def _fmtv(v):
    v = _num(v)
    return "sin dato" if v is None else es(v, 2)


if __name__ == "__main__":
    import time
    t0 = time.time()
    train_and_save()
    svc = XRayService()
    print(f"ok en {time.time() - t0:.0f}s; empresas={len(svc.summary)}; alertas último mes={len(svc.monitor()['alerts'])}")
    print(svc.companies()["companies"][0])
    r = svc.scenario(svc.summary[0]["company_id"], 3, {"inflow": 0.6})
    print(r["summary_text"], r["band_before"], "→", r["band_after"])
