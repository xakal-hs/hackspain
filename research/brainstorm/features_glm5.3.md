<!-- modelo: glm5.3 vía Helmcode · 309s · uso: None -->

# Propuesta de features nuevas — X-Ray (HackSpain 2026, reto Embat)

> **Nota de evidencia.** No he ejecutado código contra el dataset en esta sesión: **todas las features van marcadas como "no comprobada"**, con el test concreto que propongo correr contra `research/src/targets.py → add_events` (AUC global + tasa de evento por decil, split temporal: calibración ≤ 2026-02, validación posterior, y split por `group_id` para evitar fuga entre grupos).

**Preprocesado común (aplica a todas):**
- Flujos = `transactions` con `status ∈ {booked, null}` (se excluye `pending`), importe convertido a EUR (`to_eur`), excluidas transferencias internas (pares mismo día / importe opuesto, mismo `company_id`) e intragrupo (pares entre empresas del mismo `group_id`).
- Facturas: AR = `amount > 0` y `document_type = 'invoice'`; AP = `amount < 0`. Pagada = `status='paid'` y `pending_amount == 0` (solo entonces `payment_date` es válido); impagada = `pending_amount ≠ 0` y `status ≠ 'paid'` (se ignora `payment_date`, trampa del 96 %). Fechas imposibles (año > 2026 o < 2020) fuera.
- Causalidad estricta: toda ventana cierra el último día del mes m. Winsorización p1/p99 antes de convertir a percentil.
- Cuando la ventana larga (12m) no existe, se usa baseline de ≥6 meses marcando el dato como "parcial" (el 31 % de empresas tiene <12 meses).

---

## Bloque A — Criticidad y velocidad de caja

### P1. Δ runway a 3 meses (meses de caja ganados o perdidos)
1. **Pregunta:** 3 y 4. Es la implementación directa de la fila "Crítica" de `scoring.md`.
2. **Definición.** `panel.parquet`: con la definición de la feature 2 actual, `runway(m) = cash_end(m) / max(gasto_3m(m), gasto_12m(m))`. Feature = `runway(m) − runway(m−3)`. Suavizar `cash_end` con la mediana de los últimos 2 meses para amortiguar outliers de reconstrucción (±1e13). Requiere ≥4 meses de panel.
3. **Hipótesis.** Si prestaras 100.000 €, no preguntas cuánto hay en la cuenta: preguntas a qué velocidad se vacía. Perder un mes de runway en un trimestre es, literalmente, "se le está acabando el dinero".
4. **Dirección:** más es mejor; 0 legítimo (runway estable).
5. **Cobertura y riesgos.** Est. ~80 % (solo fallan los 3 primeros meses de cada empresa). Riesgos: ruido de `cash_end` reconstruida → mediana móvil; historia corta → acoplar a P20 (shrinkage).
6. **Evidencia.** No comprobada. Validar AUC vs *saldo negativo* y *apagado* a 6m; hipótesis: supera a la feature 2 actual (nivel) por su componente direccional.
7. **Prioridad:** alta. Coste: bajo (solo panel).

### P2. Racha de quema y profundidad acumulada
1. **Pregunta:** 3 y 4.
2. **Definición.** `panel`: `net(t) = inflow(t) − outflow(t)`. Racha = nº de meses consecutivos con `net ≤ 0` terminando en m (cap 6). Profundidad = `−Σ net(racha) / media(outflow 6m)`.
3. **Hipótesis.** Quemar caja un mes es un bache; quemarla tres seguidos es cómo una pyme entra en espiral: cada mes negativo obliga a tocar pólizas, ahorros o proveedores.
4. **Dirección:** más es peor; 0 legítimo (no está quemando).
5. **Cobertura y riesgos.** Est. ~90 % (basta 1–6 meses). Riesgo: meses parciales por onboarding → exigir mes completo.
6. **Evidencia.** No comprobada. Validar vs *saldo negativo* (complementaria a la caja mínima intramensual ya en cola) y vs *apagado*.
7. **Prioridad:** media. Coste: bajo.

## Bloque B — Bache frente a caída (problema hoy no resuelto, AUC 0,50)

### P3. Asimetría de ajuste cobros–pagos
1. **Pregunta:** 4.
2. **Definición.** `panel`: `adj(m) = [inflow_3m(m)/media12(inflow)] − [outflow_3m(m)/media12(outflow)]` (baselines ≥6m si 12m no disponible, marcado parcial).
3. **Hipótesis.** Cuando cobran menos, las pymes sanas recortan pagos en paralelo (ajuste); las enfermas siguen gastando igual con los cobros cayendo (agujero). La *diferencia* entre las dos tendencias separa gestión de fuga, algo que ninguna de las 17 features ve.
4. **Dirección:** más es mejor (positivo = cobros aguantan y/o gasto recortado).
5. **Cobertura y riesgos.** Est. ~70–75 % con baseline flexible. Riesgos: estacionalidad fiscal en ventanas de 3m → usar medias móviles de 3m; correlación con la feature 1 actual → comprobar aporte incremental.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* y como discriminator del par bache/caída.
7. **Prioridad:** alta. Coste: bajo.

### P4. Persistencia de la caída de cobros
1. **Pregunta:** 4.
2. **Definición.** `panel oper_in`: `base = mediana(oper_in, 12m hasta m−1)`; feature = nº de meses de los últimos 6 con `oper_in < 0,7 × base`.
3. **Hipótesis.** Un mes flojo es un cliente que paga tarde; tres de seis es que se perdió el negocio. La persistencia es la frontera operativa entre bache y caída.
4. **Dirección:** más es peor; 0 legítimo.
5. **Cobertura y riesgos.** Est. ~64 % (≥7 meses). Riesgo: solape semántico con el evento *caída de cobros* (que mira los 6m futuros); la feature es causal, pero vigilar que no absorba toda la calibración de ese evento.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* y *apagado*.
7. **Prioridad:** alta. Coste: bajo.

### P5. Ratio de rebote (recuperación en V)
1. **Pregunta:** 2 y 4. Es la cara positiva del bache.
2. **Definición.** `panel oper_in`: `rebote = max(oper_in(m−1), oper_in(m)) / min(oper_in últimos 6m)`, capado a 3,0. Definido solo si el mínimo ≥ 0,3 × mediana 6m (evita inflarse con un mes casi cero) y hay ≥4 meses.
3. **Hipótesis.** Si tras el mes malo el cobro vuelve por encima del 120 % del mínimo, fue un bache; si se queda en el 60 %, era estructural. Sirve para el caso 45→65 del enunciado.
4. **Dirección:** más es mejor.
5. **Cobertura y riesgos.** Est. ~65 %. Riesgo: mínimo con outlier → se usa el filtro indicado o el p10 en lugar del mínimo.
6. **Evidencia.** No comprobada. Validar vs *crecimiento* y en interacción con P4 (ver combinaciones).
7. **Prioridad:** media. Coste: bajo.

## Bloque C — Comportamiento de pago (anticipación)

### P6. Aceleración del DSO (días de cobro)
1. **Pregunta:** 3. Es la derivada de la feature 5 actual (nivel): lo que anticipa no es el retraso, es su *aceleración*.
2. **Definición.** `invoices` AR pagadas (regla común): `dso_rec = mediana(payment_date − due_date)` de las pagadas con `payment_date ∈ [m−2, m]`; `dso_base =` misma mediana en `[m−12, m−4]`; feature = diferencia en días. Exigir ≥5 facturas pagadas por ventana, si no, null.
3. **Hipótesis.** Cuando a una empresa le empieza a costar cobrar, lo primero que se mueve son los días reales de pago de sus clientes, meses antes de que caiga la caja.
4. **Dirección:** más es peor (+días); 0 legítimo; "no aplica" con <5 facturas.
5. **Cobertura y riesgos.** Est. ~35–40 % (ERP + dos ventanas pobladas). Riesgos: dependencia ERP fuerte; trampa del `payment_date` en impagadas (ya cubierta por la regla común); medianas, nunca medias (colas).
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* y *saldo negativo* con lag 3–6m.
7. **Prioridad:** alta. Coste: medio (recalcular a nivel factura).

### P7. Pago anticipado de clientes (cara positiva)
1. **Pregunta:** 1 y 2.
2. **Definición.** `invoices` AR pagadas en 6m: `% con payment_date ≤ due_date − 5 días`.
3. **Hipótesis.** Que te adelanten el pago es la señal más limpia de demanda fuerte y poder de negociación: el equivalente a que tu cliente te pague por adelantado porque no quiere perderte.
4. **Dirección:** más es mejor; 0 legítimo.
5. **Cobertura y riesgos.** Est. ~45 %. Riesgo: condiciones sectoriales → si calibra mal en cross-section, usar delta intraempresa.
6. **Evidencia.** No comprobada. Validar vs *crecimiento* (señal esperada positiva).
7. **Prioridad:** media. Coste: medio.

### P8. Estiramiento del plazo concedido a clientes (AR)
1. **Pregunta:** 3.
2. **Definición.** `invoices` AR emitidas en 3m con `due_date > issuance_date`: `term_rec = mediana(due_date − issuance_date)`; `term_base` = misma mediana en `[m−12, m−4]`; feature = delta en días. Exigir ≥5 facturas.
3. **Hipótesis.** Cuando el producto no rota, se vende a más plazo: alargar condiciones es descuento disfrazado y aparece 1–2 trimestres antes de que caiga el cobro.
4. **Dirección:** más es peor.
5. **Cobertura y riesgos.** Est. ~40–45 %. Riesgos: renegociaciones legítimas; pocas facturas → mediana y umbral mínimo.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* con lag.
7. **Prioridad:** media. Coste: medio.

### P9. Estiramiento del plazo recibido de proveedores (AP)
1. **Pregunta:** 3.
2. **Definición.** Igual que P8 sobre facturas AP (`amount < 0`): mediana de plazo 3m vs baseline 12m.
3. **Hipótesis.** El proveedor es la primera línea de crédito de una pyme apurada: si tus plazos de compra se alargan sin que lo negocies tú, es que estás pidiendo aire.
4. **Dirección:** más es peor, pero ambiguo (puede ser poder de negociación) → **proponer en interacción con P1**: solo penaliza si la runway está cayendo.
5. **Cobertura y riesgos.** Est. ~40–45 %. Riesgo ERP; ambigüedad de dirección resuelta por la interacción.
6. **Evidencia.** No comprobada. Validar la interacción vs *saldo negativo*.
7. **Prioridad:** media. Coste: medio.

### P10. Retraso de la nómina (día de pago de salarios)
1. **Pregunta:** 3; también alimenta 5 y 6 (señal datable con meses de antelación).
2. **Definición.** `transactions` con `category='salary'` y `amount < 0`: `day_rec` = mediana del día-de-mes de las nóminas en `[m−2, m]`; `day_base` = misma mediana en `[m−12, m−4]` (o primeros 6m con nómina); feature = `day_rec − day_base` en días. Excluir meses parciales por onboarding.
3. **Hipótesis.** Lo primero que se retrasa cuando la caja aprieta es la nómina: nadie deja de cobrar a propósito, pero el día de la nómina se desliza del 1 al 5 y del 5 al 10. Es la señal de "vivir al límite" más barata del dataset y no necesita ERP.
4. **Dirección:** más es peor; 0 legítimo.
5. **Cobertura y riesgos.** Est. ~45–50 % de empresa-mes (solo empresas con `salary`). Riesgos: 1–2 pagos/mes → mediana robusta; festivos → umbral de significancia ≥3 días.
6. **Evidencia.** No comprobada. Validar vs *saldo negativo* y *apagado*; hipótesis de lead time 2–4 meses.
7. **Prioridad:** alta. Coste: bajo-medio.

### P11. Triage: retraso selectivo a proveedores recurrentes
1. **Pregunta:** 3.
2. **Definición.** `invoices` AP 3m: proveedor recurrente = `counterparty_id` con ≥3 AP en los 12m previos. `late_rec` = % de AP a recurrentes impagadas (regla común) o pagadas >15d tarde (solo `status='paid'` y `pending==0`). Feature = `late_rec − late_share_ap` (la feature 4 actual). Exigir ≥3 recurrentes.
3. **Hipótesis.** En apuros se paga primero a quien hace falta para producir y se estrangula al resto; cuando el retraso alcanza a los proveedores estructurales, el problema ya es de supervivencia, no de gestión.
4. **Dirección:** más es peor.
5. **Cobertura y riesgos.** Est. ~40 % (ERP + recurrencia). Riesgo: pocas contrapartes recurrentes por empresa → umbral mínimo.
6. **Evidencia.** No comprobada. Validar vs *saldo negativo* y *apagado*.
7. **Prioridad:** media. Coste: medio-alto (matching de contrapartes).

## Bloque D — Clientes, cartera y crecimiento (cara positiva)

### P12. Adquisición de clientes nuevos
1. **Pregunta:** 2 (quién mejora).
2. **Definición.** `invoices` AR con `issuance_date ≤ fin m`: primera factura AR histórica por `counterparty_id`. `new_3m` = nº de clientes con primera factura en `[m−2, m]`, excluyendo los 2 primeros meses tras `first_inv` (artefacto de arranque). Feature = `new_3m / max(n_cust_12m, 1)`.
3. **Hipótesis.** Estrenar clientes es el mejor predictor de la cara 45→65: una cartera que se renueva sostiene los cobros del futuro; la que no estrena nadie en 6 meses vive de la cola.
4. **Dirección:** más es mejor; 0 legítimo.
5. **Cobertura y riesgos.** Est. ~40–45 %. Riesgos: fuga temporal en empresas nuevas (requiere ≥6m de historia); ERP.
6. **Evidencia.** No comprobada. Validar vs *crecimiento*.
7. **Prioridad:** alta. Coste: medio.

### P13. Deriva de concentración (ΔHHI 6m)
1. **Pregunta:** 3. Es la derivada de la feature 8 actual (nivel).
2. **Definición.** `panel hhi_ar_6m`: feature = `hhi_ar_6m(m) − hhi_ar_6m(m−6)`.
3. **Hipótesis.** El nivel del HHI dice cuán expuesto estás hoy; la derivada, hacia dónde vas. Subir de 0,2 a 0,5 en seis meses es un cliente que se lo está comiendo todo: riesgo futuro aunque el nivel hoy parezca sano.
4. **Dirección:** más es peor.
5. **Cobertura y riesgos.** Est. ~35 %. Riesgo: ruido con pocas facturas (el HHI 6m ya suaviza).
6. **Evidencia.** No comprobada. Validar vs *caída de cobros*.
7. **Prioridad:** media. Coste: bajo.

### P14. Ticket medio de facturación
1. **Pregunta:** 3 y 2.
2. **Definición.** `invoices` AR 3m: `tick_rec = mediana(amount)`; `tick_base` = mediana en `[m−12, m−4]`; feature = `tick_rec/tick_base − 1`.
3. **Hipótesis.** Vender más facturas pero más pequeñas es bajar precios para rotar: se ve en el ticket medio antes que en la facturación total y anticipa margen a la baja. Al revés, ticket al alza con volumen = poder de precios (cara positiva).
4. **Dirección:** más es mejor.
5. **Cobertura y riesgos.** Est. ~45 %. Riesgo: mix de producto; el delta intraempresa controla sector.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* y *crecimiento*.
7. **Prioridad:** media. Coste: medio.

### P21. Recurrencia de ingresos (calidad de cartera)
1. **Pregunta:** 1 y 4 (solidez estructural).
2. **Definición.** `invoices` AR 12m hasta m: feature = `Σ amount` facturado a contrapartes con ≥3 facturas AR en la ventana ÷ `Σ |amount|` AR total.
3. **Hipótesis.** El ingreso que repite cada mes es contrato; el que no, suerte. A igual facturación, el 70 % de cartera recurrente aguanta un bache que a la empresa esporádica la mata. Ortogonal al HHI (concentración ≠ recurrencia) y a la amplitud (feature 6).
4. **Dirección:** más es mejor; 0 legítimo (todo esporádico).
5. **Cobertura y riesgos.** Est. ~50 %. Riesgo ERP; IDs de contraparte estables en el dataset, matching fiable.
6. **Evidencia.** No comprobada. Validar vs *apagado* y *caída de cobros* (esperado protector).
7. **Prioridad:** media. Coste: medio.

## Bloque E — Bancos, deuda y texto de movimientos

### P15. Salto de comisiones bancarias
1. **Pregunta:** 3 y 5. La categoría `fee` (179k filas) existe en el panel (`fees`) y **ninguna de las 17 features la usa**.
2. **Definición.** `panel fees`: `fee_ratio(m) = fees_3m / max(inflow_3m, ε)`; feature = `fee_ratio − mediana(fee_ratio, 12m previos)`. Alternativa binaria: `fees(m) > p90` de la propia historia (≥6m) → 1.
3. **Hipótesis.** Las comisiones son el termómetro del banco: se disparan con descubiertos, recibos devueltos y mantenimiento extra. El banco te cobra más justo cuando peor lo pasas; señal mensual que no depende del ERP.
4. **Dirección:** más es peor; 0 legítimo.
5. **Cobertura y riesgos.** Est. ~90–95 %. Riesgo: el crecimiento de la actividad infla fees → por eso ratio y delta intraempresa.
6. **Evidencia.** No comprobada. Validar vs *saldo negativo* (hipótesis fuerte) y *apagado*.
7. **Prioridad:** alta. Coste: bajo.

### P16. Peso de intereses en el servicio de deuda
1. **Pregunta:** 3.
2. **Definición.** `transactions` 6m: `i = Σ|amount|` con `category='interest_charge'`; `p = Σ|amount|` con `category='debt_repayment'`; feature = `i/(i+p)`. **Null si no hay flujos de deuda; ojo: 0 no es "no aplica" aquí, 0 = se amortiza todo principal.**
3. **Hipótesis.** Pagar solo intereses sin amortizar es la cinta de correr del crédito: la deuda no baja nunca. Cuando el peso de intereses sube dentro del servicio, la empresa ya no genera caja para devolver principal (complementa a la feature 11, que mide la carga total).
4. **Dirección:** más es peor; null = sin deuda observable.
5. **Cobertura y riesgos.** Est. ~40–50 % de empresa-mes con flujos de deuda. Riesgo: que algún banco mezcle interés dentro de `debt_repayment` → revisar 20 descripciones de ejemplo antes de confiar.
6. **Evidencia.** No comprobada. Validar vs *apagado* y *saldo negativo*.
7. **Prioridad:** media. Coste: bajo.

### P17. Deuda nueva con caja cayendo
1. **Pregunta:** 3. Literal de `scoring.md`: "pide un préstamo para tapar el agujero".
2. **Definición.** Alta = primer `interest_charge`/`debt_repayment` no visto en los 6m previos, o `debt_products.created_at ∈ [m−2, m]` (caveat: es fecha de conexión, no de concesión). Feature = `alta × max(0, 0,9 − inflow_3m/media12(inflow))`: magnitud proporcional al frío de la actividad en el momento del alta.
3. **Hipótesis.** Financiarse para crecer es sano; financiarse para llegar a fin de mes no. La misma alta de deuda vale lo contrario según la trayectoria: por eso es interacción, no nivel.
4. **Dirección:** más es peor.
5. **Cobertura y riesgos.** Est. ~40–45 % para la interacción. Riesgos: `created_at` no causal en sentido económico; falsas altas por primera conciliación.
6. **Evidencia.** No comprobada. Validar vs *apagado* y *saldo negativo* a 6m.
7. **Prioridad:** alta. Coste: medio.

### P18. Colchón financiero fuera de la cuenta corriente
1. **Pregunta:** 1 y 2 (solidez, cara positiva).
2. **Definición.** `banking_products` con `type ∈ {investment, saving}` y `created_at ≤ fin m` → hay colchón. Feature = `Σ investment_return 12m / (Σ oper_in 12m + Σ investment_return 12m)` (categoría de `transactions`). **Null si no hay productos de inversión; no imputar 0.**
3. **Hipótesis.** Es el ahorro fuera de la cuenta corriente: no lo ves en el checking, pero cambia por completo la probabilidad de impago ante un bache.
4. **Dirección:** más es mejor; null = sin productos.
5. **Cobertura y riesgos.** Est. ~10 % (201 productos investment + 10 saving). Cobertura baja → usar como bonificador acotado, no como feature de peso.
6. **Evidencia.** No comprobada. Validar vs *saldo negativo* (esperado efecto protector).
7. **Prioridad:** baja. Coste: bajo.

### P19. Pulso TPV (ventas de los últimos 30 días)
1. **Pregunta:** 3 y 5. La señal con mayor resolución temporal del dataset.
2. **Definición.** `transactions` con `category='pos_settlement'` (+ opcional `'cash_settlement'`, incluida la variante typo `'cash_settlements'`): `pulse = Σ(últimos 30d) / mediana(Σ 30d móviles en los 90d previos) − 1`. Exigir ≥8 días con settlements en 90d.
3. **Hipótesis.** El TPV liquida a diario: dos semanas de ventas cayendo se ven aquí un mes antes que en el agregado mensual de cobros. Es la vía más corta a "con cuántos meses de antelación se vio".
4. **Dirección:** más es mejor.
5. **Cobertura y riesgos.** Est. ~15–25 % (subconjunto comercio). Riesgos: comparación solo intraempresa (estacionalidad comercial fuerte); fuera de distribución si el comercio nuevo no tiene 90d.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* en el subconjunto con TPV.
7. **Prioridad:** media. Coste: medio.

### P22. Silencio de cobros (latido de caja)
1. **Pregunta:** 3 y 5.
2. **Definición.** `transactions` con `category ∈ {collection, bulk_collection, pos_settlement, cash_settlement}`: `gap_now` = días desde el último cobro operativo ≤ fin m; `gap_med` = mediana de intervalos entre cobros consecutivos en los 6m previos; feature = `gap_now / max(gap_med, 1)`. Null si <2 cobros en 6m.
3. **Hipótesis.** Cada pyme tiene su ritmo (remesa semanal, TPV diario). Cuando el ritmo se rompe —llevas el triple de tu intervalo normal sin cobrar— es la forma más temprana y barata de ver que algo se ha parado. Más fina que `months_since_last_tx` (que cuenta cualquier movimiento).
4. **Dirección:** más es peor.
5. **Cobertura y riesgos.** Est. ~75 %. Riesgo: cobros genuinamente irregulares → normalizar por el propio ritmo lo mitiga.
6. **Evidencia.** No comprobada. Validar vs *apagado* y *caída de cobros* con lag corto (3m).
7. **Prioridad:** alta. Coste: bajo.

## Bloque F — Robustez, estacionalidad y producto

### P20. Prior de grupo (shrinkage de actividad)
1. **Pregunta:** 3 y 1; pieza clave de robustez para el test oculto (empresas nuevas con historia corta).
2. **Definición.** Por `group_id` y mes: `group_trend` = mediana entre empresas del grupo de `inflow_3m/media12(inflow)`. Feature final para historia corta: `f = w·trend_in + (1−w)·group_trend` con `w = meses_historia/(meses_historia+3)`. Grupo de 1 empresa → null → mediana global del mes.
3. **Hipótesis.** Las filiales comparten cliente, ciclo y dirección: si el grupo entero se enfría, la filial con 4 meses de historia hereda ese riesgo aunque su serie propia no dé para nada. Es el sustituto bayesiano del "todavía no sé".
4. **Dirección:** más es mejor (es una tendencia).
5. **Cobertura y riesgos.** Est. ~95 % en meses con grupo activo. Riesgo: grupos unitarios (≈ muchos de los 250) → caen a mediana global; fuga si en el test oculto cambian las composiciones de grupo.
6. **Evidencia.** No comprobada. Validar en el subset con <12m de historia vs *caída de cobros*: hipótesis de que reduce el error justo donde las features propias son nulas.
7. **Prioridad:** alta. Coste: medio.

### P23. Cobros año contra año (desestacionalizado)
1. **Pregunta:** 1 y 3.
2. **Definición.** `panel oper_in`: `yoy = oper_in(m)/max(oper_in(m−12), ε) − 1`, exigiendo el mes m−12 completo; winsorizado a [−1, +3].
3. **Hipótesis.** Comparar con el mismo mes del año pasado elimina de golpe el IVA trimestral y la estacionalidad del sector: es la única tendencia de cobros que no miente en enero ni en agosto. Ataca directamente la causa del "⚠️ solo la mitad baja" de la feature 1.
4. **Dirección:** más es mejor.
5. **Cobertura y riesgos.** Est. ~55–65 % de empresa-mes (historia ≥13m). Riesgos: fuga temporal (empresas nuevas fuera); crecimiento orgánico alto confunde nivel con tendencia → complementa, no sustituye, a la feature 1.
6. **Evidencia.** No comprobada. Validar vs *caída de cobros* y *crecimiento*; hipótesis: orden monótono por deciles (lo que la feature 1 no consigue).
7. **Prioridad:** alta. Coste: bajo.

### P24. Índice de confianza y bandera OOD (capa de producto, **no puntúa**)
1. **Pregunta:** 5 y robustez del test oculto.
2. **Definición.** Componer un 0–1 con: meses de historia (panel), `has_erp`, % de transacciones con `accounting_status='DISCARDED'` (3m), % de entradas sin categorizar, % con `status='pending'`, `months_since_last_tx` y cobertura de saldos. Tres usos: (a) etiqueta de confianza junto al score; (b) apaga features ERP-dependientes bajo umbral; (c) bandera OOD: si un ratio cae fuera de [p0,5, p99,5] del histórico, el percentil se clipea y se marca "revisión".
3. **Hipótesis.** Un score sin confianza es un número peligroso: un 78 calculado sobre 2 meses y media cuenta descartada induce la decisión equivocada. La observabilidad es cobertura, no riesgo (y tratarla como castigo penaliza a quien conecta más cuentas).
4. **Dirección:** más confianza es mejor. Explícitamente fuera de la media ponderada del score.
5. **Cobertura y riesgos.** 100 %. Riesgo: mal uso si alguien lo mezcla en el score; documentarlo.
6. **Evidencia.** No comprobada. Validar: correlación del índice con el error del score (`|score(m+6) − score(m)|`) en backtest.
7. **Prioridad:** alta para el producto. Coste: bajo-medio.

---

## Top 5 razonado

1. **P1 — Δ runway 3 meses.** Traduce a feature la "criticidad crítica" que `scoring.md` exige y el score actual pierde al promediar ratios. Barata, causal, y responde a la vez "quién se tuerce" (Q3) y "gravedad de lo que se movió". Es la pieza que más cambia decisiones: prestar/vigilar/no prestar.
2. **P3 — Asimetría de ajuste cobros–pagos.** Ataca el problema declarado como no resuelto (bache vs caída, AUC 0,50) con una idea contable sencilla: ¿quién ajusta el gasto cuando falta el cobro? Dos caras, sin ERP, percentil fácil. Complemento natural: P4 (persistencia) y P5 (rebote) para cerrar el cuadrante completo.
3. **P10 — Retraso de la nómina.** Señal conductual anticipada, barata, sin ERP, y con la mejor explicación de una frase del lote ("si retrasas la nómina, estás justo"). Funciona exactamente en el segmento donde el ERP no ayuda (36 % de empresas) y encaja con la analogía consumidor del scoring.
4. **P20 — Prior de grupo (shrinkage).** El test oculto son 60–80 empresas nunca vistas, posiblemente con historia corta: este es el único mecanismo propuesto que mejora por construcción en ese régimen, usando estructura (`group_id`) que ya existe. Sin él, las empresas nuevas salen con percentiles vacíos o sesgados.
5. **P23 — Cobros año contra año.** La corrección más directa al ruido estacional (IVA trimestral) que hoy rompe la monotonía de la feature 1. Misma idea, mejor estimador, orden por deciles esperado limpio. Coste mínimo, riesgo mínimo, ganancia inmediata en la calibración logística existente.

Menciones honrosas: P15 (comisiones, la categoría huérfana del panel), P22 (silencio de cobros) y P6 (aceleración del DSO) si se quiere más profundidad ERP.

## Cómo combinarlas

- **Capa de criticidad, no peso en la media.** Flag crítico si `runway < 2 meses` **o** `Δrunway_3m ≤ −1` (P1) **o** (`racha ≥ 3` y `profundidad > 0,5`, P2). Si crítico: el score final no puede superar un techo (p. ej. p40) y la explicación principal pasa a ser "la caja se está evaporando". Esto implementa el "no suavizarlo con un promedio de ratios" de scoring.md.
- **Plano bache vs caída.** Eje x = P4 (persistencia), eje y = P5 (rebote) → cuadrantes {bache en curso, bache resuelto, deterioro estructural, estable}. En "bache resuelto", amortiguar con decaimiento exponencial (½-vida de 2 meses) las señales negativas del mes del golpe. Es también la mejor lámina para el jurado.
- **Shrinkage generalizado.** Aplicar el esquema de P20 (`w = n/(n+3)`) a toda feature de tendencia: P23, P3 y la feature 1 actual. Convierte "sin dato" en "prior informado" en vez de imputar medias.
- **Interacciones dirigidas** (no producto cartesiano): P9 (plazo AP) × P1<0; P17 (deuda nueva) × tendencia de cobros; P16 (peso de intereses) × P15 (fees altas) = "cinta de correr" completa: paga intereses, no amortiza y el banco le cobra por descubrirse.
- **Renormalización por cobertura.** Con features ERP y no-ERP conviviendo, renormalizar los pesos al conjunto de features disponibles *de esa empresa-mes* en lugar de imputar el neutro; evita el sesgo estructural a favor de quien no conecta el ERP.
- **Q5/Q6 (qué señal y con cuánta antelación).** Registrar por feature la primera fecha de cruce de umbral propio (P10 > +3 días, P15 > p90 propio, P22 > 2× intervalo) y calcular el lead time frente a cada evento con `add_events`. Eso da la tabla "señal → meses de antelación" para la demo y sirve para reponderar: solo mandan en el score las señales con lead time demostrado.
- **Higiene de validación.** Todas las nuevas features al mismo pipeline: percentil 0–100, logísticas contra eventos a 6m, split temporal + split por `group_id`, y comparación de AUC incremental frente al modelo de 17 features (aporte marginal, no correlación con las existentes).