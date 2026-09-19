# Fase 0 · Datos: limpieza y análisis exploratorio data-lead

Eres el **orquestador** del workflow de autoresearch. Esta es la **primera fase**: los datos pueden estar sucios y la suciedad contamina todo lo que venga después. Aquí la cuantificas, la discutes en el consejo y decides qué se limpia, qué se marca y qué se deja.

**La estrategia del reto es data-lead: los datos primero.** Antes de formular cualquier hipótesis (cualquier premisa de la fase 2), hay que mirar los datos. Esta fase produce la **base de evidencia** sobre la que el consejo redacta premisas falsables, no opiniones.

Regla de oro (de `AGENTS.md`): **los CSV crudos de `data/` no se tocan nunca.** La limpieza se aplica en una **capa de mapeo** al leer (como `src/mapping/`) o en `research/src/` (panel/features). Si el cambio afecta a las features, se mide con la PM y se decide en el bucle de la fase 3.

## Paso 1 · Evidencia cuantificada (suciedad)

```bash
cd research && uv run python ../.devin/workflows/autoresearch/auditoria_datos.py --out ../.devin/workflows/autoresearch/salida/auditoria_datos.md
```

Ese informe lista, con conteo y porcentaje, las anomalías de `transactions`, `invoices`, `balances`, `companies` y del panel: centinelas, FX ≤ 0, fechas imposibles, estados contradictorios, inactividad, intragrupo, moneda dominante, claves repetidas… **No es una limpieza, es la prueba.**

Lee también lo ya inventariado para **no relitigar**: `src/mapping/ISSUES.md` (catálogo de fallos y acciones), `research/DECISIONS.md` (D03 FX, D05 facturas, D06 mes parcial, D07 inactividad, D10 ceros) y `REFLEXIONES.md` (R08 intragrupo, R15 agosto-2026).

## Paso 1b · Análisis exploratorio data-lead (la base de evidencia)

```bash
cd research && uv run python ../.devin/workflows/autoresearch/analisis_datos.py
```

Produce dos artefactos que son el **cimiento de todo lo que viene después**:

- `salida/analisis_datos.md` — distribuciones, nulos, outliers, patrones temporales, correlaciones, persistencia y, sobre todo, **la asociación observada de cada candidato con cada evento** (tasa dentro vs fuera, lift, AUC, n).
- `salida/hechos_datos.jsonl` — un *hecho* por línea (id `H0xx`): patrón observado con su `condicion`, `evento`, `n`, `tasa_grupo`, `tasa_base`, `lift` y `auc`. **Es lo que una premisa debe citar como `evidencia`.**

Este paso no es decorativo: es la regla **data-lead**. Una hipótesis sin un hecho de datos detrás no entra en el consejo. Y el hecho es *exploratorio* (en muestra); la confirmación con umbral congelado y fuera de grupo es la fase 2. Distinguir «lo que veo» (hecho) de «lo que afirmo» (premisa) es lo que evita el sobreajuste.

Lee `analisis_datos.md` y anota en `salida/datos_limpieza.md` (o en un anexo `salida/hechos_datos.md`) los **hechos que la limpieza cambia**: si una anomalía sucia una condición candidata, dilo aquí; se re-mide en la fase 3 con la PM.

## Paso 2 · El consejo discute cada anomalía

Lanza en paralelo los perfiles del consejo, cada uno con **el informe de auditoría y el inventario previo**. Para **cada** anomalía con `n` relevante, cada rol responde desde su interés:

- `auditor-datos` (GLM): ¿es suciedad o realidad? ¿cuántos casos? ¿qué regla la limpia sin inventar? ¿introduce fuga?
- `riesgo-modelo` (Opus): ¿la limpieza cambia el score, la monotonía o la explicación? ¿sesga la validación?
- `prestamista` (Opus): ¿esta suciedad cambia una decisión de crédito (lend/watch/decline)?
- `cfo` (GPT): ¿la limpieza borra algo real de la empresa (estacionalidad, un pago puntual, un intragrupo legítimo)?
- `abogado-diablo` (GPT): ¿la limpieza se puede *gaming*? ¿esconde un riesgo real?
- `cobrador` (DeepSeek): ¿afecta a las señales de recuperación (caja mínima intramensual, cobros que entran tarde)?

Prohibido limpiar por inercia: cada acción debe tener un caso concreto que la justifique y un riesgo si no se hace.

## Paso 3 · Producto: `salida/datos_limpieza.md`

Una tabla con una fila por anomalía:

| anomalía | n | veredicto | acción | regla | impacto en el score | quién la pide |
|---|---|---|---|---|---|---|

- **veredicto**: `suciedad` · `real` · `ambiguo`.
- **acción**: `limpiar` (corregir al leer) · `marcar` (flag, sin tocar el valor) · `dejar` (es real).
- **regla**: la corrección concreta (p. ej. «`exchange_rate ≤ 0` → usar el tipo real del mes», D03).
- **impacto en el score**: si cambia features, se cuantifica en la fase 3 con la PM; si no, se dice por qué.

Cierra con la lista de **premisas de datos** (verificables) que salen del debate, para añadirlas a `premisas.jsonl` con el esquema de `premisas.py`.

## Paso 4 · Aplica lo acordado (capa de mapeo)

- Limpieza de **lectura**: en `src/mapping/` o `research/src/panel.py`/`features.py`, nunca reescribiendo `data/`.
- Limpieza de **valores centinela / signos / fechas**: marca con flags (`dq_*`) en lugar de recortar silenciosamente.
- Si un cambio toca las features o los eventos, **no lo cierres aquí**: déjalo listo y que la fase 3 mida si la PM mejora. Anótalo en `salida/datos_limpieza.md` como «pendiente de medir».
- Actualiza `src/mapping/ISSUES.md` con lo nuevo que hayas encontrado.

## Criterios de aceptación

- `salida/auditoria_datos.md` existe y cubre las cinco fuentes.
- `salida/analisis_datos.md` y `salida/hechos_datos.jsonl` existen y cubren los candidatos × los 4 eventos (la base de evidencia data-lead).
- `salida/datos_limpieza.md` tiene una fila por anomalía con veredicto, acción y regla, y al menos **una postura de cada rol** registrada.
- Ningún fichero de `data/` fue modificado (`git status data/` limpio).
- Las premisas de datos están en `premisas.jsonl`, **citan su hecho** (`evidencia`) y pasan `premisas.py validate`.

## Reglas

- Escribes en `.devin/workflows/autoresearch/salida/` y en `research/src/` (capa de mapeo) y `src/mapping/`. **Nunca** en `data/`.
- No leas ni muestres secretos.
- Escribe en español. Cada afirmación sobre los datos lleva su conteo (`auditoria_datos.py`) o su `file:line`.
- Termina con: nº de anomalías auditadas, cuántas se limpian / marcan / dejan, y qué queda pendiente de medir en la fase 3.
