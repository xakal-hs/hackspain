"""Carga en Supabase la decisión del prestamista y el catálogo del modelo.

Antes: ejecutar ``supabase/decision_schema.sql`` y generar los ficheros con
``python3 scripts/export_decision_publication.py``.

La clave de servicio se lee solo desde .env y nunca se envía al navegador.

    python3 scripts/load_decision_publication.py                            # todo
    python3 scripts/load_decision_publication.py company_decision_monthly   # solo una
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from load_health_publication import env  # noqa: E402  (mismo .env, mismo contrato)

BATCH = 2_000
TABLES = ("company_decision_monthly", "score_catalog")
CONFLICT_KEYS = {
    "company_decision_monthly": "company_id,month",
    "score_catalog": "score_version",
}
JSON_COLUMNS = ("vetos", "avisos", "razones")


def convert(row: dict[str, str]) -> dict:
    converted = {key: (None if value == "" else value) for key, value in row.items()}
    for key in JSON_COLUMNS:
        if converted.get(key) is not None:
            converted[key] = json.loads(converted[key])
    if converted.get("importe_max_meses") is not None:
        converted["importe_max_meses"] = float(converted["importe_max_meses"])
    return converted


def rows_of(table: str, directory: Path) -> list[dict]:
    """El catálogo es un JSON de una fila; la decisión, un CSV por empresa-mes."""
    if table == "score_catalog":
        path = directory / "score_catalog.json"
        if not path.exists():
            raise SystemExit(f"Falta {path}; ejecuta antes scripts/export_decision_publication.py.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [{"score_version": payload["score_version"], "payload": payload}]

    path = directory / f"{table}.csv"
    if not path.exists():
        raise SystemExit(f"Falta {path}; ejecuta antes scripts/export_decision_publication.py.")
    with path.open(newline="", encoding="utf-8") as source:
        return [convert(row) for row in csv.DictReader(source)]


def upload(table: str, url: str, key: str, directory: Path) -> None:
    endpoint = f"{url.rstrip('/')}/rest/v1/{table}?on_conflict={CONFLICT_KEYS[table]}"
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    rows = rows_of(table, directory)
    for start in range(0, len(rows), BATCH):
        batch = rows[start:start + BATCH]
        response = requests.post(endpoint, headers=headers, json=batch, timeout=120)
        if not response.ok:
            raise SystemExit(f"{table}: HTTP {response.status_code} {response.text[:400]}")
    print(f"{table}: {len(rows)} filas")


if __name__ == "__main__":
    settings = env()
    supabase_url, secret = settings.get("SUPABASE_URL"), settings.get("SUPABASE_SECRET_KEY")
    if not supabase_url or not secret:
        sys.exit("Faltan SUPABASE_URL y SUPABASE_SECRET_KEY en .env.")
    out = ROOT / "supabase" / "export"
    for name in sys.argv[1:] or TABLES:
        if name not in TABLES:
            sys.exit(f"Tabla no permitida: {name}")
        upload(name, supabase_url, secret, out)
