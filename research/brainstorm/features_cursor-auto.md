# Features nuevas propuestas (cursor-auto)

Evaluación contra `research/src/targets.py` → `add_events` (horizonte 6m) sobre `research/data/panel.parquet` y agregados causales de `transactions` / `invoices`. AUC: valor crudo de la feature prediciendo el evento (AUC>0,5 ⇒ valores altos ↔ más eventos). n = filas con feature y etiqueta no nulas. Cobertura = % de filas del panel con dato.

Eventos ancla (tasas aprox. en muestra evaluable): apagado ~3 %, saldo negativo ~5 %, caída de cobros ~17 %, crecimiento ~16 %, adverso = unión.

---

## 1. Irregularidad de nómina (`payroll_cv`)

1. **Preguntas:** 3, 5, 6 (se tuerce antes de que falte caja; señal laboral).
2. **Definición:** `panel.payroll`. Ventana 6 meses ≤ fin de m.  
   `payroll_cv = std(payroll_{m-5..m}) / (mean(payroll_{m-5..m}) + ε)` si mean>0; si no, nulo (no aplica).
3. **Hipótesis:** Si prestaras 100.000 €, una nómina que baila mes a mes suele anticipar recortes o cierre antes de que el saldo se vea vacío.
4. **Dirección:** más = peor. Cero/nulo = sin nómina observable (no aplica).
5. **Cobertura:** ~53 %. Riesgos: empresas sin `salary` categorizado; ruido si la categoría falla; no depende de ERP.
6. **Evidencia:** vs `churn_6m` AUC **0,689** (n=5.314): D0 1,9 % → D9 **6,8 %**. vs `adverse_6m` AUC 0,585: D0 15,8 % → D9 29,4 %.
7. **Prioridad:** alta. Coste: bajo (solo panel).

---

## 2. Impuesto trimestral omitido (`tax_miss`)

1. **Preguntas:** 3, 4, 5 (obligación recurrente que no aparece).
2. **Definición:** `panel.tax`, `month`. Solo en meses 1/4/7/10.  
   `expected = sum(tax, 12m) / 4`.  
   `tax_miss = max(0, expected − tax_m) / (expected + ε)` si expected > umbral de escala; si no, nulo.
3. **Hipótesis:** Si el IVA/seguridad fiscal “tocaba” y no sale el movimiento, o hay aplazamiento o hay estrés de caja que aún no se ve en el saldo.
4. **Dirección:** más = peor. Nulo fuera de mes fiscal o sin historial de tax.
5. **Cobertura:** ~20 % (solo meses fiscales con historial). Riesgo: empresas que pagan tax fuera de categoría o en otro mes; falso positivo si el calendario real no es trimestral ES.
6. **Evidencia:** vs `churn_6m` AUC **0,668** (n=1.960): cola D8–D9 **6,6–8,2 %** vs ~1–3 % en el resto. vs `cash_stress_6m` AUC 0,570.
7. **Prioridad:** alta (mejora la idea en cola de “obligaciones omitidas”). Coste: bajo.

---

## 3. Concentración de beneficiarios bancarios (`payee_concentration`)

1. **Preguntas:** 1, 3, 6 (sin ERP; dependencia de pocos pagos).
2. **Definición:** `transactions` con `amount<0` y `counterparty_id` no nulo; importe en moneda empresa (`amount/exchange_rate` validado). Por mes, HHI de |importe| por contraparte. Feature = media móvil 3m del HHI. Causal por `date ≤ fin(m)`.
3. **Hipótesis:** Pagar casi todo a una o dos contrapartes es fragilidad operativa (un proveedor/acreedor te apaga).
4. **Dirección:** más = peor. Nulo si no hay salidas con contraparte.
5. **Cobertura:** ~40 %. No ERP. Riesgo: contrapartes genéricas/nulas; internas si no se filtran (usar la misma lógica anti-interno del panel).
6. **Evidencia:** vs `churn_6m` AUC **0,753** (n=3.885): D0–D1 **0 %** → D7–D9 ~2–5 %. vs `decline_6m` AUC **0,606**: D0 9,5 % → D8 **32,4 %**.
7. **Prioridad:** alta. Coste: medio (agg mensual de tx).

---

## 4. Concentración de proveedores ERP (`hhi_ap_6m`)

1. **Preguntas:** 1, 3, 5.
2. **Definición:** `invoices` con `amount<0` (AP), `issuance_date` en ventana. HHI mensual del |importe| por `counterparty_id`; media 6m.
3. **Hipótesis:** Un solo proveedor grande que te deja de fiar anticipa tensión de pagos y de actividad.
4. **Dirección:** más = peor. Nulo sin ERP/AP.
5. **Cobertura:** ~52 % (ERP). Complementa HHI de clientes ya existente.
6. **Evidencia:** vs `churn_6m` AUC **0,676** (n=4.979): D9 **6,4 %** vs D0–D4 ~1 %. vs `decline_6m` AUC **0,618**: D0 9,8 % → D8 **28,3 %**.
7. **Prioridad:** alta. Coste: medio.

---

## 5. Persistencia de cobros operativos (`oper_persistence_6m`)

1. **Preguntas:** 2, 3, 4 (cara positiva y estructural).
2. **Definición:** `panel.oper_in`. `med12 = median(oper_in, 12m)`. Mes “ok” si `oper_in ≥ 0,5·med12`. Feature = media de ok en 6m.
3. **Hipótesis:** Cobrar de forma intermitente (meses en blanco respecto a la mediana) es deterioro estructural, no un mal mes.
4. **Dirección:** más = mejor. Cubre empresas sin ERP (usa categorías de cobro del banco).
5. **Cobertura:** ~76 %.
6. **Evidencia:** vs `decline_6m` AUC crudo 0,379 ⇒ **0,621 invertido** (n=8.261): D0 (poca persistencia) **35,1 %** caída vs D9 **12,0 %**. Separa bache/estructural: AUC **0,67** prediciendo `struct_drop` vs `temp_dip` cuando se invierte (baja persistencia ⇒ estructural).
7. **Prioridad:** alta. Coste: bajo.

---

## 6. Profundidad del aging AR (`ar_aging_deep`)

1. **Preguntas:** 3, 5, 6 (mejora la idea de tramos de deuda).
2. **Definición:** `panel.overdue_90_ar / (overdue_ar + ε)` si `overdue_ar>0`; si no, nulo o 0 según política.
3. **Hipótesis:** No es lo mismo tener facturas un poco vencidas que una cartera ya en >90 días: eso anticipa impagos y caída de cobros.
4. **Dirección:** más = peor. Nulo sin saldo vencido / sin ERP.
5. **Cobertura:** ~43 %.
6. **Evidencia:** vs `decline_6m` AUC **0,592** (n=3.980): D0 12,3 % → D9 **25,6 %**. vs `adverse_6m` AUC 0,585. vs `churn_6m` AUC 0,575.
7. **Prioridad:** alta. Coste: bajo (columnas ya en panel).

---

## 7. Profundidad del aging AP (`ap_aging_deep`)

1. **Preguntas:** 3, 5.
2. **Definición:** `overdue_90_ap / (overdue_ap + ε)` análogo.
3. **Hipótesis:** Estirar a proveedores hasta >90 días es señal de que se está financiando con el crédito comercial al límite.
4. **Dirección:** más = peor.
5. **Cobertura:** ~51 %.
6. **Evidencia:** vs `churn_6m` AUC **0,612** (n=4.673). vs `decline_6m` AUC **0,583**.
7. **Prioridad:** media-alta. Coste: bajo.

---

## 8. Aceleración de clientes perdidos (`lost_accel`)

1. **Preguntas:** 3, 6 (anticipa sobre `lost_share` estático).
2. **Definición:** `lost_share_m − lost_share_{m-3}` (panel, sticky forward ya aplicado en features).
3. **Hipótesis:** No solo cuántos clientes se fueron, sino si la hemorragia se está acelerando este trimestre.
4. **Dirección:** más = peor. Nulo sin ERP / sin historial 3m.
5. **Cobertura:** ~24 %. Solapa con feature 3 actual pero añade dinámica.
6. **Evidencia:** vs `churn_6m` AUC **0,737** (n=2.676): D0 0,4 % → D9 **7,8 %**. vs `decline_6m` AUC 0,582.
7. **Prioridad:** alta donde hay ERP. Coste: bajo.

---

## 9. Estrés multi-señal (`multi_signal_stress`)

1. **Preguntas:** 4, 5 (bache vs caída).
2. **Definición:** cuenta 0–4 de flags causales en m:  
   `growth_vs_12m < −0,2`; `activity_trend < −0,2`; `cust_trend < −0,2` (0 si nulo); `(cash_end − cash_{m-3}) / burn < −1`.
3. **Hipótesis:** Un solo golpe (caja o un mes malo) es bache; varias familias de señales a la vez es cambio de régimen.
4. **Dirección:** más = más estructural / peor. Cero = ninguna señal encendida.
5. **Cobertura:** ~81 %. Robusto sin ERP (3 de 4 flags no ERP).
6. **Evidencia:** vs `decline_6m` AUC **0,589** (n=8.239): 0 señales → 13,3 %; 3–4 señales → **~35 %**. Discriminación struct vs temp AUC **0,576**. Hoy el monitor de bache está en AUC~0,50: este contador es una base interpretable.
7. **Prioridad:** alta. Coste: bajo (reusa features actuales).

---

## 10. Shock puntual vs habitual (`shock_vs_usual`)

1. **Preguntas:** 4 (bache vs estructural).
2. **Definición:** Si `net_m < 0`: `|net_m| / (median(|net|, 6m) + ε)`; si net≥0, nulo o 0.
3. **Hipótesis:** Un agujero mucho mayor de lo habitual suele ser un pago puntual; un agujero “normal” repetido es el nuevo suelo.
4. **Dirección:** entre meses negativos, más shock ⇒ más bache (mejor prognosis estructural). Cero/nulo si no hay mes negativo.
5. **Cobertura:** ~45 % (solo meses netos negativos).
6. **Evidencia:** vs `decline_6m` AUC 0,428 ⇒ **0,572 invertido** (n=4.460): D0 (shock pequeño = deterioro “normal”) **30 %** caída vs D8 **11,4 %**. Encaja con la hipótesis de bache; la separación binaria temp/struct aislada queda ~0,50 (pocos temp_dip etiquetados), pero el gradiente sobre decline es claro.
7. **Prioridad:** alta para el problema abierto “bache”. Coste: bajo.

---

## 11. DPO realizado (`dpo_3`)

1. **Preguntas:** 1, 3, 5 (días que tarda en pagar; lenguaje consumidor).
2. **Definición:** Facturas AP con `payment_date` en m, `status` efectivamente cobrada/pagada (`pending≈0`, no fiarse de `payment_date` en overdue), `days_to_pay = payment_date − issuance_date` ∈ [−30, 365]. Mediana mensual; media 3m.
3. **Hipótesis:** Alargar de verdad el plazo de pago a proveedores es vivir del crédito comercial.
4. **Dirección:** más = peor (en pymes estresadas). Nulo sin ERP.
5. **Cobertura:** ~50 %. Cuidado con fechas imposibles (filtrar años).
6. **Evidencia:** vs `churn_6m` AUC **0,641** (n=4.542). vs `cash_stress_6m` AUC 0,572.
7. **Prioridad:** media-alta. Coste: medio.

---

## 12. Tendencia de DSO (`dso_trend`)

1. **Preguntas:** 3, 5, 6.
2. **Definición:** Igual que DPO pero AR; `dso_3 − dso_12` (días).
3. **Hipótesis:** Si los clientes empiezan a pagar más tarde, la caja futura se resiente antes que el saldo actual.
4. **Dirección:** más = peor.
5. **Cobertura:** ~35 %.
6. **Evidencia:** vs `churn_6m` AUC 0,545 (débil). vs `decline_6m` ~0,49 (sin orden claro en deciles). **Parcialmente comprobada**; mejor como explicación/driver que como peso fuerte.
7. **Prioridad:** media. Coste: medio.

---

## 13. Tendencia de DPO (`dpo_trend`)

1. **Preguntas:** 3, 5.
2. **Definición:** `dpo_3 − dpo_12`.
3. **Hipótesis:** Empezar a pagar cada vez más tarde anticipa estrés aunque el late_share aún no salte.
4. **Dirección:** más = peor.
5. **Cobertura:** ~42 %.
6. **Evidencia:** vs `cash_stress_6m` AUC **0,532**. Señal modesta pero alineada.
7. **Prioridad:** media. Coste: medio.

---

## 14. Pago anticipado a proveedores (`ap_early_3`)

1. **Preguntas:** 1, 4 (ambigua: solidez vs quema de caja).
2. **Definición:** Entre AP pagadas en la ventana 3m con due válido, % con `payment_date < due_date`.
3. **Hipótesis:** Pagar siempre antes de vencimiento puede ser disciplina… o quemar buffer; hay que leerlo junto a runway.
4. **Dirección:** interactiva (ver top 5). Crudo: más early ↔ más `cash_stress` en los datos.
5. **Cobertura:** ~50 %.
6. **Evidencia:** vs `cash_stress_6m` AUC **0,629** (n=4.341): D1 ~2,6 % → D9 **10,2 %**. Interpretación: early extremo predice estrés de caja (sacan dinero antes de tiempo), no “salud”. Para el score: penalizar early alto **si** runway bajo.
7. **Prioridad:** media (como interacción). Coste: medio.

---

## 15. Facturación vs cobro (`billing_to_cash`)

1. **Preguntas:** 3, 5.
2. **Definición:** `sum(ar_issued, 3m) / (sum(oper_in, 3m) + ε)` si `has_erp`.
3. **Hipótesis:** Facturar mucho y cobrar poco hincha AR; el inverso (cobrar sin facturar) también es raro. Lo crítico en datos: ratios **muy bajos** (poco issue vs cobro bancario) asocian a apagado — posible desconexión ERP o actividad fantasma.
4. **Dirección:** extremos malos; el orden monótono favorece “más bajo = peor” para churn.
5. **Cobertura:** ~55 %.
6. **Evidencia:** vs `churn_6m` AUC crudo 0,339 ⇒ **0,661 invertido** (n=4.970): D0–D1 **4,6–8,6 %** churn vs ~1 % en deciles medios/altos.
7. **Prioridad:** media. Coste: bajo.

---

## 16. Tendencia de pagadores entrantes (banco) (`bank_cp_in_trend`)

1. **Preguntas:** 2, 3, 6 (amplitud de clientes sin ERP).
2. **Definición:** `n_cp_in` = nº `counterparty_id` distintos en entradas del mes.  
   `log((mean_3m + 1)/(mean_12m + 1))`.
3. **Hipótesis:** Perder diversidad de quien te ingresa anticipa caída de cobros aunque el importe aún aguante por un cliente grande.
4. **Dirección:** más = mejor.
5. **Cobertura:** ~85 %. Sustituto de `cust_trend` sin ERP.
6. **Evidencia:** vs `decline_6m` AUC 0,451 ⇒ **0,549 invertido** (n=8.158): D0 **22,4 %** vs D8–D9 **~12,5 %**.
7. **Prioridad:** alta (cobertura). Coste: medio.

---

## 17. Δ runway 3m (`runway_delta_3m`)

1. **Preguntas:** 2, 3, 5 (trayectoria de “meses de sueldo en cuenta”).
2. **Definición:** `runway_m − runway_{m-3}` (misma definición de runway que `features.py`).
3. **Hipótesis:** La velocidad a la que se acortan los meses de caja importa más que el nivel (criticidad del brief).
4. **Dirección:** más = mejor para deterioro; cuidado con reversión a la media en el evento `positive_6m`.
5. **Cobertura:** ~81 %.
6. **Evidencia:** vs `decline_6m` AUC **0,553** (subir runway ↔ más decline es débil/mean-revert en cola). vs `positive_6m` AUC 0,421 ⇒ **0,579 invertido**: quien ya mejoró runway crece menos hacia el evento “growth” (definición exigente). Mejor usarla como **driver de trayectoria/alerta**, no como peso lineal al evento growth. vs `adverse_6m` AUC 0,542.
7. **Prioridad:** media (producto/explicación). Coste: bajo.

---

## 18. Δ caja / burn 6m (`cash_delta_6m`)

1. **Preguntas:** 2 (cara positiva de tendencia de caja; idea en cola).
2. **Definición:** `(cash_end_m − cash_end_{m-6}) / burn_m`.
3. **Hipótesis:** Recapitalizarse de forma sostenida es la cara Northbrook; vaciarse en 6m es Velasco.
4. **Dirección:** más = mejor para salud de nivel; el evento `positive_6m` muestra mean-reversion (AUC 0,413).
5. **Cobertura:** ~64 %.
6. **Evidencia:** Orden claro en deciles para positive pero **invertido** respecto a la intuición del evento (D0 23,5 % growth vs D9 10,3 %): el label premia a quien aún no ha subido caja. Contra `decline_6m` AUC 0,544 (más delta ⇒ más decline) — también mean-reversion. **Comprobada como señal de régimen/mean-reversion**, no como “más caja ⇒ más growth label”. Para score de nivel, combinar con persistencia.
7. **Prioridad:** media. Coste: bajo.

---

## 19. Asimetría de volatilidad (`vol_asymmetry`)

1. **Preguntas:** 2, 4.
2. **Definición:** `down_vol = net_vol_6m` (ya existe). `up_vol = rms(max(net,0), 6m) / burn`.  
   `vol_asymmetry = down_vol / (down_vol + up_vol)`.
3. **Hipótesis:** Solo hay volatilidad a la baja cuando los meses buenos no compensan: peores colas; en este dataset también marca empresas que luego rebotan (mean-reversion del label positive).
4. **Dirección:** ambigua según uso: alto = más riesgo de cola negativa, pero AUC 0,606 vs `positive_6m` (rebote).
5. **Cobertura:** ~87 %.
6. **Evidencia:** vs `positive_6m` AUC **0,606** (n=8.248): D0 8,1 % → D9 **25,8 %**. vs `adverse` ~0,49. Útil en un modelo de dos caras / rebote, no como “siempre malo”.
7. **Prioridad:** media. Coste: bajo.

---

## 20. Continuidad de nómina (`payroll_continuity_6m`)

1. **Preguntas:** 2, 3, 4.
2. **Definición:** media en 6m de `1{payroll_m > 0}`.
3. **Hipótesis:** Seguir pagando nómina en meses flojos es señal de continuidad; cortar nómina anticipa apagado.
4. **Dirección:** más = mejor. Nulo/no aplica si la empresa nunca tuvo payroll en historia (distinguir de continuity=0).
5. **Cobertura:** ~88 % numérica; interpretabilidad exige “algún payroll histórico”.
6. **Evidencia:** vs `churn_6m` AUC 0,341 ⇒ **0,659 invertido**: continuity alta (D9) **1,0 %** churn vs ~5 % cuando es intermitente. Discriminación struct vs temp AUC 0,58 (más continuity ↔ más structural en el pool adverso — matiz: las estructurales “grandes” siguen pagando un tiempo; usar junto a persistence de cobros).
7. **Prioridad:** media. Coste: bajo.

---

## 21. YoY de cobros (`yoy_inflow`)

1. **Preguntas:** 2, 3, 4 (ajusta estacionalidad mejor que 3 vs 12).
2. **Definición:** `(inflow_m − inflow_{m-12}) / (|inflow_{m-12}| + ε)`.
3. **Hipótesis:** Caer respecto al mismo mes del año pasado no es “enero de impuestos”: es deterioro real.
4. **Dirección:** más = mejor.
5. **Cobertura:** ~30 % (hace falta 12m+). OOD en empresas nuevas.
6. **Evidencia:** vs `decline_6m` AUC 0,379 ⇒ **0,621 invertido** (n=2.524): D0 **41,3 %** vs D5–D7 ~11 %. Fuerte donde hay historia.
7. **Prioridad:** alta si `month_idx≥12`; else skip. Coste: bajo.

---

## 22. Transferencias sustituyendo operación (`transfer_replacing_ops`)

1. **Preguntas:** 3, 5.
2. **Definición:** `transfer_dep × (1 − oper_share)` con ventanas 3m ya del scorer.
3. **Hipótesis:** Vivir de transferencias cuando los cobros operativos se encogen es pedirle dinero al grupo/accionista para tapar el agujero.
4. **Dirección:** más = peor.
5. **Cobertura:** ~100 %.
6. **Evidencia:** vs `decline_6m` AUC ~0,48 (débil en univariante). Mantener como **interacción explicable**; no como peso solo.
7. **Prioridad:** baja-media. Coste: bajo.

---

## 23. Intensidad de comisiones (`fee_intensity`)

1. **Preguntas:** 3, 5.
2. **Definición:** `sum(fees, 3m) / (sum(outflow, 3m) + ε)`.
3. **Hipótesis:** Pico de fees (descubiertos, reclamaciones, cambio de condiciones) aparece antes en el extracto que un saldo negativo sostenido.
4. **Dirección:** más = peor; cola baja también rara (AUC no monótona).
5. **Cobertura:** 100 %.
6. **Evidencia:** vs `churn_6m` AUC 0,417 ⇒ **0,583 invertido** con forma en U en deciles (D1 y D9 altos). **⚠️ orden no monótono** — mejor como alerta de cola o binaria “fee spike”.
7. **Prioridad:** baja (spike relativo a mediana 12m sí aportó en tests cualitativos). Coste: bajo.

---

## 24. Deuda nueva mientras drena caja (`debt_while_draining`)

1. **Preguntas:** 3, 5 (pedir prestado para tapar el agujero).
2. **Definición:** Si `cash_end_m < cash_end_{m-3}`: `sum(granted de debt_products con created_at en 3m) / (in3 + ε)`; si no, 0. **No usar `outstanding` histórico** (foto final no causal).
3. **Hipótesis:** Nueva financiación con caja cayendo es la analogía “vive de la tarjeta”.
4. **Dirección:** más = peor.
5. **Cobertura:** evento raro (muchas filas a 0). `created_at` de deuda es usable; importes `granted` ok.
6. **Evidencia:** univariante vs eventos ~0,50 (poca densidad). **No comprobada** en AUC; hipótesis de producto fuerte.
7. **Prioridad:** media como flag binario en demo. Coste: bajo-medio.

---

## 25. Runway vs grupo (`runway_vs_group`)

1. **Preguntas:** 1, 5 (contexto de grupo empresarial).
2. **Definición:** `runway_m − median(runway | group_id, month)`.
3. **Hipótesis:** La filial seca dentro de un grupo líquido es la que apagas o la que el grupo deja caer.
4. **Dirección:** más = mejor relativo.
5. **Cobertura:** ~99 %. Fuga: el grupo mediana usa peers del mismo mes (ok causal). No filtrar la propia empresa en grupos de 1.
6. **Evidencia:** discriminación struct/temp AUC ~0,43 (invertido ~0,57). Univariante débil; útil como contexto/OOD de grupo.
7. **Prioridad:** baja-media. Coste: bajo.

---

## 26. Ciclo de conversión proxy (`cash_conversion_proxy`)

1. **Preguntas:** 1, 5.
2. **Definición:** `dso_3 − dpo_3` (días).
3. **Hipótesis:** Cobrar tarde y pagar pronto quema caja de trabajo; lo contrario la financia.
4. **Dirección:** más = peor.
5. **Cobertura:** ~42 %.
6. **Evidencia:** vs `cash_stress_6m` AUC 0,518 (débil/no monótono). **No comprobada** de forma limpia.
7. **Prioridad:** baja. Coste: medio (requiere DSO/DPO).

---

## Top 5 razonado

| # | Feature | Por qué |
|---|---|---|
| 1 | `payee_concentration` | Mejor AUC de apagado sin ERP (0,75); señal que el score actual no tiene (solo HHI de clientes facturados). |
| 2 | `payroll_cv` | Anticipa churn/adverse con cobertura decente y frase de jurado trivial (“la nómina les baila”). |
| 3 | `oper_persistence_6m` | Ataca a la vez caída de cobros y bache/estructural; funciona sin facturas. |
| 4 | `multi_signal_stress` + `shock_vs_usual` | Par explícito para la pregunta 4 (hoy AUC~0,50): amplitud de régimen vs tamaño del golpe puntual. |
| 5 | `hhi_ap_6m` / `ar_aging_deep` | Donde hay ERP, cierran el lado proveedores y el aging profundo que el late_share plano no separa. |

Menciones de honor: `tax_miss` (alta precisión en meses fiscales), `bank_cp_in_trend` (cust_trend sin ERP), `yoy_inflow` (cuando hay ≥12m), `lost_accel` (dinámica sobre lost_share).

---

## Cómo combinar (interacciones, umbrales, regímenes)

1. **Régimen bache vs estructural (pregunta 4)**  
   - Si `shock_vs_usual` alto **y** `multi_signal_stress ≤ 1` **y** `oper_persistence_6m` alto → etiquetar **bache**.  
   - Si `multi_signal_stress ≥ 2` **o** `oper_persistence_6m` bajo **o** `yoy_inflow` << 0 → **estructural**.  
   - Producto: no bajar el score 20 puntos en un bache; sí disparar vigilancia.

2. **Criticidad de caja (scoring.md)**  
   - `runway_delta_3m` (o burn de caja intradía cuando exista) con peso alto solo si además `multi_signal_stress≥1`.  
   - Evitar mean-reversion: no premiar `cash_delta_6m` alto como “growth”; usarlo como nivel/trayectoria, y el growth label con `activity_trend` + `oper_persistence` + `bank_cp_in_trend`.

3. **Early AP × runway**  
   - `ap_early_3` alto ∧ runway bajo → penalización fuerte (“pagan pronto con la cuenta justa”).  
   - `ap_early_3` alto ∧ runway alto → neutro o leve positivo (disciplina).

4. **Concentración dual**  
   - `max(payee_concentration_pctil, hhi_ap_6m_pctil, hhi_ar_6m_pctil)` como “dependencia de contraparte” única en la explicación.

5. **Obligaciones omitidas**  
   - Flag = `tax_miss` alto ∨ (payroll_continuity cae ∧ payroll_cv sube) ∨ (debt_service esperado ausente, idea en cola).  
   - Alimenta alerta proactiva con lead time, no el score base.

6. **Dos caras del score**  
   - Cara negativa: concentración, payroll_cv, aging deep, lost_accel, tax_miss.  
   - Cara positiva: oper_persistence, bank_cp_in_trend, yoy_inflow>0, payroll_continuity, (opcional) upside_vol sin asimetría extrema.  
   - No mezclar en un único percentil lineal señales con mean-reversion fuerte (`cash_delta_6m` vs `positive_6m`).

7. **Sin ERP / historia corta**  
   - Priorizar: payee_concentration, bank_cp_in_trend, oper_persistence, payroll_cv, multi_signal_stress, shock_vs_usual.  
   - Aparcar: aging, HHI AP, DSO/DPO, lost_accel, tax_miss.

---

## Notas de método

- Scripts auxiliares solo en `/tmp` (`feature_eval_panel.txt`, `feature_eval_tx.txt`, `feature_eval_extra.txt`, `feature_deciles_final.txt`); ningún otro fichero del repo modificado.
- Labels de `temp_dip` / `struct_drop` son proxies internos (dip: estrés corto de caja con recuperación y sin `decline_6m`); n_temp es bajo (~119), así que la discriminación bache/estructural debe validarse también cualitativamente en la demo.
- `outstanding` de `debt_products` y balances finales no se usaron como series históricas (no causales).
- Las 17 features actuales no se re-proponen; varias de esta lista son **derivadas dinámicas** o **simétricas** (proveedores, banco sin ERP, calendario, régimen).
