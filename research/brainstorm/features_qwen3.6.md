<!-- modelo: qwen3.6 vía Helmcode · 77s · uso: None -->



# Propuesta de 20 Features Nuevas para Score de Salud Financiera (HackSpain 2026)

A continuación se detallan 20 features diseñadas para capturar anticipación, distinguir baches de caídas estructurales, operar en ambas direcciones y mantenerse robustas ante OOD, historias cortas o ausencia de ERP. Todas las definiciones son causales: calculan valores ≤ mes `m` para predecir el estado en `m`.

---

### 1. Deriva del Medio de Pago (DPO Delta)
1. **Pregunta del reto:** 3 (quien empieza a torcerse), 4 (bache vs caída)
2. **Definición:** `DPO_3m = (ap_issued_3m / outflow_3m * 30)`. `DPO_Delta = DPO_3m(m) - DPO_3m(m-3)`. Fichero: `panel.parquet` (`ar_issued`, `ap_issued`, `outflow`). Ventana: causal, solo datos ≤ fin de `m`.
3. **Hipótesis:** Una empresa que alarga sus pagos a proveedores está transfiriendo su falta de liquidez a la cadena de valor; un delta positivo sostenido anticipa impagos y pérdida de crédito comercial.
4. **Dirección:** Más bajo (o negativo) es mejor. 0 indica estabilidad.
5. **Cobertura/Riesgos:** ~55 % (empresas con `ap_issued`). Riesgo de ruido trimestral por impuestos; se mitiga con ventana de 3 meses y winsorización al 1 %.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo (cálculo vectorial sobre panel)

### 2. Tasa de Cobro Efectivo (Cash Collection Ratio)
1. **Pregunta del reto:** 1 (quién está sano), 3 (tendencia oculta)
2. **Definición:** `CRR = oper_in_3m / ar_issued_3m`. Fichero: `panel.parquet`. Ventana: causal ≤ mes `m`.
3. **Hipótesis:** La facturación es contable; el efectivo es real. Un `CRR` que cae por debajo de 0.7 en 3 meses indica que los clientes tardan o impagan antes de que la caja se vuelva negativa.
4. **Dirección:** Más alto es mejor. <0.8 es zona crítica.
5. **Cobertura/Riesgos:** 68 % (excluye sin ERP). OOD en empresas nuevas (<3 meses): se imputa a 1.0 o se marca como `no aplica`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 3. Fragilidad de Contrapartes Nuevas (New Counterparty Inflow Share)
1. **Pregunta del reto:** 2 (quien mejora), 5 (señal movida)
2. **Definición:** `NCS_inflow = inflow_counterparties_new_3m / inflow_total_3m`. Se calcula cruzando `transactions.category='collection'` con `counterparty_id` únicos por mes, identificando los que aparecen por primera vez en los 12 meses previos. Causal.
3. **Hipótesis:** Un NCS alto (>30 %) sugiere que la empresa sustituye clientes por relaciones incipientes; el riesgo de impago temprano es mayor y la salud es frágil aunque el volumen crezca.
4. **Dirección:** Más bajo es mejor. 0 indica rotación estable.
5. **Cobertura/Riesgos:** 95 %. Riesgo: crecimiento real no penalizado; se calibra por percentil dentro del sector/fecha.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Medio (group-by + set operations)

### 4. Subsidio Intragrupos Neto (Intragroup Dependency)
1. **Pregunta del reto:** 4 (bache vs caída), 6 (señal)
2. **Definición:** `IntraDep = sum(inflow from same group) / inflow_total_3m`. Se identifica filtrando `transactions` donde `counterparty_id` pertenece a empresa con `group_id == current_company.group_id` y `date ≤ mes m`. Se excluyen los pares mismo día e importe opuesto (internas). Causal.
3. **Hipótesis:** Dependencia de transfers intragrupos para operar indica actividad real insuficiente. Si `IntraDep` cae de >40 % a 0 %, la holding deja de tapar el agujero y el deterioro se vuelve evidente.
4. **Dirección:** Cercano a 0 es mejor. Desviaciones >25 % son señal de alarma.
5. **Cobertura/Riesgos:** 70 %. Riesgo: `counterparty_id` puede ser `null` en transfers; se usa `description` + `product_id` match para recuperarlos.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Medio (joins por grupo)

### 5. Friction de Conciliación (Reconciliation Lag Ratio)
1. **Pregunta del reto:** 3 (torcerse oculto), 4 (bache)
2. **Definición:** `ReconLag = count(transactions.status='pending' OR accounting_status IN ['PENDING','DISCARDED']) / count(total_transactions_3m)`. Fichero: `transactions.csv`. Causal.
3. **Hipótesis:** Transacciones pendientes o descartadas no se han cubierto. Es un precursor directo de saldo negativo: la caja está "ocupada" por pasivos operativos no resueltos.
4. **Dirección:** Más bajo es mejor. >10 % es crítico.
5. **Cobertura/Riesgos:** 100 % (campo existe). Riesgo: bancos con API lenta generan pending crónico; se descarta el top 1 % más extremo por banco.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 6. Velocidad de Quema de Reserva (Liquidity Runway Proxy)
1. **Pregunta del reto:** 1 (quién está sano), 3 (torcerse)
2. **Definición:** `Runway_m = (cash_end_m - outflow_m+1) / avg(outflow_3m_prev)`. Uso de `panel.parquet` (`cash_end`, `outflow`). Causal: `outflow_m+1` se usa solo para simular en validación; en producción se sustituye por `outflow_m` o mediana forward de 1 mes. Causal estricta: `Runway = cash_end_m / avg(outflow_3m_prev)`.
3. **Hipótesis:** Cuántos meses aguanta si se corta el flujo. <1.5 meses indica evaporación rápida (crítico); >3 meses indica colchón. Mide criticidad directamente.
4. **Dirección:** Más alto es mejor.
5. **Cobertura/Riesgos:** 99 %. Riesgo: saldos reconstruidos con errores ±1e13; se usa mediana de 3 meses y truncado al [0, 24].
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 7. Pendiente de Actividad Normalizada por Volatilidad (Bache vs Estructural)
1. **Pregunta del reto:** 4 (bache vs caída), 2 (mejora)
2. **Definición:** `Slope_Vol = slope(oper_in_6m) / std(oper_in_6m)`. Regresión lineal simple sobre los últimos 6 meses ≤ `m`. Causal.
3. **Hipótesis:** Una pendiente negativa con alto residuo (alta `std`) suele ser un bache recuperable; una pendiente negativa con R² alto y `std` baja es una caída estructural. El ratio normalizado captura la dirección relativa al ruido.
4. **Dirección:** Positivo o cercano a 0 es mejor. Muy negativo = caída.
5. **Cobertura/Riesgos:** 90 %. Riesgo: ventanas <6 meses usan ventana adaptativa (min 3 meses).
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Medio (OLS por grupo)

### 8. Deterioro de la Deuda (Interest/Principal Shift)
1. **Pregunta del reto:** 3 (torcerse), 5 (señal)
2. **Definición:** `IntPr_ratio_3m = sum(interest_charge_3m) / (sum(interest_charge_3m) + sum(debt_repayment_3m))`. Delta = `ratio_3m(m) - ratio_3m(m-3)`. Fichero: `transactions.csv` (`category`). Causal.
3. **Hipótesis:** Si sube la proporción de intereses frente a amortización, la empresa refinancia pasivo por falta de flujo para capital. Anticipa renegociación o incumplimiento.
4. **Dirección:** Delta negativo o neutro es mejor.
5. **Cobertura/Riesgos:** 40 % (solo con deuda). OOD sin deuda: se marca `no aplica`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Bajo

### 9. Concentración de Proveedores (Supplier HHI Trend)
1. **Pregunta del reto:** 3 (torcerse), 5 (señal)
2. **Definición:** `HHI_AP_6m = sum((ap_issued_6m_j / total_ap_6m)^2 for j in counterparties)`. `HHI_Delta = HHI_6m(m) - HHI_6m(m-6)`. Fichero: `panel.parquet` (`ap_issued` por counterparty, requiere join con `transactions.category='payment'` si no hay ERP). Causal.
3. **Hipótesis:** La concentración crece cuando proveedores pequeños cortan fianza por impago. Un HHI_Delta positivo indica pérdida de poder de negociación y mayor riesgo operativo.
4. **Dirección:** Estable o bajando es mejor.
5. **Cobertura/Riesgos:** 60 %. Riesgo: sin ERP se approxima con pagos; se valida con `concept` en facturas.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Bajo

### 10. Indicador de Obligaciones Faltantes (Missed Schedule Count)
1. **Pregunta del reto:** 3 (torcerse), 4 (bache)
2. **Definición:** `MissedDebt = count(debt_schedule_config.next_payment_date <= mes m AND NOT EXISTS(transactions.category IN ['debt_repayment','interest_charge'] AND date == next_payment_date))`. Fichero: `debt_schedule_config` + `transactions`. Causal ≤ mes `m`.
3. **Hipótesis:** Un pago programado sin materializar es incumplimiento tácito o renegociación informal. Anticipa quiebra o venta de activo mucho antes de que la caja se vueva negativa.
4. **Dirección:** 0 es mejor. Conteo creciente = peor.
5. **Cobertura/Riesgos:** 30 % (solo 87 schedules). Muy robusto para ese segmento; no aplica a resto.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta (para subset) / Bajo

### 11. Fragmentación de Flujos (Cash Flow CV)
1. **Pregunta del reto:** 4 (bache), 3 (torcerse)
2. **Definición:** `CV_net = std(net_amount_weekly_3m) / mean(net_amount_weekly_3m)`. Agrupación semanal de `transactions.amount` por `company_id` y mes ≤ `m`. Causal.
3. **Hipótesis:** Gestión sana = patrones estables. CV alto indica dependencia de "plazos" o cobros esporádicos, típico de empresas a punto de quebrar.
4. **Dirección:** Más bajo es mejor.
5. **Cobertura/Riesgos:** 100 %. Riesgo: diferenciar por tamaño; se usa percentil dentro de cuartiles de `inflow`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Medio (agrupación temporal)

### 12. Respaldo de Inversiones/Ahorro (Cash Hoarding Ratio)
1. **Pregunta del reto:** 2 (mejora), 1 (sano)
2. **Definición:** `InvRatio = sum(investment_return_3m + investment_deployment_3m) / inflow_3m`. Fichero: `transactions.csv` (`category`). Causal.
3. **Hipótesis:** Empresas que mueven efectivo a cuentas de inversión o ahorro progresivamente están saneadas. Si el ratio cae bruscamente, reasignan liquidez a gastos o deuda: señal de deterioro.
4. **Dirección:** Subir es mejor (hasta límite razonable ~0.2).
5. **Cobertura/Riesgos:** 20 %. Poca cobertura pero altísimo signal-to-noise.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Baja / Bajo

### 13. Anticipación de Obligaciones Fiscales (Tax Month Deviation)
1. **Pregunta del reto:** 4 (bache vs estructura), 6 (señal)
2. **Definición:** `TaxDev = (outflow_3m / tax_3m) / (avg(outflow_Q / tax_Q) prev 3Q)`. Fichero: `panel.parquet` (`outflow`, `tax`). Ventana trimestral causal ≤ mes `m`.
3. **Hipótesis:** En Q de impuestos, outflow sube ~30 %. Si la relación cae o se distorsiona, la empresa está postergando pagos fiscales o reduciendo actividad real antes de la fecha de vencimiento.
4. **Dirección:** Estable es mejor. Desviaciones >15 % en meses no fiscales = señal.
5. **Cobertura/Riesgos:** 95 %. Riesgo: empresas con exenciones; se ignora si `tax_3m == 0`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Bajo

### 14. Efectividad de Cobros Recurrentes (Collection Stickiness)
1. **Pregunta del reto:** 2 (mejora), 3 (torcerse)
2. **Definición:** `Stickiness = n_counterparties_con_pagos_≥3_meses_consecutivos_6m / n_cust_total_6m`. Fichero: `transactions` (`collection`, `counterparty_id`). Causal.
3. **Hipótesis:** Clientes que pagan puntualmente mes a mes son el núcleo de salud. Si `Stickiness` cae, el motor de caja se desmonta antes de que baje el volumen total.
4. **Dirección:** Más alto es mejor.
5. **Cobertura/Riesgos:** 80 %. Riesgo: facturación por proyecto; se calibra con HHI de clientes.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 15. Depreciación del Activo Circulante (AR Pending Ratio)
1. **Pregunta del reto:** 3 (torcerse), 5 (señal)
2. **Definición:** `AR_Pending = sum(invoices.pending_amount WHERE status IN ['pending','overdue']) / sum(invoices.amount)`. Ventana 6m causal ≤ mes `m`. Fichero: `invoices.csv`. Causal.
3. **Hipótesis:** Si el AR pendiente crece aunque `ar_issued` se mantenga, los clientes pagan más lento. Muestra deterioro de la cadena antes de llegar el cash.
4. **Dirección:** Menor es mejor.
5. **Cobertura/Riesgos:** 65 %. Sin ERP no se calcula; se marca `no aplica`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 16. Divergencia Grupo-Empresa (Peer Divergence Ratio)
1. **Pregunta del reto:** 3 (torcerse), 4 (bache)
2. **Definición:** `PeerDiv = oper_in_3m_company / oper_in_3m_group`. Fichero: `panel.parquet` (join por `group_id`). Causal ≤ mes `m`.
3. **Hipótesis:** Si el grupo crece y la empresa cae (ratio <0.5), es riesgo idiosincrático (gestión, pérdida de clientes clave). Si ambos se mueven juntos, el deterioro es estructural o coyuntural.
4. **Dirección:** Cercano a 1 o >1 es mejor.
5. **Cobertura/Riesgos:** 90 %. Riesgo: grupos de 1 empresa → ratio = 1 (no informativo); se omite en ese caso.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Alta / Bajo

### 17. Coste de la Deuda Implícita (Effective Interest Proxy)
1. **Pregunta del reto:** 3 (torcerse), 5 (señal)
2. **Definición:** `EffIntRate = (sum(interest_charge_3m) / outstanding_debt_m) * 4`. `outstanding_debt_m` se approxima con `debt_products.outstanding` (foto) o acumulando `debt_repayment` hacia atrás desde `m`. Causal.
3. **Hipótesis:** Si el coste efectivo sube (>10 % anual), el mercado/banco encarece el riesgo o la empresa recurre a financiación cara (factoring, leasing). Anticipa cierre o venta.
4. **Dirección:** Menor es mejor.
5. **Cobertura/Riesgos:** 35 %. OOD sin deuda: `no aplica`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Medio

### 18. Resiliencia de Nómina (Payroll Variance)
1. **Pregunta del reto:** 3 (torcerse), 4 (bache)
2. **Definición:** `Payroll_CV = std(salary_6m) / mean(salary_6m)`. Fichero: `transactions.csv` (`category='salary'`). Causal.
3. **Hipótesis:** La nómina es rígida. Si fluctúa mucho, la empresa paga "a destajo" por liquidez, precursor de despidos o parón. Muestra estrés operativo temprano.
4. **Dirección:** Menor es mejor.
5. **Cobertura/Riesgos:** 55 %. Empresas sin nómina: `no aplica`.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Bajo

### 19. Indicio de Reestructuración (Restructuring Keyword Signal)
1. **Pregunta del reto:** 3 (torcerse), 5 (señal)
2. **Definición:** `Restruct_3m = 1 IF count(transactions.description LIKE '%consolidación%' OR '%renegociación%' OR '%quita%' OR '%perdón%') > 0 ELSE 0`. Ventana 3m causal ≤ mes `m`.
3. **Hipótesis:** Intento de reestructurar deuda o activos es señal de que la empresa no puede servir su pasivo actualmente. Anticipa incumplimiento o venta de activo.
4. **Dirección:** 0 es mejor. 1 es peor.
5. **Cobertura/Riesgos:** 5 %. Muy específico pero de altísimo valor predictivo en el segmento que aparece.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Baja / Bajo (regex ligero)

### 20. Desalineación Estacional de Cobros (Seasonal Collection Shift)
1. **Pregunta del reto:** 4 (bache vs estructura), 6 (señal)
2. **Definición:** `SeasonShift = (oper_in_3m / avg(oper_in_3m_Q_prev)) - 1`. Fichero: `panel.parquet`. Causal ≤ mes `m`.
3. **Hipótesis:** Los cobros tienen estacionalidad conocida. Una desviación > ±25 % fuera de ventanas fiscales indica deterioro real, no bache estacional.
4. **Dirección:** 0 es mejor.
5. **Cobertura/Riesgos:** 95 %. Riesgo: empresas <6 meses; se usa media del grupo o同行业 como baseline.
6. **Evidencia:** no comprobada
7. **Prioridad/Coste:** Media / Bajo

---

## Top 5 Razonado

1. **Velocidad de Quema de Reserva (Runway Proxy)** → Mide la criticidad directa: "¿se le acaba el dinero en pocas semanas?". Anticipa saldo negativo sin esperar a que ocurra. Bajo coste, alta cobertura, interpretabilidad inmediata para el jurado.
2. **Deriva del Medio de Pago (DPO Delta)** → Señal de estrés temprano: la empresa usa a proveedores como caja giratoria. Mueve el score antes que los impagos se materialicen en `invoices`.
3. **Pendiente de Actividad Normalizada por Volatilidad (Slope_Vol)** → Resuelve el problema no resuelto de "bache vs caída". Normaliza la dirección por el ruido propio de cada empresa, distinguiendo recuperación coyuntural de deterioro estructural.
4. **Tasa de Cobro Efectivo (CRR)** → Convierte facturación en caja real. Un `CRR` en caída anticipa sequía de efectivo con 1-2 meses de margen. Clave para la pregunta 3 del reto.
5. **Divergencia Grupo-Empresa (Peer Divergence)** → Aísla riesgo idiosincrático del macro. Si el grupo sanea y la empresa no, el score debe penalizar independientemente de la tendencia absoluta. Mejora la precisión en OOD y grupos grandes.

---

## Ideas de Combinación y Producción

- **Interacciones críticas:** `Runway < 1.5` × `CRR < 0.8` → Score ≤ 25 (evaporación + sin conversión). `Slope_Vol < -2` × `CRR > 0.9` → Score 40-50 (bache recuperable, no estructural).
- **Umbrales de régimen:** Definir 3 estados: `COLLAPSE` (Runway <1, ReconLag >10 %, CRR <0.7), `DEGRADATION` (DPO_Delta >5, IntPr_Delta >0.2, Stickiness <0.4), `STABLE/IMPROVING` (Slope_Vol ≥0, CRR ≥0.85, IntraDep <0.15). Transiciones entre estados deben escalar los pesos del score.
- **Adaptación a OOD/Historia corta:** Para `months < 6`, sustituir tendencias por `runway` y `crr` estáticos, y aumentar peso de `peer_divergence` y `recon_lag`. Para sin ERP, desactivar `CRR`/`AR_Pending` y compensar con `payroll_CV` y `inflow_CV`.
- **Explicabilidad al jurado:** Mapear cada feature a lenguaje consumidor: `Runway` → "le quedan X semanas de combustible", `DPO_Delta` → "se está retrasando a proveedores", `Slope_Vol` → "es un bache recuperable o una fuga estructural", `CRR` → "la facturación no se está convirtiendo en efectivo". El score final se presenta como un termómetro con las 3 señales más activas destacadas.