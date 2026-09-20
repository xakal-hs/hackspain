-- Mapped X-Ray source tables. Private schema: not on the Data API.
-- Dirt stays in the rows (no FKs). Mapping is applied in DuckDB before load.

create schema if not exists xray;

revoke all on schema xray from public;
revoke all on schema xray from anon, authenticated;
grant usage, create on schema xray to postgres, service_role;

create table xray.groups (
    group_id text primary key,
    erp_raw text,
    erp_code text,
    erp_label text,
    erp text,
    n_companies_in_sample bigint,
    dq_erp_unmapped boolean
);

create table xray.companies (
    company_id text primary key,
    group_id text,
    country_raw text,
    country text,
    currency text,
    erp_raw text,
    erp_code text,
    erp_label text,
    erp text,
    created_at timestamptz,
    observation_start date,
    has_checking boolean,
    has_invoices boolean,
    erp_connected boolean,
    balance_missing boolean,
    dq_country_unmapped boolean,
    dq_erp_unmapped boolean
);

create table xray.banking_products (
    product_id text primary key,
    company_id text,
    label text,
    type text,
    type_family text,
    bank_name_raw text,
    bank_name text,
    service_raw text,
    service text,
    currency text,
    created_at timestamptz,
    connected_after_cutoff boolean,
    observation_start date,
    service_kind text
);

create table xray.debt_products (
    product_id text primary key,
    company_id text,
    label text,
    type text,
    type_family text,
    bank_name_raw text,
    bank_name text,
    service_raw text,
    service text,
    service_kind text,
    currency text,
    created_at timestamptz,
    granted double precision,
    outstanding double precision,
    granted_raw double precision,
    outstanding_raw double precision,
    granted_liability double precision,
    outstanding_liability double precision,
    liquidity double precision,
    connected_after_cutoff boolean,
    observation_start date,
    dq_positive_outstanding boolean,
    dq_granted_outstanding_sign_mismatch boolean,
    dq_outstanding_exceeds_granted boolean
);

create table xray.debt_schedule_config (
    product_id text primary key,
    company_id text,
    settlement_product_id_raw text,
    settlement_product_id text,
    dq_settlement_orphan boolean,
    currency text,
    amortization_type_raw text,
    amortization_type text,
    interest_calc_method text,
    amortising_frequency_raw text,
    amortising_frequency text,
    granted_balance double precision,
    outstanding_balance double precision,
    total_periods bigint,
    next_payment_date timestamptz,
    last_payment_date timestamptz,
    annual_interest_rate_or_spread double precision,
    interest_type text,
    dq_schedule_amount_mismatch boolean
);

create table xray.balances (
    product_id text primary key,
    company_id text,
    date timestamptz,
    balance double precision,
    available text,
    granted double precision,
    liquidity double precision,
    countable double precision,
    balance_quality text,
    dq_balance_suspect boolean
);

create table xray.invoices (
    operation_id text primary key,
    company_id text,
    document_type text,
    issuance_date timestamptz,
    due_date timestamptz,
    payment_date timestamptz,
    payment_date_raw timestamptz,
    payment_date_was_due_alias boolean,
    amount double precision,
    pending_amount double precision,
    currency text,
    accounting_currency text,
    exchange_rate double precision,
    exchange_rate_raw double precision,
    status text,
    status_raw text,
    concept text,
    counterparty_id text,
    counterparty_id_raw text,
    dq_due_before_issuance boolean,
    dq_paid_before_issuance boolean,
    dq_pending_exceeds_amount boolean,
    dq_pending_sign_mismatch boolean
);

create table xray.transactions (
    transaction_id text primary key,
    company_id text,
    product_id text,
    date timestamptz,
    value_date_raw timestamptz,
    value_date_clean timestamptz,
    amount double precision,
    exchange_rate_raw double precision,
    exchange_rate double precision,
    status text,
    accounting_status text,
    category_raw text,
    category text,
    description text,
    counterparty_id_raw text,
    counterparty_id text
);

create table xray.products (
    product_id text primary key,
    company_id text,
    product_class text,
    type text,
    currency text,
    created_at timestamptz,
    catalog_status text
);

alter table xray.groups enable row level security;
alter table xray.companies enable row level security;
alter table xray.banking_products enable row level security;
alter table xray.debt_products enable row level security;
alter table xray.debt_schedule_config enable row level security;
alter table xray.balances enable row level security;
alter table xray.invoices enable row level security;
alter table xray.transactions enable row level security;
alter table xray.products enable row level security;

grant all on all tables in schema xray to postgres, service_role;
grant all on all sequences in schema xray to postgres, service_role;
alter default privileges in schema xray grant all on tables to postgres, service_role;
alter default privileges in schema xray grant all on sequences to postgres, service_role;
