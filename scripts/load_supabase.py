"""Sube a Supabase las tablas maestras y las tablas de la app.

Solo usa HTTPS (PostgREST) porque el puerto 5432/6543 puede estar bloqueado.
Las tablas se crean con `supabase/schema.sql` (generado por `--emit-sql`).
transactions.csv e invoices.csv NO se suben: no caben en el plan Free (500 MB).

    python scripts/load_supabase.py --emit-sql        # regenera supabase/schema.sql
    python scripts/load_supabase.py                   # carga todo
    python scripts/load_supabase.py companies groups  # carga solo esas tablas
"""
import csv
import math
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BATCH = 2000

# tabla -> (csv, clave primaria, {columna: tipo}). Las columnas no listadas son text.
TABLES = {
    "groups": ("data/groups.csv", ["group_id"], {"n_companies_in_sample": "int"}),
    "companies": ("data/companies.csv", ["company_id"], {"created_at": "timestamp"}),
    "banking_products": ("data/banking_products.csv", ["product_id"], {"created_at": "timestamp"}),
    "debt_products": (
        "data/debt_products.csv",
        ["product_id"],
        {"created_at": "timestamp", "granted": "numeric", "outstanding": "numeric", "liquidity": "numeric"},
    ),
    "debt_schedule_config": (
        "data/debt_schedule_config.csv",
        ["product_id"],
        {
            "granted_balance": "numeric", "outstanding_balance": "numeric", "total_periods": "int",
            "next_payment_date": "timestamp", "last_payment_date": "timestamp",
            "annual_interest_rate_or_spread": "numeric",
        },
    ),
    "balances": (
        "data/balances.csv",
        ["product_id"],
        {"date": "timestamp", "balance": "numeric", "available": "numeric", "granted": "numeric",
         "liquidity": "numeric", "countable": "numeric"},
    ),
    "company_static": (
        "data/processed/company_static.csv",
        ["company_id"],
        {"n_debt_products": "int", "debt_granted": "float", "debt_outstanding": "float", "debt_util": "float",
         "tiene_deuda_producto": "bool", "tiene_facturas": "bool", "tiene_erp": "bool", "paga_deuda_banco": "bool",
         "tiene_saldo": "bool", "meses_historia": "int", "saldo_inconsistente": "bool",
         "cuentas_moneda_distinta": "bool"},
    ),
    "panel_monthly": (
        "data/processed/panel_monthly.csv",
        ["company_id", "month"],
        {**{c: "float" for c in (
            "net_bank inflow_op outflow_op debt_service transfer_net out_salary out_social_security out_tax "
            "out_fin_cost net_op cash_end cash_min net_op_3m inflow_op_3m outflow_op_3m debt_service_3m margin_3m "
            "runway_m debt_service_ratio_3m overdue_amt sales_3m pct_vencido dso payables_overdue90 "
            "payables_overdue90_recent").split()},
         **{c: "int" for c in ("n_tx", "days_negative", "hist_months")},
         **{c: "bool" for c in ("saldo_inconsistente", "historia_corta", "tiene_facturas")}},
    ),
    "events_candidates": (
        "data/processed/events_candidates.csv",
        ["company_id", "month"],
        {c: "float" for c in ("obligacion_regular_falta factura_recibida_vencida_90d saldo_negativo "
                              "caja_agotandose coste_financiero_disparado").split()},
    ),
}
PG = {"int": "integer", "float": "double precision", "numeric": "numeric(18,2)", "bool": "boolean",
      "timestamp": "timestamp", "text": "text"}


def header(csv_path):
    with open(ROOT / csv_path, newline="") as f:
        return next(csv.reader(f))


def emit_sql():
    out = ["-- Generado por scripts/load_supabase.py --emit-sql. No editar a mano.",
           "-- Maestras (copia fiel de data/*.csv) + tablas de la app (data/processed/*.csv).",
           "-- Sin claves foráneas: los CSV crudos tienen suciedad referencial (ver src/mapping/ISSUES.md).", ""]
    for name, (path, pk, types) in TABLES.items():
        cols = [f"  {c} {PG[types.get(c, 'text')]}" for c in header(path)]
        cols.append(f"  primary key ({', '.join(pk)})")
        out.append(f"create table if not exists public.{name} (\n" + ",\n".join(cols) + "\n);")
        out.append(f"alter table public.{name} enable row level security;")
        out.append(f'drop policy if exists "read {name}" on public.{name};')
        out.append(f'create policy "read {name}" on public.{name} for select to anon, authenticated using (true);')
        out.append("")
    out.append("-- Índices de consulta habituales")
    for t in ("companies", "banking_products", "debt_products", "debt_schedule_config", "balances"):
        out.append(f"create index if not exists {t}_company_idx on public.{t} (company_id);")
    out.append("create index if not exists companies_group_idx on public.companies (group_id);")
    out.append("create index if not exists panel_monthly_month_idx on public.panel_monthly (month);")
    (ROOT / "supabase").mkdir(exist_ok=True)
    (ROOT / "supabase/schema.sql").write_text("\n".join(out) + "\n")
    print("escrito supabase/schema.sql")


def convert(v, t):
    if v == "":
        return None
    if t == "int":
        return int(float(v))
    if t in ("float", "numeric"):
        x = float(v)
        return None if math.isnan(x) else x
    if t == "bool":
        return v.lower() in ("true", "1")
    return v


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v.strip("'\"")
    return env


def upload(name, url, key):
    path, pk, types = TABLES[name]
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    endpoint = f"{url}/rest/v1/{name}?on_conflict={','.join(pk)}"
    n = 0
    with open(ROOT / path, newline="") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            batch.append({c: convert(v, types.get(c, "text")) for c, v in row.items()})
            if len(batch) == BATCH:
                n += push(endpoint, headers, batch, name)
                batch = []
        if batch:
            n += push(endpoint, headers, batch, name)
    print(f"{name}: {n} filas")


def push(endpoint, headers, batch, name):
    r = requests.post(endpoint, headers=headers, json=batch, timeout=120)
    if not r.ok:
        sys.exit(f"{name}: HTTP {r.status_code} {r.text[:400]}")
    return len(batch)


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--emit-sql" in args:
        emit_sql()
        sys.exit()
    env = load_env()
    for name in args or TABLES:
        upload(name, env["SUPABASE_URL"], env["SUPABASE_SECRET_KEY"])
