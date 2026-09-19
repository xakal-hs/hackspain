# Fase 2 · El consejo de agentes: las preguntas que el score debe poder responder

Eres el **orquestador** del workflow de autoresearch. Esta fase **no modifica código ni el modelo**. Su producto es un conjunto de **más de 100 premisas** verificables —las preguntas que hay que poder responder para que un credit score tenga sentido— escritas en `salida/premisas.jsonl`, listas para que el bucle de la fase 3 las testee.

Partes de `salida/politica_prestamo.md` (fase 1). Si no existe, para y avisa.

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

## Rondas

**Ronda 1 · Posiciones independientes.** Lanza los seis consejeros con `is_background: true`, todos con el mismo encargo: a partir de `politica_prestamo.md`, produce tus posiciones (premisa → decisión → condición → señal medible → cómo se verificaría). No ven a los demás. Guarda cada respuesta en `salida/consejo/r1_<rol>.md`.

**Síntesis.** El orquestador consolida las seis respuestas: agrupa por tema, marca acuerdos y contradicciones, y redacta un borrador de premisas en `salida/consejo/borrador.md`. Objetivo: 60-80 premisas antes de la ronda 2.

**Ronda 2 · Refutación.** Vuelve a lanzar los seis consejeros, cada uno con **el borrador completo y las posiciones anonimizadas de los otros cinco**. Encargo: añade premisas que falten, ataca las que creas falsas o mal definidas, y señala dónde tu interés choca con el de otro rol. Cada ataque cita el `id` o la frase atacada. Guarda en `salida/consejo/r2_<rol>.md`.

**Ronda 3 · Convergencia (opcional).** Si quedan contradicciones sin resolver, una pasada más centrada solo en ellas. No busques unanimidad: documenta el desacuerdo.

## Producto: `salida/premisas.jsonl`

Consolida todo en **> 100 premisas** (cuantas más, mejor; apunta a 120-150). Una por línea, JSON válido, con el esquema que lee `.devin/workflows/autoresearch/premisas.py` (ver `README.md`). Campos obligatorios:

- `id` (`P001`…), `rol` (autor), `ambito` (liquidez · cobros · pagos · deuda · observabilidad · comportamiento · estabilidad · calibracion · producto · recuperacion · gaming · sesgos).
- `premisa`: una frase, **falsable**. Nada de «la caja es importante»; sí «una empresa con la caja negativa 3 meses seguidos tiene más impago a 6 meses que la media».
- `por_que`: qué decisión de crédito cambia si la premisa es verdadera o falsa.
- `condicion` (cuando aplique): «si X entonces Y, salvo Z». Es el corazón del reto: *¿si lleva 3 meses con la caja rota le daría pasta? ¿bajo qué condiciones?*
- `verificable`: `true` si el runner puede testearla hoy; `false` si es juicio humano/modelo.
- `test`: si es verificable, el objeto con `tipo` (`tasa_evento`, `auc`, `condicional`, `correlacion`, `cobertura`, `estadistico`), las columnas y el `esperado`. Columnas disponibles: las 40 del panel, las 17 features de `research/src/features.py` y los eventos de `research/src/targets.py` (ver `README.md`).

### Cobertura mínima

- ≥ 20 de liquidez y caja; ≥ 15 de cobros/pagos; ≥ 12 de deuda y productos; ≥ 12 de observabilidad/comportamiento.
- ≥ 10 sobre **condiciones de concesión** («¿bajo qué condiciones sí?»), no solo sobre detección.
- ≥ 10 que solo se pueden juzgar con juicio (`verificable: false`), marcadas como tal con el motivo.
- ≥ 8 aportadas por cada rol (que ningún rol domine).

### La obligación de explicar

Toda premisa que se refiera a una **clasificación de rating** (lend / watch / decline, o banda sana/vigilar/riesgo) debe exigir que el sistema diga **por qué**: qué señales (Y, Z, K) movieron la nota y cuándo. Si una premisa solo pide el número y no la razón, reescríbela.

## Validación

Antes de cerrar, ejecuta el runner y comprueba que las premisas verificables se evalúan sin errores:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run
```

El `estado` que asigne el runner **no se decide aquí** (eso es la fase 3); aquí solo se comprueba que ninguna premisa está mal formada (`error`) y que hay al menos 30 verificables con `n` razonable.

## Reglas

- **Solo escribes** dentro de `.devin/workflows/autoresearch/salida/`. No edites código ni el modelo, no toques `data/`, no hagas commits.
- No leas ni muestres secretos.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line` o columna).
- Termina con: nº de premisas por ámbito y por rol, nº de verificables, las 5 contradicciones que quedan vivas y la lista de `id` que el consejo considera **centrales** (las que, si fallan, invalidan el sistema).
