-- Empleados Embat (AM + CS) y CRM en el proyecto del frontend.
-- El servidor Nitro los lee con la secret key; el navegador no.

create table if not exists public.embat_employees (
  id uuid primary key,
  first_name text not null,
  last_name text not null,
  full_name text not null,
  job_title text not null,
  company text not null,
  non_investor_check boolean not null default true,
  sales_role text,
  ai_full_name text not null unique,
  ai_job_title text not null,
  standardized_role text not null,
  team text not null check (team in ('account_management', 'customer_success')),
  created_at timestamptz not null default now()
);

create index if not exists embat_employees_team_idx
  on public.embat_employees (team);

alter table public.embat_employees enable row level security;

grant select, insert, update on public.embat_employees to service_role;

drop policy if exists "service role reads embat employees" on public.embat_employees;
create policy "service role reads embat employees"
  on public.embat_employees for all to service_role using (true) with check (true);

comment on table public.embat_employees is
  'Empleados actuales de Embat (comercial + customer success). Unión de data/embat_am.csv y data/embat_cs.csv.';

insert into public.embat_employees (
  id, first_name, last_name, full_name, job_title, company,
  non_investor_check, sales_role, ai_full_name, ai_job_title,
  standardized_role, team
)
select
  id, first_name, last_name, full_name, job_title, company,
  non_investor_check, sales_role, ai_full_name, ai_job_title,
  standardized_role, team
from json_populate_recordset(null::public.embat_employees, $embat$[{"id": "a3bda2b2-b82b-51e1-a024-b1190c0ce6b1", "first_name": "Nuria", "last_name": "Terol", "full_name": "Nuria Terol", "job_title": "Founding AE - Enterprise Finance Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Nuria Terol", "ai_job_title": "Founding AE - Enterprise Finance Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "71e8f813-8523-5cba-831a-19157e099a6c", "first_name": "Sam", "last_name": "Reardon", "full_name": "Sam Reardon", "job_title": "Finance Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Sam Reardon", "ai_job_title": "Finance Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "4506fd13-965f-5e4b-9d07-4586d38945a7", "first_name": "Antonio", "last_name": "García", "full_name": "Antonio Navarro García", "job_title": "Sales Team Lead", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Antonio Navarro García", "ai_job_title": "Sales Team Lead", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "d6d25776-36b8-51a5-9e32-d0c67f63aafd", "first_name": "Diego", "last_name": "Juarros", "full_name": "Diego Aguirre Juarros", "job_title": "Enterprise Account Executive / Treasury & Banking", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Diego Aguirre Juarros", "ai_job_title": "Enterprise Account Executive / Treasury & Banking", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "17b5fd53-9277-5365-97ae-d74e8f696d1f", "first_name": "Leopoldo", "last_name": "López", "full_name": "Leopoldo Vizoso López", "job_title": "Senior Treasury Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Leopoldo Vizoso López", "ai_job_title": "Senior Treasury Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "1be5de12-4271-50c8-a5be-531e677b5829", "first_name": "Tom", "last_name": "Stachiewicz", "full_name": "Tom Stachiewicz", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Tom Stachiewicz", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "29f28dca-9433-5deb-bd80-7d3cc1d51b68", "first_name": "Juan", "last_name": "de Hijas", "full_name": "Juan Rodríguez-Marín Martín de Hijas", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Juan Rodríguez-Marín Martín de Hijas", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "01e13f3e-587c-5656-a584-f5ae3b0d2aa0", "first_name": "Will", "last_name": "Curtis", "full_name": "Will Curtis", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Will Curtis", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "728c2290-5c5f-516d-8c09-c847d94a15e3", "first_name": "Tilly", "last_name": "Dingwall", "full_name": "Tilly Dingwall", "job_title": "Finance Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Tilly Dingwall", "ai_job_title": "Finance Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "081a34ab-ddbf-5cf5-b6aa-2c7d63344d72", "first_name": "Yolanda", "last_name": "Pineda", "full_name": "Yolanda Pineda", "job_title": "Enterprise Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Yolanda Pineda", "ai_job_title": "Enterprise Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "deb11b92-6b4e-5dfd-a769-3462ce0f8886", "first_name": "Orla", "last_name": "White", "full_name": "Orla White", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Orla White", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "aa159d4a-b36c-5295-9605-bbe9ba3cbb81", "first_name": "Isabel", "last_name": "Barriga", "full_name": "Isabel Benito Barriga", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Isabel Benito Barriga", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "53e74ac5-1fa3-538d-b296-9c415371ec6d", "first_name": "Katie", "last_name": "Huber", "full_name": "Katie Huber", "job_title": "Senior Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Katie Huber", "ai_job_title": "Senior Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "c6faca86-1429-54cb-aeeb-1b3ebd76acfe", "first_name": "Gabriel", "last_name": "Schröck", "full_name": "Gabriel Schröck", "job_title": "Founding Account Executive DACH", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Gabriel Schröck", "ai_job_title": "Founding Account Executive DACH", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "69a88265-5d52-5f93-a0a9-0eba9eb99dc9", "first_name": "Marcus", "last_name": "Kirchhofer", "full_name": "Marcus Kirchhofer", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Marcus Kirchhofer", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "6f695e76-f6dd-5913-87a6-2a48569410bb", "first_name": "Natalia", "last_name": "Laplaza", "full_name": "Natalia Vasco Laplaza", "job_title": "Treasury Consultant - BDR", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Natalia Vasco Laplaza", "ai_job_title": "Treasury Consultant - BDR", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "2d1af5b1-c892-5147-984e-af393a653455", "first_name": "Sam", "last_name": "Hopkins", "full_name": "Sam Hopkins", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Sam Hopkins", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "a3d812a1-b66c-542d-b384-1271d8547f2b", "first_name": "Francesco", "last_name": "Choque", "full_name": "Francesco Garcia Choque", "job_title": "Senior Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Francesco Garcia Choque", "ai_job_title": "Senior Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "35d49e9e-1b3e-5a2a-bf7c-eadd494fc96b", "first_name": "Moritz", "last_name": "Demmel", "full_name": "Moritz Demmel", "job_title": "Finance Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Moritz Demmel", "ai_job_title": "Finance Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "d387f623-733b-545a-b26c-4021c87a817b", "first_name": "Santiago", "last_name": "Moreno", "full_name": "Santiago Garcia Moreno", "job_title": "BDR | Treasury Consultant", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Santiago Garcia Moreno", "ai_job_title": "BDR | Treasury Consultant", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "aab300c3-12a6-580f-b2d6-f5e084dee48c", "first_name": "Maria", "last_name": "Barragán", "full_name": "Maria Paula Ricaurte Barragán", "job_title": "Account Executive", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Maria Paula Ricaurte Barragán", "ai_job_title": "Account Executive", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "db718db9-3a0b-5286-8a4b-e93a61a0c4d6", "first_name": "Jaime", "last_name": "Paz-Ares", "full_name": "Jaime Yanes Paz-Ares", "job_title": "Business Development", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Jaime Yanes Paz-Ares", "ai_job_title": "Business Development", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "448e3cee-d870-59dd-8f1b-311c26456409", "first_name": "Melisa", "last_name": "González", "full_name": "Melisa González", "job_title": "BDR | Treasury Consultant", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Melisa González", "ai_job_title": "BDR | Treasury Consultant", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "48395b5c-ec30-5d0b-bae7-ce93b415fa0f", "first_name": "Carlos", "last_name": "Nogales", "full_name": "Carlos McCann Nogales", "job_title": "BDR | Treasury Consultant", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Carlos McCann Nogales", "ai_job_title": "BDR | Treasury Consultant", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "4ae45323-8c54-5c0d-8b65-380ef364eeac", "first_name": "Miguel", "last_name": "Medina", "full_name": "Miguel Martín Medina", "job_title": "Comercial Inmobiliario en EMBAT S.I.", "company": "Embat Servicios Inmobiliarios SL", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Miguel Martín Medina", "ai_job_title": "Comercial Inmobiliario en EMBAT S.I.", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "47ec9dd5-c60f-599d-b56c-3443854785a2", "first_name": "Pedro", "last_name": "Gimenez", "full_name": "Pedro Bonny Gimenez", "job_title": "Sales Representative", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Pedro Bonny Gimenez", "ai_job_title": "Sales Representative", "standardized_role": "Account Executive", "team": "account_management"}, {"id": "21616b09-a527-59f4-a779-da5939f4dc5c", "first_name": "Sergio", "last_name": "Gomez", "full_name": "Sergio Romero Gomez", "job_title": "Customer Success Manager", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Sergio Romero Gomez", "ai_job_title": "Customer Success Manager", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "f4996a1e-e7f1-5403-b725-967ea916f76d", "first_name": "Il", "last_name": "Park", "full_name": "Il Ho Park", "job_title": "Treasury Success Specialist", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Il Ho Park", "ai_job_title": "Treasury Success Specialist", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "5c505688-68d8-58ef-b3c5-b008f9eafc06", "first_name": "Priscila", "last_name": "Kishimoto", "full_name": "Priscila Kishimoto", "job_title": "Operations Efficiency - Customer Experience", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Priscila Kishimoto", "ai_job_title": "Operations Efficiency - Customer Experience", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "97360964-14c7-52a5-8ad0-cc4bb5486c67", "first_name": "Leandro", "last_name": "Margarit", "full_name": "Leandro Guerrero Margarit", "job_title": "Customer Success Lead – Corporate Treasury Solutions", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Leandro Guerrero Margarit", "ai_job_title": "Customer Success Lead – Corporate Treasury Solutions", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "9f991e10-f90c-5298-8675-f8bc6282930f", "first_name": "Ignacio", "last_name": "Martínez", "full_name": "Ignacio Atienza Martínez", "job_title": "Customer Success", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Ignacio Atienza Martínez", "ai_job_title": "Customer Success", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "49d6223c-1e7e-598a-b30b-4aa55ad4f3fc", "first_name": "Juan", "last_name": "Viveros", "full_name": "Juan Manuel López Viveros", "job_title": "Customer Experience Specialist", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Juan Manuel López Viveros", "ai_job_title": "Customer Experience Specialist", "standardized_role": "Customer Experience", "team": "customer_success"}, {"id": "39eb649d-bf59-50a1-bc6b-e92bdcb18c02", "first_name": "Sergio", "last_name": "Gómez", "full_name": "Sergio Merino Gómez", "job_title": "Customer success", "company": "Embat", "non_investor_check": true, "sales_role": "Response", "ai_full_name": "Sergio Merino Gómez", "ai_job_title": "Customer success", "standardized_role": "Customer Experience", "team": "customer_success"}]$embat$::json)
on conflict (id) do update set
  first_name = excluded.first_name,
  last_name = excluded.last_name,
  full_name = excluded.full_name,
  job_title = excluded.job_title,
  company = excluded.company,
  non_investor_check = excluded.non_investor_check,
  sales_role = excluded.sales_role,
  ai_full_name = excluded.ai_full_name,
  ai_job_title = excluded.ai_job_title,
  standardized_role = excluded.standardized_role,
  team = excluded.team;

create table if not exists public.embat_leads (
  id uuid primary key default gen_random_uuid(),
  company_id text not null references public.companies(company_id) on delete cascade,
  status text not null default 'nuevo'
    check (status in ('nuevo', 'contactado', 'reunion', 'cerrado')),
  assigned_to uuid not null references public.embat_employees(id),
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

alter table public.embat_leads enable row level security;
grant select, insert, update on public.embat_leads to service_role;

drop policy if exists "service role manages leads" on public.embat_leads;
create policy "service role manages leads"
  on public.embat_leads for all to service_role using (true) with check (true);

insert into public.embat_leads (company_id, status, assigned_to, signal, email_draft)
select v.company_id, v.status, e.id, 'financiar', $draft$Asunto: Revisión de tesorería con tu asesor

Hola,

Hemos visto una señal de tensión de caja. No es un diagnóstico cerrado: es el momento de revisar si un puente de financiación encaja antes de que la cuenta se quede corta.

Tu asesor personal puede mirarlo contigo en una llamada corta.

Agenda aquí: https://calendly.com/embat-asesor/revision-caja

Equipo Embat
$draft$
from (
  values
    ('COMP_0779', 'nuevo', 'Antonio Navarro García'),
    ('COMP_0130', 'contactado', 'Carlos McCann Nogales'),
    ('COMP_1155', 'reunion', 'Diego Aguirre Juarros')
) as v(company_id, status, employee_name)
join public.embat_employees e on e.ai_full_name = v.employee_name
where not exists (
  select 1 from public.embat_leads l
  where l.company_id = v.company_id
    and l.status in ('nuevo', 'contactado', 'reunion')
);
