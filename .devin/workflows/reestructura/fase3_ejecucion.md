# Fase 3 · Ejecución del plan aprobado

Eres el **orquestador**. Ejecutas `.devin/workflows/reestructura/salida/fase2_plan.md`, ya aprobado por el usuario. Sus respuestas a las decisiones abiertas están en `.devin/workflows/reestructura/salida/decisiones_usuario.md`, y **prevalecen sobre el plan**.

## Preparación

1. Comprueba que el árbol de trabajo está limpio, salvo `.devin/workflows/reestructura/salida/`.
2. Crea la rama `refactor/reestructura` desde `main`.
3. Comprueba que existe `salida/baseline/`. Si no existe, **para** y avisa: la línea base se captura en `main`, antes de tocar nada, con `./run.sh baseline`.

## Bucle por paquete (en el orden del plan)

1. Lanza un subagente `implementer` con este encargo:
   - El paquete, con sus ficheros **propios**. No puede tocar otros.
   - Mover o borrar con `git mv` o `git rm`, para conservar el historial.
   - Actualizar las referencias en código y documentación.
   - Ejecutar `cd research && uv run python ../.devin/workflows/reestructura/verificar.py check`.
   - Si el paquete mueve los puntos de entrada, actualizar `TRAIN`, `PREDICT` y `TESTS` en `verificar.py`, **y nada más de ese fichero**.
2. Lanza un subagente `reviewer` sobre el `git diff` del paquete. Debe revisar:
   - Cambios de comportamiento.
   - Rutas rotas: grep de la ruta antigua en todo el repo, incluidos `research/app/static/index.html` y los `.md`.
   - Imports rotos.
   - Ficheros fuera de su propiedad.
   - Que `verificar.py` compara lo mismo que antes.
3. Si hay problemas bloqueantes, vuelve al `implementer` con ellos. Se permiten 2 intentos como máximo; después, para y avisa.
4. Si todo está en verde, haz un commit: `refactor(<área>): <qué>`. En el cuerpo pon el porqué y el resultado de `verificar.py`.

Solo paraleliza los paquetes que el plan marque como paralelizables **y** cuyos ficheros sean disjuntos.

## Cierre

1. Ejecuta `verificar.py check` una última vez (con `uv run` desde `research/`).
2. Levanta el servidor en el puerto 8090, para no chocar con el 8000 ni el 8080: `cd research && uv run uvicorn app.server:app --port 8090` (o la ruta nueva). Comprueba que `/api/companies`, `/api/company/<id>`, `/api/decisions` y `/api/metrics` responden 200. Para el servidor al terminar.
3. Actualiza `research/ESTADO.md`, sección 6: marca lo resuelto y añade lo que quedó fuera. Actualiza también `README.md` y `AGENTS.md` si cambió la estructura.
4. Haz push de la rama. Si `gh` está disponible, abre un PR contra `main` con el resumen de paquetes y la salida de `verificar.py`. **No hagas merge:** lo decide el usuario.

## Reglas

- **Sin cambios de comportamiento.** Si un paquete los exige, sácalo del alcance y anótalo en `REFLEXIONES.md`.
- No toques `data/`, no hagas commit de `research/data/`, `artifacts/`, `.venv/` ni `salida/`, y no escribas secretos.
- Sigue `AGENTS.md`, y `research/app/DESIGN.md` si se toca la SPA.
- Escribe en español. Termina con: la tabla de paquetes (hecho, fallido u omitido), los commits, el resultado de `verificar.py` y la URL de la rama o del PR.
