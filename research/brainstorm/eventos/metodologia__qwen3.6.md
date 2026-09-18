<!-- modelo: qwen3.6 vía Helmcode · lente: metodologia · 63s · uso: None -->



### 1. Posición
El sistema actual sufre de **circularidad estructural**: se calibra y valida contra variables (`cash_end`, `in6`, `in12`, `months_since_final_tx`) que son la materia prima exacta de las features. Eso infla artificialmente el AUC y enmascara la falta de señal predictiva real. Los eventos binarios fijos a 6 meses pierden la dimensión temporal y son inestables para tasas bajas (~3 %). La dirección correcta es pasar a un marco de **supervivencia / aprendizaje con etiquetas débiles**, donde la quema de caja sea la ancla, los retardos y la estructura de pagos actúen como transiciones, y la validación se haga con consistencia económica y robustez temporal, no con AUC sobre las mismas columnas.

### 2. Veredicto sobre cada evento actual
| Evento actual | Veredicto | Motivo |
|---|---|---|
| **Apagado** | **Redefinir → Variable de supervivencia (time-to-event)** | El 3 % de frecuencia es insuficiente para una logística plana; se solapa mecánicamente un 69 % con caída de cobros. Debe tratarse como censor/censurado (Cox o AFT) y separarse como baja de plataforma vs cierre real. |
| **Saldo negativo** | **Degradar a feature principal + mantener como validación de estrés** | AUC 0,77 es circular por usar `cash_end`. Debe medirse con caja *reconstruida intramensual* o flujo neto proyectado, no con stock final. Es la señal de criticidad máxima, no un objetivo binario independiente. |
| **Caída de cobros** | **Degradar a feature (síntoma) y eliminar como objetivo** | Reversión a la media y solapamiento con el apagado. Ya está capturado en `in6/in12` y `tendencia de cobros`. No aporta información marginal para la calibración. |
| **Crecimiento** | **Mantener pero redefinir a horizonte extendido** | Útil para la pregunta 2 del reto, pero necesita ≥2 trimestres consecutivos para filtrar picos estacionales. Funciona como validación de estado positivo, no como ancla. |

### 3. Eventos recomendados
**Ancla principal:** `Quema acelerada de caja (Transición a tensión operativa)`. Combina velocidad de evaporación de efectivo y falta de cobertura de deuda/pagos fijos.

| Nombre | Definición implementable (columnas) | Tipo | Preguntas del reto | Frecuencia estimada | Riesgos |
|---|---|---|---|---|---|
| Quema acelerada de caja | `cash_end` intramensual < 30 días en los próximos 3 m, tras ≥3 m con `cash_end` ≥ 60 días. Cálculo: `(cash_end / oper_outflow_3m) < 1` (promedio mensual). | Transición | 3, 4, 6 | ~8–10 % (est.) | Estacionalidad de impuestos trimestrales; falsos positivos en meses de vencimientos masivos. |
| Ruptura de ciclo de tesorería | `DSO_3m` > `DPO_3m` sostenido + `debt_outstanding_6m` crece >10 % sin reducción de `cash_end`. Filtro: `invoices` + `debt_products`. | Transición / Estado | 3, 5 | ~12 % (est.) | 36 % sin ERP (DSO/DPO proxy por `transactions.category`). Sensible a monedas débiles si no se normaliza. |
| Pérdida de base de cobros | >20 % de los `counterparty_id` activos en `invoices.issuance_date` [-12m, 0] no aparecen en los próximos 6 m. | Síntoma | 3, 4 | ~15 % (est.) | Estacionalidad comercial; empresas con ciclo de ventas largo (<12 m). |
| Sano sostenido | 0 eventos de estrés y `cash_end` media 3 m > 2× `oper_outflow_3m` en los próximos 12 m. | Estado positivo | 1, 2 | ~25 % (est.) | Conservador; sesga a empresas grandes y con ERP. |
| Baja operativa / Apagado | >60 días sin transacciones con `category ∈ {collection, payment, bulk_collection, bulk_payment, salary}`. | Resultado | 4, 6 | ~3 % (est.) | Confusión con desconexión de Embat; uso de `transactions.category` y `accounting_status`. |

### 4. Críticas a la propuesta actual
1. **Circularidad features ↔ events:** Las 17 features y los 4 eventos se construyen sobre los mismos agregados (`cash_end`, `in6`, `in12`, `inflow`). El modelo aprende a predecir su propia entrada; el AUC refleja fidelidad de reconstrucción, no capacidad predictiva fuera de distribución.
2. **Horizonte fijo vs. anticipación:** Un label binario a 6 m trata igual un evento en el mes 2 que en el mes 10. Esto castiga la pregunta 6 ("¿cuándo se vio venir?") y obliga a usar umbralización cruda en lugar de densidades de riesgo.
3. **Combinación de eventos por media aritmética:** Promediar AUCs de logísticas ignora que los eventos no son mutuamente excluyentes ni de igual coste financiero. El deterioro por quema de caja tiene externalidad mayor que la caída de cobros aislada. La media diluye la criticidad.
4. **Falta de distinción transición/estado:** Las features actuales son niveles o tendencias suaves. No capturan el *punto de inflexión* (bache vs caída) que es el núcleo del producto. Sin umbrales de régimen o modelos de cambio de punto, el score oscila innecesariamente.
5. **Validación sin holdout temporal estricto:** Usar el mismo panel para calibrar y validar genera optimismo sobre el test oculto. El 31 % de empresas tiene <12 m de historia; si no se stratifica por antigüedad y moneda, la señal colapsa en OOD.

### 5. Cómo validarías los eventos sin etiquetas
- **Crossover temporal (Out-of-Time):** Entrenar en `T-12:T`, validar en `T+1:T+6`. Medir PR-AUC y F2-score, no solo AUC-ROC. Si la curva de ganancia acumulada (lift) no supera 1.5x en el top decil, el proxy no aporta valor económico.
- **Modelos de supervivencia (Cox / Random Survival Forests):** Validar que las features predicen *tiempo hasta* el evento (concordancia C-index > 0.65 como umbral mínimo). Esto reemplaza el horizonte fijo y mide directamente la anticipación.
- **Etiquetas débiles (Weak Supervision / PU Learning):** Construir reglas económicas independientes (ej. “si quema >20 % de caja/mes en 2 m consecutivos y no hay refinanciación, P(estrés) ≈ 0.8”). Usar MAD, Snorkel o Positive-Unlabeled con noise matrix para calibrar el score sin labels verdaderas.
- **Validación por estabilidad de régimen:** Particionar en “bache” vs “caída” mediante cambio de punto (Pelt, BinSeg) en la trayectoria de caja. Si el score no separa ambos grupos con >15 pp de mediana, el modelo no distingue ruido de deterioro.
- **Robustez OOD controlada:** Validar en subcolectos no vistos en entrenamiento: empresas sin ERP, monedas no EUR/USD, antigüedad <12 m. Usar covariate shift correction (importance weighting) si la distribución de features cambia.
- **Prueba de invarianza causal:** Perturbar aleatoriamente el 20 % de una feature (ej. DSO) y verificar que el score no se mueve artificialmente. Si el efecto es >2 pp, hay dependencia espuria (ej. estacionalidad trimestral confundida con riesgo).

### 6. Preguntas para la organización
1. ¿El “apagado” refleja cierre real de la empresa o desconexión de la plataforma Embat? ¿Tenemos alguna señal externa o de grupo para distinguirlas?
2. ¿Se permiten modelos de supervivencia o scoring continuo (densidad de riesgo) para el leaderboard, o se exige estrictamente un número mensual 0–100?
3. ¿Cuál es la distribución de antigüedad y presencia de ERP en el test oculto? ¿Hay empresas que nacen dentro de los 24 m?
4. ¿Qué umbral de anticipación (meses) se considera viable para el producto que se venderá a bancos/empresas? ¿1 mes, 3 meses, 6?
5. ¿Se permite usar datos macro (PMI sectorial, tipos de interés) para ajustar estacionalidad y validar robustez, o solo los 9 ficheros del dataset?

### 7. Verificaciones hechas
No tengo acceso directo a los datos ni ejecuto scripts. Todas las cifras y solapamientos son **estimaciones** derivadas del brief y de la estructura del dataset:
- Estimo que el solapamiento apagado ↔ caída de cobros (~69 %) puede reducirse a ~30–40 % si se filtra por transacciones operativas reales (excluyendo `category = '-'`, `transfer` y `cash_settlements`).
- Estimo que un horizonte de supervivencia de 3–4 meses captura ~70 % de las transiciones reales, dado que los impuestos son trimestrales y los ciclos de tesorería pymes suelen cerrar en un trimestre.
- Estimo que la frecuencia de “Quema acelerada” (~8–10 %) es plausible si se usa caja mínima intramensual y no solo saldo a fin de mes.
- Confirmo que la circularidad es crítica: `cash_end`, `in6`, `in12` y `inflow` aparecen tanto en la construcción de features como en la definición de targets, lo que invalida el AUC actual como medida de generalización.