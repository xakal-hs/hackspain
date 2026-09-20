-- Generado por scripts/load_supabase.py --emit-sql. No editar a mano.
-- Maestras (copia fiel de data/*.csv) + tablas de la app (data/processed/*.csv).
-- Sin claves foráneas: los CSV crudos tienen suciedad referencial (ver src/mapping/ISSUES.md).

create table if not exists public.groups (
  group_id text,
  erp text,
  n_companies_in_sample integer,
  primary key (group_id)
);
alter table public.groups enable row level security;
drop policy if exists "read groups" on public.groups;
create policy "read groups" on public.groups for select to anon, authenticated using (true);

create table if not exists public.companies (
  company_id text,
  group_id text,
  country text,
  currency text,
  erp text,
  created_at timestamp,
  primary key (company_id)
);
alter table public.companies enable row level security;
drop policy if exists "read companies" on public.companies;
create policy "read companies" on public.companies for select to anon, authenticated using (true);

create table if not exists public.banking_products (
  product_id text,
  company_id text,
  label text,
  type text,
  bank_name text,
  service text,
  currency text,
  created_at timestamp,
  primary key (product_id)
);
alter table public.banking_products enable row level security;
drop policy if exists "read banking_products" on public.banking_products;
create policy "read banking_products" on public.banking_products for select to anon, authenticated using (true);

create table if not exists public.debt_products (
  product_id text,
  company_id text,
  label text,
  type text,
  bank_name text,
  service text,
  currency text,
  created_at timestamp,
  granted numeric(18,2),
  outstanding numeric(18,2),
  liquidity numeric(18,2),
  primary key (product_id)
);
alter table public.debt_products enable row level security;
drop policy if exists "read debt_products" on public.debt_products;
create policy "read debt_products" on public.debt_products for select to anon, authenticated using (true);

create table if not exists public.debt_schedule_config (
  product_id text,
  company_id text,
  settlement_product_id text,
  currency text,
  amortization_type text,
  interest_calc_method text,
  amortising_frequency text,
  granted_balance numeric(18,2),
  outstanding_balance numeric(18,2),
  total_periods integer,
  next_payment_date timestamp,
  last_payment_date timestamp,
  annual_interest_rate_or_spread numeric(18,2),
  interest_type text,
  primary key (product_id)
);
alter table public.debt_schedule_config enable row level security;
drop policy if exists "read debt_schedule_config" on public.debt_schedule_config;
create policy "read debt_schedule_config" on public.debt_schedule_config for select to anon, authenticated using (true);

create table if not exists public.balances (
  product_id text,
  company_id text,
  date timestamp,
  balance numeric(18,2),
  available numeric(18,2),
  granted numeric(18,2),
  liquidity numeric(18,2),
  countable numeric(18,2),
  primary key (product_id)
);
alter table public.balances enable row level security;
drop policy if exists "read balances" on public.balances;
create policy "read balances" on public.balances for select to anon, authenticated using (true);

create table if not exists public.company_static (
  company_id text,
  group_id text,
  country text,
  currency text,
  erp text,
  n_debt_products integer,
  debt_granted double precision,
  debt_outstanding double precision,
  debt_util double precision,
  tiene_deuda_producto boolean,
  tiene_facturas boolean,
  tiene_erp boolean,
  paga_deuda_banco boolean,
  tiene_saldo boolean,
  meses_historia integer,
  saldo_inconsistente boolean,
  cuentas_moneda_distinta boolean,
  primary key (company_id)
);
alter table public.company_static enable row level security;
drop policy if exists "read company_static" on public.company_static;
create policy "read company_static" on public.company_static for select to anon, authenticated using (true);

create table if not exists public.panel_monthly (
  company_id text,
  month text,
  net_bank double precision,
  inflow_op double precision,
  outflow_op double precision,
  debt_service double precision,
  transfer_net double precision,
  out_salary double precision,
  out_social_security double precision,
  out_tax double precision,
  out_fin_cost double precision,
  n_tx integer,
  net_op double precision,
  cash_end double precision,
  cash_min double precision,
  days_negative integer,
  saldo_inconsistente boolean,
  net_op_3m double precision,
  inflow_op_3m double precision,
  outflow_op_3m double precision,
  debt_service_3m double precision,
  margin_3m double precision,
  runway_m double precision,
  debt_service_ratio_3m double precision,
  hist_months integer,
  historia_corta boolean,
  overdue_amt double precision,
  sales_3m double precision,
  pct_vencido double precision,
  dso double precision,
  payables_overdue90 double precision,
  payables_overdue90_recent double precision,
  tiene_facturas boolean,
  primary key (company_id, month)
);
alter table public.panel_monthly enable row level security;
drop policy if exists "read panel_monthly" on public.panel_monthly;
create policy "read panel_monthly" on public.panel_monthly for select to anon, authenticated using (true);

create table if not exists public.events_candidates (
  company_id text,
  month text,
  obligacion_regular_falta double precision,
  factura_recibida_vencida_90d double precision,
  saldo_negativo double precision,
  caja_agotandose double precision,
  coste_financiero_disparado double precision,
  primary key (company_id, month)
);
alter table public.events_candidates enable row level security;
drop policy if exists "read events_candidates" on public.events_candidates;
create policy "read events_candidates" on public.events_candidates for select to anon, authenticated using (true);

-- Índices de consulta habituales
create index if not exists companies_company_idx on public.companies (company_id);
create index if not exists banking_products_company_idx on public.banking_products (company_id);
create index if not exists debt_products_company_idx on public.debt_products (company_id);
create index if not exists debt_schedule_config_company_idx on public.debt_schedule_config (company_id);
create index if not exists balances_company_idx on public.balances (company_id);
create index if not exists companies_group_idx on public.companies (group_id);
create index if not exists panel_monthly_month_idx on public.panel_monthly (month);
