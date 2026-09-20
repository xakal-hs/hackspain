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

Los valores viven en Vercel y nunca se versionan. `XRAY_API_BASE` es una
compatibilidad local con el backend de experimentación y no debe configurarse
en Vercel: producción consulta los datos publicados en Supabase desde Nitro.

## Validación

Antes de mergear una PR:

```bash
cd frontend
node --test tests/*.test.mjs
pnpm typecheck
pnpm build
```

Después del despliegue se comprueban la portada, `/login`, `/api/companies`,
`/api/company-directory` y `/api/embat/caja` tanto en preview como en la URL
de producción.
