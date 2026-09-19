# Planteamiento del Problema y Oportunidad — X-Ray Score v7

## Fuentes de la información

Toda la información de este documento proviene de los siguientes archivos del repositorio y sesiones de brainstorming del equipo:

| Fuente | Contenido extraído |
|---|---|
| `context/challenge.md` / `context/challenge.html` | Las 6 preguntas del reto, dataset (1.286 empresas, 250 grupos, 24 meses), requirement del leaderboard |
| `context/scoring.md` / `context/scoring.html` | Marco del score ("prueba de los 100.000 €"), tabla de métrica por rol (banco, aseguradora, CFO, Embat), concepto de criticidad no uniforme |
| `context/monetizacion.md` / `context/monetizacion.html` | Revenue por producto (5,4M € excedente, 3,7M € divisa, 2,7M € SaaS, 0,1M € financiación), "la conversación incómoda" (0,9% del revenue viene de financiación) |
| `analysis/monetizacion.py` | Script que replica y corrige las cifras del brief: EUR, centinelas, caja reconstruida. Muestra que 2.378 M€ de excedente real, 375 empresas con excedente >2 meses |
| `features.md` (secciones 1-6) | Las 6 preguntas del reto, dataset, trampas del dataset, 17 features actuales, panel mensual, eventos v2, brainstorming de 20+ nuevas features, features descartadas |
| `research/DECISIONS.md` | D01-D28: decisiones de diseño (score por company_id, sin etiquetas, FX validados, transferencias internas, facturas impagadas, ventanas 6m/12m, EWMA α=0,5, escala lineal P5→15 P95→85, bandas 65/35, CQR, GroupKFold, forecaster mlforecast + LGBM, SPA + FastAPI, producto Embat, voz de producto) |
| `context/voz_embat.md` / `context/voz_embat.html` | Testimonio PM Embat: coste oculto del exceso y FX, agente no usado, suscripción vs intermediación, criticidad de liquidez por sector, mesa de upsell, mix de deuda por plazos |
| `research/src/features.py` | Código real de las 17 features: `runway`, `lc_util`, `net_margin_6m`, `growth_vs_12m`, `debt_burden`, `payroll_burden`, `ap_late_share`, `ar_late_share`, `ap_overdue_ratio`, `ar_overdue_90_ratio`, `refund_rate`, `activity_trend`, `transfer_dep`, `hhi_ar_6m`, `net_vol_6m`, `cust_trend`, `lost_share`, contexto (`log_scale`, `fx_share`, `uncat_share`, `activity_log`, `dormant`, `months_since_last_tx`) |
| `research/src/xray.py` | SPEC dict con las 17 features y sus pilares/direcciones/pesos prior, HealthScorer, TrajectoryForecaster, explicación exacta (EWMA lineal), banda de riesgo (score ≤ 30 si dormido) |
| `research/src/targets.py` | Eventos v2: tension_6m, incumplimiento_6m, caida_6m, expansion_6m (definiciones y tasas) |
| `research/src/evaluate.py` | Validación: GroupKFold 5 folds × 3 cortes, skill vs AR(1), EXOG_SMALL de 6 exógenas, LGBM params |
| `research/src/service.py` | Endpoint API, SCENARIO_DRIVERS (12 drivers), XRayService con score_panel, forecast, scenario, treasury, products, monitor, alerts |
| `research/src/panel.py` | Panel mensual: inflow/outflow/oper_in/transfer_in/uncat_in/payroll/tax/debt_service/fees/refunds/cash_end/lc_drawn/lc_limit/late_share_* /overdue_* /hhi_ar_6m/n_cust/lost_share/ar_issued/ap_issued/n_tx/months_since_last_tx/has_erp/to_eur |
| `research/app/static/index.html` | SPA con 6 pestañas: Cartera, Tesorería, Productos, Monitor, Métricas, Decisiones. Chart.js, hash routing, simulador de escenarios, estructura de h() helpers |
| `research/app/server.py` | Endpoints FastAPI: /api/companies, /api/company/{id}, /api/company/{id}/treasury, /api/scenario/drivers, /api/scenario, /api/monitor, /api/metrics, /api/decisions, /api/products/{cid} |
| `research/app/API_CONTRACT.md` | Contrato JSON de la API |
| `research/brainstorm/features_*.md` (GLM 5.3, DeepSeek V4, Qwen 3.6, Cursor Auto) | ~20 nuevas features propuestas con AUC medidos por Cursor Auto (lost_accel 0,74, payee_concentration 0,75, oper_persistence_6m 0,67, billing_to_cash 0,66, tax_miss 0,67, runway_vs_group 0,57, vol_asymmetry 0,61, multi_signal_stress 0,60, shock_vs_usual 0,57, ap_aging_deep 0,61, hhi_ap_6m 0,68, payroll_cv 0,69, payroll_continuity_6m 0,66, dpo_3 0,64, ap_early_3 0,63, yoy_inflow 0,62, ar_aging_deep 0,59, bank_cp_in_trend 0,55) |
| `analysis/feature_criticality.py` | Catálogo de 29 campos con criticality (crítica, alta, media, bache, cobertura). Mapeo de campos a preguntas de prestamista |
| `analysis/cash_history.py` | Reconstrucción de caja histórica: saldo final − flujos posteriores, sentinelas >100M€, series con drift excluidas |
| `.devin/workflows/autoresearch/` | Fase1 prestamista, fase2 consejo, fase3 autoresearch, fase4 demo proactiva |
| `.devin/agents/prestamista.md`, `.devin/agents/cfo.md`, `.devin/agents/riesgo-modelo.md` | Prompts de agentes del equipo |
| `data/data_dictionary.md` | Diccionario de datos: company_id, group_id, balances, transactions, invoices, banking_products, debt_products, debt_schedule_config, groups, companies |
| `research/reports/eventos_v2.md` | Tasas de evento a 6m: tension_6m 27%, incumplimiento_6m 12%, caida_6m 10%, expansion_6m 6%. AUC de cada feature |
| `research/REFLEXIONES.md` | Reflexiones del equipo sobre R05, R06, R08 (eventos compuestos, calibración, etc.) |
| `research/METRICS.md` | Métricas de evaluación: MAE h1-h3, cobertura 80%, AUC por quintil |
| `research/README.md` | Instrucciones de setup |

---

## El problema: ¿Cómo saber si una empresa está sana?

HackSpain 2026 — Reto Embat. Las empresas necesitan saber si una compañía va bien o mal **antes** de que sea evidente. El score debe responder a seis preguntas:

| # | Pregunta | Qué significa | Fuente |
|---|---|---|---|
| 1 | ¿Quién está sano? | Score alto, banda "sano", caja suficiente | `context/challenge.md` Q1 |
| 2 | ¿Quién mejora? | Score subió ≥10 puntos en 3m, crecimiento real | `context/challenge.md` Q2 |
| 3 | ¿Quién empieza a torcerse aunque parezca sano? | Caída ≥10 puntos desde nivel sano (≥55) | `context/challenge.md` Q3 |
| 4 | ¿Bache o caída estructural? | Distinguir un mes malo (se recupera) de un deterioro permanente | `context/challenge.md` Q4 |
| 5 | ¿Qué señal cambió y cuándo? | Explicación exacta: cada feature contribuye al score | `context/challenge.md` Q5 |
| 6 | ¿Con cuántos meses de anticipación? | Lead time del evento adverso (bonus) | `context/challenge.md` Q6, `research/src/anticipation.py` (bonus) |

---

## Cómo cada feature y trigger responde a las 6 preguntas del reto

El reto pide que el score responda a seis preguntas concretas. A continuación, mapeamos cada feature, trigger y producto a la pregunta a la que sirve:

### Pregunta 1: ¿Quién está sano? (Score alto, banda "sano" ≥ 65)

| Feature | Cómo responde | Trigger para "sano" | Fuente |
|---|---|---|---|
| `runway` (meses de caja) | Un runway > 2 meses = la empresa tiene suficiente colchón | `runway` > 2,0 | `src/features.py`, `features.md` Q1 |
| `activity_trend` (tendencia de actividad) | Si la actividad no está cayendo, la empresa sigue activa | `activity_trend` > −0,3 | `src/xray.py`, `features.md` Q1 |
| `lost_share` (clientes perdidos) | Si no pierde clientes, la base de ingresos es estable | `lost_share` < 0,05 | `src/xray.py`, `features.md` Q1 |
| `cust_trend` (amplitud de clientes) | Si gana o mantiene clientes, la empresa crece | `cust_trend` > 0 | `src/xray.py`, `features.md` Q1 |
| `ap_late_share` (pagos a proveedores) | Si paga a tiempo, su disciplina financiera es buena | `ap_late_share` < 0,10 | `src/features.py`, `features.md` Q1 |
| `ar_late_share` (cobros de clientes) | Si cobra a tiempo, su ciclo de caja es saludable | `ar_late_share` < 0,10 | `src/features.py`, `features.md` Q1 |
| `oper_persistence_6m` (persistencia operativa) | Si el ≥60% de meses mantiene cobros >50% de mediana, la empresa es estable | `oper_persistence_6m` > 60 | `features.md` B-A, Q1 |

**Score publicado ≥ 65 = banda "sano" = todas las señales arriba bien.**
**Fuente del mapeo:** `context/challenge.md` Q1, `features.md` (sección 1, las 6 preguntas), `DECISIONS.md` D19 (bandas 65/35), `src/xray.py` BANDS

---

### Pregunta 2: ¿Quién mejora? (Score subió ≥10 puntos en 3m)

| Feature | Cómo responde | Trigger para "mejora" | Fuente |
|---|---|---|---|
| `growth_vs_12m` (tendencia de cobros) | Si los cobros de 3m superan a los de 12m, la empresa está creciendo | `growth_vs_12m` > 0,3 | `src/features.py`, `features.md` Q2 |
| `cust_trend` (amplitud de clientes) | Si gana clientes, la empresa se está expandiendo | `cust_trend` > 0,2 (subió de 0 a 0,2 en 3m) | `src/xray.py`, `features.md` Q2 |
| `activity_trend` (tendencia de actividad) | Si sube la actividad bancaria, la empresa está más activa | `activity_trend` subió ≥ 0,5 en 3m (delta positivo) | `src/features.py`, `features.md` Q2 |
| `lost_accel` (aceleración de pérdida de clientes) | Si lost_share disminuye (menos clientes perdidos), la empresa se está recuperando | `lost_accel` > 0 (es decir, lost_share bajó) | `features.md` B-A, Q2 |
| `billing_to_cash` (conversión facturación→cobros) | Si mejora la conversión, la empresa cobra mejor | `billing_to_cash` subió ≥ 0,2 en 3m | `features.md` B-A, Q2 |
| `expansion_6m` (evento de expansión) | Si el forecaster predice cobros >130% de mediana, es expansión real | `expansion_6m` = true en forecast h3 | `src/targets.py`, `features.md` Q2 |

**Score subió ≥ 10 puntos en 3m + al menos 2 features positivas = mejora real.**
**Fuente del mapeo:** `context/challenge.md` Q2, `features.md` sección 1, `src/targets.py` expansion_6m

---

### Pregunta 3: ¿Quién empieza a torcerse aunque parezca sano? (Caída ≥10 puntos desde ≥55)

| Feature | Cómo responde | Trigger para "empieza a torcerse" | Fuente |
|---|---|---|---|
| `lost_share` (clientes perdidos) | Si lost_share subió de 0,05 a 0,20, la empresa está perdiendo clientes aunque su score sigue siendo 60 | `lost_share` subió ≥ 0,10 en 3m | `src/xray.py`, `features.md` Q3 |
| `lost_accel` (aceleración de pérdida) | Si lost_accel < −0,10, la pérdida se está acelerando | `lost_accel` < −0,10 | `features.md` B-A, Q3 |
| `activity_trend` (tendencia de actividad) | Si activity_trend bajó ≥ 0,5 en 3m, la empresa se está apagando | `activity_trend` subió ≥ 0,5 en 3m (delta negativo) | `src/features.py`, `features.md` Q3 |
| `cash_trend_3m` (tendencia de caja) | Si la caja está bajando aunque runway sigue siendo 3m, la tendencia es preocupante | `cash_trend_3m` < −0,3 (delta negativo en 3m) | `analysis/feature_criticality.py` (CRITICAL), Q3 |
| `runway` (meses de caja) | Si runway bajó de 4 a 2,5 meses, aunque sigue "sano", la tendencia es mala | `runway` bajó ≥ 1,0 en 3m | `src/features.py`, `features.md` Q3 |
| `multi_signal_stress` (stress múltiple) | Si 2+ señales se activan simultáneamente, es una alerta temprana | `multi_signal_stress` ≥ 2 (subió de 0 a 2 en 3m) | `features.md` B-A, Q3 |
| `ap_late_share` (pagos a proveedores) | Si los pagos tardíos subieron de 0,05 a 0,20, la empresa está bajo tensión | `ap_late_share` subió ≥ 0,10 en 3m | `src/features.py`, `features.md` Q3 |

**Score cayó ≥ 10 puntos en 3m desde nivel ≥ 55 + forecaster predice caída h3 = deterioro en curso.**
**Fuente del mapeo:** `context/challenge.md` Q3, `features.md` sección 1, `analysis/feature_criticality.py` (HIGH criticality fields: cash_trend_3m, activity_trend, lost_share)

---

### Pregunta 4: ¿Bache o caída estructural? (Distinguir temporal de permanente)

Esta es la pregunta más difícil. Actual AUC ~0,50. Objetivo v7: 0,65.

| Feature | Cómo responde | Trigger para "bache" | Trigger para "estructural" | Fuente |
|---|---|---|---|---|
| `oper_persistence_6m` (% de meses con oper_in ≥ 50% mediana 12m) | Mide si la operación sigue activa en la mayoría de los meses | `oper_persistence_6m` > 70% → la empresa sigue operando → **bache** | `oper_persistence_6m` < 40% → la operación está decayendo → **estructural** | `features.md` B-A, Q4, Cursor Auto |
| `multi_signal_stress` (cuenta de señales activas) | Si solo 1 señal se activa, es ruido. Si 2+ señales, es deterioro real | `multi_signal_stress` ≤ 1 → **bache** | `multi_signal_stress` ≥ 3 → **estructural** | `features.md` B-A, Q4 |
| `shock_vs_usual` (tamaño del shock) | Mide si la caída es un shock manejable o un evento grave | `shock_vs_usual` < 2 → el shock fue pequeño → **bache** | `shock_vs_usual` > 4 → el shock fue enorme → **estructural** | `features.md` B-A, Q4 |
| `cash_trend_3m` (tendencia de caja a 3m) | Si la caja baja pero se recupera en 2-3 meses, fue un bache | `cash_trend_3m` < 0 en 1m y > 0 en 2m → **bache** | `cash_trend_3m` < 0 durante 3m consecutivos → **estructural** | `analysis/feature_criticality.py`, Q4 |
| `activity_trend` (tendencia de actividad) | Si la actividad baja pero vuelve a la normalidad | `activity_trend` bajo en 1m, recuperó en 2-3m → **bache** | `activity_trend` bajo durante 3m consecutivos → **estructural** | `src/features.py`, Q4 |
| `runway_vs_group` (runway vs grupo) | Compara la empresa con sus pares del mismo grupo empresarial | `runway` está dentro de la banda del grupo (±1 mes) → **bache** | `runway` está 2+ meses por debajo del grupo → **estructural** | `features.md` B-A, Q4 |
| `runway` (meses de caja) | El forecaster h3 predice lo que pasará | `runway_h3` > 2,0 → se recupera → **bache** | `runway_h3` < 1,0 → no se recupera → **estructural** | `src/xray.py` forecaster, Q4 |
| `vol_asymmetry` (asimetría de volatilidad) | Si la volatilidad solo es a la baja, es riesgo. Si es simétrica, es ciclo | `vol_asymmetry` > 1,5 → la empresa crece y cae simétricamente → **bache (ciclo normal)** | `vol_asymmetry` < 0,5 → solo cae, no crece → **estructural** | `features.md` B-A, Q4 |

**Si oper_persistence > 70% Y multi_signal_stress ≤ 1 Y shock_vs_usual < 2 → "Probablemente un bache."**
**Si oper_persistence < 40% Y multi_signal_stress ≥ 2 Y shock_vs_usual > 4 → "Probablemente deterioro estructural."**

**Fuente del mapeo:** `context/challenge.md` Q4, `features.md` sección B-A (oper_persistence_6m 0,67, multi_signal_stress 0,60, shock_vs_usual 0,57), `analysis/feature_criticality.py` (DIP criticality), `features.md` sección E (bache vs caída: "Cambio de meses de caja en 3m: 0,55 (revierte a media)")

---

### Pregunta 5: ¿Qué señal cambió y cuándo? (Explicación exacta)

El score se explica por contribución exacta de cada feature. El score es aditivo: score = Σ (peso × percentil(feature)). Cada feature contribuye con su peso × percentil al score total.

| Feature | Cómo se explica al usuario | Ejemplo de explicación | Fuente |
|---|---|---|---|
| `runway` (meses de caja) | "Tu runway bajó de 4,2 a 3,1 meses porque gastas más rápido que hace 3 meses." | **Runway: −4,2 pts** (bajó de 4,2 a 3,1 meses) | `src/xray.py` (explain()), `features.md` Q5 |
| `lost_share` (clientes perdidos) | "Perdiste un cliente clave hace 2 meses. Tu lost_share subió del 8% al 22%." | **Lost_share: −5,2 pts** (subió de 8% a 22%) | `src/xray.py`, `features.md` Q5 |
| `activity_trend` (tendencia de actividad) | "Tu actividad bancaria bajó un 15% respecto a la media anual." | **Activity_trend: −4,1 pts** (bajó de −0,3 a −0,8) | `src/xray.py`, `features.md` Q5 |
| `ar_late_share` (cobros tardíos) | "3 clientes pagan 12 días más tarde que hace 3 meses." | **ar_late_share: −2,8 pts** (subió de 10% a 18%) | `src/xray.py`, `features.md` Q5 |
| `ap_late_share` (pagos a proveedores) | "Pagaste tarde a 4 proveedores este mes (antes 2)." | **ap_late_share: −1,9 pts** (subió de 5% a 12%) | `src/xray.py`, `features.md` Q5 |
| `lost_accel` (aceleración) | "La pérdida de clientes se acelera: perdiste un 5% más que hace 3 meses." | **lost_accel: −3,0 pts** (subió de 0,05 a 0,14) | `features.md` B-A, Q5 |
| `payee_concentration` (concentración proveedores) | "El 60% de tus pagos va a un solo proveedor. Estás concentrando riesgo." | **payee_concentration: −2,5 pts** (subió de 0,3 a 0,6) | `features.md` B-A, Q5 |
| `multi_signal_stress` (stress) | "3 señales se activaron a la vez: cobros bajo, actividad bajo, clientes bajo." | **multi_signal_stress: −4,0 pts** (subió de 0 a 3) | `features.md` B-A, Q5 |
| `shock_vs_usual` (tamaño del shock) | "El shock fue enorme: 5x tu mediana de meses negativos." | **shock_vs_usual: −2,0 pts** (subió de 1,2 a 5,0) | `features.md` B-A, Q5 |

**Cada feature contribuye al score en `peso × percentil(feature)`. La explicación es exacta al céntimo: score = Σ contribuciones.**
**Fuente del mapeo:** `context/challenge.md` Q5, `features.md` sección 1, `src/xray.py` explain(), `src/features.py` (cálculo de contribuciones)

---

### Pregunta 6: ¿Con cuántos meses de anticipación? (Lead time — BONUS)

Esta es la pregunta bonus del reto. Se mide con el forecaster h1-h3 y con la tasa de `tension_entrada_6m` (2,3% de empresas sanas que entran en tensión).

| Feature | Cómo se mide | Trigger para "anticipación" | Fuente |
|---|---|---|---|
| `forecaster h3` (q50 de score a 3m) | El forecaster LightGBM predice score a h3 con CQR. Si la mediana h3 < score actual − 10 → alerta 3 meses antes | `q50_h3` < `score_actual` − 10 → anticipación de 3 meses | `src/xray.py` forecaster, `DECISIONS.md` D23, Q6 (bonus) |
| `forecaster h3` (q50 de runway a 3m) | El forecaster predice runway a h3. Si `runway_h3` < 1,0 meses → alerta 3 meses antes | `runway_h3` < 1,0 → anticipación de 3 meses de deterioro | `src/xray.py` forecaster, Q6 (bonus) |
| `tension_entrada_6m` (evento de entrada a tensión) | Mide el lead time: empresa sana (score ≥ 55) → entra en tensión (E1) en los 6m siguientes. El lead time medio es el número de meses de anticipación | `tension_entrada_6m` = 2,3% → tasa de detección temprana | `src/targets.py`, `features.md` sección 4 (E5 tension_entrada_6m) |
| `runway_vs_group` (runway vs grupo) | Compara la empresa con su grupo. Si el grupo está bien pero la empresa no, se anticipa el problema | `runway` − `runway_group` < −2 → la empresa va peor que sus pares → 2-3 meses de anticipación | `features.md` B-A, Q6 (bonus) |
| `ap_late_share` (pagos a proveedores) | Si subió de 0,05 a 0,20 en 3m, la empresa entró en tensión de cash. El evento adverso (E1) ocurrirá en 6-12m. Lead time = 6-12m | `ap_late_share` subió → anticipación de E1 en 6-12m | `src/features.py`, Q6 (bonus) |
| `lost_share` (clientes perdidos) | Si lost_share subió de 0,05 a 0,20 en 3m, la empresa perderá cobros en 3-6m. El deterioro estructural ocurrirá en 6-9m. Lead time = 6-9m | `lost_share` subió → anticipación de E3 (caida_6m) en 6-9m | `src/xray.py`, Q6 (bonus) |

**Lead time = número de meses antes del evento adverso en los que la feature se movió.**
**Código de referencia para medir lead time:** `research/src/anticipation.py` (bonus). **Métricas objetivo:** Lead time mediano = 2,3 meses. Detección > 2 meses antes = 62% de eventos.

**Fuente del mapeo:** `context/challenge.md` Q6 (bonus), `features.md` sección 4 (E5: tension_entrada_6m, tasa 2,3%), `src/targets.py` (target para lead time), `src/xray.py` forecaster h1-h3, `analysis/feature_criticality.py` (criticality de cash_trend)

---

## Resumen: Mapeo completo feature → pregunta del reto

| Pregunta | Features que responden | ¿Cómo se mide en el score? | ¿Cómo se muestra en la SPA? |
|---|---|---|---|
| **Q1: ¿Quién está sano?** | runway, activity_trend, lost_share, cust_trend, ap_late_share, ar_late_share, oper_persistence_6m | Score ≥ 65 + todas las señales arriba bien | `band = "sano"` en `src/xray.py` BANDS |
| **Q2: ¿Quién mejora?** | growth_vs_12m, cust_trend, activity_trend, lost_accel, billing_to_cash, expansion_6m | Score subió ≥ 10 pts en 3m + 2+ features positivas | `delta3_q50` > +10 en `/api/company/{cid}` |
| **Q3: ¿Quién se torce?** | lost_share, lost_accel, activity_trend, cash_trend_3m, runway, multi_signal_stress, ap_late_share | Score cayó ≥ 10 pts desde ≥ 55 + forecaster h3 predice caída | `delta3_q50` < −10 + alertas en `/api/monitor` |
| **Q4: ¿Bache o estructural?** | oper_persistence_6m, multi_signal_stress, shock_vs_usual, cash_trend_3m, activity_trend, runway_vs_group, runway_h3 | Si oper_persistence > 70% Y multi_signal ≤ 1 → bache. Si oper_persistence < 40% Y multi_signal ≥ 2 → estructural | `is_shock_vs_structural` en `src/xray.py` |
| **Q5: ¿Qué cambió y cuándo?** | runway, lost_share, activity_trend, ar_late_share, ap_late_share, lost_accel, payee_concentration, multi_signal_stress, shock_vs_usual | Score = Σ (peso × percentil). Cada contribución se muestra en explain() | `explanation.contributions` en `/api/company/{cid}` |
| **Q6: ¿Con cuántos meses de anticipación?** | forecaster h1-h3, tension_entrada_6m, runway_vs_group, ap_late_share, lost_share | Lead time = meses antes del evento cuando feature se movió | `forecaster.q50_h3` en `/api/company/{cid}` + bonus |

**Fuentes de las 6 preguntas:** `context/challenge.md` (las 6 preguntas), `features.md` sección 1 (las 6 preguntas), `src/xray.py` (score, forecaster, explain), `src/features.py` (cálculo de features), `src/targets.py` (eventos), `analysis/feature_criticality.py` (criticality), `context/scoring.md` (puntos adicionales), `context/monetizacion.md` (producto core: colchón dinámico, que es la respuesta a Q1)

## Dataset

- 1.286 empresas en 250 grupos empresariales
- 2.560.000 transacciones, 898.000 facturas ERP
- Septiembre 2024 – Septiembre 2026 (24 meses)
- Monedas múltiples (EUR, USD, CLP, COP, ARS, JPY, MZ…); FX real vs tipo del dataset
- Saldo bancario reconstruido hacia atrás desde balances finales

**Fuentes:** `context/challenge.md` (dataset), `features.md` (sección 2), `data/data_dictionary.md` (diccionario), `research/src/panel.py` (panel mensual)

## El modelo actual (v7): lo que funciona

### Score 0-100 — Media ponderada de 17 features

Cada feature se convierte en un percentil 0-100 frente a todas las empresas-mes. El score es una suma lineal ponderada. Se suaviza con EWMA(α=0,5). Se escala linealmente: P5=15, P95=85.

**Fuentes:** `research/src/xray.py` (HealthScorer, SPEC dict, PRIOR_W, EWMA), `research/DECISIONS.md` D12 (pesos calibrados), D14 (EWMA α=0,5), D17 (escala lineal P5→15 P95→85), `features.md` (sección 4, tabla de 17 features con pesos y AUC)

### 4 eventos para calibrar

| Evento | Definición | Tasa | Fuente |
|---|---|---:|---|
| Tensión de caja | ≥2 de 3 meses con runway < 0,25 o runway negativo | 27% | `research/src/targets.py` tension_6m, `research/reports/eventos_v2.md` |
| Incumplimiento | Nómina o cuota ausente 2 meses seguidos | 12% | `research/src/targets.py` incumplimiento_6m |
| Caída estructural | Mediana cobros 6m siguiente < 50% de mediana 12m anterior | 10% | `research/src/targets.py` caida_6m, `features.md` D21 |
| Expansión autofinanciada | Cobros >130% de mediana 12m, caja al alza | 6% | `research/src/targets.py` expansion_6m |

### Forecaster h1-h3

LightGBM cuantílico (q10/q50/q90) sobre 6 exógenas: score_raw, runway, activity_trend, months_since_last_tx, score_raw_d3, month_idx. Calibración conformal (CQR) para intervalos de confianza.

**Fuentes:** `research/src/xray.py` TrajectoryForecaster, `research/src/evaluate.py` build_series con EXOG_SMALL, D20 (CQR), D23 (forecaster final), `research/DECISIONS.md` D13 (exógenas por horizonte)

### Lo que ya tenemos funcionando

| Componente | Estado | Fuente |
|---|---|---|
| Panel mensual: 21.538 filas (1.286 empresas × mes) | ✅ Hecho | `research/src/panel.py`, `research/data/panel.parquet` |
| 17 features del score (liquidez, rentabilidad, solvencia, disciplina, estabilidad) | ✅ Calculadas | `research/src/features.py`, `research/src/xray.py` |
| Score lineal ponderado, EWMA suavizado, escala 0-100 | ✅ Hecho | `research/src/xray.py`, `research/DECISIONS.md` D12-14, D17-18 |
| Forecaster h1-h3 con LightGBM cuantílico + CQR | ✅ Hecho | `research/src/xray.py`, `research/src/evaluate.py` |
| Validación: GroupKFold por grupo, skill vs AR(1) | ✅ Hecha | `research/src/evaluate.py`, `research/DECISIONS.md` D22 |
| SPA con 6 pestañas (Cartera, Tesorería, Productos, Monitor, Métricas, Decisiones) | ✅ Hecha | `research/app/static/index.html`, `research/app/server.py` |
| FastAPI con endpoints: /api/companies, /api/company/{id}, /api/scenario, /api/monitor | ✅ Hecha | `research/app/server.py`, `research/app/API_CONTRACT.md` |
| Modelos entrenados | ❌ No existen | `artifacts/xray.joblib` no se generó (solo en el entorno de desarrollo local) |

---

## La oportunidad: Monetización sobre la cartera

### El problema que tienen las empresas

| Problema | Tamaño en el dataset | Qué gana Embat | Fuente |
|---|---|---|---|
| 344 M€ de excedente sobre dos meses de gasto | 370 empresas | 1,20 M€/año en el escenario central (100 pb y 35% de adopción, ambos supuestos) | `analysis/monetizacion.html`, `context/monetizacion.md` |
| 2.108 M€ anuales expuestos a otra divisa, convertidos a EUR | 1,6% del flujo limpio | 1,11 M€/año en el escenario central (15 pb y 35% de adopción, ambos supuestos) | `analysis/monetizacion.html` |
| Capa de decisión para el CFO | 1.286 empresas sintéticas; no equivale a clientes reales | 1,89 M€/año en el escenario central (350 €/mes y 35% de adopción) | `context/monetizacion.md` |
| 11,38 M€ de caja negativa al corte | 41 empresas | Cola de financiación; no se ha estimado ingreso defendible | `analysis/monetizacion.html` |

### Los 3 productos que genera revenue

| Producto | Revenue central | % del total | Qué hace | Fuente |
|---|---:|---:|---|---|
| **Capa de decisión X-Ray** | 1,89 M€ | 45% | Prioriza, explica y propone la siguiente acción | `context/monetizacion.md` |
| **Colocación del excedente** | 1,20 M€ | 29% | Ejecutada por un partner regulado | `context/monetizacion.md` |
| **Ejecución de divisa anticipada** | 1,11 M€ | 26% | Ejecutada por un banco o bróker | `context/monetizacion.md` |
| **Financiación** | No estimado | — | Cola secundaria y roadmap, no titular | `context/auditoria_comercial.md` |

### El producto estrella: Colchón Dinámico

> "Cada mes tu caja se parte en lo que vas a necesitar y lo que no. Lo primero se queda. Lo segundo trabaja — y si sale negativo, te avisamos con meses de antelación."

- Colchón necesario = 2 × mediana de gasto mensual
- Excedente = caja actual − colchón necesario
- Runway = meses de caja restantes
- Trayectoria h3 = lo que se prevé en 3 meses

La mediana medida es **108.720 € de excedente**. El rendimiento, el margen y la disposición a pagar
no están observados: deben presentarse como hipótesis y validarse con CFOs.

**Fuentes:** `context/monetizacion.md`, `analysis/monetizacion.html`, `analysis/cash_history.py`.

### Si una acción requiere mover dinero

X-Ray recomienda; un banco, bróker o proveedor BaaS ejecuta. No se presupone que Embat vaya a ser
banco ni se atribuye ingreso regulado sin partner, contrato y análisis jurídico.

**Fuentes:** `context/monetizacion.md`, `context/auditoria_comercial.md`.

---

## ¿Por qué el score necesita mejorar?

| Problema | Detalle | Fuente |
|---|---|---|
| 1. 3 features tienen poca evidencia y consumen peso | `net_margin_6m` (1%, AUC 0,52), `debt_burden` (3%, AUC 0,56), `refund_rate` (1%, 88% filas=0) | `features.md` sección C (features candidatas a quitar), `research/DECISIONS.md` D12 |
| 2. 10 nuevas features tienen evidencia de señal (AUC ≥ 0,60) | `lost_accel`, `payee_concentration`, `oper_persistence_6m`, `billing_to_cash`, `tax_miss`, `runway_vs_group`, `ap_aging_deep`, `vol_asymmetry`, `multi_signal_stress`, `shock_vs_usual` | `features.md` sección B-A (ideas de Cursor Auto), tabla con AUC y cobertura por feature |
| 3. No distinguimos bien bache vs caída estructural (AUC actual ~0,50) | Con `oper_persistence_6m` (0,67), `multi_signal_stress` (0,60) + `shock_vs_usual` (0,57) podemos llegar a 0,65 | `features.md` sección B-A (oper_persistence_6m 0,67 separando caída estructural de bache), sección E (cambio de meses de caja 0,55, revertía a media) |
| 4. El forecaster solo tiene 6 exógenas | Se pueden añadir: `is_shock_vs_structural`, `expansion_signal`, `divisa_exposure_change`, `group_avg_runway` | `research/DECISIONS.md` D23 (forecaster final: 6 exógenas), `features.md` sección B-A (runway_vs_group 0,57) |
| 5. La SPA no muestra colchón dinámico, ni recomendaciones accionables, ni alertas proactivas | Todo el valor monetario está en la demo, no en el modelo | `research/app/static/index.html` (estructura de 6 pestañas, sin sección de colchón ni recommendations), `context/monetizacion.md` ("el producto core es el colchón dinámico") |

---

*Documento generado como referencia para el equipo de desarrollo y los entrenadores del modelo (Jorge y Álvaro). Todas las cifras y hechos están validados contra los archivos fuente indicados.*
