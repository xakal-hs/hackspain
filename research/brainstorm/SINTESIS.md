# Síntesis del brainstorming de features

Cuatro modelos recibieron el mismo brief (`features.md`) y el perfil del dataset:

| Modelo | Vía | Acceso a datos | Propuestas | Fichero |
|---|---|---|---|---|
| GLM 5.3 | Helmcode (API) | No | 24 | `features_glm5.3.md` |
| DeepSeek V4 Flash | Helmcode (API) | No | 25 | `features_deepseek-v4-flash.md` |
| Qwen 3.6 | Helmcode (API) | No | 20 | `features_qwen3.6.md` |
| Cursor Auto | CLI `agent` (agéntico) | **Sí**: calculó cada feature y su AUC contra los eventos a 6 meses | 26 | `features_cursor-auto.md` |

GPT-5.6 Sol y Grok 4.6 no se pudieron usar. Sol exige saldo prepago en Helmcode, y Grok no está disponible en el plan gratuito de Cursor.

## Temas por consenso

La columna "Evidencia" solo existe donde Cursor Auto lo midió. El AUC está orientado de forma que 0,5 significa sin señal.

| # | Tema | Quién lo propone | Evidencia medida (Cursor Auto) | Lectura |
|---|---|---|---|---|
| 1 | **Nómina: irregularidad, continuidad y puntualidad** | 4/4 | `payroll_cv` 0,69 frente a apagado; `payroll_continuity_6m` 0,66 | ✅ Fuerte y sin ERP. "La nómina les baila" |
| 2 | **Concentración de proveedores o de a quién se paga** | 4/4 | `payee_concentration` (banco) **0,75** frente a apagado y 0,61 frente a declive; `hhi_ap_6m` (ERP) 0,68 | ✅ La mejor medida. Hay que controlar el tamaño (ver avisos) |
| 3 | **Dinámica de clientes: aceleración de pérdidas, clientes nuevos, pagadores en banco** | 4/4 | `lost_accel` **0,74** frente a apagado; `bank_cp_in_trend` 0,55 frente a declive | ✅ `lost_accel` fuerte; la versión bancaria cubre a las empresas sin ERP |
| 4 | **Obligaciones omitidas (impuesto trimestral, cuota, nómina)** | 3/4 (+ en cola) | `tax_miss` 0,67 frente a apagado (solo en meses fiscales, cobertura del 20 %) | ✅ Alta precisión en su ventana |
| 5 | **Plazos de cobro y pago: DSO/DPO realizados y su tendencia; facturación frente a cobro** | 4/4 | `dpo_3` 0,64 frente a apagado; `billing_to_cash` 0,66; `ap_early_3` 0,63 frente a tensión de caja; tendencias DSO/DPO ~0,53-0,55 | ✅ El nivel sí, la tendencia apenas. Pagar "demasiado pronto" también es señal de estrés |
| 6 | **Bache frente a caída: persistencia, rebote, asimetría, estrés multiseñal** | 4/4 | `oper_persistence_6m` 0,62 frente a declive y **0,67 separando estructural de temporal**; `multi_signal_stress` 0,59 (0,58 estructural/temporal); `vol_asymmetry` 0,61 frente a crecimiento | ⚠️ Primera señal real para la pregunta 4 (hoy AUC 0,50) |
| 7 | **Estacionalidad: cobros año contra año** | 4/4 | `yoy_inflow` 0,62 frente a declive (solo con más de 12 meses de historia) | ✅ Sustituye a las tendencias ruidosas cuando hay historia |
| 8 | **Velocidad de caja: Δ runway, burn, segunda derivada** | 4/4 (top 1 de GLM, DeepSeek y Qwen) | `runway_delta_3m` 0,55; `cash_delta_6m` con orden invertido | ❌ Intuitiva pero débil en los datos: revierte a la media. Mejor como explicación que como peso |
| 9 | **Financiación forzada: deuda nueva con caja cayendo, póliza acelerando, factoring nuevo, intereses** | 4/4 | `debt_while_draining` ~0,50 (pocos casos) | ❓ Sin evidencia todavía; hipótesis de producto fuerte ("tapa el agujero") |
| 10 | **Grupo empresarial: prior, divergencia, dependencia intragrupo** | 4/4 | `runway_vs_group` ~0,57 separando estructural de temporal | ⚠️ Útil sobre todo para empresas nuevas del test (shrinkage hacia el grupo) |
| 11 | Comisiones bancarias | 2/4 | `fee_intensity` 0,58 pero en forma de U | ⚠️ Mejor como alerta de pico |
| 12 | Texto de descripciones y conceptos (refinanciación, impago, aplazamiento) | 2/4 | No medido | ❓ Barato de probar con palabras clave |
| 13 | Colchón fuera de la cuenta corriente (ahorro e inversión) | 2/4 | No medido | ❓ |
| 14 | Conciliación como calidad del dato | 2/4 | No medido | Contexto o confianza, no salud |
| 15 | Pulso TPV, silencio de cobros, fragmentación bancaria, operaciones anómalas | 1/4 | No medido | ❓ |

## Avisos antes de incorporar nada

- **La evidencia es univariante.** Una feature puede predecir el apagado solo porque se correlaciona con el tamaño o la juventud de la empresa. Por ejemplo, las empresas pequeñas tienen pocos proveedores, alto HHI y más apagados. Hay que medir el **valor incremental**: AUC del score con y sin la feature, controlando por tamaño y meses de historia.
- **El apagado es un evento raro (3 %)**, así que un AUC alto frente al apagado puede apoyarse en pocos casos. Hay que exigir que se sostenga en varios cortes temporales y folds por grupo.
- **Las ideas preferidas por los modelos sin datos (velocidad de caja, deuda nueva) son justo las más débiles al medirlas.** Conviene no fiarse de un brainstorming sin validación.

## Propuesta de siguiente paso (v7)

1. Implementar en `features.py` los temas 1, 2, 3, 4, 5 (niveles), 6 y 7, en versión causal.
2. Medir el valor incremental de cada uno con la validación por grupos (GroupKFold × cortes) y quedarse con los que mejoren el AUC frente a eventos sin empeorar la estabilidad.
3. Pasar las notas a riesgo observado por tramos (tipo scorecard/WoE), porque muchas de estas señales solo actúan en la cola.
4. Usar `oper_persistence_6m` + `multi_signal_stress` como base de un clasificador de bache frente a caída.
