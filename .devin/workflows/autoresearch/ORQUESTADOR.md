# Orquestador del workflow de autoresearch (punto de entrada único)

Ejecuta este fichero de arriba abajo en **un solo chat**. No lances las fases por separado: tú eres el orquestador y las conduces en orden, encadenando la salida de una con la entrada de la siguiente.

```yaml
modo: piloto          # piloto = fases 1-2 + runner, sin tocar código. completo = todo hasta la demo y el PR.
iteraciones_max: 12   # solo en modo completo (fase 3)
orq_model: claude-fable-5-1-high
```

Si el usuario no dice lo contrario, empieza en **piloto**: es barato, no toca el modelo y deja la política y las premisas listas para revisar. Para pasar a **completo**, cambia `modo` o pídelo en el chat.

## Preparación (una vez)

1. Lee `AGENTS.md`, `.devin/workflows/autoresearch/README.md`, `research/ESTADO.md` y `context/scoring.md`.
2. Comprueba que existe `research/data/panel.parquet`. Si no, para y avisa (hay que ejecutar antes `uv run python src/panel.py`).
3. `mkdir -p .devin/workflows/autoresearch/salida/logs`. Todo tu producto va en `salida/`.
4. Confirma al usuario el modo y arranca.

## Fase 1 · Prestamista

Sigue **íntegro** `.devin/workflows/autoresearch/fase1_prestamista.md`. Usa subagentes `researcher` en background para las cuatro investigaciones de apoyo. Escribe `salida/politica_prestamo.md`.

**Puerta 1 (breve).** Muestra al usuario un resumen de 10 líneas: el comprador, los 3 criterios de decisión y el nº de premisas candidatas. En modo piloto, pregunta si sigue o si quiere ajustar la política antes del consejo; si no responde o dice «sigue», continúa.

## Fase 2 · Consejo

Sigue **íntegro** `.devin/workflows/autoresearch/fase2_consejo.md`. Lanza los seis consejeros (`prestamista`, `cfo`, `auditor-datos`, `riesgo-modelo`, `abogado-diablo`, `cobrador`) con `run_subagent`, ronda 1 en paralelo (`is_background: true`), sintetiza, ronda 2 de refutación, y consolida `salida/premisas.jsonl` con **>100 premisas**.

Después ejecuta el runner tú mismo:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py build
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py run
```

Corrige las premisas mal formadas (estado `error`) hasta que no quede ninguna, y arregla las que tengan `n` irrisorio.

**Puerta 2 (importante).** Presenta `salida/premisas_resultado.md`: cuántas pasan, cuántas fallan y cuáles. Marca como **centrales** las que cumplan: (a) las señaló el consejo como centrales, o (b) tocan liquidez/deuda y fallan, o (c) su fallo cambiaría una decisión de concesión. Pide al usuario que confirme o ajuste la lista; si no responde, usa tu criterio y sigue.

**Si el modo es `piloto`, para aquí.** Deja `salida/premisas.jsonl`, `salida/politica_prestamo.md` y `salida/premisas_resultado.md`, y termina con el resumen y la recomendación de qué iterar primero. No toques código.

## Fase 3 · Autoresearch (solo modo completo)

Sigue **íntegro** `.devin/workflows/autoresearch/fase3_autoresearch.md`. Crea la rama `autoresearch/<fecha>`, captura la línea base y ejecuta el bucle hasta cumplir los criterios de parada (o `iteraciones_max`). Un cambio por iteración, con su diagnóstico y su registro en `salida/iteraciones/`. Usa subagentes `implementer` para el cambio y `reviewer` para revisarlo.

No aceptes ningún cambio que baje el AUC del nivel, rompa los tests o deje de cuadrar la explicación aditiva. El forecaster LGBM queda fuera.

## Fase 4 · Sala de situaciones (solo modo completo)

Sigue **íntegro** `.devin/workflows/autoresearch/fase4_demo.md`. Es la fase final y su producto es la **sala de situaciones**: una pestaña en la SPA donde el equipo analiza las +100 situaciones del consejo (filtros por ámbito/rol/estado/central, detalle con el diagnóstico y las empresas de ejemplo enlazadas a su ficha), más el caso destacado de demo proactiva (empresas nuevas que necesitan factoring o refi).

Exporta antes los datos de la UI: `cd research && uv run python ../.devin/workflows/autoresearch/premisas.py export`. Comprueba que el servidor responde 200 en `/api/situaciones` y `/api/proactive` (puerto 8090). Al terminar, para el servidor.

## Cierre

1. Actualiza `research/ESTADO.md`, `DECISIONS.md` y `REFLEXIONES.md` con lo aprendido.
2. `salida/informe_autoresearch.md` con la tabla de premisas antes/después y el AUC por evento.
3. Haz push de la rama y abre un PR contra `main` con el resumen. **No hagas merge:** lo decide el usuario.
4. Termina con un resumen de 15 líneas: modo, situaciones generadas, cuántas fallaban al inicio y al final, centrales que siguen fallando, cambios aceptados y descartados, y la ruta de la pestaña «Situaciones».

## Reglas (valen para todo el chat)

- En `piloto` **no tocas código**: solo escribes en `salida/`.
- No toques `data/` ni los CSV originales. No escribas secretos en ningún fichero.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line`).
- Los consejeros y el implementer no ven tu conversación: dales contexto completo en cada encargo.
- No inventes modelos: usa los perfiles de `.devin/agents/` (los modelos ya están pinneados).
