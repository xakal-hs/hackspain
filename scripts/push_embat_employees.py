"""Merge data/embat_am.csv + data/embat_cs.csv into public.embat_employees
on the frontend Supabase project (frontend/.env).

    python3 scripts/push_embat_employees.py

Raw CSVs stay untouched. Exact duplicate rows are dropped on ai_full_name.
Creates embat_employees + embat_leads (CRM) so Equipo and Financiación
read real comerciales instead of seed names.
"""

from __future__ import annotations

import csv
import json
import os
import uuid
from pathlib import Path
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "supabase" / "embat_employees_schema.sql"
SOURCES = (
    (ROOT / "data" / "embat_am.csv", "account_management"),
    (ROOT / "data" / "embat_cs.csv", "customer_success"),
)
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://xray.embat/embat_employees")


def log(message: str) -> None:
    print(message, flush=True)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def frontend_conf() -> tuple[str, str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    if not url or not key:
        raise SystemExit("Faltan SUPABASE_URL / SUPABASE_SECRET_KEY en frontend/.env")
    host = url.split("//", 1)[-1].split(".", 1)[0]
    return url, key, host


def truthy(value: str) -> bool:
    return value.strip() in {"✅", "true", "True", "1", "yes", "YES"}


def rows_from_csv() -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    skipped_dupes = 0
    for path, team in SOURCES:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                ai_full = (raw.get("Use AI Full Name") or raw.get("Full Name") or "").strip()
                if not ai_full:
                    continue
                if ai_full in merged:
                    skipped_dupes += 1
                    continue
                merged[ai_full] = {
                    "id": str(uuid.uuid5(NS, ai_full)),
                    "first_name": (raw.get("First Name") or "").strip(),
                    "last_name": (raw.get("Last Name") or "").strip(),
                    "full_name": (raw.get("Full Name") or ai_full).strip(),
                    "job_title": (raw.get("Job Title") or "").strip(),
                    "company": (raw.get("Company") or "").strip(),
                    "non_investor_check": truthy(raw.get("Non-Investor Check") or ""),
                    "sales_role": (raw.get("Sales Role") or "").strip() or None,
                    "ai_full_name": ai_full,
                    "ai_job_title": (raw.get("Use AI Job Title") or raw.get("Job Title") or "").strip(),
                    "standardized_role": (raw.get("Use AI Standardized Role") or "").strip(),
                    "team": team,
                }
    log(f"Filas únicas={len(merged)}  duplicados={skipped_dupes}")
    return list(merged.values())


def rest(url: str, key: str, method: str, path: str, body=None, extra: dict | None = None):
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Prefer": "return=representation,resolution=merge-duplicates",
    }
    if extra:
        headers.update(extra)
    data = None if body is None else json.dumps(body).encode()
    req = request.Request(f"{url}{path}", data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=60) as response:
            payload = response.read()
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {path} -> {exc.code}: {detail[:800]}") from exc
    if not payload:
        return None
    return json.loads(payload)


def table_exists(url: str, key: str, name: str) -> bool:
    try:
        rest(url, key, "GET", f"/rest/v1/{name}?select=id&limit=1", extra={"Prefer": "count=exact"})
        return True
    except SystemExit as exc:
        if "PGRST205" in str(exc) or "Could not find the table" in str(exc):
            return False
        raise


def apply_schema_via_management(ref: str) -> bool:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from push_supabase import access_token
    except Exception:
        return False
    token = access_token()
    sql = SCHEMA.read_text(encoding="utf-8")
    payload = json.dumps({"query": sql}).encode()
    req = request.Request(
        f"https://api.supabase.com/v1/projects/{ref}/database/query",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with request.urlopen(req, timeout=60) as response:
            response.read()
        log(f"Schema aplicado vía Management API en {ref}")
        return True
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:240]
        log(f"Management API no puede tocar {ref}: {exc.code} {detail}")
        return False


def upsert_employees(url: str, key: str, rows: list[dict[str, object]]) -> None:
    rest(
        url,
        key,
        "POST",
        "/rest/v1/embat_employees?on_conflict=id",
        rows,
    )


def sample(url: str, key: str) -> None:
    rows = rest(
        url,
        key,
        "GET",
        "/rest/v1/embat_employees?select=team,id&limit=100",
    ) or []
    am = sum(1 for row in rows if row["team"] == "account_management")
    cs = sum(1 for row in rows if row["team"] == "customer_success")
    log(f"  account_management={am}  customer_success={cs}  total={len(rows)}")


def main() -> None:
    load_env(ROOT / "frontend" / ".env")
    url, key, ref = frontend_conf()
    log(f"Proyecto frontend {ref}  {url}")
    rows = rows_from_csv()
    if not rows:
        raise SystemExit("No hay filas que cargar.")

    if not table_exists(url, key, "embat_employees"):
        if not apply_schema_via_management(ref):
            raise SystemExit(
                "embat_employees no existe en el Supabase del frontend y este "
                "login de CLI no tiene permiso para crear tablas ahí. "
                f"Pega {SCHEMA.relative_to(ROOT)} en SQL Editor: "
                f"https://supabase.com/dashboard/project/{ref}/sql/new"
            )

    upsert_employees(url, key, rows)
    sample(url, key)


if __name__ == "__main__":
    main()
