<!-- modelo: qwen3.6 vía Helmcode · lente: producto · 61s · uso: None -->



### 1. Posición
No puede existir un único score genérico; la propuesta debe escindirse en tres señales independientes (riesgo de liquidez/caja, riesgo operativo/impago y potencial de mejora) que se recombinen mediante reglas explícitas según el comprador. El "apagado" es un evento de negocio crítico para Embat (retención, upsell y monitor de actividad), aunque no refleje salud financiera intrínseca, por lo que debe tratarse como un producto paralelo y no como etiqueta de calibración del score de riesgo. El framework de los 100.000 € exige jerarquizar la criticidad: la velocidad de evaporación de caja domina sobre el deterioro de DSO/DPO, y el sistema debe distinguir operativamente bache frente a caída antes de emitir un número.

### 2. Veredicto sobre cada evento actual
| Evento actual | Veredicto | Motivo |
|---|---|---|
| **Apagado** | Separar como otro producto ("Monitor de Churn/Actividad") | Mide pérdida de observabilidad y deserción de la plataforma, no riesgo de insolvencia. Su solapamiento (69 % con caída de cobros) lo hace útil para anticipar baja, pero no para calibrar un score financiero. |
| **Saldo negativo** | Mantener y redefinir como "Evaporación acelerada de caja" | Un punto de corte estático es poco informativo; la criticidad de scoring.md exige capturar la *velocidad* de quema. Se mantiene como ancla, pero se reformula para premiar la trayectoria descendente antes de llegar a 0. |
| **Caída de cobros** | Degradar a feature (síntoma de deterioro operativo) | Frecuencia alta (17 %) y casi duplicada con el apagado. Sirve para predecir impago (aseguradoras) y para el diagnóstico del CFO, pero no puede ser objetivo de calibración por su ruido estacional y circularidad. |
| **Crecimiento** | Mantener y redefinir como "Mejora sostenida" | Responde a la pregunta 2 del reto y habilita productos de upsell (líneas de circulante, seguros con prima dinámica). Se redefinen los umbrales para evitar que la reversión a la media genere falsos positivos. |

### 3. Eventos recomendados
| Nombre | Definición implementable (causal, ≤ mes m) | Tipo | Preguntas del reto | Frecuencia estimada | Riesgos |
|---|---|---|---|---|---|
| **Riesgo de Liquidez** (Ancla Principal) | `cash_end` cae a <1,5 meses de caja en ≤2 meses consecutivos tras haber estado >3, o `cash_end` <0. (Calculado con `cash_end` y gasto mensual reconstruido causal). | Resultado / Transición grave | 1, 3, 4, 6 | ~5–7 % (estimación basada en tasa de saldo negativo + solapamiento de quema) | Circularidad con reconstrucción de saldos; requiere validación con flujo diario o mínimos intramensuales. |
| **Riesgo Operativo/Impago** | Presencia de obligaciones recurrentes omitidas (nómina, IVA trimestral, cuota deuda `debt_schedule_config`) o `overdue_90_ar/ap` creciente sostenidamente ≥2 meses. | Síntoma grave / Transición | 3, 5, 6 | ~8–10 % (estimación por densidad esperada de pagos estructurales) | Estacionalidad trimestral; ventanas de cálculo deben excluir meses fiscales para no penalizar correctamente. |
| **Caída Estructural vs. Bache** | Mediana de `in6` (cobros operativos) <70 % de `in12` en 3 meses consecutivos = caída; si `cash_end` se recupera a >2 meses de caja en el mes siguiente = bache. | Clasificador | 4, 5 | ~15 % (estimación por naturaleza de datos sintéticos con estacionalidad) | Ruido por impuestos/estacionalidad; necesita umbral de persistencia de ≥2-3 meses para estabilizar. |
| **Mejora Sostenida** | Cobros operativos >120 % media anual en 3 meses consecutivos, `cash_end` al alza y sin alta neta de deuda `debt_products` que tape huecos. | Estado positivo | 2, 6 | ~12 % (estimación conservadora frente a la tasa original del 16 %) | Reversión a media; empresas en estacionalidad alta pueden falsear la señal si no se estacionaliza la ventana. |
| **Churn de Plataforma** | `months_since_last_tx` >30 días causal + sin reconexión en los 2 meses siguientes. | Resultado de negocio | 6 | ~3 % (medida en brief) | Baja de Embat ≠ cierre real; requiere cruzar con `groups` para diferenciar inactividad de filiales vs. cierre del grupo. |

**Ancla principal:** Riesgo de Liquidez. Es la señal que mejor responde a la prueba de los 100.000 € y a la criticidad marcada en `scoring.md`.

### 4. Críticas a la propuesta actual
- **Mezcla de naturaleza de riesgo:** Definir "incumplimiento" como una obligación omitida o proveedores >90d vencidos diluye la prioridad que marca el framework de scoring.md. La caja que se evapora debe mover el score más que un desvío de disciplina de pagos; al unirlos en una sola etiqueta se penaliza la sensibilidad a la liquidez.
- **Umbral de tensión excesivamente estricto:** 0,25 meses de caja o negativo tras 3 meses sanos captura solo la etapa terminal. El prestamista (o el producto de circulante) necesita activarse cuando la *velocidad* de quema cruza 1,0–1,5 meses de caja restantes, no cuando ya está en rojo.
- **Falta de criterio cuantitativo para bache vs. caída:** La propuesta menciona la distinción pero no proporciona una regla implementable y causal. Sin un umbral de persistencia (p. ej., 2-3 meses de mediana <70 % vs. recuperación en 1 mes), el sistema no podrá generar alertas estables ni cumplir el requisito de estabilidad del leaderboard.
- **No se explicita la reconfiguración por comprador:** `scoring.md` deja claro que la métrica y los pesos cambian según la oferta (banco, aseguradora, CFO). La propuesta asume un único motor; hay que documentar explícitamente cómo cada comprador recibe su propia vista ponderada del score sin romper la coherencia del backbone.

### 5. Cómo validarías los eventos sin etiquetas
- **Validación por coherencia temporal jerárquica:** En un ciclo financiero real, la tensión de caja debe preceder a la omisión de pagos, que a su vez precede a la caída de cobros. Validaré que la mediana de antelación entre eventos se mantenga en el orden esperado (liquidez → operativo → flujo). Si el orden se invierte, el evento está mal definido o hay fuga de información.
- **Walk-forward backtesting por horizonte:** Calibración sobre 2024–2025 (v1) y validación estricta sobre 2025–2026 (v2), separando por tramos de antigüedad (<6 m, 6–12 m, >12 m) para testar robustez OOD. Se medirá la estabilidad de las tasas por mes (variación <±2 p.p.) para descartar artefactos de generación.
- **Prueba de sensibilidad a estacionalidad y reconstrucción:** Se repetirán los cálculos de las features de caja y cobros usando solo transacciones categorizadas (`category != '-'`) y excluyendo meses de pago trimestral de impuestos para verificar que las tasas no se inflan artificialmente.
- **Densidad de explicación causal:** Para cada evento, se exigirá que la feature que lo dispara sea monótona en al menos el 70 % de los deciles del dataset. Si un evento se activa solo en colas extremas o sin orden por tramos, se reparametriza o se degrada a regla contextual.

### 6. Preguntas para la organización
- ¿Qué proporción real del "apagado" corresponde a baja de la plataforma Embat frente a cierre comercial o inactividad de la filial dentro de un grupo activo?
- ¿Existe historial de reactivación (empresas que retoman movimientos tras >30 días de inactividad) para calibrar el umbral de "bache" frente a "caída"?
- ¿Se permiten modelos de contagio intragrupo (p. ej., si un holding está en tensión, penalizar filiales) o el score debe ser estrictamente empresa-individual para cumplir la regla de causalidad por `company_id`?
- ¿Cuál es el buyer primario del leaderboard para la demo final: el banco (crédito/circulante) o la propia pyme (CFO/tesorería)? Esto define si priorizamos sensibilidad a liquidez (banco) o a explicabilidad y recomendaciones (CFO).
- ¿Hay acceso a datos de `debt_schedule_config` históricos o solo a la foto final? De lo contrario, la señal de "obligaciones recurrentes omitidas" requerirá inferencia por frecuencia y montos habituales.

### 7. Verificaciones hechas
No tengo acceso directo a ejecutar consultas ni a leer los archivos `research/data/*.parquet` en tiempo real. Todas las frecuencias, solapamientos y densidades mencionados en las secciones anteriores que extrapolan o combinan variables se han marcado como **estimaciones**, basadas estrictamente en la información provista en el brief y en la estructura de `targets.py`. He verificado contra los documentos adjuntos:
- Causalidad y ventanas temporales: confirmadas según `features.md` (ventanas ≤ mes m, exclusión de meses parciales, manejo de `-` y estacionalidad trimestral).
- Estructura de columnas y claves: alineadas con `data_dictionary.md` (`company_id`, `in6`/`in12` derivados de `inflow`, `cash_end` reconstruido, `overdue_90_ar/ap`, `debt_schedule_config` como foto final).
- Jerarquía de criticidad y framework de scoring: respetada en la selección de ancla (liquidez) y en la degradación de "caída de cobros" a feature, tal como prescribe la prueba de los 100.000 €.