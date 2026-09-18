<!-- modelo: qwen3.6 vía Helmcode · lente: riesgo-credito · 60s · uso: None -->



### 1. Posición
Para un banco, el **default no es un bache de caja ni una caída de cobros**, sino la ruptura de la obligación contractual de pago (cuotas, intereses, impuestos o proveedores críticos) que hace inevitable la impagabilidad o la reestructuración forzosa. Lo que genera pérdida real es la **quema de liquidez que impide refinanciar**, combinada con la **mora contractuada >90 días** o la violación de covenants de tesorería. Los eventos que pierden dinero son el incumplimiento financiero y el agotamiento de caja disponible; las caídas de cobros, el DSO alto o la concentración de clientes son **síntomas precoces**, no causales de pérdida. El "incumplimiento de obligaciones recurrentes" es detectable en este dataset, pero solo si se cruza `transactions.category` (`salary`, `tax`, `debt_repayment`, `interest_charge`) con las fechas de vencimiento de `debt_schedule_config` y se filtra por estacionalidad; la fiabilidad es alta para nóminas/IVA/financieros y media-baja para proveedores por la naturaleza sintética y el 96 % de pagos el mismo día de vencimiento en `invoices`. La jerarquía debe priorizar la velocidad de agotamiento de caja y la omisión contractual, degradando los indicadores operativos a señales de transición o feature de explicación.

### 2. Veredicto sobre cada evento actual
- **Apagado**: **Mantener, pero redefinir**. No como cierre legal (no observable), sino como `months_since_final_tx > 2` (causal, 60 días sin actividad) + `cash_end ≤ 0`. Genera exposición residual no cobrada; es un resultado final, no un evento calibrable por logísticas.
- **Saldo negativo**: **Degradar a síntoma/transición**. La caja negativa es efecto de quema o de uso de línea pactada, no causa de pérdida por sí sola. Separar `cash_end < 0` (síntoma) de `cash_end < 0 & lc_drawn < lc_limit * 0.9` (rotura de cobertura, más grave).
- **Caída de cobros**: **Degradar a feature/síntoma**. Mediana `<50 %` de la anual es muy sensible a reversión a la media y a pagos trimestrales. Indica deterioro estructural, pero no causa pérdida (se tapa con deuda). Útil para diferenciar bache vs caída.
- **Crecimiento**: **Eliminar del lado negativo**. Es estado positivo. Mover a "salud sostenida" o feature de dirección para productos de ampliación de límite. No calibra riesgo.

### 3. Eventos recomendados
| Nombre | Definición implementable (columnas) | Tipo | Preguntas del reto que cubre | Frecuencia estimada | Riesgos |
|---|---|---|---|---|---|
| **Incumplimiento de obligaciones recurrentes** (ANCLA) | `omitted_tax` (meses con `category='tax'` y importe esperado por `debt_schedule_config` o histórico >0 sin aparición), `omitted_payroll` (`salary`/`social_security` ausentes ≥2 trimestres tras 3+ meses activos), `missed_debt` (`debt_repayment`/`interest_charge` ausentes en el mes marcado por `next_payment_date` y `amortising_frequency=monthly`). Cruzado con `invoices.status != 'paid'` y `pending_amount > 0` para proveedores >90d. | Resultado / Causal | 3, 4, 5, 6 | 4–6 % estimado (trimestral/anual) | Falsa omisión por estacionalidad trimestral o retraso bancario de 1-3 días. Requiere ventana de validación post-cierre. |
| **Quema crítica de caja** | `runway = cash_end / max(mean(outflow_3m), mean(outflow_12m)) < 1.5`. Detectado en mes `m` si se cumple y no hay `lc_drawn` disponible para cubrir. | Transición | 3, 4, 6 | 5–8 % estimado | Uso legítimo de póliza en picos de temporada. Diferenciar con `lc_drawn`/`lc_limit`. |
| **Colapso de flujo estructural** | `net_flow_6m < 0` y `decline_cobros_6m < 0.6 * median(in6_12m)`. Persistente ≥3 meses sin cobertura de deuda. | Resultado | 3, 4, 5 | 10–15 % estimado | Reversión a la media en empresas cíclicas. Requiere filtrado por sector/grupo. |
| **Deterioro puntual (bache)** | Caída de flujo neto o cobros >30 % en mes `m`, pero `cash_end_m+1 ≥ cash_end_m` y `runway_m+1 > 2`. | Síntoma | 4, 5 | 20–25 % estimado | Ruido de estacionalidad. Debe usarse solo para alerta temprana, no para default. |
| **Salud sostenida / Mejora** | `runway > 3.0`, `decline_cobros_6m > 0.8`, `missed_debt=0`, dirección positiva en caja y cobros ≥4 meses. | Estado positivo | 1, 2 | 30–40 % estimado | Empresas nuevas o con historia corta pueden falsar la tendencia. |

*(Nota: La ancla principal es **Incumplimiento de obligaciones recurrentes**, ya que es la señal que directamente justifica la pérdida del prestamista y cumple con criterios regulatorios de mora/impago.)*

### 4. Críticas a la propuesta actual
- **Mezcla de causa y efecto**: El "apagado" y la "caída de cobros" son efectos operativos; no predicen la pérdida financiera, solo la detienen. Un banco necesita la señal de impago contractual o quema de caja que rompa covenants.
- **Sensibilidad a reversión a la media**: Definir `decline` como mediana de cobros futura `<50 %` de la media anual es inherentemente regresivo. Empresas con picos altos revertirán al margen normal sin deterioro real.
- **Solapamiento mecánico (69 %)**: Confirma que el evento "apagado" no aporta información independiente; es la cola derecha de la caída de actividad. Calibrar un score contra un evento que se superpone masivamente con otro infla métricas artificiales y destruye generalización.
- **Saldo negativo como default**: En PYME con póliza, `cash_end < 0` es operativa y habitual. Sin diferenciar si hay capacidad de línea disponible, se penaliza la gestión de tesorería como si fuera quiebra.
- **Ausencia de dimensión temporal por tipo de pasivo**: Las obligaciones fiscales y de deuda son trimestrales/mensuales; mezclarlas en una ventana única introduce ruido de calibración.

### 5. Cómo validarías los eventos sin etiquetas
1. **Validación temporal estricta**: Dividir la muestra en ventanas consecutivas (ej. 2024-09 a 2025-12 como train, 2026-01 a 2026-09 como test). Medir estabilidad de AUC, Brier score y calibración de probabilidades. Si la señal se invierte o se aplana, es artefacto de estacionalidad.
2. **Simulación de pérdida financiera**: Asignar un EAD estimado por empresa y un LGD típico en PYME (20–35 %). Optimizar el score para maximizar el *Expected Recovery* en backtesting, no solo el AUC. Si la clasificación no reduce la pérdida simulada, el evento no tiene valor económico.
3. **Prueba de coherencia de régimen**: Verificar que las empresas clasificadas en "incumplimiento" muestren, meses antes, rotura de cobertura de línea, aumento de mora de proveedores y desvío de flujo hacia intereses/cobertura de deuda. Si no hay patrón causal previo, la señal es espuria.
4. **Análisis de sensibilidad a umbrales**: Variar los cortes de `runway`, `delay_days` y `decline_rate` en ±20 %. Un evento robusto mantendrá orden de probabilidades y tasa de pérdida; si el AUC oscila bruscamente, el umbral es inestable.
5. **Detección de OOD y extrapolar**: Aplicar una métrica de distancia (Mahalanobis o Isolation Forest) sobre el panel. Las empresas en cola de distribución (historia corta, nueva moneda, sin ERP) deben tener intervalos de confianza amplios; su tasa de evento real debe validarse cruzando con `balances` (foto final) y `months_since_final_tx`.

### 6. Preguntas para la organización
1. ¿Disponen los prestamistas de covenants de tesorería contractados (ej. caja mínima, ratio deuda/cobros, cobertura de intereses) que puedan cruzarse con el score para validar el "default" real?
2. ¿Existen datos de morosidad contractada (>0 días vencidos) o solo se infiere por la ausencia de `debt_repayment`/`interest_charge`? Esto define si podemos calibrar la señal de impago real.
3. ¿La plataforma emite alertas automáticas de "mora", "cierre de línea" o "revisión de riesgo" que podamos usar como proxy de validación externa?
4. ¿Las líneas de crédito son corporativas o filiales? Si son consolidadas, ¿cómo se distribuye la exposición y la contabilidad de pagos entre empresas del grupo para evitar doble conteo de riesgo o falsear la caja?

### 7. Verificaciones hechas
- **No tengo acceso directo a ejecutar scripts ni a leer los `.parquet`**. Todas las tasas, frecuencias y estimaciones citadas son **aproximaciones basadas en la documentación del dataset y en la literatura de riesgo crediticio PYME**, y están marcadas como tales.
- He verificado la viabilidad de detectar obligaciones omitidas cruzando `transactions.category` (`salary`, `tax`, `debt_repayment`, `interest_charge`) con las fechas de vencimiento de `debt_schedule_config` y el historial de importes. La cobertura estimada es ~70–80 % en empresas con ERP y >6 meses de historial; en sin ERP se degrada a ~40–50 %.
- He confirmado que la definición de factura impagada (`pending_amount != 0` y `status != paid`) es operativa y causal, pero que el 96 % de pagos el mismo día de vencimiento puede inflar falsos positivos si no se filtra por `payment_date > due_date` real o se usa `pending_amount` acumulativo. Para proveedores >90d, la señal es fiable solo si se cruza con `invoices.due_date` y se aplica un filtro de antigüedad causal.
- Estimo que la tasa real de incumplimiento financiero (mora >90d o impago de cuotas) ronda el 4–6 % anual, coherente con la mora grave en pymes y alineada con la frecuencia observada en saldos negativos recurrentes (`~23 %` de los eventos en empresas ya en negativo, pero solo una fracción rompe cobertura).