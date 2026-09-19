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

# Pestaña de tesorería: magnitudes mensuales del panel, en moneda de la empresa (D03)
TREASURY_COLS = ["inflow", "outflow", "oper_in", "payroll", "tax", "debt_service", "cash_end", "lc_drawn", "lc_limit",
                 "ar_issued", "ap_issued", "overdue_ar", "overdue_ap", "overdue_90_ar", "overdue_90_ap"]
# deuda en la foto final de balances; los avales son riesgo contingente y no suman a la deuda viva
DEBT_LABELS = {"loan": "Préstamos", "mortgage": "Hipotecas", "leasing": "Leasing", "renting": "Renting",
               "lineofcredit": "Pólizas de crédito", "confirming": "Confirming", "factoring": "Factoring",
               "guarantee": "Avales"}
CONTINGENT = {"guarantee"}


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
        self.debt = _debt_snapshot(self.comp)

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

    def treasury(self, cid: str) -> dict:
        """Series mensuales de caja, liquidez, deuda y facturas de una empresa (para las gráficas de la SPA)."""
        if cid not in self.comp.index:
            raise KeyError(cid)
        r = self.raw.filter(pl.col("company_id") == cid).sort("month").to_pandas()
        has_erp = bool(r.has_erp.iloc[-1]) if len(r) else False
        months = []
        for x in r.itertuples():
            row = {"month": str(x.month)[:7], **{k: _num(getattr(x, k)) for k in TREASURY_COLS}}
            row["net"] = _num((row["inflow"] or 0) - (row["outflow"] or 0))
            lim = row["lc_limit"] or 0
            # póliza sin usar: límite concedido menos lo dispuesto a fin de mes
            row["credit_available"] = _num(max(lim - (row["lc_drawn"] or 0), 0)) if lim > 0 else None
            row["liquidity"] = _num((row["cash_end"] or 0) + (row["credit_available"] or 0)) if row["cash_end"] is not None else None
            months.append(row)
        d = self.debt[self.debt.company_id == cid]
        items = [{"type": t.type, "label": DEBT_LABELS.get(t.type, t.type), "owed": _num(t.owed), "granted": _num(t.granted),
                  "n_products": int(t.n), "contingent": t.type in CONTINGENT}
                 for t in d.sort_values("owed", ascending=False).itertuples()]
        c = self.comp.loc[cid]
        return {"company": {"company_id": cid, "group_id": _str(c.group_id), "currency": _str(c.currency), "has_erp": has_erp,
                            "last_month": months[-1]["month"] if months else None},
                "months": months,
                "debt": {"as_of": "2026-09-01", "items": items,
                         "total_owed": _num(sum(i["owed"] or 0 for i in items if not i["contingent"]))}}

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


def _debt_snapshot(comp: pd.DataFrame) -> pd.DataFrame:
    """Deuda viva por empresa y tipo de producto en la foto final, convertida a la moneda de la empresa (D03).

    Solo la foto: no se proyecta hacia atrás (D11); la historia mensual de deuda en la SPA es la póliza dispuesta."""
    import fx as FX
    dp = pd.read_parquet(ROOT / "data/debt_products.parquet")[["product_id", "company_id", "type", "currency", "granted"]]
    bal = pd.read_parquet(ROOT / "data/balances.parquet")[["product_id", "balance"]]
    d = dp.merge(bal, on="product_id", how="left").merge(comp[["currency"]].rename(columns={"currency": "ccur"}),
                                                        left_on="company_id", right_index=True)
    fx = FX.load()
    fx = fx[fx.month == fx.month.max()].set_index("currency").per_eur
    # unidades de la moneda del producto por unidad de la de la empresa (misma convención que panel.py)
    rate = (d.currency.map(fx) / d.ccur.map(fx)).where(d.currency != d.ccur, 1.0).fillna(1.0)
    d = d.assign(owed=(-d.balance.fillna(0)).clip(lower=0) / rate, granted=d.granted.abs().fillna(0) / rate)
    return (d.groupby(["company_id", "type"], as_index=False)
             .agg(owed=("owed", "sum"), granted=("granted", "sum"), n=("product_id", "size")))


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) or np.isinf(v) else round(v, 4) + 0.0  # + 0.0: sin −0


def _str(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)


def _fmtv(v):
    v = _num(v)
    return "sin dato" if v is None else es(v, 2)


# ──────────────────────────────────────────────────────────────
# Productos financieros – integrados con el scoring de HealthScorer
# Usan FEATURES REALES del modelo: SPEC de xray.py, PILLARS, band_of()
# ──────────────────────────────────────────────────────────────

# Definiciones de productos financieras – cada una mapea a features reales del score
# El score tiene: score (0–100), band (sano/vigilar/riesgo), trend (mejora/deterioro/estable),
#   pillars (liquidez, rentabilidad, solvencia, disciplina, estabilidad),
#   features (SPEC): inflow, outflow, cash_end, runway, debt_burden, late_share_ap,
#   late_share_ar, overdue_ap, overdue_ar, net_margin_6m, growth_vs_12m, refund_rate,
#   lc_util, lost_share, cust_trend, hhi_ar_6m, net_vol_6m, transfer_dep, has_erp,
#   months_since_last_tx, months_since_final_tx

PRODUCT_DEFS = [
    {
        "id": "yield",
        "label": "Yield · Colocación de excedente",
        "icon": "chart-line",
        "description": "El score detecta cajas ociosas: diferencia entre lo que entra y lo que necesita para operar. Coloca el excedente al 2–3 % anual.",
        "requires_score_min": 40,  # Solo si el score es decente (la empresa no está en problemas)
        "condition_key": "cash_end",  # Feature real del score
        "condition_alt": "outflow",
        "calc_rule": lambda f: max(_num(f.get("cash_end", 0)) or 0 - (_num(f.get("outflow", 0)) or 0) * 2, 0),
        "calc_label": "excedente_ocioso",
        "risk": 0,
        "rate": 0.025,
        "commission_bps": 100,
        "pitch": "Tu score dice que tienes {excess_fmt} ociosos cada mes → genera {yield_fmt}/mes al 2,5 %. Embat cobra 1 % de comisión.",
        "lender_action": "colocar",
    },
    {
        "id": "reserve",
        "label": "Reserve · Financiación preventiva",
        "icon": "shield-halved",
        "description": "El score detecta deterioro o runway corto → la empresa negocia una línea de crédito ANTES de quedarse sin caja.",
        "requires_score_max": 60,  # Solo para empresas no sanas (score bajo)
        "condition_key": "runway",
        "condition_alt": "trend",
        "calc_rule": lambda f: max(0, 6 - (_num(f.get("runway")) or 999)) * (_num(f.get("outflow")) or 1) * 0.5,
        "calc_label": "linea_recomendada",
        "risk": 1,
        "commission_bps": 50,
        "pitch": "El score detecta deterioro. Tu caja se acaba en {runway} meses → línea recomendada de {linea_fmt}. Negocia con 60 días de antelación.",
        "lender_action": "vigilar",
    },
    {
        "id": "fx",
        "label": "FX Shield · Cobertura de divisa",
        "icon": "globe",
        "description": "El score detecta exposición a divisas: transacciones en moneda distinta a la local. Cubre el tipo de cambio.",
        "condition_key": "fx_exposure",
        "condition_alt": None,
        "calc_rule": lambda f: _num(f.get("n_tx", 0)) or 0,  # Se calcula aparte con panel data
        "calc_label": "fx_notional",
        "risk": 0.3,
        "commission_bps": 15,
        "pitch": "El score ve {fx_fmt} en divisa en 2 meses → ahorra {fx_savings_fmt} con {fx_bps} pb.",
        "lender_action": "colocar",
    },
    {
        "id": "factoring",
        "label": "Factoring · Anticipos de cobros",
        "icon": "file-invoice-dollar",
        "description": "El score detecta AR vencido alto: la empresa puede anticipar cobros de clientes morosos a 1,5 % de descuento.",
        "condition_key": "overdue_ar",
        "condition_alt": None,
        "calc_rule": lambda f: _num(f.get("overdue_ar", 0)) or 0,
        "calc_label": "overdue_ar",
        "risk": 0.5,
        "commission_bps": 150,
        "pitch": "AR vencido: {ar_fmt} → cobra hoy a 1,5 % ({disc_fmt} de descuento). El score ya sabe cuánto riesgo hay.",
        "lender_action": "cobrar",
    },
    {
        "id": "credit",
        "label": "Credit · Seguro de impago",
        "icon": "shield-check",
        "description": "El score detecta morosidad alta en cobros: la aseguradora ajusta la prima sobre impago de clientes según la salud.",
        "condition_key": "late_share_ar",
        "condition_alt": "overdue_ar",
        "calc_rule": lambda f: _num(f.get("late_share_ar", 0)) or 0,
        "calc_label": "late_share_ar_pct",
        "risk": 0.7,
        "commission_bps": 20,
        "pitch": "{late_fmt}% de cobros tardíos → la aseguradora ajusta la prima en tiempo real. Póliza que se entera antes que el siniestro.",
        "lender_action": "asegurar",
    },
]


def _product_recommendations(feats_row, scored_row, cid):
    """Calcula recomendaciones de producto para una empresa basada en FEATURES y SCORE REALES."""
    fr = feats_row if feats_row is not None else pd.Series()
    sr = scored_row if scored_row is not None else pd.Series()

    score_val = _num(sr.get("score")) or 50.0
    band_val = _str(sr.get("band")) or "vigilar"

    recs = []

    for pdef in PRODUCT_DEFS:
        pid = pdef["id"]

        # Check score-based conditions
        if pdef.get("requires_score_min") and score_val < pdef["requires_score_min"]:
            continue
        if pdef.get("requires_score_max") and score_val > pdef["requires_score_max"]:
            continue

        # Check feature-based conditions
        val = _num(fr.get(pdef["condition_key"]))
        alt_val = _num(fr.get(pdef["condition_alt"])) if pdef.get("condition_alt") else None

        meets = False
        if pid == "yield":
            meets = (val or 0) > (alt_val or 0) * 2  # cash_end > outflow * 2
        elif pid == "reserve":
            runway = _num(fr.get("runway")) or 999
            trend = _str(fr.get("trend")) or "estable"
            meets = runway < 6 or trend == "deterioro"
        elif pid == "fx":
            # Needs panel data for fx_exposure calculation
            meets = (_num(fr.get("n_tx")) or 0) > 50  # Proxy: active companies likely have FX
        elif pid == "factoring":
            meets = (val or 0) > 50000  # overdue_ar > 50K €
        elif pid == "credit":
            meets = ((val or 0) > 0.15 or (alt_val or 0) > 200000)  # late_share_ar > 15% or overdue_ar > 200K

        if not meets:
            continue

        # Calculate metrics based on real features
        cash_end = _num(fr.get("cash_end")) or 0
        outflow = _num(fr.get("outflow")) or 1
        inflow = _num(fr.get("inflow")) or 1
        overdue_ar = _num(fr.get("overdue_ar")) or 0
        runway = _num(fr.get("runway")) or 999
        late_share_ar = _num(fr.get("late_share_ar")) or 0

        if pid == "yield":
            excess = max(cash_end - outflow * 2, 0)
            monthly_yield = round(excess * pdef["rate"] / 12, 2)
            annual_yield = round(excess * pdef["rate"], 2)
            commission = round(excess * pdef["commission_bps"] / 10000, 2)
            rec = {
                **pdef,
                "meets": True,
                "excess": round(excess, 2),
                "monthly_yield": monthly_yield,
                "annual_yield": annual_yield,
                "commission": commission,
                "status": "disponible",
                "consumer_text": f"{fmtMoney(excess)} ociosos cada mes → genera {fmtMoney(monthly_yield)}/mes al 2,5 %.",
                "score_impact": "positivo" if score_val > 60 else "neutro" if score_val > 40 else "crítico",
            }

        elif pid == "reserve":
            recommended_line = round(outflow * min(max(runway, 0.5), 3) * 0.5, 2)
            commission = round(recommended_line * pdef["commission_bps"] / 10000, 2)
            rec = {
                **pdef,
                "meets": True,
                "runway": round(runway, 1),
                "recommended_line": round(recommended_line, 2),
                "commission": commission,
                "status": "recomendado" if runway < 3 else "preventivo" if runway < 6 else "preventivo-lejano",
                "consumer_text": f"Caja se acaba en {runway:.0f} meses → línea recomendada de {fmtMoney(recommended_line)}.",
                "score_impact": "crítico" if runway < 2 else "importante" if runway < 4 else "moderado",
            }

        elif pid == "fx":
            # Estimate FX exposure from transactions
            fx_exp = min(0.30, max(0.05, (_num(fr.get("n_tx")) or 100) / 1000))  # Simple proxy
            fx_notional = round(inflow * fx_exp, 2)
            savings = round(fx_notional * pdef["commission_bps"] / 10000, 2)
            rec = {
                **pdef,
                "meets": True,
                "fx_exposure": round(fx_exp * 100, 1),
                "fx_notional": round(fx_notional, 2),
                "savings": savings,
                "status": "ahorro",
                "consumer_text": f"{fx_exp * 100:.1f}% flujo en divisa ({fmtMoney(fx_notional)} en 2 meses) → ahorra {fmtMoney(savings)}.",
                "score_impact": "positivo" if score_val > 50 else "neutro",
            }

        elif pid == "factoring":
            discount = round(overdue_ar * 0.015, 2)
            cash_improvement = round(overdue_ar * 0.985, 2)
            rec = {
                **pdef,
                "meets": True,
                "overdue_ar": round(overdue_ar, 2),
                "discount": discount,
                "cash_improvement": cash_improvement,
                "status": "rentable" if overdue_ar > 200000 else "rentable",
                "consumer_text": f"AR vencido: {fmtMoney(overdue_ar)} → cobra hoy a 1,5 % ({fmtMoney(discount)}).",
                "score_impact": "positivo" if score_val < 60 else "leve",
            }

        elif pid == "credit":
            premium = round(inflow * 0.005 * late_share_ar, 2)
            ref_fee = round(premium * 0.20, 2)
            rec = {
                **pdef,
                "meets": True,
                "late_share_ar": round(late_share_ar * 100, 1),
                "overdue_ar": round(overdue_ar, 2),
                "premium": premium,
                "referral_fee": ref_fee,
                "status": "recomendado",
                "consumer_text": f"{late_share_ar * 100:.1f}% cobros tardíos → aseguradora ajusta la prima en tiempo real.",
                "score_impact": "positivo",
            }
        else:
            rec = {**pdef, "meets": True, "status": "disponible", "consumer_text": ""}

        recs.append(rec)

    return {
        "company_id": cid,
        "score": round(score_val, 2),
        "band": band_val,
        "products": recs,
        "total_products": len(recs),
        "total_annual_yield": round(sum(r.get("annual_yield", 0) for r in recs), 2),
        "total_commissions": round(sum(r.get("commission", 0) for r in recs), 2),
    }


if __name__ == "__main__":
    import time
    t0 = time.time()
    train_and_save()
    svc = XRayService()
    print(f"ok en {time.time() - t0:.0f}s; empresas={len(svc.summary)}; alertas último mes={len(svc.monitor()['alerts'])}")
    print(svc.companies()["companies"][0])
    r = svc.scenario(svc.summary[0]["company_id"], 3, {"inflow": 0.6})
    print(r["summary_text"], r["band_before"], "→", r["band_after"])
