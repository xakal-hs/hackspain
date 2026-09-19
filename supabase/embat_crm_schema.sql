-- CRM interno de Equipo Embat. El backend lo lee y escribe con service_role;
-- nunca el navegador.

create table if not exists public.embat_account_managers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.embat_leads (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies(company_id) on delete cascade,
  status text not null default 'nuevo'
    check (status in ('nuevo', 'contactado', 'reunion', 'cerrado')),
  assigned_to uuid not null references public.embat_account_managers(id),
  signal text not null default 'financiar' check (signal = 'financiar'),
  email_draft text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists embat_leads_open_company
  on public.embat_leads (company_id)
  where status in ('nuevo', 'contactado', 'reunion');

create index if not exists embat_leads_assigned_to_idx
  on public.embat_leads (assigned_to);

alter table public.embat_account_managers enable row level security;
alter table public.embat_leads enable row level security;

grant select on public.embat_account_managers to service_role;
grant select, insert, update on public.embat_leads to service_role;

drop policy if exists "service role reads account managers" on public.embat_account_managers;
create policy "service role reads account managers"
  on public.embat_account_managers for select to service_role using (true);

drop policy if exists "service role manages leads" on public.embat_leads;
create policy "service role manages leads"
  on public.embat_leads for all to service_role using (true) with check (true);

comment on table public.embat_account_managers is
  'Account managers de la demo Equipo Embat. Nombres de presentación, no usuarios de Auth.';
comment on table public.embat_leads is
  'Peticiones de financiación disparadas desde Flujo de caja. El draft no lleva datos de la empresa.';

insert into public.embat_account_managers (name)
values ('Marta Gil'), ('Luis Navarro'), ('Elena Ortiz')
on conflict (name) do nothing;

-- Tres avisos de demo para que el CRM no arranque vacío.
insert into public.embat_leads (company_id, status, assigned_to, signal, email_draft)
select v.company_id, v.status, m.id, 'financiar', $draft$Asunto: Revisión de tesorería con tu asesor

Hola,

Hemos visto una señal de tensión de caja. No es un diagnóstico cerrado: es el momento de revisar si un puente de financiación encaja antes de que la cuenta se quede corta.

Tu asesor personal puede mirarlo contigo en una llamada corta.

Agenda aquí: https://calendly.com/embat-asesor/revision-caja

Equipo Embat
$draft$
from (
  values
    ('COMP_0779', 'nuevo', 'Marta Gil'),
    ('COMP_0130', 'contactado', 'Luis Navarro'),
    ('COMP_1155', 'reunion', 'Elena Ortiz')
) as v(company_id, status, manager_name)
join public.embat_account_managers m on m.name = v.manager_name
where not exists (
  select 1 from public.embat_leads l
  where l.company_id = v.company_id
    and l.status in ('nuevo', 'contactado', 'reunion')
);

