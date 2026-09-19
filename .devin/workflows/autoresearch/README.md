# Workflow: autoresearch del credit score X-Ray

Reinventa el score desde la mirada de quien presta el dinero, lo somete a un consejo de agentes
y lo mejora con un bucle medible de testear → diagnosticar → cambiar → repetir.

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

## Un solo lanzamiento

No hace falta ejecutar fase a fase. Hay un prompt orquestador que las encadena en un único chat:

```bash
bash .devin/workflows/autoresearch/run.sh piloto   # fases 1-2 + runner, sin tocar código (barato)
bash .devin/workflows/autoresearch/run.sh todo     # pipeline completo (fases 1-4) y PR
```

O, en un chat interactivo con Fable:

> Lee `.devin/workflows/autoresearch/ORQUESTADOR.md` y ejecútalo en modo piloto.

El fichero `ORQUESTADOR.md` lleva un bloque de configuración (`modo: piloto | completo`, `iteraciones_max`)
y dos puertas de revisión (la política de préstamo y las premisas centrales). En `piloto` se detiene antes
de tocar el modelo, que es lo prudente para la primera pasada.

## Fases (por si quieres reanudar o inspeccionar)

| Fase | Comando | Qué produce | Toca el repo |
|---|---|---|---|
| 1 · Prestamista | `./run.sh fase1` | `salida/politica_prestamo.md`: a quién prestaríamos, con qué condiciones y cómo rankeamos | No (solo `salida/`) |
| 2 · Consejo | `./run.sh fase2` | `salida/premisas.jsonl`: **>100** preguntas falsables, con su test | No (solo `salida/`) |
| — · Runner | `./run.sh premisas` | `salida/premisas_resultado.md`: qué premisas pasan y cuáles fallan | No |
| 3 · Autoresearch | `./run.sh fase3` | Cambios en el modelo medidos contra las premisas; rama + PR | Sí, en su rama |
| 4 · Sala de situaciones | `./run.sh fase4` | Vista «Situaciones» en la SPA para analizar las +100 situaciones, más la demo proactiva (factoring/refi) | Sí |

Entre fase 2 y fase 3, revisa `salida/premisas_resultado.md` y marca las premisas **centrales**.

## El runner de premisas

`premisas.py` evalúa las premisas verificables contra `research/data/panel.parquet`, sus features
(`research/src/features.py`) y sus eventos (`research/src/targets.py`):

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build   # cachea salida/derivado.parquet
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run     # evalúa salida/premisas.jsonl (o la semilla)
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py export  # salida/situaciones.json (para la UI)
```

`export` escribe el array que consume la pestaña «Situaciones» de la fase 4: cada situación con su test,
su estado, su diagnóstico y hasta 6 `ejemplos` (empresa × mes) para inspeccionarla.

Tipos de test: `tasa_evento`, `auc`, `condicional`, `correlacion`, `cobertura`, `estadistico`.
`esperado` acepta `>0.6`, `<=0.25`, `==0`, `!=0`, `~0.5` y `entre 0.2 y 0.35`.

### Esquema de una premisa

```json
{"id": "P001", "rol": "prestamista", "ambito": "liquidez",
 "premisa": "Una empresa con la caja negativa 3 meses seguidos tiene más impago que la media.",
 "por_que": "Cambia la decisión de concesión y la condición del covenant.",
 "condicion": "si caja < 0 durante 3 meses, no prestar salvo factoring con recurso",
 "verificable": true,
 "test": {"tipo": "condicional", "objetivo": "incumplimiento_6m", "condicion": "cash_end < 0",
          "sobre": "lift", "esperado": ">1.2"}}
```

Las premisas con `"verificable": false` (juicio humano/modelo) se listan aparte y no se evalúan.
`premisas.seed.jsonl` es la semilla de arranque, extraída de `DECISIONS.md` y `REFLEXIONES.md`;
la fase 2 la amplía a `salida/premisas.jsonl`.

## Red de seguridad

- La fase 3 no acepta un cambio si baja el AUC del nivel (E1-E4), rompe los tests o deja de cuadrar
  la explicación aditiva. Todo cambio descartado se registra con su porqué.
- El **forecaster de trayectoria (LGBM) queda fuera del bucle**: el objeto es el score de nivel.
- `salida/` no se versiona (informes, derivados y logs).

## Origen

- Estado y deuda técnica de partida: `research/ESTADO.md`.
- Dudas abiertas: `research/REFLEXIONES.md`.
- Marco de decisión: `context/scoring.md`.
