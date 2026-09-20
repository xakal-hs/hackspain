-- Capa de decisión y catálogo del modelo. Ejecutar después de health_schema.sql.
--
-- La nota ordena el riesgo; no decide. Encima van los vetos, que son hechos de HOY y
-- mandan sobre cualquier nota. El cálculo vive en research/src/decision.py y se publica con
-- scripts/export_decision_publication.py: PostgreSQL sirve resultados, nunca decide.

create table if not exists public.company_decision_monthly (
  company_id text not null,
  month date not null,
  accion text not null check (accion in ('prestar', 'vigilar', 'no_prestar', 'sin_nota')),
  accion_label text not null,
  -- la razón que manda: el veto bloqueante, o la banda. La interfaz no inventa el motivo.
  razon text not null default '',
  -- objetos completos {codigo, etiqueta, texto, bloquea, levantable}: el texto viaja con la
  -- regla para que el navegador no tenga que saber qué significa `veto_ss_ausente`.
  vetos jsonb not null default '[]'::jsonb,
  avisos jsonb not null default '[]'::jsonb,
  razones jsonb not null default '[]'::jsonb,
  -- importe máximo en meses de gasto. Se recorta por observabilidad, no por salud.
  importe_max_meses double precision,
  score_version text not null,
  calculated_at timestamptz not null default now(),
  primary key (company_id, month)
);

create index if not exists company_decision_monthly_latest_idx
  on public.company_decision_monthly (company_id, month desc);

-- Una sola fila: pesos, escala, bandas, anclas de evento y el catálogo de vetos.
-- Es todo lo que el modelo aprendió más los textos de las reglas que van encima.
create table if not exists public.score_catalog (
  score_version text primary key,
  payload jsonb not null,
  published_at timestamptz not null default now()
);

alter table public.company_decision_monthly enable row level security;
alter table public.score_catalog enable row level security;

-- Solo servidor: la decisión del prestamista no se sirve al navegador sin pasar por Nitro.
grant select on public.company_decision_monthly, public.score_catalog to service_role;

drop policy if exists "service role reads decisions" on public.company_decision_monthly;
create policy "service role reads decisions" on public.company_decision_monthly
  for select to service_role using (true);

drop policy if exists "service role reads score catalog" on public.score_catalog;
create policy "service role reads score catalog" on public.score_catalog
  for select to service_role using (true);

-- ---------------------------------------------------------------------------
-- Cartera: una fila por empresa con todo lo que enseña la tabla de cartera.
--
-- Existe para que la función serverless haga UNA consulta de 1.286 filas en vez de
-- paginar 22.000 de panel y 21.500 de salud en cada petición. Agrega aquí, no en Nitro.
create or replace view public.company_portfolio_latest as
with panel_ranked as (
  select
    company_id, month, cash_end, runway_m, dso, pct_vencido, margin_3m,
    debt_service_ratio_3m, n_tx, inflow_op, outflow_op,
    lag(runway_m, 3) over (partition by company_id order by month) as runway_prev,
    lag(dso, 3) over (partition by company_id order by month) as dso_prev,
    row_number() over (partition by company_id order by month desc) as rn
  from public.panel_monthly
),
panel_now as (select * from panel_ranked where rn = 1),
flows as (
  -- panel_monthly.month es texto 'AAAA-MM': ordena lexicográficamente y ya viaja formateado.
  select company_id, jsonb_agg(jsonb_build_object(
           'month', month,
           'in', coalesce(inflow_op, 0),
           'out', abs(coalesce(outflow_op, 0)),
           'cash', coalesce(cash_end, 0)) order by month) as flows
  from panel_ranked where rn <= 12 group by company_id
),
health_ranked as (
  select h.*, row_number() over (partition by company_id order by month desc) as rn
  from public.company_health_monthly h
),
health_now as (select * from health_ranked where rn = 1),
history as (
  select company_id, jsonb_agg(round(health_score::numeric, 1) order by month) as history
  from health_ranked where rn <= 12 group by company_id
),
months as (
  select company_id, count(*)::int as n_months
  from public.company_health_monthly group by company_id
)
select
  h.company_id,
  s.group_id,
  coalesce(s.currency, 'EUR') as currency,
  coalesce(s.tiene_erp, false) as has_erp,
  m.n_months,
  h.month as last_month,
  round(h.health_score::numeric, 1) as score,
  h.health_band as band,
  round(h.score_delta_3m::numeric, 1) as delta3,
  h.health_trend,
  h.coverage,
  h.confidence,
  h.ood_share,
  h.risk_flags,
  h.liquidez_score, h.rentabilidad_score, h.solvencia_score,
  h.disciplina_score, h.estabilidad_score,
  d.accion, d.accion_label, d.razon, d.vetos, d.avisos, d.importe_max_meses,
  p.cash_end,
  p.runway_m as runway_now,
  p.runway_prev,
  p.dso as dso_now,
  p.dso_prev,
  -- pct_vencido es una fracción, no un porcentaje: la interfaz escribe el «%» detrás.
  case when p.pct_vencido is null then null else round((p.pct_vencido * 100)::numeric, 1) end as overdue_share,
  p.margin_3m,
  p.debt_service_ratio_3m,
  coalesce(p.n_tx, 0) as n_tx,
  s.debt_outstanding,
  s.debt_util,
  coalesce(f.flows, '[]'::jsonb) as flows,
  coalesce(hi.history, '[]'::jsonb) as history
from health_now h
join months m on m.company_id = h.company_id
left join public.company_static s on s.company_id = h.company_id
left join public.company_decision_monthly d on d.company_id = h.company_id and d.month = h.month
left join panel_now p on p.company_id = h.company_id
left join flows f on f.company_id = h.company_id
left join history hi on hi.company_id = h.company_id;

grant select on public.company_portfolio_latest to service_role;

comment on view public.company_portfolio_latest is
  'Cartera lista para servir: último mes de cada empresa con su decisión, sus magnitudes y 12 meses de flujos y notas.';
