<!-- modelo: qwen3.6 vía Helmcode · lente: jurado-dataset · 35s · uso: None -->



# 1. Posición
El leaderboard de un reto sintético como este rara vez premia un evento aislado; suele evaluar un **espacio de estados latentes** (sano, mejora, deterioro, bache) y, sobre todo, la **capacidad del modelo para anticipar transiciones entre ellos**. Los generadores de datos financieros para hackathons suelen usar procesos de régimen (HMM o cadenas de Markov con saltos de media/varianza) donde la etiqueta oculta no es un punto, sino una trayectoria probabilidad-conditioned. Por tanto, el score debe verse como un **clasificador dinámico de regímenes con intensidad de transición**, calibrado contra horizontes múltiples y validado por estabilidad en ventanas walk-forward, no contra un umbral binario fijo.

# 2. Veredicto sobre cada evento actual
| Evento actual | Veredicto | Motivo |
|---|---|---|
| Apagado (churn) | **Separar como contexto/censura** | El 69 % de solapamiento con caída de cobros y la mezcla de baja real vs desconexión de Embat lo convierten en ruidoso para calibrar el score principal. Funciona mejor como variable de censura o regla de seguridad. |
| Saldo negativo (cash stress) | **Redefinir como transición crítica** | El binario actual es circular con `cash_end` y sensible a la reconstrucción. Cambiarlo a ruptura de runway (`< 0,25 meses` tras ≥3 meses estables) captura la velocidad de quema, que es la señal más predictiva del generador. |
| Caída de cobros (decline) | **Degradar a feature/síntoma** | Ya no sirve como objetivo principal: solapa con apagado y no distingue bache de caída. Convertirla en tendencia de cobros operativos o volatilidad a la baja dentro del score aporta información sin duplicar señal. |
| Crecimiento (growth) | **Mantener pero redefinir como estado positivo** | Para el leaderboard y el producto, la expansión verificada es un arquetipo válido. Mantenerlo como `expansión sostenida` (cobros y caja al alza con cobertura de deuda) permite medir la cara positiva y alinear con la pregunta 2. |

# 3. Eventos recomendados
| nombre | definición implementable (columnas) | tipo | preguntas del reto que cubre | frecuencia estimada | riesgos |
|---|---|---|---|---|---|
| **Ruptura de Liquidez** (Ancla Principal) | `cash_end` pasa a `< 0,25` meses de gasto mensual (media de 3m de `outflow` + `fees`) en un mes `t`, tras tener `cash_end >= 0,5` y `months_since_last_tx == 0` en `t-3:t-1`. | Transición | 3, 4, 6 | ~8–10 % (estimación) | Sensible a reconstrucción de saldos; usar estadísticos robustos (truncar >3 σ). Validar causalidad estricta. |
| **Deterioro Estructural** | Mediana de `inflow` (6m `t+1:t+6`) < 60 % de mediana de `inflow` (12m `t-11:t`), Y `cash_end` en `t+1` no se recupera al nivel de `t-1`. | Resultado/Regímen | 3, 4, 5 | ~12–15 % (estimación) | Estacionalidad trimestral (impuestos); usar percentiles relativos al peer group del grupo o sector. |
| **Omisión de Obligaciones Recurrentes** | En el trimestre `q`, ausencia de categoría `tax`, `salary` o `debt_repayment` en `transactions`, Y acumulados de `invoices` con `status='pending'` y `due_date > t+90d` en AP. | Síntoma | 3, 5, 6 | ~20–25 % (estimación) | Fuga temporal si no se cierra a fin de mes; requiere mapeo de calendarios fiscales reales por país. |
| **Mejora Sostenida** | Media de `inflow` 3m `t:t+2` > 110 % media 12m `t-12:t-1`, `cash_end` en `t+2` > `t`, Y `debt_service` (de `transactions` + `debt_schedule_config`) ≤ 40 % de `inflow` 3m. | Estado positivo | 1, 2 | ~15–18 % (estimación) | Pocos casos extremos en data sintética; útil para producto de circulante, menos para leaderboard general. |
| **Bache Verificado** | Caída mensual de `inflow` o `cash_end` > 20 %, pero recuperación total a nivel pre-caída en ≤ 2 meses siguientes, Y sin omisión de obligaciones. | Resultado/Ruido | 4, 6 | ~25–30 % (estimación) | Alto solapamiento con estacionalidad; debe servir para filtrar falsas alarmas, no como señal de peso. |

*Ancla principal:* **Ruptura de Liquidez**. Es la variable que mejor captura la criticidad del generador: la velocidad de evaporación de caja, no el nivel absoluto.

# 4. Críticas a la propuesta actual
1. **Mezcla niveles de abstracción:** El evento principal propuesto (incumplimiento) es un síntoma contable tardío y muy dependiente del ERP (36 % sin ERP). El generador probablemente no lo usa como etiqueta oculta, sino como feature de régimen. Calibrar pesos contra él introduce multicolinealidad con `cash_end` y `inflow`.
2. **Umbral de transición sin distribución:** Fijar `0,25 meses de caja` como punto de corte sin validar la cola de la distribución muestral genera falsos positivos en empresas estacionales o monedas débiles. Los generadores usan transiciones de régimen suaves; los umbrales fijos deben derivarse de percentiles de `cash_end` o de la desviación estándar del gasto.
3. **Falta variable de persistencia para bache vs caída:** La propuesta distingue ambos conceptos, pero no define la variable intermedia (duración, amplitud o tasa de recuperación). Sin un indicador de persistencia explícito, la variable se solapará con el ruido del mes y no separará regímenes en el leaderboard.
4. **Apagado como evento competitivo:** Tratar el churn como parte del mismo score compite con la detección de deterioro estructural. Es mejor tratarlo como censoring derecho o regla de seguridad (score ≤ X sin movimientos → alerta de observabilidad), liberando al modelo de aprender una señal que ya está cubierta por `months_since_last_tx`.
5. **Producto vs score:** La propuesta no cierra cómo se traducen los eventos al producto comprado por la empresa. Un score sin un mecanismo de acción (recorte de línea, alerta de tesorería, refinanciación) no cumple el requisito de comprador identificado.

# 5. Cómo validarías los eventos sin etiquetas
1. **Walk-forward temporal:** Entrenar/calibrar pesos en ventanas deslizantes (ej. entrenar en m1–m6, validar en m7–m12, correr en m13–m18). Medir estabilidad de AUC y Brier score entre ventanas. Un buen evento no colapsa en la última ventana.
2. **Monotonicidad por deciles del score:** Verificar que la tasa de evento baje (o suba, según corresponda) de forma monótona al ordenar empresas por percentil del score. Si hay cruces o colas planas, el evento no separa regímenes.
3. **Matriz de transición de regímenes:** Clusterizar el panel con un HMM o K-Means en features de trayectorias (tendencia 3m, volatilidad 6m, runway). Verificar si los eventos propuestos coinciden con transiciones entre clústeres. Si la tasa de transición Sano → Deterioro es significativamente mayor en la cola baja del score, el evento está alineado con la estructura latente del generador.
4. **Lag de anticipación:** Medir cuántos meses antes (`t-1` a `t-6`) se mueve la feature antes de que el evento ocurra. Un evento válido para el leaderboard debe mantener significancia estadística hasta `t-3` o `t-4`, no solo en `t-0`.
5. **Sensibilidad de umbrales:** Variar los puntos de corte en rangos razonables (ej. 0,15–0,35 meses de caja) y buscar regiones planas de AUC. Solo los umbrales en mesetas estables son robustos al ruido del generador.

# 6. Preguntas para la organización
1. ¿El leaderboard evalúa un score compuesto único o múltiples métricas desagregadas (precisión en deterioro, retención en sano, F1 en mejora)?
2. ¿El proceso generador usa un régimen oculto (HMM/Markov) con parámetros fijos por grupo, o reglas deterministas basadas en arquetipos predefinidos?
3. ¿Existe una penalización asimétrica en el leaderboard: es más grave una falsa alarma de deterioro que perder una mejora?
4. ¿El test oculto incluye empresas con historia parcial (<12 meses) o sin ERP, y se mide su capacidad de generalización a perfiles nunca vistos?
5. ¿El script de leaderboard devuelve desglose por tipo de evento o solo un ranking final con métrica global?

# 7. Verificaciones hechas
No tengo acceso directo al dataset ni a las herramientas de cómputo. Todas las frecuencias, umbrales y referencias a columnas se han deducido de la estructura proporcionada y de patrones estándar en la generación de datos financieros sintéticos. Las cifras se marcan como estimaciones aproximadas (`~X %`) y deben validarse con `research/src/targets.py` → `add_events` y walk-forward en `research/data/panel.parquet`. Lo que se verificaría en el entorno de ejecución son: la cola de `cash_end` para calibrar el umbral de ruptura, la matriz de transición de `inflow` vs `tax`/`salary`/`debt_repayment`, y la estabilidad del AUC al truncar outliers de saldos reconstruidos (±10⁹ €) y al excluir meses trimestrales de pago de impuestos como ruido.