<!-- modelo: deepseek-v4-flash vía Helmcode · lente: producto · 121s · uso: None -->

# Lente producto Embat: qué eventos vende cada comprador

> **Sin acceso a herramientas ni datos.** Las cifras de frecuencia son las que reporta el brief del equipo (las marco como *medidas por el equipo*) o estimaciones mías a partir de ellas. Todo lo que es inferencia de producto va marcado como hipótesis.

---

## 1. Posición

No existe un evento "verdad" único: existe un **vector de eventos** y cada comprador paga por uno distinto. El leaderboard probablemente premia una sola cabeza (riesgo de caja/incumplimiento), pero el producto que se enseña al jurado debe exponer varias, porque `context/scoring.md` ya dice que *"la métrica cambia con la oferta y con quien mira"*: un mismo 72 no significa lo mismo para un banco que para el CFO. El **apagado es el evento más valioso para Embat** (es su churn, no la salud del cliente) y precisamente por eso **no debe ser ancla de salud**: meterlo en el score de crédito enseña al modelo a predecir bajas de plataforma disfrazadas de deterioro financiero, y el 69 % de solapamiento con la caída de cobros lo confirma. La propuesta actual acierta al separarlo, pero se queda corta: no lo convierte en score propio ni define los eventos de aseguradora y de CFO. Mi recomendación es **un score principal (riesgo de caja/incumplimiento) + tres cabezas específicas** (churn de plataforma, impago a proveedores/cartera, potencial de crecimiento), todas alimentadas por el mismo panel pero con pesos y umbrales por oferta.

---

## 2. Veredicto sobre cada evento actual

| Evento actual | Veredicto | Motivo (lente producto) |
|---|---|---|
| **Apagado** | **Separa como score propio** (no lo borres ni lo uses como salud) | Es el churn de Embat, el evento que justifica el módulo de retención y el upsell. Como ancla de salud contamina: el 22 % se va con >3 meses de caja (*medido*) y solo el 36 % mostró síntomas previos (*medido*). Eso no es una empresa que se muere, es una cuenta que se desconecta. Hipótesis a confirmar con la organización. |
| **Saldo negativo** | **Mantén como síntoma, degrada como objetivo** | AUC 0,77 con la caja de hoy es *en parte circular* (lo dice el propio brief). Vale como **transición** (entrada en tensión) y como explicación para el banco, pero como ancla de calibración premia al modelo que reproduce lo que ya se ve. |
| **Caída de cobros** | **Redefine con persistencia**, no la degrades del todo | La propuesta la degrada a feature. Error parcial: es la única señal con frecuencia alta (17 %, *medida*) y cubre la cara de deterioro. Pero hay que exigir persistencia (que no rebote en ≤3 meses) para separar bache de caída. Como feature sola, pierdes la pregunta 3 ("quién se tuerce aún pareciendo sano"). |
| **Crecimiento** | **Mantén como evento positivo**, refínalo | Es la única ancla de la cara buena (pregunta 2, Northbrook). El problema es que ">130 % de la media y caja al alza" mezcla dos cosas; sepárala en **crecimiento con caja** (sano) y **crecimiento sin caja** (vulnerable). |

**Sobre la pregunta directa "¿es el apagado valioso para Embat aunque no sea salud?"** — Sí, y es el evento con mejor ROI comercial del dataset: es accionable en una semana (playbook de CSM), se puede medir su precisión internamente (sabes quién se fue de verdad) y alimenta un producto distinto (retención) del que vende el score de crédito. Lo que **no** puedes hacer es usarlo para calibrar el 0-100 de salud, porque entonces tu score de crédito está optimizando churn.

---

## 3. Eventos recomendados

| Evento | Definición implementable | Tipo | Preguntas | Frecuencia (est.) | Comprador → decisión | Riesgos |
|---|---|---|---|---|---|---|
| **Incumplimiento de obligación recurrente** ⭐ **ancla principal** | `transactions.category ∈ {salary, social_security, tax, debt_repayment}`: categoría con ≥N ocurrencias regulares en 12m previos que en su ventana esperada (+`debt_schedule_config.next_payment_date`/frecuencia) no aparece en los 3m siguientes | Resultado (adverso) | 3, 5, 6 | 10-15 % (⚠️ estimación; alto riesgo de artefacto) | Banco → no prestar / recortar; CFO → alerta | 25 % sin categorizar y 45 % del importe de entradas sin categoría; meses truncados generan falsos omitidos |
| **Entrada en tensión de caja** | Primer mes con `cash_end`/gasto <0,25 m **o** `cash_end`<0 tras ≥3 meses ≥1 mes de caja | Transición | 3, 4, 6 | ~8 % (est.) | Banco / CFO → vigilar, límite condicional | Umbral 0,25 arbitrario; circular con `cash_end` |
| **Caída estructural de cobros** | Mediana `inflow` 6m <50 % mediana 12m **y** que siga por debajo 3 meses después (no rebote) | Resultado (adverso) | 2, 3, 4 | ~8-10 % tras persistencia (17 % bruto, *medido*) | Banco / aseguradora → precio y exposición | Regresión a la media si no exiges persistencia |
| **Bache de caja** | Mes con `cash_end`<0 o caída >30 % que **revierte** en ≤2 meses | Síntoma (no adverso) | 4 | ~12-15 % (est.) | CFO → "no es caída, no renegocies" | Es la etiqueta negativa de "caída"; sin ella la pregunta 4 sigue en AUC 0,50 |
| **Recuperación** | Pasa de tensión (caja <0,25 m) a caja ≥1 m sostenido 3 meses | Transición (positiva) | 2, 3 | ~6 % (est.) | Banco → subir límite; Embat → upsell | Necesita ≥12m de historia; panel desbalanceado |
| **Sano sostenido** | 12 meses sin evento adverso **y** caja ≥1 m **y** cobros no cayendo >15 % | Estado positivo | 1 | 20-25 % (est.) | Banco → prestar barato; Embat → sello | 31 % de empresas con <12m de historia (*medido*) quedan fuera |
| **Crecimiento con caja** | `in6` >1,3 × (`in12`/12) **y** `cash_end` al alza | Resultado (positivo) | 2 | ~10 % (est.) | Inversor / marketplace → ordenar | Sesgo a empresas con historia larga |
| **Churn de plataforma** (apagado, score propio) | `months_since_final_tx` >0 de forma definitiva **con deuda viva o caja >3 m** (separando baja de cierre) | Resultado (de plataforma) | — (retención) | ~3 % (*medido*) | **Embat** → CSM, retención, descuento | Semántica desconocida: ¿baja o cierre? Confirmar con la organización |
| **Deterioro de cartera de clientes** | Sube `overdue_90_ar` **y** sube `hhi_ar_6m` **o** cae `n_cust_12m`, sostenido 2 meses | Resultado (adverso) | 3, 5 | ~10 % (est.) | **Aseguradora** → prima, límite por comprador | 36 % sin ERP → sin dato; cobertura parcial |
| **Consumo de póliza / deuda nueva con caja cayendo** | `lc_drawn`/`lc_limit` >80 % **o** alta de deuda nueva mientras `cash_end` baja 3m | Transición (adversa) | 3, 6 | ~5 % (est.) | Banco → cortar exposición | `lc_limit` sin dato en 86 % (*medido*); evidencia AUC ~0,50, débil |

**Ancla principal recomendada: incumplimiento de obligación recurrente**, por tres razones de producto: (1) es la señal que un banco entiende en una frase, (2) es observable y explicable ("no pagó la nómina de marzo"), (3) obliga al modelo a mirar comportamiento de pago, no solo caja. Pero **solo si la cobertura de categorías aguanta**: hay que medir cuántos falsos positivos genera en meses truncados antes de adoptarla.

---

## 4. Críticas a la propuesta actual

1. **"Incumplimiento" como ancla única es apuesta fuerte.** Depende de `category`, que falta en el 25 % de filas y el 45 % del importe de entradas. Si el test oculto trae empresas sin ERP o con categorías raras, el ancla se cae. Necesita un plan B.
2. **El apagado "aparte" queda indefinido.** Separarlo está bien; dejarlo sin score propio desaprovecha el evento más vendible para Embat. Debe ser la cabeza de un producto de retención, no una nota al margen.
3. **Falta el comprador aseguradora.** La propuesta no define ningún evento de cartera de clientes (DSO, overdue >90, concentración), y esos son los que determinan prima y límite por comprador.
4. **"Sano sostenido" a 12 meses choca con el panel.** El 31 % tiene <12 meses (*medido*): la etiqueta positiva sesga a las empresas antiguas y el modelo aprende "empresa vieja = sana".
5. **"Entrada en tensión de caja" a 0,25 meses es circular con `cash_end`.** El brief reconoce AUC 0,77 de la caja de hoy frente a saldo negativo. Hay que construirlo desde saldo diario intramensual y días en negativo, que ya da AUC ~0,79 (*en cola*), no desde el cierre de mes.
6. **Degradar la caída de cobros a feature pierde la cara de deterioro sin síntoma de caja.** El hilo conductor del reto (Velasco 82→68) es justo ese: se cae antes de que la caja lo note.
7. **No hay decisión pegada a cada evento.** Un evento sin una acción ("vigilar / recortar / acelerar cobros") no se puede vender. La tabla de la propuesta no dice quién haría qué cuando el evento se dispara.

---

## 5. Cómo validaría los eventos sin etiquetas

1. **Consistencia con la foto final.** `balances` a 1-sep-2026 es el único pseudo-ground-truth duro. Compruebo que las empresas que acaban con saldo negativo o deuda impagada hayan disparado los eventos adversos antes, y que las "sanas sostenidas" terminen con caja positiva. Si no cuadra, el evento está mal definido.
2. **Estabilidad temporal (hold-out por meses).** Defino el evento con datos hasta m y lo mido en m+6. Repito por tramos y verifico que la tasa del evento no se desploma ni explota en ningún tramo: un evento que solo existe en la segunda mitad de la serie es un artefacto.
3. **Placebo temporal.** Barajo el orden de los meses dentro de empresa y compruebo que el AUC del score frente al evento cae a ~0,50. Si no cae, hay fuga.
4. **Anticipación medida.** Uso el evento como ancla *held-out* y mido cuántos meses antes el score cruza el umbral. Es un bonus del reto y a la vez un test de validez: si el evento no se puede anticipar, no es un evento, es una descripción.
5. **Backtest de la decisión del comprador.** Simulo "habría prestado a quien score>X en m, ¿cuántos eventos adversos evitados y cuántos buenos clientes rechazados?". Un evento que no mueve una decisión no sirve, aunque tenga buen AUC.
6. **Coherencia entre cabezas.** Compruebo que churn y salud adversa no van 1:1 (el 69 % de solapamiento del apagado con caída de cobros es la señal de alarma a vigilar). Si dos scores distintos ordenan igual, sobra uno.

---

## 6. Preguntas para la organización

1. **¿El leaderboard pide un score o un ranking, y contra qué etiqueta?** ¿Hay ground truth para la cara positiva o solo para el deterioro?
2. **¿Qué significa exactamente "apagado"?** ¿Es baja de Embat, cierre del negocio o fin del período de datos? De esto depende si es un producto de retención o una etiqueta de salud.
3. **¿El test oculto incluye empresas <12 meses, sin ERP o en moneda distinta?** ¿Cómo se puntúan los huecos?
4. **¿Se puede entregar más de un score?** ¿El jurado premia separar churn de riesgo de crédito o lo penaliza como complejidad?
5. **¿La cobertura de datos (`accounting_status`, categoría) es diferente en el test?** Si el test está peor categorizado, el evento de incumplimiento no es aplicable.
6. **¿Han definido quién paga?** El enunciado dice que la pyme es el comprador obvio, pero `scoring.md` apunta al banco. ¿Cuál pesa en la evaluación?

---

## 7. Verificaciones hechas con los datos

**No tengo acceso a herramientas ni a `research/data/*.parquet` en esta sesión.** No he ejecutado `targets.py` ni `add_events`, ni he medido AUC, tasas por decil ni cobertura real.

Las cifras que cito son **las reportadas en el brief del equipo** (marcadas como *medidas*: apagado 3 %, saldo negativo 5 %, caída de cobros 17 %, crecimiento 16 %; 22 % se apaga con >3 m de caja; 69 % de solapamiento; AUC 0,77 de la caja; 36 % sin síntomas previos; 31 % con <12 m de historia; 86 % sin dato de pólizas) o **estimaciones mías** a partir de ellas, señaladas como `(est.)`. Todas las frecuencias de la tabla de eventos recomendados son estimaciones sin validar. Antes de fijar el ancla principal hay que medir: (a) cobertura real de categorías por mes, (b) tasa de incumplimiento con y sin control de meses truncados, (c) AUC del score actual frente a cada evento propuesto.