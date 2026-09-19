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

The app works with a small Nitro-hosted development portfolio out of the box. To use the existing FastAPI service, copy `.env.example` to `.env`, start the backend on port 8080, and set:

```bash
XRAY_API_BASE=http://localhost:8080
```

Nitro then forwards `/api/companies` to the backend, keeping the browser on a same-origin API.

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
- `/dashboard/banco`: decision, portfolio, signals and offers sent.
- `/dashboard/empresa`: own trajectory, what changed, and offers received.
- `/dashboard/embat`: both sides, with anticipation as the headline number.

Each dashboard takes `?section=` with `resumen` (default), `cartera` (not for
`empresa`), `senales` or `ofertas`. The earlier standalone routes `/cartera`,
`/monitor`, `/escenarios` and `/empresas/:id` now redirect into these sections.

Switch perspectives or exit using the user panel at the bottom of the desktop sidebar. On mobile, navigation and the user panel move above the content. Dashboard deep links redirect to demo sign-in when no demo-role cookie exists. This cookie is a UI convenience, not an authorization boundary.

The dashboards use explicitly fictional EUR fixtures from `app/data/demo.ts`, independently of `XRAY_API_BASE`. Sending an offer for Distribuciones Ibérica makes it available in Empresa; acceptance changes only demo state. Offers survive client-side navigation and reset on a full page reload. The role cookie survives reloads until logout/browser session expiry.

Manual acceptance flow: enter as Banco, search/select a company, send an offer for Distribuciones Ibérica, switch to Empresa and confirm acceptance, then switch to Embat and inspect signals. Also check empty search, disabled financing for Recolectora Sureste, logout, direct-link redirect, and mobile/desktop layouts.
