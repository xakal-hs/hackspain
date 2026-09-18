<!-- modelo: deepseek-v4-flash vía Helmcode · 83s · uso: None -->

# Features nuevas para el score X-Ray (reto Embat, HackSpain 2026)

**Nota de método.** No he podido ejecutar código contra `research/data/*.parquet` desde este entorno; por eso **todas las casillas de evidencia figuran como "no comprobada"**. Las fórmulas usan exactamente columnas del diccionario y del panel descrito (`panel.parquet`, `transactions`, `invoices`, `debt_products`, `debt_schedule_config`, `banking_products`, `groups`, `balances`). Las ventanas son causales (`≤ fin del mes m`). Donde digo "moneda empresa" aplico `to_eur` o `exchange_rate` validado al tipo real, como ya hace `panel.py`.

---

## Bloque A — Anticipación de caja (lo que se mueve antes que el saldo)

### 1. `cash_burn_velocity_3m` — velocidad de drenaje de caja
1. **Nombre y pregunta**: Velocidad de drenaje de caja. Responde a 3 (quién empieza a torcerse) y 4 (bache vs caída).
2. **Definición**: `panel.cash_end`, `panel.outflow`. Sea `gasto_hab = max(media móvil 3m de outflow, media móvil 12m de outflow)`. `burn = (cash_end[m-3] − cash_end[m]) / (3 · gasto_hab)`. Filtro: descartar filas con `|cash_end| > 1e10` (los saldos ±1e13) y exigir `months_since_first_tx ≥ 3`.
3. **Hipótesis**: "si prestaras 100.000 €, no te asusta lo que tiene hoy en la cuenta, sino a qué velocidad se está vaciando la hucha".
4. **Dirección**: más es mejor (positivo = acumula, negativo = quema). Cero = neutro, no "no aplica".
5. **Cobertura**: ~99 %; riesgos: saldo reconstruido con outliers extremos (hay que invertir con criterio robusto) y primer mes parcial.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste bajo (ya está `cash_end` en el panel).

### 2. `dso_implicit_3m` y `dso_trend` — antigüedad real de cobro
1. **Nombre y pregunta**: DSO implícito y su tendencia. Responde a 3 y 5 (qué señal se movió y cuándo).
2. **Definición**: `invoices` con `document_type='invoice'`, `amount>0` (AR), `status='paid'`, `pending_amount=0`, `payment_date ≤ fin de m`, `payment_date ≥ issuance_date` y `year(payment_date) < 2100` (filtro de fechas imposibles). `dso_3m = mediana(payment_date − issuance_date)` para facturas pagadas en `(m−3, m]`. `dso_trend = dso_3m − dso_12m`. Análogo en EUR (`amount/exchange_rate`).
3. **Hipótesis**: el cliente medio empieza a estirar el pago semanas antes de que el banco vea caer los ingresos; es la primera señal del deterioro del circulante.
4. **Dirección**: menor es mejor; `dso_trend` positivo = peor. Cero = "no aplica" (sin facturas pagadas en la ventana).
5. **Cobertura**: máx. 61 % (solo 785/1286 empresas tienen ERP), y dentro de ese subconjunto algo menos por la ventana. Riesgos: `payment_date == due_date` en overdue (hay que ignorar impagadas), fechas 7025, sensibilidad a pocas facturas.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste medio.

### 3. `dpo_implicit_3m` y `dpo_widening` — estiramiento del pago a proveedores
1. **Nombre y pregunta**: DPO implícito y su ensanchamiento. Responde a 3 y 5.
2. **Definición**: `invoices` con `document_type='invoice'`, `amount<0` (AP), `status='paid'`, `payment_date ≤ fin de m` y coherencia de fechas. `dpo_3m = mediana(payment_date − issuance_date)` de pagos en `(m−3, m]`; `dpo_widening = dpo_3m − dpo_12m`.
3. **Hipótesis**: cuando una empresa se queda sin efectivo, deja de pagar a proveedores antes de dejar de pagar a Hacienda o a la nómina; ese ensanchamiento del DPO precede al impago.
4. **Dirección**: menor es mejor; `dpo_widening` positivo = peor. Cero = "no aplica".
5. **Cobertura**: ~45-50 %. Riesgos: mismo conjunto de fechas sucias; no capta a quien ya no paga (esas facturas son `overdue` y hay que mirar `overdue_ap`, ya existente).
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste medio.

### 4. `salary_punctuality_coverage` — nóminas pagadas y a tiempo
1. **Nombre y pregunta**: cobertura y puntualidad de la nómina. Responde a 3, 5 y 6 (con cuánta antelación se ve).
2. **Definición**: `transactions` con `category='salary'`, agrupadas por mes. `cobertura = sum(salary[m]) / mediana(sum(salary) en 6 meses previos)`. `puntualidad = día-del-mes del último pago de nómina (m) − mediana del día de pago en 6 meses previos`. Alternativa robusta: `flag_impago = 1` si `cobertura < 0.7` o no hay nómina en m cuando sí la había en ≥4 de los 6 meses previos.
3. **Hipótesis**: "si le prestaras a una persona y deja de cobrar el sueldo puntual o se le corta, ya no te fías; en la pyme la nómina es el pago menos discrecional".
4. **Dirección**: `cobertura≈1` y `puntualidad≈0` = sano; caída de cobertura o retraso = peor. Cero/no aplica si no hay nómina en 12 meses.
5. **Cobertura**: ~43 % (empresas con nómina). Riesgos: mayo-agosto y diciembre suelen tener extras/atípicos; conviene usar mediana, no media.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste bajo.

### 5. `tax_exposure_next_quarter` — colchón frente a la próxima cuota de impuestos
1. **Nombre y pregunta**: exposición al pago trimestral de impuestos. Responde a 3 (torcedura temprana) y 4.
2. **Definición**: `transactions.category='tax'` y `panel.tax`. Sea `tax_norm = mediana(sum(tax) de los 4 trimestres fiscales previos)`. `exposure = tax_norm / max(cash_end[m], ε)`. Si m es el mes previo a un trimestre fiscal (dic, mar, jun, sep → siguiente enero/abril/julio/oct), multiplicar por un flag de proximidad.
3. **Hipótesis**: el IVA trimestral es la obligación más rígida y más predecible; saber si la empresa cubre la próxima cuota con la caja actual anticipa el bache unos días.
4. **Dirección**: menor es mejor. Cero = "no aplica" si no hay histórico de `tax`.
5. **Cobertura**: ~40 %. Riesgos: `tax` incluye IBI, tasas locales y otras; conviene excluir ayuntamientos si el texto lo permite.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

---

## Bloque B — Deuda, líneas y financiación forzada

### 6. `new_debt_while_cash_falls` — deuda nueva tapando el agujero
1. **Nombre y pregunta**: nueva deuda con caja cayendo. Responde a 3 y 4.
2. **Definición**: `debt_products.created_at` en `(m−3, m]`; `granted_new = sum(granted)` (en valor absoluto). `ratio_nueva_deuda = granted_new / max(oper_in_3m, ε)`. Señal compuesta: `s = ratio_nueva_deuda · max(0, −Δcash_3m / gasto_hab)`. Alternativa binaria: 1 si en la ventana hay nueva deuda y `Δcash_3m < 0`.
3. **Hipótesis**: "si alguien pide un préstamo para tapar el descubierto en vez de para invertir, te está diciendo que su caja se ha roto".
4. **Dirección**: más es peor. Cero = no aplica (sin nueva deuda).
5. **Cobertura**: ~100 % del flag, ~20-30 % con valor positivo en algún mes. Riesgos: `granted` puede venir en negativo (ver `GUARANTEE` en el perfil) → usar `abs()`.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste bajo.

### 7. `lc_drawdown_velocity_3m` — velocidad de uso de las pólizas
1. **Nombre y pregunta**: velocidad de disposición de líneas de crédito. Responde a 3 y 5.
2. **Definición**: `panel.lc_drawn` y `panel.lc_limit`. `uso(m) = lc_drawn / max(lc_limit, ε)`; `vel = uso(m) − uso(m−3)`. Alternativa: pendiente de `uso` en 6 meses.
3. **Hipótesis**: "si vive al límite de la tarjeta, lo primero que notas no es el saldo, sino lo rápido que sube el disponible consumido".
4. **Dirección**: más es peor. Cero/no aplica si no hay póliza.
5. **Cobertura**: ~14 % (86 % sin dato). Riesgo: cambio de límite por renovación puede dar saltos espurios → normalizar por límite en m y m−3 con `min`.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media-alta (por cobertura baja). Coste bajo.

### 8. `new_factoring_confirming` — aparición de factoraje o confirming
1. **Nombre y pregunta**: financiación forzada del circulante. Responde a 3, 5 y 6.
2. **Definición**: `debt_products` con `type IN ('factoring','confirming')` y `created_at` en `(m−3, m]`. Feature = 1 si aparece al menos una, 0 en caso contrario; versión continua: `abs(granted) / oper_in_3m`.
3. **Hipótesis**: descontar facturas o meter un confirming es lo que hace una pyme cuando necesita cobrar YA; aparece semanas antes del impago.
4. **Dirección**: 1 = peor. Cero = no aplica (la mayoría).
5. **Cobertura**: ~100 % del flag, ~2-4 % con valor 1 (según perfil: 24 factorings + 229 confirmings). Riesgos: puede ser una política financiera estable → distinguir "nuevo" de "ya existía".
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste bajo. Muy explicable.

### 9. `interest_burden_trend` — coste financiero creciente
1. **Nombre y pregunta**: peso y tendencia del coste financiero. Responde a 3 y 5.
2. **Definición**: `transactions.category='interest_charge'`. `ib_3m = sum(interest_charge en 3m) / max(oper_in_3m, ε)`; `trend = ib_3m − ib_12m`. Moneda empresa.
3. **Hipótesis**: más intereses sobre los mismos cobros significa más deuda y peor tipo; es la factura que precede a la asfixia.
4. **Dirección**: más es peor. Cero = no aplica (sin intereses).
5. **Cobertura**: alta (todas las que tienen deuda; ~30-40 % con valor >0 en algún mes). Riesgo: confundir una ampliación con un deterioro → usar tendencia, no nivel.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

### 10. `next_installment_coverage` — cobertura de la próxima cuota
1. **Nombre y pregunta**: caja vs próxima cuota de préstamo/leasing. Responde a 3 y 5.
2. **Definición**: `debt_schedule_config.next_payment_date` dentro de los 60 días siguientes al fin de m. Cuota estimada = `outstanding_balance / max(total_periods − pagos_realizados, 1)` o separar `debt_repayment` recurrente del histórico de `transactions`. `coverage = (cash_end + lc_limit − lc_drawn) / max(cuota, ε)`.
3. **Hipótesis**: saber si la próxima letra cabe en la caja con la póliza disponible es la pregunta más literal que se hace un prestamista.
4. **Dirección**: más es mejor. Cero = no aplica.
5. **Cobertura**: baja (~7 % de empresas tienen schedule). Riesgos: solo 87 productos, `next_payment_date` puede estar vencido por extracción.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media-baja por cobertura, alta por explicabilidad. Coste medio.

---

## Bloque C — Contrapartes, proveedores y texto

### 11. `net_customer_gain_3m` — captación neta de clientes
1. **Nombre y pregunta**: captación neta de clientes. Responde a 1 (quién está sano) y 2 (quién mejora).
2. **Definición**: `invoices` con `amount>0`, `counterparty_id` no nulo. `nuevos = |distinct counterparty_id con primera emisión en (m−3, m]|`; `perdidos = |distinct counterparty_id con emisión en (m−12, m−3] y ninguna en (m−3, m]|`. `net = (nuevos − perdidos) / max(n_cust_3m, 1)`.
3. **Hipótesis**: la cara positiva del score es la cartera viva; si gana clientes netos, la próxima caída de caja probablemente sea coyuntura, no estructura.
4. **Dirección**: más es mejor. Cero = neutro; "no aplica" si no hay histórico.
5. **Cobertura**: ~50 % (necesita ERP). Riesgos: factura única de un cliente ocasional infla "nuevos"; exigir `nuevos` con importe mínimo > 0 y contarlo con `amount`.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste medio. Complementa "clientes perdidos" ya existente.

### 12. `supplier_base_churn` — churn de proveedores
1. **Nombre y pregunta**: churn de proveedores. Responde a 3 y 4 (bache, si el giro es de aprovisionamiento).
2. **Definición**: `invoices` con `amount<0`, `counterparty_id` no nulo. `ratio_prov = n_prov_3m / max(n_prov_12m / 4, 1)`. Alternativa: número de proveedores activos vs los 12 meses previos.
3. **Hipótesis**: una pyme sana renueva y mantiene su base de proveedores; si se le caen sin sustitución, o pierde actividad, o ya no le fían.
4. **Dirección**: más es mejor. Cero = "no aplica".
5. **Cobertura**: ~50 %. Riesgo: puede caer legítimamente por cambio de proveedor; complementar con `new_supplier_share`.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste medio.

### 13. `distress_text_marker_3m` — marcadores de refinanciación/impago en descripciones
1. **Nombre y pregunta**: marcadores de tensión en texto libre. Responde a 5 (qué señal se movió).
2. **Definición**: `transactions.description` (y opcionalmente `invoices.concept`). Regex case-insensitive sobre los últimos 3 meses: `refinanc|aplaz|prorrog|acuerdo de pago|fraccionamiento|impag|devoluci[oó]n|rebot|suspend|reclamac|mora|comisi[oó]n de descubierto|denegad|unpaid`. `flag = 1` si hay ≥1 match; versión continua: `matches / n_tx_3m`.
3. **Hipótesis**: "el rastro que el banco no ve" incluye el lenguaje operativo; una palabra como "APLAZAMIENTO" en la descripción llega antes que un saldo negativo.
4. **Dirección**: más es peor. Cero = no aplica (habitual).
5. **Cobertura**: 100 % (todas tienen `description`). Riesgos: falsos positivos con `refund`/`devolución` operativos; calibrar contra muestra manual. OOD: idiomas mixtos.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media-alta. Coste medio (regex + control de idioma).

### 14. `hhi_ap_6m_text` — concentración de pagos por contraparte (parseada del texto)
1. **Nombre y pregunta**: concentración de proveedores / dependencia. Responde a 1 y 3.
2. **Definición**: `transactions` con `amount<0`, `category NOT IN ('transfer')` y agrupación por contraparte derivada con `COALESCE(counterparty_id, regexp_extract(description, 'COUNTERPARTY_(\\d+)'), regexp_extract(description, '\\[COMPANY\\]'))`. `HHI = Σ (pago_i / total_pagos)^2` en ventana de 6 meses.
3. **Hipótesis**: si el 60 % del pago va a un solo proveedor, un corte de suministro le rompe la operativa; simétrico al HHI de AR ya existente, pero por el lado del gasto.
4. **Dirección**: más es peor. Cero → "no aplica" si el parsing no resuelve contrapartes.
5. **Cobertura**: 60-70 % con parsing (frente al 10 % de `counterparty_id` no nulo). Riesgos: `COUNTERPARTY_\d+` está solo en una parte del texto; el resto necesita lista de tokens `[COMPANY]`/`[PERSON]` para no agrupar nombres de personas con empresas.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste medio.

### 15. `key_supplier_payment_gap` — días sin pagar al proveedor principal
1. **Nombre y pregunta**: gap con proveedores clave. Responde a 3, 5 y 6.
2. **Definición**: top-5 contrapartes por importe pagado (outflow) en 12 meses, con contraparte derivada como en la feature 14. Para cada una, `días_desde_último_pago(m)`; `gap_rel = días_desde_último_pago / max(mediana de gaps históricos, 1)`. Feature = máximo de `gap_rel` sobre los top-5, con la restricción de haber registrado ≥4 pagos en 12m (para no castigar a quien paga trimestral).
3. **Hipótesis**: dejar de pagar al proveedor principal es una señal muy anterior al impago formal, y muy explicable: "llevas 90 días sin pagar al que te trae la materia prima".
4. **Dirección**: más es peor. Cero = no aplica.
5. **Cobertura**: 60-70 % con parsing; menor si la empresa tiene pocos proveedores recurrentes. Riesgos: cerrar un contrato cambia de proveedor y sube el gap; exigir históricos ≥4 pagos mitiga el falso positivo.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste medio.

---

## Bloque D — Diversificación y calidad del negocio

### 16. `inflow_source_entropy_3m` — diversificación de fuentes de cobro
1. **Nombre y pregunta**: diversificación de fuentes de entrada. Responde a 1 y 3.
2. **Definición**: `transactions` entrada (`amount>0`), categorías operativas (`collection`, `bulk_collection`, `pos_settlement`, `cash_settlement(s)`, `investment_return`, `tax_refund`). `p_i = importe_cat_i / total`. `H = −Σ p_i log p_i` normalizada por `log(n_cat)`, ventana 3 meses.
3. **Hipótesis**: quien cobra por varias vías (transferencia, TPV, remesa) tiene un flujo menos frágil; quien depende de una sola vía cae entera con ella.
4. **Dirección**: más es mejor. Cero = "no aplica" (una sola categoría).
5. **Cobertura**: ~100 % si filtramos categorías operativas. Riesgo: el 25 % de las filas y el 45 % del importe de entradas está categorizado como `-`; excluirlo puede sesgar → conviene un falso "unknown" en la entropía.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

### 17. `intragroup_dependency_3m` — dependencia de la matriz / hermanas
1. **Nombre y pregunta**: financiación intragrupo. Responde a 3 y 5.
2. **Definición**: `transactions` más `groups.group_id`. Emparejar movimientos mismo día, mismo `abs(amount)`, signo opuesto, entre dos empresas con el mismo `group_id` y productos distintos. `intragroup_in_3m / max(inflow_3m, ε)`.
3. **Hipótesis**: cuando una pyme empieza a vivir de la caja de la matriz, su salud ya no es propia; el banco presta a algo que en realidad depende de un tercero.
4. **Dirección**: más es peor. Cero = no aplica (empresas sin hermanas).
5. **Cobertura**: ~70-80 % (250 grupos con 1-24 empresas). Riesgo: solapamiento con el `transfer_in / oper_in` ya existente; esta lo restringe a intragrupo, que es la parte realmente informativa.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta. Coste medio.

### 18. `reconciliation_coverage_3m` — calidad de conciliación (contexto, no salud)
1. **Nombre y pregunta**: disciplina de conciliación. Responde a 1 (sano = ordenado) pero sobre todo a la confianza del score.
2. **Definición**: `transactions.accounting_status` no nulo. `share = |status ∈ {RECONCILIATION_COMPLETED, ACCOUNTING_COMPLETED}| / |no nulos|`, ventana 3 meses. Alternativa: share de `DISCARDED` (bandera de ruido).
3. **Hipótesis**: quien concilia con disciplina sabe dónde está su caja; quien tiene un 40 % de `PENDING` no. Es la traducción "enseñar las cuentas".
4. **Dirección**: alto = mejor. `null` = "no aplica" (no confundir con mal dato).
5. **Cobertura**: 38 % (62 % de `accounting_status` nulos). Regla de `scoring.md`: **tratar como confianza, no como salud**; se puede usar como multiplicador de la confianza del score y como gauge del dashboard.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media-baja como feature, alta como contexto. Coste bajo.

### 19. `bank_account_fragmentation` — fragmentación bancaria
1. **Nombre y pregunta**: número de cuentas/bancos y su novedad. Responde a 3 (torcedura temprana) y a cobertura.
2. **Definición**: `banking_products` con `created_at ≤ fin de m`. `frag = n_products_3m / max(n_products_12m, ε)` y `nuevos_3m = |created_at en (m−3, m]|`. Número de `bank_name` distintos.
3. **Hipótesis**: abrir varias cuentas nuevas cuando la caja aprieta suele indicar que el banco principal está cortando el grifo; por el lado positivo, incorporar una cuenta nueva puede indicar crecimiento.
4. **Dirección**: **ambigua** — por eso se combina con `Δcash_3m`: nuevos bancos + caja cayendo = malo; nuevos bancos + caja subiendo = bueno.
5. **Cobertura**: ~100 % (todas las empresas tienen productos). Riesgo: `created_at` es la conexión a la plataforma, no la apertura real → puede reflejar onboarding, no decisión financiera. Marcar como "contexto".
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: baja. Coste bajo.

---

## Bloque E — Dinámica temporal: bache vs caída

### 20. `net_flow_bounce_back` — rebote tras el peor mes
1. **Nombre y pregunta**: bache vs caída. Responde a 4.
2. **Definición**: `panel`, `net = inflow − outflow`. `peor = min(net[m−5..m−2])`, `recuperacion = media(net[m−1..m])`, `bounce = recuperacion / max(|peor|, ε)`.
3. **Hipótesis**: "un mal mes con recuperación es un gasto puntual; un mal mes que no rebota es que el negocio ha cambiado".
4. **Dirección**: más es mejor. Cero = neutro.
5. **Cobertura**: 100 %. Riesgo: confundir flujos internos con operativos → usar `inflow − outflow` ya limpios (sin internas ni intragrupo), como hace el panel.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: alta (ataca directamente el AUC 0,50 actual). Coste bajo.

### 21. `volatility_persistence_3_12` — persistencia de volatilidad
1. **Nombre y pregunta**: si el shock es reciente y no se ha disipado. Responde a 4.
2. **Definición**: `ratio = std(net_flow últimos 3m) / max(std(net_flow últimos 12m), ε)`.
3. **Hipótesis**: un pico puntual sube la volatilidad corta y luego se diluye; un régimen roto mantiene `ratio ≫ 1` de forma persistente.
4. **Dirección**: más es peor. Cero = "no aplica" (histórico insuficiente).
5. **Cobertura**: 100 %. Riesgo: empresas con actividad muy estacional muestran `ratio` alto cada año.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

### 22. `deseasonalized_net_flow_z` — flujo neto libre de estacionalidad
1. **Nombre y pregunta**: residuo de estacionalidad. Responde a 3 y 4.
2. **Definición**: con `panel`, estimar media por mes-calendario de `net_flow` sobre todas las empresas (o por empresa si hay ≥18 meses). `resid(m) = net(m) − mean_seasonal[mes(m)]`; `z = resid(m) / std(resid de la empresa, 12m)`.
3. **Hipótesis**: "un mes malo que en realidad es tu mes estacional malo no cuenta; un mes malo cuando sueles ir bien sí".
4. **Dirección**: más es mejor. Cero = neutro.
5. **Cobertura**: ~100 %; mejor si se permite usar estacionalidad poblacional para empresas cortas.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media-alta (mitiga el ruido de impuestos trimestrales). Coste medio.

### 23. `recurring_payment_regularity` — regularidad del calendario de pagos
1. **Nombre y pregunta**: disciplina operativa del calendario. Responde a 3 y 4.
2. **Definición**: para cada contraparte (derivada como en feature 14) o producto recurrente que aparezca ≥4 de los últimos 6 meses, calcular el día-del-mes del pago (o el `gap` entre pagos) y su desviación estándar. `reg = mediana(stds)`. Análogo sobre salarios y suministros.
3. **Hipótesis**: una empresa que paga sus recurrentes en fechas estables está ordenada; la irregularidad suele aparecer antes que el impago.
4. **Dirección**: más es peor. Cero = "no aplica" (no hay recurrentes).
5. **Cobertura**: 60-70 %. Riesgo: empresas con pagos semanales frente a mensuales → normalizar por mediana de gaps.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste medio.

### 24. `cash_second_derivative_3m` — aceleración (o frenada) de la caja
1. **Nombre y pregunta**: aceleración de la caja. Responde a 3 y 4.
2. **Definición**: `accel = (cash_end[m] − 2·cash_end[m−1] + cash_end[m−2]) / max(gasto_hab, ε)`.
3. **Hipótesis**: no es lo mismo una caída a velocidad constante que una caída que se acelera; la segunda es la que precede al saldo negativo.
4. **Dirección**: más es mejor. Cero = neutro.
5. **Cobertura**: ~99 %. Riesgo: sensible al ruido del último mes; filtrar outliers `|cash| > 1e10` y suavizar con mediana de 2.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

### 25. `large_tx_share_3m` — peso de operaciones anómalas
1. **Nombre y pregunta**: dependencia de operaciones atípicas. Responde a 3 y 4.
2. **Definición**: `transactions` entrada/salida, ventana 3m. `p99 = p99(|amount|)` de la empresa en 12m; `share = sum(|amount| de tx > p99) / sum(|amount|)`. Alternativa: `top-1 día / total 3m`.
3. **Hipótesis**: si el 40 % de la caja de un mes viene de una operación única (una venta de inmovilizado, un préstamo de un socio), la salud aparente es frágil.
4. **Dirección**: más es peor. Cero = "no aplica".
5. **Cobertura**: ~100 %. Riesgo: empresas muy cíclicas con contratos grandes legítimos → complementar con `n_tx_3m` como contexto.
6. **Evidencia**: **no comprobada**.
7. **Prioridad**: media. Coste bajo.

---

## Top 5 razonado

1. **`cash_burn_velocity_3m` (feature 1).** Es la traducción numérica de la criticidad **crítica** de `scoring.md`: "la caja disponible se evapora en poco tiempo". Ninguna de las 17 actuales mide **velocidad**; `Meses de caja` mide **nivel**. Captura 3, 4 y 6, y es el input natural para la banda "crítica" del producto.
2. **`new_debt_while_cash_falls` (feature 6).** El "tapar el agujero con la tarjeta" en lenguaje consumidor. Es la señal que el banco no ve porque el banco solo mira el saldo del préstamo, no la caja diaria. Muy explicable, coste bajo, y muestra la combinación de **dos** fuentes (deuda + caja) que solo Embat tiene.
3. **`key_supplier_payment_gap` (feature 15).** Anticipación pura: dejar de pagar al proveedor principal precede al impago en semanas. Es también la "cobertura que el banco no tiene" (conciliación y proveedores reales detectados por texto). Buena para la oferta a aseguradoras (impago de clientes y fricción del circulante).
4. **`salary_punctuality_coverage` (feature 4).** Analogía consumidor directa ("se le corta el sueldo"), implementable con `transactions.category='salary'`, robusta sin ERP, y con muy buena interpretabilidad en el pitch. Detecta tanto el deterioro (3) como la recuperación (2).
5. **`net_flow_bounce_back` (feature 20).** Es la pieza que hoy no resuelven (AUC 0,50 en bache vs caída). Combinado con `volatility_persistence_3_12`, distingue un mal mes que rebota de una caída estructural, y es lo que permite decir al CFO "esto no es estructural, es tu trimestre fiscal".

## Interacciones y régimen sugeridas

- **"Caja que se evapora + nueva deuda + póliza agotándose"**: multiplicar `cash_burn_velocity_3m`, `new_debt_while_cash_falls` y `lc_drawdown_velocity_3m` como señal de régimen "crítico". Sustituye a la media plana de ratios que critica `scoring.md`.
- **"Señal temprana con caja sana aparente"**: `key_supplier_payment_gap` alto + `dpo_widening` positivo + `cash_end` alto → caso "empieza a torcerse aunque aún parezca sano" (82 → 68). Debe pesar más que el nivel de caja.
- **"Mejora real"**: `net_customer_gain_3m` > 0 + `net_flow_bounce_back` > 1 + `dso_trend` ≤ 0. Debe activar la cara positiva (45 → 65).
- **"No es salud"**: `reconciliation_coverage_3m` baja, ERP ausente o mes truncado → degradar la **confianza** del score, no imputar riesgo. Regla explícita de `scoring.md`.
- **Interacción con el calendario**: multiplicar `tax_exposure_next_quarter` por el flag de trimestre fiscal. Es la interacción más barata y con más efecto en las ventanas de 1 mes.
- **Régimen por sector implícito**: `inflow_source_entropy_3m` bajo y estable + `n_tx_3m` alto = comercio con TPV; `intragroup_dependency_3m` alto = filial de grupo; `salary_punctuality_coverage` muy alta y estable = servicios con plantilla fija. Usar el régimen para modular pesos.

Cada una de las 25 features es facturable en una frase, calibrable con `research/src/targets.py::add_events`, y usa solo datos `≤ fin de m`. Las que dependen de ERP están etiquetadas como "no aplica" cuando el `pending_amount`/`counterparty_id` no permiten el cálculo, para que el score no confunda cobertura con salud.