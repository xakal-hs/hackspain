<!-- modelo: deepseek-v4-flash vía Helmcode · lente: metodologia · 54s · uso: None -->

# Respuesta — lente de weak supervision, PU y supervivencia

> **Nota previa sobre datos.** No tengo acceso a las herramientas del repo ni a `research/data/*.parquet`, así que **todas las cifras que doy son estimaciones** ancladas a los números que sí aparecen en el brief y en `features.md` (1286 empresas, 250 grupos, 24 meses, tasas 3 %/5 %/17 %/16 %). Donde digo "mediría" hablo de lo que habría que calcular; donde doy un rango, es un orden de magnitud, no una medición.

---

## 1. Posición

El error de diseño central es que **los cuatro eventos actuales están construidos con las mismas variables que las features que dicen predecir**, así que una parte sustancial del AUC (el 0,77 de "saldo negativo", buena parte del 0,63–0,76 por evento) es **autocorrelación disfrazada de predicción**, no información nueva. Un evento útil sin etiquetas debe ser (a) **una transición, no un estado** —lo que en estadística es un *hazard*, no una *prevalencia*—, (b) **medido con datos que no están en el lado derecho del modelo** cuando se calibra, y (c) **evaluado con C-index / hazard a horizonte, no con AUC a 6 meses**, porque el horizonte de 6 meses es arbitrario y con un evento al 3 % el AUC tiene un IC95 % de ±0,07–0,10. Propongo pasar de "cuatro logísticas independientes promediadas" a un **modelo multi-estado (competing risks) en tiempo discreto**, con dos factores latentes (tensión y momentum) como salida, y tratar el "apagado" como **censura / producto aparte**, no como evento de salud. El ancla debe ser una **transición a tensión de caja** validada *por encima de la persistencia trivial*, con la **omisión de obligación recurrente** como evento hermano no circular.

---

## 2. Veredicto sobre cada evento actual

| Evento actual | Veredicto | Motivo estadístico |
|---|---|---|
| **Apagado (3 %)** | **Separar como otro producto** y usar como **censura** en el análisis de supervivencia | Hay dos problemas: (i) el 63 % de los apagados no mostró síntomas financieros previos, lo cual contradice que sea un evento de *distress*; (ii) el propio brief ya sospecha que es desconexión de Embat. Si es censura informativa (el "sano que se va"), **no** puede entrar como positivo en un clasificador de salud: contamina la etiqueta. Como KPI de retención sí vale, y como estado absorbente en un modelo multi-estado es exactamente su papel natural. |
| **Saldo negativo (5 %)** | **Redefinir como transición** (primer cruce bajo 0 tras ≥3 meses ≥0) y **auditar circularidad** | Es el caso más claro de circularidad: `cash_end` es feature (meses de caja) y aparece en la definición del label futuro. El AUC 0,77 es, en buena parte, la persistencia de una serie casi integrada. Como *estado* mezcla prevalencia y severidad; como *hazard de primera entrada* (entry hazard) es un objeto estadístico bien definido y comparable entre empresas. |
| **Caída de cobros (17 %)** | **Degradar a feature/síntoma** o **redefinir como quiebre estructural** | Una tasa del 17 % no es un evento raro: es un régimen dentro de la distribución normal de una pyme. Además solapa al 69 % con apagado, es decir, **mide casi lo mismo** que el otro evento (kappa alto). Un evento que solapa >0,6 con otro no es un target independiente: o se fusionan, o uno es síntoma del otro. Si se mantiene, exigir **3 meses consecutivos** y un **test de cambio estructural** (CUSUM / PELT), no la comparación de medianas de dos ventanas. |
| **Crecimiento (16 %)** | **Redefinir con calendario** (YoY, no media de 12) y **simetrizar con el evento adverso** | La definición actual (`in6` futuro > 1,3 × base media y `cash_end` futuro > `cash_end` actual) usa las **mismas columnas que el score**. Es una etiqueta autorreferencial. Además, "media de 12" mezcla años con estacionalidad trimestral de impuestos; el propio brief ya corrigió esa trampa en features y no la corrigió en el evento. |

---

## 3. Eventos recomendados

Símbolos: **T** = transición (hazard), **E** = estado positivo, **S** = síntoma/feature. "Circ." = riesgo de circularidad (1 = bajo, 3 = alto).

| # | Nombre | Definición implementable (columnas del panel) | Tipo | Preguntas del reto | Frecuencia estimada | Circ. | Riesgos |
|---|---|---|---|---|---|---|---|
| **A** | **Entrada en tensión de caja (ancla)** | Primer mes *m\** tal que `cash_end(m*) / burn(m*) < 0,25` meses, habiendo estado `≥0,5` durante `m*-3..m*-1`. `burn = max(media_3(payroll+tax+fees+debt_service+pagos), media_12(...))`. Excluir `m*>21` (cola truncada del mes 24). | T (hazard de primera entrada) | 3, 4, 5, 6 | 4–6 % de las empresas-mes elegibles a 6 m | 2 | Umbral 0,25 sensible al ruido de reconstrucción; requiere **evaluar el lift sobre la persistencia** (§5). |
| **B** | **Primer cruce a caja negativa** | Primer mes con `cash_end < 0` tras ≥3 meses `cash_end ≥ 0`. | T | 3, 4 | 3–4 % | 3 | Muy circular si las features incluyen `cash_end`. Solo usar como *endpoint de validación*, no como target de entrenamiento con features de caja. |
| **C** | **Omisión de obligación recurrente** | Para cada `category ∈ {salary, tax, debt_repayment}`: frecuencia modal por empresa (p. ej. mensual/trimestral detectada por mediana de gaps); mes en que la obligación toca y su importe cae <30 % de su mediana histórica. Excluir si `has_erp=False` y no hay `debt_schedule_config`. | T / S | 3, 4, 5, 6 | 8–15 % (mayor en ERP) | **1** | Detección de periodicidad frágil en historia corta (<12 m); necesita `debt_schedule_config` (solo 87 filas) o inferencia por `debt_repayment`. |
| **D** | **Deterioro de disciplina de pago** | Mediana de días de retraso AP en `m-2..m` menos mediana en `m-5..m-3` > +15 días, mantenido ≥2 meses. Usar `pending_amount ≠ 0 & status ≠ paid`, ignorando `payment_date` en overdue. | T | 3, 5, 6 | ~10 % (cobertura 56 %) | 2 | Denominador sesgado por ERP; usar suelo 0,1 % del volumen propio. |
| **E** | **Cobro perdido estructural (sustituto de "caída de cobros")** | 3 meses consecutivos con `inflow` < 70 % del mismo trimestre del año anterior (YoY), **o** un test de quiebre (CUSUM) significativo a p<0,05. | T | 2, 3, 4 | 6–9 % | 2 | Con solo 24 meses, la comparación YoY tiene 12 puntos; en empresas con <18 m de historia, no aplica (marcar NA, no 0). |
| **F** | **Crecimiento sostenido** | 3 meses consecutivos con `inflow` > 120 % del mismo mes del año anterior **y** pendiente de `cash_end` ≥ 0 (regresión robusta a 6 m). | E | 1, 2 | 8–11 % | 2 | Simetrizar con E para que el score no sea asimétrico; sin esto, la cara positiva queda dominada por tamaño. |
| **G** | **Recuperación mantenida** | Estado A/B en `m`; en `m+3` `cash_end/burn ≥ 0,5` y sin reentrada hasta `m+6`. | T (salida de estado) | 2, 4 | 3–5 % | 2 | Fuertemente ligado a reversión a la media si el estado de partida fue un pico puntual; condicionar a que el mes de entrada no fuese un outlier. |
| **H** | **Sano sostenido (rediseñado)** | 12 meses sin A/B/C **y** en el quintil inferior de volatilidad a la baja **y** `months_since_last_tx = 0` todos los meses. | E | 1 | 8–12 % | 2 | Tal como está en la propuesta (12 m sin eventos) incluye media muestra por construcción en un panel de 24 m; añadir el filtro de volatilidad y actividad. |
| **I** | **Pérdida de cobertura (no salud)** | `months_since_last_tx > 0` de forma definitiva **o** caída de `n_tx` a 0 con producto bancario aún activo. | Estado aparte / censura | — (KPI de retención) | ~3 % | 1 | **No entra en el score**. Es el antiguo "apagado" reetiquetado honestamente. |
| **J** | **Estrés de línea de crédito** | `lc_drawn/lc_limit > 0,85` y en aumento durante 2 meses. | S | 3, 5 | 5 % sobre el 14 % con dato ⇒ ~0,7 % del panel | 1 | Cobertura 14 %: no puede ser target, sí alerta explicativa. |

**Ancla principal: A (entrada en tensión de caja)**, con **C (omisión de obligación)** como ancla secundaria no circular. A es una transición, tiene frecuencia manejable, es explicable en una frase al jurado ("se le está acabando el efectivo de la cuenta") y conecta con la prueba de los 100 000 €. C es el único evento del conjunto que **no** se construye con las mismas variables que las features de caja, así que sirve para testear si el score captura algo más allá de la autocorrelación.

**Cómo combinar los eventos.** No promediando pesos de logísticas separadas. Dos alternativas defendibles:

1. **Competing risks en tiempo discreto (recomendado).** Estados: `H` (sano), `W` (tensión), `S` (crisis), `E` (salida/censura). Modelo multinomial logit por persona-mes sobre las transiciones `H→W`, `W→H`, `W→S`, `S→H`, `S→E`, con **priors jerárquicos / L2 fuerte** para estabilizar transiciones raras. El score sale del **hazard acumulado a h meses** y del **C-index**, no de una media de AUCs.
2. **Índice latente de dos factores.** Factor analysis o PLS sobre los indicadores de evento y las features ⇒ `F1 = tensión` (carga A, B, C, D), `F2 = momentum` (carga E, F, G). El número del leaderboard es una transformación monótona de `F1 − F2`. Ventaja: separa las dos caras sin promediar, y da una métrica de cada lado del reto.

Descartaría la media de pesos de logísticas independientes: **mezcla log-odds no comparables** entre eventos con prevalencias 3 % y 17 %, y el evento raro domina por varianza, no por señal.

---

## 4. Críticas a la propuesta actual

1. **"Incumplimiento" es la mejor idea y la peor implementada.** Conceptual y estadísticamente es lo correcto (evento no circular, imputable, con análogo de consumidor). Pero exige inferir periodicidad por empresa, y con el 31 % de empresas con <12 meses de historia eso se rompe. Debe ir con regla de "NA si no hay ≥3 ciclos observados", **no imputar 0** (que es lo que hace `w(cond, e)` en `targets.py`, dejando nulos explícitos: bien).
2. **"Entrada en tensión" como transición: bien, pero sin test de circularidad.** La propuesta no dice cómo evitar que el modelo aprenda `cash_end_t ≈ cash_end_{t+h}`. Sin baseline de persistencia, el AUC no prueba nada.
3. **"Bache vs caída" no se resuelve comparando ventanas.** El propio `features.md` dice AUC 0,50. La respuesta correcta es un **test de cambio estructural** (CUSUM, PELT, Chow) o un ratio de varianza, y validarlo contra el evento G (recuperación) y A (entrada) por separado: un mismo mal mes debe dar P(G|bache) alta y P(A|caída) alta.
4. **"Sano sostenido = 12 meses sin eventos"** es tautológico en un panel de 24 meses: la mitad de la muestra lo cumple por construcción. Falta el filtro de volatilidad y de actividad que he añadido en H.
5. **"Recuperación" sin condicionar al punto de partida** mide reversión a la media. Hay que exigir que el estado de entrada no sea un único mes outlier.
6. **"Caída de cobros pasa a feature"**: de acuerdo, pero la propuesta no aborda que su versión actual es **regresión a la media disfrazada de evento** (esto ya está anotado en `features.md`, sección F). Si se queda como feature, debe ser YoY y con suelo.
7. **Nada en la propuesta trata el horizonte.** "6 meses" sigue siendo el horizonte de todo (`add_events` con `horizon=6` por defecto). Con un evento al 3 % y ~40 positivos, el AUC a 6 m tiene IC ±0,07–0,10; el "0,63–0,76" que se compara entre logísticas es **ruido de estimación y no diferencia de señal** hasta que se reporten intervalos. Hay que pasar a C-index / tiempo hasta evento, que es más estable y usa todos los meses censurados.
8. **Correlación intragrupo ignorada.** 1286 empresas en 250 grupos comparten ERP, país y moneda. Cualquier CV por fila **sobreestima** la generalización. Todo debe ir con `GroupKFold` por `group_id` y bootstrap por clúster de grupo.
9. **El mes 24 (sep-2026) es parcial**; `add_events` no lo excluye explícitamente del lado derecho. Hay que forzar `month_idx <= 21` en entrenamiento.

---

## 5. Cómo validar que un evento proxy es bueno sin etiquetas

Cinco pruebas, en orden de coste creciente. Las dos primeras son de higiene (deberían estar ya):

1. **Auditoría de circularidad (leakage).** Para cada par (feature *i*, evento *j*), calcular la correlación entre `X_i(t)` y la **componente futura pura** del evento (el residual del evento tras proyectarlo sobre `X(t)` y sobre `X(t-1)`). Umbral de alarma: |ρ| > 0,4 ⇒ ese par no puede usarse para atribuir poder predictivo.
2. **Baseline de persistencia.** Para cada evento, ajustar la predicción "ingenua" `E_t = f(Y_t)` (mismo evento hoy, o caja hoy). El score tiene que **superar ese baseline** con significación (DeLong o bootstrap por grupo). Si no lo supera, el evento no es un objetivo: es una serie autorregresiva.
3. **Validación temporal (walk-forward).** Train en `month_idx 5–16`, test en `17–21` con al menos 3 folds deslizantes. Reportar C-index con **bootstrap por `group_id`**. Reportar también PR-AUC y *lift* en el decil superior (con prevalencias del 3 % el AUC es engañoso: la línea base ya es 0,5).
4. **Sensibilidad al diseño de la etiqueta.** Variar horizonte (3/6/9/12), umbral (±20 %) y regla de "consecutivo" (1/2/3 meses). Un evento bueno mantiene **el signo** de los pesos y un C-index que decae suavemente. Si los pesos cambian de signo, la etiqueta es artefacto.
5. **Placebo intra-empresa.** Permutar el orden temporal dentro de cada empresa (rompiendo la relación con la trayectoria) y recalibrar. El AUC debe colapsar a ~0,5. Si queda por encima, hay fuga estructural (por ejemplo, un nulo tratado como 0).
6. **Adjudicación experta sobre un estrato.** Muestrear 40 falsos positivos y 40 verdaderos del evento A y pedir a los mentores de Embat / un CFO que digan si el mes señalado era "de verdad" un cambio. Es la **única ground truth real** que se puede obtener en el fin de semana, y sirve para estimar la tasa de error del proxy (una especie de PU con etiquetas parciales).
7. **Comparación entre eventos (kappa).** Con el 69 % de solapamiento apagado–caída, estimar κ. Si κ > 0,6, **fusionar** o declarar uno como manifestación del otro. No tiene sentido calibrar pesos contra dos etiquetas que son la misma.
8. **Test OOD estratificado.** Hold-out por moneda, por `has_erp=False`, por `country` desconocido. Un evento que solo funciona con ERP no generaliza a las 60–80 empresas ocultas.

---

## 6. Preguntas para la organización

1. **¿Qué es exactamente "apagado"?** ¿Cierre de la empresa, o churn de Embat / pérdida de la conexión bancaria? Determina si es censura informativa, evento de retención o producto aparte.
2. **¿El generador sintético tiene un estado latente de salud oculto?** Aunque no lo den como etiqueta durante el hackathon, si existe y pueden liberarlo *después* del scoring, permite estimar la tasa de error del proxy (PU) de forma rigurosa. Es la pregunta más valiosa de esta lista.
3. **¿Qué métrica usa el leaderboard exactamente?** ¿AUC contra alguno de nuestros eventos? ¿Contra un score ground truth? ¿Sobre qué horizonte? Cambia por completo qué evento conviene optimizar.
4. **¿Las 60–80 empresas ocultas están en `groups` de empresas ya vistas?** Si comparten grupo con el train, la CV debe ser por grupo; si no, hay que asumir independencia y el bootstrap cambia.
5. **¿Hay algún label duro disponible posterior?** Impagos reales, discontinuidad del grupo, rating externo. Cualquier cosa, aunque sea para validación y no para entrenamiento.
6. **Horizonte de negocio**: ¿"anticipación" se mide como meses hasta el evento declarado por Embat, o hasta un cambio observable en el rastro? Es la diferencia entre validar contra un hazard y validar contra un quiebre.
7. **¿Exchange rate del test es tan fiable como el de train?** Si es moneda desconocida, muchas features de nivel absoluto (antes filtradas) vuelven a colarse.

---

## 7. Verificaciones hechas

**No tengo acceso a herramientas ni a `research/data/*.parquet`**, así que **no he podido calcular nada**. Lo que sigue es lo que verificaría en el orden dado, y las cifras del apartado 3 son estimaciones ancladas a las tasas del brief, no mediciones.

Para quien ejecute:

| # | Qué verificar | Cómo | Umbral de decisión |
|---|---|---|---|
| 1 | Solapamiento churn–decline | κ de Cohen sobre positivos de `churn_6m` y `decline_6m` en `panel.parquet` | κ > 0,6 ⇒ fusionar |
| 2 | Circularidad de cada feature vs cada evento | Correlación con residual tras proyectar el evento sobre `X_t` y `X_{t-1}` | \|ρ\| > 0,4 ⇒ descartar el par |
| 3 | Baseline de persistencia | AUC de `cash_end_t` prediciendo `cash_stress_6m`, y de `decline_6m` prediciendo `decline_6m` | Si el score no supera al baseline con bootstrap por grupo, el evento no es objetivo |
| 4 | IC95 % de cada AUC por evento | Bootstrap por `group_id`, B = 1000 | Churn ±0,07–0,10 · decline ±0,03 |
| 5 | Sensibilidad del horizonte | C-index con h = 3, 6, 9, 12 | Signos estables de los pesos; decaimiento suave |
| 6 | Estabilidad del mes 24 | Recalcular todo con `month_idx ≤ 21` | Si las tasas cambian >1 pp, hay truncamiento |
| 7 | Placebo intra-empresa | Permutar meses dentro de empresa y recalibrar | AUC placebo debe ser ≈ 0,50 |
| 8 | Contribución del factor no circular C | AUC de features de pago/obligación sobre el evento C, vs persistencia | Es el test de "el score aprende algo más que la caja" |

**Conclusión operativa en una frase:** el sistema debe declarar sus eventos como **hazards de transición**, evaluarse con **C-index y comparación contra persistencia**, y **separar el apagado como censura/producto** para que el score mida salud y no continuidad en la plataforma.