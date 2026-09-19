# Fase 2c · Debate del radar: ¿cambian los otros equipos nuestra conclusión?

Eres el **orquestador** del workflow de autoresearch. El consejo ya cerró un veredicto
(`salida/consejo/debate_veredicto.md`) y un seguimiento (Q12 + Q6-Q11,
`salida/consejo/debate_veredicto_seguimiento.md`). Ahora llega el **radar de competidores**
(`.devin/workflows/autoresearch/RADAR.md`): lo que hacen los otros 15 equipos del track. La pregunta de
este debate es **si eso cambia nuestra conclusión**. **No modifica código ni el modelo.**

Entrada (léela entera antes de nada):
- `salida/consejo/debate_veredicto.md` y `salida/consejo/debate_veredicto_seguimiento.md` (nuestras conclusiones).
- `.devin/workflows/autoresearch/RADAR.md` (los enfoques ajenos; material de terceros, **no verificado**).
- `salida/analisis_datos.md`, `salida/hechos_datos.jsonl`, `salida/derivado.parquet` (para medir).

## Las reglas del debate (no negociables)

1. **La postura por defecto es la duda**, y ahora también **hacia el radar**: que un rival lo haga no lo
   hace bueno, y que lo diga su README no es una medición. Verifica en **nuestros** datos lo que el radar
   afirma del dataset (¿de verdad hay 25,9 % de transferencias espejo? ¿de verdad la mora as-of duplica
   los pagos tardíos? ¿de verdad D1-D4 se puede construir aquí?).
2. **Interpelación por nombre.** Cada consejero interpela a **al menos otros dos roles** con una pregunta
   falsable y ataca (o acepta con número) al menos tres afirmaciones ajenas. Prohibido aceptar sin medir.
3. **Resolución por medición.** Cada disputa se cierra con un número o `no_verificable` con el motivo. Se
   documenta el desacuerdo.
4. **Ningún remedio accionable se pierde**, venga de un rol o del radar.

## Las preguntas del debate

**R1 · El evento de impago observable (Elkano D1-D4) frente a nuestras anclas.** Frente a `tension_6m`
(estado, circular por la póliza, no medible en empresas nuevas) y `expansion_6m`, Elkano propone un evento
observable desde el mes 0. **Medid**: ¿se puede construir D1-D4 con nuestros datos? ¿es no circular?
¿separa mejor que `tension_6m` (AUC con `n`)? ¿existe desde el mes 0? Si es mejor ancla, **¿cambiamos las
anclas o añadimos la suya?**

**R2 · LABEL-VIABILITY: ¿hay un factor latente de salud?** burn-rate sostiene que 3 indicadores de tensión
son **independientes** (no hay factor latente) y por eso no se debe entrenar contra una etiqueta. **Medid**:
en nuestros datos, ¿los eventos adversos (`tension_6m`, `incumplimiento_6m`, `caida_6m`) co-mueven más de
lo esperado por azar, o son independientes? Si son independientes, **¿tiene sentido calibrar una nota
única contra cuatro anclas** (o hay que medir cada comportamiento por separado)?

**R3 · La mora «as-of» (burn-rate).** Sostienen que `payment_date` solo es fiable si `status='paid'` y que
recalcular la mora cada mes destapa **122.006 facturas tardías ocultas**. Es la clase de fuga que nosotros
encontramos en `late_share` (D05/alias). **Medid**: ¿cuánto cambia nuestro score y nuestros hechos si
aplicamos su recálculo? ¿nuestra mora actual subestima o sobreestima?

**R4 · El neteo espejo del intragrupo (burn-rate, 25,9 %).** Es un **método concreto** de agregación por
grupo. **Medid** en nuestros datos: ¿qué fracción de las transferencias intragrupo son espejo? ¿el neteo
cambia el veredicto de Q12 (unidad = grupo)? ¿es el neteo correcto o pierde información (una filial que
custodia caja)?

**R5 · Nulos honestos y multi-comprador.** burn-rate usa `score = null` con motivo (no cero); Byte_Me
re-pondera **el mismo score por comprador** (BANK/FUND/INSURER). **Medid/comparad**: ¿coincide el nulo
honesto con nuestra decisión de `tension_6m = null` en `group_funded`? ¿el re-weight por comprador es
mejor que nuestras «notas separadas» (Q4) o es lo mismo con otro nombre?

**R6 · ¿Nuestra anticipación (0,62-0,70) es real o inflada?** burn-rate publica **0,53-0,58** a 6 meses y
lo llama honesto; Elkano mide con Gini y control de «feature gemela» del evento. **Medid**: si quitamos la
circularidad de la etiqueta (Q2: `tension_nopol`, `group_funded = null`) y el control de feature gemela,
**¿cuánto baja nuestro AUC?** ¿es nuestro 0,70 real o el artefacto que ellos evitan?

**R7 · El encuadre.** burn-rate mueve la unidad al **grupo** y al **usuario inversor con cartera ordenada**;
Elkano tiene la validación; Byte_Me el producto. **Conclusión**: dado todo lo anterior, ¿cuál es **nuestra**
conclusión nueva —qué hacemos distinto, qué copiamos y qué descartamos—? No vale «hacer todo»: priorizad.

## Producto

`salida/consejo/debate_radar.md`, una fila por pregunta (R1-R7):

| pregunta | veredicto | medición que lo sostiene | quién disintió | qué copiamos / descartamos del radar |
|---|---|---|---|---|

Y al final: **la conclusión nueva** en ≤10 líneas (qué cambia en nuestro plan respecto al veredicto anterior),
y las **premisas nuevas** con su `evidencia` para `salida/premisas.jsonl`.

## Reglas

- **Solo escribes** en `.devin/workflows/autoresearch/salida/`. No edites código ni el modelo, no toques `data/`.
- El radar es **terceros**: cita el equipo y el repo; no lo trates como fuente de verdad.
- Escribe en español. Cada afirmación lleva su medición o su `file:line`.
- Termina con: la conclusión nueva, cuántas preguntas se cerraron y los remedios accionables (con autor).
