# Dónde ser nosotros

**Marco de producto · 19 de septiembre de 2026.** La oportunidad no es el SKU con más
comisión en la SPA. Es una decisión de colchón que parte la caja en lo que hay que conservar,
lo que puede trabajar y lo que hay que adelantar —y esa decisión abre productos que hoy
ejecuta un partner y mañana pueden estar en el balance de Embat.

Cálculo: [`notebooks/02_productos.ipynb`](../notebooks/02_productos.ipynb) y
[`analysis/productos.py`](../analysis/productos.py) → [`analysis/productos.html`](../analysis/productos.html).
Las rentas de excedente y divisa coinciden con [`monetizacion.md`](monetizacion.md).

## El criterio

Tres lentes a la vez, en este orden:

1. **Impacto para el CFO** — ahorro recurrente o un salto grande de salud financiera (caja hoy, runway, no quebrar el colchón).
2. **Dinero para Embat dentro de ese impacto** — spread o origination, no un ranking de comisiones simuladas.
3. **Derecho a crear o intermediar el producto** — hoy no somos banco; el rastro tiene que dejar un libro que mañana sí pueda estar en balance (depósito o circulante).

Lo que no entra: maximizar un Excel de take independiente (reserve a 37 M€, seguro crudo a 15 M€). Eso es cola del generador, no identidad.

## Producto en una frase

> **X-Ray parte la caja en colchón, exceso y agujero, y enruta cada uno a un producto financiero: barrer, adelantar cobros o ejecutar divisa. Hoy un partner ejecuta; el score ya es la política del banco que Embat todavía no es.**

El módulo de decisión es lo que se vende a Embat. Los rieles (depósito, factoring, FX, póliza) son lo que se intermedia ahora y se puede poseer después.

## Hay dos palos grandes

El resto es timing, upsell o semilla de underwriting.

```
Detectar → partir caja (colchón / exceso / agujero)
                │
     ┌──────────┼──────────────┐
  exceso      agujero + AR    divisa
  barrido     factoring       ejecutar cuando toca
  (pasivo)    (activo)        (flujo)
```

### 1. Barrido de excedente — crear un producto que el cliente no tiene

**344 M€** ociosos en **370** empresas; **368 no tienen cuenta `saving`**. X-Ray no compite con un depósito de Embat: lo inventa sobre cuentas corrientes.

| Quién | A 100 % | A 35 % |
|---|---:|---:|
| CFO (neto ~1,5 % tras 100 pb) | **5,16 M€/año** | 1,81 M€/año |
| Embat (100 pb) | 3,44 M€/año | **1,20 M€/año** |

El cliente gana más que Embat. Eso es el diseño correcto: impacto primero, spread segundo.

Camino a banco: hoy un bróker o BaaS ejecuta el barrido. El día que Embat tome depósitos, **esta cola es el pasivo**. El score ya sabe quién puede sacar dinero de la cuenta sin romper el colchón.

### 2. Anticipar cobros — caja hoy, sin préstamo nuevo

Aquí está el impacto de salud financiera más grande, y el activo del banco futuro. Un banco ya presta. Nadie más ve a la vez **caja viva + factura impagada + que no hay póliza**.

- **320** empresas tensas tienen AR vencido factorable: **795 M€**. **314** no tienen factoring.
- De **41** agujeros (11,38 M€), **26** son factorables. Su AR vencido es **137 M€** frente a un agujero de **8,8 M€**. No necesitan un marketplace de crédito: necesitan cobrar lo suyo.
- **19** agujeros no tienen póliza y sí tienen AR cedible. Foto de «no somos banco todavía, pero ya sabemos a quién no hay que mandar al banco».

Techo medido, no previsión: adelantar el AR elegible desbloquea del orden de **1.260 M€ de caja hoy** a un coste del 1,5 %. Embat, como intermediario, se lleva una fracción de ese 1,5 %. Como factor, el día de mañana, el libro —con el rastro de tesorería y ERP que el banco no ve.

Hay **110** empresas con excedente **y** AR vencido (141 M€ ociosos + 275 M€ de cobros). Ahí «ser nosotros» es no recomendar barrido a ciegas ni un préstamo: **cobrar primero, colocar el resto**.

## Cómo se sostiene el trío

| Palanca | Impacto CFO | Dinero Embat ahora | Intermediario → banco |
|---|---|---|---|
| **Yield** | Recurring, medible, riel inexistente | 1,20 M€/año @ 35 % | Depósito propio |
| **Factoring** | Liquidez: cientos de M€ de AR en empresas tensas | One-shot / origination; libro si sois el factor | Activo (circulante) |
| **FX** | Ahorro = vuestro take (15 pb) | 1,11 M€/año @ 35 % | Principal. Embat **ya** cobra pagos internacionales; X-Ray aporta el *cuándo* |
| **Línea / reserve** | Existencial en 41 agujeros, no un cupón | 0,02 M€ sobre el agujero medido | Licencia + underwriting; **no** lidera el P&L |
| **Seguro** | Prima, no caja | Take pequeño y solapado con factoring | Referral; no os hace banco |

FX es dinero de verdad y entra en el pitch de tesorería. Es **menos identidad**: Embat ya vende el riel. Yield y factoring sí crean un producto que el CFO no tiene delante.

La cifra de crédito defendible sigue siendo pequeña: **11,38 M€** en 41 agujeros. Por eso el jurado no ve un marketplace. El relato de compañía es otro: el agujero es pequeño; **el AR detrás de la tensión no lo es**; el excedente en corriente, tampoco.

## Secuencia

**Ahora** — capa de decisión + intermediación (sin licencia bancaria)

1. Colchón explicable. Eso no lo duplica el forecast de Embat.
2. Barrido del excedente con partner.
3. Factoring / confirming como acción por defecto cuando hay tensión y hay facturas, no «busca un préstamo».

**Después** — dueños del riel

Tomar el depósito del barrido y el libro de anticipos. El score ya es la política: a quién se le barre, a quién se le anticipa, a quién se le dice que no.

**Más tarde** — banco de circulante

La póliza y el crédito genérico salen de haber visto 24 meses de caja. Los 41 agujeros son la prueba de underwriting, no el TAM.

## Reglas

- El pitch de jurado abre con el colchón, el excedente medido y la divisa. No con 11 M€ de agujero.
- El pitch de compañía añade el AR de las tensas y el camino pasivo → activo.
- No rankear la demo de Productos por comisión de la SPA (mezcla yield del CFO con take de Embat, y FX con `n_tx > 50`).
- No originar líneas con una fórmula de gasto que explota en colas. Eso maximiza un Excel, no el impacto ni el derecho a ser el banco después.

## Qué está medido frente a lo que se asume

| Afirmación | Clase |
|---|---|
| 370 empresas, 344 M€ de excedente; 368 sin saving | Medida |
| 261 empresas, 2.108 M€/año de FX; take 1,11 M€ @ 35 % | Medida la base; 15 pb y adopción, supuesto |
| 320 tensas con 795 M€ de AR factorable; 314 sin producto | Medida la elegibilidad; que se ceda, supuesto |
| 26 de 41 agujeros factorables; 137 M€ de AR vs 8,8 M€ de agujero | Medida |
| 1.260 M€ de caja hoy si se factoriza todo el AR elegible | Techo medido, no previsión |
| 5,16 M€/año netos al CFO a 1,5 % sobre 344 M€ | Hipótesis de colocación 2,5 % y 100 pb |
| Embat tomará depósitos o el libro de factoring | Hoja de ruta; no hecho |

Adopción 25 / 35 / 45 %, márgenes y disposición a ceder facturas siguen siendo hipótesis. No escalar 1.286 empresas sintéticas a «500 equipos Embat».
