# X-Ray frontend

The production frontend lives here. It is a Nuxt 4 application built on Vue 3's Composition API and TypeScript, with Vite for development and builds, Nitro for the server boundary, Pinia for client state, and TanStack Vue Query for remote state.

## Run locally

The Nuxt toolchain requires a supported Node release. This workspace pins Node 22.22 in `.nvmrc`.

```bash
cd frontend
nvm install
nvm use
corepack enable
pnpm install
pnpm dev
```

The app works with a small Nitro-hosted development portfolio out of the box. To serve the
real portfolio, give it Supabase credentials — there is no second server to start:

```bash
cp .env.example .env    # fill NUXT_PUBLIC_SUPABASE_URL and NUXT_SUPABASE_SECRET_KEY
pnpm dev
```

Nitro reads the published X-Ray contract from Supabase and serves every product route
itself: portfolio, company, explanation, lender decision, model and vetoes. The score and
the decision are computed offline by a reproducible job (`research/`) and
published with `scripts/`; this project never recomputes them. The response contract lives
in `app/types/portfolio.ts`.

## Structure

- `app/pages/`: file-based routes.
- `app/components/`: reusable product surfaces.
- `app/stores/`: Pinia UI state.
- `app/composables/`: TanStack Query server-state hooks.
- `app/assets/css/`: `tokens.css` (both themes), `main.css` (base, primitives,
  charts, landing) and `workspace.css` (the cockpit layer), loaded in that order.
- `app/utils/chart.ts`: scales and path builders shared by every chart.
- `server/api/`: Nitro server endpoints that read the published contract in Supabase.
- `DESIGN_SYSTEM.md`: the palette, type, structure and motion rules.

## Checks

```bash
pnpm typecheck
pnpm build
```

## Troubleshooting

If Rolldown reports that `format` received `['underline', 'gray']`, the terminal is using Node 21 or
another unsupported release. Run `nvm use` inside this directory, confirm `node --version` reports
`v22.22.0`, and reinstall with `pnpm install`. The strict engine check now stops earlier with a clear
version error when the runtime is unsupported.

## Demo perspectives

- `/`: public landing, built around the moment a deterioration is detected.
- `/login`: simulated sign-in without credentials or real authentication.
- `/dashboard/empresa`: the company's own treasury — X-Ray Score, Colchón Dinámico and Divisa Inteligente.
- `/dashboard/embat`: Equipo Embat — caja del portfolio and the financing CRM.

Each dashboard takes `?section=`. Empresa has `score` (default), `flujo`, `credito` and
`divisa`; Embat has `caja` (default), `crm` and `equipo`. A section the perspective does not have
falls back to its default. The earlier standalone routes `/cartera`, `/monitor`,
`/escenarios` and `/empresas/:id` now redirect into Equipo Embat.

Switch perspectives or exit using the user panel at the bottom of the desktop sidebar. On mobile, navigation and the user panel move above the content. Dashboard deep links redirect to demo sign-in when no demo-role cookie exists. This cookie is a UI convenience, not an authorization boundary.

The Empresa perspective and all product-only fields use explicit fixtures from
`app/data/demo.ts`. In the Embat perspective, `/api/companies` resolves two sources, and
the header chip says which one is live:

1. **Supabase** (`source: 'supabase'`) — the published X-Ray contract, real for all 1,286
   companies: score, band, 3-month change, confidence, lender decision with its written
   reason and its vetoes, cash, months of cash, DSO, overdue invoices, margin and monthly
   flows. It reads `company_portfolio_latest`, a view that aggregates health, decision and
   panel in PostgreSQL so one request serves the whole portfolio. Names, sectors, the
   three-month forecast and the offer terms are still fixtures.
2. **Fixtures** (`source: 'demo'`) — when Supabase is not configured, or when reading it
   fails. Five companies, so `pnpm dev` works with no environment at all.

Missing values arrive as `null` and stay missing: a company without enough invoices shows
"no hay facturas suficientes", not a borrowed number. Roughly half the portfolio has no
DSO, so this matters more than it sounds.

There is no separate API server. Every product route is a Nitro route in this project and
reads results that a reproducible job already published; see `DEPLOYMENT.md`.

Empresa treasury screens read Supabase (`company-directory`, `flujo`). Equipo Embat:

1. **Caja** (`GET /api/embat/caja`) — the 20 `featured_companies`, with operational cash (`cash_end`, `net_op`, runway) and financial cash (debt service, outstanding, utilisation) from `panel_monthly` / `company_static`. Alert vs opportunity comes from the same rotura/excedente forecast Flujo de caja uses.
2. **Financiación** (`GET/POST /api/embat/leads`) — CRM pipeline. When the company clicks **Quiero pedir financiación**, a lead is assigned to a commercial from `embat_employees` with a generic email draft (no company data, fake Calendly).
3. **Equipo** (`GET /api/embat/employees`) — AM + customer success from `data/embat_am.csv` and `data/embat_cs.csv`, merged into `embat_employees`. Apply `supabase/embat_employees_schema.sql` on the frontend project (`frontend/.env`) so leads persist in Postgres; until then the server keeps a local file under `frontend/.data/` and serves the same employee list from `frontend/server/data/embat-employees.json`.

Reload employees with `python3 scripts/push_embat_employees.py` (uses `frontend/.env`, never the X-Ray source project).

The role cookie survives reloads until logout/browser session expiry.

Manual acceptance flow: enter as Empresa, open Flujo de caja, request financing; switch to Embat and find the lead in Financiación. Walk Caja filters (alerta / oportunidad). Also check logout, direct-link redirect, and mobile/desktop layouts.

## Supabase configuration

Keep local credentials in `frontend/.env`: Nuxt loads this file when run from
this directory. The repository ignores environment files; `.env.example`
contains placeholders only.

Browser code can read `useRuntimeConfig().public.supabaseUrl` and
`useRuntimeConfig().public.supabasePublishableKey`. The secret key is available
only to server code as `useRuntimeConfig().supabaseSecretKey`; never copy it
into public config or client code. `supabaseJwksUrl` is also configured on the server.
The original `SUPABASE_*` names are accepted for local development.

For deployed Nuxt servers, set `NUXT_PUBLIC_SUPABASE_URL`,
`NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NUXT_SUPABASE_SECRET_KEY`, and
`NUXT_SUPABASE_JWKS_URL` in the hosting environment. Production does not
automatically load `.env`. This config prepares the connection; the demo
sign-in and fixtures are still unchanged.

The project `.mcp.json` configures the Supabase MCP server for Claude Code.
Run `claude /mcp` in a regular terminal, select `supabase`, and choose
Authenticate to complete the browser OAuth flow with your Supabase account.

### Empresa seleccionada (Supabase)

La vista Empresa permite elegir las 1.286 entradas de `companies` desde el rail
(y su menú de cambio de vista). Se conserva la selección al navegar y recargar.
Los identificadores `COMP_…` son las etiquetas: `companies` no tiene un nombre
comercial. El sector se une por `company_id` desde
`company_business_profile.top_sector`; `top_sector_score` no es un score de
salud del sector y no se utiliza como tal.

- `/api/company-directory`: empresas y sectores, paginados en bloques de 500.
- `/api/company-directory/:id`: panel mensual, score, explicaciones del último
  score y monedas de cuentas de esa empresa. Las lecturas son independientes:
  si falla una fuente, se indica y se mantienen las demás.
- X-Ray Score: `company_health_monthly` aporta nota, banda, trayectoria y cambio
  a tres meses; `company_health_driver_monthly` aporta contribuciones. Las
  fechas de los gráficos corresponden a los meses recibidos.
- Frente al sector: `sector_health_monthly`, filtrado por `top_sector`. El selector
  Media / Mediana usa `score_mean` / `score_median` y conserva la elección al
  cambiar de empresa. Compara meses coincidentes con el score real, indica el
  último mes común y el número de empresas (`n`), sin sustituir ausencias por mocks.
  Ambas líneas se prolongan tres meses en trazo discontinuo: `shared/proyeccion.ts`
  añade a la EWMA del score su segundo término de Holt —la pendiente, amortiguada—
  ancladas en el último valor publicado, porque el score ya viene suavizado y volver
  a suavizar el nivel haría que la previsión arrancase por encima de una caída
  reciente. Se calcula al servir el detalle y no se guarda: `company_health_monthly`
  solo contiene meses cerrados, y `decision_schema` / `featured_companies` toman de
  ella el mes más reciente como el actual.
- Colchón: caja reconstruida y meses de pagos desde `panel_monthly`, en la
  moneda de la compañía; se avisa cuando `saldo_inconsistente` está marcado.
- Divisa: moneda de la empresa y monedas de `banking_products`.

**Pendiente / demo:** previsiones, recomendaciones del agente, colchón objetivo, excedentes,
depósitos, rentabilidad, operaciones, exposición FX, cotizaciones, pagos
previstos, coberturas y ahorros. Si no hay score se mantiene el
escenario demo rotulado; un dato de caja ausente se muestra como «Sin dato».
No se modifica ninguna tabla ni se incluyen secretos en el cliente. El acceso
sigue el modelo de demo existente; no representa autorización multiempresa de
un producto autenticado.

Validación: `pnpm typecheck`, `pnpm build`, consulta local de ambas rutas y cambio
entre empresas/las tres secciones en navegador; verificar que la selección se
conserva al recargar y que los meses reales no se etiquetan como «hoy».
