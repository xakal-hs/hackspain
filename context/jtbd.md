# JTBD de las tres funcionalidades que salen del score

**Marco de producto · 19 de septiembre de 2026.** Colchón Dinámico, Divisa Inteligente y el
módulo SaaS son las tres funcionalidades que se sacan del scoring. Este documento dice qué
trabajo hace cada una para el CFO, dónde se contradicen hoy en la interfaz y cómo unirlas para
que se lean como un producto y no como tres.

No añade cifras nuevas. Las medidas siguen en [`monetizacion.md`](monetizacion.md), la
colocación de producto en [`oportunidades.md`](oportunidades.md) y la voz cualitativa en
[`voz_embat.md`](voz_embat.md).

## 1. El trabajo maestro

Las tres responden a la misma pregunta del CFO, con distinto sujeto:

> **Cuando miro la caja, quiero saber qué parte de este dinero es mía de verdad y qué me está
> costando no decidir, para no descubrir el problema cuando ya no tenga margen de maniobra.**

De ahí sale la única métrica que las une: **el coste de no hacer nada**, en euros y con fecha.
La PM de Embat lo dejó dicho —el dinero parado y la divisa no se viven como problema, son costes
ocultos ([`voz_embat.md`](voz_embat.md) §1 y §2)—. Si el producto no enseña ese coste, ni el
yield ni el FX se activan aunque el cálculo sea correcto.

Cada funcionalidad cobra ese coste en una moneda de dolor distinta:

| Funcionalidad | Coste de no hacer nada | Unidad |
|---|---|---|
| SaaS (score, alerta, explicación) | Enterarse tarde | **Meses** de antelación |
| Colchón Dinámico | Dinero parado, o quedarse corto | **€/mes** |
| Divisa Inteligente | Convertir en el momento equivocado | **€ por pago** |

## 2. Los tres trabajos, uno a uno

### 2.1 SaaS — el score, la alerta y el porqué

Es lo que se paga (350 €/mes, [`monetizacion.md`](monetizacion.md)). No es una pantalla más:
es el derecho a tener las otras dos.

- **Funcional** — «Cuando el consejo o el banco me preguntan cómo vamos, quiero un número
  defendible y su porqué, para no depender de mi intuición ni de un Excel de hace tres semanas.»
- **Emocional** — no ser el último en enterarme.
- **Social** — llegar al comité con una lectura que nadie discute.
- **Se contrata** en el cierre de mes, antes de un consejo, antes de negociar con el banco.
- **Se despide** a la primera falsa alarma. Por eso la precisión del silencio (98,4 %) no es una
  métrica de modelo: es la métrica de retención.
- **Progreso que compra** — de enterarme cuando ya está en la caja, a enterarme 2,3 meses antes.

### 2.2 Colchón Dinámico — cuánto no puedo tocar

- **Funcional** — «Cuando tengo 620 k€ en cuenta, quiero saber cuánto no puedo tocar en los
  próximos tres meses, para mover el resto sin arriesgarme a un descubierto.»
- **Emocional** — el saldo gordo tranquiliza; el miedo real es quedarse corto un martes. La
  ansiedad no es «no gano rendimiento», es «no sé cuánto es mío de verdad».
- **Social** — poder justificar por qué hay X parado, o por qué se movió.
- **Se despide** si le rompes la caja una sola vez.
- **No es un producto de rendimiento, es un producto de límite.** Trabaja en las dos
  direcciones: el estado «mal» del mock actual manda *devolver* 120 k€ del depósito antes del
  agujero. Esa simetría es el producto; el yield es la consecuencia.

### 2.3 Divisa Inteligente — cuándo, no cómo

- **Funcional** — «Cuando tengo un pago de 45 k USD el día 15, quiero saber si convierto hoy o
  espero, para no pagar 900 € de más por no haber mirado.»
- **Emocional** — el FX le parece complejo y de casino. No quiere convertirse en trader.
- **Social** — no tener que explicar una pérdida de cambio que «no es del negocio».
- **Se contrata** cuando hay un pago o cobro en moneda con fecha conocida en el ERP.
- **Se despide** si le dejas una posición huérfana, o si le pides que opere un riel que le asusta.
- **El trabajo no es ejecutar.** Embat ya vende pagos internacionales. Lo que falta es el
  *cuándo* y el coste de no convertir, visibles en la app y sin pasar por el agente —que,
  según la PM, es de las funcionalidades que no se usan.

## 3. El patrón común: cuatro primitivas

Los tres son la misma frase con distinto sujeto. Esto es lo que hace posible un único diseño:

| | Sujeto | Reloj | Umbral | Coste de no hacer nada | Acción |
|---|---|---|---|---|---|
| Score | la empresa | mes | banda 65 · Δ3m | meses de retraso | vigilar / avisar |
| Colchón | el saldo | mes, con h3 | colchón necesario | €/mes parados, o descubierto | colocar / devolver |
| Divisa | un pago con fecha | días hasta la fecha | Δ tipo ≥ 2 % + volatilidad | € por pago | cubrir / esperar / revertir |

**Exposición, umbral, reloj y coste.** Cuatro campos. Cualquier cosa que quepa en esa tabla
puede entrar en el producto sin inventar una pantalla nueva —incluido el traspaso intragrupo,
que según [`oportunidades.md`](oportunidades.md) es la primera acción de tesorería y hoy no
tiene sitio en la interfaz.

## 4. Dónde se rompe hoy la coherencia

Todo lo de abajo está en el repositorio, no es hipótesis.

1. **Tres pestañas hermanas.** `treasurySections = ['score', 'colchon', 'divisa']`
   (`frontend/app/pages/dashboard/[role].vue:63`) crea tres destinos independientes, cada uno con
   su página completa. El CFO tiene que ir a buscarlos. Contradice la tesis: si el coste es
   oculto, no puede vivir detrás de una pestaña que nadie abre.
2. **Dos sistemas visuales conviviendo.** La cabina usa `--mint/--amber/--crimson/--live/--ahead`,
   Schibsted Grotesk y radios `--r-panel: 18px`. Los tres mocks usan el bloque `.centinela`
   (`frontend/app/assets/css/tokens.css:204`): `--ok/--warn/--bad`, Space Grotesk + Work Sans,
   radios 8/10/12 y estilos inline. El puente para tema oscuro ya existe
   (`tokens.css:269`), pero es un puente: tipografía, escala y radios siguen divergiendo.
3. **Dos marcas.** Los mocks se llaman **Centinela** y tienen su propio rail, su topbar y su
   breadcrumb. El producto se llama X-Ray. Incluso con `chrome=false` sobrevive el «Agente
   Centinela» dentro del score.
4. **Tres escalas de estado para lo mismo.** BIEN/NORMAL/MAL con emoji en los mocks; bandas
   SANO/VIGILANCIA/RIESGO en el score; `DecisionTag` con Prestar/Vigilar/No prestar en el
   resumen.
5. **El verbo equivocado para el usuario equivocado.** El panel «La decisión» del resumen pinta
   `DecisionTag` sin condicionar el rol: un CFO mirando su propia empresa lee **«Prestar»**. Ese
   es el trabajo del prestamista, no el suyo.
6. **El simulador de demo, tres veces dentro del producto.** «Simular estado» se repite en los
   tres componentes; es andamio de demo viviendo dentro de la ficha.
7. **El SaaS no tiene superficie para el CFO.** Existe como línea de revenue
   (`frontend/app/data/internal.ts:84`, 238 k€/mes) y como pestaña interna. Para quien lo paga no
   hay ninguna pantalla que diga qué le ha dado.
8. **El coste de no hacer nada no está en el resumen.** Los paneles de portada son La decisión,
   La ventaja, Lo que podemos ver, Trayectoria, Frente al sector, Qué ha cambiado y El dinero de
   la cuenta. Ni euros ociosos ni exposición en divisa. La pieza que activa las otras dos es
   justo la que no se ve al entrar.
9. **`--ahead` está sin usar.** El token reservado a «lo que el producto sabe antes de que pase»
   (`tokens.css:4`) no aparece en ninguno de los tres mocks —y es exactamente la firma visual que
   los tres comparten: el marcador «avisamos aquí» del score, el runway h3 del colchón y el tipo
   previsto de la divisa son la misma idea.

## 5. Cómo juntarlo

**Tesis de diseño: no son tres productos, son una cola de decisiones sobre el mismo dinero,
generada por el mismo score.** El SaaS es el derecho a tener la cola; el colchón y la divisa son
dos generadores de entradas.

### A. Un solo objeto: la tarjeta de decisión

Un `<DecisionCard>` con seis huecos fijos, iguales en las tres familias:

1. **Familia** — caja / divisa / trayectoria. Icono, no color.
2. **Urgencia** — actuar ahora · vigilar · sin acción. Color, no icono.
3. **Titular en euros** — «Dejar 380 k€ parados te cuesta 1.240 €/mes».
4. **Porqué** — dos a cuatro drivers con su contribución. Los tres mocks ya traen `drivers`.
5. **Reloj** — «decide antes del 15 nov» o «vuelve a evaluarse el 12 dic».
6. **Acción, alternativa y no hacer nada** — mesa de opciones, nunca un SKU único
   ([`voz_embat.md`](voz_embat.md) §6).

Los tres mocks ya tienen banner + KPI + drivers + CTA + historial. Lo que falta no es inventar
el componente: es que sea **uno** y no tres HTML paralelos.

### B. Una portada, no tres pestañas

El resumen del CFO abre con la cola: «3 decisiones abiertas · 2 pueden esperar». El score deja de
ser pestaña hermana y pasa a ser **la cabecera** —nivel, trayectoria y ventaja en meses—, porque
es lo que explica por qué esas decisiones están ahí. Colchón y divisa pasan a ser **filtros y
detalle** de la misma cola.

Rail propuesto para la perspectiva empresa: **Resumen · Decisiones · Señales · Ofertas.** De
siete destinos a cuatro.

*Versión conservadora si no da tiempo antes del jurado:* mantener las tres pestañas, pero (a)
unificar tokens y tipografía, (b) sacar «Simular estado» al shell una sola vez, y (c) poner las
tres tarjetas en el resumen enlazando a su pestaña. Es el mínimo para que se lea como un producto.

### C. Una sola escala, y en el verbo del CFO

La escala no es bien/normal/mal: es **actuar ahora / vigilar / sin acción**, que es lo que el CFO
hace. Prestar/Vigilar/No prestar se queda en la perspectiva Embat, donde sí es el trabajo real.
Y «sin acción» se diseña como estado de primera clase, con su fecha de próxima revisión: el
silencio es la feature que sostiene el 98,4 %.

### D. Primero el euro, después el producto

Cada tarjeta lleva un número grande en euros y una fecha. Puntos básicos y porcentajes bajan a
letra pequeña: los pb son el negocio de Embat, no el problema del CFO. Regla de redacción:
**coste antes que SKU**, que es literalmente lo que pide [`oportunidades.md`](oportunidades.md).

### E. El color codifica urgencia; el icono, familia

Hoy el color hace dos trabajos: en los mocks es el estado, y en `internal.ts` es la familia de
producto. Separarlos. Y activar `--ahead` como la firma común de los tres: todo lo previsto
—forecast h3, runway h3, tipo esperado, marcador «avisamos aquí»— se pinta con él y con nada
más. Es lo que distingue a X-Ray de un panel de saldos.

### F. Una marca

Quitar «Centinela» del chrome. Si se conserva, que sea el nombre del agente —pero como el agente
no se usa, lo coherente es que las recomendaciones vivan en la ficha y el nombre desaparezca.

### G. Qué es el SaaS a nivel de diseño

No una pantalla más: **el marco**. Dos superficies concretas:

- **Para el CFO** — una franja permanente de «lo que X-Ray te ha dado»: meses de antelación y
  euros de coste evitado, acumulados. Es lo único que legitima los 350 €/mes en el momento de la
  renovación, y hoy esas cifras solo existen en la vista interna del modelo.
- **Para Embat** — `revenue` ya existe; falta el vínculo causa-efecto entre decisiones ejecutadas
  y revenue del mes.

Con una regla de honestidad que el repositorio ya exige: **el take de Embat no se enseña al CFO
en la misma tarjeta que su ahorro.**

### H. Orden de la cola

Por impacto para el CFO y por fecha límite. **Nunca por comisión** —[`oportunidades.md`](oportunidades.md)
lo fija como criterio—. Y el traspaso intragrupo, cuando existe, va por delante de colocar o de
pedir: 13 grupos tienen excedente y agujero a la vez, y ahí la primera llamada no es a un
producto.

## 6. Deuda concreta que habría que tocar

| Fichero | Qué cambia |
|---|---|
| `frontend/app/components/{XRayScoreApp,ColchonDinamicoApp,DivisaInteligenteApp}.vue` | ~1.200 líneas de estilos inline y fixtures. Extraer los estados a `app/data/decisions.ts` y el layout a `<DecisionView>` + `<DecisionCard>` |
| `frontend/app/assets/css/tokens.css` | El bloque `.centinela` deja de ser paleta paralela: alias de los tokens de la cabina también en tema claro, o se elimina cuando los componentes usen `--mint/--amber/--crimson` |
| `frontend/app/components/WorkspaceSidebar.vue` · `pages/dashboard/[role].vue` | `treasurySections` pasa de tres entradas a una (`decisiones`) con filtros por familia |
| `pages/dashboard/[role].vue` (resumen) | `DecisionTag` condicionado al rol; añadir coste ocioso y exposición FX a la portada |
| `frontend/app/data/internal.ts` | Vincular decisiones ejecutadas con las líneas de revenue |

## 7. Lo que no se toca

- El score sigue siendo el motor: las tres funcionalidades leen de él, ninguna lo sustituye.
- Las cifras de [`monetizacion.md`](monetizacion.md) no cambian por reorganizar la interfaz.
- La divisa no se netea contra el excedente: es flujo de moneda, no saldo.
- Nada de esto convierte los fixtures en datos conectados. En la demo se sigue diciendo
  «escenario de producto con datos ficticios».
