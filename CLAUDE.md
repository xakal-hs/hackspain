# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado del repo

Repo para HackSpain 2026, reto **X Ray** de Embat. El dataset ya está en `data/` y hay un EDA reproducible en `analysis/`. Todavía no hay score, producto ni demo.

El enunciado completo está en `X Ray.pdf`, en la raíz. Al PDF le falta el final de la sección de evaluación.

## Setup y ejecución

Stack: Python 3.12 + DuckDB (consultas sobre los CSV, sin cargar nada en memoria) + Plotly (informe autocontenido, sin CDN).

```bash
uv venv --python 3.12
uv pip install duckdb plotly streamlit pandas

.venv/Scripts/python.exe scripts/build_cash_db.py      # materializa analysis/cash.duckdb (~20 s)
.venv/Scripts/python.exe analysis/generate_report.py   # genera analysis/report.html (~80 s)
.venv/Scripts/python.exe scripts/validate_cash.py      # comprobaciones del histórico de caja
.venv/Scripts/python.exe -m streamlit run analysis/app.py
```

| Fichero | Contenido |
| --- | --- |
| `analysis/generate_report.py` | Informe EDA completo: universo, tesorería, facturas, deuda, correlaciones, outliers y calidad |
| `analysis/cash_history.py` | Reconstrucción del histórico de caja empresa × mes, métricas de trayectoria, diagnóstico y secciones 05–09 del informe |
| `analysis/app.py` | Explorador interactivo: cohorte, empresa, grupo, estacionalidad y consola SQL |
| `scripts/build_cash_db.py` | Materializa el panel en `analysis/cash.duckdb`; la app lo abre y arranca en segundos en lugar de minutos |
| `scripts/validate_cash.py` | Valida la reconstrucción contra el saldo ancla e imprime cobertura y centinelas |
| `scripts/check_determinism.py` | Construye el panel tres veces y comprueba que los recuentos y los diagnósticos no cambian |

`analysis/cash.duckdb` está en `.gitignore` y se regenera. La app lo abre en solo lectura a propósito: con acceso de escritura DuckDB bloquea el fichero y `build_cash_db.py` falla con un error de E/S opaco.

### Decisiones de la reconstrucción de caja

Están documentadas en `analysis/cash_history.py` y explicadas en el informe. Las que condicionan cualquier modelo posterior:

- **Fórmula**: `caja(p,t) = saldo_ancla(p) + Σ movimientos hasta t − Σ movimientos hasta la fecha del ancla`, por producto y en su divisa nativa. El cuadre contra `balances.csv` es exacto (desvío máximo < 1e-5 €).
- **El ancla no es única**: los saldos van del 2026-08-25 al 2026-09-01, hay que usar la fecha real de cada producto.
- **Caja = cuentas líquidas** (`checking`, `saving`, `wallet`). `investment` y `risk` no tienen ni un movimiento; tarjetas, TPV y plataformas de gasto miden consumo, no saldo.
- **Divisas**: `exchange_rate` trae 1,0 por defecto; al filtrar ese valor se comporta como unidades por euro. Se usa la mediana por divisa. Las 15 divisas sin evidencia se excluyen en lugar de convertirse a la par.
- **Valores centinela**: 4 cuentas y 13 movimientos superan los 100 M € (el P99 real es 1,7 M €). Un ingreso ficticio de 1.000 M deja toda la historia anterior en −1.000 M, así que se descuentan.
- **Ventana observada**: cada serie empieza en el primer mes con movimientos de la empresa y termina en 2026-08. Solo 422 de las 1.286 empresas tienen actividad en 2024-09; antes del primer movimiento el back-cast es una línea plana artificial.
- **El nivel absoluto no es solvencia**: la caja visible cubre solo 0,73 meses de pagos en la mediana, porque las cuentas conectadas son un subconjunto. Se lee como cobertura relativa a la propia empresa.
- **Series con deriva**: si el back-cast exige más de un mes de pagos en descubierto, la serie no es fiable (faltan cuentas). Son el 4% de la cola y se excluyen de los agregados, sobre todo del déficit por grupo: una sola empresa así lo multiplicaba por cuatro.
- **La caja se redondea al céntimo**: la reconstrucción suma miles de importes en coma flotante, así que las cuentas que vuelven a saldo cero caen en ±1e-13 con un signo que depende del orden de agregación de DuckDB. Sin redondear, 28 empresas con caja exactamente nula salían como `caja negativa` y el recuento cambiaba en cada ejecución (80, 83, 81 en tres construcciones seguidas). Redondeando en `panel_product` y `panel_company` el panel es reproducible y esas empresas pasan a `colchón crítico`, que es lo que son. Cualquier umbral de signo sobre importes reconstruidos necesita este redondeo.
- **El país es texto libre y hay que normalizarlo**: España llega escrita de siete formas (`ES`, `ESPAÑA`, `España`, `ESPANYA`, `Espanya`, `Spain` y una con espacio final), y también aparecen `Portugal`, `Italia` y `Alemania` junto a sus ISO-2. Sin normalizar, el mismo país se parte en varios segmentos: `ES` pasa de 142 a 167 empresas al unificarlo. La macro `country_norm` de `cash_history.py` lo reduce a ISO-2 e incluye grafías que el train no trae, porque el test oculto puede escribirlo de otra manera. El 82% de las empresas no informa país, así que sigue siendo un segmento pobre.

## El reto

A partir del rastro financiero de 24 meses de cada empresa (septiembre 2024 → septiembre 2026), hay que construir:

1. Un **score de salud financiera** por empresa y mes. Es el motor de todo lo demás.
2. **Un producto vendible construido sobre el score**: un marketplace, una póliza, una línea de circulante, un agente… Hay que identificar al comprador. La pista del enunciado es que el comprador más obvio es la empresa que aporta los datos, es decir, Embat.

No se trata de predecir quiebras. Hay que leer el comportamiento en las dos direcciones y hacerlo antes de que sea evidente. El sistema debe responder a seis preguntas, empresa por empresa y mes a mes:

- **Quién está sano.** Detectar empresas excepcionalmente sólidas importa tanto como detectar las que se hunden.
- **Quién está mejorando.** Por ejemplo, una empresa que pasa de 45 a 65.
- **Quién empieza a torcerse.** Por ejemplo, una que baja de 82 a 68 y todavía parece sana.
- **Bache o caída.** Hay que separar un mal mes de caja de un deterioro estructural.
- **Por qué ha cambiado.** Qué señal se movió y cuándo.
- **Cuándo se vio venir.** Cuántos meses de antelación tuvo la detección.

## Requisitos de la entrega

Obligatorios:
- **Predicción sobre el test oculto.** Hay 60–80 empresas que el sistema nunca ve y que entran en el leaderboard. El score tiene que generalizar, así que conviene validar con particiones que no se crucen: si una misma entidad aparece en train y validación, se filtra información.
- **Señal en las dos direcciones.** Hay que reconocer la mejora igual de bien que el deterioro.
- **Trayectoria, no foto.** La salida debe reflejar hacia dónde va la empresa, no solo su nivel en el último mes.
- **Explicación.** Para cualquier empresa hay que poder decir por qué saca ese número y qué lo movió desde el mes anterior. Una caja negra no vale.
- **Producto encima del score, con comprador identificado.** Hay que saber quién paga y por qué le sale a cuenta.
- **Demo navegable.** Tiene que abrirse y probarse delante del jurado. Un notebook que solo corre en un portátil no cuenta.

Bonus:
- **Anticipación medida.** Cuántos meses antes se detecta el cambio.
- **Monitor.** Alertas proactivas cuando una empresa se mueve de verdad.

Evaluación: se puntúan tres bloques con el mismo peso.
- **Si acierta:** generalización, trayectoria y las dos caras.
- **Si llega a tiempo:** anticipación, estabilidad frente a baches y monitor.
- **Si vale algo:** producto, comprador, explicación y artesanía.

Según el enunciado, *"un modelo sencillo con un producto claro encima nos interesa más que uno sofisticado que se queda en el número"*. Hay que priorizar en consecuencia.

## Dataset (todavía no está en el repo)

Son datos sintéticos generados a partir de distribuciones reales de tesorería de pymes: 1.286 empresas agrupadas en 250 grupos empresariales, repartidos en nueve ficheros. `company_id` es la clave que cruza todos los ficheros.

| Fichero | Contenido |
| --- | --- |
| `groups.csv` | Grupos empresariales, de 1 a 24 empresas por grupo (mediana 2) |
| `companies.csv` | Grupo, país, moneda, ERP y fecha de alta |
| `banking_products.csv` | Cuentas: corriente, tarjeta, TPV, ahorro, inversión y plataforma de gastos |
| `debt_products.csv` | Préstamos, leasing, líneas de crédito, hipotecas, renting, factoring, confirming y avales, con importe concedido y saldo pendiente |
| `debt_schedule_config.csv` | Cuadros de amortización: tipo de cuota, frecuencia, plazos, tipo de interés y próxima fecha de pago |
| `transactions.csv` | Movimientos bancarios: fecha, importe, categoría, conciliación, contraparte y concepto |
| `invoices.csv` | Facturas del ERP emitidas y recibidas: emisión, vencimiento, fecha de cobro o pago, pendiente, estado y contraparte |
| `balances.csv` | Saldos a 1 de septiembre de 2026 (solo la foto final) |
| `data_dictionary.md` | Descripción de todos los campos, fichero a fichero |

Implicaciones a tener en cuenta:
- `balances.csv` solo contiene la foto final. Los saldos históricos mensuales hay que reconstruirlos hacia atrás a partir de `transactions.csv`; ya está hecho en `analysis/cash_history.py`.
- Hay datos multimoneda y multipaís. Normalizad los importes antes de agregarlos.
- **No hay campo de sector.** Los únicos segmentos declarados son país (a menudo vacío), moneda y ERP. El informe usa además un sector inferido: clústeres de empresas por la mezcla de categorías de sus movimientos.
- Consultad `data_dictionary.md` antes de suponer la semántica de un campo o de sus valores categóricos.

## Preguntas abiertas

Resolvedlas con la organización y documentad aquí la respuesta:
- ¿El score y el test oculto se calculan por empresa (`company_id`) o por grupo empresarial? El enunciado habla de "250 empresas", pero el dataset tiene 1.286 empresas en 250 grupos.
- ¿Qué formato de predicción pide el leaderboard y cómo se envía?
- ¿Existe una variable objetivo o unas etiquetas en el set de entrenamiento, o el score es no supervisado?
