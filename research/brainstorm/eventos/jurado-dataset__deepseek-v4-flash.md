<!-- modelo: deepseek-v4-flash vía Helmcode · lente: jurado-dataset · 47s · uso: None -->

## 1. Posición

El leaderboard no mide "quién se apaga" ni "quién tiene caja negativa": mide si reconstruyes **la curva latente de salud que el generador plantó** en cada empresa. Un dataset sintético para hackathon se construye casi siempre igual: se asigna un **arquetipo** por empresa (sano sostenido, mejora, deterioro, bache-y-vuelta, tensión), se dibuja una **trayectoria latente** mes a mes y los seis ficheros son la **proyección ruidosa** de esa trayectoria. Las seis preguntas del enunciado son literalmente la lista de arquetipos, y el bonus de "anticipación" premia detectar el ramp que el generador dibujó antes del cruce visible. Nuestros cuatro eventos actuales son **artefactos operativos** (churn = baja de conexión, caja negativa = reconstrucción, caída de cobros = reversión a la media, crecimiento = ruido), no la verdad. La apuesta correcta es reconstruir la **dirección** de la trayectoria con una señal ancla tipo incumplimiento y construir el score como nivel × dirección, no como media de eventos desalineados.

---

## 2. Veredicto sobre cada evento actual

| Evento | Veredicto | Motivo desde la lente de generador sintético |
|---|---|---|
| **Apagado (churn)** | **Separar como otro producto / degradar a feature** | En generadores de hackathon el "churn" suele ser un *flag de dropout* independiente del arquetipo de salud: la empresa deja de reportar a Embat en el mes T. Los datos cuadran: 22 % se apaga con >3 meses de caja, solo el 36 % tuvo síntomas previos y el 69 % solapa con caída de cobros. Es **pérdida de cobertura**, no default. Producto: monitor de observabilidad, no de riesgo. |
| **Saldo negativo** | **Redefinir como transición ("entrada en tensión")** y degradar el binario a feature | La caja es una variable **derivada** del generador; el binario "negativo" captura un punto, no la dirección. El AUC 0,77 con la caja de hoy es parcialmente circular y el 46 % con >3 meses seguidos negativos huele a artefacto de reconstrucción. Lo informativo es *el primer cruce tras haber estado bien*. |
| **Caída de cobros** | **Degradar a feature (síntoma)** | Está bien construida contra base anual, pero mide **actividad**, no deterioro estructural: el 69 % solapa con churn y castiga a quien tuvo pico. En un generador, "decline" se siembra como reducción de cobros **+** impagos al alza **+** deuda usada, no como una sola variable. |
| **Crecimiento** | **Mantener como evento positivo pero redefinir** | Nuestra definición (cobros >130 % + caja al alza) confunde salto con rampa. El arquetipo "mejora" tipo Northbrook 45→65 es una **pendiente sostenida**, no un mes bueno. Redefinir como "mejora sostenida ≥4 meses". |

---

## 3. Eventos recomendados

Todas las definiciones son causales (datos ≤ fin de m) y están expresadas con columnas del dataset. Frecuencias **estimadas** (no he ejecutado código en esta sesión).

| Evento | Definición implementable | Tipo | Preguntas | Frec. estim. | Riesgos |
|---|---|---|---|---|---|
| **Incumplimiento de obligación recurrente** *(ancla principal)* | Para cada `category` con calendario estable en los 12 m previos (`salary`, `social_security`, `tax`, `debt_repayment`), detectar el mes en que "tocaba" por patrón (día ±5, importe ±40 %, periodicidad mensual/trimestral) y no hay tx, o aparece >7 días tarde. Evento = ≥1 obligación omitida en 3 m. | Resultado | 3, 4, 5, 6 | 12-18 % | Categoría `-` (25 % filas) y empresas sin ERP. Requiere calibrar calendario por empresa. |
| **Entrada en tensión de caja** | Primer mes con `cash_end / gasto_12m < 0,25` **o** `cash_end < 0` **tras** ≥3 m con `meses_caja ≥ 0,5`. Marca el **mes de transición**, no el nivel. | Transición | 3, 4, 6 | 8-12 % | Reconstrucción de caja hereda errores; suavizar con mediana de 3 m. |
| **Deterioro estructural** | ≥3 meses consecutivos con `rolling_median(inflow, 3) < 0,7 × rolling_median(inflow, 12)` **y** al menos un incumplimiento en la ventana **y** `overdue_ap` o `late_share_ap` al alza mes a mes. | Resultado (persistencia) | 3, 4, 5 | 10-15 % | Se confunde con estacionalidad trimestral; usar comparación contra mismo trimestre. |
| **Bache (dip-and-recover)** | Un único mes con caída >40 % de `inflow` o `cash_end < 0`, con recuperación a la mediana en ≤2 m, sin más incumplimientos y sin caída de `n_cust_3m`. | Resultado transitorio | 4, 5 | 10-14 % | Es el evento que hoy NO resolvemos (AUC 0,50). Es también el arquetipo más discriminante del leaderboard. |
| **Mejora sostenida** | Pendiente positiva (Spearman >0 en ≥4 de 6 meses) de `rolling_median(inflow,3)` sobre la de 12, sin incumplimientos ni `cash_end < 0`, y con `n_cust_3m` estable o al alza. | Estado positivo | 2, 6 | 12-18 % | Fuga si se mide con `in6` futuro; usar solo pasado hasta m. |
| **Sano sostenido** | 12 m sin incumplimiento, sin caja < 0, `meses_caja ≥ 3` en mediana móvil, `late_share_ar/ap` ≤ cuantil 40 histórico. | Estado positivo | 1 | 15-20 % | Casi tautológico con score: recalcular con features **no usadas** en el score. |
| **Palanca de financiación** | Mes en que `lc_drawn/lc_limit > 0,6` y creciente, o aparición de nueva deuda (`debt_schedule_config.next_payment_date` en ≤3 m) con `cash_end` a la baja. | Transición | 3, 5, 6 | 6-10 % | `outstanding`/`granted` son foto final: solo usar `lc_limit/lc_drawn` y el calendario de cuotas, no el stock. |
| **Régimen de pagos degradado** | DSO y DPO (por facturas, `payment_date − due_date`) suben >7 días frente a mediana de 12 m y se mantienen 2 m. | Síntoma temprano | 5, 6 | 20-25 % | `payment_date == due_date` en `overdue`: usar `pending_amount ≠ 0`. |
| **Pérdida de cobertura** *(producto aparte)* | Mes con `months_since_last_tx > 0` o ERP desconectado (`has_erp` cae) o `uncat_in` sube >2σ. | Producto separado | — | 3-5 % | No puntuar en el score; alimentar alerta de "Empresa deja de reportar". |

**Ancla principal recomendada:** *Incumplimiento de obligación recurrente*. Es la huella más directa de un generador que siembra deterioro: en un dataset sintético, el deterioro se hace **romper la disciplina** de nómina/IVA/cuota antes de que la caja cruce a negativo, porque es barato de generar y explica "por qué cambió". El equipo ya midió indicios (IVA trimestral AUC 0,67 frente a apagado en el review de v1). Es también la señal que un prestamista usaría de verdad ("¿paga a quien le fía?").

---

## 4. Críticas a la propuesta actual

1. **Falta declarar el target del leaderboard.** Se asume implícitamente que el target son los eventos, cuando lo probable es que sea la curva latente del generador. Calibrar pesos contra eventos-propios te aleja del target.
2. **"Transición de caja" sin desambiguar nivel y dirección.** "Menos de 0,25 meses de caja" puede llevar 6 meses sin moverse: sin cláusula de "venía de arriba", es nivel, no transición.
3. **"Bache vs caída" no se operacionaliza.** La propuesta nombra el problema pero no da el criterio de **persistencia** (¿cuántos meses? ¿qué magnitud?) ni cómo se mide sin fuga.
4. **"Evento principal incumplimiento" está bien elegido pero subdefinido.** No dice cómo se infiere el calendario cuando la empresa solo tiene 6 meses, cómo se trata `-` (25 % de filas) ni qué periodicidad se asume para IVA (trimestral) frente a nómina (mensual).
5. **"Sano sostenido 12 m" es casi tautológico con el score.** Si lo defines con las mismas señales, la validación es circular; hay que medirlo con features que **no** puntúan.
6. **"Recuperación: pasa de riesgo a sano y se mantiene"** depende de umbrales del score: vuelve a ser circular. Necesita definición en variables observables.
7. **Apagado "aparte"** sin decir a dónde va: si es un producto, ¿para quién? Si es feature, ¿de contexto o de score? Está bien aislarlo, mal dejarlo huérfano.
8. **Los pesos del score se optimizan contra eventos que no son el target probable.** El equipo ya notó que una logística por evento da AUC 0,63-0,76 frente a 0,59 del promedio: eso es señal de que **los eventos no son objetivos consistentes**, sino artefactos distintos.

---

## 5. Cómo validarías los eventos sin etiquetas

- **Reverse-engineering de arquetipos.** Clustering sobre features de trayectoria (pendiente de caja, pendiente de cobros, cambio de DSO/DPO, persistencia, nº de incumplimientos). Si el generador plantó 4-5 arquetipos, `k=4-5` debe dar silhouette alto y clusters interpretables. Si los clusters no aparecen, o el generador es continuo (y el leaderboard puntúa ranking) o el ruido es muy alto.
- **Detección de régimen / change-point.** CUSUM o `ruptures` por empresa sobre `inflow`, `late_share_ar/ap`, `lc_drawn/lc_limit`. Dos diagnósticos: (a) si los puntos de cambio se concentran en 1-2 meses concretos, es artefacto del generador; (b) si están dispersos y con rampa, hay trayectoria latente.
- **Monotonía.** Spearman de señales clave en ventana móvil. Rampa monótona ⇒ reconstruible; ruido blanco ⇒ no hay nada que reconstruir.
- **Consistencia intragrupo.** Si el generador asigna arquetipo a nivel de grupo, la varianza intra-grupo del score debe ser baja. Si es alta, el arquetipo es por empresa.
- **Coherencia cruzada.** ¿Convergen 3 vías independientes (transacciones, facturas, deuda) en el mismo mes de cambio? En sintéticos, las tres derivan de la misma latente: convergencia = señal real.
- **Holdout temporal.** Cortar los últimos 6 meses y evaluar la habilidad del score (construido con ≤m) para predecir "quién termina peor" según caja/impago del holdout. Mide generalización temporal y evita circularidad.
- **Perturbación.** Submuestrear contrapartes o meses y mirar estabilidad del ranking: debería ser alta.
- **Calibración de mezcla.** Si el score no produce ~15-25 % de empresas en cada uno de los cuatro estados (sano, mejora, deterioro, bache), no captura el mix que el generador plantó.

---

## 6. Preguntas para la organización

1. **Target del leaderboard**: ¿etiqueta discreta por empresa (arquetipo), trayectoria continua, o ranking? ¿AUC, RMSE, Spearman, correlación de trayectoria?
2. **Composición del test oculto**: ¿mismo generador con distinta seed, o hay OOD (monedas raras, historia corta, sin ERP)?
3. **¿El generador plantó arquetipos explícitos?** ¿Cuántos y con qué proporción? ¿Salud por empresa o empresa-mes?
4. **Forma del ramp**: lineal, exponencial, con ruido AR; ¿cuándo empieza respecto al cruce visible?
5. **¿Por qué `debt_products.outstanding` es foto final?** ¿Es que el generador no modeló la deuda en el tiempo, o es un tema del snapshot?
6. **¿Hay campos no documentados con orden de salud** (p. ej. un ID o un flag interno)? ¿Se penaliza usarlos?
7. **¿El leaderboard tolera features que usan `balances`** (que solo existe a 1-sep-2026)? Si no, validar sin ellas.
8. **¿Se premia explícitamente la "anticipación"?** ¿Contra un horizonte fijo o contra "el mes del cambio"?

---

## 7. Verificaciones hechas

**No tengo acceso a los ficheros ni a herramientas en esta sesión.** Todo lo anterior es conjetura basada en el brief y en cómo se construyen habitualmente datasets sintéticos para hackathons; las cifras de frecuencia están marcadas como **estimadas**. Lo que verificaría primero al abrir los datos, en este orden:

1. **Reproducir el hallazgo del IVA trimestral omitido (AUC 0,67 vs apagado)** ya medido por el equipo. Si se confirma, es la primera huella del generador en obligaciones recurrentes y justifica elevar "incumplimiento" a ancla.
2. **Regularidad del calendario de nómina/social_security por empresa**: la ruptura de esa regularidad es el mejor candidato a feature de deterioro temprano.
3. **Detección de change-points** en `cash_end`, `inflow`, `late_share_ar/ap`: mapa de puntos de cambio por empresa y ver si se agrupan.
4. **Clustering k=4-5 sobre features de trayectoria** para ver si aparecen arquetipos interpretables.
5. **Consistencia intra-grupo del score**: mide si el generador correlacionó salud por grupo.
6. **Coherencia entre transacciones y facturas** en el mismo evento: si la caída de cobros de facturas precede a la caída de inflows bancarios, la latente está en el ERP; si es al revés, en el banco.
7. **Análisis del residuo de `debt_schedule_config.next_payment_date`**: cuántas empresas omiten cuotas poco antes de un cambio de régimen — el "cobarde del generador" clásico.

Con eso, en una tarde se puede saber si el target del leaderboard es arquetípico o continuo, y decidir si el ancla es incumplimiento (arquetípico) o trayectoria (continuo).