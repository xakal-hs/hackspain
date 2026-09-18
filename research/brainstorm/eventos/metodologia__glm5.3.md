<!-- modelo: glm5.3 vía Helmcode · lente: metodologia · 256s · uso: None -->

# Eventos como verdad del score: lente de supervisión débil

## 1. Posición

Los eventos actuales no son etiquetas de salud sino cruces de umbral de las mismas series que alimentan las features, así que parte del AUC (0,77 frente a saldo negativo) es identidad mecánica y no predicción; antes de calibrar pesos hay que auditar esa circularidad con ablación. El problema correcto no es "evento en ventana fija de 6 meses" sino supervivencia en tiempo discreto con riesgos en competencia: el apagado corta la observabilidad de todos los demás eventos (69 % de solapamiento con declive es consecuencia de la definición, no del mundo) y además es una censura probablemente informativa (baja de Embat ≠ muerte). Con una base del 3 %, el AUC tiene un error de ±0,04–0,05 con clustering por grupo (estimación): calibrar pesos contra apagado puro es ruido, y por eso el ancla debe ser el evento adverso con potencia (declive causa-específico, ~13–15 % estimado tras quitar contaminación de apagado) más uno con significado de impago (incumplimiento de obligación). Para combinar eventos, ni promediar coeficientes ni un compuesto binario (ya demostró que el declive domina y la disciplina de pago muere): un índice latente único con un enlace por evento, o etiquetas blandas estilo modelo de etiquetas, respetando la correlación conocida entre eventos. La validación sin etiquetas es un paquete: ablación de circularidad, sensibilidad a umbrales y horizonte, triangulación entre canales (banco vs ERP vs nómina/impuestos) y redescubrimiento de patrones económicos conocidos.

## 2. Veredicto sobre cada evento actual

| Evento actual | Veredicto | Motivo |
|---|---|---|
| Apagado (3 %) | **Separar como otro producto** + usarlo como **censura/riesgo en competencia** para los demás | Base del 3 %: potencia insuficiente para calibrar pesos. Es ambiguo entre muerte y baja de Embat. Contamina mecánicamente al declive. Redefinir: silencio ≥2–3 meses y desdoblar en "apagado total" (también cesa ERP) y "apagado solo bancario" (churn de canal). Silencio al final de serie = censura administrativa, no evento |
| Saldo negativo (5 %) | **Redefinir** como transición material | El 23 % de eventos con negativos en t−3..t−1 delata parpadeo alrededor de cero; el 46 % de persistencia >3 meses sugiere artefacto de reconstrucción o sobregiro legítimo (el 20 % tiene póliza). Exigir materialidad (caja < −0,25 × gasto o runway < 0,25), 2 meses consecutivos, y condicionar severidad al crédito disponible. El AUC 0,77 es circular: los meses de caja y el evento comparten variable |
| Caída de cobros (17 %) | **Redefinir y mantener como ancla** (causa-específica); solo la versión mensual/corta se degrada a feature | Es el único evento adverso con potencia estadística. Degradarlo entero deja la calibración en manos de eventos raros. Redefinición obligatoria: censurar en apagado (riesgos en competencia), porque hoy ~2 pp de sus 17 % son muerte mecánica vía cobros a cero |
| Crecimiento (16 %) | **Redefinir** | Exigir media anual (`in12`) excluye al 31 % con historia <12 meses, justo el caso del test oculto. Usar mediana de 3m futuros vs mediana de 6–12m previos, mínimo 6 meses de historia, y robustez a one-offs (pago bulk único) |
| `adverse` compuesto (en `targets.py`) | **Eliminar como objetivo de calibración** | La unión de causas hace que el evento más frecuente domine la logística; ya se comprobó (disciplina de pagos a peso 0) |

## 3. Eventos recomendados

| # | Nombre | Definición implementable | Tipo | Preguntas | Frecuencia | Riesgos |
|---|---|---|---|---|---|---|
| 1 | **Incumplimiento de obligación** | Primer mes en que tocaba pago y no aparece: (a) sin `salary`/`social_security` con nómina en ≥2 de los 3 meses previos y actividad continua; (b) sin `tax` en mes fiscal (ene/abr/jul/oct) con `tax>0` en ≥1 de los 2 trimestres fiscales previos; (c) cuota de préstamo solo para los ~87 productos con `debt_schedule_config` (cobertura mínima, auxiliar) | Resultado | Q3, Q4, Q5, Q6 | **2–6 %** (estimación) | 25 % de filas sin categorizar → falsos positivos (pago hecho pero no categorizado); pagos por `bulk_payment` u otra cuenta; exigir mín. historia |
| 2 | **Declive causa-específico** (ancla principal) | Mediana de `inflow` de los 6m siguientes < 50 % (sensibilidad 40–60 %) de la mediana de los 12 previos, **censurando la fila en el mes de apagado** | Resultado | Q3, Q4, Q6 | 13–15 % (estimado; 17 % medido con contaminación: 69 % de 3 % ≈ 2 pp) | Momentum compartido con features 1 y 7 → reportar AUC ablado |
| 3 | **Entrada en tensión de caja** | Primer mes con runway < 0,25 o caja < −0,25 × gasto, **2 meses consecutivos**, tras ≥3 meses con runway ≥ 1; severidad distinta si hay crédito disponible en póliza | Transición | Q3, Q6 | 4–7 % (estimación; 5 % medido sin condiciones) | **Circularidad alta** con feature "meses de caja": solo válida con AUC ablado; umbral 0,25 arbitrario → sensibilidad 0,15–0,5 |
| 4 | **Crecimiento sostenido** | Mediana de inflow 3m futuros > 130 % de mediana 6–12m previos, `cash_end` en t+3 > t, incremento no dominado por un cobro puntual (p. ej. `bulk_collection` < 50 % del incremento), mín. 6m historia | Resultado (positivo) | Q2 | 10–16 % (estimación; 16 % medido con otra base) | Regresión a la media; estacionalidad trimestral (por eso mediana, no media) |
| 5 | **Recuperación sostenida** | De estado de tensión a runway ≥ 1 durante ≥3 meses, con mediana de cobros de esos 3m ≥ mediana previa de 12 (nivel, no solo salida del estado) | Transición (positiva) | Q2 | 3–6 % (estimación) | Mayoría es regresión a la media: por eso se exige nivel y persistencia |
| 6 | **Apagado total / bancario** | ≥3 meses consecutivos sin movimientos antes de fin de serie; "total" si además deja de emitir facturas; "bancario" si el ERP sigue vivo | Resultado (absorbente) + censura | Producto de retención (aparte) | 3 % medido (conjunto); desglose 1,5–2,5 % / 0,5–1,5 % (estimación) | Silencio de fin de serie es censura, no evento; doble análisis (como evento y como censura) |
| 7 | Bache vs caída | Taxonomía post-hoc: caída de nivel con recuperación ≥80 % en ≤2m = bache; sin recuperación a +3m = caída | Taxonomía de evaluación (no ancla) | Q4 | — | No sirve para calibrar pesos (necesita 3–6m de futuro: censura fuerte); sirve para evaluar la lógica de alertas |
| 8 | Solidez sostenida | Estado: runway ≥6m, vencido >60d ≈ 0, sin incumplimientos en 12m, base de clientes estable | Estado positivo | Q1 | 10–15 % (estimación) | Es la complementaria de los adversos: en lógica PU es "no etiquetado fiable", no prueba de excelencia. Validar por estabilidad (mismo decil superior ≥6 meses), no calibrar contra él |

**Ancla principal: declive causa-específico (#2)**, por potencia; **incumplimiento (#1)** fija el significado semántico ("lo que un prestamista teme"). 

**Cómo combinarlos.** Índice latente único: score s = Σ w_f · percentil_f; cada evento k con P(evento_k) = σ(α_k + β_k·s), β_k ≥ 0, ajustado por máxima verosimilitud conjunta (modelo de un factor / multitarea con interceptos propios). Esto respeta que cada evento tiene base rate e informatividad distintas, evita el dominio del evento frecuente (se pueden reponderar las verosimilitudes por prioridad de producto), y da una sola explicación. Alternativa consistente con weak supervision: modelo de etiquetas tipo Dawid-Skene/Snorkel con los eventos como anotadores y corrección de su correlación conocida (apagado↔declive), produciendo etiquetas blandas. Promediar coeficientes de logísticas independientes es el caso degenerate donde se fuerza β_k igual entre eventos: es lo que ya falló.

## 4. Críticas a la propuesta actual

1. **Dirección correcta, potencia sacrificada.** Sustituye el único evento adverso frecuente (17 %) por eventos que serán raros (incumplimiento est. 2–6 %): los pesos ganarán varianza. La solución no es elegir, es mantener el declive redefinido como ancla de potencia.
2. **"Entrada en tensión" no resuelve la circularidad.** Sigue definida sobre la variable de la feature dominante; condicionar el estado previo corrige la mezcla incidencia/prevalencia, pero el AUC seguirá inflado. Sin ablación, ese número no significa nada.
3. **Mezcla de severidades.** Runway bajo con póliza disponible (sobregiro caro pero viable) y negativo sin crédito (quiebra técnica) no son el mismo evento; el 20 % con póliza lo demuestra.
4. **"Caída estructural" como evento exige 3–6 meses de futuro observado**: con entradas escalonadas (31 % con <12m) y censoring en apagado, las filas elegibles se desploman. Como taxonomía de evaluación (mi #7) funciona mejor.
5. **"Recuperación" sin condición de nivel es regresión a la media institucionalizada** — el mismo error por el que ya descartaron el declive relativo al trimestre.
6. **"Sano sostenido" es ausencia de evidencia, no evidencia de excelencia**, y el requisito de 12 meses excluye a las de historia corta, que son justo el test oculto.
7. **Nadie trata el solapamiento 69 % estructuralmente**: sin riesgos en competencia, el declive sigue midiendo "muerte inminente vía cobros a cero".
8. **Falta el protocolo de anticipación (Q6)**: no es un evento, es una métrica sobre lead times con censura (mes del evento − primer mes de alerta, estimado con Kaplan-Meier invertido sobre no-eventos censurados). Si no se define ya, no habrá número para el jurado.
9. **Validación y bootstrap por `group_id`**, no por empresa: 250 grupos, flujos intragrupo del 27 % del volumen bruto; el clustering por empresa inflará la confianza.

## 5. Cómo validar los eventos sin etiquetas

1. **Ablación de circularidad**: para cada evento, reentrenar sin las features construidas sobre las variables que lo definen. ΔAUC > 0,03–0,05 (umbral estimado) ⇒ etiqueta demasiado cercana al modelo.
2. **Sensibilidad de definición**: repetir con horizonte 3/6 y umbrales ±20 %. Si el ranking de features cambia (Spearman < 0,7, objetivo estimado), la "verdad" es frágil y los pesos heredarán ese capricho.
3. **Triangulación de canales**: una empresa que muere deja de pagar impuestos, nóminas y facturar a la vez. Si el apagado bancario no viene acompañado de cese ERP, es churn. Esto valida el evento #6 y separa sus dos modalidades. Igual dentro de #1: un incumplimiento creíble debería verse en la caja retenida o en `overdue_ap` subiendo.
4. **Validez de constructo por redescubrimiento**: entrenar contra el evento y comprobar que recupera relaciones económicas conocidas (deuda nueva con caja cayendo ⇒ más riesgo; concentración de clientes ⇒ más; caja al alza ⇒ menos). Un proxy bueno reordena el mundo como se espera; uno ruidoso, no.
5. **Coherencia temporal**: hazard estable por antigüedad y mes calendario; artefactos en el borde de la serie delatan censura mal tratada. Esperado AUC(h=3) ≥ AUC(h=6); si se invierte, fuga o artefacto.
6. **Incertidumbre honesta**: bootstrap por grupo; con base del 3 %, el IC del AUC es ±0,04–0,05 (estimación) — ninguna decisión de pesos por debajo de esa diferencia. Reportar también AUPRC y precisión@k: con prevalencia del 3 %, un AUC 0,75 puede tener precisión inútil para el monitor.
7. **Calibración por deciles**: frecuencia observada vs hazard predicho; descalibración sistemática señala ruido de etiqueta.
8. **Controles positivo y placebo**: inyectar trayectorias sintéticas tipo Velasco/Northbrook y medir disparo y lead time; permutar etiquetas dentro de empresa como control nulo del pipeline.

## 6. Preguntas para la organización

1. En el generador, ¿"apagado" es cierre de empresa, baja de Embat o ambos? ¿Existe una variable latente de muerte/éxito? Una respuesta recalibra todo el sistema.
2. ¿El test oculto comparte generador, reglas de alta y mezcla de historias cortas/sin ERP con el train?
3. ¿El riesgo es compartido dentro del grupo empresarial (cross-default)? ¿El score debe ser por empresa, por grupo, o ambos?
4. ¿Qué definición de "impago" usará el comprador (banco/Embat) para juzgar el score, y con qué horizonte? ¿Hay costes asimétricos FN/FP para el monitor?
5. ¿La póliza de crédito permite saldo negativo legítimo (sobregiro) y a qué coste? Condiciona la severidad de la tensión de caja.
6. ¿Se puede confirmar la convención para meses truncados (sep-2026 parcial, primer mes tras el alta)?
7. ¿Hay opción de etiqueta oculta post-hoc (parámetros del generador por empresa) para validar después del hackathon?

## 7. Verificaciones hechas

**No tengo acceso a herramientas ni a los datos en esta sesión**: no he medido nada. Las cifras que cito están tomadas de los documentos del equipo (apagado 3 %, saldo negativo 5 %, declive 17 %, crecimiento 16 %, solapamiento 69 %, 36 % de apagados con síntomas previos, 23 %/46 %/20 % de saldo negativo, AUC 0,77 y rango 0,63–0,76, 31 % con historia corta, 27 % de volumen intragrupo, 25 % sin categorizar, 87 filas en `debt_schedule_config`). **Todas las frecuencias de los eventos propuestos (incumplimiento 2–6 %, tensión 4–7 %, declive causa-específica 13–15 %, crecimiento 10–16 %, recuperación 3–6 %, desglose del apagado) y los errores estándar del AUC (±0,04–0,05) son estimaciones a priori que deben medirse con `targets.py` antes de tomar ninguna decisión de pesos.**