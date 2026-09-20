"""Push mapped X-Ray CSVs into the private `xray` schema on Supabase.

    python3 scripts/push_supabase.py
    python3 scripts/push_supabase.py --all    # include invoices + transactions

Mapping stays in DuckDB (`src/mapping`); raw CSVs are never rewritten. Prefer
DuckDB COPY over the session pooler; if port 5432/6543 is blocked, fall back to
batched `json_populate_recordset` on the Management API (HTTPS).

On a Free plan (500 MB cap) invoices and transactions are skipped unless
`--all` or `XRAY_FORCE_LARGE_TABLES=1`.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import math
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_REF = "eisukkwjjyatitoyatuy"
MIGRATION = ROOT / "supabase" / "migrations" / "20260919141521_xray_schema.sql"
LARGE_TABLES = frozenset({"invoices", "transactions"})

TABLES: dict[str, tuple[str, ...]] = {
    "groups": (
        "group_id",
        "erp_raw",
        "erp_code",
        "erp_label",
        "erp",
        "n_companies_in_sample",
        "dq_erp_unmapped",
    ),
    "companies": (
        "company_id",
        "group_id",
        "country_raw",
        "country",
        "currency",
        "erp_raw",
        "erp_code",
        "erp_label",
        "erp",
        "created_at",
        "observation_start",
        "has_checking",
        "has_invoices",
        "erp_connected",
        "balance_missing",
        "dq_country_unmapped",
        "dq_erp_unmapped",
    ),
    "banking_products": (
        "product_id",
        "company_id",
        "label",
        "type",
        "type_family",
        "bank_name_raw",
        "bank_name",
        "service_raw",
        "service",
        "currency",
        "created_at",
        "connected_after_cutoff",
        "observation_start",
        "service_kind",
    ),
    "debt_products": (
        "product_id",
        "company_id",
        "label",
        "type",
        "type_family",
        "bank_name_raw",
        "bank_name",
        "service_raw",
        "service",
        "service_kind",
        "currency",
        "created_at",
        "granted",
        "outstanding",
        "granted_raw",
        "outstanding_raw",
        "granted_liability",
        "outstanding_liability",
        "liquidity",
        "connected_after_cutoff",
        "observation_start",
        "dq_positive_outstanding",
        "dq_granted_outstanding_sign_mismatch",
        "dq_outstanding_exceeds_granted",
    ),
    "debt_schedule_config": (
        "product_id",
        "company_id",
        "settlement_product_id_raw",
        "settlement_product_id",
        "dq_settlement_orphan",
        "currency",
        "amortization_type_raw",
        "amortization_type",
        "interest_calc_method",
        "amortising_frequency_raw",
        "amortising_frequency",
        "granted_balance",
        "outstanding_balance",
        "total_periods",
        "next_payment_date",
        "last_payment_date",
        "annual_interest_rate_or_spread",
        "interest_type",
        "dq_schedule_amount_mismatch",
    ),
    "balances": (
        "product_id",
        "company_id",
        "date",
        "balance",
        "available",
        "granted",
        "liquidity",
        "countable",
        "balance_quality",
        "dq_balance_suspect",
    ),
    "products": (
        "product_id",
        "company_id",
        "product_class",
        "type",
        "currency",
        "created_at",
        "catalog_status",
    ),
    "invoices": (
        "operation_id",
        "company_id",
        "document_type",
        "issuance_date",
        "due_date",
        "payment_date",
        "payment_date_raw",
        "payment_date_was_due_alias",
        "amount",
        "pending_amount",
        "currency",
        "accounting_currency",
        "exchange_rate",
        "exchange_rate_raw",
        "status",
        "status_raw",
        "concept",
        "counterparty_id",
        "counterparty_id_raw",
        "dq_due_before_issuance",
        "dq_paid_before_issuance",
        "dq_pending_exceeds_amount",
        "dq_pending_sign_mismatch",
    ),
    "transactions": (
        "transaction_id",
        "company_id",
        "product_id",
        "date",
        "value_date_raw",
        "value_date_clean",
        "amount",
        "exchange_rate_raw",
        "exchange_rate",
        "status",
        "accounting_status",
        "category_raw",
        "category",
        "description",
        "counterparty_id_raw",
        "counterparty_id",
    ),
}

INDEXES = (
    "create index if not exists companies_group_id_idx on xray.companies (group_id)",
    "create index if not exists banking_products_company_id_idx on xray.banking_products (company_id)",
    "create index if not exists debt_products_company_id_idx on xray.debt_products (company_id)",
    "create index if not exists balances_company_id_idx on xray.balances (company_id)",
    "create index if not exists products_company_id_idx on xray.products (company_id)",
    "create index if not exists invoices_company_id_idx on xray.invoices (company_id)",
    "create index if not exists invoices_issuance_date_idx on xray.invoices (issuance_date)",
    "create index if not exists transactions_company_id_idx on xray.transactions (company_id)",
    "create index if not exists transactions_product_id_idx on xray.transactions (product_id)",
    "create index if not exists transactions_date_idx on xray.transactions (date)",
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key, value = key.strip(), value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def project_ref() -> str:
    return os.environ.get("SUPABASE_PROJECT_REF", DEFAULT_REF)


def access_token() -> str:
    env = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if env:
        return env
    try:
        raw = subprocess.check_output(
            [
                "security",
                "find-generic-password",
                "-s",
                "Supabase CLI",
                "-a",
                "access-token",
                "-w",
            ],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "No SUPABASE_ACCESS_TOKEN and no `supabase login` token in the keychain."
        ) from exc
    if raw.startswith("go-keyring-base64:"):
        return base64.b64decode(raw.split(":", 1)[1]).decode()
    return raw


def api(method: str, path: str, body: dict | None = None, timeout: int = 60):
    token = access_token()
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"https://api.supabase.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {path} -> {exc.code}: {detail[:800]}") from exc
    if not payload:
        return None
    return json.loads(payload)


def run_sql(sql: str, timeout: int = 120):
    return api(
        "POST",
        f"/v1/projects/{project_ref()}/database/query",
        {"query": sql},
        timeout=timeout,
    )


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def org_plan() -> str:
    project = api("GET", f"/v1/projects/{project_ref()}")
    org_id = project["organization_id"]
    org = api("GET", f"/v1/organizations/{org_id}")
    return str(org.get("plan") or "free").lower()


def schema_ready() -> bool:
    rows = run_sql("select to_regclass('xray.groups') is not null as ok")
    return bool(rows and rows[0]["ok"])


def log(message: str) -> None:
    print(message, flush=True)


def apply_migration() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    run_sql(sql, timeout=120)
    log(f"Aplicada {MIGRATION.name}")


def ensure_loader(password: str) -> None:
    role = "xray_loader"
    run_sql(
        f"""
        do $$
        begin
          if not exists (select 1 from pg_roles where rolname = '{role}') then
            create role {role} login password {sql_literal(password)}
              nosuperuser nocreatedb nocreaterole;
          else
            alter role {role} with login password {sql_literal(password)};
          end if;
        end $$;
        grant connect on database postgres to {role};
        grant usage on schema xray to {role};
        grant all on all tables in schema xray to {role};
        grant all on all sequences in schema xray to {role};
        alter default privileges in schema xray grant all on tables to {role};
        """
    )
    for name in TABLES:
        run_sql(
            f"""
            do $$
            begin
              if not exists (
                select 1 from pg_policies
                where schemaname = 'xray' and tablename = '{name}'
                  and policyname = 'xray_loader_all'
              ) then
                execute format(
                  'create policy xray_loader_all on xray.%I for all to {role} using (true) with check (true)',
                  '{name}'
                );
              end if;
            end $$;
            """
        )


def connection_targets(password: str) -> list[tuple[str, str, int]]:
    explicit = os.environ.get("SUPABASE_DB_URL", "").strip()
    if explicit:
        parsed = urllib.parse.urlparse(explicit)
        host = parsed.hostname or ""
        port = parsed.port or 5432
        return [(explicit, host, port)]
    encoded = urllib.parse.quote(password, safe="")
    user = urllib.parse.quote(f"xray_loader.{project_ref()}", safe="")
    return [
        (
            f"postgresql://{user}:{encoded}@aws-0-eu-west-1.pooler.supabase.com:5432/postgres?sslmode=require",
            "aws-0-eu-west-1.pooler.supabase.com",
            5432,
        ),
        (
            f"postgresql://{user}:{encoded}@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require",
            "aws-0-eu-west-1.pooler.supabase.com",
            6543,
        ),
    ]


def port_open(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def attach_postgres(connection, password: str) -> bool:
    reachable = [
        dsn for dsn, host, port in connection_targets(password) if port_open(host, port)
    ]
    if not reachable:
        log("Puerto 5432/6543 no alcanzable; carga por Management API (HTTPS).")
        return False
    connection.execute("install postgres; load postgres;")
    last_error = None
    for dsn in reachable:
        try:
            connection.execute("detach pg")
        except Exception:
            pass
        try:
            escaped = dsn.replace("'", "''")
            connection.execute(f"attach '{escaped}' as pg (type postgres)")
            connection.execute("select 1 from pg.xray.groups limit 0")
            log("DuckDB ATTACH postgres listo (COPY).")
            return True
        except Exception as exc:
            last_error = exc
    log(f"ATTACH falló ({last_error}); carga por Management API.")
    return False


def col_sql(columns: tuple[str, ...]) -> str:
    return ", ".join(columns)


def jsonable(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def remote_count(name: str) -> int:
    rows = run_sql(f"select count(*) as n from xray.{name}")
    return int(rows[0]["n"])


def push_table_copy(connection, name: str) -> None:
    columns = col_sql(TABLES[name])
    local = connection.execute(f"select count(*) from {name}").fetchone()[0]
    connection.execute(f"delete from pg.xray.{name}")
    started = time.perf_counter()
    connection.execute(
        f"insert into pg.xray.{name} ({columns}) select {columns} from {name}"
    )
    elapsed = time.perf_counter() - started
    remote = connection.execute(f"select count(*) from pg.xray.{name}").fetchone()[0]
    log(f"  {name:22} local={local:>8} remote={remote:>8}  {elapsed:.1f}s  copy")
    if local != remote:
        raise SystemExit(f"{name}: conteo distinto (duckdb {local} vs postgres {remote})")


def push_table_api(connection, name: str, batch_size: int = 400) -> None:
    columns = TABLES[name]
    local = connection.execute(f"select count(*) from {name}").fetchone()[0]
    run_sql(f"truncate table xray.{name}")
    started = time.perf_counter()
    result = connection.execute(f"select {col_sql(columns)} from {name}")
    loaded = 0
    while True:
        batch = result.fetchmany(batch_size)
        if not batch:
            break
        records = [
            {col: jsonable(value) for col, value in zip(columns, row)}
            for row in batch
        ]
        payload = json.dumps(records, ensure_ascii=False)
        run_sql(
            f"insert into xray.{name} select * from "
            f"json_populate_recordset(null::xray.{name}, $xray${payload}$xray$::json)",
            timeout=180,
        )
        loaded += len(batch)
        if local >= 2_000:
            log(f"  {name:22} {loaded:>8}/{local}")
    elapsed = time.perf_counter() - started
    remote = remote_count(name)
    log(f"  {name:22} local={local:>8} remote={remote:>8}  {elapsed:.1f}s  api")
    if local != remote:
        raise SystemExit(f"{name}: conteo distinto (duckdb {local} vs postgres {remote})")


def db_size() -> str:
    rows = run_sql("select pg_size_pretty(pg_database_size(current_database())) as db_size")
    return rows[0]["db_size"]


def sample_checks() -> None:
    country = run_sql(
        """
        select country, count(*) as n
        from xray.companies
        group by 1
        order by n desc
        limit 8
        """
    )
    log("  countries: " + ", ".join(f"{row['country'] or 'null'}={row['n']}" for row in country))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="Load invoices and transactions even on a Free plan",
    )
    return parser.parse_args()


def main() -> None:
    load_env(ROOT / ".env")
    args = parse_args()
    force_large = args.all or os.environ.get("XRAY_FORCE_LARGE_TABLES") == "1"

    project = api("GET", f"/v1/projects/{project_ref()}")
    status = project.get("status")
    if status not in {"ACTIVE_HEALTHY", "COMING_UP", "RESTORING"}:
        raise SystemExit(f"Proyecto {project_ref()} en estado {status}")
    if status != "ACTIVE_HEALTHY":
        log(f"Proyecto {status}; esperando health...")

    plan = org_plan()
    log(f"Proyecto {project_ref()}  status={status}  plan={plan}  size={db_size()}")
    if plan == "free" and not force_large:
        log("Free (500 MB): se omiten invoices y transactions. Pasa --all si el upgrade ya está hecho.")

    if not schema_ready():
        apply_migration()
    else:
        log("Schema xray ya existe")

    password = secrets.token_urlsafe(32)
    ensure_loader(password)

    import duckdb
    from mapping.load import attach

    duck = attach(duckdb.connect())
    duck.execute("pragma threads=4")
    use_copy = attach_postgres(duck, password)
    push = push_table_copy if use_copy else push_table_api

    skip = LARGE_TABLES if plan == "free" and not force_large else frozenset()
    for name in TABLES:
        if name in skip:
            log(f"  {name:22} SKIP (free plan)")
            continue
        push(duck, name)

    for statement in INDEXES:
        table = statement.split(" on xray.", 1)[1].split(" ", 1)[0]
        if table in skip:
            continue
        run_sql(statement)
    log(f"Índices listos. Tamaño: {db_size()}")
    sample_checks()


if __name__ == "__main__":
    main()

