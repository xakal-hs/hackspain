# research/: X-Ray, score de salud financiera y trayectoria

Sistema completo para el reto X Ray: un score interpretable por empresa y mes, una previsión de trayectoria con intervalos de confianza, un monitor de alertas y un simulador de escenarios servidos por una API y una SPA. Cada decisión está registrada con su porqué en [`DECISIONS.md`](DECISIONS.md) y en la pestaña «Decisiones» de la SPA, con gráficas calculadas sobre los datos.

Marco de decisión (consumidor → empresa, criticidad de la caja, output que no es solo un número): [`../context/scoring.md`](../context/scoring.md). Una empresa que vacía la caja disponible en poco tiempo debe mover el score mucho más que un deterioro leve de cobros o pagos. La SPA tiene que poder decirlo en lenguaje llano y sugerir prestar / vigilar / no prestar. El valor frente al banco es el rastro de tesorería que ellos no ven; la métrica no es única: cambia con la oferta y con el rol de quien mira.

## Arranque rápido

```bash
cd research
uv sync
uv run python src/ingest.py            # CSV de ../output (zip) o ../data (git lfs pull) -> data/*.parquet
uv run python src/fx.py                # tipos de cambio reales (BCE + currency-api) -> data/fx/
uv run python src/panel.py             # panel empresa × mes -> data/panel.parquet
uv run python src/service.py           # entrena el modelo final -> artifacts/xray.joblib
uv run python src/decisions.py         # registro de decisiones + métricas para la SPA
uv run uvicorn app.server:app --port 8080   # abrir http://localhost:8080
```

Otros comandos:

```bash
uv run pytest -q tests                              # 9 tests: API sklearn, OOD, escala, monotonía, explicación exacta, escenarios
cd src && uv run python evaluate.py v6 --small      # validación GroupKFold × 3 cortes (~5 min)
cd src && uv run python anticipation.py             # antelación, bache frente a caída y alertas out-of-fold (~20 min; --from-cache reutiliza las alertas)
uv run python src/predict_submission.py --csv-dir <carpeta_test> --out submission   # empresas nuevas
```

## Qué hay

| Pieza | Fichero | Qué hace |
| --- | --- | --- |
| Datos | `src/panel.py`, `src/fx.py` | Panel mensual con estas transformaciones: FX validado contra el BCE y currency-api; transferencias internas e intragrupo excluidas; caja y pólizas reconstruidas hacia atrás; facturas impagadas según `pending_amount`; dinámica de clientes; inactividad causal |
| Features | `src/features.py` | 17 ratios adimensionales con suelo relativo a la escala de la empresa (invariantes de ×1e-6 a ×1e6) |
| Eventos ancla | `src/targets.py` | Apagado, tensión de caja, declive (con medianas) y crecimiento a 6 meses. Solo se usan para calibrar y validar |
| **API sklearn** | `src/xray.py` | `HealthScorer.fit(X, y)/transform/score_panel` y `TrajectoryForecaster.fit/predict` (mlforecast + LightGBM cuantílico q10/q50/q90 + CQR), más `explain`, `alerts_for` y `fmt_feature` |
| Servicio | `src/service.py`, `app/server.py` | Modelo en memoria, simulador de escenarios (`apply_scenario`) y API FastAPI según `app/API_CONTRACT.md` |
| SPA | `app/static/index.html` | Cartera, ficha de empresa con abanico de previsión, tesorería por empresa (flujo de caja, liquidez, deuda y facturas), «por qué cambió», simulador de escenarios, monitor, métricas y decisiones. Lenguaje visual (tokens, superficies, elevación): `app/DESIGN.md` |
| Validación | `src/evaluate.py`, `src/anticipation.py` | GroupKFold(5) por `group_id` × cortes nov-25, feb-26 y may-26. Referencias: naive, AR(1) agrupado y arrastre del EWMA |

## Cómo funciona (en una frase por pieza)

1. **Score** = a + b · Σ w_f · s_f. s_f es el percentil de la feature, orientado y congelado en train; si falta, vale 50 (neutro). Los w_f salen de una logística con signo restringido por evento (3 adversos y 1 positivo). a y b llevan el P5 a 15 y el P95 a 85. El score publicado es un EWMA con α = 0,5. Como todo es lineal, **el score es la suma exacta de contribuciones por feature**, también después del suavizado.
2. **Trayectoria**: un MLForecast directo h = 1..3 con LightGBM cuantílico. Seis exógenas específicas por horizonte (`c_h{h}` = c retardada h meses, de modo que el modelo nunca ve el futuro) y calibración conformal de los intervalos.
3. **Monitor**: alerta de deterioro o mejora si la mediana prevista a 3 meses se mueve ≥ 10 puntos. La severidad depende del intervalo y de si la empresa aún parece sana. Bache frente a caída tras una caída mensual ≥ 10. Inactividad inmediata.
4. **Escenarios**: se modifican los drivers brutos (cobros, pagos, caja, nóminas, deuda, retrasos, vencidos, actividad…) en los últimos N meses. Los cambios de flujo se acumulan en la caja y se recalculan features, score, previsión y alertas.

## Resultados (v6, validación out-of-group, escala publicada 0-100)

| Pregunta del reto | Métrica | Modelo | AR(1) |
| --- | --- | --- | --- |
| Quién empieza a torcerse | AUC de caída ≥ 15 a 3 meses | **0,742** | 0,703 |
| … aunque aún parezca sana (quintil alto) | AUC en el quintil alto | **0,574** | 0,493 |
| Quién mejora | AUC de subida ≥ 15 a 3 meses | **0,715** | 0,683 |
| … desde abajo (quintil bajo) | AUC en el quintil bajo | **0,635** | 0,542 |
| Dónde actuar | Precisión en el 5 % con mayor caída / subida prevista | **47 % / 41 %** | 30 % / 25 % |
| Trayectoria | MAE a h1 / h3 | **4,5 / 11,2** | 5,4 / 11,7 |
| Confianza | Cobertura del intervalo 80 % en h1 / h3 | 84 % / 82 % | — |
| Nivel con sentido | AUC del score frente a evento adverso / apagado / crecimiento a 6 meses | 0,59 / 0,59 / 0,57 | — |
| Monitor | Precisión de la alerta de deterioro / mejora (tasa base) | 42 % (16 %) / 45 % (12 %) | — |

**Anticipación** (`anticipation.py`: origen móvil mensual, 9 cortes, fuera de fold). Detalle en `reports/anticipation_v5.json`:

| Pregunta | Resultado |
| --- | --- |
| Cuándo se vio venir | De 229 caídas estructurales, el 48 % tuvo alerta antes de cruzar a riesgo; antelación mediana de **3 meses** (hasta 11) |
| Alerta de deterioro / mejora | Precisión 34 % (tasa base 14 %, lift 2,4×) / 37 % (tasa base 13 %, lift 2,9×); recall 32 % / 8 % |
| Bache o caída | **No resuelto**: el 84 % de las caídas ≥10 persisten y el modelo casi no distingue las que rebotan (AUC 0,53) |
| Ruido | El 23 % de las alertas de deterioro se apagan al mes siguiente |

## Lo que no está resuelto (honestamente)

- **La mejora frente al AR(1) es modesta en el promedio** (+3,8 % de MAE a h3; a h1 solo un 2 % sobre el arrastre mecánico del EWMA). La ganancia real está en la cola y en las empresas que aún parecen sanas. Es la clase de señal que el enunciado pide, pero no es espectacular.
- **El nivel del score discrimina de forma moderada** (AUC ~0,6). Sin etiquetas, el ancla son eventos observables que son proxies. Hay que confirmar con la organización qué significa «apagarse» (¿cierre o baja de Embat?) y si existen etiquetas.
- **Agosto de 2026 tiene el doble de caídas** que la media, con un 25 % menos de facturas sincronizadas: puede ser un efecto de borde del dataset.
- **Bache frente a caída sin poder discriminante** (AUC 0,53). La regla actual acierta el 74 % porque casi todo es caída. Para mejorarla harían falta señales de recuperación: cobros que entran tras el mes malo o la caja mínima intramensual.
- **Ruido de alertas**: el 23 % se enciende y se apaga. Una histéresis (exigir dos meses seguidos) lo reduciría a cambio de antelación.
- Pendiente con valor: caja mínima intramensual (el review midió AUC 0,79 frente a tensión de caja), antigüedad de deuda por tramos y un agregado por grupo.

## Iteraciones y reviews

La tabla completa por versión está en la SPA (Métricas) y en `reports/metrics_*.json`. Hubo un review de 3 lentes en paralelo (validación, variables, OOD/API) tras v1, v5b y v6. Los hallazgos están en `reports/review_v1.md`, `reports/review_v5b.md` y `reports/review_v6.md` (este último aún sin aplicar); los aplicados figuran en el registro de decisiones. `reports/variables.html` es un atlas de variables generado por el agente de la lente de variables en el review de v5b.
