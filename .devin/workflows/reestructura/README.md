# Workflow: reestructuración del repositorio con subagentes de Devin

Orquesta los perfiles de `.devin/agents/`. Los modelos siguen las preferencias de `AGENTS.md`:

- `researcher`: GLM 5.3, solo lectura.
- `implementer`: GPT-5.6 Sol.
- `reviewer`: Claude Opus 5.

El orquestador es GPT-5.6 Sol; se cambia con `ORQ_MODEL=...`. El brief de partida es [`research/ESTADO.md`](../../../research/ESTADO.md).

| Paso | Comando | Qué hace | Toca el repo |
|---|---|---|---|
| 1 | `./run.sh fase1` | 4 `researcher` en paralelo (datos y caja · features y eventos · modelo y servicio · documentación y entornos). El orquestador escribe el mapa y el plan por paquetes, y un `reviewer` lo critica | No: solo escribe en `salida/` |
| 2 | *Tú* | Lees `salida/fase1_mapa.md` y `salida/fase2_plan.md` y respondes las decisiones abiertas en `salida/decisiones_usuario.md` | — |
| 3 | `./run.sh baseline` (en `main`) | Tests, reentrenamiento y scoring del train, guardados como línea base | No |
| 4 | `./run.sh fase3` | En la rama `refactor/reestructura`: por cada paquete, `implementer` → `verificar.py check` → `reviewer` → commit. Al final, push y PR sin merge | Sí, en su rama |

**Red de seguridad.** `verificar.py` compara `scores_monthly.csv` y `forecast_latest.csv` con la línea base, con tolerancia 1e-6, y exige que los tests pasen. La reestructuración no puede cambiar ni un score. Los cambios de lógica quedan fuera de alcance y se anotan en `research/REFLEXIONES.md`.

`salida/` no se versiona. Contiene los informes, la línea base y los logs (`--export`).
