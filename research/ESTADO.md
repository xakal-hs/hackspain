# Estado del proyecto X-Ray (19-sep-2026, tras el autoresearch de la fase 3)

Resumen de lo construido hasta ahora, de las decisiones que siguen abiertas y de la deuda técnica acumulada. Sirve para ponerse al día y como brief de la reestructuración (`.devin/workflows/reestructura/`). El detalle de cada decisión está en `DECISIONS.md`, las dudas abiertas en `REFLEXIONES.md` y las features en `../features.md`.

## 1. Qué hace el sistema

Cada empresa, cada mes, recibe:

1. **Una nota de salud de 0 a 100.** Es una media ponderada de 17 features adimensionales (catálogo revisado en la fase 3: entran `payroll_cv` y `oper_persistence_6m`, salen `payroll_burden` y `net_margin_6m`; D28-D30). Cada feature se convierte en su percentil dentro del histórico de entrenamiento.
2. **La probabilidad de cada evento a 6 meses.** Es nuevo en la v7: `prob_tension_6m`, `prob_incumplimiento_6m`, `prob_caida_6m`, `prob_expansion_6m` y `prob_adverso`.
3. **Una trayectoria a 1-3 meses con intervalo del 80 %.** La calcula mlforecast con LightGBM cuantílico y calibración conformal.
4. **Alertas.** Deterioro, mejora, bache frente a caída e inactividad.
5. **Una explicación exacta**, en puntos, de qué feature movió la nota.

Todo se sirve con FastAPI y una SPA de un solo fichero. La SPA tiene cartera, ficha de empresa con tesorería y simulador de escenarios, monitor, métricas y decisiones.

## 2. Cómo se calcula (v7 + autoresearch, rama `autoresearch/2026-09-19`)

| Paso | Qué hace | Dónde |
|---|---|---|
| Datos | CSV → parquet. Tipos de cambio validados contra el BCE y currency-api. Excluye traspasos internos e intragrupo. Reconstruye la caja hacia atrás desde el saldo final. Detecta facturas impagadas por `pending_amount` | `src/ingest.py`, `src/fx.py`, `src/panel.py` |
| Features | 17 ratios con suelo relativo a la escala de cada empresa, invariantes de ×1e-6 a ×1e6. Con caja centinela, `runway` es «sin dato» (D31) | `src/features.py` |
| Eventos (la "verdad") | v2: tensión de liquidez persistente, incumplimiento estricto, caída estructural de cobros y expansión autofinanciada. Los v1 se conservan para comparar. **El apagado ya no calibra:** el 52 % son desconexiones | `src/targets.py` |
| Pesos | Una logística por evento con pesos ≥ 0, normalizados y promediados | `src/xray.py` (`HealthScorer`) |
| Escala | P5 → 15 y P95 → 85, más un EWMA con α = 0,5. Nota relativa al train (R01). Las probabilidades dan la escala absoluta (R02) | `src/xray.py` |
| Trayectoria | MLForecast directo con h = 1..3, 6 exógenas por horizonte y CQR. Con historia corta, respaldo AR(1) | `src/xray.py` (`TrajectoryForecaster`) |
| Validación | GroupKFold(5) por `group_id` × 3 cortes. Referencias: naive, AR(1) y arrastre del EWMA | `src/evaluate.py`, `src/anticipation.py` |

## 3. Resultados (validación con grupos que el modelo no ve)

Bucle de autoresearch (`.devin/workflows/autoresearch/`, fase 3): 8 iteraciones, 4 cambios aceptados (D28-D31), 2 descartados con medida, 2 de diagnóstico. Registro completo en `.devin/workflows/autoresearch/salida/iteraciones/` e `informe_autoresearch.md`. Etiquetas `ar000` (base = v7 sobre el panel con flags de calidad) y `ar007` (final). **PM** = media del AUC del nivel frente a E1-E4 (`puntuacion.py`).

| Métrica | v6 | v7 | ar000 (base) | **ar007 (final)** |
|---|---|---|---|---|
| **PM** | — | 0,614 | 0,615 | **0,626** |
| AUC del nivel frente a tensión de liquidez a 6 meses | 0,604 | 0,657 | 0,659 | **0,664** |
| AUC del nivel frente a incumplimiento | 0,607 | 0,603 | 0,603 | **0,626** |
| AUC del nivel frente a caída estructural de cobros | 0,613 | 0,587 | 0,588 | **0,616** |
| AUC del nivel frente a expansión | 0,607 | 0,607 | 0,611 | 0,596 |
| AUC de caída ≥ 15 puntos a 3 meses (AR(1)) | 0,742 (0,703) | 0,725 (0,693) | 0,728 | 0,716 |
| AUC de subida ≥ 15 puntos a 3 meses (AR(1)) | 0,715 (0,683) | 0,730 (0,692) | 0,725 | **0,743** |
| Mejora del MAE a 3 meses frente a AR(1) | 3,8 % | 2,0 % | 1,8 % | **2,7 %** |
| Cobertura del intervalo del 80 % a 3 meses | 82 % | 81 % | 81 % | 82 % |

Sobre **todas** las filas fuera de grupo (no solo los 3 cortes; `pm_oof.py`): PM 0,6067 → 0,6143; tensión 0,700 → 0,702, incumplimiento 0,557 → 0,572, caída 0,596 → 0,616, expansión 0,573 → 0,567 (±0,014). La tensión del 20 % mejor por nota baja de 9,6 % a 9,5 % y la del 20 % peor sube de 45,4 % a 45,9 %.

Premisas del consejo (150): 27 fallaban al inicio, 29 al final, pero de las **19 centrales** pasan de 11 fallos a 9; dos se arreglaron (P172 nómina, P199 margen), nueve se reclasificaron como premisas incorrectas con evidencia (R17) y cinco quedan como «correctas para el prestamista, no para una sola nota» (R10). Las que cambian de estado fuera de las centrales son umbrales frágiles (P023, P177, P179, P197) fijados al filo tras medir en muestra.

La probabilidad publicada separa bien los extremos. Con nota 10, el 59 % de las empresas sufre algún evento adverso; con nota 90, el 12 %.

Antelación (v5/v6): el 48 % de 229 caídas estructurales se alertó antes de ocurrir, con 3 meses de mediana. Hay dos cosas sin resolver:

- **Bache frente a caída:** AUC 0,53.
- **Parpadeo:** el 23 % de las alertas se enciende y se apaga.

## 4. Qué hemos aprendido

- **El límite está en la información, no en la forma del modelo.** Una logística lineal y un LightGBM dan el mismo AUC. Añadir no linealidad por feature apenas aporta.
- **Promediar los pesos de varios eventos diluye cada uno.** Una logística por evento saca 0,63-0,76.
- **La caja cuadra con los movimientos.** El 16 % de meses que parecían descuadrados son **financiación intragrupo** (cash pooling); no es un error de reconstrucción.
- **Las grandes empresas tienen diez veces menos meses de caja** sin más eventos. `runway`, `payroll_burden` y `net_vol_6m` dependen del tamaño (R03).
- **Features del brainstorming con señal frente a los eventos v2:** `payroll_cv` (a la baja) y `oper_persistence_6m` **ya están en el score** (D28, D30). `lost_accel` y `yoy_inflow` son demasiado ruidosas; `payee_concentration` y `hhi_ap_6m` exigen rehacer el panel (R07).
- **Liquidez frente a crecimiento es un trade-off estructural (R10).** Dar más criticidad a la caja (peso ×2 al evento de tensión, o la regla «< 0,5 meses de liquidez → no sano») sube la tensión hasta +0,059 de AUC y baja la expansión y la caída: las empresas sanas con poca caja crecen 2,3× más. Una sola nota no puede servir al prestamista y ordenar la expansión a la vez; la salida es una **nota del prestamista** junto a la general (fase 4).
- **Nueve premisas del consejo eran incorrectas** y se supo midiendo antes de tocar código (R17): la caja «implausible» es riqueza real, el «sesgo de arranque» era calendario, la póliza sin usar y no tener deuda sí protegen.
- **Se consultó a cinco familias de modelos** (GLM, DeepSeek, Qwen, Cursor Auto y Grok). Coinciden en usar la tensión de liquidez y el incumplimiento como anclas, en dejar el apagado fuera y en que la caída de cobros es un síntoma.

## 5. Decisiones abiertas (ver `REFLEXIONES.md`)

1. ¿Nota absoluta, con bandas fijadas por probabilidad, o relativa? (R01/R02)
2. ¿Percentiles por tamaño de empresa? (R03)
3. ¿Qué features del brainstorming quedan por probar? `payee_concentration` y `hhi_ap_6m` exigen panel nuevo (R07). La carga de deuda no ordena el riesgo entre quien tiene deuda (R16).
4. ¿Una nota o varias, por comprador? El trade-off liquidez/crecimiento está medido; propuesta: nota del prestamista con `EVENT_W` tensión ×2 (R10).
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
