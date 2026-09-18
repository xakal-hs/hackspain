<!-- modelo: deepseek-v4-flash vía Helmcode · lente: auditor-datos · 58s · uso: None -->

# Auditoría escéptica de los eventos X-Ray

## 1. Posición

Los cuatro eventos actuales no miden lo mismo que dicen medir: **"apagado" es más probablemente una desconexión o una migración intragrupo que un cierre**, "saldo negativo" depende de una reconstrucción hacia atrás que puede fabricar el evento, "caída de cobros" está contaminada por la estacionalidad trimestral y por las categorías `-` (45% del importe de entradas) y "crecimiento" se confunde con una disposición de deuda o una entrada de grupo. La propuesta del equipo mejora la dirección (obligaciones recurrentes, tensión de caja, bache vs caída) pero deja sin resolver el problema central: **ningún evento se define contra un test de falsedad**, y en este dataset hay al menos seis mecanismos mecánicos que generan eventos falsos sin que haya deterioro real. Mi tesis: antes de calibrar pesos, hay que declarar cada evento "sospechoso hasta que pase las comprobaciones de la sección 7"; el ancla principal debería ser un **incumplimiento de obligación recurrente bien definido** (lo ya vencido no se reconstruye), con **tensión de caja persistente** validada como ancla secundaria, y con **apagado y caída de cobros fuera del conjunto de calibración**. El evento más fiable, si se implementa con calendario por empresa, es el incumplimiento; el menos fiable es "apagado" como señal de salud.

## 2. Veredicto sobre cada evento actual y propuesto

| Evento | Veredicto | Motivo (mecanismo de falso evento principal) |
|---|---|---|
| **Apagado** | **Separar como otro producto / degradar a covariable de cobertura** | Es un hecho observable (dejan de entrar movimientos) pero no es salud: 22% se va con >3 meses de caja y solo 36% mostró síntomas. Confundible con desconexión de banco, migración de actividad a otra empresa del grupo y truncamiento en el borde del dataset. |
| **Saldo negativo** | **Redefinir** como "tensión de caja persistente" tras validar la reconstrucción | La reconstrucción hacia atrás desde una única foto (1-sep-2026) puede generar negativos falsos: cuentas tarjeta/inversión con signo propio, balances finales extremos (±1e13), tipos de cambio erróneos (=1 en MZN, =0 en VND) y pólizas que enmascaran el hueco. La circularidad con `cash_end` de hoy ya está reconocida (AUC 0,77). |
| **Caída de cobros** | **Degradar a feature/síntoma** | 69% solapa con apagado (mecánico). La base de 12 meses y la ventana de 6 no eliminan la estacionalidad trimestral (IVA ene/abr/jul/oct) ni el efecto de las categorías: un cambio de criterio del banco mueve `inflow` sin cambio económico. |
| **Crecimiento** | **Mantener, redefinido** (operativo, sin deuda, sin transferencias, con umbral mínimo de volumen) | Hoy mezcla `oper_in` con `transfer_in`, `uncat_in` y con caja que sube por una disposición de línea o una inyección del grupo. También lo dispara una base anual deprimida por un solo trimestre malo. |
| **Incumplimiento** (propuesto) | **Mantener como ancla principal, con definición estricta y calendario por empresa** | Es el único evento anclado en una obligación **ya vencida** (no se reconstruye). Riesgos: calendario mal estimado, pagos recategorizados, gap de conexión confundido con omisión y nómina centralizada en el grupo. |
| **Tensión de caja** (propuesto) | **Mantener como transición**, condicionada a persistencia ≥3 meses y a ausencia de disposición de póliza | Hereda todos los artefactos de reconstrucción. El umbral 0,25 meses es arbitrario y no contempla estacionalidad ni grupo. |
| **Caída estructural vs bache** (propuesto) | **Mantener**, definiendo persistencia (≥3 meses) y umbral | Sin definición operativa es un eslogan. Hoy el AUC bache/caída es 0,50. |
| **Recuperación** (propuesto) | **Mantener** con requisito de mantenimiento ≥3 meses | Riesgo: empresa que baja de actividad parece "estable" y se confunde con recuperación. |
| **Sano sostenido** (propuesto) | **Mantener** con umbral mínimo de actividad y cobertura | Riesgo: sin ERP, sin nómina o con pocos movimientos aparece "sana" por falta de señal, no por salud. |

## 3. Eventos recomendados

Frecuencias **estimadas**: no tengo acceso a los parquet; las cifras del brief (3%, 5%, 17%, 16%) sí están medidas por el equipo.

| Evento | Definición implementable | Tipo | Preguntas | Frecuencia estim. | Riesgos | Ancla |
|---|---|---|---|---|---|---|
| **Incumplimiento de obligación recurrente** | Para empresas con ≥6 repeticiones históricas de cada obligación (`category in {salary, social_security, tax, debt_repayment}`), construir calendario modal (mes esperado, importe mediano ±50%). Evento si en el mes esperado no aparece el cargo y **no** hay doble pago en los 2 meses siguientes. Obligaciones: nómina mensual, IVA en ene/abr/jul/oct, cuota de préstamo (`debt_schedule_config.next_payment_date`). | Resultado | 3,4,5,6 | 3-8% (estimado) | Calendario mal estimado; recategorización; gap de conexión; nómina en el grupo; empresa sin empleados | **SÍ (principal)** |
| **Tensión de caja persistente** | Primer mes con `cash_end < 0,25 × gasto_12m` (o `<0`), tras ≥3 meses con `cash_end ≥ 1 mes`; se confirma si persiste ≥3 meses; se **anula** si `lc_drawn > 0` en el mismo mes (la línea tapa el hueco). Excluir meses 0 y último. | Transición | 3,4,5,6 | 5-10% | Reconstrucción, cuentas tarjeta, grupo, borde | **SÍ (secundaria)** |
| **Caída estructural** | Mediana de `inflow` (o `oper_in`) de 3 meses seguidos por debajo del 60% de la mediana de 12, sin recuperar a ≥80% en 3 meses. | Estado | 4 | 8-12% | Estacionalidad, categorías | No |
| **Bache (control negativo)** | Un mes por debajo del umbral que recupera a ≥80% de la mediana de 12 en ≤2 meses. | Estado | 4 | 10-15% | Umbral | No |
| **Recuperación** | Pasa de incumplimiento o tensión a `score > umbral_sano` y se mantiene ≥3 meses con actividad ≥ umbral mínimo. | Estado positivo | 2 | 8-12% | Baja actividad | No |
| **Sano sostenido** | ≥12 meses sin evento adverso **y** `n_tx ≥ 3/mes` **y** (si `has_erp`, `ar_issued > 0`). | Estado positivo | 1 | 25-35% | Cobertura baja | No |
| **Crecimiento operativo** | `oper_in` de 6m > 130% de la media de 12m **y** caja al alza **y** `transfer_in + uncat_in < 30%` de las entradas del periodo **y** volumen mínimo (percentil 20 de la empresa). | Resultado positivo | 1,2 | 10-13% | Deuda, grupo, base deprimida | No |
| **Apagado (separado)** | Deja de tener movimientos y `months_since_final_tx > 0`, con última fecha < 2026-08 para excluir borde. | Evento de plataforma / cobertura | 3,5 (contexto) | 3% | Desconexión, migración, borde | **No** (covariable) |
| **Caída de cobros (feature)** | Igual que hoy pero estacionalizada y calculada sobre `oper_in`; se usa como explicación, no como objetivo. | Síntoma | 4,5 | 10-17% | Estacionalidad, categorías | No |

## 4. Críticas a la propuesta actual

1. **"Incumplimiento" sin calendario por empresa es un falso positivo en potencia.** "Proveedores con >90 días vencidos que crecen" mide nivel y tendencia de un saldo que puede ser normal en el sector; el crecimiento puede venir de una factura grande única. Falta el umbral de repetición histórica.
2. **No aborda la reconstrucción.** Tanto "tensión de caja" como "saldo negativo" se apoyan en `cash_end` reconstruido hacia atrás desde una sola foto. Sin validación, el evento puede ser un artefacto de la cuenta tarjeta o del balance final.
3. **No aborda las pólizas.** La propuesta no dice qué hacer cuando `lc_drawn > 0`: una empresa puede estar en tensión real y no mostrar caja negativa porque la línea la sostiene. Eso genera **falsos negativos**.
4. **No aborda el grupo.** No hay ninguna regla para consolidar. Un cierre de filial con actividad migrada al holding se leerá como 3 eventos (apagado + caída + incumplimiento) sin que pase nada.
5. **No aborda el borde.** El mes de septiembre de 2026 es parcial; cualquier evento cuya ventana de 6 meses toque el final debe excluirse. `targets.py` ya lo hace con `fut(month, horizon).is_not_null()`, pero la propuesta no lo menciona.
6. **No aborda el 36% sin ERP ni el 45% de la categoría `-`.** El incumplimiento de nómina/IVA depende de categorías que pueden estar mal asignadas o directamente ausentes.
7. **"Caída de cobros pasa a feature" es correcto, pero no dice con qué versión.** Hay que conservar una versión estacionalizada y sobre `oper_in`, y decidir si la actual (sobre `inflow` bruto) se mantiene como síntoma o se retira.
8. **No fija umbral de actividad para "sano sostenido".** Una empresa inactiva con cobertura baja será clasificada como sana por defecto.
9. **No dice qué hacer con los apagados en la calibración.** Si se separan como producto, ¿se excluyen del conjunto de eventos adversos o se mantienen como covariable? Dejarlo ambiguo contamina los pesos.

## 5. Cómo validar los eventos sin etiquetas

- **Test de placebo temporal (fuga).** Calcular cada evento en meses pasados y comprobar que las features de meses futuros **no** lo predicen (AUC ≈ 0,50). Si predicen, hay fuga en la definición.
- **Test de estabilidad partida.** Partir el histórico en meses pares/impares o pre/post-2025-09 y medir el mismo odds ratio de cada feature. Si el signo cambia, el evento es frágil.
- **Test de reconstrucción (kappa).** Recalcular el evento con dos reconstrucciones de caja (con y sin cuentas tarjeta/inversión; con y sin balances implausibles >50×) y medir la concordancia. Kappa < 0,6 ⇒ el evento es un artefacto de la reconstrucción.
- **Test de grupo.** Calcular el evento a nivel empresa y a nivel grupo. Si el evento a nivel empresa es 2-3× más frecuente que a nivel grupo y todos los casos caen en grupos con otra empresa que crece, es migración, no deterioro.
- **Test de consistencia con facturas.** Para "caída de cobros", comparar con `ar_issued`: si las facturas emitidas no caen pero los cobros bancarios sí, es timing o categoría, no demanda.
- **Ajuste estacional.** Regresar el evento contra dummies de mes; si los residuos concentran el evento en agosto/enero, redefinir con ventana de 12 meses o contra el mismo mes del año anterior.
- **Sensibilidad a umbrales.** Mover el umbral (0,25 ↔ 0,5 meses; 50% ↔ 60% de caída) y ver si el ranking de empresas cambia. Si cambia mucho, no hay señal robusta.
- **Validación por grupos (GroupKFold)**: nunca dejar empresas del mismo `group_id` en train y validación.
- **Verificación de anticipación**: si una feature se mueve **después** del evento, no vale como detector; medir el desfase.

## 6. Preguntas para la organización

1. ¿El generador sintético modela explícitamente **cierre de empresa**, **desconexión de banco** y **migración de actividad al grupo**? ¿Son distinguibles en los datos?
2. ¿El mes de septiembre de 2026 está **completo o parcial**, y cómo afecta a la reconstrucción hacia atrás?
3. ¿La categoría `-` es intencional? ¿Cambia su proporción a lo largo del tiempo?
4. ¿Los grupos tienen **cash pooling**? ¿Un préstamo intragrupo aparece como `debt_products` con `bank_name = Other (customer-defined)`?
5. ¿Los préstamos de `debt_schedule_config` se **refinancian** dentro de los 24 meses? ¿Cómo se refleja?
6. ¿`balances` incluye **todas** las cuentas o solo las conectadas? ¿Hay cuentas sin saldo final?
7. ¿Las empresas sin ERP tienen realmente facturas o simplemente no se sincronizaron?
8. ¿Qué es `settlement_product_id` y se usa para reconstruir pagos?
9. ¿Hay empresas que cambian de **moneda** o de país dentro del periodo?
10. ¿El test oculto comparte distribución con el train o incluye regímenes nuevos (sin ERP, moneda distinta, historia corta)?

## 7. Verificaciones hechas con los datos

**No tengo acceso a los ficheros** (`research/data/*.parquet`, `research/data/panel.parquet`) ni a herramientas en esta conversación. Todo lo que sigue son **comprobaciones diseñadas**, no ejecutadas; las cifras que cito entre paréntesis son las del brief (medidas por el equipo) o estimaciones mías.

**Comprobaciones de "apagado":**

| Qué calcular | Columnas | Resultado que confirmaría | Resultado que refutaría |
|---|---|---|---|
| Distribución del mes de última transacción para empresas apagadas | `transactions.date`, `panel.months_since_last_tx` | Concentración en jul-sep 2026 ⇒ artefacto de borde | Cola extendida ⇒ cierre real |
| Continuidad intragrupo en la ventana ±6 meses | `panel.inflow`, `group_id` | Grupo estable o al alza ⇒ migración | Grupo cae con la filial ⇒ cierre real |
| Cierre frente a refinanciación: `next_payment_date` posterior al apagado | `debt_schedule_config` | Pago programado después ⇒ empresa viva | Sin pagos pendientes ⇒ probable cierre |
| Tasa de apagado por nº de productos bancarios y por `has_erp` | `banking_products`, `companies.erp` | Más apagados con 1 producto / sin ERP ⇒ desconexión | Sin diferencia ⇒ cierre real |

**Comprobaciones de "saldo negativo":**

| Qué calcular | Columnas | Confirmaría | Refutaría |
|---|---|---|---|
| Reconstrucción con solo `checking` vs todas las cuentas | `banking_products.type`, `transactions.product_id`, `balances` | La tasa de negativos cae mucho ⇒ artefacto de tarjeta/inversión | Se mantiene ⇒ tensión real |
| Sensibilidad a balances implausibles >50× | `balances.balance`, volumen mensual | Al excluirlos, cae la tasa ⇒ artefacto | Se mantiene |
| Solo `status = booked` | `transactions.status` | Cambia la tasa ⇒ incluir `pending` distorsiona | No cambia |
| Persistencia y posición temporal de los negativos | `panel.cash_end`, `month_idx` | Negativos concentrados en meses 0/último o en tramos largos ⇒ artefacto | Negativos aislados y en medio de la serie ⇒ tensión real |
| Efecto de la póliza | `panel.lc_drawn`, `lc_limit` | Muchos negativos con línea no dispuesta ⇒ la línea no lo tapa; muchos sin negativo con línea dispuesta ⇒ falso negativo | — |
| Grupo vs empresa | `cash_end` agregado por `group_id` | Grupo nunca negativo ⇒ tensión intragrupo, no real | Grupo también negativo ⇒ real |

**Comprobaciones de "caída de cobros":**

| Qué calcular | Columnas | Confirmaría | Refutaría |
|---|---|---|---|
| Estacionalidad del mes de inicio del evento | `panel.month` | Concentración en ago/ene ⇒ estacionalidad | Distribución uniforme |
| Versión `inflow` vs `oper_in` vs `oper_in + uncat_in` | `panel.inflow, oper_in, uncat_in` | Tasa muy distinta ⇒ categoría mal asignada | Tasa estable ⇒ caída real |
| Contraste con facturación emitida | `panel.ar_issued` | `ar_issued` estable pero cobros caen ⇒ timing/categoría | Facturación también cae ⇒ caída real |
| Nivel empresa vs grupo | `inflow`, `group_id` | Grupo estable ⇒ migración | Grupo cae |
| Tasa por `has_erp` | `companies.erp` | Gran diferencia ⇒ dependencia de sincronización | Sin diferencia |

**Comprobaciones de "crecimiento":** descomponer la variación en `oper_in`, `transfer_in` y `uncat_in`; si el crecimiento viene de los dos últimos, es financiación o categoría, no actividad. Repetir con umbral mínimo de volumen (percentil 20) y comprobar sensibilidad de la base (12 vs 24 meses).

**Comprobaciones de "incumplimiento" (propuesto):** construir el calendario modal por empresa y medir (a) la varianza del importe de las obligaciones históricas, (b) si el mes omitido coincide con un doble pago posterior (timing) o con un mes sin movimientos (gap de conexión), (c) la proporción de pagos de IVA realmente categorizados como `tax` frente a `payment`, y (d) si la nómina aparece centralizada en otra empresa del grupo.

**Más y menos fiable.** El evento **más fiable, si se implementa con calendario por empresa y tolerancia, es el incumplimiento de obligación recurrente**: se apoya en algo ya vencido, no en una reconstrucción ni en una predicción, y su mecanismo económico es el que un prestamista reconoce ("dejó de pagar la nómina"). El **menos fiable es "apagado" como señal de salud**: el propio equipo mide que el 22% se apaga con >3 meses de caja y que solo el 36% tuvo síntomas, además del 69% de solapamiento con caída de cobros; la evidencia apunta a desconexión o migración intragrupo, no a deterioro. **"Caída de cobros" es el segundo menos fiable** como ancla, por estacionalidad y por categorías; como feature explicativa sí tiene valor.