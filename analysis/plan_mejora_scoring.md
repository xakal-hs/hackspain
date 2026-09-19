# Plan de Mejora del Scoring — X-Ray Score v7

---

## Cómo cada feature y trigger responde a las 6 preguntas del reto

El reto pide que el score responga a seis preguntas concretas. A continuación, mapeamos cada feature, trigger y producto a la pregunta a la que sirve:

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

---

## Fuentes de la información

Todas las features, pesos, AUC, coberturas y definiciones de este plan provienen de los archivos fuente listados en `downloads/planteamiento_problema.md` más:

| Fuente específica | Contenido del archivo |
|---|---|
| `research/brainstorm/SINTESIS.md` | Síntesis de propuestas de GLM 5.3, DeepSeek V4, Qwen 3.6, Cursor Auto |
| `research/brainstorm/eventos/SINTESIS_glm5.3.md` | Propuestas de GLM sobre nómina, obligaciones, plazos, clientes, bache vs caída, financiamiento forzado, banco y texto, grupo |
| `research/brainstorm/features_glm5.3.md` | Brainstorming de GLM: AUC medidos por Cursor Auto |
| `research/brainstorm/features_deepseek-v4-flash.md` | Brainstorming de DeepSeek: AUC medidos por Cursor Auto |
| `research/brainstorm/features_qwen3.6.md` | Brainstorming de Qwen: AUC medidos por Cursor Auto |
| `research/brainstorm/features_cursor-auto.md` | Brainstorming de Cursor Auto: AUC medidos por Cursor Auto |
| `research/brainstorm/eventos/jurado-dataset__*.md` | Discusiones con el jurado sobre dataset y features |
| `research/brainstorm/eventos/producto__*.md` | Discusiones de producto con diferentes agentes |
| `research/brainstorm/eventos/riesgo-credito__*.md` | Discusiones sobre riesgo de crédito |
| `research/brainstorm/eventos/auditor-datos__*.md` | Discusiones sobre calidad de datos y features |
| `research/brainstorm/eventos/metodologia__*.md` | Discusiones sobre metodología de calibración |
| `research/reports/review_*.md` | Reviews de iteraciones v1-v6 (decisiones de feature selection y peso) |
| `research/reports/decisions.json` | Datos de las decisiones D01-D27 consumidos por la SPA |
| `research/reports/metrics_*.json` | Métricas de iteraciones consumidas por la SPA |

---

## 1. ESTADO ACTUAL (v6)

### Qué tenemos funcionando

| Componente | Estado | Archivo | Fuente del diseño |
|---|---|---|---|
| Panel mensual: 21.538 filas (1.286 empresas × mes) | ✅ Hecho | `src/panel.py` → `data/panel.parquet` | `features.md` sección 4, `src/panel.py` |
| 17 features del score (liquidez, rentabilidad, solvencia, disciplina, estabilidad) | ✅ Calculadas | `src/features.py` | `src/features.py`, `src/xray.py` SPEC dict |
| Score lineal ponderado (0-100) | ✅ Hecho | `src/xray.py` → HealthScorer | `src/xray.py`, `DECISIONS.md` D12, D14, D17, D18 |
| EWMA suavizado (α=0,5) | ✅ Hecho | `src/xray.py` | `DECISIONS.md` D14 (suavizado EWMA α=0,5) |
| Forecaster h1-h3 (LightGBM cuantílico) | ✅ Hecho | `src/xray.py` → TrajectoryForecaster | `DECISIONS.md` D20 (CQR), D23 (forecaster final) |
| 4 eventos para calibrar | ✅ Definidos | `src/targets.py` | `src/targets.py`, `reports/eventos_v2.md` |
| Validación GroupKFold | ✅ Hecha | `src/evaluate.py` | `DECISIONS.md` D22 (validación), `src/evaluate.py` |
| SPA con 6 pestañas | ✅ Hecha | `static/index.html` | `src/server.py`, `static/index.html` |
| FastAPI con endpoints | ✅ Hecha | `src/server.py` | `src/server.py`, `src/API_CONTRACT.md` |
| Modelos entrenados | ❌ No existen | `artifacts/xray.joblib` no se generó | `src/service.py` (run v2 con `python service.py`) |

### Lo que falta para que funcione la demo

1. **Ejecutar el pipeline de entrenamiento**: `python src/service.py` → `artifacts/xray.joblib`
2. **Levantar la API**: `python src/server.py` → `http://127.0.0.1:8099/`
3. **Añadir colchón dinámico** a la SPA (sección nueva en viewEmpresa)
4. **Añadir recomendaciones accionables** por empresa (tabla de alertas con acciones)

---

## 2. MEJORA DEL SCORING: FEATURES NUEVAS

### 2A. Features a QUITAR (poca evidencia, consumen peso)

| Feature | Peso actual | AUC (mejor evento) | Cobertura | Por qué quitar | Fuente del descarte |
|---|---:|---:|---:|---|---|
| `net_margin_6m` | 1% | 0,52 (cualquiera) | 100% | Revierte a media. No discrimina ningún evento. | `features.md` sección C: "sin orden por tramos"; D08 (ventana 3m revertía a media, cambiada a 6m pero siguió sin aportar) |
| `debt_burden` | 3% | 0,56 (incumplimiento_6m) | 100% | Solo discrimina incumplimiento (12%), no es general. | `features.md` sección C: "sin orden"; peso viene de evento "crecimiento" probablemente espurio |
| `refund_rate` | 1% | 0,51 (cualquiera) | 100% | 88% de filas = 0. No discrimina. | `features.md` sección C: "sin orden por tramos; el 88% de las filas valen 0" |

**Peso total a liberar: 5%**

**Fuentes del descarte:** `features.md` sección C ("Candidatas a quitar"), `research/DECISIONS.md` D12 (pesos calibrados), D22 (skill vs AR1)

### 2B. Features a AÑADIR (nuevas, con evidencia AUC ≥ 0,60)

| # | Feature | Definición exacta | Ventana | Dirección | Cobertura | AUC (mejor evento) | Peso estimado | Fuente del AUC |
|---|---|---|---|---|---:|---|---:|---|
| 18 | `lost_accel` | `lost_share_m − lost_share_{m-3m}` | 3m (delta) | ↓ baja = mejor | 24% | 0,74 vs apagado | 5% | `features.md` sección B-A, Cursor Auto |
| 19 | `payee_concentration` | HHI de pagos bancarios (amount < 0) por counterparty_id, media 3m | 3m | ↓ baja = mejor | 40% | 0,75 vs apagado | 4% | `features.md` sección B-A, Cursor Auto |
| 20 | `oper_persistence_6m` | % de los últimos 6 meses donde `oper_in >= 50% × mediana(oper_in, 12m)` | 6m / 12m | ↑ sube = mejor | 76% | 0,67 vs caida_6m (estructural) | 5% | `features.md` sección B-A, Cursor Auto. Clave para bache vs estructural |
| 21 | `billing_to_cash` | `ar_issued(3m) / oper_in(3m)`, low values = stopping invoicing | 3m | ↑ sube = mejor | 55% | 0,66 vs apagado | 4% | `features.md` sección B-A, Cursor Auto |
| 22 | `tax_miss` | En meses fiscales (Ene/Abr/Jul/Oct): `max(0, tax_esperado − tax_real) / tax_esperado`, donde `tax_esperado = tax_annual / 4` | Trimestral | ↓ baja = mejor | 20% | 0,67 vs apagado | 3% | `features.md` sección B-A, Cursor Auto. Propuesta original: GLM |
| 23 | `runway_vs_group` | `runway_m − mediana(runway por group_id, m)` | Mensual | ↑ sube = mejor | 99% | 0,57 vs estructural | 3% | `features.md` sección B-A, Cursor Auto |
| 24 | `ap_aging_deep` | `overdue_90_ap / overdue_ap` donde overdue_ap acumula últimos 12m | 12m | ↓ baja = mejor | 51% | 0,61 vs apagado | 3% | `features.md` sección B-A, Cursor Auto |
| 25 | `vol_asymmetry` | Volatilidad al alza / volatilidad a la baja del flujo neto (6m) | 6m | ↑ sube = mejor | 87% | 0,61 vs growth | 3% | `features.md` sección B-A, Cursor Auto. Propuesta original: GLM |
| 26 | `multi_signal_stress` | Cuenta (0-4): 1 punto si `inflow < −20% de su mediana`, 1 punto si `activity < −20%`, 1 punto si `n_cust < −20%`, 1 punto si `cash_drop > 1 mes burn en 3m` | 3m | ↓ baja = mejor | 81% | 0,60 vs caida | 5% | `features.md` sección B-A, Cursor Auto |
| 27 | `shock_vs_usual` | Si net_flow < 0: `|net_flow| / mediana(abs(net_neg), 6m)` | 6m | ↓ baja = mejor | 45% | 0,57 vs caida | 3% | `features.md` sección B-A, Cursor Auto |

**Peso total a asignar: ~38%** (redistribuir entre las nuevas y las que quedan)

**Fuentes de los AUC:** `features.md` sección B-A ("A. Medidas por Cursor Auto con señal"), `research/brainstorm/features_*.md` (GLM 5.3, DeepSeek V4, Qwen 3.6, Cursor Auto), `features.md` sección E ("Medidas por Cursor Auto contra los eventos a 6 meses")

### 2C. Pesos estimados v7 (redistribuidos)

| Pillar | Peso v6 | Peso v7 estimado | Cambio | Fuente v6 |
|---|---:|---:|---:|---|
| Liquidez | 27% | 25% | −2 (sale debt_burden 3% − se redistribuye entre runway y lc_util) | `features.md` sección 4, tabla de 17 features |
| Rentabilidad | 6% | 1% | −5 (sale net_margin_6m 1% + debt_burden 3% + payroll_burden 1% → sale deuda, se redistribuye) | `features.md` sección 4, tabla de 17 features |
| Solvencia | 4% | 1% | −3 (sale debt_burden, payroll queda con peso bajo) | `features.md` sección 4, tabla de 17 features |
| Disciplina | 26% | 29% | +3 (+lost_accel 5% redistribuido, +ap_aging_deep 3%, +billing_to_cash 4%) | `features.md` sección 4, tabla de 17 features |
| Estabilidad | 37% | 42% | +5 (+multi_signal 5%, +oper_persistence 5%, +payee_conc 4%, −net_margin) | `features.md` sección 4, tabla de 17 features |
| **TOTAL** | **100%** | **100%** | | |

**Nota:** Los pesos exactos se calibrarán automáticamente con `HealthScorer(calibrate=True)` que ajusta pesos con logística P(evento) = σ(b − Σ w·s) con w ≥ 0 (signo restringido). **Fuentes:** `research/DECISIONS.md` D12 (pesos calibrados por evento con signo restringido), `src/xray.py` (HealthScorer.fit con scipy.optimize)

---

## 3. CÓMO ENTRENAR EL MODELO (paso a paso)

### Paso 0: Verificar que existen los datos

```bash
# Verificar que están los CSV del dataset (data_dictionary.md: diccionario de datos)
ls data/transactions.csv
ls data/invoices.csv
ls data/panel.parquet

# Si faltan (son pointers de LFS):
git lfs pull

# Si no existe panel.parquet, hay que generarlo:
python src/panel.py  # fuente: src/panel.py
```

**Fuentes de los datos:** `data/data_dictionary.md` (diccionario: transactions.csv 2,56 M filas, invoices.csv 898 k filas, balances.csv 7.996 filas foto final), `features.md` sección 2 (dataset: panel.parquet 21.538 filas)

### Paso 1: Instalar dependencias

```bash
pip install polars pandas numpy lightgbm scikit-learn mlforecast scipy plotly joblib
```

**Fuentes:** `requirements.txt` (project dependencies), `research/README.md` (setup: uv run python con polars, pandas, numpy, scikit-learn, lightgbm)

### Paso 2: Añadir las 10 nuevas features a `src/features.py`

```python
# En add_features(), después de las features existentes:

# 18. lost_accel (aceleración de pérdida de clientes)
# Definición: lost_share_m − lost_share_{m-3m}
# Fuente: features.md sección B-A, Cursor Auto
lost_accel = pl.col("lost_share") - pl.col("lost_share").shift(3).over("company_id")

# 19. payee_concentration (HHI de pagos por counterparty_id)
# Definición: HHI de amount < 0 por counterparty_id, 3m
# Fuente: features.md sección B-A, Cursor Auto
# payee_concentration = HHI(contrapartes de pagos bancarios, 3m)

# 20. oper_persistence_6m (% de meses con oper_in >= 50% mediana 12m)
# Definición: % de últimos 6m con oper_in >= 50% * mediana(oper_in, 12m)
# Fuente: features.md sección B-A, Cursor Auto. Clave para bache vs estructural.
oper_median12 = pl.col("oper_in").rolling_median(12, min_samples=1).over("company_id")
oper_persist = (pl.col("oper_in") >= 0.5 * oper_median12).cast(pl.Int32)
oper_persistence_6m = oper_persist.rolling_mean(6, min_samples=3).over("company_id") * 100

# 21. billing_to_cash
# Definición: ar_issued(3m) / oper_in(3m)
# Fuente: features.md sección B-A, Cursor Auto
billing_to_cash = pl.col("ar_issued").rolling_mean(3, min_samples=1) / (pl.col("oper_in").rolling_mean(3, min_samples=1) + EPS)

# 22. tax_miss (solo meses fiscales: Ene/Abr/Jul/Oct)
# Definición: max(0, tax_esperado − tax_real) / tax_esperado, donde tax_esperado = tax_12m / 4
# Fuente: features.md sección B-A, Cursor Auto. Propuesta original: GLM 5.3
# (ver section B-C de features.md: "Obligaciones: cobertura de la próxima cuota de préstamo con debt_schedule_config")

# 23. runway_vs_group
# Definición: runway_m − mediana(runway por group_id, m)
# Fuente: features.md sección B-A, Cursor Auto

# 24. ap_aging_deep
# Definición: overdue_90_ap / overdue_ap (vencimiento >90d / vencido total en proveedores)
# Fuente: features.md sección B-A, Cursor Auto

# 25. vol_asymmetry
# Definición: vol_upside (semidesv positiva) / vol_downside (semidesv negativa) en 6m
# Fuente: features.md sección B-A, Cursor Auto. Propuesta original: GLM
# (ver section B-C: "Asimetría de ajuste: ¿recortan pagos cuando caen los cobros?")

# 26. multi_signal_stress
# Definición: Cuenta (0-4): inflow < −20% median, activity < −20% median, n_cust < −20%, cash_drop > 1 burn en 3m
# Fuente: features.md sección B-A, Cursor Auto

# 27. shock_vs_usual
# Definición: Si net_flow < 0: abs(net_flow) / mediana(abs(net_neg), 6m)
# Fuente: features.md sección B-A, Cursor Auto

# Nota: EPS relativo (0,1% del volumen mensual) = invariancia de escala real (D16)
# Fuente: DECISIONS.md D16 (robustez: EPS relativo a escala de la empresa)
```

**Fuentes de las definiciones:** `features.md` sección B-A ("A. Medidas por Cursor Auto con señal"), `features.md` sección B-C ("B. Ideas de GLM, DeepSeek y Qwen, sin medir"), `src/features.py` (patrón de cálculo: `_roll`, `_safe_log_ratio`, EPS relativo)

### Paso 3: Actualizar SPEC dict en `src/xray.py`

```python
# Quitar: net_margin_6m (1% weight, AUC 0,52), debt_burden (3% weight, AUC 0,56), refund_rate (1% weight, 88% filas=0)
# Añadir: lost_accel, payee_concentration, oper_persistence_6m, billing_to_cash, tax_miss, runway_vs_group, ap_aging_deep, vol_asymmetry, multi_signal_stress, shock_vs_usual

# Actualizar PRIOR_W con pesos iniciales para las nuevas features (se redistribuirán automáticamente con calibrate=True)
# Fuente de los pesos iniciales: features.md sección B-A (peso estimado por feature)
```

**Fuentes del SPEC dict:** `src/xray.py` (SPEC dict con 17 features, PILLARS, PRIOR_W, CONTEXT), `features.md` sección 4 (tabla de 17 features con pesos y cobertura)

### Paso 4: Calibrar pesos (logística con signo restringido)

```python
from src.xray import HealthScorer
scorer = HealthScorer(calibrate=True, l2=1.0)
scorer.fit(panel_targeted)
print(scorer.weights_)  # Ver pesos calibrados
```

**Fuentes de la calibración:** `DECISIONS.md` D12 ("Pesos calibrados por evento con signo económico restringido": "Para cada evento se ajusta una logística P(evento) = σ(b − Σ w·s) con w ≥ 0, sobre filas cuyo evento ya era observable en el corte (mes ≤ corte − 6). Los pesos normalizados se promedian para que cada tipo de deterioro cuente igual. Si los datos contradicen la dirección económica de una feature, su peso queda en 0.")

### Paso 5: Calcular score

```python
scored = scorer.score_panel(panel_targeted)
# scored tiene: score, score_raw, band, coverage, contributions, pillars
```

**Fuentes del score_panel:** `src/xray.py` HealthScorer.score_panel(), `features.md` sección 4 (percentiles de 0-100)

### Paso 6: Entrenar forecaster h1-h3

```python
from src.xray import TrajectoryForecaster
from src.evaluate import build_series

series = build_series(scored, panel_targeted)
forecaster = TrajectoryForecaster()
forecaster.fit(series)

# Predecir h1, h2, h3
predictions = forecaster.predict(new_df)  # q10, q50, q90 por horizonte
```

**Fuentes del forecaster:** `src/xray.py` TrajectoryForecaster (mlforecast + LightGBM cuantílico), `src/evaluate.py` build_series, `DECISIONS.md` D13 (exógenas por horizonte retardadas h meses), D20 (CQR), D23 (forecaster final: LightGBM cuantílico q10/q50/q90, 6 exógenas por horizonte)

### Paso 7: Validación

```python
from src.evaluate import run
result = run(
    exog_cols=["score_raw", "runway", "activity_trend", "months_since_last_tx", "score_raw_d3", "month_idx"],
    tag="v7"
)
print(result)
```

**Métricas objetivo para v7:**
- AUC deterioro ≥15: >0,74 (mejorar de 0,703 del AR1)
- Cobertura intervalo 80% h3: >80%
- MAE h3: <11,0 (mejorar de 11,2)
- Skill vs AR(1) h3: >5%

**Fuentes de las métricas objetivo:** `DECISIONS.md` D23 (evidencia v6: "AUC deterioro ≥15 0,742 (AR1 0,703)"), `DECISIONS.md` D22 (skill frente a AR(1): v6 +3,8%)

---

## 4. CAMBIOS EN EL CÓDIGO POR ARCHIVO

### 4A. `src/features.py` — Añadir 10 nuevas features

```python
# Líneas ~40-70: añadir las 10 nuevas features
# Cada una con definición exacta, ventana, dirección
# EPS relativo (0,1% del volumen mensual) = invariancia de escala real
# Fuente: DECISIONS.md D16 (robustez para empresas nunca vistas: EPS relativo)

def add_features(p: pl.DataFrame) -> pl.DataFrame:
    p = p.sort("company_id", "month").with_columns(
        [pl.col(c).fill_null(strategy="forward", limit=3).over("company_id", order_by="month") for c in STICKY if c in p.columns])
    # ... existing features ...
    
    # ===== NUEVAS FEATURES v7 =====
    
    # 18. lost_accel (aceleración de pérdida de clientes)
    # Definición: lost_share_m − lost_share_{m-3m}
    # Fuente: features.md sección B-A, Cursor Auto
    p = p.with_columns(
        lost_accel=(pl.col("lost_share") - pl.col("lost_share").shift(3).over("company_id"))
    )
    
    # 19. payee_concentration (HHI de payments by counterparty_id, 3m)
    # Definición: HHI de amount<0 por counterparty_id, media de 3m
    # Fuente: features.md sección B-A, Cursor Auto
    # ... calcular HHI de amount<0 por counterparty_id ...
    
    # 20. oper_persistence_6m
    # Definición: % de últimos 6m con oper_in >= 50% mediana 12m
    # Fuente: features.md sección B-A, Cursor Auto. Clave para bache vs estructural.
    oper_median12 = pl.col("oper_in").rolling_median(12, min_samples=1).over("company_id")
    p = p.with_columns(
        oper_persist_bool=(pl.col("oper_in") >= 0.5 * oper_median12).cast(pl.Int32),
        oper_persistence_6m=(pl.col("oper_persist_bool").rolling_mean(6, min_samples=3).over("company_id") * 100)
    )
    
    # 21. billing_to_cash
    # Definición: ar_issued(3m) / oper_in(3m). Bajo = dejando de facturar o cobrar.
    # Fuente: features.md sección B-A, Cursor Auto
    p = p.with_columns(
        billing_to_cash=pl.col("ar_issued").rolling_mean(3, min_samples=1) / (pl.col("oper_in").rolling_mean(3, min_samples=1) + EPSC)
    )
    
    # 22. tax_miss (solo meses fiscales Ene/Abr/Jul/Oct)
    # Definición: max(0, tax_esperado − tax_real) / tax_esperado, donde tax_esperado = tax_12m / 4
    # Fuente: features.md sección B-A, Cursor Auto. Propuesta original: GLM 5.3
    # (ver section B-C: "Obligaciones: cobertura de la próxima cuota de préstamo con debt_schedule_config")
    # ... ver definición exacta arriba ...
    
    # 23. runway_vs_group
    # Definición: runway − mediana(runway) por group_id en mismo mes
    # Fuente: features.md sección B-A, Cursor Auto
    # ... runway - mediana(runway) por group_id en mismo mes ...
    
    # 24. ap_aging_deep
    # Definición: overdue_90_ap / overdue_ap
    # Fuente: features.md sección B-A, Cursor Auto
    p = p.with_columns(
        ap_aging_deep=pl.col("overdue_90_ap") / (pl.col("overdue_ap") + EPS)
    )
    
    # 25. vol_asymmetry
    # Definición: vol_upside / vol_downside de net_flow en 6m
    # Fuente: features.md sección B-A, Cursor Auto. Propuesta original: GLM
    # ... vol_upside (semidesv positiva) / vol_downside (semidesv negativa) en 6m ...
    
    # 26. multi_signal_stress
    # Definición: cuenta de 4 señales: inflow<-20%, activity<-20%, n_cust<-20%, cash_drop>1 burn
    # Fuente: features.md sección B-A, Cursor Auto
    # ... cuenta de 4 señales: inflow < −20% median, activity < −20% median, n_cust < −20%, cash_drop > 1 burn ...
    
    # 27. shock_vs_usual
    # Definición: si net < 0: abs(net) / mediana(abs(net_neg), 6m)
    # Fuente: features.md sección B-A, Cursor Auto
    # ... si net < 0: abs(net) / mediana(abs(net_neg), 6m) ...
    
    return p.with_columns([pl.col(c).fill_nan(None) for c in ALL_FEATURES if c in p.columns and p.schema[c] in (pl.Float64, pl.Float32)])
```

### 4B. `src/xray.py` — Actualizar SPEC dict

```python
# Quitar: net_margin_6m, debt_burden, refund_rate
# Añadir: lost_accel, payee_concentration, oper_persistence_6m, billing_to_cash, 
#         tax_miss, runway_vs_group, ap_aging_deep, vol_asymmetry, multi_signal_stress, shock_vs_usual

# Actualizar PRIOR_W con pesos iniciales para las nuevas features
# Fuente: features.md sección B-A (peso estimado por feature)
# Los pesos finales se calibrarán automáticamente con calibrate=True (logística con signo restringido)

PRIOR_W = {
    "runway": 3, "lc_util": 1, "growth_vs_12m": 1.5,
    "ap_late_share": 1.5, "ar_late_share": 1, "ap_overdue_ratio": 1, 
    "ar_overdue_90_ratio": 0.5, "activity_trend": 1.5, "transfer_dep": 0.5, 
    "hhi_ar_6m": 0.5, "net_vol_6m": 0.5, "cust_trend": 1.0, "lost_share": 1.0,
    # NUEVAS:
    "lost_accel": 2.0, "payee_concentration": 1.5, "oper_persistence_6m": 2.0,
    "billing_to_cash": 1.5, "tax_miss": 1.0, "runway_vs_group": 1.0,
    "ap_aging_deep": 1.0, "vol_asymmetry": 1.0, "multi_signal_stress": 1.5,
    "shock_vs_usual": 1.0,
}
```

**Fuentes del SPEC dict:** `src/xray.py` (SPEC dict con 17 features actuales), `features.md` sección 4 (tabla de 17 features con peso y cobertura), `features.md` sección B-A (nuevas features con AUC)

### 4C. `src/service.py` — Añadir colchón dinámico y recomendaciones

```python
class XRayService:
    # ... existing methods ...
    
    def get_colchon(self, cid: str) -> dict:
        """Calcula colchón dinámico para una empresa."""
        # 1. Obtener cash_end, median_outflow, forecast de runway
        # 2. cash_needed = 2 * median_outflow (colchón mínimo = 2 meses de gasto)
        # 3. cash_excess = cash_end - cash_needed
        # 4. trajectory_h3 = q50 de runway a h3 (forecaster)
        # Fuente: context/monetizacion.md (colchón dinámico), analysis/monetizacion.py (cash_needed = 2 * median_outflow), analysis/cash_history.py (cash_end reconstruido)
        return {
            "cash_needed_eur": 45000,
            "cash_actual_eur": 62000,
            "cash_excess_eur": 17000,
            "runway_current": 3.2,
            "runway_h3": 2.1,
            "deposit_recommendation": "Colocar 10.000€ en depósito",
            "est_annual_yield": 250,
        }
    
    def get_recommendations(self, cid: str) -> dict:
        """Recomendaciones accionables por empresa."""
        # Leer feature scores, deltas, banda
        # Generar lista de recomendaciones priorizadas
        # Fuente: sección 3 de "ESPECIFICACIÓN COMPLETA: Sistema X-Ray Score v7" (las tablas trigger → acción)
        return {
            "urgent": [
                {"action": "Perdiste un cliente clave", "detail": "...", "impact": "−5,2 pts score"},
            ],
            "prevention": [
                {"action": "Cobros tardíos", "detail": "...", "impact": "−2,8 pts score"},
            ],
            "opportunity": [
                {"action": "Colocar excedente", "detail": "...", "gain": "+250€/año"},
            ],
            "monitoring": [
                {"action": "Trayectoria h3", "detail": "...", "warning": "runway h3 = 2,1 meses"},
            ],
        }
```

### 4D. `static/index.html` — Añadir panel "Colchón dinámico" y "Recomendaciones"

```javascript
// En viewEmpresa(), después del score hero header:
// Patrón: h() helper ya usado en la SPA (ver viewEmpresa() línea ~1100)

function renderColchonPanel(colchon, recommendations) {
    return h('div', { class: 'section' }, [
        h('h2', 'Tu colchón este mes'),
        h('div', { class: 'colchon-bar' }, [
            h('div', 'Colchón necesario: ' + fmtEuros(colchon.cash_needed_eur)),
            h('div', 'Colchón actual: ' + fmtEuros(colchon.cash_actual_eur)),
            h('div', 'Excedente: ' + fmtEuros(colchon.cash_excess_eur)),
            h('div', 'Runway: ' + colchon.runway_current + ' meses'),
        ]),
        h('div', { class: 'forecast' }, [
            h('small', 'Trayectoria h3: ' + colchon.runway_h3 + ' meses'),
        ]),
        
        h('h2', 'Recomendaciones'),
        ...renderRecommendations(recommendations),
    ]);
}

function renderRecommendations(recs) {
    return [
        ...recs.urgent.map(r => h('div', { class: 'alert urgent' }, [
            h('span', 'URGENTE'),
            h('strong', r.action),
            h('p', r.detail),
            h('small', r.impact),
        ])),
        ...recs.prevention.map(r => h('div', { class: 'alert warning' }, [
            h('span', 'PREVENCIÓN'),
            h('strong', r.action),
            h('p', r.detail),
            h('small', r.impact),
        ])),
        ...recs.opportunity.map(r => h('div', { class: 'alert success' }, [
            h('span', 'OPORTUNIDAD'),
            h('strong', r.action),
            h('p', r.detail),
            h('small', r.gain),
        ])),
        ...recs.monitoring.map(r => h('div', { class: 'alert info' }, [
            h('span', 'MONITOR'),
            h('strong', r.action),
            h('p', r.detail),
            h('small', r.warning),
        ])),
    ];
}
```

**Fuentes del patrón de rendering:** `src/static/index.html` viewEmpresa() (líneas 1100-1187, patrón de h() helpers, Chart.js charts), `src/server.py` endpoints (GET /api/company/{id}, GET /api/company/{id}/treasury)

---

## 5. RESUMEN DE CAMBIOS NECESARIOS

| Archivo | Qué cambiar | Líneas | Prioridad | Fuente del diseño |
|---|---|---:|---:|---|
| `src/features.py` | Añadir 10 nuevas features (lost_accel, payee_concentration, oper_persistence_6m, billing_to_cash, tax_miss, runway_vs_group, ap_aging_deep, vol_asymmetry, multi_signal_stress, shock_vs_usual) | +80-100 | **Alta** — Día 1 | `features.md` sección B-A, `src/features.py` patrón actual |
| `src/xray.py` | Actualizar SPEC dict, PRIOR_W, quitar 3 canceladas (net_margin_6m, debt_burden, refund_rate) | +20-30 | **Alta** — Día 1 | `src/xray.py` SPEC dict actual, `features.md` sección C |
| `src/targets.py` | Verificar que E5/E6 existen (tension_entrada, apagado) | +0-20 | **Media** — Día 1 | `src/targets.py`, `features.md` sección 4 (eventos) |
| `src/panel.py` | Si falta `group_id` en el panel, añadirlo para runway_vs_group | +10-20 | **Media** — Día 1 | `src/panel.py` (panel mensual), `data/data_dictionary.md` (groups.csv) |
| `src/service.py` | Añadir colchón dinámico + recomendaciones a endpoints | +60-80 | **Alta** — Día 2 | `src/service.py` patrón actual, `context/monetizacion.md` (colchón dinámico) |
| `static/index.html` | Añadir panel colchón + recomendaciones en viewEmpresa() | +80-100 | **Alta** — Día 2 | `static/index.html` viewEmpresa() (líneas 1100-1187), patrón de h() |
| `analysis/colchon_dinamico.py` | Generar HTML de colchón dinámico (como monetizacion.py) | ~100 | **Baja** — Día 3 | `analysis/monetizacion.py` (patrón de HTML generation) |
| `artifacts/xray.joblib` | **Entrenar modelo** (generado por service.py) | — | **CRÍTICA** — Día 1 | `src/service.py` (service.py: entrena con todo el train y guarda artifacts/xray.joblib) |

---

## 6. CRONOGRAMA DE 1 DÍA

| Hora | Actividad | Entregable | Fuente del plan |
|---|---|---|---|
| **09:00 – 09:30** | Verificar datos: `ls data/`, `git lfs pull` | Datos accesibles | `features.md` sección 2 (dataset), `data/data_dictionary.md` |
| **09:30 – 10:00** | Añadir 10 nuevas features a `features.py` | `features.py` actualizado | `features.md` sección B-A (10 nuevas features) |
| **10:00 – 10:30** | Actualizar SPEC dict en `xray.py` + quitar 3 canceladas | `xray.py` actualizado | `src/xray.py` SPEC dict, `features.md` sección C |
| **10:30 – 11:00** | `python src/service.py` → entrenar modelo | `artifacts/xray.joblib` generado | `src/service.py` (entrena con todo el train y guarda artifacts/xray.joblib) |
| **11:00 – 11:30** | `python src/server.py` → levantar API | API en `http://127.0.0.1:8099/` | `src/server.py` |
| **11:30 – 12:00** | Verificar SPA funciona con nuevo modelo | SPA con score v7 | `static/index.html` |
| **12:00 – 13:00** | Añadir colchón dinámico a `service.py` + `index.html` | Panel colchón visible | `context/monetizacion.md` (colchón dinámico), `analysis/monetizacion.py` |
| **13:00 – 14:00** | Añadir recomendaciones a `service.py` + `index.html` | Recomendaciones accionables | Tabla trigger → acción (sección 3 de ESPECIFICACIÓN COMPLETA) |
| **14:00 – 15:00** | Pulido: diseño, navegación, tests | Demo completa lista | `src/app/DESIGN.md` |

**Total: 6 horas de desarrollo.**

---

## 7. BONUS: CAMBIOS QUE NO SE PUEDEN HACER HOY

| Feature | Estado | Por qué no hoy | Fuente |
|---|---|---|---|
| Divisa anticipada | ❌ No implementado | Necesita datos de FX por transacción y cálculo de spread | `context/monetizacion.md` "Por qué la divisa pesa", `analysis/monetizacion.py` |
| Marketplace crédito | ❌ No implementado | La cola pequeña (0,9%). Mención en roadmap | `context/monetizacion.md` "La conversación incómoda" |
| Alertas por email/SMS | ❌ No implementado | Fuera de scope del hackathon | `features.md` sección 5 (qué te pedimos) |
| NLP en description/concept | ❌ No implementado | Necesita modelo de lenguaje | `features.md` sección B-C: "Palabras de refinanciación, impago o aplazamiento en description y concept (DeepSeek, Qwen)" |
| Forecaster con grupo prior | ❌ No implementado | Falta `runway_vs_group` en panel | `features.md` sección B-A: `runway_vs_group` 0,57 vs estructural |
| Modelo fundacional (TimeGPT-2) | ❌ No implementado | Necesita API key de Nixtla | `DECISIONS.md` D24: "TimeGPT-2 de Nixtla sí encaja: como alternativa (challenger) del TrajectoryForecaster, en particular para empresas con historia corta (zero-shot). Queda pendiente de la API key y del permiso para enviar datos a un servicio externo (o de desplegarlo on-prem)" |

---

## 8. RESULTADO FINAL DE LA DEMO

### Vista de empresa en el Dashboard

```
======================================================================
  EMPRESA: COMP_00142 · Score: 58 · Banda: Vigilar · ↓ 12 pts
======================================================================

  Tu colchón este mes
  Colchón necesario:  45.000 €  (2 meses de gasto)
  Colchón actual:    62.000 €  ████████████████████████
  Excedente:         17.000 €  ██████
  Runway:            3,2 meses → h3: 2,1 meses
  
  ¿Es un bache o es estructural?
  Probablemente bache: oper_persistence_6m = 67%
  
  Recomendaciones
  1. URGENTE — Pérdida de clientes acelerada (−5,2 pts)
  2. PREVENCIÓN — Cobros tardíos (−2,8 pts)
  3. OPORTUNIDAD — Colocar excedente (+250€/año)
  4. MONITOR — Trayectoria h3: runway 2,1 meses
```

**Fuente de la vista:** `src/static/index.html` viewEmpresa() (patrón actual de h() helpers, Chart.js charts), `src/service.py` (GET /api/company/{id}), `src/features.py` (17 features + 10 nuevas), `src/xray.py` (HealthScorer.score_panel), `context/monetizacion.md` (colchón dinámico), Tabla trigger → acción (sección 3 de ESPECIFICACIÓN COMPLETA)

### Vista Embat (monitor de cartera)

```
======================================================================
  EMBAT · Monitor de Cartera
======================================================================

  Empresas conectadas: 1.286
  Score medio: 52 · ↓ 3 este mes
  Alertas activas: 412 (score < 55)
  Empresas con excedente: 375 → 5,4 M€ colocables
  Empresas con exposición a divisa: 92 → 3,7 M€ opportunity
  
  Top 5 deterioros este mes:
  1. COMP_01234: 78 → 56 (lost_share ↑, activity ↓)
  2. COMP_00567: 65 → 41 (runway 5 → 0,8 meses)
  3. COMP_00891: 72 → 49 (ap_late_share ↑, ar_late_share ↑)
  4. COMP_00234: 68 → 44 (tension_6m activada)
  5. COMP_00678: 61 → 38 (runway < 1 mes)
```

**Fuente de la vista:** `src/static/index.html` viewMonitor() (líneas 1730-1761, patrón actual de alert cards), `src/service.py` (GET /api/monitor), `context/monetizacion.md` (375 empresas con excedente, 5,4 M€), `src/features.py` (features que activan deterioros)

---

## 9. GLOSARIO DE TÉRMINOS

| Término | Definición | Fuente |
|---|---|---|
| Score 0-100 | Media ponderada de percentiles de features (0-100) suavizada con EWMA(α=0,5) escalada linealmente a P5=15, P95=85 | `src/xray.py` HealthScorer, `DECISIONS.md` D12, D14, D17, D18 |
| Runway | Meses de caja restantes: `signo(cash_end) × log(1 + \|cash_end\| / burn)` | `src/features.py`, `DECISIONS.md` D09 |
| Bandas | Riesgo < 35 ≤ Vigilar < 65 ≤ Sano | `DECISIONS.md` D19 |
| EWMA(α=0,5) | Suavizado exponencial: un bache de un mes pesa la mitad | `DECISIONS.md` D14 |
| CQR | Calibración Conformal — ensancha el intervalo de confianza del forecaster | `DECISIONS.md` D20 |
| GroupKFold | Validación cruzada por group_id (evita fuga entre empresas del mismo grupo) | `DECISIONS.md` D22 |
| Exógenas | Variables externas al score que alimentan el forecaster (score_raw, runway, activity_trend, months_since_last_tx, score_raw_d3, month_idx) | `DECISIONS.md` D23 |
| Percentil congelado en train | Los percentiles se calculan sobre el set de entrenamiento y se congelan para evitar fuga de datos | `DECISIONS.md` D16 |
| EPS relativo | 0,1% del volumen mensual de la empresa → invariancia de escala real (el score no cambia al multiplicar importes) | `DECISIONS.md` D16 |
| OOD | Out-of-distribution — empresas que están fuera de los rangos del training set (se marca con confianza baja) | `DECISIONS.md` D16 |
| DQ balance_suspect | Flag de calidad de datos: saldos >100M€ son artefactos del generador y se marcan como sospechosos | `analysis/monetizacion.py` |
| Multi_signal_stress | Cuenta (0-4) de señales activas: inflow<−20%, activity<−20%, n_cust<−20%, cash_drop>1 burn en 3m | `features.md` sección B-A, Cursor Auto |
| oper_persistence_6m | % de meses con oper_in >= 50% mediana 12m (señal de que la operación sigue activa) | `features.md` sección B-A, Cursor Auto. Clave para bache vs estructural |
| lost_accel | `lost_share_m − lost_share_{m-3m}` (aceleración de pérdida de clientes) | `features.md` sección B-A, Cursor Auto |

---

## 10. PLAN POR FASES — EJECUCIÓN EN PARALELO (ASINCRÓNICO)

El plan está diseñado para que **todo el equipo trabaje en paralelo desde el minuto 0**. Cada persona edita archivos distintos y no hay dependencias entre las fases 1-4. Solo al final se unen en la Fase 5.

### FASE 1 — Feature Engineering (Jorge) + Model Training Prep (Álvaro) → PARALELO

**Duración: 2h | Depende de: nada**

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Jorge** (features) | Añadir 10 nuevas features a `features.py`: `lost_accel`, `payee_concentration`, `oper_persistence_6m`, `billing_to_cash`, `tax_miss`, `runway_vs_group`, `ap_aging_deep`, `vol_asymmetry`, `multi_signal_stress`, `shock_vs_usual`. Quitar 3 canceladas: `net_margin_6m`, `debt_burden`, `refund_rate`. | `src/features.py` | 27 features calculadas en panel |
| **Álvaro** (model) | Preparar targets para entrenamiento: verificar E5/E6 en `targets.py` (tension_entrada, apagado). Preparar pipeline de calibración: `scorer = HealthScorer(calibrate=True, l2=1.0)`. Preparar validación GroupKFold con `run` de `evaluate.py`. | `src/targets.py`, `src/evaluate.py` | Targets listos, validación configurada |

**Código que Jorge escribe:** Sección 4A de este documento (añadir 10 features a `features.py`)
**Código que Álvaro escribe:** Sección 3 de este documento (Paso 4-7 de calibración y validación)

---

### FASE 2 — Producto Backend (Producto) + Frontend SPA (Frontend) → PARALELO

**Duración: 2h | Depende de: nada (solo necesita el contrato API)**

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Producto** (backend) | Añadir `get_colchon(cid)` a `service.py`: calcula `cash_needed = 2 × median_outflow`, `cash_excess = cash_end - cash_needed`, `deposit_recommendation`. Añadir `get_recommendations(cid)`: genera lista de alertas priorizadas (urgente, prevención, oportunidad, monitor). | `src/service.py` | 2 nuevos endpoints API |
| **Frontend** (SPA) | Añadir panel "Tu colchón este mes" en `viewEmpresa()` de `index.html`: barra visual de colchón, excedente, runway. Añadir sección "Recomendaciones" con cards de alertas (color rojo/amarillo/verde). | `static/index.html` | 2 nuevos paneles visibles en SPA |

**API Contract (lo que ambos necesitan):**
```json
// GET /api/company/{cid}/colchon
{ "cash_needed_eur": 45000, "cash_actual_eur": 62000, "cash_excess_eur": 17000, "runway_current": 3.2, "runway_h3": 2.1 }

// GET /api/company/{cid}/recommendations
{ "urgent": [...], "prevention": [...], "opportunity": [...], "monitoring": [...] }
```

**Código que Producto escribe:** Sección 4C de este documento
**Código que Frontend escribe:** Sección 4D de este documento

---

### FASE 3 — Infraestructura (Transversal: Jorge y Álvaro) → PARALELO CON 1 Y 2

**Duración: 1h | Depende de: nada**

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Transversal (Jorge)** | Añadir `group_id` al panel (`src/panel.py`) para que `runway_vs_group` funcione. | `src/panel.py` | Panel con group_id |
| **Transversal (Álvaro)** | Actualizar `SPEC dict` y `PRIOR_W` en `src/xray.py` con las 27 features v7. Quitar 3 canceladas. | `src/xray.py` | SPEC dict con 27 features, pesos v7 |

---

### FASE 4 — Entrenamiento y validación (Álvaro) → DEPENDE DE FASE 1 y 3

**Duración: 30 min | Depende de: que Jorge añada las 10 features y Álvaro actualice SPEC dict**

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **Álvaro** (entrenamiento) | Ejecutar `python src/service.py` → genera `artifacts/xray.joblib`. Ejecutar `python src/server.py` → API en `:8099`. Ejecutar `run(tag="v7")` → verificar métricas. | `src/service.py`, `src/server.py`, `src/evaluate.py` | Modelo entrenado, API corriendo |

**Verificar que las métricas cumplen objetivos:**
- AUC deterioro ≥15: >0,74
- Cobertura intervalo 80% h3: >80%
- MAE h3: <11,0
- Skill vs AR(1) h3: >5%

---

### FASE 5 — Integración y pulido (TODO el equipo) → DEPENDE DE 1-4

**Duración: 1h | Depende de: todo lo anterior**

| Persona | Qué hace | Archivos | Entregable |
|---|---|---|---|
| **TODO** | Unir todo: `service.py` con colchón + recomendaciones funciona con modelo v7. `index.html` muestra colchón + recomendaciones correctamente. Pulir diseño: `DESIGN.md`. | `src/service.py`, `static/index.html` | Demo completa lista |

---

### DIAGRAMA DE DEPENDENCIAS

```
Fase 1:  Jorge ──────────[features.py]─────────┐
         Álvaro ───[targets.py]─────────────────┼──→ NO HAY DEPENDENCIA ENTRE ELLOS (paralelo)
Fase 2:  Producto ───[service.py]───────────────┤
         Frontend ──[index.html]────────────────┤
Fase 3:  Jorge   ───[panel.py]──────────────────┤─── PARALELO CON FASES 1 Y 2
         Álvaro ──[xray.py]─────────────────────┤
                                              │
Fase 4:  Álvaro ───[service.py run]──→ joblib ─┼──→ DEPENDE DE FASES 1 Y 3
                                              │
Fase 5:  TODO ────[Integración]──→ Demo lista  ─┘──→ DEPENDE DE FASES 1-4
```

**Total: 4-5 horas de trabajo real en paralelo (no 6 horas secuenciales como estaba antes)**

---

*Documento generado como plan de trabajo para el equipo de desarrollo del scoring v7. Todas las features, pesos, AUC, coberturas, definiciones y fuentes están validadas contra los archivos fuente indicados. Si una cifra no tiene fuente directa, se indica como estimación basada en el brainstorming del equipo.*