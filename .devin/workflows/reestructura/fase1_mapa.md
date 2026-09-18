# Fase 1 · Mapa y plan de reestructuración (solo lectura)

Eres el **orquestador** de una reestructuración del repositorio `hackspain` (reto X-Ray de Embat, HackSpain 2026). En esta fase **no modificas código**. Solo investigas y escribes dos ficheros de salida.

Lee primero:
- `AGENTS.md` y `README.md`.
- `research/ESTADO.md`: estado del proyecto y lista de deuda técnica. Es el punto de partida.
- `research/REFLEXIONES.md`.

## Objetivo de la reestructuración

Dejar un repositorio que un compañero nuevo, o el jurado, entienda en 10 minutos:

- Una sola fuente de verdad para cada pieza: datos/caja, features, eventos, modelo, validación, servicio y documentación.
- Sin duplicados ni código muerto.
- Un solo entorno reproducible.
- Documentación al día con la v7.

**Sin cambiar el comportamiento del sistema.** Los scores, las probabilidades y las previsiones deben salir idénticos; se comprueba con `.devin/workflows/reestructura/verificar.py`. Los cambios de lógica (nuevas features, nota absoluta, etc.) quedan **fuera de alcance**: van en `REFLEXIONES.md` como pendientes.

## Paso 1 · Cuatro investigaciones en paralelo

Lanza 4 subagentes `researcher` con `is_background: true`, uno por área. Todos deben devolver lo mismo:

- Inventario de ficheros con su responsabilidad y sus líneas clave (`file:line`).
- Quién importa a quién.
- Duplicados y en qué se diferencian **de verdad**; compara las implementaciones, no los nombres.
- Código muerto.
- Documentación desfasada.
- Riesgos de mover cada pieza: rutas cableadas, artefactos, scripts que la llaman o el frontend.

Las cuatro áreas:

- **A · Datos y caja.**
  - Ficheros: `research/src/ingest.py`, `fx.py` y `panel.py` frente a `analysis/cash_history.py`, `src/mapping/*` y `scripts/*`.
  - Pregunta clave: ¿son equivalentes las dos reconstrucciones de caja? Compáralas numéricamente sobre 20 empresas; puedes ejecutar comandos de solo lectura con `uv run` en `research/`.
  - ¿Cuál debería ser la canónica y qué perdería la otra?
- **B · Features y eventos.**
  - Ficheros: `research/src/features.py`, `targets.py`, `events_v2.py`, `measure_events_v2.py` y `analisis_escala.py`, `analysis/challenge_features.py`, `analysis/feature_criticality.py` y `features.md`.
  - ¿Qué partes de `events_v2.py` quedaron superadas por `targets.py`?
  - ¿Dónde viven las features del brainstorming?
- **C · Modelo, validación, servicio y demo.**
  - Ficheros: `research/src/xray.py`, `evaluate.py`, `anticipation.py`, `service.py`, `predict_submission.py` y `decisions.py`, `research/app/*` (incluido `mock_server.py`), `research/tests/*` y `analysis/app.py`.
  - ¿Qué consume la SPA exactamente (`app/API_CONTRACT.md`)?
  - ¿Qué genera `decisions.py` y qué parte está desfasada respecto a la v7?
- **D · Documentación, informes y entornos.**
  - Ficheros: `README.md`, `AGENTS.md`, `research/*.md`, `features.md`, `context/`, `research/reports/` (64 ficheros), `research/brainstorm/`, `requirements.txt` frente a `research/pyproject.toml`, `.gitignore`, `.cursor/`, `.agents/` y `skills-lock.json`.
  - ¿Qué es generado y qué es documental?
  - ¿Qué está desfasado?

## Paso 2 · Plan

Con los cuatro informes, escribe `.devin/workflows/reestructura/salida/fase1_mapa.md`. Debe incluir:

- La estructura actual en una tabla.
- Los hallazgos de cada área, con referencias `file:line`.
- Las decisiones que requieren al usuario, cada una con opciones y tu recomendación. Por ejemplo: ¿qué caja es la canónica? ¿Se fusionan los entornos?

Escribe después `.devin/workflows/reestructura/salida/fase2_plan.md`, con:

1. **Estructura objetivo:** el árbol de directorios final y qué se mueve, se fusiona, se borra o se reescribe.
2. **Paquetes de trabajo**, pequeños y ordenados. Cada uno con:
   - Objetivo.
   - Ficheros que **posee**: dos paquetes no pueden tocar el mismo fichero.
   - Pasos.
   - Criterio de aceptación: `cd research && uv run python ../.devin/workflows/reestructura/verificar.py check` en verde, más criterios propios.
   - Riesgo.
   - Si se puede paralelizar.
3. **Qué queda fuera** y va a `REFLEXIONES.md`.

## Paso 3 · Revisión adversarial del plan

Lanza un subagente `reviewer` sobre los dos ficheros. Pídele que busque:

- Pasos que cambiarían el comportamiento.
- Roturas de la SPA o de `predict_submission`.
- Paquetes que se pisan.
- Borrados de algo que alguien usa.
- Omisiones de la lista de deuda de `ESTADO.md`.

Incorpora sus objeciones al plan y añade al final de `fase2_plan.md` una sección «Revisión», con lo que aceptaste y lo que rechazaste y por qué.

## Reglas

- **Solo escribes** dentro de `.devin/workflows/reestructura/salida/`. No edites ni muevas nada más. No hagas commits.
- No leas ni muestres secretos. No copies claves de API a ningún fichero.
- No modifiques `data/`: los CSV originales no se tocan nunca.
- Escribe en español. Cada afirmación sobre el código debe llevar su referencia `file:line`.
- Termina con un resumen de 10 líneas: las decisiones que necesitas del usuario y el número de paquetes.
