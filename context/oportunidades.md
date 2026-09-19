# Dónde ser nosotros

**Marco de producto · 19 de septiembre de 2026.** La oportunidad no es el SKU con más
comisión en la SPA. Es una decisión de colchón que parte la caja en lo que hay que conservar,
lo que puede trabajar y lo que hay que adelantar —y esa decisión abre productos que hoy
ejecuta un partner y mañana pueden estar en el balance de Embat.

Cálculo: [`notebooks/02_productos.ipynb`](../notebooks/02_productos.ipynb) y
[`analysis/productos.py`](../analysis/productos.py) → [`analysis/productos.html`](../analysis/productos.html).
Las rentas de excedente y divisa coinciden con [`monetizacion.md`](monetizacion.md)
a nivel de empresa; aquí se netean antes contra el agujero de las hermanas del grupo.

## El criterio

Tres lentes a la vez, en este orden:

1. **Impacto para el CFO** — ahorro recurrente o un salto grande de salud financiera (caja hoy, runway, no quebrar el colchón).
2. **Dinero para Embat dentro de ese impacto** — spread o origination, no un ranking de comisiones simuladas.
3. **Derecho a crear o intermediar el producto** — hoy no somos banco; el rastro tiene que dejar un libro que mañana sí pueda estar en balance (depósito o circulante).

Lo que no entra: maximizar un Excel de take independiente (reserve a 37 M€, seguro crudo a 15 M€). Eso es cola del generador, no identidad.

## Producto en una frase

> **X-Ray parte la caja en colchón, exceso y agujero, y enruta cada uno a un producto financiero: barrer, adelantar cobros o ejecutar divisa. Hoy un partner ejecuta; el score ya es la política del banco que Embat todavía no es.**

El módulo de decisión es lo que se vende a Embat. Los rieles (depósito, factoring, FX, póliza) son lo que se intermedia ahora y se puede poseer después.

## Primero el grupo mueve capital

Hay **250** grupos; **179** tienen más de una sociedad. En **13** hay excedente y agujero a la vez. Un CFO de holding no compra yield en una filial y un préstamo en la otra: traspasa caja. Eso no es un SKU de la SPA; es la primera acción de tesorería.

| | Empresa a empresa | Tras pooling |
|---|---:|---:|
| Excedente colocable | 344 M€ (370) | **341 M€** (360) |
| Take yield @ 35 % | 1,20 M€/año | **1,19 M€/año** |
| Agujero (demanda de crédito) | 11,38 M€ (41) | **8,05 M€** (34) |
| Capital que se movería | — | **3,33 M€** en 13 grupos |

**7** agujeros (1,33 M€) los cubre por completo una hermana; **7** de esos no tienen póliza y no la necesitan si el grupo traspasa. **25** empresas yield tienen una hermana en números rojos: no se barre a ciegas. FX no se netea (es flujo de moneda, no saldo). El factoring de cobros estructurales sigue; como liquidez de agujero, **4** de **26** agujeros factorables quedan cubiertos internamente y quedan **22** con **129 M€** de AR.

El TAM casi no cambia. Cambia a quién no hay que vender un producto.

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

**341 M€** netos en **360** empresas cuyo grupo no tiene un agujero que tapar primero (bruto: 344 M€ en 370; 25 de ellas tienen hermana en agujero). **368 no tienen cuenta `saving`**. X-Ray no compite con un depósito de Embat: lo inventa sobre cuentas corrientes.

| Quién | A 100 % | A 35 % |
|---|---:|---:|
| CFO (neto ~1,5 % tras 100 pb, sobre 341 M€) | **5,11 M€/año** | 1,79 M€/año |
| Embat (100 pb) | 3,41 M€/año | **1,19 M€/año** |

El cliente gana más que Embat. Eso es el diseño correcto: impacto primero, spread segundo.

Camino a banco: hoy un bróker o BaaS ejecuta el barrido. El día que Embat tome depósitos, **esta cola es el pasivo**. El score ya sabe quién puede sacar dinero de la cuenta sin romper el colchón.

### 2. Anticipar cobros — caja hoy, sin préstamo nuevo

Aquí está el impacto de salud financiera más grande, y el activo del banco futuro. Un banco ya presta. Nadie más ve a la vez **caja viva + factura impagada + que no hay póliza**.

- **320** empresas tensas tienen AR vencido factorable: **795 M€**. **314** no tienen factoring. **205** de esas tensas tienen una hermana con excedente: el primer teléfono no es el factor, es tesorería de grupo.
- De **41** agujeros (11,38 M€), el grupo cubre **7** (1,33 M€). Quedan **8,05 M€** de demanda de crédito. **26** eran factorables; **4** los tapa la hermana y **22** siguen con **129 M€** de AR frente a un agujero que el grupo no cubre.
- **25** agujeros no tienen póliza y el grupo tampoco los cubre. Foto de «no somos banco todavía, pero ya sabemos a quién no hay que mandar al banco» —y a quién no hay que mandar porque la hermana puede pagar.

Techo medido, no previsión: adelantar el AR elegible desbloquea del orden de **1.260 M€ de caja hoy** a un coste del 1,5 %. Embat, como intermediario, se lleva una fracción de ese 1,5 %. Como factor, el día de mañana, el libro —con el rastro de tesorería y ERP que el banco no ve.

Hay **110** empresas con excedente **y** AR vencido (141 M€ ociosos + 275 M€ de cobros). Ahí «ser nosotros» es no recomendar barrido a ciegas ni un préstamo: **cobrar primero, colocar el resto**.

## Cómo se sostiene el trío

| Palanca | Impacto CFO | Dinero Embat ahora | Intermediario → banco |
|---|---|---|---|
| **Yield** | Recurring, medible, riel inexistente | 1,19 M€/año @ 35 % (neto de pooling) | Depósito propio |
| **Factoring** | Liquidez: cientos de M€ de AR en empresas tensas | One-shot / origination; libro si sois el factor | Activo (circulante) |
| **FX** | Ahorro = vuestro take (15 pb) | 1,11 M€/año @ 35 % | Principal. Embat **ya** cobra pagos internacionales; X-Ray aporta el *cuándo* |
| **Línea / reserve** | Existencial en el agujero que el grupo no tapa (8,05 M€), no un cupón | 0,01 M€ sobre el agujero neto | Licencia + underwriting; **no** lidera el P&L |
| **Seguro** | Prima, no caja | Take pequeño y solapado con factoring | Referral; no os hace banco |

FX es dinero de verdad y entra en el pitch de tesorería. Es **menos identidad**: Embat ya vende el riel. Yield y factoring sí crean un producto que el CFO no tiene delante.

La cifra de crédito defendible es más pequeña todavía: **8,05 M€** tras pooling (11,38 M€ brutos en 41 agujeros). Por eso el jurado no ve un marketplace. El relato de compañía es otro: el agujero es pequeño; **el AR detrás de la tensión no lo es**; el excedente en corriente, tampoco; y parte de lo que parece crédito es un traspaso entre filiales.

## Secuencia

**Ahora** — capa de decisión + intermediación (sin licencia bancaria)

1. Colchón explicable. Eso no lo duplica el forecast de Embat.
2. Si el grupo tiene excedente y agujero, movimiento de capital. No un SKU.
3. Barrido del excedente que quede, con partner.
4. Factoring / confirming como acción por defecto cuando hay tensión, hay facturas y el grupo no cubre, no «busca un préstamo».

**Después** — dueños del riel

Tomar el depósito del barrido y el libro de anticipos. El score ya es la política: a quién se le barre, a quién se le anticipa, a quién se le dice que no.

**Más tarde** — banco de circulante

La póliza y el crédito genérico salen de haber visto 24 meses de caja. Los agujeros que el grupo no cubre son la prueba de underwriting, no el TAM.

## Reglas

- El pitch de jurado abre con el colchón, el excedente medido y la divisa. No con 8 M€ de agujero. No recomendar barrido ni crédito si hay caja hermana.
- El pitch de compañía añade el AR de las tensas y el camino pasivo → activo.
- No rankear la demo de Productos por comisión de la SPA (mezcla yield del CFO con take de Embat, y FX con `n_tx > 50`).
- No originar líneas con una fórmula de gasto que explota en colas. Eso maximiza un Excel, no el impacto ni el derecho a ser el banco después.

## Qué está medido frente a lo que se asume

| Afirmación | Clase |
|---|---|
| 370 empresas, 344 M€ de excedente; 368 sin saving | Medida (empresa) |
| 360 empresas, 341 M€ de excedente neto de pooling | Medida (grupo) |
| 13 grupos con excedente y agujero; 3,33 M€ se moverían internamente | Medida |
| 7 de 41 agujeros cubiertos por la hermana; agujero neto 8,05 M€ | Medida |
| 261 empresas, 2.108 M€/año de FX; take 1,11 M€ @ 35 % | Medida la base; 15 pb y adopción, supuesto. FX no se netea |
| 320 tensas con 795 M€ de AR factorable; 314 sin producto | Medida la elegibilidad; que se ceda, supuesto |
| 22 de 26 agujeros factorables siguen abiertos; 129 M€ de AR | Medida |
| 1.260 M€ de caja hoy si se factoriza todo el AR elegible | Techo medido, no previsión |
| 5,11 M€/año netos al CFO a 1,5 % sobre 341 M€ | Hipótesis de colocación 2,5 % y 100 pb |
| Embat tomará depósitos o el libro de factoring | Hoja de ruta; no hecho |

Adopción 25 / 35 / 45 %, márgenes y disposición a ceder facturas siguen siendo hipótesis. No escalar 1.286 empresas sintéticas a «500 equipos Embat».
