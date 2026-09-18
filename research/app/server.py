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


STATIC = ROOT / "app" / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})
