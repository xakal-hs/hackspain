# Review de la iteración v5b (workflow de 3 lentes en paralelo)

Lentes: validación y métricas · robustez OOD, explicabilidad y API · variables. Hallazgos sin editar; lo aplicado figura en DECISIONS.md.

## Resumen

He revisado la validación de v5b y la he reproducido fuera de muestra: el scorer de cada fold y corte, los 15 ajustes, con las 10.347 predicciones de preds_v5b. Los scripts están en /tmp/claude-1000/-home-balalo-repos-hackspain/99e409e1-c0e5-4ab9-b464-7a8943a362c9/scratchpad/a1.py–a8.py. No he tocado src/.

Estas partes no filtran información:
- La alineación de las exógenas por horizonte es correcta. mlforecast (core.py, `_get_cols_for_horizon` y el desplazamiento de `ds` en h) toma c_h{h} en t+h, que equivale a c(t), y `predict` (xray.py:324-335) construye lo mismo.
- El scorer se ajusta solo con empresas de train y meses ≤ corte (evaluate.py:70-71).
- Las etiquetas de calibración cumplen mes ≤ corte−6 (evaluate.py:49).
- El EWMA es causal (`adjust=False`, xray.py:183).
- El GroupKFold se hace por `group_id`.

La fuga temporal real que he encontrado es `months_since_last_tx`, que depende de la última transacción de todo el dataset.

El problema principal es otro: casi toda la mejora frente al naive viene de tres cosas que no son anticipación:
1. **Regresión a la media del nivel.** Solo con el nivel se obtiene un AUC de 0,711 en deterioro y de 0,772 en mejora, frente a 0,753 y 0,787 del modelo.
2. **Arrastre mecánico del EWMA.** A h1, un naive que tiene en cuenta el EWMA da un MAE de 2,61 frente a 2,55 del modelo.
3. **Deriva de rodaje.** Las empresas jóvenes bajan de forma sistemática.

Aun así, el modelo sí aporta en la cola: precisión del 64 % en el 5 % con mayor caída prevista, frente al 54 % del nivel solo. El monitor casi no ve la mejora: el recall de sus alertas es del 1,4 %.

A las métricas les falta medir la antelación sin sesgo, la separación entre bache y caída, la estabilidad de las alertas y la cara "sano". Además, el AUC de deterioro varía entre cortes: 0,793, 0,783 y 0,698.

### [alto] Casi toda la mejora frente al naive es regresión a la media y arrastre del EWMA, no anticipación

**Evidencia.** Calculado sobre preds_v5b con h=3 (3.449 series):
- AUC de deterioro: 0,711 con solo el nivel (y_T), 0,716 con AR1, 0,749 con una regresión lineal sobre (y_T, score_raw_T) ajustada con otros folds sin mirar el futuro, y 0,753 con el modelo.
- AUC de mejora: 0,772 con el nivel, 0,789 con la lineal y 0,787 con el modelo.
- dir_acc_big_moves: 0,836 el modelo, 0,843 la lineal y 0,784 con sign(mediana − y).
- El quintil superior cae de media 7,3 puntos y el 32 % baja 10 o más en 3 meses. El inferior sube 3,2 de media.
- MAE h1: modelo 2,55; naive 3,04; naive-EWMA 2,61 (0,5·y_T + 0,5·raw_T). A h1 queda un 2 % de mejora, no un 16 %: el score publicado es un EWMA (xray.py:183) y score_raw ya entra como exógena (evaluate.py:22).
- MAE h3: modelo 5,86; lineal 6,25; naive-EWMA 6,54.
- AUC de deterioro por corte: 0,793, 0,783 y 0,698. Por fold va de 0,72 a 0,81.

**Propuesta.** En summarize (evaluate.py:108-131):
- Añadir las líneas base «nivel» y «lineal(y_T, raw_T)», y usar como métrica principal la mejora frente a la lineal y frente al naive-EWMA, no frente al naive.
- Sustituir el AUC agregado por el AUC medio dentro de cada quintil de y_last. Hoy ese AUC va de 0,61 a 0,69 en los quintiles 2 a 4, y es la cifra honesta.
- Añadir la precisión en el 5 % y en el 10 % de las series en ambas direcciones, que es donde el modelo sí gana. Caídas: 0,64 frente a 0,55 de la lineal y 0,54 del nivel. Subidas: 0,39 frente a 0,33 y 0,29, con una tasa base de 0,084.
- Dar intervalos bootstrap por grupo y la cifra de cada corte.

### [alto] Artefacto de rodaje: el score baja de forma mecánica en empresas jóvenes y eso infla el deterioro y sus alertas

**Evidencia.** - Score fuera de muestra por edad: 63,0 hasta 2 meses, 58,2 entre 3 y 5, 55,4 entre 8 y 11, y 52,6 entre 20 y 24.
- Por mes de calendario: 67,3 en sep-24 y 52,9 en ago-26.
- En series con n_hist<6 (752, el 22 % de la evaluación) el Δ3m medio es −2,99 y P(caída ≥10) es 21,4 %. Con historia ≥12 meses: −0,82 y 12,1 %.
- En ese segmento el AUC de deterioro es 0,852, pero el nivel solo ya da 0,84.
- El 54 % de las 124 alertas de deterioro cae en empresas con menos de 6 meses de historia.
- Causas: la cobertura es 0,5 en month_idx 0 y 0,9 a partir del mes 12, y transform reponderará sobre las features disponibles (xray.py:141-145). Varias features empiezan en NaN: growth_vs_12m y activity_trend (features.py:205 y 215) y net_vol_6m (min_samples=3, features.py:226). Además, month_idx es exógena (evaluate.py:22), así que el forecaster aprende que «joven implica bajar».

**Propuesta.** - Cuando la cobertura sea inferior a 0,8, acercar las features que faltan a 50 en vez de reponderar las disponibles, o bien calcular percentiles de referencia por tramo de edad.
- Quitar month_idx de EXOG o recortarla a min(month_idx, 6).
- Marcar las empresas con n_hist<6 como «en rodaje» y no emitir alertas de trayectoria para ellas.
- Dar todas las métricas de cabecera también con n_hist≥6.
- Comprobar después que la media del score por edad queda plana, con una diferencia de ±1 punto como máximo.

### [alto] El monitor casi no ve la mejora y ve poco el deterioro: la regla del intervalo desperdicia la señal

**Evidencia.** - Deterioro: 124 alertas, con precisión 0,589 y recall 0,14.
- Mejora: 11 alertas en 3.449 series, con recall 0,014.
- La regla exige que todo el intervalo del 80 % quede más allá de y_last (evaluate.py:139-144 y xray.py:372-377). Con width80_h3 = 19,8, q90 < y_last solo se da en el 4,3 % de las series y q10 > y_last en el 0,5 %.
- La señal existe: el 5 % con mayor subida prevista tiene precisión 0,39 frente a una base de 0,084, un 4,7 veces más.
- Además, la deriva hacia abajo del hallazgo anterior hace la regla asimétrica.

**Propuesta.** - Alertar según P(Δ ≤ −10) y P(Δ ≥ +10) a 3 meses. Se pueden sacar interpolando los cuantiles o con un clasificador LightGBM directo sobre las mismas features.
- Fijar el umbral de cada lado fuera de muestra para una precisión objetivo, por ejemplo el 50 %.
- En evaluate.py, sustituir alert_* por curvas de precisión y recall en ambos sentidos y por el recall con precisión fija. Así la cara de mejora se mide igual que la de deterioro.

### [medio] Fuga temporal en months_since_last_tx: los huecos de actividad a mitad de serie se marcan como activos porque hay transacciones después

**Evidencia.** - panel.py:162-171 calcula months_since_last_tx = max(mes − último mes con transacciones en todo el dataset, 0).
- En panel.parquet hay 927 meses con n_tx==0. De ellos, 429 (en 115 empresas) figuran con months_since_last_tx=0 solo porque la empresa vuelve a operar más tarde.
- En tiempo real, esos meses aplicarían el límite de 30 puntos (xray.py:151-154) y generarían la alerta de «inactividad».
- La variable también entra como exógena del forecaster (EXOG_SMALL, evaluate.py:22).
- El backtest oculta así falsas alarmas y justo los «baches» de inactividad que el reto pide separar de las caídas.

**Propuesta.** - Calcular la variable de forma causal: meses desde el último mes con n_tx>0 hasta m, con un cummax de ese último mes activo por empresa.
- Mantener churn_6m como etiqueta futura aparte.
- Volver a ejecutar v5b y reportar cuántas alertas de inactividad se revierten. Es un caso natural de bache para la métrica de bache frente a caída.

### [medio] La antelación y la distinción entre bache y caída se miden con sesgo y no están en la evaluación principal

**Evidencia.** - evaluate.py no calcula ni la antelación, ni la clasificación de bache frente a caída, ni el parpadeo de alertas.
- En anticipation.py:81, la antelación usa al[0], es decir, la primera alerta de toda la historia anterior al cruce, sin ventana y sin controlar las falsas alarmas. Por eso v2 da una mediana de 7 meses con un horizonte de 3, y solo el 21,5 % de las caídas aparece detectado.
- La «verdad» sale del scorer del último corte (anticipation.py:45-46), mientras que las alertas usan el scorer de cada corte: son escalas distintas.
- La caída estructural se define frente a la media de los 3 primeros meses (anticipation.py:75), que están inflados por el rodaje.
- Bache frente a caída se etiqueta con raw_f2 a 2 meses (anticipation.py:89-90), pero el clasificador usa q50 suavizado a h3 (xray.py:379-384).
- En el score suavizado, las caídas de 10 o más a 3 meses siguen igual de abajo a T+6 en el 76,7 % de los casos (solo el 13,6 % recupera la mitad). Con clases tan desequilibradas, la accuracy no informa.

**Propuesta.** Mover a summarize las métricas siguientes:
- **Antelación.** Para cada evento (cruce por debajo de 45 o Δ ≤ −15 mantenido 3 meses), contar los meses entre la primera alerta que se mantiene encendida dentro de [t−6, t−1] y t. Presentarla junto a la tasa de falsas alarmas por empresa y mes en las series sin evento, como curva de antelación frente a falsas alarmas.
- **Bache frente a caída.** Una caída es real si a T+6 sigue al menos a la mitad de la bajada. Reportar la accuracy equilibrada y compararla con la línea base «todo es caída».
- **Estabilidad.** Porcentaje de alertas que se apagan al mes siguiente.

Usar siempre la misma versión del scorer para la verdad y para las alertas.

### [medio] «Quién está sano»: el nivel del score casi no distingue a las empresas sólidas ni anticipa la cara positiva

**Evidencia.** - auc_level_vs_positive_6m = 0,526, y 0,527 con edad ≥6.
- Tasa de adversidad a 6 meses por banda: riesgo 43,0 %, vigilar 25,1 % y sano 19,0 %.
- Por deciles, la adversidad del decil superior (18,2 %) es la misma que la de los deciles 7 y 8 (18,6 % y 18,0 %). La señal se concentra en el decil inferior (51,3 %).
- positive_6m llega al 21,9 % en el decil superior, frente a un 15 % de base.
- Los pesos se calibran solo con eventos adversos (EVENTS en evaluate.py:20 y fit_scorer en 46-52), así que nada premia detectar excelencia.

**Propuesta.** - Añadir a la calibración un evento positivo con restricción de signo, por ejemplo «permanece en la banda sana 6 meses sin evento adverso», o positive_6m reforzado.
- Reportar tres métricas de nivel:
  - la tasa de cada evento por decil, en tabla;
  - el lift del decil superior sobre «sano sostenido 6 a 12 meses»;
  - P(seguir en sano a 6 meses | está en sano).
- Con eso la pregunta «quién está sano» tiene métrica propia y queda simétrica a la de deterioro.

## Resumen

Estresé el artefacto final (artifacts/xray.joblib) con casos sintéticos: escalas de x1e-6 a x1e6, todo NaN, ±inf, historias de 1 a 6 meses, flujos a cero, ERP eliminado, huecos, meses duplicados y df vacío. También audité explain() sobre las 1.286 empresas en el último mes. Scripts en /tmp/claude-1000/xr/s1..s8.py; no he tocado src/.

Lo que ya funciona:
- El score casi no se mueve al multiplicar los importes por 1e3 o 1e6 (|Δ| medio 0,04), porque los percentiles saturan.
- Todo NaN da 50 con cobertura 0.
- Las series cortas no rompen: por debajo de 3 meses entra el AR(1) de respaldo y el mlforecast new_df acepta series de 3 a 5 meses con los lags a NaN.
- La explicación es exacta: la suma de ec_* reproduce el score, y solo el 3,8 % de las contribuciones de 0,5 pts o más aparecen con el valor de la feature sin cambiar (arrastre del EWMA).
- clone, get_params y set_params pasan los checks de sklearn.

Fallos principales, por orden de impacto:
1. Una empresa sin actividad puntúa como sana. Una empresa sintética con todos los flujos a cero saca 61,8 con confianza 0,97. Además hay 429 meses intermedios sin movimientos que no activan la regla de inactividad.
2. EPS=1 es absoluto, así que el score no es invariante con importes pequeños. A escala x1e-6 cambia de media 4,3 pts y hasta 40 como máximo.
3. Las facturas se convierten sin validar el tipo de cambio: 99 de las 785 empresas con ERP tienen facturas mal convertidas, con factores de hasta 17.000.
4. El indicador OOD y la confianza apenas discriminan. Los umbrales salen de colas absurdas y, si falta el ERP, el score se mueve entre −10 y +6 pts sin que la confianza lo refleje.
5. explain() enseña valores en unidades engañosas, y algunas features tienen peso 0, así que nunca pueden explicar un cambio.
6. La API sklearn tiene incoherencias menores: get_feature_names_out, el df vacío, los duplicados y la discontinuidad de intervalos a los 3 meses.

Respecto a la petición del usuario: los tipos reales ya se descargan de internet (BCE más fawazahmed0/currency-api en src/fx.py), pero no se aplican a las facturas y solo cubren las monedas de train.

### [alto] La inactividad y los denominadores a cero se puntúan como salud: una empresa sin movimientos sale 'casi sana' con confianza alta

**Evidencia.** Empresa sintética (COMP_0100) con todos los flujos y n_tx a 0: score 61,8, cobertura 0,97, confianza 0,97. Sub-scores que lo explican:
- net_vol_6m=0 → 98,7 (std 0/(0+EPS), features.py:63-64)
- transfer_dep=0, debt_burden=0 y ar_overdue=0 → 100 (two-part zero_best, xray.py:129-130)
- activity_trend=log((0+1)/(0+1))=0 → 49 (neutral)

En datos reales, months_since_last_tx no es causal: se calcula contra la ÚLTIMA transacción global (panel.py:169). Por eso la regla D15 (xray.py:152-153) solo capa la inactividad final. Hay 429 meses intermedios con n_tx=0 en 115 empresas que no se capan; el 12 % de ellos puntúa ≥65 ('sano'), con sub-scores medios de refund 100, debt 95, lc_util 88 y transfer_dep 81. En el test oculto, las empresas con actividad esporádica son justo el caso que se infla.

**Propuesta.** 1. En panel.py:169, sustituir months_since_last_tx por un contador causal de meses consecutivos con n_tx==0 (cum_sum con reinicio por empresa). Así el cap D15 se aplica también a los huecos intermedios y el forecaster aprende recuperaciones.
2. En features.py, devolver NaN (no aplica) en los ratios cuyo denominador sea despreciable, en vez de un 0 que el two-part convierte en 100. Afecta a in3, out3, oper3 y a la media de inflow de net_vol. Umbral de ejemplo: in3 < 1 % de la mediana de 12 m de la empresa, o < 100 EUR.
3. Añadir un test de regresión: empresa con flujos a cero ⇒ score ≤ dormant_cap y confianza < 0,3.

### [alto] EPS=1 absoluto rompe la invariancia de escala con importes pequeños y genera ratios absurdos que vacían el indicador OOD

**Evidencia.** Multiplicando todos los importes de 60 empresas:
- x1e-6: |Δscore| medio 4,28, p90 9,48, máx 39,98
- x1e-3: medio 0,29, máx 22,15
- x1e3 y x1e6: 0,03-0,04

La asimetría viene de EPS=1.0 (features.py:8), que se suma en las líneas 18, 41, 44-50, 53 y 64. A x1e-3, debt_burden deriva de media 23,2 y net_vol_6m 119. En los datos reales hay 1.118 filas activas (5,3 %) con in3 < 100 unidades de moneda. Sus ratios producen los umbrales OOD del percentil 99,5 del modelo final: payroll_burden 4.968, net_vol_6m 2.070, debt_burden 90, ap_overdue_ratio 155.049 y ar_overdue_90_ratio 447.326.

El EPS está además en moneda local: 1 JPY no es lo mismo que 1 EUR.

**Propuesta.** 1. Hacer EPS relativo a la escala de cada empresa, por ejemplo EPS_c = max(1 EUR·per_eur, 1e-3·mediana de gross_flow de 12 m), de modo que el suelo sea comparable entre monedas y tamaños.
2. Aplicar sign-log (log1p) a los ratios sin techo natural (ap/ar_overdue, payroll/debt_burden, net_vol) antes de calcular los bounds.
3. Añadir un test de propiedad a la suite: score(X·k) ≈ score(X) para k en {1e-6..1e6}, con tolerancia de 1 pt.

### [medio] Las facturas en moneda extranjera se convierten con el exchange_rate del fichero sin la validación D03, aunque el tipo real ya está descargado

**Evidencia.** panel.py:127 hace abs_amt = amount / exchange_rate sin contrastarlo con data/fx/fx_monthly.parquet, que ya contiene los tipos del BCE y de currency-api. En transacciones sí se valida (panel.py:44-49).
- De 56.085 facturas cuya moneda no es la de la empresa, solo el 68 % tiene un tipo a ±10 % del real, y el 26,4 % trae exchange_rate=1,0: USD→EUR 7.271, MZN→EUR 2.078 (factor 72), ARS→EUR 460 (factor 1.442).
- Afecta a 99 de 785 empresas con ERP; el factor de error llega a p90 72 y máx 17.323.
- COMP_1244 muestra ap_overdue_ratio 49.504 (unos 11 tras corregir) y COMP_0666 ar_overdue_90 20.536.

El efecto en el score es pequeño (~0,6 pts, porque el percentil ya satura), pero esos valores absurdos llegan a explain() y el HHI mezcla monedas.

Para el test oculto: fx.py solo descarga las monedas presentes en train (fx.py:75-78, MONTHS fijo en fx.py:18). Una moneda nueva cae en to_eur=1 (panel.py:180) y en fx=1 (panel.py:94) sin ningún aviso.

**Propuesta.** 1. En _invoices_monthly, unir fx_monthly por mes de emisión y currency/ccur, y aplicar la misma regla que en transacciones: aceptar el tipo del fichero si está a ±10 % del real, y si no usar el real.
2. Hacer que fx.build() se ejecute bajo demanda con las monedas que traiga el test, ya que el scraping del BCE y de jsdelivr ya existe.
3. Lanzar un aviso (y marcarlo en ood_features) cuando per_eur sea null, en vez de hacer fill_null(1.0).

### [medio] El indicador OOD y la confianza no protegen en el test oculto: umbrales degenerados, dominados por el tamaño y ciegos a la falta de ERP

**Evidencia.** Umbrales y tasa de alerta:
- Los bounds son los percentiles 0,5-99,5 de colas pesadas (xray.py:75), con valores como ap_overdue 155.049, así que en los ratios casi nunca saltan.
- La tasa base es alta: el 7,45 % de las filas de train tiene ood_share>0.
- Al escalar x1e6, el 93 % de las filas se marca OOD solo por log_scale (contexto), aunque el score cambia 0,04 pts.
- Cada flag solo resta 1/18 de confianza (xray.py:167 y 188).

ERP:
- Si se quita el ERP a empresas que lo tienen, el score cambia −2,1 pts de media, con p10 −10,4 y p90 +5,9 (renormalización en xray.py:141-145), y la confianza sigue en 0,68.
- Con esa renormalización, el AUC de nivel frente a churn_6m cae a 0,567 en empresas sin ERP (0,613 en el conjunto).
- Probé imputar 50 o la media poblacional en vez de renormalizar: AUC idéntico o peor (0,6153 frente a 0,6107), así que el problema es de comunicación de la incertidumbre, no de ranking.

**Propuesta.** 1. Calcular el OOD sobre las features transformadas (sign-log) con un z-score robusto (mediana y MAD, |z|>4), separando el OOD de tamaño (log_scale, que no debe penalizar) del OOD de comportamiento.
2. Convertir coverage en un intervalo del score: con los pesos que faltan, dar el rango [score si esas features valieran p10, score si valieran p90], y mostrarlo en la ficha y en el leaderboard.
3. Mostrar la banda 'sin ERP' explícitamente en explain.
4. Medir en evaluate.py el MAE y el AUC por segmento sin ERP, además de los segmentos actuales.

### [medio] explain() es exacta pero poco legible para el jurado: unidades engañosas, features con peso 0 que nunca explican nada y casos de error

**Evidencia.** Unidades:
- 'Meses de caja: 0,01 → 0,13' muestra log(1+caja/gasto) con signo (features.py:38), no meses: un runway de 2,0 son 6,4 meses.
- Los ratios salen como fracción (0,42) y no como %, y aparecen valores de 49.504 (ver el hallazgo de las facturas).
- El texto no enseña el sub-score o percentil antes y después, que es lo que de verdad mueve el número.

Pesos:
- En el artefacto final, net_margin_6m=0,0, debt_burden=0,0 y refund_rate=0,001, y en CV debt_burden vale 0,007±0,010.
- Por eso 'Carga de deuda' y 'Margen de caja' nunca aparecen como causa, y el simulador 'Cuotas de deuda ×3' solo mueve el score a través de runway. Es difícil de defender ante un jurado financiero.

Errores:
- explain(month=...) lanza IndexError si el mes no existe (xray.py:197).
- Con delta=0, el texto dice 'baja' (xray.py:221).
- Se mezcla el cambio del mes con el arrastre del EWMA sin avisar (corr Δraw/Δpublicado 0,88; el signo difiere en el 2,3 % de los meses con |Δ|≥2).

**Propuesta.** 1. Añadir en SPEC un formateador por feature (runway → expm1 en meses; share → %; ratios → '× gasto mensual', con tope '>100×') y mostrar 's: 38 → 61 (percentil)' junto al valor.
2. Agregar las contribuciones por pilar en summary_text.
3. Separar Δ = (cambio de este mes)·α + (arrastre del suavizado)·(1−α), lo que es exacto porque el EWMA es lineal.
4. Poner weight_floor≈0,02 (el parámetro ya existe en xray.py:97) para que las features con sentido económico no se anulen.
5. Devolver KeyError claro para un mes inexistente y 'se mantiene' si |Δ|<0,05.

### [bajo] La API sklearn es solo parcialmente coherente, y los intervalos pegan un salto al pasar de historia corta a LightGBM

**Evidencia.** Lo que funciona: clone, get_params y set_params pasan check_get_params_invariance y check_set_params en los dos estimadores.

Fallos de HealthScorer:
- get_feature_names_out devuelve 18 nombres, pero transform devuelve 41 columnas, una de ellas de texto (ood_features) (xray.py:170-174). Rompe set_output y los Pipelines numéricos.
- feature_names_in_ se rellena con SPEC y no con las columnas de entrada (xray.py:81).
- fit sobrescribe y.index = X.index en silencio (xray.py:88), lo que desalinea las etiquetas si y viene reordenada.
- El score publicado (EWMA) solo existe en score_panel, fuera de transform.

Fallos de TrajectoryForecaster:
- predict con un df vacío lanza ValueError 'No objects to concatenate' (xray.py:352).
- Acepta meses duplicados y huecos sin avisar y calcula los lags por posición.

Discontinuidad de intervalos:
- Con 2 meses de historia, el ancho q10-q90 a h1 es 15,7; con 3 meses, 9,7 (min_history=3).
- El respaldo inflado ×1,5 (xray.py:350) sobrecubre: cobertura 80 % real de 0,96 en fallback frente a 0,80 global (metrics_v5b.json).

**Propuesta.** 1. Hacer que get_feature_names_out refleje todas las columnas numéricas de transform y sacar ood_features a un método aparte (ood_report).
2. Alinear y con X.index mediante reindex, o comprobar la longitud y el índice.
3. En predict: validar (unique_id, ds) únicos y la frecuencia mensual sin huecos (asfreq por serie), y devolver un DataFrame vacío con el esquema correcto si no hay filas.
4. Calibrar el factor del respaldo con CQR, igual que el modelo principal, en vez del 1,5 fijo.
5. Condicionar el ajuste CQR a la longitud de historia (<6 frente a ≥6 meses) para evitar el salto de intervalo a los 3 meses.

## Resumen

Lente VARIABLES sobre la v5b. Para los análisis ajusté el scorer calibrado con train hasta el corte 2026-02 y lo apliqué al panel completo. Además correlacioné cada feature con tres cosas: el cambio futuro del score, y(t+3)−y(t), residualizado contra el nivel; los eventos observables (adverse, decline, cash_stress, churn y positive a 6 meses); y el residuo h3 de preds_v5b. Los scripts están en el scratchpad. No he tocado src/.

Qué mueve hoy el score. Del cambio mensual del score, transfer_dep explica el 26,6 % de la varianza, runway el 23,1 % y activity_trend el 19,7 %. En nivel, la desviación típica de la contribución es de 6,9 pts para runway, 6,9 para transfer_dep y 5,3 para net_vol_6m. net_margin_6m no aporta nada: su peso es 0,004 y su AUC es 0,500 frente a adverse, decline y cash_stress.

Hay dos problemas de construcción que generan movimientos que no son reales:
- **Arranque de cada empresa.** El score cae unos 9 pts solo por la edad de la empresa.
- **Stock de facturas vencidas.** Acumula facturas sin límite de antigüedad.

Features con señal sobre el cambio futuro que no están entre las exógenas del forecaster (rho frente al residuo h3 de v5b): ar_late_share −0,145, lc_util −0,129 (n=359), ap_overdue_ratio −0,102, growth_vs_12m −0,092 y ap_late_share −0,086, todas con p<0,001 salvo lc_util (p=0,015). ar_late_share y ap_late_share se podrían añadir a EXOG_SMALL. La de ap_overdue_ratio se explica en parte por la deriva del hallazgo 3.

Señales ocasionales:
- **Impuestos.** Los picos trimestrales apenas mueven el score gracias a las ventanas de 3–6 meses. La caída media del score sin suavizar (score_raw) es de −2,1 en enero y −1,7 en octubre, pero de −0,5 en abril y +0,1 en julio. tax_missed tiene AUC 0,52, sin valor. En cambio tax_rate12 (impuestos 12m / entradas 12m) sí aporta: AUC 0,44 frente a adverse y 0,42 frente a cash_stress, y rho +0,061 frente al residuo. Como proxy de rentabilidad sirve más que net_margin_6m.
- **tax_refund.** Solo hay 2 transacciones; es irrelevante.
- **Investment.** Ya se excluye bien.
- **Deuda.** El apalancamiento sacado de debt_products (saldo pendiente de préstamos, leasing, hipotecas y renting / entradas 12m) solo tiene AUC 0,48–0,51. Tener factoring o confirming da 0,50. debt_schedule_config tiene solo 87 filas. No compensa invertir aquí.
- **Conciliación.** El porcentaje de movimientos PENDING no tiene señal (AUC ≈ 0,50).

Los tipos de cambio ya salen de datos reales descargados de internet (BCE más currency-api, fx.py). No hace falta tocar nada ahí.

### [alto] El score cae unos 9 pts en los primeros meses de toda empresa por un artefacto de arranque (renormalización de pesos)

**Evidencia.** Las tres features temporales llegan tarde: activity_trend y growth_vs_12m son null hasta month_idx>=2 (features.py:42 y :52) y net_vol_6m necesita min_samples=3 (features.py:63-64). Mientras faltan, xray.py:141-145 reparte su peso entre las demás. Entre esas otras, transfer_dep y refund_rate son de tipo cero=mejor (xray.py:129-130) y valen 100 cuando son 0. Resultado: el score medio, con empresas activas, baja 67,0 → 65,8 → 61,9 → 60,6 → 59,4 → 58,4 → 57,7 entre month_idx 0 y 6. Sin ERP pasa de 64,5 a 55,4 y con ERP de 68,6 a 55,8. En el mismo tramo la contribución de refund_rate cae de 19,6 a 9,5 pts sin que cambie la feature. El problema toca a las 397 de 1.286 empresas con menos de 12 meses de historia y a las del test oculto, y produce falsos "empieza a torcerse".

**Propuesta.** En HealthScorer.transform, cuando falten growth_vs_12m, activity_trend o net_vol_6m por historia corta, imputar el sub-score neutro 50 en lugar de renormalizar. Los n/a estructurales (sin ERP, sin línea de crédito, sin nóminas) seguirían renormalizándose. Lo simulé con los pesos actuales: el perfil por month_idx pasa a 59,4, 58,8, 58,4, 58,8, 58,5, 57,9, 57,4, es decir, plano. Con month_idx>=6 la correlación con el score actual es 0,9999, así que las empresas maduras no cambian. La confianza baja ya existente (n/6) puede seguir recogiendo la historia corta.

### [alto] transfer_dep, el primer motor del Δscore, mide sobre todo entradas sin categorizar ('-') y transferencias intragrupo, no dependencia de financiación

**Evidencia.** En panel.py:73 transfer_in incluye la categoría '-', que supone el 45,3 % del valor de las entradas externas. Muchas son cobros de clientes: 'Efecto FC24-01529', 'betaling factuur … (incasso)', 'LIQUIDACION EFECTUADA', 'SCF-AJUS.SALDO'. La correlación Spearman de transfer_dep con el porcentaje de '-' es 0,72; con el de 'transfer' propiamente dicho, 0,43. Además, el 12,6 % de las entradas coincide el mismo día y por el mismo importe con una salida de otra empresa del mismo grupo (el placebo desplazando 7 días da 0,9 %). El 49 % de esas coincidencias está categorizado como 'transfer'. Pese a esto, transfer_dep explica el 26,6 % de la varianza del Δscore mensual (1,22 pts/mes de media) con un peso de 0,13. Su AUC es 0,447 frente a decline (dirección contraria) y 0,488 frente a adverse. Solo tiene señal con cash_stress (0,658), y esa señal viene del '-' (0,663), no de las transferencias reales (0,539).

**Propuesta.** En panel.py marcar como `intragroup` los emparejamientos mismo group_id + día + |importe| (>100) entre company_id distintos. Sacarlos de inflow/outflow como ya se hace con las internas, porque también contaminan net_vol_6m y runway. Después separar dos ratios: (a) true_transfer_share_6m = entradas 'transfer' no intragrupo / entradas, en ventana de 6 meses para reducir ruido, y (b) uncategorized_share = entradas '-' / entradas. La segunda debería ir a CONTEXT o confianza, porque es calidad del categorizador y no salud. Luego recalibrar pesos. Si hay que mantener algo ya, dar a transfer_dep un peso PRIOR fijo de 0,5 sin calibrar.

### [alto] ap_overdue_ratio acumula facturas vencidas eternas y se rellena con 0 antes de que existan facturas: deriva mecánica a la baja

**Evidencia.** panel.py:137 suma todas las facturas vencidas y no pagadas, sin límite de antigüedad. En la foto final, el 52 % de lo impagado lleva más de 180 días vencido y el 31 % más de 365. En la cohorte con facturas desde sep-2024, la mediana de ap_overdue_ratio sube de 0,005 a 1,12 (2024-09 → 2026-08) y el sub-score medio baja de 82 a 35. En empresas con ERP, ec_ap_overdue_ratio cae de 9,0 a 3,0 pts solo con la antigüedad. Además, panel.py:191-192 rellena con 0 cuando has_erp, aunque todavía no haya facturas. El 50 % de las empresas con ERP emite su primera factura después de sep-2024, lo que deja 704 filas con sub-score 100 y un tramo de subida artificial tras la primera factura. Este sesgo contamina el residuo (rho −0,10), que el forecaster confunde con deterioro.

**Propuesta.** Sustituir el stock por una ventana: overdue_ap_12m = importe de facturas AP con due_date ∈ [m−11, m_end) no pagadas a cierre / (out3/3). Su mediana se mantiene estable (≈0,5) y su AUC frente a cash_stress es 0,569 (0,545 hoy). Añadir el flujo nuevo overdue_ap_new3 (due_date en los últimos 3 meses y no pagado), con AUC 0,597 frente a cash_stress. Poner null en las features de facturas antes de first_issuance + 3 meses en lugar de 0. Hacer lo mismo con overdue_90_ar.

### [medio] Falta la dinámica de la base de clientes: pérdida de clientes y amplitud de cartera predicen churn y caída mucho mejor que hhi_ar_6m

**Evidencia.** Las facturas tienen counterparty_id en el 98,7 % de los casos, pero solo se usa para el HHI (panel.py:141-145), que tiene AUC 0,548 frente a churn y 0,556 frente a decline. Probé dos features nuevas. cust_trend tiene AUC 0,702 frente a churn, 0,606 frente a decline y 0,593 frente a adverse, y rho +0,083 frente al residuo h3 de v5b (n=1.409). lost_share tiene AUC 0,74 frente a churn y 0,592 frente a decline. Su correlación con activity_trend es solo 0,16, así que aporta información nueva. En transacciones, extraer COUNTERPARTY_xxx de description sube la cobertura de contraparte de las entradas del 5,6 % al 14,9 % del valor, todavía insuficiente como alternativa.

**Propuesta.** Añadir en _invoices_monthly (lado AR, facturas y invoiceGroup no canceladas): cust_trend = log((n_distintos_clientes_facturados[m−2..m] + 1) / (n_distintos_clientes[m−11..m]/4 + 1)). Y lost_share = porcentaje de la facturación de m−11..m−3 que corresponde a clientes sin ninguna factura en m−2..m, solo si hay al menos 3 clientes previos. Ambas irían al pilar estabilidad: cust_trend con dirección +1 y lost_share con −1 y cero=mejor. Se pueden explicar tal cual: "ha dejado de facturar a clientes que suponían el X % de su facturación". Rebajar hhi_ar_6m a contexto.

### [medio] La caja a fin de mes esconde la tensión dentro del mes, y la reconstrucción hacia atrás arrastra saldos fantasma

**Evidencia.** Reconstruí el saldo diario hacia atrás con la misma lógica que panel.py:87-101. El mínimo intramensual, cash_min_runway = sign(cash_min)·log(1+|cash_min|/burn), da AUC 0,786 frente a cash_stress (0,214 invertido), por 0,760 de runway. days_neg (días del mes con saldo agregado negativo) da 0,644. En la reconstrucción, el 31 % de los meses de cada producto anteriores a su primera transacción arrastran el saldo de apertura hacia atrás; 27.088 de ellos con |saldo| > 1.000. El 9,1 % de las filas del panel (17,5 % en 2024) tienen más del 50 % de su caja en cuentas que aún no se movían. Las cuentas TPV salen negativas en el 69 % de los meses.

**Propuesta.** En _balances_backward, calcular también el saldo diario por empresa y exportar cash_min y days_neg. Definir runway_min = sign(cash_min)·log(1+|cash_min|/burn), que sustituiría a runway o entraría a medias con ella. Añadir phantom_cash_share, la fracción de |caja| en productos antes de su primera transacción, como variable de contexto que reduzca la confianza. Excluir tpv de CASH_TYPES.

### [medio] net_vol_6m (peso 0,14) toma todo su peso de un decline_6m contaminado por entradas puntuales, y penaliza a empresas con mucha caja; net_margin_6m no aporta nada

**Evidencia.** Por evento, el coeficiente de net_vol_6m es 1,25 en decline_6m, 0,23 en churn y 0 en cash_stress. En targets.py:12 y :17-18, decline se mide contra in12/12, así que un único mes pico lo dispara. spike = máx(entradas 12m)/media 12m tiene AUC 0,737 frente a decline_6m. Con decline_robust, definido sobre medianas (mediana de las entradas de los 6 meses futuros < 0,5 × mediana de 12m), el AUC de net_vol baja de 0,632 a 0,588. Frente a cash_stress, net_vol_6m da 0,350: más volatilidad va con menos estrés. Su Spearman con runway es +0,54, porque se normaliza por entradas y las empresas con mucha caja y poca actividad salen "volátiles". Aun así, su contribución en nivel tiene 5,25 pts de desviación típica. net_margin_6m (features.py:41) da AUC 0,500 frente a adverse, decline y cash_stress y la calibración lo deja en peso 0, pero sigue apareciendo en SPEC, en el pilar rentabilidad y en las explicaciones.

**Propuesta.** (1) En targets.py redefinir decline_6m con medianas, como decline_robust, para que la calibración no premie predecir la reversión de picos. (2) Redefinir net_vol_6m como semidesviación a la baja del flujo neto dividida por el gasto: sqrt(mean(min(net,0)^2) over 6m)/burn. (3) Quitar net_margin_6m del score y poner en su lugar tax_rate12 = impuestos 12m / (entradas 12m + 1), con dirección +1: AUC 0,44 frente a adverse, 0,42 frente a cash_stress y rho +0,061 frente al residuo h3. Es un proxy de beneficio basado en los impuestos pagados, más difícil de maquillar que el margen de caja.
