# Estado del proyecto X-Ray (19-sep-2026)

Resumen de lo construido hasta ahora, de las decisiones que siguen abiertas y de la deuda técnica acumulada. Sirve para ponerse al día y como brief de la reestructuración (`.devin/workflows/reestructura/`). El detalle de cada decisión está en `DECISIONS.md`, las dudas abiertas en `REFLEXIONES.md` y las features en `../features.md`.

## 1. Qué hace el sistema

Cada empresa, cada mes, recibe:

1. **Una nota de salud de 0 a 100.** Es una media ponderada de 17 features adimensionales. Cada feature se convierte en su percentil dentro del histórico de entrenamiento.
2. **La probabilidad de cada evento a 6 meses.** Es nuevo en la v7: `prob_tension_6m`, `prob_incumplimiento_6m`, `prob_caida_6m`, `prob_expansion_6m` y `prob_adverso`.
3. **Una trayectoria a 1-3 meses con intervalo del 80 %.** La calcula mlforecast con LightGBM cuantílico y calibración conformal.
4. **Alertas.** Deterioro, mejora, bache frente a caída e inactividad.
5. **Una explicación exacta**, en puntos, de qué feature movió la nota.

Todo se sirve con FastAPI y una SPA de un solo fichero. La SPA tiene cartera, ficha de empresa con tesorería y simulador de escenarios, monitor, métricas y decisiones.

## 2. Cómo se calcula (v7, en `main`: commit `42d6e50`)

| Paso | Qué hace | Dónde |
|---|---|---|
| Datos | CSV → parquet. Tipos de cambio validados contra el BCE y currency-api. Excluye traspasos internos e intragrupo. Reconstruye la caja hacia atrás desde el saldo final. Detecta facturas impagadas por `pending_amount` | `src/ingest.py`, `src/fx.py`, `src/panel.py` |
| Features | 17 ratios con suelo relativo a la escala de cada empresa, invariantes de ×1e-6 a ×1e6 | `src/features.py` |
| Eventos (la "verdad") | v2: tensión de liquidez persistente, incumplimiento estricto, caída estructural de cobros y expansión autofinanciada. Los v1 se conservan para comparar. **El apagado ya no calibra:** el 52 % son desconexiones | `src/targets.py` |
| Pesos | Una logística por evento con pesos ≥ 0, normalizados y promediados | `src/xray.py` (`HealthScorer`) |
| Escala | P5 → 15 y P95 → 85, más un EWMA con α = 0,5. Nota relativa al train (R01). Las probabilidades dan la escala absoluta (R02) | `src/xray.py` |
| Trayectoria | MLForecast directo con h = 1..3, 6 exógenas por horizonte y CQR. Con historia corta, respaldo AR(1) | `src/xray.py` (`TrajectoryForecaster`) |
| Validación | GroupKFold(5) por `group_id` × 3 cortes. Referencias: naive, AR(1) y arrastre del EWMA | `src/evaluate.py`, `src/anticipation.py` |

## 3. Resultados (validación con grupos que el modelo no ve)

| Métrica | v6 | v7 |
|---|---|---|
| AUC del nivel frente a tensión de liquidez a 6 meses | 0,604 | **0,657** |
| AUC del nivel frente a incumplimiento | 0,607 | 0,603 |
| AUC del nivel frente a caída estructural de cobros | **0,613** | 0,587 |
| AUC del nivel frente a expansión | 0,607 | 0,607 |
| AUC de caída ≥ 15 puntos a 3 meses (AR(1)) | 0,742 (0,703) | 0,725 (0,693) |
| AUC de subida ≥ 15 puntos a 3 meses (AR(1)) | 0,715 (0,683) | 0,730 (0,692) |
| Mejora del MAE a 3 meses frente a AR(1) | 3,8 % | 2,0 % |
| Cobertura del intervalo del 80 % a 3 meses | 82 % | 81 % |

La probabilidad publicada separa bien los extremos. Con nota 10, el 59 % de las empresas sufre algún evento adverso; con nota 90, el 12 %.

Antelación (v5/v6): el 48 % de 229 caídas estructurales se alertó antes de ocurrir, con 3 meses de mediana. Hay dos cosas sin resolver:

- **Bache frente a caída:** AUC 0,53.
- **Parpadeo:** el 23 % de las alertas se enciende y se apaga.

## 4. Qué hemos aprendido

- **El límite está en la información, no en la forma del modelo.** Una logística lineal y un LightGBM dan el mismo AUC. Añadir no linealidad por feature apenas aporta.
- **Promediar los pesos de varios eventos diluye cada uno.** Una logística por evento saca 0,63-0,76.
- **La caja cuadra con los movimientos.** El 16 % de meses que parecían descuadrados son **financiación intragrupo** (cash pooling); no es un error de reconstrucción.
- **Las grandes empresas tienen diez veces menos meses de caja** sin más eventos. `runway`, `payroll_burden` y `net_vol_6m` dependen del tamaño (R03).
- **Features del brainstorming con señal frente a los eventos v2:** `payee_concentration`, `lost_accel`, `payroll_cv`/`payroll_continuity_6m`, `hhi_ap_6m` y `oper_persistence_6m`. Todavía **no están en el score**.
- **Se consultó a cinco familias de modelos** (GLM, DeepSeek, Qwen, Cursor Auto y Grok). Coinciden en usar la tensión de liquidez y el incumplimiento como anclas, en dejar el apagado fuera y en que la caída de cobros es un síntoma.

## 5. Decisiones abiertas (ver `REFLEXIONES.md`)

1. ¿Nota absoluta, con bandas fijadas por probabilidad, o relativa? (R01/R02)
2. ¿Percentiles por tamaño de empresa? (R03)
3. ¿Qué features del brainstorming entran? Hay que validarlas de una en una (R07).
4. ¿Una nota o varias, por comprador? (R10)
5. Bache frente a caída, e histéresis de alertas (R11/R12).
6. Preguntas a la organización: qué es el apagado en el generador, contra qué puntúa el leaderboard y si hay etiquetas.

## 6. Deuda técnica (qué justifica reestructurar)

1. **Hay dos reconstrucciones de caja.** Por un lado, `analysis/cash_history.py` (DuckDB + `src/mapping`, en EUR, validada al céntimo y determinista). Por otro, `research/src/panel.py` (polars, en moneda de la empresa). Hay que elegir una canónica.
2. **Hay dos entornos:** `requirements.txt` + `.venv` en la raíz (Streamlit, DuckDB) y `research/pyproject.toml` + uv.
3. **Las features se calculan en tres sitios:** `research/src/features.py`, `analysis/challenge_features.py` (que importa el panel de `research/src`) y `research/src/measure_events_v2.py` (las del brainstorming).
4. **Los eventos están duplicados:** `research/src/events_v2.py` (experimental) y `research/src/targets.py` (el oficial).
5. **Documentación y artefactos generados:** `research/README.md`, `METRICS.md`, `DECISIONS.md` y
   los JSON que consume la SPA ya reflejan v7. El generador `src/decisions.py` también apunta a v7,
   pero una regeneración completa requiere `artifacts/xray.joblib`, que no está versionado; hasta
   reconstruirlo, `scripts/validate_commercial_audit.py` comprueba que los artefactos no deriven.
6. **`src/decisions.py` mezcla tres cosas:** evidencia, textos y gráficas (unas 560 líneas).
7. **`reports/` tiene 64 ficheros**, entre métricas de v1 a v7, reviews, logs y parquet ignorados. Falta separar lo generado de lo documental.
8. **Hay código muerto:**
   - `research/app/mock_server.py`.
   - El flag `--from-cache` de `anticipation.py` apunta a `alerts_oof_v5`.
9. **Tests: 9** (API, OOD, escala, monotonía, explicación exacta). No hay tests de `targets.py`, `panel.py` ni del servidor.
10. **Hay dos apps:** la SPA en `research/app` (la demo) y Streamlit en `analysis/app.py` (explorador de caja).
