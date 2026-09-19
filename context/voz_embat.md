# Voz de producto · PM de Embat

**Fuente cualitativa · 19 de septiembre de 2026.** Notas de una conversación con una PM de
Embat. No sustituye el [enunciado](challenge.md) ni las cifras medidas de
[monetización](monetizacion.md). Condiciona cómo se enseña el coste, cómo se modula la
criticidad de la liquidez y cómo se ofrece deuda o upsell.

Clase: **testimonio**. No es medida. No se usa como cifra de pitch.

## Lo que dijo

### 1. El exceso de caja es un problema de conocimiento

Las empresas no tienen mucho conocimiento sobre el dinero parado. No lo toman como un
problema real. El coste de tener liquidez ociosa es **oculto**: hay que mostrarlo en la
propia aplicación para hacer conscientes de que existe. X-Ray no gana si calcula un yield
elegante y el CFO sigue viendo el saldo como colchón inofensivo.

### 2. La divisa parece compleja

El intercambio de divisas se vive igual: les parece muy complejo. Es otro coste oculto.
La operación es normalmente muy compleja, y **el agente es una de las funcionalidades que
no se acostumbra a utilizar**. No diseñar el FX alrededor de un agente que el cliente no
abre. El valor está en hacer visible el coste y el momento, no en automatizar un riel que
ya asusta.

### 3. Solvencia sin conciliación perfecta

No hace falta conciliación perfecta para saber un estado de solvencia. Eso es de
**planificación y de análisis de previsiones**, no de cuadrar al céntimo cada movimiento.
La cobertura de conciliación sigue siendo observabilidad, no salud. Un colchón y una
previsión bastan para decidir si hay sobrante, agujero o margen de maniobra.

### 4. Suscripción primero; intermediación como parche

Les gusta el modelo de suscripción. Como Embed One no cubre todo, a veces hacen de
intermediarios. **No es lo ideal.** El módulo se vende como SaaS; la intermediación
(depósito, factoring, FX, deuda) entra cuando el riel propio no llega, no como el relato
principal.

### 5. La criticidad de la liquidez depende del sector

La liquidez de las compañías a veces depende mucho del sector. Hay empresas que **viven
de la liquidez**: si se seca, muere la propia empresa. En otras, no tienen esa atención.
El mismo runway no significa lo mismo en un mayorista que cobra a 90 días y en un negocio
con cobros recurrentes. La criticidad no es solo entre señales (caja > DSO); también es
entre empresas.

### 6. El upsell es una mesa de opciones

Cuando se busca un upsell, se proponen **varias opciones dentro de la mesa** que le
pueden encajar. Eso es lo que buscan. No un SKU único empujado por comisión. Varias
piezas, cada una con un porqué, para que tesorería elija.

### 7. Deuda: entender la necesidad y combinar plazos

Con los datos que se tienen, lo que se puede hacer en productos de deuda es:

1. **Aportar un producto.**
2. **Entender muy bien lo que necesita la empresa** y aportar varios productos conforme
   al tiempo que van a tener que devolver.
3. **Decir una combinación de deuda a corto, medio y largo plazo.**

No basta con “línea recomendada de X €”. Hay que leer el hueco (cuánto, para qué, en
cuánto tiempo se cubre) y montar un mix de plazos, no un único instrumento.

## Qué cambia en X-Ray

| Premisa anterior | Premisa ahora | Dónde aplica |
|---|---|---|
| El excedente se “vende” como yield | El excedente se **enseña como coste oculto**; el yield es la acción, no el descubrimiento | App, [oportunidades](oportunidades.md) |
| FX se ejecuta o se cubre | FX se **visibiliza** primero; el riel asusta y el agente no se usa | App, FX en la mesa |
| Conciliación alta = mejor salud | Conciliación es cobertura; la solvencia sale de **previsión y colchón** | [scoring](scoring.md) |
| Intermediar rieles es el camino | La suscripción es el modelo; intermediar es el parche de Embed One | [monetización](monetizacion.md) |
| Criticidad uniforme de la caja entre empresas | La criticidad de la liquidez **cambia con el sector** | Score y umbrales |
| Un producto por empresa (el de más take) | **Mesa de opciones** que encajan; tesorería elige | Demo Productos, upsell |
| Una línea de crédito genérica | Mix de deuda **corto / medio / largo** según el tiempo de devolución | Productos de deuda |

## Qué no cambia

- El comprador sigue siendo Embat; el usuario, el CFO.
- Las cifras de 344 M€ de excedente y 4,2 M€ de escenario no salen de esta conversación.
- Seguir sin rankear la demo por comisión de la SPA.
- Observabilidad (ERP, conciliación, mes truncado) no se imputa como salud.
- Hoy no somos banco; un partner puede ejecutar. Eso no convierte la intermediación en
  el producto que se vende.

## Cómo usarlo al construir

- En la ficha, mostrar el **coste de no hacer nada** con el dinero parado y con la
  divisa sin convertir, en euros y en frase llana, antes del SKU.
- No depender del agente para FX ni para el upsell.
- No esperar a conciliar para emitir colchón, exceso o agujero.
- Modular la criticidad de liquidez por régimen (sector inferido o huella operativa),
  no solo por un umbral global de runway.
- En Productos, una mesa de 2–4 opciones con el porqué; en deuda, plazos distintos
  según cuándo tiene que volver el dinero.
- Precio del módulo: suscripción. Intermediación: solo cuando Embed One no cubre el
  riel, y decirlo como tal.
