# Fase 2 · El consejo de agentes: las preguntas que el score debe poder responder

Eres el **orquestador** del workflow de autoresearch. Esta fase **no modifica código ni el modelo**. Su producto es un conjunto de **más de 100 premisas** verificables —las preguntas que hay que poder responder para que un credit score tenga sentido— escritas en `salida/premisas.jsonl`, listas para que el bucle de la fase 3 las testee.

Partes de `salida/politica_prestamo.md` (fase 1). Si no existe, para y avisa.

## La regla data-lead (no negociable)

**La estrategia del reto es data-lead: los datos primero.** Ninguna premisa entra en el consejo sin un **hecho de datos** detrás. La fase 0 dejó la base de evidencia en `salida/analisis_datos.md` y `salida/hechos_datos.jsonl` (un *hecho* `H0xx` por patrón observado: `condicion`, `evento`, `n`, `tasa_grupo`, `tasa_base`, `lift`, `auc`).

- Cada consejero **lee esa base y ejecuta sus propios análisis** (puede correr consultas de solo lectura con `uv run python` sobre `data/panel.parquet` y `salida/derivado.parquet`). No opina en abstracto: mira.
- Cada premisa lleva un campo **`evidencia`**: el hecho observado que la motiva, con su `hecho` (`H0xx` o «propio»), `observado` (lo que se ve), `n` y, si aplica, `lift`/`auc`. Sin `evidencia`, la premisa se descarta.
- Distingue **hecho** (exploratorio, en muestra) de **premisa** (confirmatoria, con umbral congelado y verificada fuera de grupo). El hecho motiva; la premisa es lo que se testea. Esa separación es lo que evita el sobreajuste: ver algo en los datos no es lo mismo que afirmarlo como ley.
- El consejo **re-mira** los hechos que la limpieza de la fase 0 cambia (intragrupo, caja implausible, alias de facturas): si una condición candidata se apoya en dato sucio, la premisa se marca como condicionada a la limpieza.

## El consejo

Seis consejeros, cada uno un subagente con su propio perfil, modelo y sesgo. El consejo **no busca consenso cómodo: busca romper las premisas débiles antes de que lo haga el jurado**.

| Perfil | Rol | Modelo | Qué vigila |
|---|---|---|---|
| `prestamista` | Underwriter de Embat / fondo | Opus 5 | ¿Prestaría? ¿Con qué condiciones? ¿Cómo rankea? |
| `cfo` | El prestatario | GPT-5.6 Sol | ¿Aceptaría la deuda? ¿Qué leería mal el sistema? |
| `auditor-datos` | Auditor de datos | GLM-5.3 | ¿El dataset puede demostrar la premisa? ¿Hay casos? ¿Está contaminada? |
| `riesgo-modelo` | Validador de modelo (Basilea) | Opus 5 | Explicabilidad, estabilidad, OOD, monotonicidad, sesgos |
| `abogado-diablo` | Red team | GPT-5.6 Sol | Gaming, falsos negativos, inversión de sentido |
| `cobrador` | Recuperación | DeepSeek V4.1 Flash | Qué pasa tras el impago, cuánta antelación hace falta |

## Rondas: un debate de verdad, no seis monólogos

El consejo **no existe para producir premisas: existe para romperlas**. La postura por defecto es la
**duda**: ninguna afirmación —de otro rol o del orquestador— se acepta sin una **medición** que la
sostenga. «Me parece razonable» no es un argumento; `n`, tasa, lift, AUC y `file:line` sí.

**Ronda 1 · Posiciones independientes (data-lead).** Lanza los seis consejeros con `is_background: true`, todos con el mismo encargo: lee `salida/analisis_datos.md` y `salida/hechos_datos.jsonl`, **corre tus propias consultas**, y a partir de `politica_prestamo.md` produce tus posiciones (hecho de datos → premisa → decisión → condición → señal medible → cómo se verificaría). No ven a los demás. Guarda cada respuesta en `salida/consejo/r1_<rol>.md`.

**Síntesis.** El orquestador consolida las seis respuestas: agrupa por tema, marca acuerdos y contradicciones, y redacta un borrador de premisas en `salida/consejo/borrador.md`. Objetivo: 60-80 premisas antes de la ronda 2.

**Ronda 2 · Interpelación cara a cara (NO anónima).** Vuelve a lanzar los seis consejeros, cada uno con **el borrador y las posiciones de los otros cinco, con su nombre**. El anonimato se quita a propósito: aquí no se protege a nadie. Encargo obligatorio de cada consejero:
- **Interpela por su nombre** a **al menos otros dos roles** con una pregunta **falsable** («`prestamista`: afirmas que la caja rota no recibe deuda; ¿por qué? muéstrame el lift con `n` y el `filtro`»).
- Para **al menos tres** afirmaciones ajenas: o las acepta **con el número que las sostiene**, o las **ataca** con el dato que las contradice. **Prohibido** aceptarlas sin medición.
- Responde a las preguntas que le dirijan los demás (se le pasan junto con el borrador).
- Señala dónde su interés **choca** con el de otro rol (es lo más valioso del consejo).
Guarda en `salida/consejo/r2_<rol>.md`. Cada ataque cita el `id` o la frase y trae su medición.

**Ronda 3 · Resolución por medición.** El orquestador recoge las interpelaciones sin zanjar y las
**mide** (consulta o `premisas.py run`). Cada disputa se cierra con un número, o se declara
`no_verificable` con el motivo. **No busques unanimidad: documenta el desacuerdo** y el dato que falta
para resolverlo. → `salida/consejo/r3_resolucion.md`.

**Consolidación (otra familia).** La redacción final de `salida/premisas.jsonl` **no la hace el orquestador**, que es Claude/Fable: la hace un subagente `consolidador` (GPT-5.6 Sol) para no sesgar la síntesis hacia una familia de modelo. Pásale todas las rondas y el borrador, y pídele que integre sin diluir, conserve el desacuerdo, **conserve el `evidencia` de cada premisa** (data-lead) y **congele los umbrales** sin mirar resultados. **No puede descartar un remedio accionable** propuesto por un rol (p. ej. «publicar una nota de expansión separada»): si es incómodo, entra igual, con su autor. Después, un `auditor-datos` (GLM-5.3) valida el formato con `premisas.py validate`.

## El debate de las preguntas abiertas (obligatorio)

Antes de cerrar, el consejo **debate las preguntas de `.devin/workflows/autoresearch/DEBATE.md`** con
las reglas de arriba (duda por defecto, interpelación por nombre, resolución por medición). Esas
preguntas —si las anclas E1-E4 son las correctas, si la etiqueta de tensión es circular, si tres de las
cuatro no existen para empresas nuevas, si una nota única diluye los eventos, si la regla de parada es
laxa— son **acusaciones a verificar o refutar**, no conclusiones. El consejo puede añadir preguntas.

Producto: **`salida/consejo/debate_veredicto.md`**, una fila por pregunta:

| pregunta | veredicto del consejo | medición que lo sostiene | quién disintió | acción propuesta |
|---|---|---|---|---|

Las preguntas nuevas que deje abiertas entran en `premisas.jsonl`; los **remedios accionables** que
apruebe (p. ej. notas separadas, arreglar la etiqueta) se convierten en candidatas de la fase 3.

## Producto: `salida/premisas.jsonl`

Consolida todo en **> 100 premisas** (cuantas más, mejor; apunta a 120-150). Una por línea, JSON válido, con el esquema que lee `.devin/workflows/autoresearch/premisas.py` (ver `README.md`). Campos obligatorios:

- `id` (`P001`…), `rol` (autor), `ambito` (liquidez · cobros · pagos · deuda · observabilidad · comportamiento · estabilidad · calibracion · producto · recuperacion · gaming · sesgos).
- `premisa`: una frase, **falsable**. Nada de «la caja es importante»; sí «una empresa con la caja negativa 3 meses seguidos tiene más impago a 6 meses que la media».
- `evidencia`: **obligatoria** (data-lead). El hecho observado que la motiva: `{"hecho": "H007"|"propio", "observado": "caja<0 → tensión 0.60 vs 0.27 base", "n": 11223, "lift": 2.42, "auc": 0.56}`. Si no hay hecho, la premisa no entra.
- `por_que`: qué decisión de crédito cambia si la premisa es verdadera o falsa.
- `condicion` (cuando aplique): «si X entonces Y, salvo Z». Es el corazón del reto: *¿si lleva 3 meses con la caja rota le daría pasta? ¿bajo qué condiciones?*
- `verificable`: `true` si el runner puede testearla hoy; `false` si es juicio humano/modelo.
- `test`: si es verificable, el objeto con `tipo` y sus campos. Tipos: `tasa_evento`, `auc`, `condicional`, `correlacion`, `cobertura`, `estadistico`, `banda` (¿en qué banda cae?), `probabilidad` (`prob_*`), `contribucion` (¿la explicación señala la razón esperada? `razon` + `sobre` top1/top2/negativo) y `ranking` (¿la lista ordenada separa el evento? `orden`, `n`). Columnas disponibles: las 40 del panel, las 17 features de `research/src/features.py`, los eventos de `research/src/targets.py`, y las del score: `score`, `score_oof`, `band`, `confidence`, `coverage`, `ood_share`, `prob_*`, `ec_<feature>`, `dec_<feature>` (ver `README.md`).

  **Verifica sobre `score_oof`, no sobre `score`.** El score en muestra está inflado; una premisa sobre el score que use `score` en vez de `score_oof` se evalúa sobre las mismas empresas con las que se calibró y no demuestra nada.

### Cobertura mínima

- ≥ 20 de liquidez y caja; ≥ 15 de cobros/pagos; ≥ 12 de deuda y productos; ≥ 12 de observabilidad/comportamiento.
- ≥ 10 sobre **condiciones de concesión** («¿bajo qué condiciones sí?»), no solo sobre detección.
- ≥ 10 que solo se pueden juzgar con juicio (`verificable: false`), marcadas como tal con el motivo.
- ≥ 8 aportadas por cada rol (que ningún rol domine).
- **El 100 % con `evidencia`** (data-lead): cada premisa cita el hecho de datos que la motiva. Una premisa sin hecho no se consolida.

### La obligación de explicar

Toda premisa que se refiera a una **clasificación de rating** (lend / watch / decline, o banda sana/vigilar/riesgo) debe exigir que el sistema diga **por qué**: qué señales (Y, Z, K) movieron la nota y cuándo. Si una premisa solo pide el número y no la razón, reescríbela.

## Validación (congelar umbrales antes de mirar resultados)

Primero valida **solo el formato**, sin evaluar, para congelar los umbrales antes de ver si pasan:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build --oof
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py validate
```

`validate` comprueba que cada premisa tiene sus campos, que el tipo es válido y que las columnas existen; **no** revela el `estado` (pasa/falla). Corrige todo lo que marque.

Después, y solo entonces, evalúa:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run
```

El `estado` que asigne el runner **no se decide aquí** (eso es la fase 3); aquí solo se comprueba que ninguna premisa queda en `error` y que hay al menos 30 verificables con `n` razonable. Si el consolidador ajustó umbrales después de ver resultados, márcalo como riesgo de sobreajuste en el informe.

## Reglas

- **Solo escribes** dentro de `.devin/workflows/autoresearch/salida/`. No edites código ni el modelo, no toques `data/`, no hagas commits.
- No leas ni muestres secretos.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line` o columna).
- Termina con: nº de premisas por ámbito y por rol, nº de verificables, las 5 contradicciones que quedan vivas y la lista de `id` que el consejo considera **centrales** (las que, si fallan, invalidan el sistema).
