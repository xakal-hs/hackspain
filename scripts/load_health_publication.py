"""Carga en Supabase la publicación ya calculada por X-Ray.

Antes: ejecutar ``supabase/health_schema.sql`` y generar los CSV con:
``cd research && uv run python src/export_health_publication.py --out ../supabase/export``.

La clave de servicio se lee solo desde .env y nunca se envía al navegador.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BATCH = 2_000
TABLES = ("company_health_monthly", "company_health_driver_monthly", "company_business_profile")
CONFLICT_KEYS = {
    "company_health_monthly": "company_id,month",
    "company_health_driver_monthly": "company_id,month,feature,score_version",
    "company_business_profile": "company_id",
}


def env() -> dict[str, str]:
    values = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values.setdefault(key, value.strip().strip("'\""))
    return values


def convert(row: dict[str, str]) -> dict:
    converted = {key: (None if value == "" else value) for key, value in row.items()}
    if converted.get("risk_flags") is not None:
        converted["risk_flags"] = json.loads(converted["risk_flags"])
    if converted.get("sector_set") is not None:
        converted["sector_set"] = json.loads(converted["sector_set"])
    for key in ("health_score", "score_delta_3m", "coverage", "confidence", "ood_share", "contribution",
                "liquidez_score", "rentabilidad_score", "solvencia_score", "disciplina_score", "estabilidad_score", "raw_value",
                "top_sector_score", "profile_confidence"):
        if converted.get(key) is not None:
            converted[key] = float(converted[key])
    return converted


def upload(table: str, url: str, key: str, directory: Path) -> None:
    path = directory / f"{table}.csv"
    if not path.exists():
        raise SystemExit(f"Falta {path}; genera primero la publicación X-Ray.")
    endpoint = f"{url.rstrip('/')}/rest/v1/{table}?on_conflict={CONFLICT_KEYS[table]}"
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    count, batch = 0, []
    with path.open(newline="") as source:
        for row in csv.DictReader(source):
            batch.append(convert(row))
            if len(batch) == BATCH:
                _push(endpoint, headers, batch, table); count += len(batch); batch = []
    if batch:
        _push(endpoint, headers, batch, table); count += len(batch)
    print(f"{table}: {count} filas")


def _push(endpoint: str, headers: dict, batch: list[dict], table: str) -> None:
    response = requests.post(endpoint, headers=headers, json=batch, timeout=120)
    if not response.ok:
        raise SystemExit(f"{table}: HTTP {response.status_code} {response.text[:400]}")


if __name__ == "__main__":
    settings = env()
    url, key = settings.get("SUPABASE_URL"), settings.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        sys.exit("Faltan SUPABASE_URL y SUPABASE_SECRET_KEY en .env.")
    out = ROOT / "supabase" / "export"
    for table in sys.argv[1:] or TABLES:
        if table not in TABLES:
            sys.exit(f"Tabla no permitida: {table}")
        upload(table, url, key, out)
