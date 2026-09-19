# X-Ray frontend

The production frontend lives here. It is a Nuxt 4 application built on Vue 3's Composition API and TypeScript, with Vite for development and builds, Nitro for the server boundary, Pinia for client state, and TanStack Vue Query for remote state.

## Run locally

```bash
cd frontend
npm install
npm run dev
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
- `app/assets/css/`: design tokens and global component foundations.
- `server/api/`: Nitro server endpoints and backend adapters.
- `DESIGN_SYSTEM.md`: the translated X-Ray design system and usage rules.

## Checks

```bash
npm run typecheck
npm run build
```
