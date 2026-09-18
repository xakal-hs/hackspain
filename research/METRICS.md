# Métricas del reto X-Ray

## Planteamiento (skill data-science, paso 1)

- **Objetivo de negocio**: que Embat (y sus socios financieros) sepa cada mes qué empresas están sanas, cuáles mejoran, cuáles se tuercen, si es un bache o una caída, por qué, y con cuánta antelación. Marco: [`../context/scoring.md`](../context/scoring.md) — la caja que se evapora en poco tiempo tiene que pesar más que un DSO/DPO que se mueve un poco; el output no puede ser solo el número; la métrica cambia con la oferta y con quien la mira; el valor frente a bancos es el dato de tesorería que ellos no tienen.
- **Tarea de ML**: no hay etiquetas, así que el problema se divide en dos piezas:
  1. **Nivel**: `HealthScorer`, un score de 0 a 100 interpretable y aditivo. Sus pesos se calibran contra eventos futuros observables (apagado, tensión de caja, declive y crecimiento), que funcionan como ancla externa.
  2. **Trayectoria**: `TrajectoryForecaster`, que prevé el score publicado a 1-3 meses con cuantiles q10/q50/q90.
- **Restricciones**: explicación exacta (el score es la suma de contribuciones), generalización a 60-80 empresas nunca vistas y robustez OOD (escala, moneda, historia corta, sin ERP).

Umbral de "movimiento real": **15 puntos** en la escala publicada, coherente con los ejemplos del enunciado (45→65, 82→68).

## Bloque "si acierta"

| Métrica | Qué mide | Pregunta del reto |
| --- | --- | --- |
| `auc_deterioro` / `auc_mejora` frente a `*_ar1` | Ranking de caídas o subidas de ≥15 puntos a 3 meses según el Δ previsto | Quién se tuerce / quién mejora |
| `auc_deterioro_top_quintil` | Lo mismo, solo en el 20 % con mejor score actual | "82→68 que aún parece sana" |
| `auc_mejora_bottom_quintil` | Lo mismo, solo en el 20 % con peor score actual | "45→65" |
| `prec_top5_down/up` | Precisión en el 5 % de series con mayor caída o subida prevista | Dónde actuar |
| `mae_h{1,2,3}` frente a `mae_ar1_h*` y `mae_naive_ewma_h1` | Error de la trayectoria frente al AR(1) agrupado (regresión a la media) y frente al arrastre mecánico del EWMA | Trayectoria, no foto |
| `coverage80_h*`, `width80_h*`, `pinball_h3` | Calibración de los intervalos cuantílicos | Confianza |
| `auc_level_vs_{adverse,churn,cash_stress,decline,positive}_6m` | Validez externa del nivel frente a eventos a 6 meses | Quién está sano |
| `p_sigue_sano_3m` | Persistencia de la banda sana | Quién está sano |

## Bloque "si llega a tiempo" (`anticipation.py`, origen móvil mensual out-of-fold)

| Métrica | Definición |
| --- | --- |
| `lead_time_mediana_meses`, `share_alertadas_antes` | En caídas estructurales (el score termina ≥20 por debajo de su nivel inicial y cruza a <35), meses entre la primera alerta de deterioro o caída y el cruce |
| `alert_deterioro/mejora_precision/recall` | Reglas reales del monitor frente a movimientos de ≥15 a 3 meses (con la tasa base como referencia) |
| `bache_vs_caida_accuracy/auc` | Tras una caída ≥10 del score publicado, ¿sigue abajo 2 meses después? |
| `alert_flicker_rate` | Alertas de deterioro que se encienden y se apagan al mes siguiente |

## Robustez OOD

| Métrica | Definición |
| --- | --- |
| `mae_h3_by_segment` | Error y cobertura por segmento: historia <6 meses, respaldo AR(1), OOD > 0 y cobertura < 0,6 |
| Tests (`tests/test_api.py`) | Invariancia de escala (×1e-6..×1e6, ±1 punto), todo NaN, valores ±inf, historia de 2 meses, monotonía y explicación exacta |

## Protocolo de validación

- 5 folds de GroupKFold por `group_id` × 3 cortes (nov-25, feb-26 y may-26). Ninguna empresa ni grupo aparece a la vez en train y validación.
- Scorer: cuantiles y pesos ajustados solo con empresas de train y meses ≤ corte. Las etiquetas de calibración solo cuentan si el evento a 6 meses ya era observable en el corte.
- Forecaster: ajustado con series de train hasta el corte. Las series de validación se predicen con `new_df`, como si fueran empresas nuevas.
