# Fase 1 · La mirada del prestamista (Embat / fondo de deuda)

Eres el **orquestador** del workflow de autoresearch del score X-Ray (reto de Embat, HackSpain 2026). Esta fase **no modifica código ni el modelo**. Solo construye la política de préstamo desde la que se juzgará todo lo demás.

## Por qué existe esta fase

El sistema actual (v7) se diseñó de abajo arriba: features → pesos → score. Aquí le damos la vuelta. Primero nos ponemos en el sitio de quien pone el dinero y decidimos **a qué empresas prestaríamos y cómo las rankearíamos**. Todo lo que venga después (el consejo de la fase 2 y el bucle de la fase 3) se juzga contra esta política. Si una feature no sirve para tomar una decisión de crédito, no tiene por qué estar en el score.

Lee primero:
- `context/scoring.md` (la prueba de los 100.000 €) y `context/challenge.md`.
- `research/ESTADO.md`, `research/DECISIONS.md`, `research/REFLEXIONES.md`.
- `features.md` y `data/data_dictionary.md`.
- `research/README.md` (qué hace el sistema hoy).

## Paso 1 · Investigaciones de apoyo en paralelo

Lanza 4 subagentes `researcher` con `is_background: true`. Todos devuelven columnas y `file:line`, no opiniones. Pueden ejecutar consultas de solo lectura con `uv run python` desde `research/` sobre `data/panel.parquet`.

- **A · Liquidez y caja.** ¿Qué mide hoy `runway`, `lc_util`, `cash_end`? ¿Cómo se reconstruye la caja y dónde está el intragrupo (R08)? ¿Qué significa «romper la caja» en estos datos y con cuántos meses de antelación se ve?
- **B · Cobros y pagos.** DSO/DPO, morosidad (`overdue_*`, `late_share_*`), clientes perdidos (`lost_share`, `cust_trend`), concentración (`hhi_ar_6m`). ¿Qué señales hay de que la empresa deja de cobrar o empieza a pagar con deuda?
- **C · Deuda y productos.** `debt_products` (loan, leasing, lineofcredit, mortgage, renting, **factoring**, confirming, guarantee), `debt_schedule_config`, pólizas (`lc_drawn`/`lc_limit`). ¿Qué producto encaja con qué situación? ¿Qué se puede reconstruir hacia atrás y qué es solo foto final?
- **D · Observabilidad y comportamiento.** ERP, huecos, categoría `-`, inactividad (`months_since_last_tx`), apagado (R06). ¿Qué es cobertura y qué es salud? ¿Cómo se ve que alguien «no se deja ver las cuentas»?

## Paso 2 · Escribe la política de préstamo

Escribe `.devin/workflows/autoresearch/salida/politica_prestamo.md`. Debe contener:

1. **El comprador.** Quién paga por el producto y por qué (Embat, banco, fondo de deuda, CFO). Qué decide cada uno con el score y con qué objetivo distinto.
2. **Preguntas de underwriting.** Tabla consumidor → empresa → **columna/feature del dataset** que la responde. Amplía la de `context/scoring.md`; no la repitas sin añadir.
3. **Criterios de decisión.** Por cada situación (caja rota N meses, impago de nómina, caída de cobros, póliza agotada, intragrupo que tapa el hueco, sin movimientos…): ¿prestar / vigilar / no prestar? **Bajo qué condiciones** (importe, plazo, factoring con o sin recurso, covenant de caja mínima, anticipo, garantía).
4. **Metodología de ranking.** Si tuvieras que ordenar 1.286 empresas para colocar deuda, ¿qué miras primero, qué descarta de entrada, qué desempata? Define el orden de las decisiones, no solo el número.
5. **Productos y su señal.** Por cada producto (factoring de pagarés, confirming, línea de circulante, refinanciación), la situación que lo dispara y las señales del dataset que lo confirman.
6. **Premisas candidatas.** La lista inicial de afirmaciones que el consejo deberá debatir (≥ 25), cada una en una frase, del estilo «una empresa con la caja rota 3 meses seguidos no recibe deuda nueva, salvo X».

## Paso 3 · Revisión adversarial

Lanza un subagente `reviewer` sobre `politica_prestamo.md`. Debe buscar: condiciones no medibles en el dataset, contradicciones con lo que ya sabemos (`DECISIONS.md`), casos donde prestar sería temerario y la política lo permite, y sesgos (tamaño, intragrupo, apagado). Incorpora lo aceptado y añade una sección **«Revisión»** con lo que rechazaste y por qué.

## Reglas

- **Solo escribes** dentro de `.devin/workflows/autoresearch/salida/`. No edites código, no toques `data/`, no hagas commits.
- No leas ni muestres secretos.
- Escribe en español. Cada afirmación sobre el código o los datos lleva su referencia (`file:line` o columna).
- Termina con un resumen de 10 líneas: el comprador, los 3 criterios de decisión más importantes y cuántas premisas candidatas dejas al consejo.
