# X Ray

**HackSpain 2026 · Reto de Embat**  
**18–20 de septiembre · ETSIT UPM, Madrid**

## ¿Puede el dinero decir cómo está una empresa?

Embat proporciona el rastro financiero de 250 grupos empresariales durante 24 meses. El reto consiste en construir un **score de salud financiera** y, sobre ese motor, **un producto que esas mismas empresas estarían dispuestas a comprar**.

| Dato clave | Alcance |
|---|---|
| Dataset | 1.286 empresas sintéticas en 250 grupos |
| Historia | 24 meses, de septiembre de 2024 a septiembre de 2026 |
| Test oculto | 60–80 empresas que el sistema no habrá visto |
| Entrega | El score y un producto vendible construido sobre él |

## El problema

Toda empresa deja un rastro: entra dinero, emite facturas, paga a proveedores, cobra de clientes, dispone deuda y la devuelve. Ese rastro cambia cada día, pero normalmente se analiza mediante fotos fijas, cuentas que llegan tarde y ratings que se actualizan de forma puntual.

El reto ilustra esta limitación con dos trayectorias:

- **Northbrook Foods:** 45 → 65.
- **Velasco Industrial:** 82 → 68.

En el mes 24 solo hay tres puntos de diferencia entre ambas. Sin embargo, una mejora con fuerza y la otra comienza a deteriorarse. La foto actual no permite distinguir cuál representa el mejor riesgo; la trayectoria sí.

## Las seis preguntas que debe responder el sistema

Esto no consiste en predecir quiebras, sino en leer el comportamiento financiero en ambas direcciones y hacerlo antes de que el cambio resulte evidente.

### 1. ¿Quién está sano?

No basta con detectar problemas. Reconocer una empresa excepcionalmente sólida es tan útil como identificar una que se deteriora.

### 2. ¿Quién está mejorando?

Una empresa que pasa de 45 a 65 puede mostrar cifras mediocres hoy y ser la mejor apuesta del año siguiente.

### 3. ¿Quién empieza a torcerse?

Una empresa que cae de 82 a 68 todavía parece sana, pero su comportamiento ya ha cambiado y conviene detectarlo pronto.

### 4. ¿Es un bache o una caída?

Un mal mes de caja no equivale a un deterioro estructural. El sistema debe diferenciar ruido puntual y cambio persistente.

### 5. ¿Por qué ha cambiado?

Un número sin explicación no permite decidir. Debe identificarse qué señal se movió y cuándo.

### 6. ¿Cuándo se vio venir?

Detectar el cambio cuando ya sucede aporta poco valor. Hay que medir cuántos meses antes lo anticipó el sistema.

## Las cuatro capacidades del sistema

Las tres primeras forman el motor; la cuarta convierte ese motor en algo que alguien compraría.

### Leer el rastro

Analizar movimientos bancarios, facturas emitidas y recibidas, comportamiento de pago, coste de financiación y saldos de deuda. El trabajo consiste en decidir qué señales de esos 24 meses son relevantes.

### Construir el score

Crear una puntuación que represente trayectoria y no solo la foto del último mes, y que generalice a las 60–80 empresas ocultas.

### Explicarse

Para cualquier empresa, explicar por qué obtiene su puntuación y qué provocó el cambio frente al mes anterior. Una caja negra no es suficiente para prestar o asegurar.

### Construir algo encima

Crear un producto, servicio o herramienta apoyado en el score, identificar quién pagaría por él y por qué. La propia empresa que aporta los datos es el comprador más evidente.

## El dataset

El dataset contiene **1.286 empresas sintéticas agrupadas en 250 grupos empresariales**, con 24 meses de historia. Se generó a partir de la distribución estadística de datos reales de tesorería de pymes: los volúmenes, la estacionalidad, los patrones de contraparte y las condiciones de financiación se comportan como datos reales, pero ninguna fila corresponde a una empresa, cuenta o persona real.

| Fichero | Contenido |
|---|---|
| `groups.csv` | Un grupo empresarial por fila. Un grupo puede ser un holding con varias filiales: de 1 a 24 empresas, mediana 2. |
| `companies.csv` | Una empresa por fila: grupo, país, moneda, ERP y fecha de alta. `company_id` cruza el resto de ficheros. |
| `banking_products.csv` | Cuentas corrientes, tarjetas, TPV, ahorro, inversión y plataformas de gastos, con banco y moneda. |
| `debt_products.csv` | Préstamos, leasing, líneas de crédito, hipotecas, renting, factoring, confirming y avales; incluye importe concedido y saldo pendiente. |
| `debt_schedule_config.csv` | Condiciones de préstamos con cuadro de amortización: cuota, frecuencia, plazos, interés y próximo pago. |
| `transactions.csv` | Movimientos bancarios: fecha, importe, categoría, conciliación, contraparte y concepto. |
| `invoices.csv` | Facturas ERP emitidas y recibidas: emisión, vencimiento, pago, pendiente, estado y contraparte. |
| `balances.csv` | Saldo de cada cuenta y producto a 1 de septiembre de 2026; es la foto final. |
| `data_dictionary.md` | Definición de todos los campos. |

## Requisitos de la entrega

| Requisito | Qué significa | Estado |
|---|---|---|
| Predicción sobre el test oculto | Puntuar empresas nunca vistas; el resultado entra en el leaderboard. | Obligatorio |
| Señal en las dos direcciones | Reconocer mejora y deterioro. Un detector de quiebras no basta. | Obligatorio |
| Trayectoria, no foto | Reflejar hacia dónde va la empresa, no solo dónde está hoy. | Obligatorio |
| Explicación | Explicar el score y qué lo movió desde el mes anterior. | Obligatorio |
| Producto encima del score | Construir un marketplace, póliza, línea de circulante, agente u otro producto. | Obligatorio |
| Comprador identificado | Decir quién paga y por qué obtiene valor. | Obligatorio |
| Demo navegable | Debe abrirse y probarse ante el jurado; un notebook local no cuenta. | Obligatorio |
| Anticipación medida | Mostrar cuántos meses antes se detecta el cambio. | Bonus |
| Monitor que avisa | Generar alertas proactivas cuando una empresa cambia de verdad. | Bonus |

## Evaluación

Los tres bloques pesan lo mismo. Embat prefiere un modelo sencillo con un producto claro a uno sofisticado que se queda únicamente en el número.

### Si acierta

- **Generalización:** ¿funciona en empresas nunca vistas?
- **Trayectoria:** ¿capta la dirección o solo el nivel actual?
- **Las dos caras:** ¿detecta mejora y deterioro?

### Si llega a tiempo

- **Anticipación:** ¿detecta el cambio antes de que sea evidente y mide cuántos meses antes?
- **Estabilidad:** ¿distingue un bache puntual de un deterioro real?
- **Monitor:** suma puntos si avisa sin que nadie pregunte.

### Si vale algo

- **Producto:** ¿hay algo construido encima del score?
- **Comprador:** ¿se sabe quién paga y por qué? La empresa que genera los datos es el candidato obvio.
- **Explicación:** ¿puede contarse por qué una empresa obtiene ese número?
- **Artesanía:** ¿está bien construido, cuidado y puede demostrarse?

## Posibles productos

Estas ideas son direcciones, no una lista cerrada.

### Marketplace de crédito

Conectar empresas que necesitan financiación con prestamistas, ordenadas por el score. El prestamista obtiene riesgo actualizado y la empresa evita enviar el mismo dossier a múltiples bancos.

### Seguro financiero

Cubrir el impago de clientes con una prima que evoluciona con el score, en lugar de revisarse una vez al año. La póliza detecta el deterioro antes del siniestro.

### Financiación de circulante

Anticipar cobros o extender pagos con un límite recalculado cada mes. El score determina cuánto financiar, a qué precio y cuándo reducir exposición.

### Agente de recomendaciones

Leer el rastro y recomendar acciones semanales: renegociar con proveedores, refinanciar deuda o acelerar cobros. Se vende a la empresa sobre sus propios datos.

### Predicción por sector

Agregar scores por sector para generar señales de inversión antes de los resultados trimestrales. En este caso, el comprador sería el inversor.

### Otras posibilidades

Pricing dinámico, scoring de proveedores, un sello financiero para negociar mejores condiciones o un comparador de financiación. Cualquier propuesta encaja si resuelve una necesidad por la que alguien pagaría.

## Qué aporta la organización

- **El dataset:** 250 grupos y 1.286 empresas sintéticas con 24 meses de historia, nueve ficheros y diccionario de datos.
- **El test oculto, el script de scoring y el leaderboard:** disponibles desde el viernes para medir resultados durante el fin de semana.
- **El equipo:** dos ingenieros rotando en el aula y un especialista de datos localizable durante la noche.
- **Contexto experto:** sesión sobre cómo se mueve el dinero dentro de una empresa, de dónde sale cada fichero y qué significa.

## Mensaje final

La demo cuenta tanto como el producto. Aunque la señal sea buena, si en cinco minutos no queda claro quién compra el producto y por qué, la propuesta estará incompleta. Hay que reservar tiempo para ensayar el pitch.

## Interpretación del equipo

El enunciado pide un número y un producto. Cómo pesar las señales y qué devolver además del ranking está en [Cómo pensar el score](scoring.md):

- Una caja que se evapora en poco tiempo es mucho más grave que un DSO o DPO que se mueve un poco.
- El scoring de un consumidor y el de una empresa preguntan lo mismo; cambia el dato, no la naturaleza del riesgo. La prueba: *si tuvieras 100.000 € para prestar, ¿qué te preocuparía?*
- El output no puede acabarse en un número. Hace falta criticidad, explicación en lenguaje llano y una decisión (prestar / vigilar / no prestar).
- El valor diferencial de Embat es el rastro de tesorería que el banco no tiene para valorar el crédito. Hay que contactar mucho a bancos.
- La métrica cambia según la oferta (circulante, póliza, marketplace…) y según quién mira el score, porque los objetivos no son los mismos.

---

Fuente: artefacto compartido **“X Ray”**, reto de Embat para HackSpain 2026. La sección *Interpretación del equipo* no forma parte de ese artefacto.
