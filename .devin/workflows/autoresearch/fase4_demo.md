# Fase 4 · La sala de situaciones (presentación final)

Eres el **orquestador** del workflow de autoresearch. Esta es la fase final y su producto es lo que se enseña: una **sala de situaciones** en la UI donde el equipo puede **analizar las +100 situaciones** que definió el consejo, y un caso destacado de **demo proactiva** (empresas nuevas que van a necesitar factoring o refi).

## Paso 0 · Los datos de las situaciones

Las situaciones son las premisas de la fase 2, ya evaluadas. Asegúrate de tenerlas exportadas:

```bash
cd research && uv run python ../.devin/workflows/autoresearch/premisas.py export
```

Eso escribe `salida/situaciones.json`: un array con, por cada situación:

- `id`, `rol`, `ambito`, `premisa`, `por_que`, `condicion`.
- `test` (tipo, columnas, `esperado`) y `verificable`.
- `estado` (`pasa` / `falla` / `no_verificable` / `error`), `resultado.valor`, `resultado.n`.
- `resultado.ejemplos`: hasta 6 filas `{company_id, month, ...}` que ejemplifican la situación.
- `central` (marcada por el consejo en la fase 2), `diagnostico` e `iteracion` (los rellena la fase 3).

Si la fase 3 corrió, el `diagnostico` es la parte más valiosa para analizar: distingue «premisa incorrecta» de «modelo incorrecto».

## Paso 1 · Servir las situaciones

Añade a `research/app/server.py` un endpoint `/api/situaciones` que sirva `salida/situaciones.json` (y `/api/situaciones/{id}` para una sola). Extiende `research/app/API_CONTRACT.md` con el bloque nuevo. Si el fichero no existe, el endpoint responde 200 con una lista vacía y un aviso, no un 500.

## Paso 2 · La vista «Situaciones» en la SPA

Añade una pestaña **«Situaciones»** a `research/app/static/index.html` (sigue `research/app/DESIGN.md`). Debe permitir **analizar** las +100 situaciones, no solo listarlas:

- **Cabecera de titular:** cuántas situaciones hay, cuántas pasan/fallan y, sobre todo, **cuántas centrales fallan** (eso es la noticia).
- **Filtros:** por ámbito (liquidez, cobros, pagos, deuda, observabilidad, comportamiento, estabilidad, calibración, producto, recuperación, gaming, sesgos), por rol que la propuso, por estado, por `central`, y búsqueda de texto libre.
- **Lista ordenada:** primero las centrales, luego las que fallan, luego el resto. Cada fila: id, ámbito, rol, la premisa en una línea, valor vs esperado, y el semáforo de estado.
- **Detalle al abrir una situación:** la premisa completa, por qué importa (qué decisión de crédito cambia), la condición («si X entonces Y, salvo Z»), el test (tipo, esperado, n), el resultado, el diagnóstico de la fase 3 y la iteración en que cambió.
- **Ejemplos navegables:** las empresas × mes de `resultado.ejemplos`, cada una enlazando a la ficha de empresa de la SPA (donde se ve la caja, la trayectoria y la explicación). Esto es lo que convierte «una premisa» en «una situación que puedo mirar».
- Las `no_verificable` se agrupan aparte, con su motivo (son juicio humano/modelo).

## Paso 3 · El caso destacado: demo proactiva

Dentro de la misma sala (o como panel destacado), monta el guion que cierra el reto: **empresas nuevas, que no están en el dataset**.

- Construye 4-6 empresas `NEW_*` en `salida/demo/escenarios.json` con el esquema del panel (`research/src/panel.py`), cada una con una situación diseñada: **factoring** (caja que se rompe en ~2 meses + pagarés a 60-90 días + sin póliza), **refi** (deuda viva con cuota alta y caja cayendo), **línea** (desfase estacional), un control **decline** (caja negativa persistente, sin cobros) y un control **sano**.
- Implementa `research/src/proactive.py` y el endpoint `/api/proactive` (extiende `API_CONTRACT.md`): puntúa y prevé con el modelo vigente **sin reentrenar**, detecta el mes de cruce de caja, lee los pagarés y la póliza, y decide **acción** (lend/watch/decline) y **producto** (factoring/confirming/línea/refi/ninguna) según la política de la fase 1.
- Devuelve `score`, `band`, `accion`, `producto`, `meses_antelacion`, `razones` (Y, Z, K en lenguaje llano) y la contribución por feature (`explain()`).
- Preséntalo como la cabecera de la sala: *«3 empresas nuevas van a necesitar deuda; esta necesita factoring, score X por Y, Z, K»*.

## Paso 4 · Guion para el jurado

Escribe `salida/demo/guion.md`: recorrido de 3 minutos. Debe abrirse delante del jurado sin explicaciones previas. Orden sugerido: cabecera proactiva (el caso factoring) → sala de situaciones (las centrales que fallan y por qué) → una situación abierta con sus empresas de ejemplo → la ficha de una de esas empresas.

## Criterios de aceptación

- `uv run uvicorn app.server:app --port 8090` responde 200 en `/api/situaciones`, `/api/situaciones/{id}` y `/api/proactive`, y la pestaña «Situaciones» carga.
- Aparecen **todas** las situaciones (≥100 tras la fase 2); los filtros y la búsqueda funcionan.
- Los ejemplos de cada situación enlazan a la ficha de empresa real.
- El factoring y la refi se disparan por la situación de caja + pagarés/deuda, no por una regla cableada a mano; el control «sano» no dispara deuda y el «decline» no la concede.
- Nada de reentrenar: se usa el modelo vigente.

## Reglas

- Escribe en `research/src/`, `research/app/`, `research/tests/` y `salida/`. No toques `data/`, ni los CSV, ni `analysis/`.
- Sigue `AGENTS.md` y `research/app/DESIGN.md`. Nada de secretos en ficheros.
- Escribe en español. Cada afirmación sobre el código lleva su referencia (`file:line`).
- Termina con: nº de situaciones servidas, las centrales que fallan, el veredicto de las empresas de ejemplo y la ruta de la pestaña «Situaciones» en la SPA.
