# Auditoría de datos: ¿qué eventos son verdad usable?

**Lente:** auditor de datos escéptico con acceso a `research/data/*.parquet` y a `research/src/targets.py`.  
**Fecha:** 2026-09-19. Scripts solo en `/tmp` (no se ha tocado el resto del repo).  
**Muestra:** ≥8 empresas por evento (actuales y propuestos), con historia mensual alrededor del evento.

---

## 1. Posición

Los cuatro eventos actuales **no son una verdad de salud financiera**: son proxies observables con tasas de contaminación altas. El **apagado** es, en más de la mitad de los 121 casos, desconexión / borde del panel (jul-2026) o corte con caja positiva; solo ~12 % parece cierre con deterioro. La **caída de cobros** hereda ese ruido (solapamiento mecánico con apagado ~76 % a nivel empresa-apagada; ~28 % de las no-apagadas se recuperan después). El **saldo negativo** es el más cercano a un hecho de tesorería, pero el 37–47 % de los flags no son *entradas* sino persistencia / póliza / caja≈0 de passthrough. El **crecimiento** revierte en ~27 % de los casos. **No calibraría el score ancla contra apagado ni contra decline tal cual.** Anclaría en una **transición de tensión de caja persistente** más un **incumplimiento recurrente estricto** (nómina/cuota, no IVA suelto), y trataría apagado y caída de cobros como cobertura / síntomas.

---

## 2. Veredicto sobre cada evento actual

| Evento | Veredicto | Motivo empírico |
|---|---|---|
| **Apagado** (`churn_6m`) | **Separar como otro producto** (baja Embat / observabilidad), no ancla de salud | 121 empresas; 44 (36 %) último mes = jul-2026 (borde); 94/119 con caja > 0 al callar; 33/121 siguen emitiendo facturas ERP tras silencio bancario; 28/119 apagan cuentas escalonadas; solo 15/121 clasifican como cierre plausible en reglas duras. Tasa mes-elegible 3,0 % (248/8261). |
| **Saldo negativo** (`cash_stress_6m`) | **Redefinir** como *entrada* (no “algún mes futuro < 0”) + exigir persistencia o no cobertura por póliza | Tasa 5,4 %. 213 empresas alguna vez en negativo. En el onset del flag, 37,5 % ya venían en negativo (3m previos); 46,6 % tuvieron negativo *alguna vez* antes. Persistencia >3 meses: 53 %. Con póliza: 16 %. Implausibles (>50× volumen): 1,9 %. AUC alto vs runway es en parte circular. |
| **Caída de cobros** (`decline_6m`) | **Degradar a feature / síntoma** | Tasa 17 %. 348 empresas. El 76 % de las apagadas también “caen”; el 20 % de las decline son apagadas. Tras quitar apagados, el 28 % recupera ≥80 % de la mediana base en los 6 meses *posteriores* al horizonte → bache/estacionalidad. ~16 % de meses-decline tienen ≥3 meses sin tx o post-final en el horizonte. |
| **Crecimiento** (`positive_6m`) | **Mantener solo como estado positivo auxiliar**, no simétrico del riesgo | Tasa 16 %. 437 empresas. ~27 % revierten a la media tras el horizonte. Dominio operativo en 318/437; transfer-dominado solo 26. Útil para pregunta “quién mejora”, malo como anti-label de calibración adversa. |

**Falsos eventos estimados (por tipo, población + reglas):**

| Tipo | % artefacto claro | % ambiguo | % evento real usable | Comentario |
|---|---:|---:|---:|---|
| Apagado | **~52 %** | ~36 % | **~12 %** | Si se suma ½ ambiguo → “falso-ish” ~70 % |
| Saldo negativo | **~2 %** (implausible) | **~41 %** (crónico / póliza / ≈0) | **~57 %** | Falso *como transición de estrés*: ~40–50 % |
| Caída cobros | **~42 %** (apagado + recuperación) | resto mixto | **~40–50 %** | Tras filtrar apagado, aún ~28 % bache |
| Crecimiento | **~27 %** (reversión) | ~20 % (historia corta / uncat) | **~50–55 %** | Menos tóxico que decline, no ancla |

---

## 3. Eventos recomendados

| Nombre | Definición implementable | Tipo | Preguntas del reto | Frecuencia medida / est. | Riesgos | Rol |
|---|---|---|---|---|---|---|
| **Entrada en tensión de caja (persistente)** | Tras ≥3 meses con `cash_end/burn ≥ 0,5` y `cash_end ≥ 0`, primer mes con `cash_end < 0` **o** `cash_end/burn < 0,25`, y el estrés se mantiene ≥2 de los 3 meses siguientes. `burn = max(out3/3, out12/12)`. Excluir si `\|cash_end\| > 50·gross_flow` o si `lc_limit` cubre el hueco y no hay deterioro de cobros. | Transición | 3, 4, 5, 6 | Mes-elegible cruda ~3,0 % (347 empresas, 27 % ever). Tras filtro persistencia: chronic 3m ~27 % de entradas; bounce ~26 % → **usable ~1,5–2 % mes / ~15–20 % ever** | Reconstrucción de saldos; mes parcial ago-2026; burn que cae infla runway | **Ancla principal** |
| **Incumplimiento recurrente (estricto)** | (a) Nómina: `pay_prev6_nz ≥ 4` y `payroll(m)=0` con `n_tx≥5` y `outflow>0`; o (b) cuota: `debt_prev6_nz ≥ 4` y `debt_service(m)=0` con historial estable; **no** contar IVA solo. Opcional: `overdue_90_ap` sube >50 % vs m−3 y supera 0,5·out12 (solo `has_erp`). | Resultado | 3, 4, 5, 6 | Mes: pay 3,4 %, debt 5,2 %, tax 2,2 %, ap90 6,6 %, any 16 %. Forward-6m any **33 %** (demasiado). Estricto pay∨debt estim. **~5–8 % mes / ~15–25 % ever** | Categoría `-`; vacaciones; desconexión; ERP sucio en overdue | Ancla secundaria / co-target |
| **Caída estructural de cobros** | Mediana `inflow` 6m futuros < 50 % mediana 12m **y** empresa sigue activa (`months_since_final_tx==0` todo el horizonte) **y** mediana 6m *post*-horizonte < 80 % base | Síntoma / resultado | 2, 4, 5 | Decline crudo 17 %; tras filtros ~**8–12 %** | Estacionalidad fiscal; uncat | Feature + label auxiliar |
| **Apagado / baja de cobertura** | Último mes con tx; etiquetar `disconnect` si caja>0 y (cuentas escalonadas ∨ ERP activo post-silencio ∨ gap_to_end≤1 en jul-2026); `closure_suspect` si fade+síntomas | Cobertura / producto Embat | 1, 5 (con caveat) | 121 empresas; disconnect mayoría | Borde ago-2026 | Producto retención, **no** calibración salud |
| **Recuperación sostenida** | Tras tensión o incumplimiento, 3 meses fuera de estrés y sin miss | Estado positivo | 2 | Est. baja (pocos) | Media-reversion | Demo / pregunta 2 |
| **Sano sostenido** | 12m sin tensión, sin miss estricto, activo | Estado positivo | 1 | Est. 30–40 % empresas con historia larga | Supervivencia | Pregunta 1 |

**Ancla principal:** entrada en tensión de caja **persistente** (no el `cash_stress_6m` actual).  
**Co-ancla:** incumplimiento de nómina/cuota (sin IVA suelto).  
**Caída de cobros** y **apagado** fuera del target de pesos del score de salud.

---

## 4. Críticas a la propuesta actual

1. **“Incumplimiento” tal como se esboza es demasiado ancho.** Con una implementación generosa (nómina ∪ cuota ∪ IVA ∪ AP90), el **33 %** de los meses elegibles tienen un miss en los 6 meses siguientes y el **54 %** de las empresas lo tienen alguna vez: no discrimina; calibrar contra eso empuja el score a “todo el mundo incumple”. Hay que **estrechar** (regularidad ≥4/6, actividad mínima, excluir IVA o exigir 2 trimestres seguidos).
2. **“Entrada en tensión” sin persistencia** captura baches (COMP_0779, COMP_0818: un mes malo y rebote con entrada grande). El brief ya lo intuye; hay que **codificar el ≥2/3 meses** en la etiqueta, no solo en la narrativa.
3. **Separar apagado está bien** — los datos lo exigen — pero hay que **dejar de meterlo dentro de `adverse_6m`** (`targets.py` hoy hace `churn | decline | cash`). Mientras el adverso incluya apagado, los pesos seguirán premiando señales de desconexión (p. ej. concentración de payees / lost_accel altas vs churn).
4. **“Caída estructural vs bache”** no está en el código; decline actual **no** exige actividad continua ni no-recuperación. Sin eso, degradar decline a feature es correcto; promocionarlo a evento sin filtros no.
5. **“Recuperación” / “sano sostenido”** son útiles para producto y pregunta 1–2, pero **no deberían compartir peso de calibración** con el ancla adversa (desbalance y asimetría).
6. La propuesta **no ataca la circularidad** del saldo negativo con runway: hay que evaluar el ancla de tensión con features **que no sean transformaciones del mismo `cash_end`**, o aceptar que liquidez predice liquidez y medir valor incremental.

---

## 5. Cómo validaría los eventos sin etiquetas

1. **Auditoría de casos** (esta): ≥20–50 por tipo, clasificación real / artefacto / ambiguo; publicar tasa de contaminación.
2. **Contraste de mecanismos:** cuentas que mueren a la vez vs escalonadas; ERP post-silencio; borde jul/ago-2026; saltos `Δcash − net` en reconstrucción.
3. **Persistencia / no-reversión:** exigir que el evento no se deshaga en 3 meses (tensión, decline, miss).
4. **Independencia de cobertura:** correlación del evento con `has_erp`, meses de historia, nº productos, % uncat; si AUC vs evento se explica solo por cobertura → no es salud.
5. **Splits por `group_id`** y por ventana temporal (train hasta 2025-12, val 2026) para ver si el evento es estable o un artefacto de borde.
6. **Consistencia entre señales:** un “cierre real” debería acumular decline + tensión + miss; un “disconnect” no.
7. **Juicio humano Embat** sobre 30 casos anonimizados (¿baja de producto o quiebra?) — única etiqueta semi-gold posible en el hackathon.

---

## 6. Preguntas para la organización

1. En el test oculto, ¿el “apagado” (dejar de conectar bancos) debe **penalizar** el score de salud o tratarse como **missing / baja de producto**?
2. ¿Los saldos negativos con **póliza dispuesta** cuentan como estrés o como uso normal de circulante?
3. ¿Hay **etiquetas** o proxy externos (impagos, defaults, bajas Embat) fuera de los CSV?
4. Scoring a nivel **`company_id` o `group_id`**? Un apagado de filial con matriz viva cambia el producto.
5. ¿El mes de **septiembre 2026** entra en evaluación o solo hasta agosto completo?
6. Para “incumplimiento”, ¿Embat tiene reglas internas de detección de nómina/IVA omitidos que debamos imitar?

---

## 7. Verificaciones hechas (datos)

Código: `targets.add_events` sobre panel enriquecido con `features.add_features`. Tasas mes-elegibles reproducidas: churn 3,0 %, cash_stress 5,4 %, decline 17,0 %, positive 16,3 %, adverse 22,3 %.

### 7.1 Apagado — ¿cierre o desconexión?

**Población:** 121 empresas con último mes activo < 2026-08.

| Señal | Dato |
|---|---|
| Último mes = jul-2026 | **44/121 (36 %)** |
| Último mes ∈ {jun, jul}-2026 | **60/121 (50 %)** |
| Caja > 0 al callar | **94/119 (79 %)** |
| Caja ≤ 0 al callar | **11/119 (9 %)** |
| Runway mediano al último activo | **0,59 meses** (coincide con el brief); >3 meses: 25 %; ≤0: 10 % |
| Facturas ERP **después** del silencio bancario | **33/121 (27 %)** → no es liquidación total |
| Cuentas: muerte simultánea (últimas tx ≤14d) | **79/119 (66 %)** |
| Cuentas escalonadas (span >90d y <70 % cerca del final) | **28/119 (23 %)** |
| Una sola cuenta | **63/119 (53 %)** |
| `n_tx`: plano y luego cero | **64/119 (54 %)** |
| `n_tx`: fade | 35; cliff | 20 |
| Clasificación poblacional (reglas) | artefacto 63, ambiguo 43, real 15 → **52 % / 36 % / 12 %** |

**Conclusión apagado:** predominan **corte en seco o fade con caja sana**, a menudo **cerca del borde** o con **ERP que sigue**. Las cuentas **a veces** se van una a una (23 %), pero lo más frecuente es **corte conjunto** o empresa mono-cuenta. Eso encaja con **desconexión Embat / fin de feed**, no con quiebra ordenada. Los movimientos **no** suelen “morirse de hambre” mes a mes hasta cero con síntomas: en 54 % el volumen del último mes sigue alto respecto a la media reciente y luego hay silencio absoluto.

#### Casos (≥8)

| company_id | Último activo | Patrón | Cuentas | Clasificación | Historia (resumen) |
|---|---|---|---|---|---|
| **COMP_1046** | 2025-12 | fade | 5→2 | **evento_real** | n_tx 135→89→61→60→29→34; caja ~2,4k; actividad se apaga con merma clara; silencio total 2026 |
| **COMP_0624** | 2025-11 | fade+escalonado | 3→2 | **artefacto** | n_tx ~700–900 luego 316; **caja 126k** al callar; productos escalonados → desconexión |
| **COMP_0503** | 2026-02 | fade+escalonado | — | **artefacto** | n_tx 627, luego 0,0,0,0,2; **caja 1,03M** |
| **COMP_0966** | 2026-07 | sudden / borde | — | **artefacto** | n_tx 99…43; **caja 489k**; último mes = borde dataset |
| **COMP_1259** | 2026-07 | sudden / borde | — | **artefacto** | sin síntomas; gap=1 |
| **COMP_0166** | 2026-07 | sudden / borde | — | **artefacto** | n_tx sube a 37 en el último mes y calla → feed cortado |
| **COMP_0889** | 2026-05 | fade | 1 cuenta | **ambiguo** | cobros ~2M → 306k en mayo y silencio; sin `cash_end` usable |
| **COMP_0715** | 2026-01 | sudden_stop | 1 | **ambiguo** | n_tx 2…13 y corte; historia corta |
| **COMP_0325** | 2026-04 | cliff débil | 1 | **ambiguo** | 1 tx/mes de ~30 € drenando caja 124→36; “zombie” de comisiones |
| **COMP_0771** | 2026-06 | fade | 1 | **evento_real?** | n_tx 15→4; caja 123k→85k; posible cierre o recorte — sin ERP |
| **COMP_0223** | 2025-12 | sudden | 2 | **ambiguo** | actividad irregular; caja 6,4k queda congelada |
| **COMP_0938** | 2025-09 | fade | 1 | **evento_real?** | n_tx 10→2; silencio largo (11m) |

### 7.2 Saldo negativo

**Población:** 213 empresas con algún `cash_end < 0`. Flag `cash_stress_6m`: 88 empresas con al menos un mes positivo.

| Señal | Dato |
|---|---|
| Ya negativo en 3m previos al flag | **37,5 %** |
| Negativo *alguna vez* antes del flag | **46,6 %** |
| >3 meses negativos (empresa) | **53 %** |
| Con póliza (`lc_limit>0`) | **16 %** |
| \|min cash\| > 50× gross medio | **1,9 %** |
| Entradas reales ≥0→<0 (meses) | 220 meses / 141 empresas |

#### Casos (≥8)

| company_id | Primer neg | n_neg | Clasificación | Historia |
|---|---|---|---|---|
| **COMP_0741** | 2026-05 | 1 | **evento_real** | Caja 312k→12k→**−2,4k**→35k→235k; un mes de tensión breve y recuperación |
| **COMP_0191** | 2026-07 | 1 | **evento_real** | Entrada puntual cerca del borde |
| **COMP_0712** | 2024-10 | 1 | **evento_real** | Breve |
| **COMP_0169** | 2024-09 | 21 | **ambiguo (póliza)** | Negativo crónico ~−200k con actividad fuerte y LC; en 2026-06 vuelve a +159k — **modo línea de crédito**, no “evento” |
| **COMP_0970** | 2026-04 | 1 | **ambiguo (póliza)** | −22k un mes, rebound a +109k |
| **COMP_0894** | 2025-04 | 9 | **artefacto/ambiguo** | Flujos 2–20M/mes y **caja ≈ 0 siempre** (passthrough / reconstrucción); “negativo” numérico sin significado |
| **COMP_0613** | 2025-01 | 11 | **ambiguo** | Oscila −1,4k / +12k; estrés crónico leve, no transición |
| **COMP_0050** | 2025-10 | 4 | **ambiguo** | −135k tras outflow 291k; recupera a +12k en 4 meses |
| **COMP_0611** | 2024-11 | 22 | **ambiguo** | ratio ~18×; negativo casi toda la serie |
| **COMP_0181** | 2024-09 | 2 | **ambiguo (póliza)** | Cubierto por línea |

**% falsos como “evento de estrés nuevo”:** ~40–50 % (ya negativos + póliza + caja≈0). Artefacto de reconstrucción extremo: ~2 %.

### 7.3 Caída de cobros

348 empresas; solapamiento con apagado **20 %** (lado decline) / **76 %** (lado apagado). Recuperación post-horizonte (no apagadas, n=226): **28 %**.

#### Casos (≥8)

| company_id | Flag | ¿Apagado? | base→fut→post | Clasificación |
|---|---|---|---|---|
| **COMP_1255** | 2025-03 | sí | 875 → 2 → 0 | **artefacto** (mecánico) |
| **COMP_1042** | 2025-02 | sí | 250 → 0 → 0 | **artefacto** |
| **COMP_1000** | 2026-02 | sí | 2,8M → 0 | **artefacto** |
| **COMP_1051** | 2025-11 | sí | 1,3k → 0 | **artefacto** |
| **COMP_1027** | 2025-07 | no | 5,2k → 2,2k → **4,2k** | **artefacto** (bache; recupera) |
| **COMP_1029** | 2025-02 | no | 758 → 14 → **1,1k** | **artefacto** (estacional/reversión) |
| **COMP_0263** | 2025-09 | no | 4,8k → 1,2k → 913 | **evento_real** (persiste) |
| **COMP_1211** | 2025-07 | no | 429k → 7k → 1,3k | **evento_real** |
| **COMP_0834** | 2025-02 | no | 10k → 0 → 0 | **evento_real** (colapso) |
| **COMP_0127** | 2025-12 | no | 14 → 0 | **evento_real** / escala ínfima |

**% falsos estimado ~42 %** (apagado + recuperación). El resto mezcla caídas reales y ruido de escala pequeña.

### 7.4 Crecimiento

437 empresas; reversión post-horizonte **26,5 %**; oper-dominado 318; transfer-dominado 26.

#### Casos (≥8)

| company_id | Flag | tr/uncat | Revierte | Clasificación |
|---|---|---|---|---|
| **COMP_1006** | 2025-07 | bajo | no | **evento_real** |
| **COMP_0052** | 2025-02 | bajo | no | **evento_real** |
| **COMP_0146** | 2026-01 | bajo | no | **evento_real** |
| **COMP_0210** | 2026-02 | bajo | no | **evento_real** |
| **COMP_1079** | 2025-02 | — | sí | **artefacto** (pico) |
| **COMP_0263** | 2025-10 | — | sí | **artefacto** (misma empresa que decline real en otra ventana — inestable) |
| **COMP_0973** | 2025-11 | uncat 47 % | sí | **artefacto** |
| **COMP_0760** | 2025-08 | — | sí | **artefacto** |
| **COMP_0491** | 2025-03 | — | sí | **artefacto** |
| **COMP_0614** | 2025-03 | — | sí | **artefacto** |

**% falsos ~27 %** por reversión; adicional por uncat/historia corta.

### 7.5 Propuesto: incumplimiento de obligaciones recurrentes

Implementación exploratoria sobre el panel (`payroll`, `tax`, `debt_service`, `overdue_90_ap`):

| Variante | Tasa mes (elegible) | Empresas ever |
|---|---:|---:|
| Nómina omitida | 3,4 % | 15 % |
| Cuota omitida | 5,2 % | 19 % |
| IVA trimestre omitido | 2,2 % | 23 % |
| AP90 creciente | 6,6 % | 21 % |
| Cualquiera | **16 %** | **54 %** |
| Forward-6m cualquiera | **33 %** | 459 empresas |

**Frecuencia real usable:** si se exige regularidad fuerte y se excluye IVA aislado, estimamos **~5–8 %** de meses y **~15–25 %** de empresas — usable como co-ancla. Tal cual (any_miss) es **inútilmente frecuente**.

#### Casos (≥8)

| company_id | Primer miss | Tipo | Clasificación | Notas |
|---|---|---|---|---|
| **COMP_1125** | 2025-12 | pay_miss | **evento_real** | Nómina regular ~5–27k; dic–ene a 0; vuelve en mar — fallo real de continuidad |
| **COMP_0538** | 2025-02 | debt_miss | **evento_real** | Cuota que desaparece con actividad |
| **COMP_0356** | 2025-09 | debt_miss | **evento_real** | Idem |
| **COMP_0405** | 2025-03 | ap90 | **evento_real** | AP>90 crece |
| **COMP_0071** | 2025-07 | ap90 | **evento_real** | Idem |
| **COMP_0494** | 2025-07 | ap90 | **evento_real** | Idem |
| **COMP_0572** | 2026-04 | tax_miss | **evento_real?** | IVA omitido con continuidad posterior dudosa |
| **COMP_0457** | 2025-07 | tax_miss | **artefacto** | Vuelve el trimestre siguiente |
| **COMP_1183** | 2026-07 | tax_miss | **artefacto** | Borde / gap 0 |
| **COMP_0930** | 2026-07 | tax_miss | **artefacto** | Cerca del apagado |
| **COMP_0033** | 2026-04 | tax_miss | **ambiguo** | gap 2 al final |
| **COMP_0760** | 2026-08 | debt_miss | **ambiguo** | Mes final del panel |

### 7.6 Propuesto: entrada en tensión de caja

| Métrica | Valor |
|---|---|
| Tasa mes (definición transición cruda) | **3,0 %** |
| Empresas con ≥1 entrada | **347 (27 %)** |
| Rebote ≤3 meses | **26 %** |
| Estrés los 3 meses siguientes | **27 %** |

Sin filtro de persistencia, **~26 % son baches**. Con persistencia, la frecuencia baja a un rango parecido al apagado “real” pero con semántica de tesorería.

#### Casos (≥8)

| company_id | Entrada | months_cash | Clasificación | Notas |
|---|---|---|---|---|
| **COMP_0162** | 2026-04 | 0,23 | **evento_real** | 28k→2,3k→1,1k; quema sostenida |
| **COMP_0165** | 2025-10 | 0,05 | **evento_real** | Solo outflows ~6k/mes; caja mínima persistente |
| **COMP_0522** | 2025-08 | 0,17 | **evento_real** | Persistente |
| **COMP_0779** | 2025-12 | 0,14 | **artefacto** | Un mes 2,5k y luego **inflow 274k–562k**; bache previo a ramp-up |
| **COMP_0818** | 2025-12 | −0,58 | **artefacto** | −12k un mes; rebound a +107k (¿transfer/reconstrucción?) |
| **COMP_0743** | 2025-12 | 0,24 | **ambiguo** | Caja baja con cobros irregulares; luego recupera |
| **COMP_0305** | 2026-07 | 0,18 | **ambiguo** | Empresa grande; un mes flojo cerca del borde |
| **COMP_1109** | 2025-05 | 0,19 | **ambiguo** | Luego meses a n_tx=0 con caja congelada 515k (desconexión) |
| **COMP_0035** | 2025-02 | 0,18 | **ambiguo** | Runway bajo por burn alto, caja absoluta alta |
| **COMP_0859** | 2025-12 | 0,24 | **ambiguo** | Persistencia incierta |
| **COMP_0830** | 2025-11 | 0,17 | **ambiguo** | Idem |
| **COMP_0176** | 2025-05 | 0,25 | **ambiguo** | Umbral justo en el corte |

### 7.7 Solapamientos (empresa, ever en ventana elegible)

|  | ∩ churn | ∩ cash_stress | ∩ decline | ∩ positive |
|---|---:|---:|---:|---:|
| churn | 1 | 0,04 | **0,76** | 0,23 |
| cash_stress | 0,03 | 1 | 0,31 | 0,58 |
| decline | 0,18 | 0,08 | 1 | 0,43 |
| positive | 0,04 | 0,12 | 0,34 | 1 |

El saldo negativo es casi ortogonal al apagado. Decline≈apagado en la práctica. Positive solapa demasiado con decline (43 %) — otra razón para no usarlos como par adversario/simétrico.

### 7.8 Implicación directa para `targets.py`

Hoy:

```python
adverse = churn | decline | (cash & cash_end>=0)
```

Eso **optimiza el score contra desconexión y baches de cobros**. Recomendación de código (no aplicada aquí): ancla = `tension_entry_persistent | payroll_or_debt_miss_strict`; `churn` y `decline` fuera de `adverse`; `positive` solo para métrica de mejora.

---

## Cierre

Veredicto del auditor: **las etiquetas actuales están lo bastante contaminadas como para limitar el AUC “en el techo de información” que ya medisteis** — no es solo el modelo. Limpiar la verdad (tensión persistente + incumplimiento estricto; apagado como cobertura) es el apalancamiento más barato antes de añadir features.
