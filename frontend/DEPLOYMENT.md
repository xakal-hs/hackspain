# Despliegue en Vercel

El único servicio que se despliega es frontend/: Nuxt genera el cliente y Nitro ejecuta
server/api/** como backend serverless. No se despliega el FastAPI de backend/ ni se
empaquetan datos locales en una función.

## Primera conexión

1. Crea un proyecto Vercel desde este repositorio y fija **Root Directory** en frontend/.
   Vercel detecta Nuxt/Nitro; no hace falta vercel.json.
2. En GitHub, crea los secretos de Actions VERCEL_TOKEN, VERCEL_ORG_ID y
   VERCEL_PROJECT_ID. Los dos IDs se obtienen tras enlazar el proyecto con
   vercel link (en .vercel/project.json); nunca se versionan.
3. Configura en Vercel las variables por entorno. Las variables sólo de servidor no llevan
   el prefijo NUXT_PUBLIC_:

   | Variable | Alcance | Uso |
   | --- | --- | --- |
   | NUXT_PUBLIC_SUPABASE_URL | navegador y servidor | URL de Supabase |
   | NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY | navegador y servidor | clave pública |
   | NUXT_SUPABASE_SECRET_KEY | sólo servidor | lecturas server-side de Nitro |
   | NUXT_SUPABASE_JWKS_URL | sólo servidor | verificación de JWT |
   | AGENT_BASE_URL, AGENT_MODEL, AGENT_API_KEY | sólo servidor | proveedor compatible con OpenAI, si se usa |
   | AI_GATEWAY_API_KEY | sólo servidor | alternativa al proveedor anterior |

Los pull requests del mismo repositorio generan previews; main publica producción. El
workflow no intenta desplegar hasta que estén los tres secretos de Vercel, y tampoco expone
secretos a PRs procedentes de forks. La integración Git automática de Vercel debe quedar
desactivada para este proyecto: GitHub Actions es la única vía de despliegue y evita builds
duplicados.

## Backend Nuxt: estado y destino

Nitro ya sirve las rutas de directorio, ficha y flujo mediante Supabase. La meta de producción
es que las rutas bajo server/api/ lean los hechos y scores publicados en Supabase y que
/api/chat use esas mismas rutas/herramientas. Así todas las peticiones de producto viven en
el proyecto Nuxt y escalan con Vercel.

XRAY_API_BASE es una compatibilidad local con el FastAPI de experimentación: actualmente
alimenta el portfolio completo y las herramientas del asistente. No debe configurarse en
Vercel como dependencia de producción. Antes de eliminarlo, hay que portar esos lectores a
Nitro/Supabase y conservar los contratos de /api/companies, /api/companies/:id,
/api/companies/:id/explain y /api/companies/:id/decision. El cálculo pesado y la
publicación de los scores permanecen como un job reproducible separado; la API de Vercel sólo
consulta resultados ya publicados.

## Verificación local

    cd frontend
    corepack enable
    pnpm install --frozen-lockfile
    pnpm test
    pnpm typecheck
    pnpm build
