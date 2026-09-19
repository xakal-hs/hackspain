# Registro de decisiones
Generado por `src/decisions.py`. Las gráficas están en la SPA, pestaña «Decisiones».

## D01 · El score se calcula por empresa, no por grupo

*Categoría:* producto · *Estado:* a confirmar con la organización

**Pregunta.** ¿Score por company_id o por grupo empresarial? El enunciado habla de 250 empresas y hay 1286 en 250 grupos.

**Decisión.** Score, trayectoria y alertas por company_id. La validación separa por group_id para que ningún grupo esté a la vez en train y test.

**Por qué.** Todos los ficheros se cruzan por company_id y cada empresa tiene su propia caja y sus propias facturas. Un grupo mezcla negocios distintos (holdings de hasta 24 empresas). Separar por grupo en la validación evita la fuga que avisa el enunciado.

**Alternativas descartadas.** Agregar por grupo (ponderando por volumen). Se puede hacer después sobre los scores de empresa si el leaderboard lo pide.

**Evidencia.** 1286 empresas en 250 grupos; mediana de 3 empresas por grupo.

## D02 · Sin etiquetas: score anclado a hechos observables

*Categoría:* modelo · *Estado:* a confirmar con la organización

**Pregunta.** ¿Hay variable objetivo? El dataset no trae etiquetas de impago ni de salud.

**Decisión.** El nivel es un score interpretable (percentiles ponderados). Sus pesos se calibran con eventos futuros observables: apagado (la empresa deja de operar), tensión de caja (saldo negativo) y declive (cobros <50 % de su media anual). La trayectoria es una previsión supervisada del propio score.

**Por qué.** Un score sin ancla externa puede estar al revés sin que ninguna métrica lo detecte. Eso nos pasó en la v1: AUC de 0,37 frente al apagado. Con eventos observables, el nivel del score significa algo y se puede medir.

**Alternativas descartadas.** Score totalmente no supervisado (clustering, PCA): no es interpretable ni verificable. Predecir directamente el evento: sería una caja negra y solo daría una cara del problema.

**Evidencia.** Tasas de evento a 6 meses: apagado 3,0 %, tensión de caja 5,4 %, declive 17,0 %. AUC del score final frente a evento adverso: 0.59.

## D03 · Tipos de cambio: los del dataset, validados contra BCE y currency-api

*Categoría:* datos · *Estado:* decidido

**Pregunta.** ¿Qué tipo de cambio usar para las cuentas en otra moneda?

**Decisión.** Se descargan tipos reales mensuales: BCE (oficial, 30 monedas) y fawazahmed0/currency-api (13 monedas que el BCE no publica: ARS, CLP, COP, AOA, MZN...). En transacciones y en facturas se usa el tipo del fichero si está a ±10 % del real y, si no, el real del mes. El tamaño de la empresa (log_scale) se pasa a EUR con el tipo real.

**Por qué.** El 4 % de los movimientos está en productos con una moneda distinta de la de la empresa. Sin convertir, un movimiento en CLP pesa unas mil veces más. Los tipos del dataset son correctos casi siempre, pero hay filas con fx=1 (MZN, parte de GBP) o 0 (VND redondeado), que darían importes absurdos o una división por cero.

**Alternativas descartadas.** Usar siempre el tipo real: perdería el tipo efectivo del banco. Usar siempre el del dataset: rompe con fx=1 o fx=0.

**Evidencia.** 92,3 % de las 105310 transacciones en otra moneda tienen un tipo a ±10 % del real. El resto se corrige con el tipo real del mes (fx=1 no informado, fx=0 por redondeo en VND).

## D04 · Transferencias internas fuera de los flujos

*Categoría:* datos · *Estado:* decidido

**Pregunta.** ¿Cuentan como cobros o pagos los traspasos entre cuentas de la misma empresa?

**Decisión.** Un par del mismo día, con el mismo importe y signo opuesto entre dos productos de la empresa se marca como interno. Lo mismo con los pares entre dos empresas del mismo grupo (intragrupo, >100). Ambos se excluyen de entradas y salidas, igual que investment_deployment/return.

**Por qué.** Inflan los denominadores (entradas, salidas) sin actividad económica real y diluyen ratios como el margen o la carga de deuda. Los intragrupo además hacían pasar por 'dependencia de transferencias' lo que es tesorería del grupo.

**Evidencia.** El 26,8 % del volumen bruto son traspasos internos o intragrupo.

## D05 · Facturas: impagadas según pending_amount, no según payment_date

*Categoría:* datos · *Estado:* decidido

**Pregunta.** ¿Cómo saber si una factura estaba impagada a fin de cada mes?

**Decisión.** Impagada = pending_amount ≠ 0 y status ≠ paid. En ese caso se ignora payment_date. Si hoy está impagada, estuvo impagada en todos los cierres anteriores (sin fuga). Los pagos tardíos se miden a fecha de cierre, sin mirar pagos posteriores. Se descartan las fechas imposibles (año 7025).

**Por qué.** En las facturas vencidas, payment_date es igual a due_date en el 96 % de los casos. Usar payment_date las daba por pagadas en plazo y la morosidad real (unas 170 000 facturas) no se veía.

**Evidencia.** overdue: payment_date = due_date en el 96 %, con pendiente > 0 en el 100 %; paid: payment_date = due_date en el 52 %, con pendiente > 0 en el 0 %; pending: payment_date = due_date en el 98 %, con pendiente > 0 en el 100 %

## D06 · Primer mes parcial fuera y ventanas escaladas: sin artefacto de arranque

*Categoría:* datos · *Estado:* decidido

**Pregunta.** ¿Por qué las empresas recién incorporadas parecían más sanas?

**Decisión.** Se descarta el primer mes si la primera transacción cae después del día 5 (mes parcial). Las sumas móviles se escalan a w meses (media × w) en vez de sumar lo que haya.

**Por qué.** Con rolling_sum(min_samples=1) el gasto de 3 meses con solo 1 mes de historia se infraestimaba y el runway salía inflado. Todas las empresas nuevas parecían líquidas y 'se deterioraban' al madurar.

**Evidencia.** Mediana del runway en el mes 0: 1,30 con el método antiguo y 0,64 con el nuevo; en el mes 6: 0,49 y 0.43.

## D07 · Las empresas que dejan de operar siguen en el panel

*Categoría:* datos · *Estado:* a confirmar con la organización

**Pregunta.** ¿Qué hacer con las empresas cuyas transacciones terminan antes de agosto de 2026?

**Decisión.** La rejilla llega siempre hasta el último mes completo. Los meses sin movimientos tienen flujos a 0 y un contador CAUSAL de meses consecutivos sin movimientos (months_since_last_tx), que se reinicia al volver a operar. Regla de negocio: sin movimientos, el score no puede pasar de 30. El apagado definitivo (months_since_final_tx, que mira el futuro) se usa solo como etiqueta, nunca como feature.

**Por qué.** Dejar de operar es la señal de deterioro más fuerte y antes desaparecía del panel (sesgo de supervivencia). Sus entradas caen mucho antes del final, así que es anticipable.

**Evidencia.** 121 empresas se apagan antes de 2026-08. El review de la v5 detectó que el contador anterior (meses desde la última transacción del dataset) no era causal: 429 meses sin movimientos en mitad de la serie figuraban como activos. Con el contador causal hay 991 meses de inactividad frente a 498. Queda por confirmar con la organización si el apagado es cierre o baja de Embat.

## D08 · Ventanas de 6 y 12 meses en vez de 3 (estacionalidad y ruido)

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Qué ventana usar para el margen y el crecimiento?

**Decisión.** Margen de caja a 6 meses y tendencia de cobros como media de 3 meses frente a media de 12 meses. Los impuestos trimestrales (enero, abril, julio y octubre) quedan absorbidos.

**Por qué.** Con ventanas de 3 meses el margen y el crecimiento revertían a la media: eran ruido que movía más de la mitad del score. Comparar trimestres distintos mezclaba estacionalidad.

**Evidencia.** Persistencia mes a mes (Spearman): margen 3m 0,68 frente a 6m 0,80; crecimiento trimestral 0,55 frente a 3m/12m 0.69.

## D09 · Runway con base de gasto robusta: encogerse no mejora la liquidez

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Por qué las empresas que se apagaban tenían más 'meses de caja'?

**Decisión.** Runway = signo(caja) × log(1 + |caja| / gasto), con gasto = máx(media de 3 meses, media de 12 meses). La caja negativa da un runway negativo, así que la feature binaria sobra.

**Por qué.** Si el gasto se desploma, caja/gasto sube aunque la empresa se esté apagando. Con la base anual el denominador no cae y se premia la caja real.

**Evidencia.** AUC del runway frente a tensión de caja a 6 meses: 0,23 (menos de 0,5 = protege).

## D10 · Masa en cero: el cero es 'lo mejor' o 'no aplica', nunca un empate en el percentil 0

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Cómo puntuar features donde la mayoría de filas vale exactamente 0?

**Decisión.** Deuda, devoluciones, vencidos, retrasos, uso de póliza y transferencias: el 0 vale 100 y los positivos se ordenan entre sí (continuo en 0+). Nóminas = 0 se trata como 'no aplica' (NaN). En el resto, los empates van al rango medio.

**Por qué.** Con el primer índice del cuantil, el 88 % de filas con refund_rate = 0 caía al percentil 0 y un reembolso de 0,1 % hundía el score 90 puntos. Una empresa sin nóminas no está 'más sana' por eso, simplemente la feature no aplica.

**Evidencia.** Proporción de ceros entre las filas con dato: debt_burden 60 %, refund_rate 88 %, lc_util 38 %, ap_overdue_ratio 11 %, ar_overdue_90_ratio 42 %, ap_late_share 14 %, transfer_dep 68 %

## D11 · Nuevas señales: póliza de crédito, clientes perdidos, amplitud de cartera y volatilidad a la baja

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Qué variables añadir tras el review?

**Decisión.** Se añaden estas señales: lc_util (dispuesto/límite de pólizas, reconstruido hacia atrás), lost_share (% de la facturación de hace 3-12 meses de clientes a los que ya no se factura), cust_trend (clientes facturados en 3 meses frente a 12) y hhi_ar_6m (concentración). net_vol_6m pasa a medir solo la volatilidad a la baja (semidesviación de los meses con flujo negativo, sobre el gasto). transfer_dep se queda solo con las transferencias reales: la categoría '-' (sin categorizar) pasa a contexto. No se usan debt_products ni debt_schedule_config como features mensuales porque son una foto final y proyectarlos hacia atrás filtraría información.

**Por qué.** Perder clientes es la señal más temprana de apagado y de declive. El review de la v5 mostró que transfer_dep medía sobre todo cobros sin categorizar, y que la volatilidad total penalizaba a las empresas con mucha caja: lo que daña es la volatilidad a la baja.

**Evidencia.** AUC frente a apagado: lost_share 0,72, cust_trend 0.39. Frente a tensión de caja: lc_util 0.59. transfer_dep sin '-' frente a apagado: 0,43, casi sin señal.

## D12 · Pesos calibrados por evento con signo económico restringido

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Cómo fijar los pesos del score sin etiquetas y sin perder interpretabilidad?

**Decisión.** Para cada evento (apagado, tensión de caja, declive) se ajusta una logística P(evento) = σ(b − Σ w·s) con w ≥ 0, sobre filas cuyo evento ya era observable. Los pesos normalizados se promedian para que cada tipo de deterioro cuente igual. Si los datos contradicen la dirección económica de una feature, su peso queda en 0.

**Por qué.** Calibrar contra el evento compuesto dejaba que el declive (20 % de las filas) dominara, y la disciplina de pagos, que predice los apagados, quedaba en 0. Restringir el signo mantiene la monotonía: mejorar una señal nunca baja el score.

**Alternativas descartadas.** Pesos a priori (v4a): funcionan peor frente a eventos. Logística sin restricción: pesos negativos e inexplicables.

**Evidencia.** Pesos por debajo del 1 %: ninguno. Los datos no respaldan su dirección. Mayores pesos: Tendencia de actividad 21 %, Meses de caja 16 %, Facturación de clientes perdidos 10 %, Pagos tardíos a proveedores 10 %.

## D13 · Exógenas por horizonte retardadas h meses (horizon_feature_templates)

*Categoría:* modelo · *Estado:* decidido

**Pregunta.** ¿Cómo pasar señales actuales al forecaster directo de mlforecast sin fuga de información?

**Decisión.** Por cada exógena c se crea c_h{h} = c retardada h meses y se usa horizon_feature_templates. El modelo del horizonte h lee en la fila de la fecha objetivo T+h el valor de T, que es conocido.

**Por qué.** En la estrategia directa, cada modelo h usa la exógena en la fecha objetivo. Pasar c sin retardar sería una fuga y retardarla 3 meses para todos los horizontes da información vieja a h1 y h2. Lo verificamos con datos sintéticos (y_t = 5·x_{t−1}): con desplazamiento 1 el error es casi 0 en todos los horizontes.

**Evidencia.** MAE en el experimento sintético según el desplazamiento de la exógena: 0: 3,99, 1: 0,26, 2: 4,00, 3: 4,01

## D14 · Suavizado EWMA α = 0,5 con explicación exacta

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Cuánto suavizar el score publicado?

**Decisión.** Score publicado = EWMA(α = 0,5) del score bruto. Como el EWMA es lineal, se suaviza cada contribución por separado y el score sigue siendo la suma exacta de contribuciones: explain() cuadra al céntimo.

**Por qué.** Con α = 0,5 un bache de un mes pesa la mitad y una caída estructural se refleja al 87,5 % en 3 meses. Es el equilibrio entre estabilidad ante baches (lo pide el enunciado) y retraso en la detección.

**Evidencia.** Cambio medio mensual |Δ| y proporción de movimientos ≥10 a 3 meses según α: α=0,3: 3,23 / 24 %; α=0,4: 4,02 / 31 %; α=0,5: 4,77 / 35 %; α=0,6: 5,47 / 38 %; α=0,8: 6,86 / 43 %; α=1,0: 8,38 / 46 %

## D15 · Features de facturas: se arrastra el último dato hasta 3 meses

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Por qué el score saltaba cuando no vencían facturas en un trimestre?

**Decisión.** late_share_ap, late_share_ar y hhi_ar_6m arrastran el último valor conocido durante un máximo de 3 meses. Las tendencias se calculan desde el tercer mes de historia.

**Por qué.** Cuando una feature aparecía o desaparecía, los pesos se renormalizaban y el score bruto saltaba 8,9 puntos de media, frente a 4,7 sin cambio de disponibilidad.

**Evidencia.** Medido antes del cambio: |Δ score bruto| de 8,9 con cambio de disponibilidad frente a 4,7 sin él (19 % de las filas).

## D16 · Robustez para empresas nunca vistas: ratios, percentiles congelados, OOD sobre valores crudos y confianza

*Categoría:* ood · *Estado:* decidido

**Pregunta.** ¿Cómo se comporta el sistema con empresas del test oculto, quizá muy fuera de distribución?

**Decisión.** Features adimensionales (independientes de moneda y tamaño), con un suelo EPS relativo a la escala de la empresa (0,1 % de su volumen mensual) en lugar de 1 unidad fija: el score no varía más de 1 punto al multiplicar los importes por 1e-6..1e6 (test). Los percentiles se congelan en train y saturan en 0 o 100, sin extrapolar. El OOD se mide sobre valores crudos antes de recortar, más el contexto (tamaño en EUR, actividad, % en divisa). Se publica una confianza = cobertura × (1 − OOD) × historia. Con menos de 3 meses, respaldo AR(1) con intervalo ×1,5. Columnas ausentes = NaN (baja la cobertura, no falla).

**Por qué.** El test son 60-80 empresas nuevas, con historia corta, sin ERP o con escalas nunca vistas. Mejor un score con confianza baja y explícita que uno que extrapola.

**Evidencia.** MAE h3 por segmento (modelo / AR(1)): historia<6m: 10,4 / 10,5 (n=752); historia>=12m: 11,3 / 12,0 (n=1984); ood_share>0: 12,6 / 13,1 (n=395); fallback: 9,6 / 9,5 (n=260); cobertura<0,6: 9,4 / 9,9 (n=1106)

## D17 · Sin dato = valor neutro (50), no renormalizar

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Cómo puntuar una feature sin dato (sin ERP, historia corta)?

**Decisión.** Una feature sin dato contribuye con su peso × 50, el valor neutro. No se redistribuye su peso entre las demás. La cobertura (peso con dato) reduce la confianza publicada.

**Por qué.** Al renormalizar, una empresa con 2 meses de historia se puntuaba casi solo por su caja y salía más sana que la media (sesgo de arranque, grave para el test oculto de empresas nuevas). Además, el score saltaba cuando aparecía una feature. Con el neutro, lo que no sabemos tira al centro y la confianza lo refleja.

**Alternativas descartadas.** Renormalizar (v5b): +9,4 % frente a AR(1) pero con sesgo de arranque y un 24 % de movimientos grandes. Neutro (v5e): +5,2 % frente a AR(1), sin sesgo y con un 15 % de movimientos grandes. Se prioriza la estabilidad y la justicia con las empresas nuevas.

**Evidencia.** Mediana del score bruto en el mes 0 frente al mes 11: renormalizando 71,5 → 51,1; con neutro 51,8 → 47.9.

## D18 · Escala publicada: transformación lineal P5→15, P95→85

*Categoría:* score · *Estado:* decidido

**Pregunta.** ¿Cómo hacer legible el score (del estilo '82 → 68') sin perder la explicación exacta?

**Decisión.** Score publicado = a + b × compuesto, con a = -71,6 y b = 2,21, calibrados en train para llevar el P5 del compuesto a 15 y el P95 a 85. Se recorta a [0, 100] y el recorte aparece como término explícito en la explicación.

**Por qué.** La media ponderada de percentiles, con neutro para lo desconocido, concentra el score entre 38 y 68. Una transformación lineal abre el rango y mantiene la suma exacta de contribuciones, porque la constante se reparte según los pesos. Una transformación no lineal (percentil del compuesto) rompería la explicación.

**Evidencia.** Cuantiles del compuesto → publicado: P5: 39,2 → 15,0, P25: 48,1 → 34,5, P50: 54,8 → 49,4, P75: 61,5 → 64,2, P95: 70,9 → 85,0

## D19 · Bandas sano/vigilar/riesgo (65/35) y reglas del monitor

*Categoría:* producto · *Estado:* decidido

**Pregunta.** ¿Cuándo sale una alerta?

**Decisión.** Bandas: riesgo < 35 ≤ vigilar < 65 ≤ sano, aproximadamente los cuartiles de la escala publicada. Alerta de deterioro si la mediana prevista a 3 meses cae ≥ 10 puntos y el percentil 90 también está por debajo del nivel actual (el intervalo no cruza 0). Severidad alta si todavía parece sana (≥ 55). La mejora es simétrica. Bache frente a caída: tras una caída bruta ≥ 10 en el mes, es bache si la mediana prevista recupera al menos la mitad. Inactividad: alerta inmediata.

**Por qué.** Usar el intervalo y no solo la mediana reduce las falsas alarmas: solo se alerta cuando el modelo está seguro de la dirección. Los umbrales de banda dejan unos tercios aproximados de la cartera y se pueden ajustar al apetito de riesgo del comprador.

**Evidencia.** Distribución del último mes: riesgo 32 %, vigilar 48 %, sano 20 %.

## D20 · Regresión cuantílica (q10/q50/q90) con calibración conformal (CQR)

*Categoría:* modelo · *Estado:* decidido

**Pregunta.** ¿Cómo dar confianza a la previsión?

**Decisión.** LightGBM con objective = quantile para q10, q50 y q90 dentro de mlforecast. Después, CQR: se reentrena con train cortado H meses, se miden las puntuaciones de no-conformidad y se ensancha el intervalo por horizonte. q50 es la previsión puntual y los cuantiles se ordenan para que no se crucen.

**Por qué.** Sin calibrar, el intervalo nominal del 80 % solo cubría alrededor del 60 %: LightGBM cuantílico es demasiado confiado. CQR da cobertura garantizada sin cambiar el modelo.

**Evidencia.** Cobertura del intervalo 80 % por horizonte (sin CQR → con CQR): h1: 73 % → 80 %, h2: 74 % → 83 %, h3: 73 % → 79 %

## D21 · Eventos definidos contra la base anual, no contra el trimestre actual

*Categoría:* validación · *Estado:* decidido

**Pregunta.** ¿Por qué un margen alto 'predecía' deterioro?

**Decisión.** Declive = MEDIANA de los cobros de los 6 meses siguientes < 50 % de la mediana de los 12 anteriores: robusto a meses pico, no relativo al trimestre actual. Crecimiento = cobros medios > 130 % y caja al alza. Los pesos se calibran con 3 eventos adversos y 1 positivo, así el score también distingue a las empresas sólidas (dos caras).

**Por qué.** Comparar con el trimestre actual convierte cualquier pico en una 'caída' futura: es regresión a la media disfrazada de evento y premiaba a las empresas mediocres.

**Evidencia.** AUC del margen 6m frente a caída (definición inicial → actual): 0,53 → 0,53; tendencia de cobros: 0,63 → 0,43

## D22 · Validación: GroupKFold por grupo × 3 cortes, frente a AR(1)

*Categoría:* validación · *Estado:* decidido

**Pregunta.** ¿Cómo sabemos que generaliza y que no es regresión a la media?

**Decisión.** 5 folds por group_id × cortes nov-25, feb-26 y may-26. El scorer se ajusta sin la empresa y el forecaster predice con new_df. La referencia principal es un AR(1) agrupado por horizonte, no el naive.

**Por qué.** El review mostró que la ventaja de la v1 frente al naive era regresión a la media: un AR(1) la igualaba. Por eso toda mejora se mide contra el AR(1).

**Evidencia.** Skill frente a AR(1) a h3 por versión: v3a: +1,3 %, v3b: +4,7 %, v4a: +3,0 %, v4b: +5,5 %, v4c: -9,1 %, v5a: +7,4 %, v5b: +9,4 %, v5c: -14,6 %, v5d: +8,4 %, v5e: +5,2 %, v5f: +3,1 %, v6: +3,8 %

## D23 · Forecaster final: mlforecast + LightGBM cuantílico (q10/q50/q90, CQR) con 6 exógenas por horizonte

*Categoría:* modelo · *Estado:* decidido

**Pregunta.** ¿Cuántas exógenas y cuánta regularización?

**Decisión.** Exógenas: score_raw, score_raw_d3 (cambio a 3 meses), runway, activity_trend, months_since_last_tx (causal) y month_idx. Hiperparámetros por defecto (250 árboles, 15 hojas) y calibración conformal por horizonte. Score v6: sin dato = neutro, escala lineal publicada, pesos calibrados con 3 eventos adversos y 1 positivo.

**Por qué.** Con 21 exógenas el modelo sobreajusta a patrones que no generalizan entre grupos (skill a h3 −14,6 % incluso regularizado). Sin exógenas se pierde la señal fresca del mes. 6 exógenas con sentido económico dan el mejor equilibrio. La ganancia frente al AR(1) está en la cola, que es donde se actúa, y en las empresas que aún parecen sanas.

**Evidencia.** v6: AUC deterioro ≥15 0,742 (AR1 0,703); en el quintil alto 0,574 (AR1 0,493); AUC mejora 0,715 (AR1 0,683); en el quintil bajo 0,635 (AR1 0,542); precisión en el 5 % de cola: caídas 47 % (AR1 30 %), subidas 41 % (AR1 25 %); MAE h3 11,2 (AR1 11,7); cobertura 80 % h3 82 %. A h1 solo mejora un 2 % sobre el arrastre mecánico del EWMA (4,52 frente a 4,60).

## D24 · ¿Por qué una logística para los pesos del score y no un modelo generativo (p.ej. TimeGPT-2)?

*Categoría:* modelo · *Estado:* a confirmar con la organización

**Pregunta.** ¿Por qué la regresión logística decide el score? ¿Podríamos usar un modelo generativo o fundacional?

**Decisión.** La logística NO es el score: solo calibra los pesos w_f de una suma lineal de percentiles, con w_f ≥ 0. El score sigue siendo aditivo, monótono y con explicación exacta. La previsión de trayectoria es donde un modelo fundacional de series temporales (TimeGPT-2 de Nixtla) sí encaja: como alternativa (challenger) del TrajectoryForecaster, en particular para empresas con historia corta (zero-shot). Queda pendiente de la API key y del permiso para enviar datos a un servicio externo (o de desplegarlo on-prem).

**Por qué.** El enunciado exige que no sea una caja negra: 'para cualquier empresa hay que poder decir por qué saca ese número'. Un modelo generativo o una red dan mejor ajuste potencial, pero sus pesos no son explicables al jurado ni monótonos. La logística con signo restringido es la forma más simple de anclar los pesos a hechos observables sin perder la interpretabilidad. Si se quiere no linealidad manteniendo la explicación exacta, la alternativa natural es un GAM aditivo (Explainable Boosting Machine) con restricciones monótonas, no un modelo generativo.

**Alternativas descartadas.** GAM/EBM monótono (no lineal y aditivo): candidato razonable para el siguiente paso. LightGBM + SHAP: explicación aproximada y no monótona. TimeGPT-2 como scorer: es un modelo de previsión, no de clasificación de salud; sirve para la trayectoria, no para los pesos.

## D25 · Formato de salida para el leaderboard

*Categoría:* producto · *Estado:* a confirmar con la organización

**Pregunta.** ¿Qué formato pide el leaderboard?

**Decisión.** predict_submission.py genera un CSV por company_id y mes con: score, banda, confianza, q10/q50/q90 a 1-3 meses, tendencia y alerta. Todo sale de la API sklearn (fit sobre train, transform/predict sobre las empresas nuevas).

**Por qué.** No sabemos el formato exacto. Un CSV largo por empresa y mes cubre nivel, trayectoria y anticipación, y es fácil de adaptar.

## D26 · Frontend: SPA + FastAPI en vez de Streamlit o Gradio

*Categoría:* producto · *Estado:* decidido

**Pregunta.** ¿Streamlit, Gradio o SPA?

**Decisión.** Backend FastAPI con el modelo cargado en memoria (service.py) y una SPA de un solo HTML (Chart.js) con un contrato JSON explícito (app/API_CONTRACT.md).

**Por qué.** El simulador de escenarios necesita recalcular al mover cada slider (con debounce) y superponer base frente a escenario. Una SPA con API es más fluida, se despliega en cualquier sitio y separa el modelo (reutilizable como producto: la API es lo que compraría Embat) de la demo.

**Alternativas descartadas.** Streamlit: más rápido de montar, pero se re-ejecuta entero en cada interacción y queda acoplado a Python.

## D27 · Producto y comprador: capa de decisión de Embat para el CFO

*Categoría:* producto · *Estado:* a confirmar con la organización

**Pregunta.** ¿Quién paga y por qué?

**Decisión.** Comprador e integrador: Embat. Usuario: CFO o equipo de tesorería. X-Ray ordena la cartera, explica qué cambió y propone la siguiente acción con un colchón dinámico. Banco, bróker o BaaS quedan como ejecutores opcionales cuando la recomendación requiere capital o licencia.

**Por qué.** Embat ya ofrece previsión, alertas, riesgo y pagos. La aportación incremental de X-Ray es comparabilidad, explicación aditiva y priorización transversal: convertir el rastro que Embat ya tiene en una cola de decisiones, no duplicar el forecast.
