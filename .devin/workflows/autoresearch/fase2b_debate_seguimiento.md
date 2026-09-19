# Fase 2b · Seguimiento del debate: la unidad de medida (grupo) y las preguntas nuevas

Eres el **orquestador** del workflow de autoresearch. Este es el **seguimiento del debate de la fase 2**:
el consejo ya cerró su primer veredicto (`salida/consejo/debate_veredicto.md`) y dejó preguntas abiertas
(Q6-Q11). Ahora se debate una pregunta nueva y central —**Q12: ¿la unidad de medida debe ser el grupo, no
la empresa?**— y se cierran las que quedaron vivas. **No modifica código ni el modelo.**

Entrada:
- `salida/consejo/debate_veredicto.md` (el veredicto anterior, para no repetirlo).
- `.devin/workflows/autoresearch/DEBATE.md` (con **Q12** añadida al final).
- Las preguntas nuevas Q6-Q11 del veredicto anterior.

## Las reglas del debate (las mismas, no negociables)

1. **La postura por defecto es la duda.** Ninguna afirmación —de otro rol o del fichero— se acepta sin una
   **medición** (`n`, tasa, lift, AUC, `file:line`). «Me parece razonable» no es un argumento.
2. **Interpelación por nombre.** Cada consejero interpela a **al menos otros dos roles** con una pregunta
   **falsable** y ataca (o acepta con número) al menos tres afirmaciones ajenas. Prohibido aceptar sin medir.
3. **Resolución por medición.** Cada disputa se cierra con un número o se declara `no_verificable` con el
   motivo. **Se documenta el desacuerdo**; el consenso cómodo es un fallo.
4. **Ningún remedio accionable se pierde.** Entra con su autor.

## Q12 · La unidad de medida: grupo o empresa

Es la pregunta principal. **Hipótesis a verificar o refutar:** dentro de un grupo las empresas se prestan
entre ellas (*cash pooling*, transferencias intragrupo), así que la caja *standalone* de una filial engaña —
el grupo le tapa el hueco, o la filial custodia la caja del grupo. Entonces **la unidad correcta para el
riesgo del deudor puede ser el grupo consolidado**, no la entidad legal. (El consejo ya vio que «el score no
tiene ninguna feature de grupo» y que la etiqueta excluye a las financiadas por su grupo, Q2.)

**Que el consejo mida, como mínimo:**
- En las empresas `group_funded`, ¿un score **agregado por `group_id`** (caja consolidada neta de intragrupo,
  cobros, deuda) separa la tensión del grupo mejor que el score individual? Dar AUC con `n` de grupos.
- ¿La filial que **custodia** la caja del grupo aparece como «falsa sana» por su `runway` inflado? ¿cuántas?
- ¿La agregación correcta es suma de caja, `runway` consolidado, o deuda intragrupo neteada? Comparar al menos
  dos definiciones.
- **Legal vs económico:** el deudor es la entidad legal; el grupo responde por contrato. ¿Cambia la decisión
  de préstamo o solo el diagnóstico? ¿Debe el producto publicar **dos niveles**?

## Q6-Q11 · Lo que quedó abierto

Cierra por medición las preguntas Q6 a Q11 del veredicto anterior (explicación aditiva que no viaja en la
entrega, sesgo de ventana de observación, impago vs periodicidad, la demo que vende «rompe caja», condiciones
de concesión no medibles, «crecimiento» probado con apuntes). Puedes refutarlas o confirmarlas; lo que no
puedes es dejarlas sin dato.

## Producto

- `salida/consejo/debate_veredicto_seguimiento.md`: una fila por pregunta (Q12 + Q6-Q11) con
  `pregunta | veredicto | medición que lo sostiene | quién disintió | acción propuesta`.
- Las **premisas nuevas** que salgan, con su `evidencia`, se añaden a `salida/premisas.jsonl`.
- Actualiza `salida/consejo/debate_veredicto.md` solo con un puntero a este seguimiento (no lo reescribas).

## Reglas

- **Solo escribes** en `.devin/workflows/autoresearch/salida/`. No edites código ni el modelo, no toques `data/`.
- Escribe en español. Cada afirmación lleva su medición o su `file:line`.
- Termina con: veredicto de Q12 en una frase, cuántas preguntas se cerraron, cuántas siguen abiertas y los
  remedios accionables nuevos (con autor).
