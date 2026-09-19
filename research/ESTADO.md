# Estado del proyecto X-Ray (19-sep-2026, tras la ronda 2 del autoresearch de la fase 3)

Resumen de lo construido hasta ahora, de las decisiones que siguen abiertas y de la deuda técnica acumulada. Sirve para ponerse al día y como brief de la reestructuración (`.devin/workflows/reestructura/`). El detalle de cada decisión está en `DECISIONS.md`, las dudas abiertas en `REFLEXIONES.md` y las features en `../features.md`.

## 1. Qué hace el sistema

Cada empresa, cada mes, recibe:

1. **Dos notas de 0 a 100** (D33). La **nota adversa** (la publicada) es una media ponderada de 17 features adimensionales cuyos pesos se calibran solo con los tres eventos adversos (tensión, incumplimiento, caída); la **nota de expansión** usa las mismas features con pesos calibrados con la expansión (`HealthScorer(target="expansion")`; aún no se sirve en la API). Catálogo revisado en la fase 3: entran `payroll_cv`, `oper_persistence_6m` y `oper_growth_12m`, salen `payroll_burden`, `net_margin_6m` y `growth_vs_12m` (D28-D30, D34). Cada feature se convierte en su percentil dentro del histórico de entrenamiento. Regla de banda: con menos de medio mes de caja propia la nota no es «sano» (D36).
2. **La probabilidad de cada evento a 6 meses.** Es nuevo en la v7: `prob_tension_6m`, `prob_incumplimiento_6m`, `prob_caida_6m`, `prob_expansion_6m` y `prob_adverso`.
3. **Una trayectoria a 1-3 meses con intervalo del 80 %.** La calcula mlforecast con LightGBM cuantílico y calibración conformal.
4. **Alertas.** Deterioro, mejora, bache frente a caída e inactividad.
5. **Una explicación exacta**, en puntos, de qué feature movió la nota.

Todo se sirve con FastAPI y una SPA de un solo fichero. La SPA tiene cartera, ficha de empresa con tesorería y simulador de escenarios, monitor, métricas y decisiones.

## 2. Cómo se calcula (v7 + autoresearch rondas 1 y 2, ramas `autoresearch/2026-09-19` y `autoresearch/2026-09-19-r2`)

| Paso | Qué hace | Dónde |
|---|---|---|
| Datos | CSV → parquet. Tipos de cambio validados contra el BCE y currency-api. Excluye traspasos internos e intragrupo. Reconstruye la caja hacia atrás desde el saldo final. Detecta facturas impagadas por `pending_amount` | `src/ingest.py`, `src/fx.py`, `src/panel.py` |
| Features | 17 ratios con suelo relativo a la escala de cada empresa, invariantes de ×1e-6 a ×1e6. Con caja centinela, `runway` es «sin dato» (D31) | `src/features.py` |
| Eventos (la "verdad") | v2: tensión de liquidez persistente (la financiación del grupo ya no censura como 0: la fila financiada queda sin etiqueta, D32), incumplimiento estricto (nómina o IVA; la cuota de deuda sale por inverificable, D35), caída estructural de cobros y expansión autofinanciada. v3 (jueces y anticipación, no calibran): `tension_np_raw_6m`, `entrada_estres_2m`, `rompe_caja_2m`, impago por tipo, `cura_3m`, variantes cortas. Los v1 se conservan para comparar. **El apagado ya no calibra:** el 52 % son desconexiones | `src/targets.py` |
| Pesos | Una logística por evento con pesos ≥ 0, normalizados y promediados **dentro de cada nota** (adversa: E1-E3; expansión: E4; D33) | `src/xray.py` (`HealthScorer`) |
| Escala | P5 → 15 y P95 → 85, más un EWMA con α = 0,5. Nota relativa al train (R01). Las probabilidades dan la escala absoluta (R02) | `src/xray.py` |
| Trayectoria | MLForecast directo con h = 1..3, 6 exógenas por horizonte y CQR. Con historia corta, respaldo AR(1) | `src/xray.py` (`TrajectoryForecaster`) |
| Validación | GroupKFold(5) por `group_id` × 3 cortes. Referencias: naive, AR(1) y arrastre del EWMA | `src/evaluate.py`, `src/anticipation.py` |

## 3. Resultados (validación con grupos que el modelo no ve)

Dos rondas del bucle de autoresearch (`.devin/workflows/autoresearch/`, fase 3). Ronda 1: 8 iteraciones, 4 aceptadas (D28-D31). Ronda 2: 9 iteraciones (`iter_100`-`iter_109`), **5 aceptadas (D32-D36)**, 4 descartadas con medida. Registro en `.devin/workflows/autoresearch/salida/iteraciones/` e `informe_autoresearch.md`. Etiquetas `ar000` (base ronda 1), `ar100` (base ronda 2 = ar007 + eventos v3) y **`ar107`** (final). **PM** = media del AUC del nivel frente a E1-E4 (`puntuacion.py`); desde la ronda 2 **se reporta pero no decide**: el objetivo es por evento (nota adversa frente a E1-E3; nota de expansión frente a E4) con IC bootstrap por grupo (`salida/iteraciones/notas_oof.py`).

**Aviso de comparabilidad.** Dos de los cinco cambios de la ronda 2 corrigen **etiquetas** (D32, D35): la tensión y el incumplimiento de `ar107` se miden contra etiquetas más limpias que las de `ar000`/`ar100`. La parte de mejora que es del juez y no del modelo está descompuesta en `iter_101/decision.md` (tensión: toda la subida +0,049 es de la etiqueta) e `iter_105/decision.md` (incumplimiento: +0,035 juez, +0,017 modelo). Los jueces **fijos** (`tension_np_raw_6m`, `entrada_estres_2m`, `rompe_caja_2m`, caída) sí son comparables.

| Métrica (nota adversa) | ar000 | ar100 (base r2) | **ar107 (final)** |
|---|---|---|---|
| **PM** (se reporta) | 0,615 | 0,626 | **0,659** |
| AUC del nivel frente a tensión de liquidez a 6 meses | 0,659 | 0,664 | **0,746** (etiqueta D32) |
| AUC frente a incumplimiento | 0,603 | 0,626 | **0,680** (etiqueta D35) |
| AUC frente a caída estructural de cobros | 0,588 | 0,616 | **0,627** |
| AUC frente a expansión (ya no es su trabajo) | 0,611 | 0,596 | 0,583 |
| **Nota de expansión** frente a expansión | — | — | **0,638** |
| AUC de caída ≥ 15 puntos a 3 meses (AR(1)) | 0,728 | 0,717 | **0,722** |
| AUC de subida ≥ 15 puntos a 3 meses | 0,725 | 0,744 | **0,757** |
| Mejora del MAE a 3 meses frente a AR(1) | 1,8 % | 2,6 % | **3,4 %** |
| Cobertura del intervalo del 80 % a 3 meses | 81 % | 81 % | 81 % |

Sobre **todas** las filas fuera de grupo (`notas_oof.py`, se por grupo entre paréntesis), ar100 → ar107: nota adversa (media E1-E3) 0,630 → **0,677**; tensión 0,700 → 0,791 (±0,017; de ello +0,049 es la etiqueta), **juez no circular `tension_np_raw_6m` 0,778 → 0,807 (±0,018)**, **entrada en estrés a 2 meses desde sana 0,579 → 0,602 (±0,020)**, rompe caja a 2 meses 0,563 → 0,607 (±0,031; 62 positivos), incumplimiento 0,573 → 0,623 (de ello +0,035 etiqueta), caída 0,617 → 0,618, mora AP estructural 0,510 → 0,560. Nota de expansión frente a expansión: 0,567 (nota única) → **0,628** (±0,032). Tensión del 20 % mejor por nota **9,5 % → 8,5 %**; del 20 % peor **45,9 % → 74,6 %** (etiqueta + modelo). Pesos finales de la nota adversa: `runway` 0,204, `payroll_cv` 0,122, `lc_util` 0,113, `activity_trend` 0,108, `oper_persistence_6m` 0,100; `debt_burden` 0,005 (fuera de facto, R16).

Premisas del consejo (270): al final de la ronda 2 fallan 54 (53 en la base, 12 de ellas porque documentaban las etiquetas viejas); de las **centrales**, 19 fallan (21 en la base). Arregladas en la ronda: P120 (sanas con < 0,5 meses de liquidez: 0 %), P152 (la deuda ya no resta a igual caja), P023, P174, P197, P207, P119, P249; P173 pasa de 0,937 a 0,058 (falta 0,002); P224 oscila alrededor de su umbral (0,40-0,46). Quince premisas que **documentaban el estado** de las etiquetas viejas (P002, P148, P203, P112, P113, P143, P144, P146, P147, P155, P163, P192…) fallan ahora por construcción y están anotadas como tales; P206 resultó **incorrecta** en su literal (pide «riesgo» en el primer mes inactivo donde C7 y los datos dicen «vigilar»).

La probabilidad publicada separa bien los extremos. Con nota 10, el 59 % de las empresas sufre algún evento adverso; con nota 90, el 12 % (cifras de la v7; pendiente de recalcular con las etiquetas D32/D35).

Antelación (v5/v6): el 48 % de 229 caídas estructurales se alertó antes de ocurrir, con 3 meses de mediana. Hay dos cosas sin resolver:

- **Bache frente a caída:** AUC 0,53.
- **Parpadeo:** el 23 % de las alertas se enciende y se apaga.

## 4. Qué hemos aprendido

- **El límite está en la información, no en la forma del modelo.** Una logística lineal y un LightGBM dan el mismo AUC. Añadir no linealidad por feature apenas aporta.
- **Promediar los pesos de varios eventos diluye cada uno.** Una logística por evento saca 0,63-0,76.
- **La caja cuadra con los movimientos.** El 16 % de meses que parecían descuadrados son **financiación intragrupo** (cash pooling); no es un error de reconstrucción.
- **Las grandes empresas tienen diez veces menos meses de caja** sin más eventos. `runway`, `payroll_burden` y `net_vol_6m` dependen del tamaño (R03).
- **Features del brainstorming con señal frente a los eventos v2:** `payroll_cv` (a la baja) y `oper_persistence_6m` **ya están en el score** (D28, D30). `lost_accel` y `yoy_inflow` son demasiado ruidosas; `payee_concentration` y `hhi_ap_6m` exigen rehacer el panel (R07).
- **Liquidez frente a crecimiento era un trade-off estructural de la nota única (R10), resuelto con dos notas (D33).** La nota adversa calibra solo con E1-E3 (tensión OOF 0,749 → 0,796) y la de expansión con E4 (0,568 → 0,597, y 0,638 con la tendencia de cobros en euros operativos, D34). La nota de expansión es además la mejor para la caída de cobros (0,635): la caída es momentum, no caja. Dentro de la nota adversa queda un trade-off más suave liquidez ↔ impago/caída (iter_105, iter_108): la liquidez pura la llevan `runway` en la ficha, la regla de banda (D36) y los vetos (fase 4).
- **Dos etiquetas estaban mal y se lo cargaban al modelo.** La tensión censuraba como «sana» a la filial cuyo hueco tapaba el grupo (D32: la misma nota pasa de 0,700 a 0,753 sin recalibrar); el incumplimiento tenía la mitad de sus positivos en cuotas de deuda que no son impagos verificables (D35: la nota las ordenaba al revés, 0,44). Antes de tocar un peso hay que preguntarse si el juez está bien.
- **Los guardarraíles de trayectoria no son comparables entre suavizados distintos** (iter_109): bajar α de 0,5 a 0,25 «mejora» el AUC de deterioro de 0,72 a 0,79 con AR(1) plano, porque un filtro más lento es más predecible; el precio es −30 % de reacción al arranque de la tensión y romper «inactivo ≠ sano». α se queda en 0,5.
- **Nueve premisas del consejo eran incorrectas** y se supo midiendo antes de tocar código (R17): la caja «implausible» es riqueza real, el «sesgo de arranque» era calendario, la póliza sin usar y no tener deuda sí protegen.
- **Se consultó a cinco familias de modelos** (GLM, DeepSeek, Qwen, Cursor Auto y Grok). Coinciden en usar la tensión de liquidez y el incumplimiento como anclas, en dejar el apagado fuera y en que la caída de cobros es un síntoma.

## 5. Decisiones abiertas (ver `REFLEXIONES.md`)

1. ¿Nota absoluta, con bandas fijadas por probabilidad, o relativa? (R01/R02)
2. ¿Percentiles por tamaño de empresa? (R03)
3. ¿Qué features del brainstorming quedan por probar? `payee_concentration` y `hhi_ap_6m` exigen panel nuevo (R07). La carga de deuda no ordena el riesgo entre quien tiene deuda (R16; con la cuota fuera de E2 su peso es 0,005). Candidatos medidos y descartados en la ronda 2: ventana fija de 12 meses para la tendencia (iter_103), neutro «medio» para las features de ERP (iter_106), calibrar con la caja propia (iter_108), EWMA más lento (iter_109).
4. ~~¿Una nota o varias?~~ Dos notas (D33). Pendiente: servir la nota de expansión en la API y la SPA (fase 4), y decidir si la tensión de **caja propia** (`tension_np_raw_6m`, `docs/eventos.md`) es ancla o solo juez: como ancla rompe la neutralidad al tamaño (iter_108, P180).
5. Bache frente a caída, e histéresis de alertas (R11/R12).
6. Preguntas a la organización: qué es el apagado en el generador, contra qué puntúa el leaderboard y si hay etiquetas.

## 6. Deuda técnica (qué justifica reestructurar)

1. **Hay dos reconstrucciones de caja.** Por un lado, `analysis/cash_history.py` (DuckDB + `src/mapping`, en EUR, validada al céntimo y determinista). Por otro, `research/src/panel.py` (polars, en moneda de la empresa). Hay que elegir una canónica.
2. **Hay dos entornos:** `requirements.txt` + `.venv` en la raíz (Streamlit, DuckDB) y `research/pyproject.toml` + uv.
3. **Las features se calculan en tres sitios:** `research/src/features.py`, `analysis/challenge_features.py` (que importa el panel de `research/src`) y `research/src/measure_events_v2.py` (las del brainstorming).
4. **Los eventos están duplicados:** `research/src/events_v2.py` (experimental) y `research/src/targets.py` (el oficial).
5. **Documentación desfasada:**
   - `research/README.md` y `METRICS.md` describen los eventos v1 y los resultados de v6.
   - `DECISIONS.md`, `reports/decisions.json` y `reports/metrics_app.json` (lo que ve la SPA) no se han regenerado con la v7.
6. **`src/decisions.py` mezcla tres cosas:** evidencia, textos y gráficas (unas 560 líneas).
7. **`reports/` tiene 64 ficheros**, entre métricas de v1 a v7, reviews, logs y parquet ignorados. Falta separar lo generado de lo documental.
8. **Hay código muerto:**
   - `research/app/mock_server.py`.
   - El flag `--from-cache` de `anticipation.py` apunta a `alerts_oof_v5`.
9. **Tests: 9** (API, OOD, escala, monotonía, explicación exacta). No hay tests de `targets.py`, `panel.py` ni del servidor.
10. **Hay dos apps:** la SPA en `research/app` (la demo) y Streamlit en `analysis/app.py` (explorador de caja).
