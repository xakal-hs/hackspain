-- Selección curada de la demo X-Ray. Los display_name son aliases ficticios.
-- Esta tabla es privada: el backend la lee con service_role; nunca el navegador.

create table if not exists public.featured_companies (
  company_id text primary key references public.companies(company_id) on delete cascade,
  display_order smallint not null unique check (display_order between 1 and 20),
  display_name text not null unique,
  sector text not null,
  business_kind text,
  tenor text,
  product_fit text,
  selection_reason text not null,
  snapshotted_month date not null,
  health_score numeric(5,2) not null check (health_score between 0 and 100),
  health_band text not null check (health_band in ('riesgo', 'vigilar', 'sano')),
  health_trend text not null check (health_trend in ('improving', 'stable', 'deteriorating')),
  score_delta_3m numeric(6,2),
  data_coverage numeric(4,3) not null check (data_coverage between 0 and 1),
  confidence numeric(4,3) not null check (confidence between 0 and 1),
  risk_flags jsonb not null default '[]'::jsonb,
  selected_at timestamptz not null default now()
);

alter table public.featured_companies enable row level security;
grant select on public.featured_companies to service_role;
drop policy if exists "service role reads featured companies" on public.featured_companies;
create policy "service role reads featured companies"
  on public.featured_companies for select to service_role using (true);

comment on table public.featured_companies is
  'Preselección curada de 20 empresas para la demo. Los nombres de presentación son ficticios.';
comment on column public.featured_companies.display_name is
  'Alias ficticio generado para la demo; conservar company_id como identificador canónico.';

with curated (display_order, company_id, display_name, selection_reason) as (
  values
    (1, 'COMP_0022', 'La Mesa Verde', 'Mejora muy marcada en hostelería; mantiene señales de cobros y pagos tardíos para explicar seguimiento activo.'),
    (2, 'COMP_0936', 'Cimientos Delta', 'Recuperación destacada en construcción, con pago a proveedores aún tardío.'),
    (3, 'COMP_0779', 'Nexo Capital', 'Deterioro severo en tesorería por caja de corta duración; caso claro para vigilancia inmediata.'),
    (4, 'COMP_0130', 'Clara Consultores', 'Caída estructural en servicios profesionales, con caja escasa y retrasos de cobro y pago.'),
    (5, 'COMP_1155', 'Atlas Obras', 'Riesgo relevante en construcción: deterioro, caja escasa y tensiones en proveedores y clientes.'),
    (6, 'COMP_0055', 'Linde Urbana Patrimonios', 'Caso inmobiliario de riesgo con caída pronunciada y varias señales de tensión operativa.'),
    (7, 'COMP_0654', 'Mercado Lumen', 'Deterioro claro en comercio minorista asociado a retrasos de cobro.'),
    (8, 'COMP_0673', 'Casa del Olivo', 'Hostelería en vigilancia: baja caja y retrasos simultáneos de cobro y pago.'),
    (9, 'COMP_0829', 'Fábrica Brava', 'Industria en vigilancia pero estable: caja escasa y retrasos operativos visibles que justifican monitorización.'),
    (10, 'COMP_0232', 'Río Mayor Distribución', 'Distribuidor en riesgo por caja escasa y cobros tardíos; ilustra una necesidad de circulante.'),
    (11, 'COMP_0522', 'Ruta Ágil Logística', 'Logística en deterioro por caja escasa y cobros tardíos; caso apto para factoring.'),
    (12, 'COMP_0326', 'Solaria Técnica', 'Energía en vigilancia con descenso reciente; permite comparar riesgo sectorial de medio plazo.'),
    (13, 'COMP_0461', 'Tienda Faro', 'Comercio minorista con recuperación sólida, aunque persisten alertas de plazos de cobro y pago.'),
    (14, 'COMP_0412', 'Vértice Tesorería', 'Holding que mejora, pero conserva retraso de cobro; útil para mostrar oportunidad de tesorería.'),
    (15, 'COMP_0931', 'Alba Mercantil', 'Mayorista en recuperación con alertas de proveedores y clientes aún activas.'),
    (16, 'COMP_0396', 'Puente Fiscal', 'Servicios profesionales en recuperación; el retraso de proveedores explica por qué sigue monitorizada.'),
    (17, 'COMP_0588', 'Nube Prisma', 'Software saludable y en mejora, sin alertas activas; contrapeso de oportunidad y crecimiento.'),
    (18, 'COMP_0682', 'Energía Horizonte', 'Energía saludable en mejora, con plazos operativos aún observables.'),
    (19, 'COMP_0835', 'Mirador del Mar', 'Hostelería saludable y en mejora; el retraso de cobro mantiene una oportunidad concreta de seguimiento.'),
    (20, 'COMP_0531', 'Talento Norte', 'Servicios profesionales sanos y en recuperación, con alertas de plazos que justifican seguimiento.')
),
latest_health as (
  select distinct on (company_id)
    company_id, month, health_score, health_band, health_trend,
    score_delta_3m, coverage, confidence, risk_flags
  from public.company_health_monthly
  order by company_id, month desc
)
insert into public.featured_companies (
  company_id, display_order, display_name, sector, business_kind, tenor, product_fit,
  selection_reason, snapshotted_month, health_score, health_band, health_trend,
  score_delta_3m, data_coverage, confidence, risk_flags
)
select
  c.company_id, c.display_order, c.display_name, p.top_sector, p.business_kind,
  p.tenor, p.product_fit, c.selection_reason, h.month, h.health_score,
  h.health_band, h.health_trend, h.score_delta_3m, h.coverage, h.confidence,
  h.risk_flags
from curated c
join public.company_business_profile p using (company_id)
join latest_health h using (company_id)
on conflict (company_id) do update set
  display_order = excluded.display_order,
  display_name = excluded.display_name,
  sector = excluded.sector,
  business_kind = excluded.business_kind,
  tenor = excluded.tenor,
  product_fit = excluded.product_fit,
  selection_reason = excluded.selection_reason,
  snapshotted_month = excluded.snapshotted_month,
  health_score = excluded.health_score,
  health_band = excluded.health_band,
  health_trend = excluded.health_trend,
  score_delta_3m = excluded.score_delta_3m,
  data_coverage = excluded.data_coverage,
  confidence = excluded.confidence,
  risk_flags = excluded.risk_flags,
  selected_at = now();
