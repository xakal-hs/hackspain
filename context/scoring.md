# Cómo pensar el score

**Interpretación operativa del equipo.** No sustituye el [enunciado](challenge.md): lo traduce a una forma de decidir, con el mismo criterio que usaría alguien que presta su propio dinero.

El leaderboard pide un número. El producto no puede acabarse ahí.

## La prueba de los 100.000 €

Para simplificar el problema: tienes **100.000 €** y tienes que prestarlos. Si se los prestas a una persona, ¿qué le preguntarías? ¿Qué te preocuparía que hiciera o dejara de hacer?

Eso es lo que hacen los bancos. El scoring de un consumidor y el de una empresa identifican la **misma naturaleza de riesgo**; cambia el tipo de dato, no la pregunta. Primero se piensa en el mundo del consumidor y después se lleva a la empresa.

| Si prestaras a una persona, te preocuparía… | En la empresa se llama… | En el dataset se ve en… |
|---|---|---|
| Que se le acabe el dinero de la cuenta en pocas semanas | Caja disponible que se evapora | Saldos reconstruidos + movimientos |
| Que cobre tarde o deje de cobrar | Medio de cobro / DSO | Facturas emitidas, cobros, `pending_amount` |
| Que pague cada vez más tarde a quien le fía | Medio de pago / DPO | Facturas recibidas, pagos a proveedores |
| Que el sueldo se corte o sea irregular | Cobros que caen o se vuelven erráticos | `transactions` (`collection`, `salary`) |
| Que viva al límite de la tarjeta | Líneas de crédito agotadas | `debt_products.outstanding` / `granted` |
| Que pida un préstamo para tapar el agujero | Deuda nueva mientras la caja cae | Alta de deuda + trayectoria de caja |
| Que mienta o no se deje ver las cuentas | Cobertura / observabilidad | ERP ausente, conciliación, huecos |

Las palabras raras (DSO, DPO, medio de cobro, medio de pago) hay que poder llevarlas **a lenguaje de consumidor**. Si el jurado o Embat no pueden repetir la explicación en una frase, el score no se entiende.

## Criticidad: no todas las señales pesan igual

Una empresa que **reduce la caja disponible muy rápido, en muy poco tiempo**, es una señal grave. Debe tener un nivel de impacto / criticidad alto: el score tiene que moverse mucho más que si, de repente, se deteriora un poco el medio de cobro o el medio de pago.

Ese matiz es el que un prestamista siente en la tripa y el que un modelo plano (todas las features al mismo peso) pierde.

| Criticidad | Qué ves | Equivalente consumidor | Qué no hacer |
|---|---|---|---|
| **Crítica** | La caja disponible se evapora en poco tiempo | Se le acaba el efectivo | No suavizarlo con un promedio de ratios |
| **Alta** | Deja de cobrar de forma persistente, o paga solo con deuda nueva | No le entra el sueldo y vive de la tarjeta | No esperar a que el saldo sea cero |
| **Media** | DSO o DPO se mueven un poco | Tarda unos días más en cobrar o pagar | No dejar que esto domine el ranking |
| **Bache** | Un mal mes de caja con recuperación | Un gasto puntual | No tratarlo como deterioro estructural |
| **No es salud** | ERP desconectado, mes truncado, categoría `-` | No te enseña la cuenta | Tratarlo como cobertura, no como riesgo |

La trayectoria importa más que la foto: una empresa sana que empieza a vaciar la cuenta es peor apuesta que una mediocre que está recapitalizándose. Eso es el ejemplo Northbrook (45 → 65) frente a Velasco (82 → 68), leído con criticidad y no solo con el último número.

## El output no es solo un número

Hace falta un número para el leaderboard y para ordenar. Eso no implica que el problema se acabe en un ranking de A contra B. Un prestamista no se queda en “72”: quiere saber **por qué**, **con qué gravedad** y **qué haría**.

Para cada empresa y mes, el sistema debería poder devolver, además del score:

1. **Nivel y trayectoria** — dónde está y hacia dónde va.
2. **Criticidad de lo que se movió** — caja que se evapora ≠ DSO que empeora tres días.
3. **Por qué, en lenguaje llano** — “se le está acabando el dinero de la cuenta”, no solo `Δcash_p10`.
4. **Bache o caída** — si el golpe es puntual o estructural.
5. **Qué haría un prestamista** — prestar / vigilar / no prestar; o, en el producto, avisar / recortar límite / acelerar cobros.

Eso encaja con el enunciado: explicación obligatoria, producto encima del score, y la preferencia de Embat por un modelo sencillo que **sirva para decidir** frente a uno sofisticado que se queda en el número.

## Cómo usarlo al construir

- Pesar primero la **velocidad de quema de caja disponible**; después cobros, pagos y deuda.
- Explicar cada movimiento con la analogía consumidor → empresa.
- No imputar salud a partir de huecos de observabilidad.
- Diseñar la demo para que alguien con 100.000 € que prestar sepa, en un vistazo, a quién se los daría y por qué no al otro.
