# Monetización — verdad comercial corregida

**Marco para el jurado · 19 de septiembre de 2026.** Este documento sustituye el brief que
sumaba importes en moneda nativa como si todos fueran euros. El cálculo reproducible está en
`analysis/monetizacion.py` y el detalle visual en `analysis/monetizacion.html`.

## Producto en una frase

> **X-Ray convierte el rastro de tesorería de Embat en una prioridad explicable y una siguiente
> acción para el CFO: detecta antes, explica qué cambió, calcula el colchón que necesita y señala
> qué hacer con el exceso o el déficit.**

El comprador es **Embat**, que incorpora el módulo a su plataforma. El usuario y beneficiario es el
**CFO** de la empresa conectada. Un banco, bróker o proveedor BaaS puede ejecutar determinadas
acciones, pero no es el protagonista del pitch.

## La cifra defendible

| Escenario | Adopción supuesta | Ingreso anual sobre el dataset |
|---|---:|---:|
| Conservador | 25 % | **3,0 M€** |
| Central | 35 % | **4,2 M€** |
| Agresivo | 45 % | **5,4 M€** |

En el escenario central, el reparto es:

| Línea | Ingreso anual imputado |
|---|---:|
| Módulo, a 350 €/mes | **1,89 M€** |
| Colocación de excedente, a 100 pb | **1,20 M€** |
| Divisa, a 15 pb | **1,11 M€** |
| **Total** | **4,20 M€** |

El cálculo anterior de **12,1 M€/año** queda únicamente como antecedente descartado. Mezclaba
divisas sin convertir y dejaba pasar saldos centinela del generador. No debe usarse en el pitch,
en una slide de resultados ni como previsión comercial.

## Qué está medido

Estas cifras se reproducen sobre los CSV del reto sin reescribirlos, aplicando la capa de mapeo,
conversión a EUR y la caja reconstruida:

La base principal es **344 M€ de excedente en 370 empresas**.

| Base medida | Resultado |
|---|---:|
| Empresas con excedente sobre dos meses de gasto | **370** |
| Excedente agregado | **344 M€** |
| Excedente mediano | **108.720 €** |
| Empresas con caja negativa al corte | **41** |
| Agujero agregado al corte | **11,38 M€** |
| Exposición anual a divisa, convertida a EUR | **2.108 M€** |
| Peso de esa exposición sobre el flujo limpio | **1,6 %** |

La evidencia permite decir que existen dos colas accionables —exceso y déficit— y que el crédito
no debe liderar el bloque de valor. No permite afirmar cuánto venderá Embat.

## Qué sigue siendo una hipótesis

- Adopción del 25 %, 35 % o 45 %.
- Precio de 350 €/empresa/mes.
- Margen de 100 pb sobre excedente y 15 pb sobre divisa.
- Disposición a pagar, tasa de activación, churn y coste de servir el módulo.
- Acceso regulatorio y reparto económico con bancos, brókeres o proveedores BaaS.
- Que las 1.286 empresas sintéticas representen la cartera comercial de Embat.

La web pública de Embat habla de **más de 500 equipos financieros**, no de 400 clientes. Tampoco es
correcto sustituir 1.286 empresas sintéticas por 500 equipos y escalar el ingreso linealmente: no son
unidades comparables y no conocemos su distribución de saldos y flujos.

Fuente externa: [plataforma de gestión de tesorería de Embat](https://www.embat.io/es/gestion-tesoreria).

## Por qué X-Ray es incremental

Embat ya ofrece visibilidad de caja, previsiones, detección de déficits y excedentes, alertas,
riesgo de contraparte y pagos internacionales. Por eso X-Ray no se vende como otro forecast.

La cuña incremental es:

1. **Comparar:** una medida común de nivel y trayectoria para ordenar una cartera completa.
2. **Explicar:** qué señales movieron la nota y cuántos puntos aportó cada una.
3. **Priorizar:** qué empresa requiere atención ahora y con qué confianza.
4. **Decidir:** colchón dinámico y siguiente acción según exceso, déficit o deterioro.
5. **Aprender:** registrar qué recomendación se aceptó y qué resultado produjo.

Fuentes externas: [gestión de tesorería](https://www.embat.io/es/gestion-tesoreria),
[módulos y pricing](https://www.embat.io/pricing) y
[pagos internacionales](https://www.embat.io/es/pagos-corporativos/pagos-internacionales).

## El recorrido que se enseña

**Detectar antes → explicar qué cambió → calcular colchón dinámico → recomendar una acción →
cuantificar el resultado.**

- Si el colchón es positivo, el CFO conserva la caja necesaria y evalúa poner a trabajar el resto.
- Si es negativo, recibe fecha, importe y motivos para negociar financiación antes del agujero.
- Si la señal es incierta, se vigila; no se presenta una recomendación automática como certeza.

El frontend Nuxt actual es una narrativa con fixtures ficticios. Solo `/api/companies` dispone de un
adaptador opcional al backend; las fichas, señales y ofertas no son todavía un flujo integrado. En
la demo se debe decir **“escenario de producto con datos ficticios”**, no “producto conectado”.

## Regla para cualquier cifra

| Tipo | Cómo presentarlo |
|---|---|
| Medido en el dataset | “Hemos medido…” y ruta reproducible |
| Validación del modelo | Métrica, versión, split y referencia |
| Supuesto comercial | “Si asumimos…”; nunca como resultado observado |
| Fuente externa | Enlace, fecha de consulta y sin extrapolar unidades no comparables |

La cifra comercial puede apoyar el pitch, pero no es el pitch. El cierre debe ser el producto:
Embat ya tiene los datos; X-Ray los convierte en una cola de decisiones explicables para cada CFO.
