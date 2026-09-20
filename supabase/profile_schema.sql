-- Perfil operativo: contexto de la empresa, nunca un ingrediente del Health Score.
create table if not exists public.company_business_profile (
  company_id text primary key,
  group_id text,
  business_kind text,
  sector_set jsonb not null default '[]'::jsonb,
  top_sector text,
  top_sector_score double precision,
  regime_id integer,
  regime_label text,
  profile_confidence double precision check (profile_confidence between 0 and 1),
  tenor text,
  product_fit text,
  as_of_month date not null,
  profile_version text not null,
  calculated_at timestamptz not null default now()
);

create index if not exists company_business_profile_regime_idx
  on public.company_business_profile (regime_id);
alter table public.company_business_profile enable row level security;
grant select on public.company_business_profile to anon, authenticated;
drop policy if exists "read company_business_profile" on public.company_business_profile;
create policy "read company_business_profile" on public.company_business_profile
  for select to anon, authenticated using (true);
