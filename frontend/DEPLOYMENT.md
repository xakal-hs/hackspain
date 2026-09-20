# Despliegue del frontend en Vercel

El proyecto Vercel de producción es `xakal-hackspain` y publica
<https://xakal-hackspain.vercel.app>. Sólo se despliega `frontend/`: Nuxt sirve
la aplicación y Nitro ejecuta las rutas de `server/api/`.

## Configuración del proyecto

- Equipo: `andres-santos-projects`
- Repositorio: `xakal-hs/hackspain`
- Rama de producción: `main`
- Root Directory: `frontend`
- Framework: Nuxt, detectado automáticamente
- Node.js: 22.x
- Gestor de paquetes: pnpm 10.20, fijado en `package.json`

La integración Git de Vercel genera un preview por pull request y despliega
producción al actualizar `main`. No se mantiene un workflow paralelo de
GitHub Actions para evitar despliegues duplicados.

La integración requiere que la GitHub App de Vercel tenga acceso a la
organización `xakal-hs`. Si todavía no está instalada, un owner de la
organización debe autorizarla en <https://github.com/apps/vercel> y después se
conecta el repositorio con `vercel git connect`. Hasta entonces, los mismos
artefactos se pueden publicar manualmente desde el directorio enlazado con
`vercel deploy` y `vercel deploy --prod`, sin añadir otro pipeline.

## Variables de entorno

Configurar estas variables en los entornos Preview y Production:

| Variable | Exposición | Uso |
| --- | --- | --- |
| `NUXT_PUBLIC_SUPABASE_URL` | Pública | URL del proyecto Supabase del frontend |
| `NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Pública | Clave publicable para el navegador |
| `NUXT_SUPABASE_SECRET_KEY` | Sólo servidor, sensible | Lecturas y escrituras desde Nitro |
| `NUXT_SUPABASE_JWKS_URL` | Sólo servidor | Verificación de JWT |
| `AGENT_BASE_URL` | Sólo servidor | Endpoint OpenAI-compatible de Helmcode |
| `AGENT_MODEL` | Sólo servidor | Modelo usado por el asistente |
| `AGENT_API_KEY` | Sólo servidor, sensible | Credencial de Helmcode |

Los valores viven en Vercel y nunca se versionan. `.vercelignore` impide que
los archivos locales `.env*` y `.data` entren en el contexto de despliegue.
Sin las dos primeras variables la aplicación arranca igual y sirve la cartera de
demostración. La clave de servicio nunca llega al navegador:
`company_decision_monthly`, `score_catalog` y `company_portfolio_latest` sólo
conceden `select` a `service_role`.

El asistente usa esas mismas rutas Nitro y no depende de FastAPI. No se
configuran `XRAY_API_BASE` ni `AI_GATEWAY_API_KEY`: el proveedor activo es
Helmcode mediante `AGENT_BASE_URL`, `AGENT_MODEL` y `AGENT_API_KEY`.

## Cómo se reparte el trabajo

    datos crudos ─► job reproducible (backend/, research/) ─► Supabase ─► Nitro ─► navegador
                    calcula la nota y la decisión            publica     consulta

El cálculo pesado ocurre una vez, fuera de la petición. Nitro sólo consulta resultados
ya publicados y los traduce al idioma del producto. Ninguna ruta de `server/api/`
puntúa ni decide nada, y **no hay un segundo servidor**: el FastAPI de `backend/` es el
job que calcula, no una API que levantar.

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
`/api/company-directory`, `/api/flujo/:id`, `/api/embat/*` y `/api/chat`. El agente de
`/api/chat` llama a esas mismas rutas por dentro: no tiene una fuente de datos propia.

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
`featured_companies_schema.sql`. `decision_schema.sql` es idempotente; volver a
ejecutarlo refresca la vista de cartera sin tocar los datos.

La decisión se calcula **sobre la nota ya publicada**, no sobre un score paralelo: por
eso el paso 2 va después del 1. Si se recalcula la nota y no la decisión, la acción que
se enseña deja de corresponder al número que se enseña.

## Rendimiento

`/api/companies` devuelve las 1.286 empresas con doce meses de flujos y de notas: unos
3,8 MB sin comprimir. Dos cosas lo sostienen en una función serverless:

* **La vista agrega en PostgreSQL.** Paginar en Nitro las 22.000 filas de panel y las
  21.500 de salud en cada petición costaba más que la consulta entera.
* **La lectura se cachea 5 minutos** (`defineCachedFunction`). Los datos sólo cambian
  cuando corre el job de publicación. Medido en local: 3,2 s en frío, 50 ms en caliente.

Se cachea la lectura y no el manejador, para que el respaldo de demostración —el que se
sirve cuando Supabase falla— no se quede pegado en la caché.

## Validación

Antes de mergear una PR:

```bash
cd frontend
pnpm test
pnpm typecheck
pnpm build
```

Después del despliegue se comprueban la portada, `/login`, `/api/companies`,
`/api/company-directory`, `/api/embat/caja` y una conversación real por
`/api/chat` tanto en preview como en la URL de producción.
