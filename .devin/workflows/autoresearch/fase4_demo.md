# Fase 4 · La sala de situaciones (presentación final)

Eres el **orquestador** del workflow de autoresearch. Esta es la fase final. Su producto es una **sala de situaciones** en la UI donde el equipo analiza las +100 situaciones del consejo, y un caso destacado de **demo proactiva** sobre **empresas reales que el modelo no ha visto**.

Trabajas **en la rama activa** (no crees una nueva): esta fase forma parte del entregable que ya está en curso. Si el árbol tiene cambios sin commitear de la fase 3, es lo esperado.

## Paso 0 · Los datos de las situaciones

Asegúrate de tenerlas exportadas:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py export
```

`salida/situaciones.json` trae, por situación: `id`, `rol`, `ambito`, `premisa`, `por_que`, `condicion`, `test`, `verificable`, `estado`, `resultado.valor`, `resultado.n`, `resultado.ejemplos` (hasta 6 filas `{company_id, month, ...}`) y `central`/`diagnostico`/`iteracion` si corrió la fase 3.

## Paso 1 · Servir las situaciones

Añade a `research/app/server.py` los endpoints `/api/situaciones` y `/api/situaciones/{id}` que sirvan `salida/situaciones.json`. Extiende `research/app/API_CONTRACT.md`. Si el fichero no existe, responde 200 con lista vacía y aviso, no un 500.

## Paso 2 · La vista «Situaciones» en la SPA

Pestaña **«Situaciones»** en `research/app/static/index.html` (sigue `research/app/DESIGN.md`), para **analizar**, no solo listar:

- **Titular:** cuántas hay, cuántas pasan/fallan y, sobre todo, **cuántas centrales fallan**.
- **Filtros:** ámbito, rol, estado, `central` y búsqueda libre.
- **Lista ordenada:** centrales primero, luego las que fallan. Cada fila: id, ámbito, rol, la premisa, valor vs esperado, semáforo.
- **Detalle:** premisa, por qué importa, condición («si X entonces Y, salvo Z»), test, resultado, diagnóstico de la fase 3 e iteración.
- **Ejemplos navegables:** las empresas × mes de `resultado.ejemplos`, enlazando a la ficha de empresa (caja, trayectoria, explicación).
- Las `no_verificable` se agrupan aparte con su motivo.

## Paso 3 · El motor proactivo (sin modelo de predicción)

El «va a romper la caja en 2 meses» **no** sale del forecaster de LGBM. Sale de una **proyección de tesorería determinista y explicable línea a línea**:

```
caja(T+h) = caja(T)
          + cobros pendientes con vencimiento en (T, T+h]        (facturas emitidas pendientes, por due_date)
          − pagos pendientes con vencimiento en (T, T+h]         (facturas recibidas pendientes, por due_date)
          − nóminas recurrentes de los últimos meses × h         (media robusta, no la del último mes)
          − cuotas de deuda del cuadro de amortización           (debt_schedule_config; si falta, la media de debt_service)
```

Reglas:
- **Nada de LGBM ni del `TrajectoryForecaster`.** Es aritmética sobre el panel y las facturas; cada término se puede señalar en la UI.
- La «rotura» es el primer `h` con `caja(T+h) < 0` (o por debajo del umbral de tensión de la política de la fase 1).
- Implementa `research/src/proactive.py` con esa proyección y el endpoint `/api/proactive` (extiende `API_CONTRACT.md`). Puntúa con el **modelo vigente sin reentrenar**.

## Paso 4 · Qué producto se puede financiar (factoring bien entendido)

No uses `overdue_ar` para decidir un factoring: lo que ya está vencido **casi nunca se descuenta**. Lo que se anticipa son las **facturas emitidas pendientes que aún no han vencido** (`pending_amount ≠ 0`, `status ≠ paid`, `due_date > T`, documento de tipo factura). Usa lo que hay en el dataset, no supuestos:

- `debt_products.type` incluye **24 productos de factoring** y **229 de confirming**; úsalos para saber qué producto encaja y qué hay contratado.
- `invoices` tiene **53.761 `paymentDocument`** y las facturas emitidas pendientes son la base del anticipo.
- Hay **~130.000 movimientos** con «pagaré/efecto/remesa» en la descripción: sirven para detectar cobro aplazado y estimar el descuento realizable.

Decide la **acción** (lend / watch / decline) y el **producto** (factoring / confirming / línea / refi / ninguna) según la política de la fase 1, y devuelve `score`, `band`, `accion`, `producto`, `meses_antelacion`, `razones` (Y, Z, K en lenguaje llano) y la contribución por feature (`explain()`).

## Paso 5 · Validación no circular sobre empresas reales

Diseñar un caso para que dispare el factoring y ver que lo dispara **no demuestra nada**. Añade una prueba sobre **empresas reales que el modelo no ha visto**:

1. Elige empresas del panel que **no** estén en el train del artefacto (usa `score_oof`/folds por `group_id`, o un grupo apartado).
2. Sitúate en un mes **T** cualquiera y deja que el sistema recomiende, sin ver el futuro.
3. Comprueba qué pasó de verdad en **T+2**: ¿se rompió la caja? ¿entró en tensión?
4. Reporta la **precisión de la recomendación** a 2 meses (cuántas de las «necesitan deuda» la rompieron, y cuántas de las «no necesitan» no).

El caso ideal para la demo es **«empresa real, dos meses antes»**: se enseña el panel en T, la recomendación, y el desenlace real en T+2. Eso sí convence al jurado.

Para las empresas nuevas de ejemplo, **no** inventes un `escenarios.json` con drivers: `panel.py` lee movimientos y facturas crudos. Genera un CSV con el **esquema del reto** (transactions/invoices/companies) y pásalo por `predict_submission.py --csv-dir <carpeta>`, que es la ruta real de empresas nuevas.

## Paso 6 · Guion para el jurado

Escribe `salida/demo/guion.md`: recorrido de 3 minutos. Orden sugerido: una **empresa real dos meses antes** (panel en T → recomendación → desenlace en T+2) → la **sala de situaciones** (centrales que fallan y por qué) → una situación abierta con sus empresas de ejemplo → la ficha de una de ellas.

## Criterios de aceptación

- `uv run uvicorn app.server:app --port 8090` responde 200 en `/api/situaciones`, `/api/situaciones/{id}` y `/api/proactive`; la pestaña «Situaciones» carga.
- Aparecen todas las situaciones (≥100 tras la fase 2); filtros y búsqueda funcionan; los ejemplos enlazan a la ficha real.
- La proyección de caja es **aritmética y explicable**; no usa el forecaster.
- El factoring se decide sobre **facturas emitidas pendientes no vencidas**, no sobre vencidas.
- La validación sobre empresas reales no vistas reporta precisión a 2 meses.
- El control «sano» no dispara deuda y el «decline» no la concede. Nada de reentrenar.

## Reglas

- Escribe en `research/src/`, `research/app/`, `research/tests/` y `salida/`. No toques `data/`, ni los CSV, ni `analysis/`.
- Trabajas en la rama activa. Sigue `AGENTS.md` y `research/app/DESIGN.md`. Nada de secretos en ficheros.
- Escribe en español. Cada afirmación sobre el código lleva su referencia (`file:line`).
- Termina con: nº de situaciones servidas, las centrales que fallan, la precisión a 2 meses de la recomendación y la ruta de la pestaña «Situaciones».
