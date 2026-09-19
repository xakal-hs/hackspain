# Workflow: autoresearch del credit score X-Ray

Reinventa el score desde la mirada de quien presta el dinero, lo somete a un consejo de agentes
y lo mejora con un bucle medible de testear → diagnosticar → cambiar → repetir.

**Estrategia: data-lead.** Los datos primero. Antes de formular una hipótesis se mira el dato; cada
premisa cita el **hecho** que la motiva (`evidencia`). La base de evidencia la produce la fase 0.

El orquestador es **Fable** por defecto (`ORQ_MODEL=...` para cambiarlo). Los consejeros son
subagentes de `.devin/agents/`, con los modelos de la preferencia de `AGENTS.md`:

| Perfil | Rol | Modelo |
|---|---|---|
| `prestamista` | Underwriter (Embat / fondo) | Claude Opus 5 |
| `cfo` | El prestatario | GPT-5.6 Sol |
| `auditor-datos` | ¿El dato sostiene la premisa? | GLM-5.3 |
| `riesgo-modelo` | Validador de modelo (Basilea) | Claude Opus 5 |
| `abogado-diablo` | Red team | GPT-5.6 Sol |
| `cobrador` | Recuperación | DeepSeek V4.1 Flash |
| `consolidador` | Consolida el consejo en `premisas.jsonl` (otra familia que el orquestador) | GPT-5.6 Sol |

## Un solo lanzamiento

```bash
bash .devin/workflows/autoresearch/run.sh cadena   # orden canónico 0→1→2→3→4→5, una sesión por fase (recomendado)
bash .devin/workflows/autoresearch/run.sh piloto   # fases 0-2 + runner, sin tocar el modelo (barato)
bash .devin/workflows/autoresearch/run.sh todo     # pipeline completo (fases 0-5) en un único chat
```

O, en un chat interactivo con Fable:

> Lee `.devin/workflows/autoresearch/ORQUESTADOR.md` y ejecútalo en modo piloto.

`cadena` es el más robusto: cada fase es su propia sesión (si una falla, no arrastra a las demás) y
respeta el **orden canónico** 0→1→2→3→4→5. El fichero `ORQUESTADOR.md` lleva un bloque de configuración
(`modo: piloto | completo`, `iteraciones_max`) y dos puertas de revisión (la política de préstamo y las
premisas centrales).

## Fases (por si quieres reanudar o inspeccionar)

| Fase | Comando | Qué produce | Toca el repo |
|---|---|---|---|
| 0 · Datos | `./run.sh fase0` | `salida/auditoria_datos.md` + `salida/analisis_datos.md` + `salida/hechos_datos.jsonl` + `salida/datos_limpieza.md`: anomalías cuantificadas, base de evidencia data-lead y decisión del consejo (limpiar/marcar/dejar) | Sí (capa de mapeo) |
| — · EDA | `./run.sh datos` | solo auditoría + análisis exploratorio (sin el consejo de limpieza) | No |
| 1 · Prestamista | `./run.sh fase1` | `salida/politica_prestamo.md`: a quién prestaríamos, con qué condiciones y cómo rankeamos (cada criterio apoyado en un hecho) | No (solo `salida/`) |
| 2 · Consejo | `./run.sh fase2` | `salida/premisas.jsonl`: **>100** preguntas falsables, con su test y su evidencia | No (solo `salida/`) |
| — · Runner | `./run.sh premisas` | `salida/premisas_resultado.md`: qué premisas pasan y cuáles fallan | No |
| 3 · Autoresearch | `./run.sh fase3` | Cambios en el modelo medidos contra las premisas; rama + PR | Sí, en su rama |
| 4 · Sala de situaciones | `./run.sh fase4` | Vista «Situaciones» en la SPA para analizar las +100 situaciones, más la demo proactiva (factoring/refi) | Sí |
| 5 · Documento del score | `./run.sh fase5` | `salida/documento_score.md`: cómo se calcula el score, con números reales y cuestionado por ≥5 subagentes | Sí |

Entre fase 2 y fase 3, revisa `salida/premisas_resultado.md` y marca las premisas **centrales**.

## El runner de premisas

`premisas.py` evalúa las premisas verificables contra `research/data/panel.parquet`, sus features
(`research/src/features.py`) y sus eventos (`research/src/targets.py`):

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build          # features+eventos+score
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build --oof     # + score_oof (fuera de grupo)
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py validate        # solo formato (congela umbrales)
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run             # evalúa (pasa/falla)
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py export          # salida/situaciones.json (UI)
```

El derivado incluye el **score** (`score`, `score_oof`, `band`, `prob_*`, `coverage`, `ood_share`,
`ec_<feature>` y `dec_<feature>`), no solo features y eventos. Así el bucle puede distinguir «premisa
mal» de «modelo mal» mirando la nota, la banda, la probabilidad y la explicación.

`export` escribe el array que consume la pestaña «Situaciones» de la fase 4: cada situación con su test,
su estado, su diagnóstico y hasta 6 `ejemplos` (empresa × mes) para inspeccionarla.

Tipos de test: `tasa_evento`, `auc`, `condicional`, `correlacion`, `cobertura`, `estadistico`, `banda`,
`probabilidad`, `contribucion` (¿la explicación señala la razón esperada?) y `ranking` (¿la lista ordenada
separa el evento?). `esperado` acepta `>0.6`, `<=0.25`, `==0`, `!=0`, `~0.5` y `entre 0.2 y 0.35`.

**Verifica sobre `score_oof`**, no sobre `score`: el score en muestra está calibrado con las mismas
empresas y sobreestima la separación.

### ¿Estamos mejorando? (PM)

`puntuacion.py` reduce un `reports/metrics_<tag>.json` a **una cifra**, la **PM** (media del AUC del
nivel frente a E1-E4), más los guardarraíles que no deben empeorar:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/puntuacion.py reports/metrics_ar000.json reports/metrics_ar001.json
```

Es el criterio de aceptación de la fase 3: un cambio entra solo si la PM sube y los guardarraíles no empeoran.

### La base de evidencia data-lead

`analisis_datos.py` produce la base sobre la que el consejo redacta premisas: distribuciones, nulos,
patrones temporales, correlaciones y la **asociación observada de cada candidato con cada evento**
(`salida/analisis_datos.md`), más un `hechos_datos.jsonl` con un hecho `H0xx` por línea. Es lo que una
premisa debe citar como `evidencia`.

```bash
cd research && uv run python ../.devin/workflows/autoresearch/analisis_datos.py
```

### Números reales del score

`score_datos.py` vuelca del artefacto servido (`artifacts/xray.joblib`) las features con sus pesos, la
escala publicada, las bandas, la calibración por evento y los coeficientes de probabilidad. Es la fuente
de verdad del documento técnico de la fase 5 (nada de números inventados):

```bash
cd research && uv run python ../.devin/workflows/autoresearch/score_datos.py --out ../.devin/workflows/autoresearch/salida/score_datos.md
```

### Esquema de una premisa

```json
{"id": "P001", "rol": "prestamista", "ambito": "liquidez",
 "premisa": "Una empresa con la caja negativa 3 meses seguidos tiene más impago que la media.",
 "evidencia": {"hecho": "H005", "observado": "caja<0 3m → tensión 0.59 vs 0.27 base", "n": 11223, "lift": 2.29, "auc": 0.53},
 "por_que": "Cambia la decisión de concesión y la condición del covenant.",
 "condicion": "si caja < 0 durante 3 meses, no prestar salvo factoring con recurso",
 "verificable": true,
 "test": {"tipo": "condicional", "objetivo": "incumplimiento_6m", "condicion": "cash_end < 0",
          "sobre": "lift", "esperado": ">1.2"}}
```

El campo `evidencia` (data-lead) es obligatorio: cita el hecho `H0xx` de `hechos_datos.jsonl` (o «propio»)
que motiva la premisa. `premisas.py validate` avisa de las que no lo traen.

Las premisas con `"verificable": false` (juicio humano/modelo) se listan aparte y no se evalúan.
`premisas.seed.jsonl` es la semilla de arranque, extraída de `DECISIONS.md` y `REFLEXIONES.md`;
la fase 2 la amplía a `salida/premisas.jsonl`.

## Red de seguridad

- Las fases que solo escriben en `salida/` (1 y 2) corren en `dangerous` y luego `run.sh` comprueba con
  `guard_solo_salida` que el repo quedó limpio: si algo cambió fuera de `salida/`, falla. Se usa
  `dangerous` porque en `-p` un comando rechazado por el filtro de `smart` corta la sesión sin escribir nada.
- La fase 3 no acepta un cambio si baja el AUC del nivel (E1-E4), empeora la separación del ranking,
  rompe los tests o deja de cuadrar la explicación aditiva. Todo cambio descartado se registra con su porqué.
- Los umbrales de las premisas se congelan con `premisas.py validate` **antes** de ver resultados, y las
  premisas sobre el score se verifican sobre `score_oof` (fuera de grupo), no sobre el score en muestra.
- El **forecaster de trayectoria (LGBM) queda fuera del bucle** y la demo proactiva usa una proyección de
  tesorería aritmética, no el forecaster.
- `salida/` no se versiona (informes, derivados y logs).

## Origen

- Estado y deuda técnica de partida: `research/ESTADO.md`.
- Dudas abiertas: `research/REFLEXIONES.md`.
- Marco de decisión: `context/scoring.md`.
