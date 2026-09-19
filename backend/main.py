"""API del score. Arranca, entrena (o carga el artefacto) y sirve.

    uv run uvicorn main:app --reload --port 8000

El estado es una tabla en memoria: el panel puntuado. No hay base de datos porque no
hace falta — son 21 000 filas y el modelo es un scorecard congelado.

    GET /api/companies                     cartera: una fila por empresa (último mes)
    GET /api/companies/{cid}               ficha: serie, pilares, probabilidades
    GET /api/companies/{cid}/explain       por qué se movió la nota este mes
    GET /api/model                         pesos, escala y diagnóstico del ajuste
    GET /health
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import decision as dcs
import predict as prd
import preprocessing as pre
from models import CompanyDetail, CompanySummary, Explanation, MonthFlow, PortfolioResponse

ARTIFACT = Path(os.getenv("XRAY_ARTIFACT", Path(__file__).parent / "artifacts/scorer.joblib"))
TREND_MONTHS = 3
TREND_EPS = 2.0          # menos de 2 puntos en 3 meses es ruido, no tendencia
ALERT_DROP = 10.0        # caída de 3 meses que dispara aviso


FLOW_MONTHS = 12         # meses de flujos y de serie de nota que se envían al frontend


class State:
    panel: pd.DataFrame
    scored: pd.DataFrame
    cartera: pd.DataFrame     # una fila por empresa, ya con el contrato del frontend
    scorer: prd.Scorer        # nota adversa: la publicada
    expansion: prd.Scorer     # nota de expansión: mismas features, calibrada con la cara positiva


S = State()


def train(force: bool = False) -> None:
    """Carga el panel, ajusta (o recupera) los dos scorers y puntúa todo el histórico."""
    S.panel = pre.build()
    y = pre.labels(S.panel)
    if ARTIFACT.exists() and not force:
        S.scorer, S.expansion = prd.load(ARTIFACT)
    else:
        S.scorer = prd.fit(S.panel, y)
        S.expansion = prd.fit(S.panel, y, target="expansion")
        prd.save((S.scorer, S.expansion), ARTIFACT)
    S.scored = prd.score_panel(S.scorer, S.panel)
    # dos notas, no una: promediar los pesos de la tensión con los de la expansión dejaba
    # la caja sin peso. La de expansión responde «¿está creciendo?», no «¿va a romper?»
    exp = prd.score_panel(S.expansion, S.panel)[["company_id", "month", "score"]]
    S.scored = S.scored.merge(exp.rename(columns={"score": "score_expansion"}), on=["company_id", "month"])
    # trayectoria OBSERVADA, no prevista: cuánto se ha movido la nota en los últimos 3 meses
    g = S.scored.sort_values(["company_id", "month"]).groupby("company_id")
    S.scored["delta3"] = S.scored["score"] - g["score"].shift(TREND_MONTHS)
    # la decisión: vetos por encima de la nota
    dec = dcs.decide_panel(S.scored, S.panel)[["company_id", "month", "accion", "vetos", "avisos", "razon"]]
    S.scored = S.scored.merge(dec, on=["company_id", "month"])
    S.cartera = _cartera()


@asynccontextmanager
async def lifespan(app: FastAPI):
    train()
    yield


app = FastAPI(title="X-Ray score", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ------------------------------------------------------------------ helpers
def _num(v):
    """NaN/NaT -> None: JSON no tiene NaN y el frontend no debe recibir 'NaN'."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)) or pd.isna(v):
        return None
    return v.item() if hasattr(v, "item") else v


def _round(v, nd: int):
    v = _num(v)
    return None if v is None else round(float(v), nd)


def _trend(delta: float | None) -> str:
    if delta is None or abs(delta) < TREND_EPS:
        return "estable"
    return "mejora" if delta > 0 else "deterioro"


def _alert(row: pd.Series) -> str | None:
    if row.get("delta3") is not None and row["delta3"] <= -ALERT_DROP:
        return f"Cae {abs(row['delta3']):.0f} puntos en {TREND_MONTHS} meses"
    if row["band"] == "riesgo":
        return "En banda de riesgo"
    if _num(row.get("confidence")) is not None and row["confidence"] < 0.4:
        return "Datos insuficientes: nota provisional"
    return None


def _company_row(cid: str) -> pd.DataFrame:
    rows = S.scored[S.scored.company_id == cid].sort_values("month")
    if rows.empty:
        raise HTTPException(404, f"empresa desconocida: {cid}")
    return rows


@lru_cache(maxsize=1)
def _static() -> pd.DataFrame:
    """Atributos que no cambian con el mes (los toma de la última fila del panel)."""
    cols = [c for c in ["company_id", "group_id", "currency", "has_erp"] if c in S.panel.columns]
    return S.panel.sort_values("month").groupby("company_id")[cols].last().reset_index(drop=False, names="idx")


def _cartera() -> pd.DataFrame:
    """Una fila por empresa con el contrato `CompanySummary` del frontend.

    Las magnitudes se publican en la unidad que el producto enseña, no en la del modelo:
    `runway` puntúa como log(1 + caja/gasto) pero aquí van **meses de caja**, que es lo
    que lee un CFO. Lo que el panel no mide se queda en null: inventar un denominador
    para llenar un hueco de la interfaz es peor que decir «sin dato».
    """
    p = S.panel.sort_values(["company_id", "month"]).copy()
    burn = np.maximum(p.out3 / 3, p.out12 / 12).replace(0, np.nan)
    p["meses_caja"] = p.cash_end / burn
    p["margin_3m"] = (p.in3 - p.out3) / (p.in3 + p.out3).replace(0, np.nan)
    # % del pendiente de cobro con más de 60 días de retraso. El vencido total no sirve:
    # el generador acumula AR que nunca se cobra y la ratio se satura (97 % de mediana).
    p["overdue_share"] = 100 * p.overdue_90_ar / p.open_ar.replace(0, np.nan)
    g = p.groupby("company_id")
    p["meses_caja_prev"] = g["meses_caja"].shift(TREND_MONTHS)
    p["dso_prev"] = g["dso_ar_3m"].shift(TREND_MONTHS)

    flows = {c: [MonthFlow(month=f"{m:%Y-%m}", **{"in": _num(i) or 0.0, "out": _num(o) or 0.0}, cash=_num(k) or 0.0)
                 for m, i, o, k in zip(d.month, d.inflow, d.outflow, d.cash_end)]
             for c, d in p.groupby("company_id")[["month", "inflow", "outflow", "cash_end"]].tail(FLOW_MONTHS).groupby(p.company_id)}

    s = S.scored.sort_values(["company_id", "month"])
    hist = {c: [round(float(v), 1) for v in d] for c, d in s.groupby("company_id")["score"].apply(list).items()}
    n = s.groupby("company_id").size()

    last_p = p.groupby("company_id").last()
    out = s.groupby("company_id").last().join(last_p, rsuffix="_p")
    out["n_months"] = n
    out["flows"] = out.index.map(flows)
    out["history"] = out.index.map(lambda c: hist[c][-FLOW_MONTHS:])
    return out.reset_index()


# ------------------------------------------------------------------ endpoints
@app.get("/health")
def health():
    return {"ok": True, "empresas": int(S.scored.company_id.nunique()),
            "ultimo_mes": f"{S.scored.month.max():%Y-%m}", "features": S.scorer.features}


@app.get("/api/companies", response_model=PortfolioResponse)
def companies(band: str | None = Query(None, pattern="^(sano|vigilar|riesgo)$"), limit: int = 2000):
    """Cartera: el último mes de cada empresa, ordenada por nota ascendente (lo peor arriba)."""
    c = S.cartera
    if band:
        c = c[c.band == band]
    out = []
    for _, r in c.sort_values("score").head(limit).iterrows():
        d3 = _num(r.delta3)
        out.append(CompanySummary(
            company_id=r.company_id, group_id=r.group_id,
            currency=r.get("currency") or "EUR", has_erp=bool(r.get("has_erp", False)),
            n_months=int(r.n_months), last_month=f"{r.month:%Y-%m}",
            score=round(float(r.score), 1), band=r.band,
            delta3_q50=round(float(d3), 1) if d3 is not None else 0.0, trend=_trend(d3),
            alert=_alert(r), dormant=bool(r.get("c_regla_inactividad", 0) != 0),
            confidence=round(float(r.confidence), 2),
            history=r.history, flows=r.flows,
            cash_end=_num(r.cash_end),
            runway_now=_round(r.meses_caja, 1), runway_prev=_round(r.meses_caja_prev, 1),
            dso_now=_round(r.dso_ar_3m, 0), dso_prev=_round(r.dso_prev, 0),
            overdue_share=_round(r.overdue_share, 1),
            margin_3m=_round(r.margin_3m, 4), debt_service_ratio_3m=_round(r.debt_burden, 4),
            accion=r.accion, accion_label=dcs.ACCIONES[r.accion], razon=r.razon,
            vetos=[v for v in str(r.vetos).split(",") if v],
            avisos=[v for v in str(r.avisos).split(",") if v],
            score_expansion=round(float(r.score_expansion), 1),
        ))
    return PortfolioResponse(companies=out)


@app.get("/api/companies/{cid}", response_model=CompanyDetail)
def company(cid: str):
    """Ficha completa: serie histórica, pilares del último mes y probabilidades."""
    rows = _company_row(cid)
    cur = rows.iloc[-1]
    probs = {c: round(float(cur[c]), 4) for c in rows.columns if c.startswith("prob_")}
    return {
        "company_id": cid, "group_id": cur.group_id,
        "score": round(float(cur.score), 1), "band": cur.band,
        "confidence": round(float(cur.confidence), 2),
        "coverage": round(float(cur.coverage), 2),
        "ood_share": round(float(cur.ood_share), 3),
        "ood_features": [f for f in str(cur.ood_features).split(",") if f],
        "score_expansion": round(float(cur.score_expansion), 1),
        "delta3": _num(cur.delta3) and round(float(cur.delta3), 1),
        "trend": _trend(_num(cur.delta3)),
        "pillars": {p: _num(cur.get(f"p_{p}")) for p in prd.PILLARS},
        "probabilities": probs,
        "decision": _decision(cid, cur.month),
        "series": [{"month": f"{m:%Y-%m}", "score": round(float(s), 1), "score_expansion": round(float(e), 1),
                    "band": b} for m, s, e, b in zip(rows.month, rows.score, rows.score_expansion, rows.band)],
        "signals": _signals(cid, rows),
    }


def _decision(cid: str, month) -> dict:
    """Prestar / vigilar / no prestar. Los vetos mandan sobre la nota."""
    p = S.panel[(S.panel.company_id == cid) & (S.panel.month == month)]
    s = S.scored[(S.scored.company_id == cid) & (S.scored.month == month)]
    if p.empty or s.empty:
        return {}
    row = pd.concat([s.iloc[0], p.iloc[0][[c for c in p.columns if c not in s.columns]]])
    return dcs.decide(row)


@app.get("/api/companies/{cid}/decision")
def decision(cid: str, month: str | None = None):
    rows = _company_row(cid)
    m = rows.month.iloc[-1] if month is None else pd.Timestamp(month)
    d = _decision(cid, m)
    if not d:
        raise HTTPException(404, f"mes sin datos para {cid}: {month}")
    return {"company_id": cid, "month": f"{m:%Y-%m}", **d}


def _signals(cid: str, rows: pd.DataFrame) -> list[dict]:
    """Las features del último mes, ordenadas por cuánto restan a la nota."""
    cur = rows.iloc[-1]
    f = S.panel[S.panel.company_id == cid].sort_values("month").iloc[-1]
    out = []
    for name in S.scorer.features:
        spec = pre.FEATURES[name]
        out.append({"feature": name, "label": spec["label"], "pillar": spec["pilar"],
                    "formula": spec["formula"], "weight": round(S.scorer.weights[name], 3),
                    "subscore": _num(cur.get(f"s_{name}")),
                    "points": round(float(cur.get(f"ec_{name}", 0)), 2),
                    "value": _num(f.get(name)), "value_text": prd.human(name, _num(f.get(name)))})
    return sorted(out, key=lambda s: s["points"])


@app.get("/api/companies/{cid}/explain", response_model=Explanation)
def explain(cid: str, month: str | None = None):
    """Δnota del mes descompuesto por feature. Las contribuciones suman el delta, exacto."""
    _company_row(cid)
    try:
        return prd.explain(S.scored, S.panel, cid, month)
    except IndexError:
        raise HTTPException(404, f"mes sin datos para {cid}: {month}")


@app.get("/api/model")
def model():
    """Qué aprendió el modelo. Es todo: 17 pesos, dos números de escala y las curvas de probabilidad."""
    return {
        "target": S.scorer.target, "alpha_ewma": S.scorer.alpha,
        "weights": {k: round(v, 4) for k, v in sorted(S.scorer.weights.items(), key=lambda kv: -kv[1])},
        "scale": {"a": round(S.scorer.scale[0], 3), "b": round(S.scorer.scale[1], 3)},
        "bands": [{"desde": lo, "hasta": hi, "banda": n} for lo, hi, n in prd.BANDS],
        "calibration": {k: {"n": v["n"], "event_rate": round(v["event_rate"], 4), "converged": v["converged"]}
                        for k, v in S.scorer.calibration.items()},
        "probabilities": {k: {"a": round(a, 3), "b": round(b, 3), "tasa_base": round(r, 4)}
                          for k, (a, b, r) in S.scorer.proba.items()},
        "features": {f: pre.FEATURES[f] for f in S.scorer.features},
        "anclas": pre.EVENTS,
        "weights_expansion": {k: round(v, 4) for k, v in
                              sorted(S.expansion.weights.items(), key=lambda kv: -kv[1])},
    }


@app.get("/api/vetos")
def vetos():
    """El catálogo de vetos y cuánto se gana el puesto cada uno sobre el panel."""
    rep = dcs.veto_report(S.panel, S.scored)
    return {"tasa_base_tension": round(float(rep.attrs["tasa_base"]), 4),
            "vetos": [{"codigo": v, "etiqueta": dcs.VETOS[v][0], "texto": dcs.VETOS[v][1],
                       "bloquea": v in dcs.BLOQUEAN, "levantable": v in dcs.LEVANTABLES,
                       **{k: _num(r[k]) for k in rep.columns}}
                      for v, r in rep.iterrows()]}


@app.post("/api/retrain")
def retrain():
    train(force=True)
    return health()
