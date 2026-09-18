# Veredicto del jurado (lente dataset/generador): ¿qué eventos deben ser la “verdad” del score?

**Autor:** miembro del jurado Embat con acceso a `research/data/*.parquet` y `research/data/panel.parquet`, familiarizado con generadores sintéticos de tesorería.  
**Scripts:** `/tmp/cluster_trayectorias.py` y análisis ad hoc en `/tmp` (ningún otro fichero del repo modificado salvo este informe).  
**Fecha:** 2026-09-19.

---

## 1. Posición

El generador **sí planta regímenes de trayectoria** (creciente, declive, estable, bache con rebote, apagado), pero los deja como **mezcla continua con ruido**, no como k clusters limpios en el espacio de series de 48 dimensiones: la silueta de k-means/ward tras filtrar outliers es ~0,05–0,07. Aun así, una partición grosera en “caja/cobros al alza” vs “a la baja” (~52 % / 48 %) y una clasificación por reglas reproducen los arquetipos del enunciado (Northbrook vs Velasco) y **se alinean fuerte con `decline_6m` / `positive_6m`** (AUC de la pendiente de cobros ≈ 0,74 frente a “alguna vez decline/growth”).

El leaderboard, si Embat es coherente con el brief y con cómo se fabrican estos datasets, **no puntúa “quiebra” ni apagado de Embat**: puntúa **capacidad de ordenar trayectoria simétrica** (quién mejora / quién se tuerce) más nivel. Por tanto, anclar pesos solo a apagado o a saldo negativo es un mal proxy; el ancla principal debe ser **cambio estructural de cobros+caja**, con **transición a tensión de caja** como ancla adversa secundaria, **apagado fuera del score de salud**, y **bache vs caída** como etiqueta de producto (pregunta 4), no como único target binario.

---

## 2. Veredicto sobre cada evento actual

| Evento | Veredicto | Motivo (con datos) |
|---|---|---|
| **Apagado** (`churn_6m`, ~3 %) | **Separar como otro producto / cobertura**, no ancla de salud | 121 empresas. En el último mes activo, mediana de `runway` **0,46** vs **0,39** en activas; **12 %** se va con runway > 3 y **10 %** con runway ≤ 0. Solo **~58 %** tuvo `decline` o `cash_stress` en los 6 meses previos; casi no hay `cash_stress` previo (~2,5 %). **69 %** de las filas de apagado cuentan también como caída de cobros (solapamiento mecánico: al cortar actividad, la mediana futura se derrumba). Huella típica de **desconexión / fin de serie sintética**, no de insolvencia. |
| **Saldo negativo** (`cash_stress_6m`, ~5,4 %) | **Redefinir** como *transición* a tensión, no como “caja &lt; 0 en el horizonte” | Independiente del resto (corr ≈ −0,03 con decline/growth). **~31 %** de los eventos ya venían de meses negativos en t−1…t−3 (circularidad). Entre empresas con algún mes negativo (213), **46,5 %** tienen racha &gt; 3 meses (mediana de racha = 3): mezcla de tensión real y **artefacto de reconstrucción** de saldos. Solo **16 %** de las ever-neg tienen póliza (`lc_limit`&gt;0) vs 14 % base: no explica el negativo. Persistencia a +3 m = **0,67** (útil si se redefine como estado/transición). |
| **Caída de cobros** (`decline_6m`, ~17 %) | **Mantener como ancla adversa principal**, con matiz | Es el evento que **más se parece a un régimen del generador**. Persistencia a +3 m = **0,61**. En arquetipo regla “declive” (n=210): tasa media 0,27 y **58 %** somehow-ever; en “creciente” (n=262): tasa 0,04 y ever 14 %. La pendiente de cobros normalizada predice ever-decline con **AUC 0,74**. Riesgo: captura también apagados y baches profundos; conviene exigir **persistencia** (p. ej. 2 ventanas) o conjunción con caja. |
| **Crecimiento** (`positive_6m`, ~16 %) | **Mantener como ancla positiva**, simétrica | Persistencia más baja (**0,35** a +3 m): más ruidoso que decline. Aun así, en “creciente” ever-growth **76 %** vs **24 %** en “declive”. AUC pendiente cobros vs ever-growth **0,74**; pendiente de caja ayuda menos (0,65). Necesario para las preguntas 1–2 y para no convertir el score en detector de default. |
| **`adverse_6m` (unión)** | **No usar como único target** | Tasa ~22 %. Mezcla apagado (desconexión) + decline + cash. Optimizar contra la unión **premia confundir baja de Embat con deterioro** y diluye la simetría. |

---

## 3. Eventos recomendados

**Ancla principal (leaderboard / calibración de pesos):** *trayectoria estructural adversa vs favorable* — par simétrico `caída_estructural` / `recuperación_o_expansión`, construido sobre cobros operativos + caja, no sobre apagado.

| Nombre | Definición implementable (columnas panel / derivadas) | Tipo | Preguntas del reto | Frecuencia (medida o estimada) | Riesgos |
|---|---|---|---|---|---|
| **Caída estructural de cobros** *(ancla adversa)* | `oper_in` (fallback `inflow`): mediana m+1…m+6 &lt; 0,5 × mediana m−11…m **y** (mediana m+4…m+6 ≤ mediana m+1…m+3 **o** `cash_end` a m+6 &lt; `cash_end` a m). Exige empresa activa (`months_since_last_tx=0`) y `month_idx≥5`. | Resultado | 3, 4, 5, 6 | ~12–15 % (subset del 17 % actual al filtrar rebotes) | Sigue correlacionada con apagado si no se excluye churn; umbral 50 % es duro. |
| **Expansión sostenida** *(ancla positiva)* | Media `inflow` m+1…m+6 &gt; 1,3 × (`in12`/12) **y** `cash_end(m+6) > cash_end(m)` **y** sin `caída estructural` en la ventana. | Resultado | 1, 2, 5, 6 | ~16 % (actual); tras filtro de persistencia ~10–12 % | Reversión a la media; estacionalidad fiscal. |
| **Entrada en tensión de caja** | Primer mes con `runway` &lt; log-equivalente a &lt;0,25 meses de caja **o** `cash_end&lt;0`, tras ≥3 meses con runway “sano” y `cash_end≥0`. | Transición | 3, 4, 6 | Estimada 3–6 % | Depende de reconstrucción de caja; definir burn con `max(out3,out12)`. |
| **Bache de caja (no estructural)** | Caída de `cash_end` &gt; 1 IQR company en un mes, con recuperación a nivel previo en ≤2 meses **y** sin `caída estructural` de cobros en 6 m. | Síntoma / contraste | 4, 5 | ~101 / 902 ≈ **11 %** empresas con patrón (≥12 m) | Fácil de confundir con ruido FX/reconstrucción. |
| **Impago / obligación omitida** | (A) `overdue_90_ap` crece vs mediana 6 m y `late_share_ap` alto; o (B) hueco en `payroll` / `tax` trimestral / `debt_service` cuando el patrón de 12 m lo anticipaba. | Resultado (crédito) | 3, 5, 6 | A estimar; hoy no es evento en `targets.py` | Falsos positivos por categorización `-`; IVA trimestral. |
| **Sano sostenido** | 12 meses sin caída estructural, sin entrada en tensión, sin obligación omitida; `runway` estable o al alza. | Estado positivo | 1, 2 | Estimada 15–25 % | Sesgo a empresas grandes / con ERP. |
| **Apagado / fin de rastro** | `months_since_final_tx` pasa a &gt;0 de forma definitiva. | Cobertura / churn de producto | Producto Embat, no salud | 121 cos (**~9 %**); filas evento 3 % | **No calibrar el score de salud** contra esto. |

**Ancla principal:** el par **caída estructural ↔ expansión sostenida** (ranking / AUC simétrico). **Ancla adversa secundaria:** entrada en tensión de caja. **Apagado:** monitor de retención Embat, no leaderboard de salud.

---

## 4. Críticas a la propuesta actual

1. **Bien:** sacar apagado del núcleo y degradar “caída de cobros cruda” si no se distingue bache — los datos lo respaldan (apagados líquidos; decline solapa churn).  
2. **Bien:** “entrada en tensión” como transición — el evento actual de saldo negativo es demasiado circular (~31 % ya negativos) y persistente por reconstrucción.  
3. **Riesgo:** “incumplimiento” por obligación omitida / AP&gt;90d es **correcto como señal de crédito**, pero **no parece el latente principal del generador**. El generador se ve más en **trayectorias de cobros+caja** (arquetipos regla + k=2 alza/baja) que en impagos ERP (36 % sin ERP; el test oculto puede venir sin facturas). Si el leaderboard generaliza a 60–80 empresas OOD, un ancla solo-ERP falla.  
4. **Falta simetría explícita:** la propuesta lista recuperación y sano sostenido, pero el sistema actual de pesos se calibra más contra adverse. El enunciado (Northbrook 45→65 vs Velasco 82→68) exige **ancla positiva de igual rango**.  
5. **“Caída de cobros → solo feature”** es demasiado agresivo: en este dataset **decline es el mejor proxy observable del régimen adverso**. Debe ser **evento (redefinido con persistencia)**, y la mediana cruda 6/12 puede además vivir como feature.  
6. **Clustering:** no esperéis que k-means en 24+24 meses dé siluetas altas; el generador mete regímenes **en slopes/deltas**, no bolas esféricas en ℝ⁴⁸. Validar arquetipos con reglas + GMM en pendientes, no solo silueta.

---

## 5. Cómo validaría los eventos sin etiquetas

1. **Huella de generador:** clasificar regímenes por reglas (pendiente/IQR de `oper_in` y `cash_end` en la vida relativa) y exigir que el evento adverso se concentre en `declive`/`caja_erosion`/`apagado` y el positivo en `creciente`/`caja_acumula` — ya se cumple con decline/growth.  
2. **Persistencia y no circularidad:** P(evento a m+3 | evento a m); fracción de cash_stress con negativo previo; solapes (churn∩decline).  
3. **Anticipación (pregunta 6):** mes en que el score cruza umbral vs mes del evento; comparar con baseline “último valor de cobros”.  
4. **Estabilidad bache vs estructural (pregunta 4):** eventos que revierten en ≤2 m vs los que no; el score no debe caer igual en ambos.  
5. **Split por `group_id`:** pureza de arquetipo entre filiales es baja (~7 % grupos multi-empresa homogéneos) → los regímenes parecen **por `company_id`**; validar sin leakage de grupo igual.  
6. **Ablation ERP / historia corta / OOD moneda:** si el AUC del ancla se hunde sin ERP, no puede ser el único target del leaderboard.  
7. **Consistencia lineal vs árbol:** ya mediste AUC igual logística/LightGBM → el techo es la etiqueta; cambiar el evento mueve el techo más que el modelo.

---

## 6. Preguntas para la organización

1. ¿El fichero de submission del test oculto es un **score continuo por empresa (y mes?)** o una etiqueta/ranking derivado de un latente de trayectoria?  
2. ¿El latente de generación incluye **regímenes nombrados** (growth/decline/shock/churn) a nivel `company_id`? ¿El churn es “baja Embat” o “cese de actividad”?  
3. ¿La métrica del leaderboard es **AUC/ranking contra un target binario**, Spearman vs score latente, o error en trayectoria (Δsalud)?  
4. ¿Se evalúa **simetría** (mejora y deterioro) por separado o solo un adverse compuesto?  
5. ¿Las 60–80 ocultas pueden no tener ERP / historia &lt;12 m / otra moneda en la misma proporción que el train?  
6. ¿El apagado anticipado cuenta como acierto de salud o solo de monitor de conexión?

---

## 7. Verificaciones hechas (acceso a datos: sí)

### 7.1 Eventos actuales (filas válidas, `month_idx≥5`)

| Evento | Tasa |
|---|---|
| `churn_6m` | 3,00 % |
| `cash_stress_6m` | 5,38 % |
| `decline_6m` | 16,97 % |
| `positive_6m` | 16,28 % |
| `adverse_6m` | 22,32 % |

Correlaciones fila a fila: cash_stress ≈ independiente (−0,03); churn–decline **+0,24**; decline–growth **−0,17**. Dado churn, P(decline)=**0,69**.

### 7.2 Clustering de trayectorias normalizadas

- **Método:** empresas con ≥12 meses (898; 742 tras quitar outliers de norma L2 / componentes extremos). Por empresa: `oper_in` y `cash_end` escalados por mediana/IQR, remuestreados a 24 puntos de vida relativa → vector 48-D. K-means y ward; k∈[2,8]; silueta.
- **Sin filtrar outliers:** “mejor” k=2 silueta **0,95** — **engaño** (1 empresa domina).
- **Tras filtro:** mejor silueta **k-means k=2 → 0,074** (ward k=6 → 0,058). **No hay clusters esféricos claros** en ℝ⁴⁸.
- **k=2 interpretable (742 cos):**

| Cluster | n | % | Lectura | `r_decline` | `r_growth` | `r_cash` | % churn final |
|---|---|---|---|---|---|---|---|
| C0 caja/cobros a la baja | 355 | 47,8 % | erosión de caja (centroid late caja −0,31) | 0,188 | 0,079 | 0,058 | 9,9 % |
| C1 caja/cobros al alza | 387 | 52,2 % | acumulación de caja | 0,127 | 0,250 | 0,061 | 6,7 % |

- **k=4 (sil 0,052), útil para narrativas:**

| C | n | Arquetipo | Ever decline | Ever growth |
|---|---|---|---|---|
| 0 | 303 | caja en erosión | 38 % | 31 % |
| 2 | 304 | caja acumulando / cobros ↑ | 29 % | 64 % |
| 3 | 125 | declive de cobros | 53 % | 53 % |
| 1 | 10 | extremo creciente (cola) | 20 % | 80 % |

- **Solo historia 24 m (302 cos tras filtro):** misma lógica dicotómica alza/baja; siluetas ~0,03–0,06.
- **Bache con rebote:** en centroides k-means es **minoritario** (~4–8 % con heurística de tercios). Por reglas (abajo) sube a **76 / 902 ≈ 8,4 %**.

### 7.3 Arquetipos por reglas (huella de generador más legible)

Sobre 902 empresas con ≥12 m:

| Arquetipo | n | Tasa media decline | Tasa media growth | Ever decline | Ever growth |
|---|---|---|---|---|---|
| creciente | 262 | 0,043 | 0,321 | 14 % | 76 % |
| declive | 210 | 0,273 | 0,054 | 58 % | 24 % |
| estable | 103 | 0,117 | 0,124 | 39 % | 50 % |
| apagado | 93 | 0,518 | 0,092 | 75 % | 24 % |
| bache_rebote | 76 | 0,178 | 0,194 | 45 % | 57 % |
| caja_erosion | 71 | 0,121 | 0,051 | 28 % | 25 % |
| mixto | 45 | 0,100 | 0,133 | 29 % | 53 % |
| caja_acumula | 42 | 0,139 | 0,254 | 33 % | 74 % |

Pendiente de cobros vs ever-decline / ever-growth: **AUC 0,74 / 0,74**. Pendiente de caja: **0,53 / 0,65** (la caja discrimina peor el decline etiquetado; mejor el growth).

**Grupos empresariales:** en 121 grupos con ≥2 empresas clusterizadas, solo **7 %** son homogéneos de arquetipo; share del modo ≈ **0,49**. El generador **no copia el mismo régimen a todo el grupo**.

**Patrones de caja:** ~101 empresas con bache que rebota; ~55 con caída que se mantiene (≥2 meses). Coincide con la pregunta 4 del reto.

### 7.4 Conclusión operativa para el score

| Target probable del leaderboard | Qué alinear |
|---|---|
| **Más probable:** ranking / score continuo alineado a **trayectoria latente** (mejora vs deterioro de cobros+caja), simétrico | Anclas: caída estructural + expansión; features de pendiente/runway/actividad; explicar Δ mes a mes |
| **Plausible como capa adversa:** transición a tensión de liquidez | Evento transición runway/caja, no “algún negativo futuro” |
| **Poco probable como único KPI:** apagado o saldo negativo crudo | Usar en producto (retención / alerta de liquidez), no para calibrar el 0–100 de salud |
| **Necesario para el jurado de producto (no solo leaderboard):** bache vs estructural + antelación medida | Eventos de contraste + monitor |

En una frase: **calibrad el score como un lector de regímenes de trayectoria que el generador ya dejó en cobros y caja; no como un predictor de “se apagó la serie” ni de “el saldo reconstruido cruzó cero”.**
