# Brainstorming de features: X-Ray (HackSpain 2026, reto de Embat)

Este brief es para proponer **nuevas features** que se puedan calcular con el dataset, además de las que ya tenemos. Léelo entero antes de empezar.

## 1. El reto en 30 segundos

Hay que dar un **score de salud financiera por empresa y mes** (0-100) a partir de su tesorería (bancos, facturas del ERP y deuda), leyendo el comportamiento en las dos direcciones y **antes de que sea evidente**. El sistema responde a seis preguntas:

1. Quién está sano.
2. Quién mejora (p. ej. 45→65).
3. Quién empieza a torcerse aunque aún parezca sano (p. ej. 82→68).
4. Si es un bache puntual de caja o una caída estructural.
5. Qué señal se movió y cuándo.
6. Con cuántos meses de antelación se vio.

El test oculto son 60-80 empresas **nunca vistas**, que pueden venir con historia corta, sin ERP, en otra moneda o con valores fuera de distribución. El jurado prefiere un modelo sencillo y explicable con un producto claro.

Documentos de contexto:
- `context/challenge.md`: enunciado completo.
- `context/scoring.md`: marco del equipo ("la prueba de los 100.000 €": qué le preguntarías a alguien antes de prestarle dinero).
- `data/data_dictionary.md`: diccionario de datos.

## 2. Dónde está el dataset

Son datos sintéticos generados a partir de distribuciones reales de tesorería de pymes: 1.286 empresas en 250 grupos, de septiembre de 2024 a septiembre de 2026 (este último mes, parcial).

| Formato | Ruta | Notas |
|---|---|---|
| CSV originales | `data/*.csv` | `transactions.csv` e `invoices.csv` van por Git LFS: si ves un puntero de 3 líneas, usa la copia de `output/` |
| CSV (copia completa) | `output/*.csv` | Zip del reto descomprimido |
| **Parquet (recomendado)** | `research/data/*.parquet` | Los mismos ficheros, carga en segundos con polars/pandas |
| **Panel mensual ya construido** | `research/data/panel.parquet` | Una fila por empresa × mes (21.538 filas), con los agregados de la sección 4 |
| Tipos de cambio reales | `research/data/fx/fx_monthly.parquet` | BCE + currency-api, unidades por EUR y mes |

Para explorar con Python: `cd research && uv run python` (con polars, pandas, numpy, scikit-learn y lightgbm).

### Ficheros

| Fichero | Filas | Contenido | Columnas clave |
|---|---|---|---|
| `companies` | 1.286 | Empresa | `company_id`, `group_id`, `country` (sucio), `currency`, `erp`, `created_at` |
| `groups` | 250 | Grupo empresarial (1-24 empresas) | `group_id`, `erp`, `n_companies_in_sample` |
| `transactions` | 2,56 M | Movimientos bancarios | `company_id`, `product_id`, `date`, `value_date`, `amount` (− sale, + entra), `exchange_rate`, `status`, `accounting_status`, `category`, `description`, `counterparty_id` |
| `invoices` | 898 k | Facturas del ERP (785 empresas) | `document_type`, `issuance_date`, `due_date`, `payment_date`, `amount` (+ emitida/AR, − recibida/AP), `pending_amount`, `status`, `currency`, `exchange_rate`, `concept`, `counterparty_id` |
| `banking_products` | 5.987 | Cuentas | `type` (checking, card, tpv, saving, investment, expensesPlatform), `bank_name`, `currency`, `created_at` |
| `debt_products` | 2.239 | Financiación | `type` (loan, leasing, lineofcredit, mortgage, renting, factoring, confirming, guarantee), `granted`, `outstanding` (foto final) |
| `debt_schedule_config` | 87 | Cuadros de amortización | `amortization_type`, `amortising_frequency`, `total_periods`, `next_payment_date`, `annual_interest_rate_or_spread` |
| `balances` | 7.996 | Saldo por producto **solo a 1-sep-2026** | `balance`, `available`, `granted` |

Categorías de `transactions.category`: `collection`, `bulk_collection`, `pos_settlement`, `cash_settlement(s)` (cobros); `payment`, `bulk_payment`, `utility`, `fee` (pagos); `salary`, `social_security`, `tax`, `tax_refund`, `debt_repayment`, `interest_charge`, `collection_refund`, `payment_refund`, `transfer`, `cash_withdrawal`, `pos_withdrawal`, `investment_deployment`, `investment_return`, y `-` (sin categorizar, el 25 % de las filas y el 45 % del importe de entradas).

`description` y `concept` son texto libre con marcadores (`[COMPANY]`, `[PERSON]`, `[IBAN]`, `[NUM]`, `COUNTERPARTY_xxxxx`…).

## 3. Trampas del dataset que ya hemos descubierto (no las repitas)

- **Facturas impagadas.** En las facturas `overdue`, `payment_date == due_date` en el 96 % de los casos. Una factura está impagada si `pending_amount ≠ 0` y `status ≠ paid`; en ese caso hay que ignorar `payment_date`. Hay fechas imposibles (año 7025).
- **Saldos históricos.** `balances` es solo la foto final. Los saldos mensuales se reconstruyen hacia atrás: saldo(m) = saldo final − flujos posteriores a m. Hay saldos erróneos extremos (±1e13), así que hay que usar estadísticos robustos.
- **Moneda.** `amount` está en la moneda del **producto**. Para pasarlo a la moneda de la empresa se divide por `exchange_rate`, que falla en algunas filas (=1 en MZN, =0 en VND): se valida contra el tipo real a ±10 %.
- **Transferencias internas.** Los pares mismo día e importe opuesto entre dos productos de la misma empresa son internos. Entre empresas del mismo grupo son intragrupo. Suponen el 27 % del volumen bruto y no son actividad económica.
- **Panel desbalanceado.** Las empresas se incorporan en momentos distintos (el 31 % tiene menos de 12 meses) y el primer mes suele ser parcial. 121 empresas dejan de tener movimientos antes del final.
- **Estacionalidad.** Los impuestos son trimestrales (enero, abril, julio y octubre), así que las ventanas de 1 mes son ruidosas.
- **Causalidad.** Cualquier feature del mes m solo puede usar datos con fecha ≤ fin de m. En particular, "la última transacción del dataset" **no** es causal.
- **Escala.** Hay empresas de 10³ € y de 10⁹ €/mes, y monedas como CLP o COP. Las features deben ser ratios o percentiles, nunca importes absolutos.
- **Sin ERP.** El 36 % de las empresas no tiene facturas.

## 4. Lo que ya tenemos

### Panel mensual (`research/data/panel.parquet`)

`inflow`/`outflow` (sin internas ni intragrupo), `oper_in` (cobros operativos), `transfer_in`, `uncat_in`, `payroll`, `tax`, `debt_service`, `fees`, `refunds`, `cash_end` (caja reconstruida), `lc_drawn`/`lc_limit` (pólizas), `late_share_ar/ap`, `overdue_ar/ap`, `overdue_90_ar/ap`, `hhi_ar_6m`, `n_cust_3m`, `n_cust_12m`, `lost_share`, `ar_issued`, `ap_issued`, `n_tx`, `months_since_last_tx` (causal), `has_erp`, `to_eur`.

### Las 17 features actuales del score

Cada feature se convierte en un percentil de 0-100 frente a todas las empresas-mes del histórico, y el score es una media ponderada. Los pesos se calibraron con logísticas contra eventos a 6 meses (ver 4.3). "¿Orden comprobado?" indica si la tasa de eventos baja de forma monótona por tramos de percentil.

| # | Feature | Qué mide | Mejor si… | Peso | Sin dato | ¿Orden comprobado? |
|---|---|---|---|---|---|---|
| 1 | Tendencia de actividad | Movimientos bancarios de los últimos 3 meses frente a la media de 12 | sube | 0,21 | 12 % | ⚠️ solo la mitad baja |
| 2 | Meses de caja | Caja / gasto mensual habitual (el mayor entre la media de 3 y la de 12 meses) | sube | 0,16 | 1 % | ✅ en toda la escala (33 % → 0 % de saldo negativo) |
| 3 | Clientes perdidos | % de la facturación de hace 3-12 meses que era de clientes a los que ya no se factura | baja | 0,10 | 68 % | ⚠️ solo la cola mala |
| 4 | Pagos tardíos a proveedores | % de facturas recibidas pagadas >15 días tarde o impagadas (3 meses) | baja | 0,10 | 44 % | ⚠️ solo la cola mala |
| 5 | Cobros tardíos de clientes | % de facturas emitidas cobradas >15 días tarde o impagadas (3 meses) | baja | 0,08 | 53 % | sin comprobar |
| 6 | Amplitud de clientes | Clientes facturados en 3 meses frente a los de 12 | sube | 0,07 | 49 % | sin comprobar |
| 7 | Tendencia de cobros | Cobros medios de 3 meses frente a la media de 12 | sube | 0,05 | 12 % | ⚠️ débil |
| 8 | Concentración de clientes | HHI de la facturación a clientes (6 meses) | baja | 0,04 | 50 % | sin comprobar |
| 9 | Devoluciones de cobros | Devoluciones / cobros (3 meses) | baja | 0,04 | 0 % | ❌ sin orden |
| 10 | Deuda vencida con proveedores | Saldo AP vencido (últimos 12 meses) / pagos mensuales | baja | 0,03 | 42 % | sin comprobar |
| 11 | Carga de deuda | Cuotas + intereses / cobros (3 meses) | baja | 0,03 | 0 % | ❌ sin orden |
| 12 | Dependencia de transferencias | Entradas por `transfer` / cobros (3 meses) | baja | 0,03 | 0 % | sin comprobar |
| 13 | Clientes morosos > 60 días | Saldo AR vencido > 60 días / cobros mensuales | baja | 0,02 | 43 % | sin comprobar |
| 14 | Volatilidad a la baja | Semidesviación de los meses con flujo neto negativo / gasto (6 meses) | baja | 0,02 | 12 % | sin comprobar |
| 15 | Peso de nóminas | Nóminas + SS / cobros (3 meses); sin nóminas = no aplica | baja | 0,01 | 43 % | sin comprobar |
| 16 | Uso de pólizas de crédito | Dispuesto / límite de las líneas de crédito | baja | 0,01 | 86 % | sin comprobar |
| 17 | Margen de caja | (cobros − pagos) / (cobros + pagos), 6 meses | sube | 0,01 | 0 % | ❌ sin orden |

Contexto (no puntúan; sirven para la confianza y la detección OOD): tamaño en EUR, % del flujo en divisa, % de entradas sin categorizar, nº de movimientos, meses de historia, meses seguidos sin movimientos.

### Eventos que usamos como ancla (sin etiquetas oficiales)

Se miden en los 6 meses siguientes y sirven para calibrar y validar:

| Evento | Definición | Tasa |
|---|---|---|
| Apagado | La empresa deja de tener movimientos definitivamente | 3 % |
| Saldo negativo | La caja pasa a negativa | 5 % |
| Caída de cobros | La mediana de cobros de los 6 meses siguientes cae por debajo del 50 % de la mediana de los 12 anteriores | 17 % |
| Crecimiento | Cobros >130 % de la media anual y caja al alza | 16 % |

Código de referencia: `research/src/features.py`, `research/src/targets.py`, `research/src/panel.py`.

### Ideas ya en cola (no hace falta proponerlas otra vez, pero sí mejorarlas)

- Caja **mínima intramensual** y días con saldo negativo (saldo diario reconstruido): AUC ~0,79 frente a saldo negativo, mejor que la caja a fin de mes.
- **Obligaciones recurrentes omitidas**: IVA trimestral, cuota de préstamo o nómina que tocaba y no aparece.
- Tendencia de caja a 6 meses para la cara positiva.
- Antigüedad de la deuda con proveedores por tramos.

## 5. Qué te pedimos

Propón **al menos 20 features nuevas** que se puedan calcular con este dataset y que aporten algo que las actuales no capturan. Piensa sobre todo en:

- **Anticipación**: señales que se mueven antes que la caja (comportamiento de pago, clientes, proveedores, contrapartes, patrones de calendario, texto de las descripciones y conceptos, conciliación, productos bancarios, deuda).
- **Las dos caras**: señales de mejora y de solidez, no solo de deterioro.
- **Bache frente a caída**: señales que distingan un mal mes que se recupera de un deterioro estructural. Hoy no lo resolvemos (AUC 0,50).
- **Explicabilidad**: cada feature debe poder contarse en una frase al jurado.
- **Robustez**: que funcione en empresas nuevas, con poca historia o sin ERP.

Si puedes, **compruébalo con los datos**. Calcula la feature sobre `research/data/*.parquet` y mide su relación con los eventos de la sección 4: AUC o tasa de evento por deciles, con `research/src/targets.py` → `add_events`. Una feature sin evidencia está bien si la hipótesis es buena, pero márcala como no comprobada.

### Formato de respuesta, por cada feature

1. **Nombre** y **pregunta del reto** a la que responde (1-6).
2. **Definición exacta**: fichero(s), columnas, filtro, ventana temporal y fórmula. Debe ser causal (solo datos ≤ mes m).
3. **Hipótesis económica**: por qué anticiparía salud o deterioro, en una frase ("si prestaras 100.000 €…").
4. **Dirección esperada** (más es mejor o peor) y si el cero significa "no aplica".
5. **Cobertura estimada** (% de empresas-mes con dato) y riesgos: fuga temporal, OOD, ruido o dependencia del ERP.
6. **Evidencia** si la calculaste: AUC o tasas por decil frente a qué evento, y n.
7. **Prioridad** (alta, media o baja) y coste de implementación.

Termina con un **top 5 razonado** y cualquier idea sobre cómo combinar features (interacciones, umbrales o señales de régimen).

**Reglas:** no modifiques ningún fichero del repositorio salvo tu fichero de salida. Si necesitas scripts, créalos en `/tmp`.
