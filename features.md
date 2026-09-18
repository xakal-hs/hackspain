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

### Propuestas del brainstorming (pendientes de validar)

Cuatro modelos respondieron a este brief: GLM 5.3, DeepSeek V4 y Qwen 3.6 vía Helmcode, sin acceso a datos, y Cursor Auto, que calculó cada feature. Las respuestas completas están en `research/brainstorm/features_*.md` y la síntesis en `research/brainstorm/SINTESIS.md`.

**Aviso sobre la evidencia.** Es univariante, y para cada feature se muestra **el evento donde mejor sale**, así que las cifras están infladas. Antes de incorporar ninguna hay que medir cuánto mejora el score respecto al actual, controlando por tamaño y meses de historia.

**A. Medidas por Cursor Auto con señal**

| Feature | Definición | AUC (evento) | Cobertura |
|---|---|---|---|
| `payee_concentration` | HHI de los pagos bancarios (`amount<0`) por `counterparty_id`, media de 3 meses | **0,75** (apagado); 0,61 (caída de cobros) | ~40 % |
| `lost_accel` | `lost_share` actual − `lost_share` de hace 3 meses | **0,74** (apagado) | ~24 % |
| `payroll_cv` | Desviación / media de `payroll` en 6 meses (si hay nómina) | 0,69 (apagado) | ~53 % |
| `hhi_ap_6m` | HHI de facturas de proveedores (AP) por `counterparty_id`, 6 meses | 0,68 (apagado); 0,62 (caída de cobros) | ~52 % |
| `tax_miss` | En enero, abril, julio y octubre: max(0, esperado − `tax`) / esperado, con esperado = `tax` de 12 meses / 4 | 0,67 (apagado) | ~20 % |
| `billing_to_cash` | `ar_issued` de 3 meses / `oper_in` de 3 meses (ERP). Valores bajos = se deja de facturar | 0,66 (apagado) | ~55 % |
| `payroll_continuity_6m` | % de los últimos 6 meses con `payroll > 0` | 0,66 (apagado) | ~88 % |
| `dpo_3` | Mediana de días entre emisión y pago de las facturas AP pagadas, media de 3 meses | 0,64 (apagado) | ~50 % |
| `ap_early_3` | % de facturas AP pagadas antes de vencer. Pagar "demasiado pronto" = sacar caja antes de tiempo | 0,63 (saldo negativo) | ~50 % |
| `oper_persistence_6m` | % de los últimos 6 meses con `oper_in` ≥ 50 % de su mediana de 12 meses | 0,62 (caída de cobros); **0,67 separando caída estructural de bache** | ~76 % |
| `yoy_inflow` | Cobros frente a los del mismo mes del año anterior | 0,62 (caída de cobros) | ~30 % (hace falta historia de más de 12 meses) |
| `ap_aging_deep` / `ar_aging_deep` | Vencido >90 días / vencido total, en proveedores y en clientes | 0,61 (apagado) / 0,59 (caída de cobros) | ~51 % / ~43 % |
| `vol_asymmetry` | Volatilidad al alza / volatilidad a la baja del flujo neto (6 meses) | 0,61 (crecimiento) | ~87 % |
| `multi_signal_stress` | Cuántas de estas 4 señales se activan: cobros −20 %, actividad −20 %, clientes −20 %, caída de caja > 1 mes de gasto en 3 meses | 0,59 (caída de cobros); 0,58 estructural frente a bache | ~81 % |
| `shock_vs_usual` | Si el flujo neto es negativo: su tamaño / mediana de los últimos 6 meses | 0,57 (caída de cobros) | ~45 % (solo meses con flujo neto negativo) |
| `runway_vs_group` | Meses de caja − mediana de su grupo empresarial ese mes | 0,57 estructural frente a bache | ~99 % |
| `bank_cp_in_trend` | log(pagadores distintos en 3 meses / media de 12), a partir del banco. Es `cust_trend` sin ERP | 0,55 (caída de cobros) | ~85 % |

**B. Ideas de GLM, DeepSeek y Qwen, sin medir** (entre paréntesis, quién las propone)

- **Nómina:** retraso del día de pago de la nómina frente a su día habitual (GLM); puntualidad y cobertura de la nómina (DeepSeek).
- **Obligaciones:** cobertura de la próxima cuota de préstamo con `debt_schedule_config` (DeepSeek); caja frente a la próxima cuota de IVA (DeepSeek); recuento de obligaciones que faltan (Qwen).
- **Plazos de cobro y pago:**
  - Clientes que empiezan a pagar antes de vencer, la cara positiva (GLM).
  - Estiramiento del plazo concedido a clientes y del recibido de proveedores (GLM).
  - Variación del DPO (Qwen) y tasa de cobro efectivo, `oper_in` / `ar_issued` (Qwen).
  - "Triage": pagar tarde solo a ciertos proveedores recurrentes (GLM).
  - Días sin pagar al proveedor principal y rotación de proveedores (DeepSeek).
- **Clientes:**
  - Adquisición y captación neta de clientes nuevos (GLM, DeepSeek) y peso de los cobros de contrapartes nuevas (Qwen).
  - Ticket medio y recurrencia de ingresos (GLM).
  - Entropía de fuentes de cobro (DeepSeek).
  - Variación de la concentración, ΔHHI (GLM), y fidelidad de los cobros recurrentes (Qwen).
- **Bache frente a caída:**
  - Asimetría de ajuste: ¿recorta pagos cuando caen los cobros? (GLM).
  - Persistencia de la caída y ratio de rebote en V (GLM) y rebote tras el peor mes (DeepSeek).
  - Persistencia de la volatilidad (DeepSeek) y pendiente de actividad normalizada por su volatilidad (Qwen).
  - Racha de meses quemando caja y su profundidad (GLM).
- **Financiación forzada:** deuda nueva con caja cayendo (GLM, DeepSeek); velocidad de uso de pólizas y aparición de factoring o confirming (DeepSeek); peso y tendencia de los intereses (GLM, DeepSeek, Qwen).
- **Banco y texto:**
  - Salto de comisiones (GLM).
  - Palabras de refinanciación, impago o aplazamiento en `description` y `concept` (DeepSeek, Qwen).
  - Fragmentación en muchas cuentas y peso de operaciones anómalas (DeepSeek).
  - Pulso del TPV y "silencio de cobros": días sin cobrar (GLM).
  - Colchón fuera de la cuenta corriente, en ahorro e inversión (GLM, Qwen).
  - Fricción de conciliación, que es contexto y no salud (DeepSeek, Qwen).
- **Grupo, estacionalidad y robustez:**
  - Prior del grupo para empresas con poca historia (GLM) y divergencia empresa-grupo (Qwen).
  - Dependencia de fondos intragrupo (DeepSeek, Qwen).
  - Cobros año contra año (los cuatro modelos).

Las ideas que salieron flojas al medirlas (velocidad de caja, deuda nueva mientras cae la caja, tendencias de DSO/DPO…) están en el apartado E de las descartadas.

### Features descartadas (y por qué)

No las propongas otra vez salvo que traigas un giro que resuelva el motivo del descarte. El historial completo está en `research/DECISIONS.md`, y los reviews en `research/reports/review_*.md`.

**A. Sustituidas por una versión mejor**

| Descartada | Sustituta | Motivo |
|---|---|---|
| Margen de caja a 3 meses | Margen a 6 meses | Revertía a la media y metía ruido. Persistencia mes a mes 0,68 frente a 0,80 |
| Crecimiento trimestre contra trimestre anterior | Cobros de 3 meses frente a la media de 12 | Mezclaba estacionalidad (impuestos trimestrales). Persistencia 0,55 frente a 0,69 |
| Meses de caja con gasto de 3 meses y caja ≥ 0 | Gasto = máx(media 3m, media 12m) y caja con signo | Si el gasto se desplomaba, la liquidez subía: las empresas que se apagaban parecían más líquidas (AUC 0,37 del score frente a apagado en v1) |
| Caja negativa (sí/no) | Meses de caja con signo | Una binaria dentro de la media inflaba el pilar de liquidez |
| Peso del mayor cliente en cobros bancarios | Concentración HHI de facturas | `counterparty_id` es nulo en el 89 % de los cobros bancarios: la feature faltaba en el 71 % de las filas |
| Volatilidad total del flujo neto | Volatilidad a la baja | Penalizaba a empresas con mucha caja: más volatilidad iba con **menos** tensión (AUC 0,35) |
| Saldo vencido total de clientes | Vencido > 60 días | El vencido reciente es normal; importa el antiguo |
| Saldo vencido con proveedores sin límite de antigüedad | Solo vencimientos de los últimos 12 meses | Las facturas eternas creaban deriva mecánica: la mediana subía de 0,005 a 1,12 solo por el paso del tiempo |
| Dependencia de transferencias incluyendo la categoría `-` | Solo `category = transfer` | Medía cobros sin categorizar (45 % del importe de entradas). Sin ellos, la señal casi desaparece (AUC 0,43 frente a apagado); `-` pasa a contexto |
| % de pagos tardíos mirando pagos posteriores al cierre | Calculado a fecha de cierre | Fuga de hasta 15 días de información futura |
| "Meses desde la última transacción del dataset" | Contador causal de meses seguidos sin movimientos | No era causal: 429 meses inactivos en mitad de la serie figuraban como activos |
| Ratios con denominador + 1 € fijo | Suelo del 0,1 % del volumen de la propia empresa | Rompía la invariancia de escala en empresas pequeñas o monedas débiles |

**B. Movidas a contexto o a regla (no puntúan)**

| Feature | Dónde está ahora | Motivo |
|---|---|---|
| Nº de movimientos (nivel) | Contexto | Mide tamaño, no salud: premiaba ser grande |
| Tamaño en EUR, % en divisa, % sin categorizar | Contexto (confianza y OOD) | Describen la calidad y la escala del dato, no la salud |
| Empresa inactiva (sí/no) | Regla: sin movimientos, score ≤ 30 | Una binaria en la media se diluía |
| Peso de los cobros operativos sobre las entradas | Eliminada en v4 | Salió al rehacer el pilar de estabilidad **sin evaluación formal**: se puede reevaluar |

**C. Siguen en el score pero no aportan (candidatas a quitar)**

| Feature | Peso | Evidencia |
|---|---|---|
| Margen de caja 6 meses | 0,013 | Sin orden por tramos frente a saldo negativo |
| Devoluciones de cobros | 0,036 | Sin orden por tramos; el 88 % de las filas vale 0 |
| Carga de deuda | 0,030 | Sin orden. Su peso viene del evento "crecimiento" (no tener deuda ↔ crecer), probablemente espurio |
| Peso de nóminas | 0,014 | Apenas señal; el 43 % sin dato |
| Uso de pólizas de crédito | 0,013 | El 86 % sin dato |
| Volatilidad a la baja | 0,018 | Señal débil y de dirección dudosa |

**D. Descartadas por fuga o por diseño**

- **`debt_products` y `debt_schedule_config` como features mensuales.** `outstanding` y `granted` son una foto final: proyectarla hacia atrás filtra el futuro. Solo se usa el límite de las pólizas.
- **`balances` directamente.** Solo existe a 1-sep-2026 y sirve únicamente para reconstruir hacia atrás.
- **Ventanas de 1 mes.** Demasiado ruido por la estacionalidad trimestral.
- **Importes absolutos** (euros de caja, de facturación…). No son comparables entre empresas de 10³ y de 10⁹ € ni entre monedas.
- **Conciliación (`accounting_status`) y `tax_refund`.** La conciliación mide la calidad del dato, no la salud; `tax_refund` solo tiene 2 filas.
- **Impuesto trimestral omitido.** Se descartó en el review de v1 por aportar poco, pero se **reabre**: Cursor Auto midió AUC 0,67 frente a apagado en los meses fiscales.

**E. Del brainstorming, medidas y flojas (en duda)**

Medidas por Cursor Auto contra los eventos a 6 meses:

| Idea | AUC | Lectura |
|---|---|---|
| Cambio de los meses de caja en 3 meses | 0,55 | Revierte a la media. Mejor como explicación que como peso |
| Cambio de caja sobre el gasto en 6 meses | orden invertido | Quien ya subió caja crece menos después |
| Deuda nueva mientras cae la caja | ~0,50 | Pocos casos. Hipótesis de producto fuerte, sin evidencia |
| Tendencia del DSO / del DPO | 0,545 / 0,53 | El nivel sí aporta; la tendencia apenas |
| Transferencias sustituyendo cobros operativos | 0,48 | Solo como interacción |
| Ciclo de conversión de caja (proxy) | 0,52 | Sin orden limpio |
| Intensidad de comisiones bancarias | 0,58 en U | Mejor como alerta de pico que como feature lineal |

**F. Configuraciones del modelo descartadas**

| Descartado | Qué se usa ahora | Motivo |
|---|---|---|
| 21 variables exógenas en el forecaster | 6 | Sobreajuste: −14,6 % frente a AR(1) a 3 meses incluso regularizando |
| Pilares retardados 3 meses como exógenas | Exógenas específicas por horizonte (retardo h) | Daban información vieja a los horizontes de 1 y 2 meses |
| Renormalizar los pesos cuando falta una feature | Sin dato = nota 50 | Sesgo de arranque: las empresas nuevas salían más sanas (mediana 71,5 en el mes 0 frente a 51,1 en el mes 11) |
| Evento "caída de cobros" relativo al trimestre actual | Relativo a la mediana de 12 meses | Era regresión a la media disfrazada de evento: un margen alto "predecía" caída |
| Un único evento adverso compuesto para calibrar | Una logística por evento, pesos promediados | El declive (17 %) dominaba y la disciplina de pagos quedaba a 0. **A revisar:** una logística por evento da AUC 0,63-0,76, frente a 0,59 del score promediado |
| Alerta solo si todo el intervalo del 80 % cae por debajo del nivel actual | Mediana prevista ≤ −10 | Recall del 4 %; la condición no mejoraba la precisión |
| Combinación no lineal (LightGBM) de las 17 señales | Suma lineal | Mismo AUC que la logística lineal (±0,017): con estas señales, la no linealidad no aporta |

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
