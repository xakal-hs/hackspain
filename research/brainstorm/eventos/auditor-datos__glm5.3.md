<!-- modelo: glm5.3 vía Helmcode · lente: auditor-datos · 370s · uso: {'usage': None, 'finish_reason': 'stop'} -->

# Auditoría escéptica de los eventos-ancla

## 1. Posición

Los cuatro eventos mezclan fenómeno económico con artefactos de construcción del dataset: saldos reconstruidos hacia atrás (errores persistentes), un último mes parcial, censura de muestreo en los bordes de la vida de cada empresa, categorías `-` y conversiones de divisa rotas. Calibrar pesos y AUC contra etiquetas así no mide salud: mide el proceso de generación de datos, y el test oculto castigará cualquier peso aprendido de esos bugs. El **apagado es el menos fiable como verdad de salud** (las empresas se van sin estar mal: caja de salida 0,59 vs 0,48 activas; solo el 36 % sintomático —medido por el equipo—) y la **caída de cobros es la más fiable** tras corregir sus contaminaciones conocidas. Antes de usar cualquier evento como ancla exigiría corroboración con una segunda fuente independiente (banco ↔ ERP ↔ deuda) y estabilidad bajo perturbación de la reconstrucción.

## 2. Veredicto sobre cada evento actual

| Evento | Veredicto | Motivo |
|---|---|---|
| Apagado | **Separar como otro producto** (churn de Embat / censura); fuera del ancla de salud | Sale sin deterioro previo (caja 0,59 vs 0,48; 22 % se va con >3 meses; 36 % sintomático): parece truncamiento de muestreo o desconexión, no cierre. Además contamina: 69 % de los apagados cuentan como caída |
| Saldo negativo | **Redefinir**: primer mes de episodio, corroborado; el estado crónico pasa a feature | 46 % de persistencias >3 meses y AUC 0,77 de la propia caja huelen a offset de reconstrucción; el 3 % de saldos imposibles confirma errores |
| Caída de cobros | **Mantener, redefinida** (ex-churn, base ≥9 meses, mes parcial excluido, sin financiación en el inflow) | Fuente bancaria y mediana robusta: la más independiente de categorías y ERP. Candidata a ancla principal |
| Crecimiento | **Redefinir** (yoy/estacional, sobre cobros operativos, persistencia, cap de one-off) | 130 % sobre la media anual dispara falsos por estacionalidad, bases cortas o pequeñas, y financiación contada como cobro |

**Auditoría del apagado (mecanismos de falso evento y comprobaciones).**
- **F1 · Truncamiento del final.** Si septiembre 2026 llega vacío o casi, toda empresa sana con último movimiento a finales de agosto parece apagada. Comprobación: histograma del último `transactions.date` por empresa y `n_tx` de agosto 2026 de las empresas "apagadas" con último movimiento en ago-26. *Confirma artefacto*: corte brusco en una fecha y agosto normal para esas empresas. *Refuta*: últimos movimientos distribuidos de forma uniforme con ≥3 meses de decadencia previa.
- **F2 · Censura de muestreo (vida simulada independiente de la salud).** Ya sugerida por las cifras medidas. Comprobación: comparar Δinflow y meses de caja de los 3 meses previos a la salida frente a activas emparejadas por mes y decil de tamaño (KS). *Confirma*: curvas indistinguibles (coincide con lo medido).
- **F3 · Desconexión de plataforma.** Si es un apagón de datos, cesa todo a la vez. Comprobación: por empresa apagada, dispersión de la última fecha de movimiento entre `product_id`s, y comparar última `invoices.issuance_date` con último movimiento. *Confirma desconexión*: facturas y movimientos cesan el mismo día ±7 y en todas las cuentas simultáneamente, con `pending_amount > 0` sin cobrar. *Refuta (muerte real)*: la empresa sigue emitiendo facturas después de su último movimiento bancario.
- **F4 · Historia corta.** Comprobación: tasa de apagado contra meses entre `companies.created_at` y 2026-09-01. *Confirma*: tasa que cae monótonamente con la antigüedad.
- **F5 · Desconexión a nivel de grupo.** Comprobación: tasa por `group_id`; exceso de grupos con todas sus empresas apagadas frente a lo esperado binomial.

**Auditoría del saldo negativo.**
- **F1 · Offset de la reconstrucción hacia atrás.** saldo(m) = final − flujos posteriores: un flujo perdido o mal fechado desplaza todos los meses previos de forma persistente (encaja con el 46 % de negativos crónicos). Comprobación: innovación diaria d(m) = cash_end(m) − (cash_end(m+1) − flujo_neto(m+1)) sobre el panel. *Confirma artefacto*: los primeros meses negativos coinciden con |d| > P90 propio y el negativo mantiene un offset casi constante. *Refuta*: negativos episódicos sin innovación asociada.
- **F2 · Divisas.** `exchange_rate` roto (VND=0, MZN=1) y filas descartadas por la validación ±10 % dejan huecos de flujo. Comprobación: tasa de meses negativos por `companies.currency` y por empresas con conversión fallida. *Confirma*: tasa ≫ 5 % en monedas exóticas (estimo 2–5×). *Refuta*: homogénea.
- **F3 · Internas desemparejadas.** Piernas sueltas de traspasos en el cambio de mes se leen como salida neta. Comprobación: neto interno no emparejado por empresa-mes (pares mismo día, importe opuesto, misma empresa); ¿coincide con el primer mes negativo con un neto >10 % del gasto habitual?
- **F4 · Barrido a ahorro/inversión.** Si cash_end no suma `saving`/`investment` (`banking_products.type`), mover dinero parece perderlo. Comprobación: traspaso saliente hacia esos tipos en el mes negativo.
- **F5 · Sobregiro real vs error (corroboración clave).** El banco cobra por descubiertos. Comprobación: coincidencia del mes negativo con `interest_charge` o pico de `fee` (>P90) en el mes o ±1, o subida de `lc_drawn`. Coincidencia alta ⇒ evento económico; coincidencia al ruido ⇒ artefacto.
- **F6 · Imposibles.** Recortar las filas con |saldo| > 50× volumen (3 % medido) y remedir: si la tasa baja de 5 % a ~3–4 % (estimación), la contaminación es material.
- **F7 · Selección por pólizas.** Las empresas con `lc_limit > 0` rara vez muestran negativo (disponen antes): el evento subestima tensión ahí. Comprobación: tasa de evento con/sin póliza y trayectoria de `lc_drawn` previa.

**Auditoría de la caída de cobros.**
- **F1 · Mes parcial en la ventana futura.** Con horizonte 6, solo el mes de evaluación 2026-03 incluye 2026-09 en su ventana (la mediana de 6 con un mes casi vacío se deprime algo). Comprobación: tasa de decline por mes de evaluación; pico en 2026-03 que desaparece al prorratear o excluir 2026-09.
- **F2 · Base corta.** `min_samples=3` en la mediana de 12 incluye el primer mes parcial. Comprobación: tasa por meses de historia; si las de 3–8 meses duplican a las de ≥12, exigir base ≥9 meses.
- **F3 · Estacionalidad.** Ventana futura en temporada baja contra base en alta. Comprobación: índice estacional de ambas ventanas por empresa; y reversión: inflow en meses 7–12 posteriores ≥70 % de la base ⇒ era estacional/one-off, no caída.
- **F4 · Financiación contada como cobro.** Disposiciones de póliza, factoring o préstamos con categoría `-` (45 % del importe de entradas) inflan el inflow; al secarse, "caen los cobros" sin caer la actividad. Comprobación: recalcular el evento con `oper_in` y con inflow excluyendo entradas con marcadores de financiación en `description` o contraparte bancaria; κ bajo entre versiones ⇒ etiqueta inestable.
- **F5 · Solape mecánico con apagado** (69 % medido). Comprobación: remedir excluyendo futuros apagados de la ventana; quedará ~10–13 % (estimación) y esa versión limpia es el ancla.

**Auditoría del crecimiento.**
- **F1 · Umbral trivial.** 130 % sobre base corta o pequeña. Comprobación: tasa por longitud de historia y decil de `in12`; concentración en las colas ⇒ artefacto.
- **F2 · Estacionalidad.** Pico de temporada leído como crecimiento. Comprobación: exigir yoy (mismo mes del año anterior) o índice estacional; disentir cuando no pase el yoy. Estimo que un tercio de los eventos actuales son estacionales.
- **F3 · One-off y financiación.** Comprobación: % del incremento explicado por una sola transacción/contraparte; >50 % ⇒ "crecimiento por one-off", separado.
- **F4 · Intragrupo mal excluido.** Comprobación: recomputar sobre `oper_in` (el panel ya separa `transfer_in`); discrepancias entre versiones = financiación del grupo o del accionista.

## 3. Eventos recomendados

| Evento | Definición implementable | Tipo | Preguntas | Frecuencia | Riesgos |
|---|---|---|---|---|---|
| **decline_limpio (ancla principal)** | Mediana de inflow m+1..m+6 < 50 % de la mediana de los 12 previos; excluye futuros apagados en ventana, base <9 meses, 2026-09 en la ventana (o prorrateado) y financiación identificable | Resultado | 3, 4, 6 | 17 % bruta medida; **estimo 10–13 % limpia** | Estacionalidad; one-off en la base |
| transicion_tension | Primer mes con meses-de-caja <0,25 o cash_end <0 tras ≥3 meses >0,5; innovación de reconstrucción limpia; excluye primeros 6 meses de vida y transiciones precedidas solo por caída de `transfer_in` | Transición | 3, 6 | **Estimo 6–10 %** | Drift; trimestre fiscal; dependencia del grupo |
| sobregiro_corroborado | Primer mes con cash_end <0 (o mínimo diario <0) con `interest_charge`/pico de `fee` o Δlc_drawn >0 en el mes ±1; el crónico ≥3 meses va a feature | Resultado | 1, 3, 4 | 5 % bruta medida; **estimo 2–4 % corroborado** | Las pólizas enmascaran (selección) |
| incumplimiento_observado | Obligación recurrente detectada **por importe** (mismo importe ±1 %, ≥4 repeticiones) que falta ≥1 periodo con `oper_in` estable; excluye empresas que se apagan ≤2 meses después | Resultado duro | 3, 5, 6 | **Estimo 3–6 %** | Categorías `-`; pagos fuera de plataforma; solo 87 cuadros de deuda |
| bache_vs_caida | Episodio de caída: rebote ≥70 % en ≤3 meses = bache; ≥4 de 6 meses bajos = caída; solo con ≥5 meses observables y empresa viva | Clasificación | 4 | **Estimo 40–60 % de los episodios son baches** | Censura derecha; solape con apagado |
| expansion_sostenida | `oper_in` ≥130 % yoy 2 meses seguidos + caja al alza sin subir `transfer_in`; cap de one-off (top contraparte <50 % del incremento) | Resultado positivo | 2 | 16 % bruta medida; **estimo 8–12 % limpia** | Base corta; intragrupo mal excluido |
| censura_plataforma (antes "apagado") | Sin movimientos hasta el final del dato; se reporta como churn de Embat, no como salud | Otro producto/KPI | — (monitor, retención) | 3 % medida | Es censura, no economía |

**Ancla principal:** `decline_limpio`, por cobertura y fiabilidad; `transicion_tension` como ancla de anticipación (pregunta 6) e `incumplimiento_observado` como evento duro de baja frecuencia para la explicación al jurado.

**Auditoría de los eventos propuestos.**
- *Incumplimiento*: **F1** — pago hecho pero en `-` (25 % de filas). Comprobación: tasa de "IVA omitido" contra share de `-` en pagos de la empresa; si escala, es artefacto. **F2** — expectativa IVA = 12m/4: si cae la facturación, "falta" sin incumplir. Comprobación: condicionar el flag a `oper_in` estable ±20 %; si >60 % de los flags tienen cobros cayendo, es un evento de actividad. **F3** — nómina: pagos fuera de plataforma, pagas extra (junio/diciembre). Comprobación: patrón calendario propio de `payroll` por empresa antes de marcar. **F4** — cuotas: solo 87 productos con cuadro; el pago puede salir de una cuenta no conectada (`settlement_product_id`). Comprobación: match entre `debt_repayment` observado y cuota/frecuencia esperada; match <70 % ⇒ no fiable, usar detección por importes recurrentes. **F5** — solape con apagado (la empresa que se apaga "omite" todo): excluir flags ≤2 meses antes del apagado.
- *Tensión*: **F1** — el denominador (gasto habitual max 3m/12m) salta en meses fiscales o con pagos intragrupo mal excluidos. Comprobación: recomputar excluyendo ene/abr/jul/oct y con innovaciones limpias; comparar tasas. **F2** — arranque con capital inicial: parece "buena situación" y normaliza después. Comprobación: tasa de transición contra antigüedad; excluir los primeros 4–6 meses. **F3** — mínimo intramensual con reconstrucción diaria: sensible a `date` vs `value_date` y `status=pending`. Comprobación: recalcular con value_date y solo booked; Jaccard/κ entre versiones; κ<0,6 ⇒ no fiable. **F4** — subsidiaria sostenida por el grupo: la tensión llega cuando el grupo deja de funds. Comprobación: % de transiciones precedidas por caída de `transfer_in` con `oper_in` estable.
- *Bache vs caída*: **F1** — censura derecha: cerca del final solo se ven 1–3 meses y todo parece bache. Comprobación: tasa de "caída" por meses hasta el borde; si cae al acercarse, exigir ≥5 meses observables. **F2** — apagados cuentan como persistencia baja: excluirlos. **F3** — mes parcial 2026-09 como mes bajo: mismo tratamiento que en decline.
- *Recuperación y sano sostenido*: **F1** — niegan eventos sucios (un drift que revierte parece recuperación). Comprobación: exigir que la mejora venga de `oper_in`, no solo de cash_end ni de `transfer_in` creciente. **F2** — sesgo de observabilidad: sin ERP o con mucho `-`, los eventos adversos no se detectan y todo parece sano. Comprobación: tasa de "sano sostenido" por `has_erp` y share de `-`; si es mayor donde menos se ve, gatear por calidad de dato (n_tx mínimo, cobertura). **F3** — exige 12 meses: excluye al 31 % con historia corta; declarar cobertura.

## 4. Críticas a la propuesta actual

- **"Incumplimiento" mezcla tres detecciones de fiabilidad distinta** (nómina, IVA, cuota) y depende de categorías y de una expectativa de IVA que confunde "factura menos" con "no paga". Tal como está, medirá actividad, no incumplimiento. La parte de cuotas cubre a un puñado de empresas (87 cuadros).
- **"Entrada en tensión" sin limpieza de drift ni exclusión del trimestre fiscal** producirá transiciones falsas en ene/abr/jul/oct y en empresas recién creadas.
- **"Caída estructural frente a bache" no tiene guarda de censura derecha ni exclusión de apagados**; el AUC 0,50 actual puede ser culpa de la etiqueta, no solo de las features.
- **"Recuperación" y "sano sostenido" heredan los falsos positivos de los eventos que niegan** y añaden sesgo de observabilidad: quien menos se ve sale más "sano".
- **El apagado debe salir de los denominadores de los demás eventos** (hoy infla la caída en 69 % de sus casos).
- **Riesgo sistémico:** calibrar contra etiquetas contaminadas enseña al modelo los artefactos (patrones de FX roto, `-`, censura). Que la logística y el LightGBM den el mismo AUC es consistente con etiquetas parcialmente mecánicas.

## 5. Cómo validarías los eventos sin etiquetas

1. **Triangulación de fuentes:** cada evento debe aparecer en ≥2 fuentes independientes (banco: `transactions`; ERP: `invoices`; deuda: flujos `debt_repayment`). Ej.: saldo negativo + `interest_charge` ese mes; caída de cobros + caída de `ar_issued` (subset ERP). Coincidencia medida con κ; **umbral propuesto κ ≥ 0,6**.
2. **Estabilidad bajo perturbación de la reconstrucción:** recalcular eventos (a) sin el 1 % de movimientos mayores, (b) solo `booked` y con `value_date`, (c) con FX validado, (d) sin internas. Tasa que se mueve >25 % o κ<0,6 ⇒ etiqueta no fiable (umbrales propuestos).
3. **Placebo temporal:** definir el mismo evento mirando al pasado; un artefacto de reconstrucción aparece igual en ambas direcciones, un fenómeno económico no.
4. **Gradiente dosis-respuesta:** tasa por tramos de señales exógenas al evento (meses de caja, uso de póliza, overdue). Sin orden monótono, sospecha de etiqueta rota antes que de feature mala.
5. **Estratificación por subpoblaciones propensas a artefacto:** divisa/FX, `has_erp`, share de `-`, antigüedad, tamaño. Ningún subgrupo debería aportar >30–40 % de los casos siendo <15 % de la muestra.
6. **Correlación intra-grupo:** 1.286 empresas en 250 grupos no son independientes; medir ICC de cada evento por `group_id` y calibrar con GroupKFold por grupo, o el AUC estará inflado.
7. **Reversión:** para caída y crecimiento, mirar meses 7–12 posteriores donde existan; lo que revierte era estacional o one-off.
8. **Fingerprint del generador:** distribuciones de fechas límite (último movimiento, última factura), tasas de salida por cohorte de alta, clusters de apagados por grupo. Cortes bruscos = censura de diseño.

## 6. Preguntas para la organización

1. ¿Las 121 empresas que dejan de tener movimientos se generaron con un estado de cierre explícito o es truncamiento del muestreo? ¿El generador tenía estados latentes de salud por empresa?
2. ¿Hasta qué día exacto llegan `transactions` e `invoices` de septiembre 2026? ¿Debe prorratearse?
3. ¿`cash_end` del panel suma todos los productos (checking, card, saving, investment) o solo corrientes? ¿Reconstrucción con `date` o `value_date`, y cómo se trataron los `pending`?
4. ¿Cómo aparecen en `transactions` las disposiciones de pólizas, factoring y préstamos (categoría, marcador en `description`, contraparte bancaria)? ¿Se puede separar financiación de cobro operativo?
5. ¿El 25 % de `category = '-'` es aleatorio o informativo (empresa, ERP, banco)?
6. ¿El generador simula desconexiones de ERP o de cuentas (huecos de datos no ligados a salud), con o sin reconexión?
7. ¿Permite descubiertos reales en checking, o todo saldo negativo es error de reconstrucción?
8. ¿Hay inyecciones de capital intragrupo y shocks comunes por grupo? ¿Con qué frecuencia?
9. ¿El test oculto comparte las mismas trampas (mes parcial, monedas rotas, `-`, censura)?

## 7. Verificaciones hechas

**Ninguna: en esta sesión no tengo acceso a los datos ni herramientas de ejecución.** Las cifras que marco como "medida" (tasas 3/5/17/16 %, solape 69 %, persistencia 46 %, imposibles 3 %, caja al salir 0,59 vs 0,48, AUC 0,77, solapamientos y AUC de Cursor Auto) provienen de los documentos del equipo (`brief_eventos.md`, `features.md`). Todo lo demás —frecuencias post-limpieza (10–13 %, 6–10 %, 2–4 %, 3–6 %, 8–12 %), umbral de κ ≥0,6, Δ<25 %, 30–40 % de concentración— son **estimaciones o criterios propuestos, no resultados**. El protocolo de comprobaciones de las secciones 2 y 3 queda especificado para ejecutarse en `/tmp` con polars sobre `research/data/*.parquet` y `research/data/panel.parquet`.