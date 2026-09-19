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

The app works with a small Nitro-hosted development portfolio out of the box. To score the
real portfolio, start the X-Ray backend (see `backend/README.md`) and point the app at it:

```bash
cd ../backend && uv sync && uv run uvicorn main:app --port 8080             # one terminal
cd ../frontend && XRAY_API_BASE=http://localhost:8080 pnpm dev               # another
```

Nitro then forwards `/api/companies` to the backend, keeping the browser on a same-origin API.
The contract lives in two mirrored files: `backend/models.py` (FastAPI validates every
response against it) and `app/types/portfolio.ts`. Change a field in one, change it in both.

## Structure

- `app/pages/`: file-based routes.
- `app/components/`: reusable product surfaces.
- `app/stores/`: Pinia UI state.
- `app/composables/`: TanStack Query server-state hooks.
- `app/assets/css/`: `tokens.css` (both themes), `main.css` (base, primitives,
  charts, landing) and `workspace.css` (the cockpit layer), loaded in that order.
- `app/utils/chart.ts`: scales and path builders shared by every chart.
- `server/api/`: Nitro server endpoints and backend adapters.
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
- `/dashboard/embat`: both sides, with anticipation as the headline number.

Each dashboard takes `?section=`. Empresa has `score` (default), `colchon` and
`divisa`; Embat has `resumen` (default), `cartera`, `senales`, `ofertas`, `monitor`,
`revenue` and `modelo`. A section the perspective does not have falls back to its
default. The earlier standalone routes `/cartera`, `/monitor`, `/escenarios` and
`/empresas/:id` now redirect into these sections.

Switch perspectives or exit using the user panel at the bottom of the desktop sidebar. On mobile, navigation and the user panel move above the content. Dashboard deep links redirect to demo sign-in when no demo-role cookie exists. This cookie is a UI convenience, not an authorization boundary.

The Empresa perspective and all product-only fields use explicit fixtures from
`app/data/demo.ts`. In the Embat perspective, `/api/companies` resolves three sources in
order, and the header chip says which one is live:

1. **`XRAY_API_BASE`** (`source: 'api'`) — the X-Ray backend. Real for all 1,286 companies:
   score, band, 3-month change, confidence, lender decision with its written reason, cash,
   months of cash, DSO, overdue invoices, margin and monthly flows. Names, sectors, the
   three-month forecast and the offer terms are still fixtures.
2. **Supabase** (`source: 'supabase'`) — treasury facts for the five featured companies,
   with mocked scores. Two caveats in `data/processed/panel_monthly.csv`: `pct_vencido` is
   overdue stock over three-month sales (a ratio clipped to `[0, 5]`, not the share of
   pending invoices past 60 days that the backend sends), and `runway_m` is unsanitised —
   it ranges from −812,870 to 35,208,424 months because sentinel cash balances are not
   removed. The backend path drops runway for those companies instead of scoring them.
3. **Fixtures** (`source: 'demo'`) — when neither is configured.

Missing values arrive as `null` and stay missing: a company without enough invoices shows
"no hay facturas suficientes", not a borrowed number. Roughly half the portfolio has no
DSO, so this matters more than it sounds.

The role cookie survives reloads until logout/browser session expiry.

Manual acceptance flow: enter as Empresa and walk its three treasury screens, then switch to Embat, search/select a company and inspect signals. Also check empty search, logout, direct-link redirect, and mobile/desktop layouts.

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
