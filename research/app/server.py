"""Backend real de X-Ray: el modelo como servicio detrás de la SPA.

    cd research && uv run uvicorn app.server:app --port 8000
    # abrir http://localhost:8000

Contrato en app/API_CONTRACT.md. Al arrancar carga artifacts/xray.joblib (o entrena si no existe)
y precalcula scores, previsiones y alertas de todas las empresas del train.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from service import XRayService, SCENARIO_DRIVERS  # noqa: E402

app = FastAPI(title="X-Ray API", version="1.0")
svc: XRayService | None = None


def service() -> XRayService:
    global svc
    if svc is None:
        svc = XRayService()
    return svc


@app.on_event("startup")
def _warm():
    service()


class ScenarioIn(BaseModel):
    company_id: str
    months: int = Field(3, ge=1, le=24)
    drivers: dict[str, float] = {}


def _read_json(name: str) -> dict:
    p = ROOT / "reports" / name
    return json.loads(p.read_text()) if p.exists() else {}


@app.get("/api/companies")
def companies():
    return service().companies()


@app.get("/api/company/{cid}")
def company(cid: str):
    try:
        return service().company(cid)
    except KeyError:
        raise HTTPException(404, f"Empresa {cid} no encontrada")


@app.get("/api/company/{cid}/treasury")
def treasury(cid: str):
    try:
        return service().treasury(cid)
    except KeyError:
        raise HTTPException(404, f"Empresa {cid} no encontrada")


@app.get("/api/scenario/drivers")
def drivers():
    return {"drivers": SCENARIO_DRIVERS, "months": {"min": 1, "max": 12, "default": 3}}


@app.post("/api/scenario")
def scenario(body: ScenarioIn):
    valid = {d["key"] for d in SCENARIO_DRIVERS}
    unknown = set(body.drivers) - valid
    if unknown:
        raise HTTPException(422, f"Drivers desconocidos: {sorted(unknown)}")
    try:
        return service().scenario(body.company_id, body.months, body.drivers)
    except KeyError:
        raise HTTPException(404, f"Empresa {body.company_id} no encontrada")


@app.get("/api/monitor")
def monitor():
    return service().monitor()


@app.get("/api/metrics")
def metrics():
    return _read_json("metrics_app.json") or {"iterations": [], "final": {}, "charts": []}


@app.get("/api/decisions")
def decisions():
    return _read_json("decisions.json") or {"decisions": []}


@app.get("/api/products/collection")
def products_collection():
    """Todos los productos para todas las empresas (vista de cartera de productos)."""
    svc_obj = service()
    scored = svc_obj.scored
    feats = svc_obj.feats
    comp = svc_obj.comp

    all_recs = []
    for cid in sorted(scored.company_id.unique()):
        if cid not in comp.index:
            continue
        try:
            s_rows = scored[scored.company_id == cid].sort_values("month")
            latest_scored = s_rows.iloc[-1] if len(s_rows) else None
            f_rows = feats[feats.company_id == cid].sort_values("month")
            latest_feats = f_rows.iloc[-1] if len(f_rows) else None

            if latest_scored is not None and latest_feats is not None:
                rec = _product_recommendations(latest_feats, latest_scored, cid)
                if rec:
                    all_recs.append(rec)
        except Exception:
            continue

    return {
        "recommendations": all_recs,
        "summary": {
            "total_companies": len(all_recs),
            "total_yield_products": sum(1 for r in all_recs if any(p["id"] == "yield" for p in r.get("products", []))),
            "total_reserve_products": sum(1 for r in all_recs if any(p["id"] == "reserve" for p in r.get("products", []))),
            "total_fx_products": sum(1 for r in all_recs if any(p["id"] == "fx" for p in r.get("products", []))),
            "total_factoring_products": sum(1 for r in all_recs if any(p["id"] == "factoring" for p in r.get("products", []))),
            "total_credit_products": sum(1 for r in all_recs if any(p["id"] == "credit" for p in r.get("products", []))),
        },
    }


@app.get("/api/products/{cid}")
def product_for_company(cid: str):
    """Productos recomendados para una empresa concreta."""
    svc_obj = service()
    scored = svc_obj.scored
    feats = svc_obj.feats
    comp = svc_obj.comp

    if cid not in comp.index:
        raise HTTPException(404, f"Empresa {cid} no encontrada")

    try:
        s_rows = scored[scored.company_id == cid].sort_values("month")
        latest_scored = s_rows.iloc[-1] if len(s_rows) else None
        f_rows = feats[feats.company_id == cid].sort_values("month")
        latest_feats = f_rows.iloc[-1] if len(f_rows) else None

        if latest_scored is None or latest_feats is None:
            raise HTTPException(404, f"No hay datos suficientes para {cid}")

        return _product_recommendations(latest_feats, latest_scored, cid)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/products/adoption")
def product_adoption():
    """Simulador de adopción: ingresos potenciales según tasa de adopción."""
    svc_obj = service()
    scored = svc_obj.scored
    feats = svc_obj.feats
    comp = svc_obj.comp

    product_totals = {p["id"]: {"count": 0, "annual_revenue": 0} for p in PRODUCT_DEFS}

    for cid in sorted(scored.company_id.unique()):
        if cid not in comp.index:
            continue
        try:
            s_rows = scored[scored.company_id == cid].sort_values("month")
            latest_scored = s_rows.iloc[-1] if len(s_rows) else None
            f_rows = feats[feats.company_id == cid].sort_values("month")
            latest_feats = f_rows.iloc[-1] if len(f_rows) else None

            if latest_scored is None or latest_feats is None:
                continue

            recs = _product_recommendations(latest_feats, latest_scored, cid)
            if recs:
                for p in recs.get("products", []):
                    pid = p["id"]
                    if pid in product_totals:
                        product_totals[pid]["count"] += 1
                        product_totals[pid]["annual_revenue"] += p.get("commission", 0) + p.get("annual_yield", 0)
        except Exception:
            continue

    adoptions = {}
    for rate in [0.25, 0.35, 0.45, 0.55, 0.65]:
        total = 0
        by_product = {}
        for pid, data in product_totals.items():
            count_at_rate = max(1, round(data["count"] * rate))
            rev_at_rate = data["annual_revenue"] * rate
            total += rev_at_rate
            by_product[pid] = {
                "count": count_at_rate,
                "annual_revenue": round(rev_at_rate, 2),
            }
        adoptions[str(int(rate * 100))] = {
            "rate": rate,
            "total_annual_revenue": round(total, 2),
            "by_product": by_product,
        }

    return {
        "adoptions": adoptions,
        "product_totals": {pid: {k: round(v, 2) if isinstance(v, float) else v for k, v in data.items()}
                          for pid, data in product_totals.items()},
        "total_companies": len(set(scored.company_id.unique()) & set(comp.index)),
    }


STATIC = ROOT / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})
