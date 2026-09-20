# Despliegue en Vercel

El único servicio que se despliega es `frontend/`: Nuxt genera el cliente y Nitro ejecuta
`server/api/**` como backend serverless. **No hay un segundo servidor.** El FastAPI de
`backend/` no se despliega: es el job que calcula, no la API que sirve.

## Cómo se reparte el trabajo

    datos crudos ─► job reproducible (backend/, research/) ─► Supabase ─► Nitro ─► navegador
                    calcula la nota y la decisión            publica     consulta

El cálculo pesado ocurre una vez, fuera de la petición. Nitro solo consulta resultados ya
publicados y los traduce al idioma del producto. Ninguna ruta de `server/api/` puntúa ni
decide nada.

| Tabla / vista en Supabase | Qué publica | Quién la genera |
| --- | --- | --- |
| `company_health_monthly` | nota, banda, tendencia, pilares, confianza | `research/src/export_health_publication.py` |
| `company_health_driver_monthly` | contribución de cada señal a la nota | igual |
| `company_decision_monthly` | prestar / vigilar / no prestar, vetos, razones | `scripts/export_decision_publication.py` |
| `score_catalog` | pesos, escala, bandas, anclas, catálogo de vetos | igual |
| `company_portfolio_latest` (vista) | la cartera ya agregada, una fila por empresa | `supabase/decision_schema.sql` |
| `panel_monthly`, `company_static`, `companies` | hechos de tesorería | `scripts/load_supabase.py` |

Rutas que sirve Nitro: `/api/companies`, `/api/companies/:id`,
`/api/companies/:id/explain`, `/api/companies/:id/decision`, `/api/model`, `/api/vetos`,
`/api/company-directory`, `/api/flujo/:id` y `/api/chat`. El agente de `/api/chat` llama a
esas mismas rutas por dentro: no tiene una fuente de datos propia.

## Republicar después de recalcular

    # 1 · la nota (entorno de research/)
    cd research && uv run python src/export_health_publication.py --out ../supabase/export

    # 2 · la decisión y el catálogo del modelo
    python3 scripts/export_decision_publication.py

    # 3 · subirlo
    python3 scripts/load_health_publication.py
    python3 scripts/load_decision_publication.py

El esquema se aplica una sola vez, en este orden: `supabase/schema.sql`,
`health_schema.sql`, `profile_schema.sql`, `decision_schema.sql`,
`featured_companies_schema.sql`. `decision_schema.sql` es idempotente; volver a ejecutarlo
refresca la vista de cartera sin tocar los datos.

La decisión se calcula **sobre la nota ya publicada**, no sobre un score paralelo: por eso
el paso 2 va después del 1. Si se recalcula la nota y no la decisión, la acción que se
enseña deja de corresponder al número que se enseña.

## Primera conexión

1. Crea un proyecto Vercel desde este repositorio y fija **Root Directory** en `frontend/`.
   Vercel detecta Nuxt/Nitro; no hace falta `vercel.json`.
2. En GitHub, crea los secretos de Actions `VERCEL_TOKEN`, `VERCEL_ORG_ID` y
   `VERCEL_PROJECT_ID`. Los dos IDs salen de enlazar el proyecto con `vercel link`
   (`.vercel/project.json`); nunca se versionan.
3. Configura en Vercel las variables por entorno. Las variables sólo de servidor no llevan
   el prefijo `NUXT_PUBLIC_`:

   | Variable | Alcance | Uso |
   | --- | --- | --- |
   | `NUXT_PUBLIC_SUPABASE_URL` | navegador y servidor | URL de Supabase |
   | `NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | navegador y servidor | clave pública |
   | `NUXT_SUPABASE_SECRET_KEY` | sólo servidor | lecturas server-side de Nitro |
   | `NUXT_SUPABASE_JWKS_URL` | sólo servidor | verificación de JWT |
   | `AGENT_BASE_URL`, `AGENT_MODEL`, `AGENT_API_KEY` | sólo servidor | proveedor compatible con OpenAI, si se usa |
   | `AI_GATEWAY_API_KEY` | sólo servidor | alternativa al proveedor anterior |

   Sin las dos primeras la aplicación arranca igual y sirve la cartera de demostración.
   La clave de servicio nunca llega al navegador: `company_decision_monthly`,
   `score_catalog` y `company_portfolio_latest` solo conceden `select` a `service_role`.

Los pull requests del mismo repositorio generan previews; `main` publica producción. El
workflow no intenta desplegar hasta que estén los tres secretos de Vercel, y tampoco expone
secretos a PRs procedentes de forks. La integración Git automática de Vercel debe quedar
desactivada para este proyecto: GitHub Actions es la única vía de despliegue y evita builds
duplicados.

## Rendimiento

`/api/companies` devuelve las 1.286 empresas con doce meses de flujos y de notas: unos
3,8 MB sin comprimir. Dos cosas lo sostienen en una función serverless:

* **La vista agrega en PostgreSQL.** Paginar en Nitro las 22.000 filas de panel y las
  21.500 de salud en cada petición costaba más que la consulta entera.
* **La lectura se cachea 5 minutos** (`defineCachedFunction`). Los datos solo cambian
  cuando corre el job de publicación. Medido en local: 3,2 s en frío, 50 ms en caliente.

Se cachea la lectura y no el manejador, para que el respaldo de demostración —el que se
sirve cuando Supabase falla— no se quede pegado en la caché.

## Verificación local

    cd frontend
    corepack enable
    pnpm install --frozen-lockfile
    pnpm test
    pnpm typecheck
    pnpm build
