# Review de la iteración v6 (workflow de 3 lentes en paralelo)

Lentes: validación y métricas · robustez OOD, explicabilidad y API · variables. Hallazgos sin editar; lo aplicado figura en DECISIONS.md.

## Resumen

Estresé las APIs con casos sintéticos y lancé el pipeline completo del test (predict_submission.py) sobre 5 escenarios de 65 empresas: base, sin ERP, importes x1e6, solo 2-3 meses de historia y moneda PEN, que no está en la tabla de tipos. También analicé preds_v6 y el panel completo con el modelo de artifacts/xray.joblib. HealthScorer aguanta bien valores extremos: los percentiles saturan, los inf y los strings pasan a NaN y la confianza cae a 0. Los problemas de robustez están en otro sitio. (1) Con historia corta (22 % de las series de validación) el sistema se queda ciego: el fallback da intervalos de 60 puntos, el recall de alertas es del 0-5 % y la mediana prevista tiene sesgo pesimista, que además explica que las alertas de mejora se queden en un 9 % de recall. (2) activity_trend pesa un 20,6 %, tiene un artefacto de ceros en el tercer mes de cada empresa y protagoniza el 69 % de las explicaciones de los movimientos grandes, con textos absurdos del tipo «+1 % → -0 % (-2,4 pts)». (3) explain() mezcla la inercia del EWMA con el cambio del mes, así que salen features con valor idéntico que «mueven» 2,8 puntos. (4) Sin ERP el nivel apenas discrimina (AUC 0,56) y la banda «sano» significa otra cosa. (5) El pipeline del test se rompe en dos casos: un fichero con una columna vacía (la inferencia de tipos del CSV la toma como texto) y umbrales absolutos en moneda local. Además, el tipo de cambio solo cubre 44 de las 341 monedas que ofrece currency-api. (6) La API sklearn es inconsistente: set_output('pandas') falla porque transform devuelve 46 columnas y get_feature_names_out 20. Scripts de estrés en /tmp/claude-1000/-home-balalo-repos-hackspain/99e409e1-c0e5-4ab9-b464-7a8943a362c9/scratchpad/ood/ (mk.py, stress.py, expl.py, erp.py, diag_scale.py).

### [alto] Series cortas (<6 meses): sin señal y con intervalos inflados por partida doble; sesgo pesimista de q50 que se come las alertas de mejora

**Evidencia.** preds_v6, h=3. Fallback (<3 meses, n=260): anchura media del intervalo 80 % = 60,0 pts frente a 37,5 en ≥12 m. Cobertura 0,977 frente al 0,80 nominal. MAE 9,62, peor que el naive (9,36). Recall de deterioro = 0,0 y de mejora = 0,0. Series de 3-5 meses (n=492): recall de deterioro 0,053 y de mejora 0,06, frente a 0,418 y 0,114 en ≥12 m. El doble inflado viene de xray.py:398 (`base + rq[q] * 1.5`) sumado al ajuste CQR de xray.py:403. Ese ajuste se calibró solo con filas no fallback (xray.py:285, `~p.fallback`), pero se aplica también a las fallback. La regla trend (predict_submission.py:63, `h3_q10 - y > -3`) nunca se cumple con esas anchuras: en el escenario sintético de 2-3 meses, 0 de 63 empresas tuvieron alerta de tendencia. Sesgo de q50: el Δ medio previsto es -2,49 con un Δ real de -1,15 (≥12 m) y -4,33 frente a -2,29 (6-11 m). Esto explica en parte que alert_up_recall sea 0,09 frente a 0,32 en deterioro (metrics_v6.json), cuando el reto exige señal en las dos direcciones.

**Propuesta.** En TrajectoryForecaster: (a) quitar el ×1,5 del fallback y calcular un cqr_fallback_[h] propio con los residuos de las series cortas del inner-fit, sin aplicar cqr_ a las filas fallback. (b) En el mismo paso conformal, guardar la mediana del residuo (y − q50) por h y por tramo de historia (<6, 6-11, ≥12) y sumarla a q10/q50/q90 en predict: es una corrección de sesgo que reequilibra mejora y deterioro. (c) Para historia <6 m, basar la alerta en q50 y no exigir que el intervalo excluya el cero. Mostrarla como «señal temprana, confianza baja». Validar con evaluate.py mirando recall_up/down por segmento.

### [alto] activity_trend domina el score y tiene un artefacto de ceros que genera saltos y explicaciones absurdas

**Evidencia.** Es el peso calibrado más alto: 0,206, con un rango de 45,6 pts publicados. El 8,2 % de ref_['activity_trend'] vale exactamente 0, y 1.286 de esos 1.550 ceros son month_idx==2. En features.py:56, cuando month_idx=2, n3/3 == n12/12 por construcción, así que toda empresa recibe un 0 en su tercer mes. growth_vs_12m (features.py:52) tiene el mismo artefacto. Por esa masa en el 0, pasar de 0 a +0,01 sube el sub-score de 49,4 a 55,9, lo que son +2,95 pts. En 400 meses con |Δscore| ≥ 5, activity_trend es el driver principal en 277 (69 %). Ejemplo real de explain() para COMP_0092: «Tendencia de actividad: +1 % → -0 % (-2,4 pts)». La variación mensual mediana de la feature es 0,064 log, unos 12 percentiles y unos 2,8 pts tras el EWMA, así que las empresas con actividad esporádica (un caso OOD probable en el test) van a oscilar.

**Propuesta.** En features.py:52 y :56, exigir month_idx >= 5 (o >= 6) para growth_vs_12m y activity_trend. Hasta entonces, NaN, que el scorer trata como neutro, y así esos ceros artificiales salen del ref_. En HealthScorer._sub, usar la ECDF interpolada (np.interp sobre los rangos) en lugar de searchsorted, para que un cambio mínimo nunca cruce un bloque de empates. Si hace falta, poner un tope al peso de una sola feature (p.ej. 0,15 con weight_floor/cap en fit). Comprobar en evaluate.py que la AUC de nivel no baja y que la volatilidad mes a mes del score disminuye.

### [alto] explain() mezcla la inercia del EWMA con el cambio del mes, y lo que de verdad pesa (los datos que faltan) no aparece

**Evidencia.** xray.py:230-241 muestra Δec_f, la contribución suavizada, junto al valor bruto de antes y de ahora. De 74.305 contribuciones de ≥0,5 pts, el 9,2 % corresponde a una feature cuyo valor bruto no cambió y el 17,4 % tiene el signo contrario al cambio real del mes. Ejemplo de COMP_0498: «Facturación de clientes perdidos: 0 % → 0 % (+2,8 pts)», que un jurado lee como un error. La línea c_sin_datos (xray.py:171) vale siempre 0 (máximo abs = 0,0). En cambio, un dato ausente se publica como sub-score 50, que en la escala publicada equivale a 38,79 puntos. Ese es el efecto que explica el nivel de las empresas sin ERP, y no se ve por ningún lado. Por último, explain solo compara con el mes anterior, así que no responde a «cuándo se vio venir».

**Propuesta.** Como el EWMA es lineal, separar Δec_f = α·(c_f,t − c_f,t−1) + α·(c_f,t−1 − ec_f,t−1). El primer término es el «cambio de este mes» y va por feature. El segundo es la «inercia de meses anteriores» y se agrupa en una sola línea. En el texto, añadir el percentil (s_f): «Meses de caja: 0,9 → 0,3 (percentil 41 → 18)». Sustituir c_sin_datos por la suma de contribuciones de las features imputadas: «Sin datos de ERP: X pts fijos». Añadir un parámetro ref_month a explain(), para descomponer contra hace 3 o 6 meses (sale exacto por aditividad), y devolver el primer mes en que cada driver cruzó su umbral.

### [medio] En empresas sin ERP (36 % de las filas) el nivel apenas discrimina y la banda «sano» no significa lo mismo

**Evidencia.** El 44,1 % del peso está en features de ERP, y en las empresas sin ERP son NaN al 100 % y se imputan con 50 (xray.py:166). AUC del nivel frente a adverse_6m: 0,559 sin ERP y 0,625 con ERP. Con score ≥ 65 (banda «sano»), la tasa de evento adverso a 6 meses es del 20,6 % sin ERP y del 13,9 % con ERP, es decir, 1,5 veces más riesgo con la misma etiqueta. Renormalizar los pesos sobre las features disponibles no lo arregla: la AUC queda en 0,568 y el porcentaje de «sano» sin ERP pasa del 9,9 % al 35 %, así que la decisión D21 de no renormalizar es correcta. Aun así, la banda y la confianza no reflejan esta diferencia: la confianza solo multiplica por coverage, que vale 0,50 de media sin ERP.

**Propuesta.** Mantener el neutro, pero calibrar los cortes de banda por segmento (has_erp), de forma que la tasa de adverse_6m en «sano», «vigilar» y «riesgo» sea igual en los dos segmentos. Son dos cortes más en BANDS, calculados en fit con las etiquetas ya disponibles. Otra opción es exigir coverage ≥ 0,7 para mostrar «sano» y, si no se llega, «sano (confianza baja)». Llevarlo al producto: «conectar el ERP sube la precisión» es un argumento de upsell para Embat. Reportar en metrics la AUC de nivel por segmento, porque el test oculto puede traer muchas empresas sin ERP.

### [medio] El pipeline del test se rompe con CSV atípicos, no es invariante a la escala o a la moneda y el tipo de cambio solo cubre las monedas del train

**Evidencia.** Escenarios de 65 empresas pasados por predict_submission.py. (1) Si invoices.csv solo trae la cabecera, polars infiere String y panel.py:131 falla («cannot compare date/datetime to a string»). Si balances.granted viene vacío entero, _credit_lines falla (`strict_cast(String).abs()`). En ambos casos el origen es predict_submission.py:34, que llama a read_csv sin schema. (2) Si una empresa no tiene transacciones, desaparece de la salida sin avisar (inner join en build_panel): en el escenario de historia corta entraron 65 empresas y salieron 63. (3) Con los importes x1e6, el score cambia hasta 17,5 pts (COMP_0552: 11,6 → 29,1), con una media de 0,23. El origen es el umbral absoluto `a > 100` en moneda local para detectar operaciones intragrupo (panel.py:60), que alteró n_tx en 61 filas y activity_trend en 329. Para una empresa en COP (3.739 COP/EUR), 100 COP son 0,03 EUR. (4) fx_monthly.parquet tiene 44 monedas. La API currency-api (consultada hoy, 2026-09-01) devuelve 341 en el mismo JSON, pero fx.py:47 guarda solo las pedidas. Una moneda nueva en el test cae al exchange_rate del fichero o a 1,0 (panel.py:47, 144 y 218). En el train, 7.991 transacciones necesitaron ya la corrección con el tipo real.

**Propuesta.** (1) En predict_submission, leer los CSV con `schema_overrides` igual al esquema de data/*.parquet del train, o hacer un cast tras la lectura. (2) Hacer un left join de companies.csv para emitir siempre una fila por company_id: score neutro, confidence 0 y banda «sin evaluar». (3) Pasar el umbral intragrupo a EUR: `a * to_eur > 100`. (4) En fx.api_monthly, guardar todas las monedas del JSON (`rows` para cada k de data) y regenerar fx_monthly.parquet con el BCE más currency-api. Añadir en panel un warning con la lista de monedas sin tipo real. Montar un test de humo con los 5 escenarios (mk.py en el scratchpad).

### [bajo] API sklearn incoherente y señal OOD poco informativa: se publican bandas sobre filas sin datos o fuera de distribución

**Evidencia.** `HealthScorer().set_output(transform='pandas')` lanza ValueError: «Length mismatch: Expected axis has 46 elements, new values have 20», porque get_feature_names_out (xray.py:196) no coincide con las columnas de transform. En un Pipeline, get_feature_names_out devuelve 20 nombres para 46 columnas. xray.py:83 asigna a feature_names_in_ las features puntuadas y no las columnas de entrada, y no existe n_features_in_. `transform(ndarray)` falla con AttributeError en lugar de un error claro. clone y get_params funcionan en los dos estimadores. Casos sintéticos: todo NaN → 38,79, «vigilar», coverage 0. Todo 1e6 → 37,8, «vigilar», con ood_share=1 y confidence 0, pero con banda publicada. Todo cero → 84,6, «sano», porque las features two-part valen 100 con cero aunque runway=0 (p_liquidez 13,7). Runway=+inf → se trata como sin dato. Las cotas OOD al 0,5/99,5 marcan por construcción el 8,5 % de las filas del train, y la media de ood_share es 0,0073, así que el indicador no separa lo realmente raro.

**Propuesta.** Hacer que get_feature_names_out devuelva exactamente las columnas de transform (guardar la lista en fit), o dejar transform solo con score_raw/coverage/ood_share/s_* y mover c_*/p_* a un explain_frame(). Poner feature_names_in_/n_features_in_ con las columnas de entrada y validar la entrada con un error claro si no es DataFrame. Tratar runway=±inf como percentil 100/0 antes del nan_to_num (xray.py:145-146). Añadir la regla de publicación «sin evaluar» cuando coverage < 0,3 o confidence < 0,15. Para OOD, usar un número de desviaciones fuera de rango (p.ej. |x − P50| > 3·IQR) o las cotas 0,1/99,9, y bajar la confianza en proporción a cuánto se sale, no solo al porcentaje de features.

## Resumen

Lente VARIABLES, sin tocar src/. Todo el análisis está en el scratchpad /tmp/claude-1000/-home-balalo-repos-hackspain/99e409e1-c0e5-4ab9-b464-7a8943a362c9/scratchpad/. var_newf.py contiene la definición de las features candidatas y var_cv.py ejecuta evaluate.run con parches en memoria; los resultados están en var_cv_{base,oblig,act612,oblig_cash}.json. La variante base reproduce v6 exactamente (MAE h3 11,2157).

Diagnóstico general:
- El score se mueve casi entero por una sola variable ruidosa, activity_trend. Explica el 75 % de los movimientos de 15 o más puntos y por sí sola da un AUC adverso de 0,597, frente a 0,594 del score completo.
- Hay pesos altos en variables sin señal: refund_rate pesa 0,13 con un AUC de aproximadamente 0,50.
- Faltan dos señales baratas y causales que salen de transactions: las obligaciones recurrentes omitidas (impuesto trimestral, cuota, nómina) y el saldo mínimo intramensual.
- La reconstrucción de caja y la de facturas tienen artefactos concretos que hay que filtrar.

Comprobación de señal sobre el cambio futuro. Se residualiza y(t+3)−y(t) sobre score, gap raw−EWMA y Δ3 pasado (R² 0,14) y se calcula el Spearman de cada feature con el residuo:
- La señal que queda es débil: |ρ| ≤ 0,13 en todas las features.
- ar_late_share da −0,131, ap_late_share −0,106, runway +0,104, cust_trend +0,103, growth_vs_12m −0,103 y activity_trend −0,099.
- Ninguna feature en Δ3 pasa de |0,11|.
- activity_trend (−0,215) y growth_vs_12m (−0,178) tienen ρ negativo en bruto con el cambio futuro. Eso indica reversión a la media: su subida de hoy anticipa una bajada del score.

Descartadas con datos:
- tax_refund: solo hay 2 filas.
- Flujo neto de investment: ΔAUC 0,000.
- Nuevos productos de deuda por created_at: es la fecha de conexión, no la de originación, y no da lift (adverso 20,7 % frente a 22,4 %).
- Liquidez con crédito no dispuesto (liq_total): ρ 0,102, igual que runway.
- Apalancamiento reconstruido: AUC adverso 0,43, en sentido contrario.
- Señales débiles pero coherentes para una segunda ronda:
  - Conciliación: accounting_status PENDING, adverso 22,6 % en los quintiles altos frente a 13,9 %.
  - Concentración de entradas por counterparty en banco: adverso de 12,7 % a 19,5 % por quintil.

Redundancias actuales (Spearman):
- cust_trend y lost_share: −0,654.
- net_margin_6m y net_vol_6m: −0,571.
- ap_late_share y ar_late_share: 0,551.
- ap_late_share y ap_overdue_ratio: 0,487.
- growth_vs_12m y activity_trend: 0,477.

### [alto] activity_trend domina el score y mete baches: es un ratio 3m/12m de nº de movimientos que revierte a la media

**Evidencia.** features.py:56 activity_trend = log(n3/3 ÷ n12/12). Peso medio en CV v6: 0,221 (metrics_v6.json), el mayor. La varianza mensual de su contribución es de 4,60 pts de desviación, frente a 2,23 de runway, y |Δ| medio de 3,19 pts/mes (el 40 % del movimiento del score). Es el driver dominante del 75 % de los movimientos grandes a 3 meses: 1.429 de 1.908 caídas ≥15 y 1.168 de 1.605 subidas ≥15. Revierte: corr(Δ3 pasado, Δ3 futuro) de su contribución = −0,138 y en growth_vs_12m −0,244. El nivel tiene ρ −0,215 con y(t+3)−y(t). Por sí sola da AUC adverso_6m 0,597, lo mismo que el score completo (0,594). Hay estacionalidad repetida en los dos años (n_tx relativo en agosto 0,84 y 0,81, en octubre 1,12 y 1,08). Experimento CV (var_cv_act612.json), sustituyendo activity_trend por log(media n_tx 6m / media 12m): MAE h3 11,22→9,91, AUC deterioro en el quintil alto 0,574→0,630, p_sigue_sano_3m 0,60→0,64, AUC nivel vs cash_stress 0,555→0,591. A cambio, AUC nivel vs churn baja de 0,586 a 0,547 y prec_top5_down de 0,47 a 0,38.

**Propuesta.** En el score de nivel, usar activity_trend_6_12 = log((mean_6m(n_tx)+1)/(mean_12m(n_tx)+1)), que no revierte (corr Δ +0,096), o limitar su peso a ≤0,10 tras calibrar. La versión 3m se mantiene solo como exógena del forecaster (ya está en EXOG_SMALL), que es donde su señal rápida de churn aporta sin mover el nivel publicado. Así se separa bache de caída por construcción. Si se mantiene la 3m, desestacionalizarla restando la mediana transversal por mes natural aprendida en fit().

### [alto] Faltan las obligaciones recurrentes omitidas (IVA trimestral, cuota de deuda, nómina): la señal ocasional más fuerte y explicable

**Evidencia.** panel.py:84-85 agrega tax y debt_service, pero ninguna feature los usa salvo debt_burden, que es un ratio. Feature oblig_missed_3m (var_newf.py), causal y solo de transactions, con n=8.252 filas etiquetadas:
- 0 eventos: adverso 21,2 %, churn 2,6 %, decline 15,7 %.
- 1 evento: 30,5 %, 5,4 % y 26,1 %.
- ≥2 eventos: 46,7 %, 11,8 % y 44,7 %.

Por tipo, en filas con el flag frente a sin él:
- IVA no pagado en trimestre: adverso 32,7 % frente a 22,0 %, churn 9,8 % frente a 2,8 %.
- Cuota omitida: adverso 31,7 %, decline 28,8 % frente a 16,5 %.
- Nómina omitida: adverso 43,8 %, decline 38,6 %.

Afecta al 7,3 % de las filas activas y a 354 empresas. En CV (var_cv_oblig.json) la calibración le da un peso de 0,074, y los AUC de nivel suben ligeramente: adverso 0,594→0,597, churn 0,586→0,589, decline 0,618→0,622, positive 0,568→0,571. Las métricas del forecaster bajan un poco (auc_deterioro 0,742→0,730), pero comparan targets distintos.

**Propuesta.** Añadir a SPEC (pilar disciplina, dir −1, zero_best=True) oblig_missed_3m = suma en 3 meses de tres eventos, contados solo en meses activos:
- tax_miss: mes en {1,4,7,10}, pagos de tax en ≥3 de los 12 meses previos y tax=0 en el mes.
- debt_skip: debt_service>0 en los 6 meses previos (≥5) y 0 en el mes.
- pay_skip: payroll>0 en ≥5 de los 6 meses previos y 0 en el mes.

Es la explicación ideal para el jurado: «no ha pagado el IVA de octubre». Ejemplo de mensaje del monitor: «obligación omitida».

### [alto] Liquidez: runway usa el saldo de fin de mes; el mínimo diario intramensual anticipa mejor. Hay saldos centinela que envenenan cash_end

**Evidencia.** features.py:42 runway sale de cash_end, que se reconstruye en panel.py:97-111. Reconstruyendo el saldo diario con el mismo método (saldo final − flujos posteriores por día):
- cash_min_ratio = sign(min)·log1p(|min diario|/gasto) da AUC cash_stress_6m 0,792, frente a 0,766 de runway.
- runway más neg_day_share (días con saldo<0 / días con movimiento) llega a 0,801.
- El 5,5 % de los meses activos cierran con caja ≥0 pero pasaron por negativo dentro del mes.

Artefactos:
- panel.py:104 hace fill_null(0) de balance y no valida outliers. COMP_0420 tiene 2 cuentas checking con saldo −1,0e9 cada una, 12 movimientos y 3.630 €/mes de flujo; COMP_0604 tiene −5e6 y COMP_0538 −4,99e6 con 4 movimientos.
- 91 cuentas checking tienen saldo final <0 (68 empresas, ninguna con granted/available informado) y 61 empresas tienen caja<0 en más del 50 % de sus meses. 11 empresas acaban con runway < −5.

**Propuesta.** 1) En _balances_backward, si |balance| > 100 × flujo bruto mensual del producto (o |balance| ≥ 1e9), tratar el saldo como desconocido: null y feature 'sin dato'. No como 0.
2) Añadir al panel cash_min (mínimo del saldo diario del mes) y neg_days.
3) Sustituir runway por runway_min = sign(cash_min)·log1p(|cash_min|/burn), o añadir neg_day_share (dir −1, zero_best) en el pilar liquidez.

### [medio] Peso alto a variables sin señal: refund_rate (0,13) y el bloque deuda/transferencias/volatilidad, inflados por normalizar cada evento

**Evidencia.** AUC univariante en la dirección de SPEC. refund_rate queda plano en los cuatro eventos, pero pesa 0,130±0,051 en CV v6. Hay otras cinco features plano o al revés que suman unos 0,07 de peso:

| Feature | churn | cash_stress | decline | positive |
|---|---|---|---|---|
| refund_rate | 0,498 | 0,504 | 0,492 | 0,515 |
| debt_burden | 0,451 | 0,501 | 0,493 | 0,539 |
| transfer_dep | 0,434 | 0,510 | 0,480 | 0,516 |
| ar_overdue_90_ratio | 0,496 | 0,504 | 0,497 | 0,529 |
| net_vol_6m | 0,478 | 0,457 | 0,528 | 0,427 |
| net_margin_6m | 0,524 | 0,520 | 0,473 | 0,389 |

Causa: xray.py:97-100 normaliza los pesos de cada evento a suma 1 y luego promedia. En positive_6m, con pocas features útiles, refund_rate se lleva el 51,5 % del peso (corte 2025-11), el 30,0 % (2026-02) y el 16,3 % (2026-05). Churn_6m se calibra con unos 30 eventos en el primer corte (1.744 filas × 1,7 %).

La deuda funciona al revés de lo que supone SPEC. Las empresas con debt_service>0 tienen churn 2,5 % frente a 3,4 % y adverso 22,2 % frente a 22,4 %. El apalancamiento reconstruido da AUC adverso 0,43 y churn 0,27: tener financiación bancaria indica solidez, no riesgo.

**Propuesta.** Sacar de SCORE_FEATURES (features.py:80) refund_rate, debt_burden, transfer_dep y ar_overdue_90_ratio. Pasarlas a CONTEXT para explicación y OOD. La señal de deuda que sí discrimina es debt_skip (hallazgo 2). En la calibración, ponderar cada evento por su información (p. ej., por n_eventos·(AUC−0,5)) en vez de normalizar cada vector a 1. Otra opción es exigir que el ΔAUC de cada feature en validación sea >0 para darle peso >0. Con 12-13 features el score es más estable y más fácil de explicar.

### [medio] Facturas: la morosidad reconstruida mezcla impago con ERP desactualizado, y la ventana de 12 meses crea mejoras artificiales

**Evidencia.** Hay 197.931 de 762.082 facturas impagadas en la foto final. Crecen hacia el final: 13,2k vencidas en 2025-Q1 frente a 38,6k en 2026-Q2. 70 de 702 empresas con ERP tienen más del 80 % de sus facturas vencidas (sep24-jun26) sin pagar. En esas empresas:
- ap_late_share medio 0,93 frente a 0,36 del resto; score medio 28,8 frente a 52,7.
- Churn_6m 13,0 % frente a 1,8 %, pero cash_stress solo 6,6 % frente a 4,6 %.

Parece desconexión o abandono del ERP, no falta de caja. Además, panel.py:159-160 solo cuenta como vencidas las facturas con due_date en los últimos 12 meses: una factura que nunca se paga desaparece del overdue al cumplir un año y el score sube sin que haya pago. El banco sí permite contrastar: 224.670 de 250.778 transacciones con counterparty_id comparten contraparte con facturas de la misma empresa.

**Propuesta.** 1) Conciliar factura y banco: marcar como pagada una factura 'overdue/pending' si hay una transacción con el mismo counterparty_id, signo opuesto e importe ±2 % entre due_date−10d y la foto. La fecha de pago pasa a ser la del movimiento.
2) Crear erp_stale = % de facturas del mes sin actualización de pago cuando el banco sí muestra movimientos con esas contrapartes. Usarlo como contexto o confianza, no como morosidad.
3) Sustituir la ventana dura de 12 meses por un decaimiento (peso 0,5^(antigüedad/6m)), para que la salida sea gradual y el explicador pueda atribuirla.

### [medio] «Quién mejora» no tiene ninguna variable de trayectoria de caja; la tendencia de caja a 6m aporta en la cara positiva

**Evidencia.** auc_mejora es la métrica más floja de v6 (0,715) y alert_up_recall es 0,09. Ninguna feature del score mide la evolución de la caja. ΔAUC incremental sobre el score (logística score+feature) para positive_6m:
- cash_trend_6m = log1p(caja/gasto)_t − log1p(caja/gasto)_{t−6}: +0,066.
- runway_d3: +0,048.
- recon_pending: +0,018.
- activity_trend: +0,024.

Para adverso los ΔAUC son ≤0,011. En CV (var_cv_oblig_cash.json), añadir cash_trend_6m al score da auc_mejora 0,715→0,721 y AUC de mejora en el quintil bajo 0,635→0,651. Pero la calibración solo le asigna un peso de 0,008, porque los pesos promediados los dominan los tres eventos adversos.

**Propuesta.** Añadir cash_trend_6m (pilar liquidez, dir +1, disponible si month_idx≥6) y darle un peso mínimo por prior para positive_6m, o calibrar por separado un subscore de 'mejora'. Además, pasar runway_d3 y cash_trend_6m como exógenas del forecaster: evaluate.py:36-42 ya calcula runway_d3 pero EXOG_SMALL no lo usa. Así la alerta de mejora tiene un motor explícito: «caja +X meses de gasto en 6 meses».

## Resumen

No encontré fugas temporales graves en el pipeline. El EWMA es causal (`adjust=False`, xray.py:206) y las ventanas móviles solo miran hacia atrás (features.py:14). Los percentiles, los pesos y la escala del scorer se ajustan solo con empresas de train y meses <= corte (evaluate.py:49 y 70-71). Las exógenas se retardan h meses (xray.py:313 y 379-381) y GroupKFold agrupa por group_id. Quedan dos fugas menores. La etiqueta de churn usa la última transacción de todo el dataset (panel.py:207, targets.py:189); frente a una versión causal discrepa en 11, 26 y 31 filas en los tres cortes, en torno al 0,5 %. El límite de las líneas de crédito sale de la foto final (panel.py:118).

El problema de fondo es otro: casi toda la ganancia del forecaster es regresión a la media y arrastre del EWMA. El score apenas anticipa hechos externos. Tres de las seis preguntas (antelación, bache frente a caída y estabilidad de alertas) no se estaban midiendo, porque anticipation.py falla. Lo ejecuté corregido en el scratchpad con estos resultados:
- 229 caídas estructurales; el 48,5 % tiene alguna alerta antes de cruzar a riesgo, con una mediana de 3 meses de antelación.
- Las alertas se encienden y se apagan al mes siguiente el 17,9 % de las veces.
- La regla de bache frente a caída no aporta señal: AUC 0,497.

Los scripts y resultados están en /tmp/claude-1000/-home-balalo-repos-hackspain/99e409e1-c0e5-4ab9-b464-7a8943a362c9/scratchpad/ (a1.py a a7b.py, antic.py, alerts_oof.parquet, truth.parquet). No he tocado nada de src/.

### [alto] La mejora frente al naive y al AR(1) es sobre todo regresión a la media y arrastre del EWMA

**Evidencia.** El 'auc_deterioro_ar1' de 0,703 coincide exactamente con el AUC que da y_last solo (0,704): d_ar es función monótona de y_last. Construí un baseline lineal de 2 parámetros (y ~ y_last + raw_last), ajustado con los otros folds del mismo corte y sin tuning; al usar esos 3 parámetros ya ve el futuro de otras empresas, así que es un baseline algo optimista. Resultados a h3 sobre preds_v6.parquet: MAE 11,22 del modelo frente a 11,41 del baseline, es decir, skill del 1,7 % con IC95 por bootstrap de grupos entre 0,1 % y 3,6 %. AUC de deterioro 0,742 frente a 0,731 y de mejora 0,715 frente a 0,707. El skill del modelo frente al lineal por corte es -0,6 % (2025-11), 0,8 % (2026-02) y 4,7 % (2026-05). A h1, el modelo (4,52) solo gana un 2 % a la persistencia del bruto (4,60). En el decil superior de y_last, que es la pregunta 'se tuerce aún pareciendo sana', el modelo da un AUC de 0,578 y el lineal 0,604. Ningún baseline tiene en cuenta el EWMA (evaluate.py:113-116 y 133-134).

**Propuesta.** En summarize() (evaluate.py:109) conviene añadir como baselines obligatorios la persistencia del bruto (raw_last + 0,5^h·(y_last − raw_last)) y una regresión lineal y ~ y_last + raw_last ajustada con train hasta el corte. Deberían reportarse los skills y las diferencias de AUC con IC95 por bootstrap de group_id, y un AUC estratificado por deciles de y_last para aislar la regresión a la media. El titular de final_choice.json (0,742 frente a 0,703) debería compararse con esa referencia.

### [alto] El nivel del score apenas predice hechos externos y rinde menos que una sola feature

**Evidencia.** Validez externa fuera de fold en metrics_v6.json: AUC de 0,594 para adverse, 0,586 para churn, 0,555 para cash_stress, 0,618 para decline y 0,568 para positive. Ajustando el scorer en el corte 2026-02 y evaluando dentro de muestra, lo que favorece al score: runway sola da 0,769 frente a 0,61 del score en cash_stress; activity_trend sola 0,634 frente a 0,605 en decline; net_margin_6m sola 0,611 frente a 0,549 en positive. Una causa probable es que los pesos se calibran por evento y luego se promedian (xray.py:93-100), así que cada señal específica se diluye. 'Quién está sano' tampoco se valida bien: solo el 60,6 % de las empresas con score >= 65 sigue en esa banda 3 meses después. Todo el resto de métricas mide cómo se predice el score a sí mismo, lo que es circular.

**Propuesta.** La métrica principal debería ser la validez externa por evento: AUC y precisión de la banda sana y de la banda riesgo frente a adverse_6m y positive_6m, fuera de fold, comparadas con la mejor feature individual (añadir en evaluate.py:100-102). Si el compuesto no supera a runway o a activity_trend, habría que calibrar una sola logística sobre adverse_6m agrupado y otra positiva, en lugar de promediar pesos. Otra opción es publicar subscores por pregunta (caja, actividad, rentabilidad) junto al score.

### [alto] anticipation.py falla y no se ha medido la antelación ni la estabilidad del monitor en v5/v6

**Evidencia.** En anticipation.py:52 el merge T.merge(A) duplica la columna y (queda y_x e y_y), y en la línea 54 'g.y.shift(-H)' lanza 'AttributeError: DataFrameGroupBy object has no attribute y'. Por eso log_anticipation_v5.txt está vacío y no existe anticipation_v5.json; el único informe es anticipation_v2.json, de otra versión del modelo. Lo ejecuté corregido (A.drop(columns='y')) con 9 cortes mensuales y 5 folds por grupo:
- Alerta de deterioro: precisión 0,338 (tasa base 0,139), recall 0,324.
- Alerta de mejora: precisión 0,367, recall 0,079.
- 229 caídas estructurales: el 48,5 % tiene alguna alerta antes, con una mediana de 3 meses.
- Si solo cuentan las alertas de los 6 meses previos emitidas con score >= 35, baja al 39,3 % con una mediana de 4 meses.
- Flicker del 17,9 %, y el 36,6 % de las empresas recibe al menos una alerta de deterioro en 9 meses.
La definición original toma al[0], la primera alerta en cualquier momento (anticipation.py:81), y así infla la antelación con alertas antiguas sin relación con la caída. Además, no mide falsas alarmas por empresa y año.

**Propuesta.** Corregir el merge e integrar la antelación en evaluate.py como métrica del leaderboard interno. Debería incluir la antelación con ventana (≤6 meses, alerta emitida cuando la empresa aún no estaba en riesgo), la cobertura de caídas y de subidas estructurales, las falsas alarmas por empresa y año, y el flicker. Conviene sacar la curva antelación frente a precisión variando ALERT_DELTA.

### [medio] La regla de bache frente a caída no tiene señal y se evalúa sobre otra escala que la de producción

**Evidencia.** anticipation.py:40 calcula la caída sobre score_raw, pero service.py:90 y predict_submission.py:65 la calculan sobre el score publicado (EWMA). Una caída ≥15 ocurre en el 7,7 % de los orígenes con el bruto y solo en el 1,7 % con el EWMA, así que en producción la alerta casi nunca salta. En la evaluación con el bruto hay 226 caídas; la regla (xray.py:429-434) marca bache solo en el 0,4 % de ellas y aparece 9 veces en 9.959 orígenes. Su exactitud es 0,721, peor que decir siempre 'caída' (0,796), y el AUC de −(q50 − y) es 0,497. La regla también mezcla escalas: estima el nivel previo como score_now − drop con drop del bruto y α = 0,5, lo que sobrestima ese nivel en drop/2 y empuja todo hacia 'caída'.

**Propuesta.** Definir la verdad sobre el score publicado: bache si en 3 meses recupera al menos la mitad, caída estructural si no. Medirla con AUC y exactitud balanceada frente a las referencias 'siempre caída' y persistencia. Reescribir la regla con el nivel previo real (el score del mes anterior) y usar señales de amplitud: cuántos pilares caen, y si cae activity_trend o growth_vs_12m frente a solo runway o la volatilidad. Es la pregunta 4 del reto y ahora mismo no se responde.

### [medio] Las alertas son asimétricas: la mejora queda infradetectada por el sesgo de q50 y la deriva del score

**Evidencia.** En preds_v6 a h3, el umbral ±10 sobre q50 produce 447 alertas de deterioro y 93 de mejora, con recall de 0,32 para el deterioro y de 0,09 para la mejora (0,079 en el backtest mensual). La q50 está sesgada a la baja: −2,83 puntos en la banda riesgo y −1,62 en vigilar. El score medio con percentiles congelados baja de 54,0 (2024-09) a 45,8 (2026-08), sobre todo por ap_overdue_ratio (−2,4), refund_rate (−2,0) y runway (−1,5); la tasa base es de 17 % caídas frente a 13,6 % subidas. Con umbrales por cuantil simétrico (el 10 % de cada cola), la mejora da precisión 0,354 y recall 0,261, y el deterioro 0,446 y 0,263. Entre las empresas sanas (y_last >= 65), 304 de 704 (43 %) reciben alerta de deterioro con precisión 0,398 frente a una base de 0,324 (lift 1,23): es spam en la banda que más importa al comprador.

**Propuesta.** Calibrar ALERT_DELTA por separado para cada dirección, fuera de fold, para igualar la precisión o la tasa de alerta (xray.py:411 y 423-428; evaluate.py:150-155). Reportar la media de AUC y de recall de mejora y de deterioro como métrica de 'dos caras', y el lift por banda. Estudiar cómo recentrar la deriva mensual, por ejemplo con percentiles por mes o con un término de nivel en el forecaster.

### [medio] El umbral de 15 puntos cae dentro del ruido del score y la caja reconstruida tiene un artefacto con tendencia

**Evidencia.** La desviación típica del cambio mensual es 12,8 puntos en el score bruto y 6,9 en el publicado. El 24 % de los meses activos tiene |Δ3| >= 15 y share_big_moves es 0,306; para empresas con score >= 75 la proporción es del 32 %, así que un '82→68' es lo habitual. La autocorrelación de Δ1 publicado (0,38) es el arrastre mecánico del EWMA. La caja reconstruida hacia atrás (panel.py:97-111) sale negativa en el 11,1 % de las empresas activas en 2024-09, frente al 2,4 % en 2026-08. Es probable que se acumulen flujos que faltan o errores de tipo de cambio hacia atrás, y ese error contamina tanto runway (peso 0,133) como la etiqueta cash_stress_6m (targets.py:190).

**Propuesta.** Definir los movimientos reales en relación con la volatilidad de cada empresa: Δ3 / desviación típica de su Δ1, o 15 puntos mantenidos 2 meses, con los mismos umbrales para las métricas y para el monitor. Medir el error de reconstrucción (saldos negativos por antigüedad frente a la foto) y excluir o ponderar a la baja los meses antiguos en cash_stress. Recalcular churn_6m de forma causal hasta el corte en fit_scorer (evaluate.py:49), aunque su efecto sea pequeño (≈0,5 % de las etiquetas).
