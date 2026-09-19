# Los pesos del X-Ray Score, explicados sin jerga

> Documento divulgativo. Explica **de dónde sale cada peso** del score y **qué significa cada
> variable** en lenguaje de calle. El detalle técnico y la evidencia medida viven en
> [`analysis/back_engineering_variables.py`](../analysis/back_engineering_variables.py) y su
> artefacto [`analysis/back_engineering_variables.html`](../analysis/back_engineering_variables.html).
> Las fuentes de evidencia son [`research/reports/eventos_v2.md`](../research/reports/eventos_v2.md),
> [`research/reports/eda.md`](../research/reports/eda.md) y
> [`context/voz_embat.md`](../context/voz_embat.md).

---

## 0 · La idea de partida (60 segundos de finanzas)

Imagina que **tienes 100.000 € y se los vas a prestar a una empresa**. Antes de firmar, cualquier
prestamista —aunque no sepa contabilidad— se hace cuatro preguntas:

1. **¿Tiene dinero?** (la cuenta, la caja)
2. **¿Lo gana o lo pierde cada mes?** (entra más de lo que sale)
3. **¿Le deben a él?** (clientes que no pagan)
4. **¿Debe él?** (cuotas, nóminas, impuestos, proveedores)

Todo el sistema es eso, con dos añadidos:

- **¿Mejora o empeora?** → interesa la *película*, no la *foto*.
- **¿Este mal mes es un bache o el principio del final?** → porque el 72 % de las empresas tiene
  meses malos y se recupera.

### Vocabulario mínimo

| Palabra | Qué es en la calle |
|---|---|
| **Caja** | El dinero que hay en la cuenta ahora |
| **Quema** (*burn*) | Lo que se gasta al mes |
| **Runway** | Cuántos meses aguanta con la caja que tiene (caja ÷ quema) |
| **Cobros** (AR) | El dinero que entra de los clientes |
| **Pagos** (AP) | El dinero que sale a proveedores |
| **DSO** | Cuántos días tarda en cobrar |
| **DPO** | Cuántos días tarda en pagar |
| **Póliza** | Un crédito ya concedido que puede usar cuando quiera (como el margen de tu tarjeta) |
| **Nómina** | El sueldo de sus empleados |
| **Apagado** (*churn*) | La empresa deja de operar: cierra la persiana |
| **Bache** | Un mes malo que se recupera |
| **Vencido** | Algo que había que pagar o cobrar y ya pasó la fecha |

---

## 1 · De dónde sale un peso

Un peso responde a: **¿cuánto me fío de esta señal para decidir si presto?** Se decide en cuatro pasos.

### Paso 1 · Criticidad base — «¿es de vida o muerte?»

Es un juicio puesto a mano, mirando qué pasa en la empresa si esa señal va mal:

| Nivel | Valor | Significado |
|---|---|---|
| **P0 · núcleo** | 1,00 | Si esto va mal, la empresa está en peligro real |
| **P1 · alto** | 0,72 | Importante, pero no decide solo |
| **P2 · medio** | 0,45 | Contexto que ayuda a explicar |
| **P3 · bache/contexto** | 0,25 | Ruido frecuente; no debe mover el score |
| **COV · cobertura** | 0,05 | No es salud, es si podemos ver los datos |

Traducción: **un P0 vale como cuatro P3**. Aquí vive la regla del challenge: *la caja que se evapora
pesa más que un DSO que empeora tres días*.

### Paso 2 · Evidencia — «¿esto se cumple de verdad en los datos?» (el AUC)

El **AUC** mide si un indicador distingue a quien acabó mal de quien acabó bien. Forma novata de leerlo:

> Coge 100 parejas, cada una con una empresa que **terminó en tensión de caja** y otra que **no**.
> El AUC es el porcentaje de esas parejas en las que el indicador le dio el valor más «malo» a la
> que realmente cayó.
>
> **0,50** = moneda al aire (no sirve) · **0,62** = útil · **0,74** = muy bueno · **1,00** = oráculo

En el código, la evidencia se convierte en *fuerza* con `fuerza = desviación ÷ 0,26`:

- `runway` tiene AUC 0,68 → desviación 0,18 → fuerza 0,69
- `lost_accel` tiene AUC 0,74 → desviación 0,24 → fuerza 0,92
- 0,26 es la desviación de «señal tope» en este dataset (≈ AUC 0,76)

**Detalle fino e importante.** No toda la evidencia vale lo mismo. El AUC de `runway` frente a E1 es
0,68 en la población entera pero **cae a ~0,50 dentro del grupo en riesgo**. ¿Por qué? Porque *solo
puede entrar en tensión quien hoy está sano*: medir «cuánta caja tiene» sobre todo el mundo es
selección inversa. Donde de verdad hay que acertar —entre empresas que hoy están bien— el nivel de
caja no dice nada; la **aceleración** de pérdida de clientes (0,65) y la **nómina irregular** (0,59) sí.

### Paso 3 · Cobertura — «¿a cuántas empresas se lo puedo aplicar?»

Si una señal solo existe en el 25 % de las empresas, no puede ser el motor del score aunque sea
buenísima. Pero tampoco se tira:

```
factor_cobertura = 0,5 + 0,5 × √(empresas con el dato ÷ 1.286)
```

La raíz cuadrada es a propósito: la cobertura **compensa, no domina**. Con cobertura 0 el factor es
0,50 (nunca anula); con cobertura 100 % es 1,00.

### Paso 4 · Persistencia — «¿es un rasgo o un pico de un mes?»

La persistencia *lag-1* mide si el valor de un mes se parece al del mes anterior:

- **Alta** (p. ej. `payroll_burden` 0,95) = es un rasgo estructural de la empresa.
- **Baja** (p. ej. `net_margin_6m` 0,51) = rebota mes a mes; puede ser ruido.

Entra como **factor suave**, sin llegar a mandar:

```
factor_persistencia = 1 + 0,5 × (persistencia − 0,789)     # 0,789 = media del conjunto
```

Centrado en la media, así no infla a todos: el rango resultante es ≈ **0,86 – 1,09** (±10 %). Las
variables sin persistencia medida quedan neutras (1,00): no se penaliza no tener el dato.

De las 46 variables del catálogo, **12 tienen persistencia medida** y 34 quedan neutras:

| Con persistencia | Valor | Sin persistencia (queda neutra) |
|---|---|---|
| `payroll_burden` | 0,95 | `cash_end`, `cash_trend_3m`, `lost_accel`, `payroll_cv`… |
| `debt_service_burden` | 0,93 | |
| `net_vol_6m` | 0,93 | |
| `runway` | 0,87 | |
| `oper_share` | 0,85 | |
| `ap_overdue_ratio` | 0,83 | |
| `refund_rate` | 0,82 | |
| `ar_overdue_90_ratio` | 0,82 | |
| `cash_negative` | 0,77 | |
| `ar_late_share` | 0,67 | |
| `ap_late_share` | 0,65 | |
| `net_margin_6m` | 0,51 | |

**Efecto real: pequeño y en la dirección correcta.** Mueve como mucho ±0,2 puntos porcentuales de peso.
Sube lo estructural (`oper_share` 4,7 → 4,9 %; `runway` 4,7 → 4,8 %) y baja lo ruidoso
(`net_margin_6m` 1,7 → 1,5 %; `ap_late_share` 1,6 → 1,5 %). Es justo el criterio de la pregunta 4 del
challenge: premiar el rasgo, no el pico.

> **Nota de honestidad.** El EDA midió la persistencia sobre nombres ligeramente distintos
> (`activity_log`, `top_client_share`, `net_margin_3m`). Solo se hereda cuando es el mismo concepto; no
> se mapea `activity_log` → `activity_trend` (nivel y tendencia son cosas distintas) ni
> `top_client_share` → `hhi_ar_6m` (máximo y HHI tampoco).

### La fórmula y el reparto

```
prioridad = 100 × criticidad × (0,55 + 0,45 × fuerza) × factor_cobertura × factor_persistencia
```

El término `(0,55 + 0,45 × fuerza)` significa: **aunque no haya evidencia medida, la variable conserva
el 55 % de su valor**. Es deliberado — un indicador que cualquier manual de crédito considera clave no
debe desaparecer solo porque en este dataset sintético no se pudo medir el evento. Por eso el HTML
distingue `medida` (hay AUC) de `marco` (juicio experto).

Y después, el peso final:

```
peso_de_la_variable = peso_del_pilar × (su prioridad ÷ suma de prioridades del pilar)
```

### Ejemplo hecho a mano: el pilar AR

El pilar de cobros vale 20,2 % del score y tiene ocho variables. Se reparte en proporción a la
prioridad de cada una:

| Variable | Prioridad | Peso resultante |
|---|---|---|
| `lost_accel` | 85 | **4,6 %** |
| `lost_share` | 59 | 3,1 % |
| `cust_trend` | 47 | 2,5 % |
| `ar_overdue_90_ratio` | 44 | 2,3 % |
| `overdue_ar` | 43 | 2,3 % |
| `hhi_ar_6m` | 39 | 2,1 % |
| `billing_to_cash` | 34 | 1,8 % |
| `ar_late_share` | 28 | 1,5 % |
| | | **Σ = 20,2 %** |

Fíjate en lo que esto significa: **`lost_accel` pesa casi el triple que el DSO** (`ar_late_share`), y
ambas viven en el mismo bloque. No es arbitrario: una anticipa el apagado con AUC 0,74; la otra apenas
mueve el ranking.

> Los pesos de esta tabla son la salida exacta del generador. Si tocas prioridades, evidencia o
> persistencia, vuelve a ejecutar el script y actualiza las cifras.

---

## 2 · Los nueve bloques

**Dirección:** `↑ sano` = cuanto más alto, mejor. `↓ sano` = cuanto más bajo, mejor (es un problema).

### LIQ · Liquidez y autonomía de caja — 24,2 %

**Por qué pesa tanto.** Es la criticidad que manda, porque la caja es lo único que se evapora de un
día para otro. Pero ojo al matiz que cambió el diseño: dentro del grupo en riesgo, **el nivel de caja
de hoy apenas predice nada**; lo que predice es **el cambio**. Por eso el pilar se reparte casi a
partes iguales entre «cuánto tiene» y «cómo va la tendencia».

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `cash_end` | El dinero que le queda en la cuenta (corriente, ahorro, monedero) | ↑ | P0 | **4,7 %** |
| `runway` | Meses que aguanta con ese dinero | ↑ | P0 | **4,8 %** |
| `cash_trend_3m` | Si la cuenta se está vaciando (cuánto cambió en 3 meses) | ↑ | P0 | **4,6 %** |
| `burn_rate` | Lo que gasta al mes. Sin esto, el saldo no dice nada | ↓ | P0 | 4,3 % |
| `cash_negative` | La cuenta está en números rojos | ↓ | P0 | 3,7 % |
| `liquidity_available` | El crédito que **aún no ha usado** de su póliza (colchón) | ↑ | P1 | 2,1 % |

**Nota de oficio.** `cash_end` no se lee del fichero tal cual: la foto de balances es solo del final,
así que hay que **reconstruirla hacia atrás** desde los movimientos y **redondear a céntimos** para que
el signo no oscile.

### AR · Cobros y ciclo de cliente — 20,2 %

**Por qué pesa tanto.** Aquí viven los dos eventos que más se pueden anticipar: la caída limpia de
cobros y el apagado. Y aquí está la mejor señal temprana de todo el sistema, que es la dinámica de
clientes — no el DSO, que es la obsesión clásica y sin embargo casi no discrimina.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `lost_accel` | **Si la pérdida de clientes se está acelerando** | ↓ | P0 | **4,6 %** |
| `lost_share` | Qué parte de su facturación es de clientes que ya no le compran | ↓ | P1 | 3,1 % |
| `cust_trend` | Si factura a más o menos clientes que antes | ↑ | P1 | 2,5 % |
| `ar_overdue_90_ratio` | Lo que le deben y lleva **más de 90 días**: eso ya casi no se cobra | ↓ | P1 | 2,3 % |
| `overdue_ar` | Facturas de clientes vencidas y sin pagar | ↓ | P1 | 2,3 % |
| `hhi_ar_6m` | Si depende de pocos clientes | ↓ | P1 | 2,1 % |
| `billing_to_cash` | Qué parte de lo que entra está respaldada por facturas emitidas | ↑ | P2 | 1,8 % |
| `ar_late_share` | Cuánto tarda en cobrar (DSO) | ↓ | P2 | 1,5 % |

**Dos intuiciones.**

- `lost_share` responde a «¿cuánto me duele?» y `lost_accel` a «¿me está doliendo más cada vez?».
  La segunda es mucho más útil para avisar a tiempo.
- `ar_late_share` (DSO) tiene el peso más bajo del bloque aunque sea lo primero que mira un banco:
  unos días más o menos de cobro no cambian la decisión de prestar.
- Ojo con `lost_accel`: **más = peor**. Es una aceleración de pérdida, así que un valor *positivo*
  significa que la hemorragia crece y uno *negativo* que se está recuperando.

### DEBT · Endeudamiento y obligaciones recurrentes — 18,2 %

**Por qué pesa tanto.** Aquí vive el impago. Y el impago no es un «poco peor»: es un **veto**, una
regla que impide prestar aunque el score esté bien. Además los hallazgos obligaron a trocear el
concepto: deber la nómina no es lo mismo que deber al proveedor.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `impago_nomina/ss/iva/cuota` | Deja de pagar algo que pagaba **siempre** | ↓ | P0 | **3,2 %** |
| `payroll_cv` | **Si la nómina es irregular** (a veces sí, a veces no, o bailan los importes) | ↓ | P0 | **3,0 %** |
| `payroll_continuity_6m` | Si paga la nómina todos los meses sin fallar | ↑ | P1 | 2,0 % |
| `lc_util` | Cuánto tiene dispuesto de su póliza | ↓ | P1 | 1,7 % |
| `debt_service_burden` | Qué parte de lo que ingresa se va en pagar cuotas de deuda | ↓ | P1 | 1,7 % |
| `new_debt_vs_cash` | Pide crédito nuevo **mientras la caja cae** | ↓ | P1 | 1,5 % |
| `debt_utilization` | Cuánto de su deuda total está viva | ↓ | P1 | 1,4 % |
| `schedule_pressure` | Cuánto le vence próximamente (calendario contractual) | ↓ | P1 | 1,2 % |
| `tax_miss` | Si deja de pagar impuestos en los trimestres que toca | ↓ | P2 | 1,2 % |
| `factoring_confirming` | Cuánto adelanta facturas con el banco | ↓ | P2 | 0,7 % |
| `interest_rate` | El interés que le cobran | ↓ | P2 | 0,6 % |

**Detalles que valen oro.**

- **Por qué el impago es P0 y además veto.** El 38,6 % de las nóminas «desaparecidas» reaparecen al mes
  siguiente. Es decir, *una ausencia sola es ruido*. Por eso se exige **regularidad** (dos meses
  seguidos) antes de declarar impago. Si te lo saltas, gritas en falso una de cada tres veces.
- **Por qué `lc_util` es contraintuitiva.** Disponer de la póliza da dinero, así que a corto plazo
  *protege* de quedarse seco (AUC 0,30 frente a E1: va al revés de lo esperado). Pero significa que
  **está quemando su colchón**: si el dispuesto está pegado al concedido, está ahogado. Se lee junto a
  la caja, nunca sola.
- **`schedule_pressure` solo existe para 40 empresas.** Coincidencia baja, pero cuando existe es
  **decisiva**: es el único sitio donde sabes exactamente cuándo tiene que llegar el dinero.

### CF · Generación de caja y actividad — 14,1 %

**Por qué este peso y no más.** Parece el corazón del negocio, pero la evidencia manda otra cosa: la
actividad sí anticipa (el negocio se apaga antes de caer), pero **el margen neto revierte a la media**;
darle mucho peso mete ruido.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `oper_share` | Qué parte de lo que entra es cobro real (y no préstamos ni traspasos) | ↑ | P0 | **4,9 %** |
| `activity_trend` | Si mueve menos dinero que antes (3 meses vs 12 meses) | ↑ | P1 | 3,6 % |
| `oper_persistence_6m` | Si su operación sigue activa la mayoría de los meses | ↑ | P2 | 2,1 % |
| `growth_vs_12m` | Si factura más que su media anual | ↑ | P2 | 2,0 % |
| `net_margin_6m` | Si cobra más de lo que gasta (el «ahorro» del mes) | ↑ | P2 | 1,5 % |

**Intuición clave.** `activity_trend` es de los mejores chivatos porque **una empresa se apaga antes de
caer**: deja de moverse, de pagar, de cobrar… y solo después se hunde. Su persistencia mes a mes es
altísima (0,97): si se mueve menos, es un rasgo, no un accidente.

**`net_margin_6m` con 1,7 % es un mensaje deliberado.** AUC ≈ 0,50 (no distingue) y persistencia 0,51
(rebota). Es la candidata número uno a bajar aún más de peso: *explica*, pero no *discrimina*.

### AP · Pagos y disciplina con proveedores — 9,6 %

**Por qué menos peso del que la intuición sugiere.** El vencido a proveedores es el mejor
discriminador crudo del impago (AUC 0,72), pero **está contaminado**: el evento de impago incluye como
componente «deber más de 90 días a proveedores», así que parte de su acierto es mecánico — se está
midiendo a sí mismo. Un buen analista descuenta eso.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `payee_concentration` | Si concentra sus pagos en pocos proveedores | ↓ | P1 | 3,2 % |
| `ap_overdue_ratio` | Lo que debe a proveedores y ya venció | ↓ | P1 | 2,8 % |
| `payroll_burden` | Cuánto de lo que ingresa se va en nóminas (coste fijo rígido) | ↓ | P1 | 2,1 % |
| `ap_late_share` | Cuánto tarda en pagar (DPO) | ↓ | P2 | 1,5 % |

**Matiz importante sobre pagar tarde.** Pagar tarde no es siempre malo. Puede ser **tensión** (no tengo
dinero) o **abuso de posición** (tengo dinero y me aprovecho porque soy el cliente grande). Se lee
siempre junto a la caja, nunca solo.

### STAB · Estabilidad: bache o caída — 10,1 %

**Por qué existe como bloque propio.** Por un dato brutal: **por cada caída que no se recupera hay 1,66
baches**, y el 72 % de las empresas tiene baches. Si el score trata cada mal mes como deterioro
estructural, el monitor de alertas se convierte en una alarma que suena todo el día y nadie mira. Este
bloque es la pregunta 4 del challenge y hoy es el más flojo: es donde está la mayor mejora pendiente.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `multi_signal_stress` | Cuántas señales se encienden **a la vez** (cobros, actividad, clientes, caja) | ↓ | P1 | 2,7 % |
| `net_vol_6m` | Cuánto se le hunde la caja en los meses malos | ↓ | P1 | 2,7 % |
| `vol_asymmetry` | Si su volatilidad es de ciclo (sube y baja) o solo de caída | ↑ | P2 | 1,7 % |
| `shock_vs_usual` | Si el golpe fue grande **comparado con sus meses malos habituales** | ↓ | P2 | 1,6 % |
| `credit_notes` | Notas de crédito emitidas (pueden anular facturas ya emitidas) | ↓ | P3 | 0,7 % |
| `refund_rate` | Reembolsos y devoluciones | ↓ | P3 | 0,7 % |

**La analogía médica.** Un solo síntoma (fiebre) puede ser cualquier cosa; cuatro síntomas a la vez ya
es un cuadro. `multi_signal_stress` es exactamente eso: cuenta de 0 a 4 cuántas familias de señales
están encendidas. 0 señales → 13,3 % de probabilidad de caída; 3-4 señales → ~35 %.

**`refund_rate` con 0,7 %.** El 88 % de las filas son cero y su AUC es ≈ 0,50. Es un pico puntual, no un
deterioro. Candidata directa a desaparecer.

### SOLV · Solvencia y capacidad de cobertura — 3,5 %

**Por qué es un bloque residual.** En este dataset el margen y la cobertura de intereses **apenas
separan eventos** (AUC ≈ 0,50). Se mantienen porque son el lenguaje clásico del crédito y sirven para
el corte de decisión y la explicación, pero **no como motor del score**. Es una decisión deliberada:
mejor un sistema honesto con la evidencia que uno que reparta peso por costumbre.

| Variable | Qué significa en la calle | Dir. | Nivel | Peso |
|---|---|---|---|---|
| `self_funding` | Si crece sin pedir más crédito | ↑ | P2 | 1,9 % |
| `interest_coverage` | Cuántas veces cubre sus cuotas con lo que cobra | ↑ | P2 | 1,6 % |

### GRP · Grupo y contagio — **no puntúa** (modificador)

**Por qué no puntúa.** Porque el 32 % de las «tensiones de caja» son **artefactos**: una filial que vive
con la caja justa porque su matriz la financia parece «en tensión» sin estar en riesgo. Al excluir el
flujo intragrupo, de 75 arranques quedan 51. Meter esto como puntos sería castigar a media plantilla
por cómo su grupo lleva la tesorería.

| Variable | Qué significa en la calle |
|---|---|
| `intragroup_dependency` | Si vive de que le transfiera su grupo. **Filtro obligatorio antes de puntuar** |
| `runway_vs_group` | Si va peor que sus empresas hermanas |
| `operating_regime` | Qué tipo de negocio es: cobro recurrente vs mayorista a 90 días |
| `group_stress` | Si el grupo entero está tenso (diagnóstico aparte del score) |

**El hallazgo de la PM de Embat va aquí, y es de sentido común poderoso.** El **mismo runway no
significa lo mismo en todo negocio**: un mayorista que cobra a 90 días y un negocio de suscripción con
cobro mensual no deben compartir el mismo umbral. Se infiere el **régimen** (huella operativa: DSO,
recurrencia de cobros, estacionalidad, número de clientes) y se ajusta el corte. No es señal de salud:
es el contexto que fija el listón.

### OBS · Observabilidad — **0 % del score, pero ajusta la confianza**

**Por qué es la distinción más importante de todo el sistema.** Hay 501 empresas sin facturas y un
25 % de movimientos sin categoría. Eso **no es una empresa enferma, es una empresa opaca**. Confundir
las dos cosas es el error más caro posible, porque castigarías por no compartir datos en lugar de por
estar en riesgo.

| Variable | Qué significa en la calle |
|---|---|
| `erp_connected` | Si deja ver sus facturas |
| `uncat_share` | Cuánto movimiento no está etiquetado |
| `reconciliation` | Si lleva la contabilidad al día (es proceso, no solvencia) |
| `history_length` | Cuánto tiempo lleva en la plataforma |
| `currency_exposure` | Cuánto mueve en otra divisa (no se suma sin convertir) |
| `internal_flow` | Traspasos entre sus propias cuentas (hay que quitarlos antes de medir) |

---

## 3 · Lo que está por encima del score: los vetos

Un veto no suma ni resta puntos: **decide**. Es la diferencia entre un sistema de *ranking* y un sistema
*accionable*. Da igual que el score sea 82: si no ha pagado la nómina, no se presta hasta ver la
siguiente.

| Disparador | Efecto |
|---|---|
| **Nómina ausente** | No prestar hasta ver la siguiente nómina regular |
| **Seguridad Social ausente** | Deja de pagar algo que pagaba siempre |
| **IVA ausente** | Dos trimestres fiscales seguidos sin pagar |
| **Cuota de deuda ausente** | Deja de pagar una cuota habitual |
| **Póliza agotada con caja corta** | No ampliar: ya vive al límite del disponible |
| **Grupo en estrés** | Modula la decisión, no el score individual |
| **Caja negativa** | **No** es veto automático: depende de persistencia y de si el grupo cubre el desfase |

---

## 4 · La lógica de pesos en una frase por bloque

| Pilar | Peso | La frase |
|---|---|---|
| **LIQ** | 24,2 % | La caja manda, pero **su cambio manda más que su nivel** |
| **AR** | 20,2 % | El DSO es el famoso; **la pérdida de clientes es el que acierta** |
| **DEBT** | 18,2 % | El impago no puntúa: **veta**. Y la nómina irregular lo anuncia |
| **CF** | 14,1 % | El negocio se apaga antes de caer; el margen solo explica |
| **AP** | 9,6 % | Buen predictor, pero contaminado: se descuenta |
| **STAB** | 10,1 % | 1,66 baches por caída: separar ruido de deterioro es un pilar |
| **SOLV** | 3,5 % | Honestidad con la evidencia: aquí casi nada discrimina |
| **GRP** | overlay | Un tercio de las «tensiones» son cómo el grupo mueve su tesorería |
| **OBS** | 0 % | No poder ver ≠ estar enfermo |

---

## 5 · Cómo reproducirlo

```bash
uv run --python 3.12 --with duckdb --no-project python analysis/back_engineering_variables.py
```

Genera [`analysis/back_engineering_variables.html`](../analysis/back_engineering_variables.html). Los
CSV de `data/` no se reescriben: la cobertura se calcula al vuelo con DuckDB.

### Avisos sobre estas cifras

- Los pesos son un **reparto de arranque**, no un peso calibrado. Los finales salen de la logística con
  signo restringido.
- Las prioridades sin AUC propio usan criticidad de marco (marcadas como `marco` en el HTML): el marco
  manda aunque no haya evento medible.
- Varias evidencias tienen intervalos amplios (E1 con 75 casos, calendario con 40 empresas, factoring).
- Si al generar el HTML no hay DuckDB disponible, las coberturas salen a 0 y **todos los pesos se
  aplastan**. Comprueba que la sección de coberturas tiene números antes de fiarte de un peso.
- **Un mismo concepto, dos nombres.** La deuda se llama `debt_service_burden` en el análisis
  (`feature_criticality.py` y este documento) y `debt_burden` en el score
  ([`research/src/features.py`](../research/src/features.py)). Es la misma variable.
- **Las cifras de este documento son la salida del generador en la fecha del commit.** Si cambias
  prioridades, evidencia, cobertura o persistencia, vuelve a ejecutar el script y actualízalas.
