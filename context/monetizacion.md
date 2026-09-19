# Monetización — la fila del CFO, con números

[`scoring.md`](scoring.md) establece que **la métrica cambia con la oferta y con
quien mira**, y lo resuelve en una tabla de cuatro filas: banco, aseguradora, CFO,
Embat. Este documento rellena **la fila del CFO** con lo que se le vende y cuánto
vale, medido sobre el dataset.

No cambia el score ni el marco del prestamista. El motor es el mismo; esto es qué
se monta encima y quién lo paga.

> *"Si en cinco minutos no queda claro quién compra el producto y por qué, la
> propuesta estará incompleta."* — enunciado

---

## TL;DR

**12,1 M€/año** sobre las 1.286 empresas (banda 4,3 – 28,5 M€). El 99% sin riesgo
de crédito.

Y un dato que conviene tener claro **antes** del turno de preguntas: sobre esta
cartera, **la financiación son 105 k€/año — el 0,9% del total**. Lo que pesa es
colocar el excedente y ejecutar la divisa. Ver *"La conversación incómoda"* abajo.

---

## El tamaño de la oportunidad

**12,1 M€/año sobre la cartera, sin captar un solo cliente nuevo.**

Eso es lo que hace que la cifra importe. No es un plan de crecimiento que dependa de
vender más suscripciones: es ingreso adicional sobre las empresas que Embat **ya
tiene conectadas**, con los datos que **ya está ingiriendo**. Expansión sobre la base
instalada, que es el ingreso más valioso que existe en SaaS y el que mueve la
valoración.

Para poner los 12,1 M€ en contexto: Embat procesó **250.000 M€ en 2025** y levantó
una Serie B de **30 M€**. El flujo anual del dataset (275.160 M€) coincide con ese
orden de magnitud — es la misma escala de negocio.

### La cifra es robusta al tamaño de la cartera

El dataset tiene 1.286 empresas; Embat declara 400+ clientes. Parecería que la
estimación se cae por tres. No se cae, porque **el 76% del ingreso está ligado al
flujo y a los saldos, no al número de empresas**:

| Línea | Depende de | ¿Cambia con 400 vs 1.286? |
|---|---|---|
| Divisa (3,7 M€) | Flujo en divisa | No — el flujo es el mismo |
| Excedente (5,4 M€) | Saldos ociosos | Apenas — mismos saldos, menos cuentas |
| Módulo (2,7 M€) | Nº de empresas | **Sí** — bajaría a ~0,8 M€ |
| Resto | Mixto | Marginal |

Sobre una cartera de 400 clientes con el mismo flujo, el total sale **~10,2 M€** en
vez de 12,1 M€. La estimación aguanta porque las líneas grandes no se cuentan por
cabezas, se cuentan por euros que pasan.

### La comparación que lo deja claro

Para añadir 12,1 M€ vendiendo más suscripciones habría que **triplicar la base de
clientes**. Por esta vía, cero clientes nuevos: el producto se activa sobre quien ya
está dentro, y el score que lo habilita es el mismo que estamos construyendo para el
reto.

---

## El espejo de nuestra propia tesis

`scoring.md` pone como **criticidad crítica** que *la caja disponible se evapore en
poco tiempo*. Correcto, y es la señal buena.

Nadie ha mirado el caso contrario: **la caja que no se mueve.**

| Tipo de cuenta | Saldo | Cuentas | % |
|---|---:|---:|---:|
| `checking` | 8.057 M€ | 3.612 | **96,1%** |
| `investment` | 242 M€ | 147 | 2,9% |
| `saving` | 82 M€ | **8** | 1,0% |

**Ocho cuentas de ahorro en 1.286 empresas.** Ratio ocioso/remunerado: 24,8×.

Descontando un colchón de dos meses de gasto operativo, quedan **2.378 M€ de
excedente real** en **375 empresas** (mediana 120.658 € cada una).

**Y esto no es desconocimiento, es desconfianza.** El barrido automático de
excedentes existe hace décadas y no lo usan, porque ningún CFO entrega caja
operativa a una regla estática que no sabe que el día 5 vence una amortización.

Por eso **el score desbloquea el producto**: el colchón se calcula, no se fija. Sin
trayectoria, decirle a una empresa que inmovilice caja es temerario. Con ella,
sabes cuánto y hasta cuándo. Es la misma señal de criticidad de `scoring.md`, leída
por el otro extremo.

---

## Qué compra la empresa

Todo se vende **a la empresa que aporta los datos**, que el enunciado señala como
el comprador más evidente.

| Qué compra | Empresas | Qué gana |
|---|---:|---|
| Colocación del excedente | 375 | 2-3% sobre dinero que estaba al 0% |
| Ejecución de divisa anticipada | multi-divisa | 150 pb → 15 pb en sus obligaciones |
| Financiación con fecha e importe | 313 | Evitar el impago negociando con meses |
| El cuadro de mando | todas | Saber, que es lo que hoy no tienen |

### Ingreso

| Línea | Conservador | **Central** | Agresivo |
|---|---:|---:|---:|
| Margen sobre excedente | 1,8 M€ | **5,4 M€** | 10,7 M€ |
| Divisa | 1,2 M€ | **3,7 M€** | 11,9 M€ |
| Suscripción del módulo | 1,1 M€ | **2,7 M€** | 5,4 M€ |
| Pagos internacionales | 81 k€ | 212 k€ | 379 k€ |
| Originación de financiación | 77 k€ | 105 k€ | 144 k€ |
| **TOTAL** | **4,3 M€** | **12,1 M€** | **28,5 M€** |

≈ 9.400 €/empresa/año. Netas de reparto con partner (banco o BaaS para el depósito,
bróker para la divisa), porque Embat es software y no entidad. En bruto serían
17,4 M€.

### La unidad económica

Una empresa con el excedente mediano de **120.658 €** gana 2.400–3.600 €/año de
rendimiento que hoy no percibe, y paga ~1.200 € de margen. **Neto +1.200 a
+2.400 €.** El cliente gana dinero comprando el producto: no hay objeción de precio.

---

## La conversación incómoda

`scoring.md` está construido sobre la lógica del prestamista — la prueba de los
100.000 €, *"prestar / vigilar / no prestar"*, *"hay que contactar mucho a bancos"*.
**Ese marco es correcto para el score.** Pero sobre esta cartera concreta, el
producto de crédito es pequeño:

| | Ingreso central | % |
|---|---:|---:|
| Financiación | 105 k€ | **0,9%** |
| Excedente + divisa | 9,1 M€ | 76% |

Si presentamos un marketplace de crédito y alguien de Embat pregunta *"¿cuánto vale
esto sobre nuestra cartera?"*, la respuesta honesta es "poco". Mejor tenerlo
medido nosotros que descubrirlo en el turno de preguntas.

**No es un argumento para cambiar el score.** Es para elegir con qué producto se
lidera el bloque de Valor, y para tener la cifra preparada por si preguntan.

---

## Por qué la divisa pesa

**7,2% del flujo está en divisa distinta a la de la empresa** — 19.812 M€/año sobre
275.160 M€ totales.

Hoy la empresa compra divisa **el día que paga**, al spread de su banco (50-200 pb).
Si el modelo ve con 60 días una obligación de 400.000 USD, se compra cuando se
quiere y al precio que se quiere.

**El competidor no es otro bróker: es que el cliente no se entere hasta el día del
pago.** El producto no compite en precio, compite en antelación — que es
exactamente lo que mide el bloque de anticipación.

*Regulatorio:* divisa al contado dentro de un pago es entidad de pago (PSD2, ligero);
seguros de cambio a plazo son derivados (MiFID, pesado). Salida habitual: partner con
reparto de spread, ya descontado arriba.

---

## Valor creado vs. capturado

| Para las empresas | Al año |
|---|---:|
| Excedente colocado al 2-3% | 47,6 – 71,3 M€ |
| Ahorro en divisa (150 pb → 15 pb) | **267 M€** |
| Impagos evitados | 19,2 M€ en riesgo |
| **Total** | **~350 M€** |

**Se crean ~350 M€ y se captura el 3,5%.** No se extrae, se reparte.

---

## Bases medidas

Reproducibles sobre `data/`. Lo de abajo no es supuesto.

| | |
|---|---:|
| Flujo anual (suma de \|importe\|) | 275.160 M€ |
| Expuesto a divisa (7,2%) | 19.812 M€ |
| Caja en corriente al 0% | 8.057 M€ |
| Excedente sobre colchón de 2 meses | 2.378 M€ |
| Demanda de financiación anualizada | 19,2 M€ |
| Empresas que tocan déficit / superávit | 313 / 375 |

**Supuestos** (no medidos): adopción 25-45% según línea, 15 pb en divisa, 100 pb de
margen bruto en depósito, 350 €/mes el módulo.

---

## Tres avisos

**Tipos de interés.** La línea de depósito es función del ciclo. Con el euríbor al
2-3% funciona; en 2021, con tipos negativos, valía cero. Decirlo antes de que lo
pregunten.

**Posicionamiento.** El discurso de Embat es *"conectamos con TUS bancos, somos
neutrales"*. Captar saldos lo tensiona. La versión que no lo rompe: no ser la cuenta
operativa, ser **la cuenta del excedente**.

**Divisas sin convertir.** Los saldos están sumados en crudo. El 82% de los productos
son EUR, así que el orden de magnitud aguanta, pero la cifra exacta no es rigurosa
hasta aplicar conversión.

---

## El producto, en una frase

> **El colchón dinámico: cada mes tu caja se parte en lo que vas a necesitar y lo que
> no. Lo primero se queda. Lo segundo trabaja — y si sale negativo, te avisamos con
> meses de antelación.**

Un solo cálculo, las dos colas de la cartera, 688 empresas. Responde al titular del
reto —*¿puede el dinero decir cómo está una empresa?*— y añade la parte accionable:
como lo dice con antelación, se puede hacer algo al respecto.
