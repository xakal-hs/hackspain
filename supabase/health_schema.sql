-- Contrato de publicación de X-Ray. Ejecutar después de supabase/schema.sql.
-- El cálculo vive en research/src/export_health_publication.py; PostgreSQL solo
-- sirve resultados ya validados y explicables, nunca recalcula el modelo.

create table if not exists public.company_health_monthly (
  company_id text not null,
  month date not null,
  health_score double precision not null check (health_score between 0 and 100),
  health_band text not null check (health_band in ('riesgo', 'vigilar', 'sano')),
  health_trend text not null check (health_trend in ('improving', 'stable', 'deteriorating')),
  score_delta_3m double precision,
  liquidez_score double precision,
  rentabilidad_score double precision,
  solvencia_score double precision,
  disciplina_score double precision,
  estabilidad_score double precision,
  coverage double precision not null check (coverage between 0 and 1),
  confidence double precision not null check (confidence between 0 and 1),
  ood_share double precision not null check (ood_share between 0 and 1),
  risk_flags jsonb not null default '[]'::jsonb,
  score_version text not null,
  calculated_at timestamptz not null default now(),
  primary key (company_id, month)
);

create index if not exists company_health_monthly_latest_idx
  on public.company_health_monthly (company_id, month desc);

create table if not exists public.company_health_driver_monthly (
  company_id text not null,
  month date not null,
  feature text not null,
  pillar text not null,
  label text not null,
  raw_value double precision,
  display_value text not null,
  contribution double precision not null,
  score_version text not null,
  calculated_at timestamptz not null default now(),
  primary key (company_id, month, feature, score_version)
);

create index if not exists company_health_driver_monthly_lookup_idx
  on public.company_health_driver_monthly (company_id, month desc);

alter table public.company_health_monthly enable row level security;
alter table public.company_health_driver_monthly enable row level security;

grant select on public.company_health_monthly, public.company_health_driver_monthly to anon, authenticated;

drop policy if exists "read company_health_monthly" on public.company_health_monthly;
create policy "read company_health_monthly" on public.company_health_monthly
  for select to anon, authenticated using (true);

drop policy if exists "read company_health_driver_monthly" on public.company_health_driver_monthly;
create policy "read company_health_driver_monthly" on public.company_health_driver_monthly
  for select to anon, authenticated using (true);
