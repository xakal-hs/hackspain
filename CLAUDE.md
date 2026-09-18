# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado del repo

Repo recién creado para HackSpain 2026, reto **X Ray** de Embat. Aún no hay código, stack elegido ni dataset. Cuando se elijan, añadid aquí los comandos de setup, ejecución, tests y demo, y la arquitectura real.

El enunciado completo está en `X Ray.pdf`, en la raíz. Al PDF le falta el final de la sección de evaluación.

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
- `balances.csv` solo contiene la foto final. Los saldos históricos mensuales hay que reconstruirlos hacia atrás a partir de `transactions.csv`.
- Hay datos multimoneda y multipaís. Normalizad los importes antes de agregarlos.
- Consultad `data_dictionary.md` antes de suponer la semántica de un campo o de sus valores categóricos.

## Preguntas abiertas

Resolvedlas con la organización y documentad aquí la respuesta:
- ¿El score y el test oculto se calculan por empresa (`company_id`) o por grupo empresarial? El enunciado habla de "250 empresas", pero el dataset tiene 1.286 empresas en 250 grupos.
- ¿Qué formato de predicción pide el leaderboard y cómo se envía?
- ¿Existe una variable objetivo o unas etiquetas en el set de entrenamiento, o el score es no supervisado?
