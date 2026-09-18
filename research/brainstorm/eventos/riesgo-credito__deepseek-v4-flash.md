<!-- modelo: deepseek-v4-flash vía Helmcode · lente: riesgo-credito · 60s · uso: None -->

# Eventos como "verdad" del score: lectura de un analista de riesgo pyme

> **Sin acceso a los datos** en esta sesión. Todas las frecuencias, coberturas y AUC son **estimaciones** razonadas a partir de los documentos adjuntos (`brief_eventos.md`, `context/challenge.md`, `context/scoring.md`, `features.md`, `targets.py`, `data_dictionary.md`). Las que el brief ya da medidas las cito como tales y las marco.

---

## 1. Posición

Un banco no llama “default” a la caja negativa, ni a que los cobros caigan un 50 %, ni a que la empresa se desconecte de Embat. Llama default a **90 días de mora material sobre una obligación propia (Art. 178 CRR)** o, si aún no hay mora, a **UTP (“unlikely to pay”)**: el banco juzga que no va a cobrar aunque el calendario no haya vencido. Traducido a este dataset —donde no observamos la cartera de préstamos del prestamista, sino la **tesorería del deudor**— el evento de crédito tiene que proxearse con **la mora de la empresa hacia terceros** (proveedores cobrados/pagados >90 días) y con **obligaciones recurrentes que la empresa deja de atender** (nómina, IVA trimestral, `debt_repayment`). De los cuatro candidatos que propone el brief, **solo AP vencido >90 días es fiable y de cobertura amplia**; la nómina es ruidosa, el IVA es trimestral y parcial, y `debt_repayment` cubre como mucho ~87 empresas (las que tienen cuadro de amortización). Por eso mi recomendación es **una jerarquía de tres niveles**: un ancla dura (“mora material / UTP persistente”), un nivel de **síntoma agregado (SICR/Stage 2)**, y eventos **positivos** (cura y sano sostenido). Los cuatro eventos actuales pasan a features o a producto colateral —nunca a “verdad” del score.

---

## 2. Veredicto sobre cada evento actual

| Evento actual | Veredicto | Motivo |
|---|---|---|
| **Apagado (3 %)** | **Separar como otro producto / señal de churn de Embat, no de crédito** | En el propio brief: mediana de 0,59 meses de caja en el último mes activo (frente a 0,48 de las activas), 22 % se va con >3 meses de caja, solo el 36 % mostró síntomas previos. Es un patrón de **desconexión de la plataforma**, no de cese. Como ancla del score contamina: 69 % de los apagados también cuentan como “declive”, así que el modelo aprende a predecir “deja de usar Embat”, que no es lo que pierde dinero a un prestamista. |
| **Saldo negativo (5 %)** | **Mantener, pero redefinir**: pasa a **estado de “tensión de caja”**, no a *default* | La caja negativa es *overdraft* o uso de línea: ni siquiera en banca se marca default por caja negativa; se marca **UTP** o **Stage 2**. Cuidado con la **circularidad ya medida**: los meses de caja predicen saldo negativo con AUC 0,77 “en parte de forma circular”. 46 % de las empresas que entran en negativo siguen 3+ meses —esto sí es señal—: **hay que exigir persistencia (≥3 meses) para eventificar**, no un mes aislado. |
| **Caída de cobros (17 %)** | **Degradar a feature / síntoma (SICR), nunca a outcome** | Tasa base 17 % es demasiado alta para ser “default”: incluye reversión a la media y estacionalidad. En banca esto es un **trigger de Stage 2 (SICR)**, no un evento de impago. El brief ya lo apunta (“pasa a ser feature”). Además su solapamiento con apagado (69 %) la convierte en una etiqueta ruidosa. |
| **Crecimiento (16 %)** | **Mantener como outcome positivo secundario, con filtros** | Bien como cara positiva (preguntas 1 y 2). Pero una tasa base del 16 % es sospechosamente alta: probablemente captura estacionalidad y crecimiento mecánico de la cohorte. **Añadir filtro anti-apalancamiento**: penalizar si la caja sube pero `lc_utilization` también o si entra `transfer_in`/`uncat_in` en lugar de `oper_in`. |

---

## 3. Eventos recomendados

> **Frecuencias estimadas** salvo las marcadas “(medido)” que vienen del brief. La cobertura de cada uno se deduce de los `sin dato` de `features.md`.

| # | Evento | Definición implementable | Tipo | Preguntas | Frecuencia (est.) | Riesgos |
|---|---|---|---|---|---|---|
| **1** | **Mora material >90 días (ANCLA)** | Por cada empresa-mes *m*: existen facturas **recibidas** (`invoices.document_type=invoice`, `amount<0`) con `pending_amount != 0`, `status != 'paid'` y `(fin_de_mes_m − due_date) > 90 días`, y la suma de esas facturas supera el **umbral de materialidad** (p. ej. 5 % de los pagos mensuales de la empresa, o 0,1 × gasto mensual medio). Complemento para empresas con `debt_schedule_config`: cuota vencida sin `debt_repayment` en `transactions` ese mes. | **Outcome duro (default proxy)** | 3, 5, 6 | **6-9 %** | Materialidad hay que calibrarla (1 % exp. o €500 es el estándar CRR; aquí no hay “exposición” explícita). Cobertura: ~58 % de filas con dato AP. Disputas comerciales normales pueden colarse si el umbral es bajo. |
| **2** | **UTP: tensión de caja sostenida** | `cash_end < 0` durante ≥3 meses consecutivos **o** `cash_end < 0,25 × gasto_mensual` durante ≥3 meses, **con** al menos uno de: `lc_drawn/lc_limit > 0,7`, `overdue_ap > 60d` creciente, o nueva deuda dispuesta con caja cayendo. | **Outcome blando (UTP)** | 3, 4, 6 | **4-6 %** | Solapa parcialmente con saldo negativo; hay que jerarquizar (UTP gana a “tensión” simple). Circularidad si se usa como input del score: **prohibido** usar `cash_end` en el score cuando se calibra contra este evento; sí se puede contra el evento 1. |
| **3** | **Obligación crítica omitida – nómina** | Para cada empresa con patrón `salary` establecido (≥3 meses, importe ±30 %, misma cadencia), si el mes siguiente no aparece ningún `salary` o cae >40 % sin reducción detectable (cambio en el nº de pagos únicos de nómina). | **Outcome duro condicional** | 3, 5, 6 | **6-10 %** (baja cobertura, alta precisión cuando aplica) | Muy ruidoso: 12 vs 14 pagas, bonus, bajas, pagos por varias cuentas. Necesita **detector de patrón**, no una regla rígida. Cobertura ~57 % (43 % sin dato de nómina). |
| **4** | **Obligación crítica omitida – IVA trimestral** | En meses fiscales esperados (ene/abr/jul/oct, o el patrón propio de la empresa), si el cargo `tax` esperado de importe ≥ mediana trimestral no aparece dentro de ±15 días. | **Outcome duro condicional** | 3, 5, 6 | **5-9 %** | Solo aplica a trimestrales (cobertura estimada 30-50 %). OOD con empresas nuevas sin histórico fiscal. El brief ya cita AUC 0,67 vs apagado (medido) —señal real pero no suficiente como ancla. |
| **5** | **Obligación crítica omitida – cuota de deuda** | Para las empresas con `debt_schedule_config`: cada `next_payment_date` debe tener un cargo `debt_repayment` correspondiente ±5 días; si falta, es mora directa y si persiste ≥3 meses → evento 1. | **Outcome duro** | 3, 5, 6 | **≈0,5-1 %** (muy baja cobertura) | Solo 87 de 2 239 productos. Como evento independiente casi no aporta; **sí** como refuerzo del evento 1 donde exista. |
| **6** | **Cura / recuperación** | La empresa sale de evento 1, 2 o 3 y se mantiene 3 meses sin reincidir, con `overdue_ar_90` + `overdue_ap_90` volviendo a su nivel previo y caja ≥1 mes de gasto. Estilo *forbearance exit* regulatorio (3 meses de prueba). | **Estado positivo** | 1, 2, 4, 6 | **3-5 %** | Una “cura” corta puede ser un bache. Requiere ventana de confirmación. |
| **7** | **Sano sostenido** | ≥12 meses sin eventos 1-4, `cash_months ≥ 2` y `margen_6m > 0`. | **Estado positivo** | 1, 4 | **15-25 %** | Sesgo hacia empresas grandes y con ERP. Usar como referencia de salud, no como score alto. |
| **8** | **Deterioro significativo (SICR / Stage 2)** | Catalizador: Δ negativo en ≥3 de {`overdue_ap_90`, `overdue_ar_90`, proxy DPO/DSO, `lc_utilization`, `cash_months_3m/12m`, `inflow_3m/inflow_12m`}. Estado, no evento. | **Síntoma agregado (no outcome)** | 2, 3, 6 | **10-15 %** | Riesgo de doble conteo con eventos 3-5. Es el que da el *early warning*; no debe usarse como etiqueta porque precede al outcome. |
| **9** | **Apagado (colateral)** | La empresa deja de tener movimientos definitivamente. Se mantiene **con otro propósito**: producto de retención Embat (riesgo de churn), no evento de crédito. | **Otro producto** | — | **3 %** (medido) | Ya analizado. |

**Ancla principal propuesta: evento 1 (mora material >90 días en AP o en cuota de deuda)**. Es el único que mapea directamente a la definición regulatoria de default y el que mejor separa “se le acaba el dinero” de “no paga a sus acreedores”.

---

## 4. Críticas a la propuesta actual del brief

1. **Mezcla outcome y síntoma en el mismo “incumplimiento”.** Juntar “nómina/IVA/cuota omitida” con “proveedores >90 días y creciendo” aúna dos economías muy distintas: la primera es **cesación de pago** (outcome), la segunda es **estrés de tesorería** (síntoma). Si se calibran juntos, el score aprende a detectar el síntoma, que es lo fácil, y pierde el outcome.
2. **“Proveedores >90 vencidos que crecen” no es un evento binario.** Es un *level + slope*: hay que fijar materialidad y qué significa “crecer”. Sin umbral, la etiqueta se contamina. Mejor: umbral duro de materialidad y dejar la pendiente como feature de explicación.
3. **Falta el evento de impago de la propia deuda (`debt_repayment`).** Es el único caso donde un banco sabe con certeza que la empresa no pagó *lo que tocaba*. Aunque su cobertura sea baja (≈87 empresas), debe formar parte del ancla y de la explicación.
4. **Se omiten cubos 30/60/90.** Los *early warning systems* bancarios trabajan por tramos de mora. Colapsar todo a binario pierde capacidad de anticipación y la posibilidad de medir la migración entre tramos (que es exactamente “bache frente a caída”).
5. **No hay umbral de materialidad ni de reincidencia.** Una factura de 80 € impagada no es default. Un mes aislado de caja negativa no es UTP. Sin materialidad y persistencia, las etiquetas se inflan y la calibración se rompe.
6. **“Entrada en tensión de caja” está mal tipada** en la propuesta (la llaman transición). Es un **estado** con puerta de entrada y de salida; conviene modelarlo como estado y no como evento puntual, igual que hace Basilea con *forbearance*.
7. **“Caída estructural vs bache” no es un evento, es una clasificación.** Debe derivarse de los eventos 1-3 con ventana de confirmación, no ser etiqueta.
8. **No hay criterio de cura explícito.** Regulatoriamente, una exposición sale de default tras 3 meses de comportamiento normal. Omitirlo infla la etiqueta y hace que “mejora” (pregunta 2 del reto) no tenga ancla.
9. **No se explota la dimensión de grupo.** El dataset tiene 250 grupos con 1-24 empresas; el default de una filial frecuentemente anticipa el del grupo. Hay que al menos usar el comportamiento del grupo como contexto y evitar contaminar train/test con filiales del mismo grupo.
10. **El propio brief prevé circularidad** en saldo negativo (“AUC 0,77, en parte de forma circular”). La propuesta no la resuelve: mezclar `cash_end` como input y como etiqueta vicia el score.

---

## 5. Cómo validar los eventos sin etiquetas

Sin ground truth, la estrategia debe ser doble: **estabilidad interna** y **consistencia con un relato de crédito**.

1. **Backtest tipo cartera sombra.** Para cada empresa-mes *m*, simular que un prestamista hipotético da 100 k€ con vencimiento a 6 meses. Calcular pérdida esperada = P(evento duro) × LGD asumida (usar 45 % estándar o generar según caja recuperada). Comparar con un *benchmark* aleatorio. Un evento útil debe separar PD en deciles de forma monótona.
2. **Rank-ordering por deciles.** Ya se hace con features: aplicar el mismo test a los eventos. Si la tasa de evento no decrece monótonamente por deciles de un score preliminar, la etiqueta es ruidosa.
3. **Coherencia entre eventos.** Matriz de correlación entre eventos. Si el nuevo “mora material” correlaciona >0,8 con “caída de cobros”, uno de los dos sobra. Espero correlación **baja** entre mora material (AP) y caída de cobros (entradas), y **alta** entre mora material y UTP persistente (que es lo deseable: una cadena causal).
4. **Estabilidad temporal.** Frecuencia por mes de cada evento a lo largo de los 24 meses. Un evento útil no debería tener frecuencia 5× mayor en los últimos 3 meses (eso sería artefacto de reconstrucción o de onboarding).
5. **Placebo / permutación.** Barajar `company_id` manteniendo la estructura temporal y recalcular. La AUC de un score preliminar debe caer a ~0,50.
6. **Revisión manual de 20 casos por evento.** Leer las `description` de `transactions` e `invoices.concept` para comprobar que el evento captura lo que dice capturar (no una transferencia interna, no una factura dudosa, no un mes truncado).
7. **Tasas de cura.** Si >50 % de los eventos de “mora material” se curan en 6 meses, el umbral es demasiado laxo. Si <10 % se curan, probablemente estás capturando el final del ciclo. Objetivo razonable: 25-40 % de cura.
8. **Sensibilidad al umbral.** Barrer materialidad (1 %, 3 %, 5 %, 10 % de pagos mensuales) y persistencia (1, 2, 3 meses). Reportar la tasa de evento resultante. Elegir el umbral donde la sensibilidad se aplana (meseta), no donde el evento es más frecuente.
9. **Lead time del EWS.** Para cada outcome, medir cuántos meses antes se disparan los síntomas (DPO stretch, `lc_utilization` alta, `cash_months` cayendo). Esa métrica responde directamente a la pregunta 6 del reto y es la que el jurado premia con bonus.
10. **Contraste contra la reconstrucción de `balances`.** Donde exista `balances` final consistente, comprobar que las marcas de mora material no aparecen justo donde el saldo reconstruido es implausible (filtra artefactos).

---

## 6. Preguntas para la organización

1. **¿`debt_schedule_config.next_payment_date` y `last_payment_date` están actualizados?** Si `last_payment_date` es muy anterior a `next_payment_date`, ¿podemos usarlo como indicio de mora real? Sería el proxy de default más limpio del dataset.
2. **¿La categoría `tax` distingue trimestral de mensual?** ¿Se puede separar IVA de otros impuestos por `description`/`concept`?
3. **¿`salary` se paga en 12 o 14 pagas?** ¿Hay forma de identificar la fecha esperada por patrón de pagos?
4. **¿Existen eventos de insolvencia / concurso / cese en algún fichero auxiliar** (aunque sea como metadato de generación)? Sin ellos, `churn` seguirá siendo ambiguo.
5. **¿Grupos comparten cuentas bancarias o hay contrapartes intragrupo que distorsionan los flujos?** ¿Cuál es la regla de oro para tratar transferencias intragrupo?
6. **¿Embat tiene visibilidad de impagos fuera de las cuentas conectadas** (por ejemplo, del propio `debt_products` con estado de mora)? ¿Se puede usar `outstanding` en algún punto sin fuga?
7. **¿Cuántas de las 87 empresas con `debt_schedule_config` son clientes de alto volumen** y por tanto candidatas a un scoring más preciso?
8. **¿El test oculto viene con `debt_schedule_config`** o podría no tener nada de deuda? Condiciona si el evento 5 puede ser ancla o solo refuerzo.
9. **¿La definición “oficial” de Embat de ‘empresa sana’** es “no quiebra a 12 meses” o algo más laxo? Cambia el horizonte y la etiqueta.
10. **¿Se admite un evento a nivel grupo?** Regulatoriamente sí, y probablemente mejora el AUC si hay contagio intragrupo.

---

## 7. Verificaciones hechas

**No tengo acceso a los datos en esta sesión.** Todas las cifras que aparecen marcadas “(est.)” son estimaciones razonadas a partir de:

- Tasas ya medidas y citadas en el brief: apagado 3 %, saldo negativo 5 %, caída de cobros 17 %, crecimiento 16 %, solapamiento apagado-declive 69 %, 46 % de negativos persisten >3 meses, 22 % de apagados se va con >3 meses de caja, AUC 0,77 de `cash_months` frente a saldo negativo, AUC 0,67 de IVA omitido frente a apagado (medidos).
- Coberturas conocidas de `features.md`: 42 % sin dato AP, 44 % sin pagos tardíos a proveedores, 43 % sin pesode nóminas, 86 % sin uso de pólizas, 53 % sin cobros tardíos.
- Recuentos del `data_dictionary.md`: 87 filas en `debt_schedule_config` sobre 2 239 en `debt_products`.

**Verificaciones que habría corrido en 30 minutos con los parquet** y que recomiendo priorizar antes de congelar las etiquetas:

1. `invoices` filtrado por `pending_amount != 0 AND status != 'paid' AND (today − due_date) > 90`: tasa empresames y cobertura por `has_erp`.
2. `transactions.category == 'salary'`: por empresa, medir cadencia y CV del importe; cuantificar cuántas empresas tienen un patrón estable vs cuántas son irregulares.
3. `tax` en meses fiscales: cuántas empresas realmente tienen cargo `tax` en ene/abr/jul/oct, y cuántas faltan.
4. `debt_repayment` por empresa con schedule: qué porcentaje de `next_payment_date` tiene un cargo correspondiente.
5. Matriz de correlación entre los cuatro eventos actuales + los nuevos propuestos (el brief ya da pistas: “saldo negativo casi independiente del resto”).
6. Curva de sensibilidad de la mora material al umbral de materialidad (1/3/5/10 %) para ver dónde se aplana.

Marcaría como **pendientes de verificar** los eventos 2 (UTP sostenida), 3 (nómina) y 4 (IVA) hasta confirmar cobertura y precisión sobre los parquet.