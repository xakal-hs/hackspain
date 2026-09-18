"""Servidor mock de la API X-Ray para desarrollar y probar la SPA sin el backend real.

Sigue app/API_CONTRACT.md al pie de la letra con datos sintéticos deterministas.

    cd research && uv run uvicorn app.mock_server:app --port 8765
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

STATIC_DIR = Path(__file__).parent / "static"

MONTHS = [f"{2024 + (8 + i) // 12}-{(8 + i) % 12 + 1:02d}" for i in range(24)]  # 2024-09 .. 2026-08
FORECAST_MONTHS = ["2026-09", "2026-10", "2026-11"]
LAST_MONTH = MONTHS[-1]
N_COMPANIES = 140

PILLARS = ["liquidez", "rentabilidad", "solvencia", "disciplina", "estabilidad"]
PILLAR_WEIGHTS = {"liquidez": 0.30, "rentabilidad": 0.20, "solvencia": 0.20, "disciplina": 0.15, "estabilidad": 0.15}

FEATURE_META: dict[str, dict[str, Any]] = {
    "runway_log": {"label": "Meses de caja", "pillar": "liquidez", "direction": 1,
                   "description": "Caja disponible entre la salida media mensual (escala logarítmica)."},
    "net_margin": {"label": "Margen de caja", "pillar": "rentabilidad", "direction": 1,
                   "description": "(Cobros − pagos) / cobros del mes."},
    "inflow_growth": {"label": "Crecimiento de cobros", "pillar": "rentabilidad", "direction": 1,
                      "description": "Variación de los cobros frente a la media de los 3 meses anteriores."},
    "debt_coverage": {"label": "Cobertura de deuda", "pillar": "solvencia", "direction": 1,
                      "description": "Cobros del mes / servicio de la deuda."},
    "late_share_ap": {"label": "Pagos a proveedores con retraso", "pillar": "disciplina", "direction": -1,
                      "description": "Proporción de facturas recibidas pagadas después del vencimiento."},
    "late_share_ar": {"label": "Cobros de clientes con retraso", "pillar": "disciplina", "direction": -1,
                      "description": "Proporción de facturas emitidas cobradas después del vencimiento."},
    "inflow_cv": {"label": "Volatilidad de cobros", "pillar": "estabilidad", "direction": -1,
                  "description": "Coeficiente de variación de los cobros en 6 meses."},
}

DRIVERS = [
    {"key": "inflow", "label": "Cobros / entradas", "kind": "mult", "min": 0, "max": 2, "step": 0.05, "default": 1,
     "unit": "×", "description": "Multiplica los cobros mensuales."},
    {"key": "outflow", "label": "Pagos / salidas", "kind": "mult", "min": 0.5, "max": 2, "step": 0.05, "default": 1,
     "unit": "×", "description": "Multiplica los pagos mensuales."},
    {"key": "cash_end", "label": "Caja a fin de mes", "kind": "mult", "min": 0, "max": 3, "step": 0.05, "default": 1,
     "unit": "×", "description": "Multiplica el saldo de caja al cierre."},
    {"key": "payroll", "label": "Nóminas", "kind": "mult", "min": 0.5, "max": 2, "step": 0.05, "default": 1,
     "unit": "×", "description": "Multiplica el gasto en nóminas."},
    {"key": "debt_service", "label": "Servicio de la deuda", "kind": "mult", "min": 0, "max": 3, "step": 0.05,
     "default": 1, "unit": "×", "description": "Multiplica cuotas de préstamos, leasing y renting."},
    {"key": "late_share_ap", "label": "Retraso en pagos a proveedores", "kind": "add", "min": -0.5, "max": 0.5,
     "step": 0.05, "default": 0, "unit": "pp", "description": "Suma puntos a la proporción de pagos con retraso."},
    {"key": "late_share_ar", "label": "Retraso en cobros de clientes", "kind": "add", "min": -0.5, "max": 0.5,
     "step": 0.05, "default": 0, "unit": "pp", "description": "Suma puntos a la proporción de cobros con retraso."},
]
DRIVER_BY_KEY = {d["key"]: d for d in DRIVERS}
# Sensibilidad (puntos de score) de cada driver: mult → coef·ln(x); add → coef·x
DRIVER_COEF = {"inflow": 20.0, "outflow": -16.0, "cash_end": 7.0, "payroll": -6.0, "debt_service": -5.0,
               "late_share_ap": -28.0, "late_share_ar": -18.0}
DRIVER_PILLAR = {"inflow": "rentabilidad", "outflow": "rentabilidad", "cash_end": "liquidez", "payroll": "rentabilidad",
                 "debt_service": "solvencia", "late_share_ap": "disciplina", "late_share_ar": "disciplina"}


def es(x: float, nd: int = 1, sign: bool = False) -> str:
    s = f"{abs(x):,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if sign:
        return ("+" if x >= 0 else "−") + s
    return ("−" if x < 0 else "") + s


def band_of(score: float) -> str:
    return "sano" if score >= 70 else ("vigilar" if score >= 50 else "riesgo")


def clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def build_company(i: int) -> dict[str, Any]:
    rng = random.Random(1000 + i)
    cid = f"COMP_{i + 1:04d}"
    archetype = rng.choices(
        ["sano", "mejora", "deterioro", "bache", "caida", "riesgo", "estable_medio"],
        weights=[22, 14, 14, 12, 8, 10, 20])[0]
    n_months = 24 if rng.random() > 0.15 else rng.randint(9, 23)
    months = MONTHS[-n_months:]
    has_erp = rng.random() > 0.25
    country, currency = rng.choice([("ES", "EUR"), ("ES", "EUR"), ("ES", "EUR"), ("PT", "EUR"), ("MX", "MXN"),
                                    ("GB", "GBP"), ("FR", "EUR")])
    start = {"sano": 80, "mejora": 44, "deterioro": 82, "bache": 72, "caida": 76, "riesgo": 38,
             "estable_medio": 60}[archetype] + rng.uniform(-6, 6)
    slope = {"sano": 0.1, "mejora": 1.1, "deterioro": -0.9, "bache": 0.05, "caida": 0.0, "riesgo": -0.1,
             "estable_medio": 0.0}[archetype] * rng.uniform(0.7, 1.3)
    drop_at = rng.randint(max(2, n_months - 8), n_months - 2) if archetype == "caida" else None
    dip_at = rng.randint(n_months - 5, n_months - 1) if archetype == "bache" else None

    scores: list[float] = []
    lvl = start
    for t in range(n_months):
        lvl += slope + rng.gauss(0, 0.8)
        if drop_at is not None and t >= drop_at:
            lvl -= 3.5
        s = lvl
        if dip_at is not None and t == dip_at:
            s -= 13
        scores.append(clip(s, 3, 97))
    scale = math.exp(rng.gauss(11.3, 0.9))
    cash = scale * rng.uniform(1.0, 4.0)
    history = []
    for t, (m, s) in enumerate(zip(months, scores)):
        q = (s - 50) / 50  # -1..1
        inflow = scale * (1 + 0.25 * q + rng.gauss(0, 0.07)) * (1 + 0.1 * math.sin(t / 2))
        outflow = inflow * (0.95 - 0.12 * q + rng.gauss(0, 0.03))
        cash = max(scale * 0.05, cash + inflow - outflow + rng.gauss(0, scale * 0.05))
        debt_service = scale * rng.uniform(0.03, 0.12) * (1 - 0.3 * q)
        late_ap = clip(0.25 - 0.22 * q + rng.gauss(0, 0.04), 0, 1) if has_erp else None
        late_ar = clip(0.3 - 0.15 * q + rng.gauss(0, 0.05), 0, 1) if has_erp else None
        pillars = {p: round(clip(s + rng.gauss(0, 6) + off), 1)
                   for p, off in zip(PILLARS, [2, -5, 4, 0, -2])}
        if not has_erp:
            pillars["disciplina"] = None
        prev_inflows = [h["drivers"]["inflow"] for h in history[-3:]] or [inflow]
        feats = {
            "runway_log": round(math.log1p(cash / max(outflow, 1)), 3),
            "net_margin": round((inflow - outflow) / inflow, 3),
            "inflow_growth": round(inflow / (sum(prev_inflows) / len(prev_inflows)) - 1, 3),
            "debt_coverage": round(inflow / max(debt_service, 1), 2),
            "late_share_ap": None if late_ap is None else round(late_ap, 3),
            "late_share_ar": None if late_ar is None else round(late_ar, 3),
            "inflow_cv": round(clip(0.25 - 0.15 * q + rng.gauss(0, 0.03), 0.02, 1), 3),
        }
        history.append({
            "month": m, "score": round(s, 1), "score_raw": round(clip(s + rng.gauss(0, 2.5)), 1),
            "pillars": pillars, "features": feats,
            "drivers": {
                "inflow": round(inflow, 2), "outflow": round(outflow, 2), "cash_end": round(cash, 2),
                "payroll": round(outflow * 0.32, 2), "debt_service": round(debt_service, 2),
                "overdue_ap": round(scale * 0.4 * (late_ap or 0.2), 2),
                "overdue_ar": round(scale * 0.5 * (late_ar or 0.25), 2),
                "late_share_ap": None if late_ap is None else round(late_ap, 3),
                "late_share_ar": None if late_ar is None else round(late_ar, 3),
                "n_tx": int(40 + scale / 1500 * rng.uniform(0.8, 1.2)),
            },
        })

    last = history[-1]["score"]
    recent_slope = (history[-1]["score"] - history[max(0, len(history) - 4)]["score"]) / 3
    confidence = round(clip(0.55 + 0.4 * (n_months / 24) - rng.uniform(0, 0.2), 0.2, 0.97), 2)
    forecast = []
    for h in (1, 2, 3):
        q50 = clip(last + 0.6 * recent_slope * h)
        w = (2.5 + 1.8 * h) * (1.4 - confidence)
        forecast.append({"month": FORECAST_MONTHS[h - 1], "h": h, "q10": round(clip(q50 - w * 1.2), 1),
                         "q50": round(q50, 1), "q90": round(clip(q50 + w), 1)})
    d3 = {k: round(forecast[-1][k] - last, 1) for k in ("q10", "q50", "q90")}
    trend = "mejora" if d3["q50"] > 2.5 else ("deterioro" if d3["q50"] < -2.5 else "estable")

    # Alertas históricas
    alerts: list[dict[str, Any]] = []
    for t in range(3, n_months):
        d = history[t]["score"] - history[t - 3]["score"]
        m = history[t]["month"]
        if dip_at is not None and t == dip_at:
            alerts.append({"month": m, "type": "bache", "severity": "baja",
                           "text": f"Mes puntual flojo: el score cae {es(history[t - 1]['score'] - history[t]['score'])} pts "
                                   "pero liquidez y disciplina se mantienen; probable bache de caja."})
        elif drop_at is not None and t == drop_at + 2:
            alerts.append({"month": m, "type": "caida", "severity": "alta",
                           "text": f"Deterioro estructural: {es(d, sign=True)} pts en 3 meses con caída de cobros "
                                   "y aumento de retrasos a proveedores."})
        elif d <= -7 and not any(a["type"] == "deterioro" and a["month"] >= history[t - 3]["month"] for a in alerts):
            alerts.append({"month": m, "type": "deterioro", "severity": "alta" if d <= -10 else "media",
                           "text": f"El score baja {es(-d)} pts en 3 meses (de {es(history[t - 3]['score'])} a "
                                   f"{es(history[t]['score'])})."})
        elif d >= 7 and not any(a["type"] == "mejora" and a["month"] >= history[t - 3]["month"] for a in alerts):
            alerts.append({"month": m, "type": "mejora", "severity": "media" if d >= 10 else "baja",
                           "text": f"Mejora sostenida: {es(d, sign=True)} pts en 3 meses, impulsada por cobros y margen."})
    if rng.random() < 0.03:
        alerts.append({"month": LAST_MONTH, "type": "inactividad", "severity": "media",
                       "text": "Menos de 10 movimientos en el último mes: cuenta casi inactiva."})
    last_alerts = [a for a in alerts if a["month"] == LAST_MONTH]
    alert = last_alerts[0]["text"] if last_alerts else None

    # Explicación del último mes
    prev, now = history[-2], history[-1]
    delta = round(now["score"] - prev["score"], 1)
    raw = {}
    for f, meta in FEATURE_META.items():
        a, b = prev["features"][f], now["features"][f]
        if a is None or b is None:
            continue
        scale_f = {"runway_log": 0.3, "net_margin": 0.05, "inflow_growth": 0.1, "debt_coverage": 5,
                   "late_share_ap": 0.05, "late_share_ar": 0.05, "inflow_cv": 0.03}[f]
        raw[f] = meta["direction"] * (b - a) / scale_f
    tot = sum(raw.values()) or 1.0
    contribs = []
    for f, r in raw.items():
        pts = delta * r / tot if abs(tot) > 0.3 else r * 0.5
        a, b = prev["features"][f], now["features"][f]
        meta = FEATURE_META[f]
        contribs.append({"feature": f, "label": meta["label"], "pillar": meta["pillar"],
                         "delta_points": round(pts, 2), "value_prev": a, "value_now": b,
                         "text": f"{meta['label']} {es(a, 2)} → {es(b, 2)}: {es(pts, sign=True)} pts"})
    contribs.sort(key=lambda c: -abs(c["delta_points"]))
    top = contribs[0]["label"].lower() if contribs else "el conjunto de señales"
    verb = "sube" if delta > 0 else ("baja" if delta < 0 else "se mantiene")
    summary = (f"El score {verb} {es(abs(delta))} puntos frente a {prev['month']}, sobre todo por {top}."
               if delta else f"El score se mantiene estable; la señal que más se mueve es {top}.")

    company = {
        "company_id": cid, "group_id": f"GROUP_{i // 5 + 1:04d}", "currency": currency, "has_erp": has_erp,
        "n_months": n_months, "last_month": LAST_MONTH, "score": last, "band": band_of(last),
        "delta3_q10": d3["q10"], "delta3_q50": d3["q50"], "delta3_q90": d3["q90"], "trend": trend,
        "alert": alert, "dormant": any(a["type"] == "inactividad" for a in last_alerts), "confidence": confidence,
    }
    return {
        "company": {**company, "country": country, "erp": rng.choice(["sap", "holded", "a3", "sage", "odoo"])
                    if has_erp else None},
        "history": history, "forecast": forecast,
        "explanation": {"month": now["month"], "prev_month": prev["month"], "delta": delta,
                        "contributions": contribs, "summary_text": summary},
        "alerts": alerts, "pillar_weights": PILLAR_WEIGHTS, "feature_meta": FEATURE_META,
        "_summary": company,
    }


DB = {f"COMP_{i + 1:04d}": build_company(i) for i in range(N_COMPANIES)}

app = FastAPI(title="X-Ray mock")


@app.get("/api/companies")
def companies() -> dict:
    return {"companies": [c["_summary"] for c in DB.values()]}


@app.get("/api/company/{company_id}")
def company(company_id: str) -> dict:
    c = DB.get(company_id)
    if c is None:
        raise HTTPException(404, f"Empresa {company_id} no encontrada")
    return {k: v for k, v in c.items() if not k.startswith("_")}


@app.get("/api/company/{company_id}/treasury")
def treasury(company_id: str) -> dict:
    c = DB.get(company_id)
    if c is None:
        raise HTTPException(404, f"Empresa {company_id} no encontrada")
    rng = random.Random(company_id)
    erp = c["company"]["has_erp"]
    lim = rng.choice([0.0, 0.0, 2.0e5, 5.0e5])
    months = []
    for h in c["history"]:
        d = h["drivers"]
        drawn = round(lim * rng.uniform(0, 0.8), 2) if lim else None
        avail = round(lim - drawn, 2) if lim else None
        months.append({
            "month": h["month"], "inflow": d["inflow"], "outflow": d["outflow"], "net": round(d["inflow"] - d["outflow"], 2),
            "oper_in": round(d["inflow"] * 0.85, 2), "payroll": d["payroll"], "tax": round(d["outflow"] * 0.1, 2),
            "debt_service": d["debt_service"], "cash_end": d["cash_end"], "lc_drawn": drawn, "lc_limit": lim or None,
            "credit_available": avail, "liquidity": round(d["cash_end"] + (avail or 0), 2),
            "ar_issued": round(d["inflow"] * rng.uniform(0.8, 1.1), 2) if erp else None,
            "ap_issued": round(d["outflow"] * rng.uniform(0.5, 0.8), 2) if erp else None,
            "overdue_ar": d["overdue_ar"], "overdue_ap": d["overdue_ap"],
            "overdue_90_ar": round(d["overdue_ar"] * 0.3, 2) if erp else None,
            "overdue_90_ap": round(d["overdue_ap"] * 0.3, 2) if erp else None,
        })
    owed = round(rng.uniform(0, 8e5), 2)
    items = [{"type": "loan", "label": "Préstamos", "owed": owed, "granted": round(owed * 1.6, 2), "n_products": 2, "contingent": False}]
    if lim:
        items.append({"type": "lineofcredit", "label": "Pólizas de crédito", "owed": months[-1]["lc_drawn"], "granted": lim,
                      "n_products": 1, "contingent": False})
    return {"company": {"company_id": company_id, "group_id": c["company"]["group_id"], "currency": c["company"]["currency"],
                        "has_erp": erp, "last_month": months[-1]["month"]},
            "months": months,
            "debt": {"as_of": "2026-09-01", "items": items, "total_owed": round(sum(i["owed"] or 0 for i in items), 2)}}


@app.get("/api/scenario/drivers")
def scenario_drivers() -> dict:
    return {"drivers": DRIVERS, "months": {"min": 1, "max": 12, "default": 3}}


class ScenarioIn(BaseModel):
    company_id: str
    months: int = 3
    drivers: dict[str, float] = {}


def driver_points(key: str, value: float) -> float:
    d = DRIVER_BY_KEY[key]
    if d["kind"] == "mult":
        return DRIVER_COEF[key] * math.log(max(value, 0.05))
    return DRIVER_COEF[key] * value


@app.post("/api/scenario")
def scenario(req: ScenarioIn) -> dict:
    c = DB.get(req.company_id)
    if c is None:
        raise HTTPException(404, f"Empresa {req.company_id} no encontrada")
    drivers = {k: v for k, v in req.drivers.items() if k in DRIVER_BY_KEY}
    if not c["company"]["has_erp"]:
        drivers.pop("late_share_ap", None)
        drivers.pop("late_share_ar", None)
    hist = c["history"]
    months = max(1, min(12, req.months, len(hist)))
    # empresas débiles son algo más sensibles
    sens = 1.0 + (70 - hist[-1]["score"]) / 150
    pts = {k: driver_points(k, v) * sens for k, v in drivers.items()}
    full = sum(pts.values())
    base_hist = [{"month": h["month"], "score": h["score"]} for h in hist]
    scen_hist = []
    for idx, h in enumerate(hist):
        k = idx - (len(hist) - months) + 1  # 1..months en la ventana
        if k >= 1:
            ramp = 0.55 + 0.45 * k / months
            scen_hist.append({"month": h["month"], "score": round(clip(h["score"] + full * ramp), 1)})
        else:
            scen_hist.append({"month": h["month"], "score": h["score"]})
    delta_now = round(scen_hist[-1]["score"] - base_hist[-1]["score"], 1)
    base_fc = c["forecast"]
    scen_fc = []
    for f in base_fc:
        shift = delta_now * (1 + 0.12 * f["h"])
        widen = abs(delta_now) * 0.08 * f["h"]
        scen_fc.append({"month": f["month"], "h": f["h"], "q10": round(clip(f["q10"] + shift - widen), 1),
                        "q50": round(clip(f["q50"] + shift), 1), "q90": round(clip(f["q90"] + shift + widen), 1)})
    ratio = delta_now / full if abs(full) > 1e-9 else 0.0
    contribs = []
    for k, p in pts.items():
        d = DRIVER_BY_KEY[k]
        v = drivers[k]
        base_v = hist[-1]["drivers"].get(k)
        if d["kind"] == "mult":
            now_v = None if base_v is None else round(base_v * v, 3)
            lever = f"{d['label']} ×{es(v, 2)}"
        else:
            now_v = None if base_v is None else round(clip(base_v + v, 0, 1), 3)
            lever = f"{d['label']} {es(v * 100, 0, sign=True)} pp"
        contribs.append({"feature": k, "label": d["label"], "pillar": DRIVER_PILLAR[k],
                         "delta_points": round(p * ratio, 2), "value_prev": base_v, "value_now": now_v,
                         "text": f"{lever}: {es(p * ratio, sign=True)} pts"})
    contribs.sort(key=lambda x: -abs(x["delta_points"]))
    b0, b1 = band_of(base_hist[-1]["score"]), band_of(scen_hist[-1]["score"])
    alerts_after = []
    if scen_hist[-1]["score"] < 50 <= base_hist[-1]["score"] or delta_now <= -10:
        alerts_after.append({"month": LAST_MONTH, "type": "caida", "severity": "alta",
                             "text": f"El escenario provoca una caída de {es(-delta_now)} pts: pasa a {b1}."})
    elif delta_now <= -5:
        alerts_after.append({"month": LAST_MONTH, "type": "deterioro", "severity": "media",
                             "text": f"El escenario deteriora el score {es(-delta_now)} pts."})
    elif delta_now >= 7:
        alerts_after.append({"month": LAST_MONTH, "type": "mejora", "severity": "baja",
                             "text": f"El escenario mejora el score {es(delta_now, sign=True)} pts."})
    if not drivers:
        summary = "Sin cambios: el escenario coincide con la situación base."
    else:
        main = contribs[0]["text"].split(":")[0]
        summary = (f"En este escenario el score de {LAST_MONTH} pasaría de {es(base_hist[-1]['score'])} a "
                   f"{es(scen_hist[-1]['score'])} ({es(delta_now, sign=True)} pts)"
                   + (f" y la empresa pasaría de «{b0}» a «{b1}»" if b0 != b1 else f"; sigue en «{b1}»")
                   + f". Palanca principal: {main}.")
    return {
        "baseline": {"history": base_hist, "forecast": base_fc},
        "scenario": {"history": scen_hist, "forecast": scen_fc},
        "band_before": b0, "band_after": b1, "delta_now": delta_now,
        "contributions": contribs, "summary_text": summary, "alerts_after": alerts_after,
    }


@app.get("/api/monitor")
def monitor() -> dict:
    out = []
    for c in DB.values():
        for a in c["alerts"]:
            if a["month"] == LAST_MONTH:
                out.append({"company_id": c["company"]["company_id"], **a, "score": c["company"]["score"],
                            "delta3_q50": c["company"]["delta3_q50"]})
    return {"month": LAST_MONTH, "alerts": out}


ITERATIONS = [
    {"tag": "v1", "description": "Score por reglas: runway, margen y retrasos con pesos a mano.",
     "metrics": {"mae_h3": 7.9, "spearman_h3": 0.41, "auc_deterioro": 0.66, "auc_mejora": 0.58,
                 "anticipacion_meses": 0.8, "falsas_alarmas_bache": 0.41}},
    {"tag": "v2", "description": "Pilares normalizados por percentil dentro del sector y tamaño.",
     "metrics": {"mae_h3": 6.8, "spearman_h3": 0.52, "auc_deterioro": 0.72, "auc_mejora": 0.66,
                 "anticipacion_meses": 1.2, "falsas_alarmas_bache": 0.33}},
    {"tag": "v3", "description": "Suavizado EWMA del score y detector de bache frente a caída.",
     "metrics": {"mae_h3": 6.1, "spearman_h3": 0.58, "auc_deterioro": 0.75, "auc_mejora": 0.71,
                 "anticipacion_meses": 1.6, "falsas_alarmas_bache": 0.19}},
    {"tag": "v4", "description": "LightGBM cuantílico para la previsión a 3 meses (q10/q50/q90).",
     "metrics": {"mae_h3": 5.2, "spearman_h3": 0.66, "auc_deterioro": 0.81, "auc_mejora": 0.77,
                 "anticipacion_meses": 2.1, "falsas_alarmas_bache": 0.17}},
    {"tag": "v5", "description": "Validación por grupo empresarial y calibración de la cobertura de los cuantiles.",
     "metrics": {"mae_h3": 5.4, "spearman_h3": 0.64, "auc_deterioro": 0.80, "auc_mejora": 0.78,
                 "anticipacion_meses": 2.3, "falsas_alarmas_bache": 0.15, "cobertura_q10_q90": 0.79}},
]


_rng_scatter = random.Random(7)
_SCATTER_X = [_rng_scatter.gauss(0, 7) for _ in range(120)]


@app.get("/api/metrics")
def metrics() -> dict:
    tags = [it["tag"] for it in ITERATIONS]
    return {
        "iterations": ITERATIONS,
        "final": ITERATIONS[-1]["metrics"],
        "charts": [
            {"type": "line", "title": "Error de previsión a 3 meses por iteración", "x_label": "Iteración",
             "y_label": "MAE (puntos de score)", "labels": tags,
             "datasets": [{"label": "MAE h=3", "data": [it["metrics"]["mae_h3"] for it in ITERATIONS]}],
             "note": "v5 sube algo el MAE porque deja de filtrar información entre empresas del mismo grupo."},
            {"type": "bar", "title": "Capacidad de detección en las dos direcciones", "x_label": "Iteración",
             "y_label": "AUC", "labels": tags,
             "datasets": [{"label": "Deterioro", "data": [it["metrics"]["auc_deterioro"] for it in ITERATIONS]},
                          {"label": "Mejora", "data": [it["metrics"]["auc_mejora"] for it in ITERATIONS]}]},
            {"type": "scatter", "title": "Previsto frente a real (h=3, validación)", "x_label": "Δ previsto (q50)",
             "y_label": "Δ real",
             "datasets": [{"label": "Empresas", "data": [
                 {"x": round(x, 1), "y": round(x * 0.8 + random.Random(k).gauss(0, 4), 1)}
                 for k, x in enumerate(_SCATTER_X)]}],
             "note": "Cada punto es una empresa de validación (particiones por grupo)."},
        ],
    }


DECISIONS = [
    {"id": "D01", "category": "datos", "title": "Reconstruir saldos hacia atrás",
     "question": "¿Cómo obtenemos la caja mensual si balances.csv solo trae la foto final?",
     "decision": "Partimos del saldo a 1 de septiembre de 2026 y restamos los movimientos mes a mes hacia atrás.",
     "why": "Es la única forma de tener liquidez histórica sin inventar datos.",
     "alternatives": "Usar solo flujos (sin nivel de caja); imputar saldos con la mediana del sector.",
     "evidence": "El 97 % de las cuentas cuadra con diferencias < 1 % en los meses con extractos completos.",
     "status": "decidido", "chart": None},
    {"id": "D02", "category": "datos", "title": "Normalizar a euros",
     "question": "¿Cómo agregamos importes en varias monedas?",
     "decision": "Convertimos a EUR con el tipo medio mensual del BCE y usamos ratios siempre que se pueda.",
     "why": "Los ratios no dependen de la moneda; la conversión solo afecta a los tamaños absolutos.",
     "alternatives": "Trabajar solo con empresas en EUR.", "evidence": "Un 11 % de las empresas opera en otra moneda.",
     "status": "decidido",
     "chart": {"type": "bar", "title": "Empresas por moneda", "x_label": "Moneda", "y_label": "Empresas",
               "labels": ["EUR", "GBP", "MXN", "USD"], "datasets": [{"label": "Empresas", "data": [1144, 61, 48, 33]}]}},
    {"id": "D03", "category": "score", "title": "Cinco pilares ponderados",
     "question": "¿Cómo hacemos el score explicable?",
     "decision": "Score = media ponderada de cinco pilares (liquidez, rentabilidad, solvencia, disciplina y estabilidad).",
     "why": "Cada punto del score se puede atribuir a un pilar y a una señal concreta.",
     "alternatives": "Un único modelo de caja negra con SHAP a posteriori.",
     "evidence": "Los pilares explican el 92 % de la varianza del score en validación.", "status": "decidido",
     "chart": {"type": "bar", "title": "Peso de cada pilar", "x_label": "Pilar", "y_label": "Peso",
               "labels": ["Liquidez", "Rentabilidad", "Solvencia", "Disciplina", "Estabilidad"],
               "datasets": [{"label": "Peso", "data": [0.30, 0.20, 0.20, 0.15, 0.15]}]}},
    {"id": "D04", "category": "score", "title": "Separar bache de caída",
     "question": "¿Cómo evitamos alarmas por un mal mes de caja?",
     "decision": "Un descenso es «caída» solo si persiste dos meses y afecta a más de un pilar; si no, es «bache».",
     "why": "Los compradores (riesgo, tesorería) penalizan mucho las falsas alarmas.",
     "alternatives": "Umbral fijo sobre el score mensual.", "evidence": "Reduce falsas alarmas del 41 % al 15 %.",
     "status": "decidido",
     "chart": {"type": "line", "title": "Falsas alarmas por bache", "x_label": "Iteración", "y_label": "Proporción",
               "labels": ["v1", "v2", "v3", "v4", "v5"],
               "datasets": [{"label": "Falsas alarmas", "data": [0.41, 0.33, 0.19, 0.17, 0.15]}]}},
    {"id": "D05", "category": "modelo", "title": "Previsión cuantílica a 3 meses",
     "question": "¿Cómo mostramos hacia dónde va la empresa y no solo su foto?",
     "decision": "LightGBM cuantílico (q10, q50, q90) sobre el cambio del score a 1, 2 y 3 meses.",
     "why": "El abanico comunica incertidumbre y permite ordenar por riesgo de empeorar.",
     "alternatives": "ARIMA por empresa; regresión lineal sobre la pendiente.",
     "evidence": "MAE h=3 de 5,4 pts frente a 7,9 con la extrapolación lineal.", "status": "decidido", "chart": None},
    {"id": "D06", "category": "validación", "title": "Particiones por grupo empresarial",
     "question": "¿Cómo evitamos que se filtre información entre train y validación?",
     "decision": "GroupKFold por group_id: todas las empresas de un grupo caen en la misma partición.",
     "why": "Las empresas de un grupo comparten clientes y se mueven juntas.",
     "alternatives": "KFold por company_id; partición temporal.",
     "evidence": "Con KFold por empresa el AUC se inflaba 0,06 puntos.", "status": "decidido",
     "chart": {"type": "scatter", "title": "AUC por fold: grupo frente a empresa", "x_label": "AUC con KFold por empresa",
               "y_label": "AUC con GroupKFold",
               "datasets": [{"label": "Folds", "data": [{"x": 0.86, "y": 0.80}, {"x": 0.85, "y": 0.79},
                                                         {"x": 0.87, "y": 0.81}, {"x": 0.84, "y": 0.78},
                                                         {"x": 0.86, "y": 0.82}]}]}},
    {"id": "D07", "category": "validación", "title": "¿Score por empresa o por grupo?",
     "question": "¿El test oculto se evalúa por company_id o por grupo empresarial?",
     "decision": "Calculamos el score por empresa y ofrecemos un agregado por grupo ponderado por volumen.",
     "why": "El enunciado habla de 250 empresas pero el dataset tiene 1.286 empresas en 250 grupos.",
     "alternatives": "Solo por grupo.", "evidence": "Pendiente de la respuesta de la organización.",
     "status": "a confirmar con la organización", "chart": None},
    {"id": "D08", "category": "producto", "title": "Comprador: Embat",
     "question": "¿Quién paga y por qué le sale a cuenta?",
     "decision": "Embat integra X-Ray como módulo premium de tesorería y como motor de preconcesión de circulante.",
     "why": "Ya tiene los datos y la relación con la pyme; convierte el score en ingresos recurrentes.",
     "alternatives": "Vender a bancos o aseguradoras de crédito directamente.",
     "evidence": "Escenarios «qué pasaría si» son la función más usada en las entrevistas con tesoreros.",
     "status": "decidido", "chart": None},
    {"id": "D09", "category": "ood", "title": "Empresas con poco historial",
     "question": "¿Qué hacemos con empresas con menos de 12 meses de datos?",
     "decision": "Mostramos el score con confianza reducida y abanico más ancho.",
     "why": "Es mejor avisar de la incertidumbre que ocultar la empresa.",
     "alternatives": "Excluirlas del score.", "evidence": "El 14 % de las empresas tiene menos de 24 meses.",
     "status": "decidido", "chart": None},
    {"id": "D10", "category": "ood", "title": "Formato del leaderboard",
     "question": "¿Qué formato de predicción pide el leaderboard?",
     "decision": "Preparamos un CSV company_id, month, score, band, delta3_q50.",
     "why": "Cubre las necesidades más probables del jurado.",
     "alternatives": "JSON por empresa.", "evidence": "El PDF no lo especifica.",
     "status": "a confirmar con la organización", "chart": None},
]


@app.get("/api/decisions")
def decisions() -> dict:
    return {"decisions": DECISIONS}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
