<!-- modelo: glm5.3 vía Helmcode · lente: sintesis · 291s · uso: {'usage': None, 'finish_reason': 'stop'} -->

# Síntesis del panel: ¿qué eventos deben ser la "verdad" del score X-Ray?

**Investigador principal · 2026-09-19**

**Leyenda de citas.** `[Aud·Cursor]` y `[Jur·Cursor]` son las dos respuestas con acceso a los parquet: sus cifras están **medidas** y pesan más que el resto. `[Aud·DS/GLM/Qw]`, `[Jur··]`, `[Met··]`, `[Prod··]`, `[Cred··]` son DeepSeek, GLM y Qwen sin acceso a datos: sus frecuencias son estimaciones y lo dicen. El brief del equipo (`brief_eventos.md`, `features.md`) cuenta como medido.

**Tesis de síntesis.** El panel converge más de lo esperado: los cuatro eventos actuales son proxies contaminados por artefactos del dataset (borde temporal, reconstrucción de saldos, solape mecánico), el apagado debe salir del score de salud, y el núcleo nuevo es una **transición de tensión de caja persistente** más un **incumplimiento estricto de obligaciones recurrentes**. El desacuerdo real es solo uno: cuál de las tres anclas adversas (liquidez, incumplimiento, caída de cobros) encabeza. Mi resolución es un sistema de dos ejes con calibración por evento, no un ancla única.

---

## 1. Consensos

**C1. El apagado no es salud: es pérdida de cobertura. Lo dicen 14 de 15 respuestas, y es el consenso mejor respaldado.** `[Aud·Cursor]` (medido): de las 121 empresas apagadas, el 36 % calla en jul-2026 (borde del dataset), el 79 % tenía caja positiva al silenciarse, el 27 % sigue emitiendo facturas ERP tras el silencio bancario, y solo ~12 % encaja con "cierre plausible" bajo reglas duras → clasificación 52 % artefacto / 36 % ambiguo / 12 % real. `[Jur·Cursor]` (medido): runway mediano al salir 0,46 frente a 0,39 en activas; solo ~2,5 % tenía estrés de caja previo. Conclusión compartida por todas las lentes (auditoría, jurado, metodología, producto, crédito): **separar como producto de retención/cobertura de Embat y como censura, nunca como ancla de calibración**. Argumento adicional de `[Aud·Cursor]`: mientras el compuesto `adverse_6m` incluya churn, los pesos premian señales de desconexión — las features con mejor AUC frente a apagado son `payee_concentration` (0,75) y `lost_accel` (0,74), ambas de observabilidad.

**C2. "Saldo negativo: algún mes < 0" mide mal; hay que redefinirlo como transición con persistencia.** `[Aud·Cursor]` (medido): el 37,5 % de los flags ya venían en negativo los 3 meses previos, el 46,6 % lo habían estado alguna vez, el 53 % dura >3 meses, el 16 % tiene póliza y solo el 1,9 % son saldos imposibles. Es decir, ~40–50 % no son *entradas* en estrés sino estados crónicos, uso normal de póliza o caja≈0 de paso. Todas las respuestas coinciden en "primer cruce tras ≥3 meses sanos, con persistencia", y `[Cred·GLM]`/`[Met·GLM]` añaden materialidad y severidad según crédito disponible.

**C3. La caída de cobros actual está contaminada; nadie la defiende tal cual.** Solape medido: 69 % a nivel de fila (brief), 76 % a nivel de empresa-apagada `[Aud·Cursor]`. El 28 % de las caídas no apagadas recuperan después del horizonte → baches/estacionalidad `[Aud·Cursor]`. Lo que diverge es el destino (ver desacuerdo D2).

**C4. El crecimiento necesita redefinición.** Reversión post-horizonte del 26,5 % medida `[Aud·Cursor]`; persistencia a +3 meses de solo 0,35 frente a 0,61 del declive `[Jur·Cursor]`. Coinciden en: base operativa (`oper_in`, no `inflow` bruto), excluida financiación/transferencias, robustez a one-offs, exclusión de empresas jóvenes y filtro de persistencia. `[Prod·GLM]` lo llama "escalamiento autofinanciado": crecer con deuda dibujada es riesgo, no salud.

**C5. La circularidad etiqueta↔features infla el AUC y hay que ablacionar.** El AUC 0,77 de los meses de caja frente a saldo negativo es en parte identidad mecánica (el evento se define sobre la variable de la feature). Lo señalan todas las lentes de metodología `[Met·DS]`, `[Met·GLM]`, `[Met·Qw]`, `[Cred·GLM]`, `[Cred·Qw]`, `[Jur·GLM]` y `[Aud·DS]`. Consenso operativo: reportar siempre el AUC ablando las features que comparten variable con el evento, y comparar contra un baseline de persistencia.

**C6. Incumplimiento de obligaciones recurrentes: buena idea, implementación actual demasiado ancha.** `[Aud·Cursor]` (medido): la unión generosa (nómina ∪ cuota ∪ IVA ∪ AP90) da **33 % de meses elegibles con un miss a 6 meses** y 54 % de empresas alguna vez → no discrimina. La versión estricta (regularidad ≥4/6, actividad mínima, sin IVA aislado) estimada en 5–8 %/mes sí es usable. Todos exigen guarda de observabilidad: el 25 % de filas sin categorizar (45 % del importe de entradas) simula omisiones, y un mes de feed degradado no es un impago.

**C7. Bache vs caída exige una regla explícita de persistencia y exclusión de apagados.** Hoy es la pregunta con peor evidencia (AUC 0,50). `[Jur·Cursor]` (medido): ~8–11 % de las empresas con ≥12 meses tienen patrón de bache-con-rebote por reglas. Las definiciones propuestas coinciden en duración: ≤2 meses con recuperación = bache; ≥3 meses sin recuperar = caída.

**C8. Higiene estadística común.** Bootstrap/CV por `group_id` (no por empresa: 250 grupos, 27 % de volumen intragrupo) `[Met·GLM]`, `[Met·DS]`, `[Prod·GLM]`; el régimen es por empresa, no por grupo (solo 7 % de grupos multi-empresa homogéneos, medido `[Jur·Cursor]`); sensibilidades de umbral y horizonte; placebos temporales; lead time medido para la pregunta 6.

**C9. La entrada en tensión como transición es la candidata más extendida a ancla** (primera u opción en `[Aud·Cursor]`, `[Met·DS]`, `[Prod·GLM]`, `[Jur·Qw]`, `[Prod·Qw]`, `[Met·Qw]`; secundaria en `[Aud·DS]`, `[Jur·Cursor]`, `[Cred·GLM]`, `[Aud·GLM]`). Nadie propone volver al binario actual.

---

## 2. Desacuerdos y cómo los resuelvo

**Criterio de arbitraje, explícito:** (1) la evidencia empírica medida pesa ×3 — solo Cursor la tiene; (2) alineación con las seis preguntas y con la criticidad de `scoring.md` (la caja que se evapora primero); (3) cobertura del panel, porque el test oculto puede traer sin ERP e historia corta; (4) potencia estadística (frecuencia suficiente para calibrar pesos); (5) no circularidad; (6) explicabilidad en una frase (prueba de los 100.000 €).

**D1 · ¿Cuál es el ancla principal: tensión de liquidez, incumplimiento o caída de cobros?**
- Tensión: `[Aud·Cursor]` (auditoría de contaminación), `[Met·DS]`, `[Prod·GLM]`, `[Jur·Qw]`, `[Prod·Qw]`, `[Met·Qw]`.
- Incumplimiento: todo el bloque DeepSeek `[Aud·DS]`, `[Jur·DS]`, `[Prod·DS]`, `[Cred·DS]`, `[Cred·Qw]`, `[Jur·Qw]`-variante; `[Cred·GLM]` como ancla de gravedad; `[Met·GLM]` como ancla semántica.
- Caída limpia: `[Jur·Cursor]` ("decline es el mejor proxy observable del régimen adverso del generador"; pendiente de cobros con AUC 0,74 frente a ever-decline), `[Aud·GLM]`, `[Met·GLM]` (por potencia: 13–15 % frente a 2–6 % del incumplimiento).
- **Resolución:** no hay una verdad, hay **dos ejes adversos de igual rango + un co-ancla**. *Ancla principal (criticidad/liquidez):* entrada en tensión persistente — es la única con auditoría de contaminación completa, cobertura del 100 % del panel (no depende de ERP, que falla en el 36 %), y es literalmente la fila "crítica" de `scoring.md`. *Co-ancla de trayectoria (leaderboard):* caída estructural ex-apagado — es el único evento adverso frecuente (10–15 %), y `[Jur·Cursor]` muestra que el generador deja el régimen en la pendiente de cobros; degradarla del todo deja la calibración en manos de eventos raros (argumento de potencia de `[Met·GLM]`). *Co-ancla de significado (crédito):* incumplimiento estricto — es lo que un prestamista teme ("dejó de pagar la nómina") y el único evento no construido sobre caja/cobros. La calibración será **una cabeza por evento** (nunca la unión: ya falló — el declive dominaba y la disciplina de pagos quedaba a peso 0, documentado en `features.md`; una logística por evento da 0,63–0,76 frente a 0,59 del promedio). Si hay que dar un solo nombre al jurado: tensión persistente.

**D2 · ¿Caída de cobros: evento o feature?** `[Aud·Cursor]`, `[Aud·DS]`, `[Jur·DS]`, `[Jur·Qw]`, `[Met·Qw]`, `[Aud·Qw]`, `[Cred·DS]`, `[Cred·GLM]` la degradan a síntoma; `[Jur·Cursor]`, `[Aud·GLM]`, `[Met·GLM]` la mantienen limpia como evento; `[Jur·GLM]` la divide (temprana = evento, profunda = resultado); `[Prod·DS]` pide persistencia sin degradarla. **Resolución:** escisión. Versión limpia, censurada en apagado y con no-recuperación, como evento de trayectoria (E3); la versión causal 3m/12m ya existente como feature. Blindaje anti-dominancia: cabezas separadas y censura.

**D3 · ¿Es el incumplimiento viable como ancla o demasiado frágil (ERP, frecuencia)?** `[Jur·Cursor]` objeta que un ancla solo-ERP falla si el test oculto viene sin facturas, y que el latente del generador parece estar en cobros+caja, no en impagos ERP. `[Prod·DS]` la condiciona a que la cobertura aguante; `[Aud·Cursor]` mide que la versión ancha es inútil. **Resolución:** co-ancla, no ancla única. Los componentes se ordenan por fiabilidad medida: cuota de deuda (5,2 %/mes) > nómina (3,4 %) > AP90 (6,6 %, solo ERP) > IVA (solo si falla 2 trimestres seguidos; el AUC 0,67 del IVA omitido frente a apagado huele a que mide desconexión, no impago `[Cred·GLM]`). Nómina y cuota vienen de categorías bancarias, así que **no requieren ERP** — eso responde parcialmente la objeción de cobertura. Medir antes de ponderar; si la prevalencia estricta cae por debajo de ~3 %/mes, plegarla en un compuesto E1∪E2 (distinto del compuesto que falló, que incluía la caída `[Cred·GLM]`).

**D4 · ¿Umbral de tensión: 0,25 meses de caja o velocidad de quema?** `[Prod·Qw]` objeta que 0,25 es terminal: el prestamista necesita alerta a 1,0–1,5 meses de runway. Los demás piden sensibilidad. **Resolución:** el evento etiqueta usa el umbral medido por `[Aud·Cursor]` (runway <0,25 o caja <0) **más persistencia ≥2 de 3 meses** (sin ella, 26 % son baches — medido). El disparador del *monitor de producto* puede ser más temprano (runway <1–1,5 con quema acelerada), a costa de precisión; son cosas distintas y así se documenta. Validación: rejilla 0,15–0,5 y quedarse con la meseta de AUC `[Jur·Qw]`; variante robusta con mínimo intramensual (ya medida: AUC 0,79 frente a saldo negativo, `features.md`).

**D5 · ¿Un score o varios?** `[Prod·DS]` pide un vector de cabezas por comprador; `[Prod·GLM]` un número público + lecturas + modelo de churn aparte; `[Met·DS]` dos factores latentes; `[Met·GLM]` un índice latente multi-tarea. **Resolución:** arquitectura de `[Prod·GLM]` con el motor de `[Met·GLM]`: un 0–100 público calibrado contra la familia adversa con cabezas por evento (o índice latente conjunto, nunca media de coeficientes), lecturas por comprador (caja/crédito/circulante/potencial) con mismos features y otros pesos, modelo de churn sobre features de observabilidad separado, y **capa de abstención**: no puntuar lo que no se ve.

**D6 · ¿Ventana fija de 6 meses o supervivencia/riesgos en competencia?** `[Met·DS]`, `[Met·GLM]`, `[Aud·Qw]`, `[Met·Qw]` proponen hazards, Cox o multi-estado con el apagado como censura. **Resolución:** pragmática. Se adopta el *principio* (censurar en apagado, separar causas, medir lead time) dentro del pipeline actual de 6 meses, porque es lo implementable en el hackathon y encaja con `targets.py`. El hazard discreto queda como verificación de robustez si hay tiempo. Con base del 3 %, el IC del AUC es ±0,07–0,10 `[Met·DS]`: ninguna decisión de pesos por debajo de esa diferencia.

**D7 (menor) · Empresa vs grupo.** Resuelto por datos: regímenes por empresa (7 % de grupos homogéneos, medido `[Jur·Cursor]`), score por empresa, validación agrupada por `group_id`.

---

## 3. Tabla final de eventos recomendados

| # | Evento | Definición implementable (columnas del panel) | Tipo | Preguntas | Frecuencia | Riesgos |
|---|---|---|---|---|---|---|
| **E1 ⭐** | **Entrada en tensión de caja persistente** *(ancla adversa principal)* | Primer mes m\* con `cash_end<0` o runway<0,25 (runway = `cash_end`/burn; burn = max(out3/3, out12/12)), tras ≥3 meses con runway ≥0,5 y `cash_end≥0`; **confirma** si el estrés persiste en ≥2 de los 3 meses siguientes (censurando por apagado); excluye `\|cash_end\|>50×flujo bruto` y episodios cubiertos por póliza (`lc_drawn` disponible) sin deterioro de cobros | Transición | 3, 4, 5, 6 | Cruda **3,0 %/mes, 27 % ever (medido `[Aud·Cursor]`)**; con filtro de persistencia est. 1,5–2 %/mes, 15–20 % ever | Reconstrucción de saldos; trimestre fiscal; mes parcial; circularidad parcial con la feature de liquidez → reportar AUC ablado |
| **E2** | **Incumplimiento estricto de obligación recurrente** *(co-ancla de crédito)* | (a) Nómina: `payroll>0` en ≥4 de 6 meses previos y `payroll=0` en mes con feed vivo (`n_tx≥5`, `outflow>0`); (b) cuota: `debt_service>0` en ≥4 de 6 y =0 en el mes esperado; (c) IVA solo si fallan 2 trimestres fiscales seguidos; (d) variante AP90 (solo `has_erp`): `overdue_90_ap` +50 % vs m−3 y >0,5·out12. **Guarda:** si `n_tx` bajo o % sin categorizar alto → etiqueta nula | Resultado | 3, 4, 5, 6 | Componentes medidas: nómina 3,4 %, cuota 5,2 %, IVA 2,2 %, AP90 6,6 %/mes; unión ancha 16 % (medido `[Aud·Cursor]`); **estricta est. 5–8 %/mes, 15–25 % ever** | Categoría `-` (25 % filas); pagos fuera de plataforma; solo 87 cuadros de amortización; vacaciones/nóminas irregulares |
| **E3** | **Caída estructural de cobros ex-apagado** *(co-ancla de trayectoria)* | Mediana de `inflow` (o `oper_in`) de m+1…m+6 < 0,5 × mediana de los 12 previos (base ≥9 meses), **empresa activa todo el horizonte** (`months_since_final_tx=0`) **y sin recuperación** (mediana m+4…m+6 ≤ m+1…m+3, o post-horizonte <0,8×base); sept-2026 parcial excluido o prorrateado | Resultado | 3, 4, 6 | 17 % cruda (medida); **limpia est. 10–15 %** (`[Jur·Cursor]` 12–15 %, `[Aud·GLM]` 10–13 %) | Sigue correlacionada con apagado si no se censura; estacionalidad; one-off en la base |
| **E4** | **Expansión sostenida (autofinanciada)** *(ancla positiva)* | Media de `oper_in` m+1…m+6 > 1,3×(in12/12) y `cash_end(m+6)>cash_end(m)`, sin E3 en la ventana, sin alta neta de deuda que financie el salto y sin un cobro puntual >50 % del incremento; `month_idx≥5` | Resultado positivo | 1, 2, 5, 6 | 16,3 % cruda (medida); **est. 10–12 % limpia** | Reversión (27 % medida `[Aud·Cursor]`); estacionalidad; base deprimida |
| **E5** | **Bache** *(taxonomía de la pregunta 4; no calibra pesos)* | Caída bajo umbral (`inflow`<0,7×med12 o desplome de caja >1 IQR propio) con recuperación a ≥0,8–0,9×nivel previo en ≤2 meses, sin E1/E2/E3 y empresa viva | Síntoma/contraste | 4, 5 | **~8–11 % de empresas con ≥12 m (medido `[Jur·Cursor]`)** | Censura derecha; confusión con ruido de reconstrucción |
| **E6** | **Sano sostenido** | Toda la historia disponible (mín. 9 meses) sin E1–E3, mediana de runway ≥1, suelo de actividad (`n_tx≥3/mes`; `ar_issued>0` si `has_erp`) | Estado positivo | 1 | est. 15–40 % según definición | Sesgo de observabilidad: quien menos se ve sale más sano → gatear por calidad de dato; sesgo de tenencia |
| **E7** | **Recuperación sostenida** | Tras E1 o estado negativo: 3 meses consecutivos con runway ≥0,5–1 y sin miss, con mediana de cobros de esos 3 meses ≥ mediana previa de 12 (guardia de nivel) | Transición positiva | 2, 4 | est. 3–6 % | Regresión a la media; pocos casos |
| **E8** | **Apagado / baja de cobertura** *(fuera del score)* | `months_since_final_tx>0` definitivo. Subclases `[Aud·Cursor]`: *desconexión* si caja>0 al callar ∧ (cuentas escalonadas ∨ ERP activo tras el silencio ∨ borde jul/ago-2026); *cierre_sospechoso* si fade + síntomas previos | Censura / producto de retención | 5 (contexto); monitor | 3 % medida (121 empresas; 52 % artefacto / 36 % ambiguo / 12 % cierre real) | En producción: 30–60 días sin sincronizar ninguna fuente; no es economía |

**Ancla principal: E1 (tensión persistente)**, con E3 de igual rango como eje de trayectoria para el ranking del leaderboard, E2 como co-ancla de crédito y E4 como contraparte positiva obligatoria (el enunciado exige simetría: Northbrook 45→65 vale tanto como Velasco 82→68). E5 responde a la pregunta 4 como clasificación, no como target binario único.

---

## 4. Qué hacer con los eventos actuales

| Evento actual | Disposición |
|---|---|
| `churn_6m` (apagado) | **Fuera del score.** Producto de retención + censura de los demás eventos. Quitarlo de la unión `adverse_6m` — cambio de código recomendado por `[Aud·Cursor]`: hoy `adverse = churn \| decline \| cash` optimiza contra desconexión y baches |
| `cash_stress_6m` (saldo negativo) | **Sustituir por E1.** El "ever negative" pasa a feature/contexto (historial de tensión) |
| `decline_6m` (caída de cobros) | **Escindir:** E3 (limpio, censurado, con no-recuperación) como evento de trayectoria + la versión causal 3m/12m como feature. Prohibido en compuestos de unión (dominó la calibración: documentado en `features.md`) |
| `positive_6m` (crecimiento) | **Redefinir como E4** (operativa, sin financiación, persistente). No usarlo como anti-etiqueta: solape medido positive∩decline = 0,43 `[Aud·Cursor]` |
| `adverse_6m` (unión) | **Eliminar como objetivo de calibración** (consenso de todas las lentes; ya degradó la disciplina de pagos a peso 0) |
| Calibración | Mantener una logística por evento (mejora ya medida: 0,63–0,76 vs 0,59); subir a índice latente multi-tarea o etiquetas blandas si hay tiempo (`[Met·GLM]`) |

---

## 5. Plan de validación sin etiquetas

Consolidado de las baterías propuestas, en cinco bloques y orden de coste. Umbrales concretos donde el panel los dio.

**A. Higiene de las etiquetas (día 1).**
1. **Auditoría de casos**: ≥20–30 series por evento nuevo (E1–E4), clasificadas real/artefacto/ambiguo; publicar la tasa de contaminación. Es lo que cambió el veredicto sobre el apagado `[Aud·Cursor]`.
2. **Independencia de cobertura**: correlación de cada evento con `has_erp`, meses de historia, % sin categorizar; si el AUC se explica por cobertura, no es salud `[Aud·Cursor]`, `[Jur·Qw]`.
3. **Estabilidad temporal**: tasas por `month_idx` y ventana (train ≤2025-12, val 2026); picos en bordes = censura mal tratada `[Aud·Cursor]`, `[Met·Qw]`.

**B. Circularidad y potencia (día 1–2).**
4. **Ablación**: reajustar cada evento sin las features construidas sobre sus variables definitorias; ΔAUC > 0,03–0,05 → etiqueta demasiado cercana al modelo `[Met·GLM]`.
5. **Baseline de persistencia**: el score debe superar a "la caja de hoy predice la tensión de mañana" con bootstrap por grupo; si no, el evento es autorregresión, no objetivo `[Met·DS]`, `[Met·GLM]`.
6. **IC por evento** con bootstrap por `group_id`; con base del 3 %, ±0,07–0,10 `[Met·DS]` — no decidir pesos por debajo.

**C. Robustez (día 2).**
7. **Sensibilidad**: umbrales ±20 % (0,15–0,5 en runway; 40–60 % en caída) y horizontes 3/6; quedarse con mesetas; los pesos no deben cambiar de signo `[Jur·Qw]`, `[Met·GLM]`, `[Met·DS]`.
8. **Placebo**: permutar meses dentro de empresa → AUC ≈ 0,5; si no cae, hay fuga estructural `[Met·DS]`, `[Met·GLM]`.
9. **Perturbación de la reconstrucción**: recalcular eventos sin el 1 % de flujos mayores, solo `booked`/`value_date`, FX validado; solape >90 % en la etiqueta o κ<0,6 → no fiable `[Aud·GLM]`.
10. **Triangulación de canales** con κ ≥ 0,6 (banco ↔ ERP ↔ deuda): un cierre real deja de pagar, facturar y mover caja a la vez; una desconexión no `[Aud·GLM]`, `[Met·GLM]`, `[Met·DS]`.

**D. Validez de constructo.**
11. **Redescubrimiento económico**: entrenado contra el evento, el modelo debe recuperar relaciones conocidas (deuda nueva con caja cayendo ⇒ más riesgo, etc.); un proxy bueno ordena el mundo como se espera `[Met·GLM]`.
12. **Coherencia temporal jerárquica**: la tensión debe preceder a la omisión, y la omisión a la caída de cobros; si el orden se invierte, la definición está mal `[Prod·Qw]`.
13. **Monotonicidad por deciles** de las features actuales frente a cada evento nuevo; y estructura de hazards: las transiciones (E1) deben elevar la probabilidad posterior de los resultados (E2, E3) `[Cred·GLM]`.
14. **Huella del generador**: reglas de arquetipos y pendiente de cobros (AUC 0,74 ya medido `[Jur·Cursor]`); change-points concentrados en 1–2 meses = artefacto, dispersos con rampa = trayectoria latente `[Jur·DS]`; plantillas de ramp-down de los 121 apagados `[Jur·GLM]`.

**E. Producto y verdad externa.**
15. **Lead time** (pregunta 6): meses entre primera alerta y evento; exigir señal ≥3 meses antes; lo que solo aparece en el mes 0 es ruido `[Jur·GLM]`, `[Prod·GLM]`, `[Jur·Qw]`.
16. **Backtest de decisión**: cartera sombra (prestar 100.000 € al decil superior; LGD 45 %), P&L simulado por lectura de comprador `[Cred·DS]`, `[Prod·DS]`, `[Prod·GLM]`.
17. **Adjudicación experta**: 30–40 casos anonimizados a Embat ("¿baja de producto o quiebra?") — la única ground truth real obtenible en el hackathon `[Met·DS]`, `[Aud·Cursor]`; explotar al especialista de datos nocturno `[Prod·GLM]`.
18. **Sondeos del script del viernes** como etiquetas débiles: pocas submissions, registro de cada respuesta, sin sobreajuste `[Jur·GLM]`, `[Prod·GLM]`.

---

## 6. Preguntas a la organización (deduplicadas y priorizadas)

**Tier 1 — bloquean el diseño de targets (preguntar hoy).**
1. **¿Qué es el "apagado" en el generador: cierre de empresa, baja de Embat o fin de muestreo? ¿Existe una variable latente de salud/estado por empresa y puede liberarse (aunque sea post-hoc) para validar los proxies?** *(preguntada por 10 respuestas; la más rentable del panel)*
2. **¿Qué puntúa exactamente el leaderboard: score continuo por empresa-mes, AUC contra qué etiqueta, ranking de trayectoria simétrico, y con qué horizonte? ¿Se evalúan mejora y deterioro por separado?** *(6 respuestas)*
3. **¿El test oculto comparte distribución (historia corta, sin ERP, divisas) con el train? ¿Habrá apagados? ¿Cómo se puntúan los huecos?** *(8 respuestas)*

**Tier 2 — afina definiciones (esta noche).**
4. ¿La caja negativa es sobregiro legítimo (con o sin póliza) o siempre artefacto de reconstrucción? ¿Cómo se categorizan las disposiciones de póliza/factoring frente a cobros operativos? *(4 respuestas; condiciona la regla de exclusión de E1)*
5. ¿Hasta qué día exacto llega sept-2026 y cómo se conviene prorratear meses parciales? *(3 respuestas)*
6. ¿El generador omite obligaciones (nómina/IVA/cuota) en los arquetipos de estrés? ¿`tax` es solo IVA? ¿12 o 14 pagas? ¿`debt_repayment` cubre capital+interés y cómo se codifica una refinanciación? *(5 respuestas; determina la viabilidad de E2)*
7. ¿El score se evalúa por empresa o por grupo? ¿Hay cash pooling y cross-default dentro del grupo? *(5 respuestas)*
8. ¿`cash_end` del panel suma saving/investment? ¿Se reconstruye con `date` o `value_date` y cómo se trató `pending`? *(2 respuestas)*
9. ¿La categoría `-` es aleatoria o informativa (empresa, ERP, banco)? *(2 respuestas)*

**Tier 3 — producto y demo.**
10. ¿Quién es el comprador protagonista de la demo (banco, CFO, aseguradora) y tolera el monitor cierta tasa de falsos positivos? *(3 respuestas)*
11. ¿Hay 10–20 casos reales anonimizados o tasas agregadas de bajas para calibrar frecuencias? *(1 respuesta, alta relación valor/coste)*
12. ¿El script de scoring admite salidas adicionales (alertas, lecturas, abstención) o solo un número? *(2 respuestas)*

---

## 7. Ideas originales de una sola respuesta que merecen atención

1. **Corroborar el sobregiro por sus costes** `[Aud·GLM]`: el banco cobra por descubiertos; si el primer mes negativo coincide con `interest_charge` o pico de `fee` (±1 mes), es evento económico; si no, artefacto de reconstrucción. La validación más barata posible de E1, con columnas que ya tenemos.
2. **Guardia de "feed vivo" para separar impago de desconexión** `[Cred·GLM]`: "mes activo" = `n_tx` ≥ 50 % de la mediana de los 3 meses previos. Sin ella, "no pagó el IVA" y "se desconectó" son el mismo bit — y explica por qué el IVA omitido da AUC 0,67 *frente a apagado*.
3. **La trampa de la silueta** `[Jur·Cursor]` (medido): sin filtrar outliers, k-means da silueta 0,95 que **es un engaño de una sola empresa**; tras filtrar, 0,074. Aviso metodológico para quien clusterice trayectorias este fin de semana.
4. **Huellas de generador** `[Jur·GLM]`: rejilla de severidad (si los ratios post-break se apilan en 0,5/0,6/0,7, hay factores scriptados), plantillas de ramp-down apilando las series normalizadas de los 121 apagados, y flips de pendiente sincronizados en meses concretos (los Northbrook/Velasco scriptados). `[Jur·DS]` añade: change-points concentrados en 1–2 meses = artefacto; dispersos con rampa = trayectoria latente.
5. **Adjudicación experta de 40 FP + 40 TP** a los mentores de Embat como estimación PU de la tasa de error del proxy: la única ground truth real del fin de semana `[Met·DS]`.
6. **Coherencia temporal jerárquica como validación** `[Prod·Qw]`: liquidez → omisión de pagos → caída de cobros debe ocurrir en ese orden; si se invierte, la definición está mal.
7. **Rotura de cobertura** `[Cred·Qw]`: distinguir `cash_end<0` con `lc_drawn < 0,9·lc_limit` (negativo descubierto, grave) del negativo cubierto por póliza (operativo). Afina E1 y responde al falso negativo de "la línea tapa el hueco".
8. **Buckets de mora 30/60/90 y tasas de cura objetivo 25–40 %** `[Cred·DS]`: la migración entre tramos es la traducción bancaria de "bache vs caída", y las curas calibran si el umbral de mora es laxo o terminal.
9. **Capa de abstención y modelo de churn sobre features de observabilidad** `[Prod·GLM]`: "no puntuar lo que no se ve" protege la credibilidad ante bancos y convierte el apagado en entregable con comprador (playbook de CS con tasa de salvación medible).
10. **`balances` final como pseudo-ground-truth de coherencia** `[Prod·DS]`: las empresas que acaban en negativo o con deuda impagada debieron disparar los eventos antes; las "sanas sostenidas" deben acabar con caja. Comprobación de una tarde que detecta etiquetas mal definidas.
11. **Índice latente multi-tarea o etiquetas blandas (Dawid-Skene/Snorkel) con corrección de la correlación conocida apagado↔declive**, en lugar de promediar coeficientes de logísticas independientes — el promedio es el caso degenerado que ya falló `[Met·GLM]`; `[Met·DS]` propone la variante de dos factores latentes (tensión y momentum) cuyo diferencia da el número.
12. **Caja mínima intramensual como variable del evento, no el saldo a fin de mes** `[Met·Qw]` — refuerza la medición ya existente (AUC ~0,79 frente a saldo negativo, `features.md`): el evento debería definirse sobre la trayectoria diaria reconstruida, no sobre el cierre.

**Nota final de prioridad.** Si solo hay tiempo para tres cosas antes de recalibrar pesos: (1) sacar el churn de `adverse_6m` y censurar el declive en apagado (cambio de `targets.py`); (2) implementar E1 con filtro de persistencia y E2 estricto con guarda de observabilidad; (3) correr la ablación de circularidad + baseline de persistencia. Todo lo demás del panel es refinamiento sobre esa base.