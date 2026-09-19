# Debate del consejo · Preguntas abiertas que hay que resolver por medición

> **Para qué existe este fichero.** Estas preguntas salieron de una revisión manual del trabajo de la
> cadena. **No son conclusiones: son acusaciones que el consejo debe verificar o refutar por su cuenta.**
> Nadie las ha demostrado todavía en un debate adversarial. El consejo las recibe como *hipótesis a
> atacar*, no como verdad. Si un consejero cree que una de estas afirmaciones es falsa, debe decirlo y
> medirlo.

## Reglas del debate (obligatorias)

1. **La postura por defecto es la duda.** Prohibido aceptar la afirmación de otro rol —o de este
   fichero— sin una **medición** que la sostenga (`n`, tasa, lift, AUC, `file:line`). «Me parece razonable»
   no es un argumento.
2. **Pregunta el porqué.** Cuando otro rol afirme algo, la respuesta por defecto es *«¿por qué X? muéstrame
   el número»*. Cada consejero debe **interpelar por su nombre** a al menos otros dos roles y formularles
   una pregunta **falsable** (que se pueda responder con una consulta).
3. **No se diluye el desacuerdo.** Si dos roles no se convencen, se registra el desacuerdo con las dos
   posturas y el dato que falta para zanjarlo. El consenso cómodo es un fallo, no un éxito.
4. **Ningún remedio accionable se pierde.** Si un rol propone una solución concreta (p. ej. «publicar una
   nota de expansión separada»), esa solución entra en el veredicto con su autor, aunque sea incómoda.
5. **Se mide antes de creer.** Toda afirmación cuantitativa se reproduce con una consulta sobre
   `research/data/panel.parquet` o `salida/derivado.parquet`. Si no se puede medir, se declara
   `no_verificable` con el motivo.

## Las preguntas abiertas

### Q1 · ¿Las cuatro anclas del score (E1-E4) son las correctas, o son una herencia sin validar?

`research/src/targets.py` define `tension_6m`, `incumplimiento_6m`, `caida_6m` y `expansion_6m`, y son
las que calibran el score (`evaluate.py` `EVENTS`). **Acusación:** se heredaron del trabajo previo y
nadie las ha validado como el objetivo correcto; el consejo las discutió de pasada pero **no propuso un
conjunto alternativo**.

**Que el consejo responda, con datos:**
- ¿Existen en el panel eventos alternativos ya calculados (`tension_onset`, `incumplimiento_mes`, las
  etiquetas v1, una etiqueta de *cura/recuperación*)? ¿Alguno separa mejor?
- ¿El horizonte de 6 meses es el correcto para un prestamista de circulante? ¿3 meses cambia la conclusión?
- ¿Debería existir una etiqueta que el reto pide y no está — «necesita financiación» / «rompe caja a 2
  meses» (el caso de la demo)— en vez de inferirla de `tension_6m`?

### Q2 · La etiqueta de tensión es circular (¿lo es de verdad?)

**Acusación:** `targets.py:84-87` suma la **póliza disponible** (`lc_limit − lc_drawn`) a la liquidez con
la que define `stress`, y `targets.py:93-95` **excluye** del evento a las empresas financiadas por su
grupo (`group_funded`). Si es cierto, `tension_6m` está **definida en parte por dos features del propio
score** (`lc_util`, intragrupo) y toda premisa sobre ellas es infalsable.

**Que el consejo responda:** ¿es circular? ¿cuánto? ¿qué se mide si se quita la póliza de la definición
de `stress` y se pone `tension_6m = null` (no 0) en `group_funded`? ¿Cambia el AUC del nivel?

### Q3 · Tres de las cuatro anclas no existen para las empresas nuevas

**Acusación:** `caida_6m` exige `month_idx >= 8`, `expansion_6m >= 5` e `incumplimiento_6m` exige
obligación regular en 4 de los últimos 6 meses. El test oculto son **empresas nuevas con historia corta**.
Si es cierto, el score se calibra con eventos que **no se pueden etiquetar en el perfil del test**, y el
peso nº 1 (`activity_trend`) se «compra» con los coeficientes de caída y expansión.

**Que el consejo responda:** ¿qué AUC del nivel se puede medir con `month_idx < 6`? ¿hay que definir
**variantes de historia corta** de cada evento? ¿qué entrega el sistema a una empresa del mes 2?

### Q4 · Una nota única que promedia cuatro eventos diluye cada uno

**Acusación:** la nota promedia los pesos de los cuatro eventos (D12/R10). Medido: `runway` tiene
coeficiente 3,414 para tensión y **0,000** para expansión; `runway` sola separa tensión **0,791** frente
al score 0,695, y `n_tx` sola separa expansión **0,616** frente a 0,566. Es decir, **el score es peor que
su propio ingrediente en los dos extremos**. El remedio propuesto por un rol: **notas separadas**
(adversa y de expansión), no bajar umbrales.

**Que el consejo responda:** ¿se confirma que el score pierde frente a una sola columna? ¿la solución son
notas separadas, una nota con pesos por comprador, o dejar el promedio? ¿cómo se mantiene la explicación
aditiva exacta con dos notas?

### Q5 · La regla de parada del bucle es demasiado laxa

**Acusación:** `fase3_autoresearch.md` para el bucle con **dos** iteraciones seguidas sin mejora
(«meseta»). Con el propio margen de error que el informe declara (±0,012-0,025 por evento), dos
iteraciones sin mejora son **ruido**, no un techo. El bucle paró en la iteración 8 de 12 con cambios
candidatos sin probar.

**Que el consejo responda:** ¿cuántas iteraciones sin mejora son una meseta de verdad? ¿qué cambios
quedaron sin probar y por qué? ¿el objetivo (PM) debe ser el promedio o por evento?

### Q12 · ¿La unidad de medida debe ser el **grupo**, no la empresa?

**Hipótesis (a verificar o refutar):** dentro de un grupo, las empresas se prestan entre ellas (transferencias
intragrupo, *cash pooling*). La caja *standalone* de una filial engaña justo por eso: o el grupo le tapa el
hueco, o la filial custodia la caja de todo el grupo. Entonces **la unidad correcta para el riesgo del deudor
puede ser el grupo consolidado**, no la entidad legal. El consejo ya detectó que «el score no tiene ninguna
feature de grupo» (`r2_riesgo-modelo.md`) y la etiqueta excluye a las financiadas por su grupo (Q2); esto
propone la respuesta contraria a excluirlas: **medirlas donde de verdad se decide la liquidez.**

**Que el consejo responda, con datos:**
- ¿El score *standalone* **desclasifica** a las filiales de grupo? Medir: en las empresas `group_funded`, ¿un
  score **agregado por `group_id`** (caja consolidada, cobros, deuda) predice la tensión del grupo mejor que
  el score individual? ¿cuánto mejor (AUC, con `n` de grupos)?
- ¿Cómo se agrega bien? ¿suma de caja neta de intragrupo, `runway` consolidado, deuda intragrupo neteada?
  ¿La filial que **custodia** la caja del grupo infla su propio `runway` (falso sano)?
- **Legal vs económico.** El deudor es la entidad legal; el grupo solo responde por contrato (avales,
  *comfort letters*, cash pooling formal). ¿Cambia la decisión de préstamo o solo el diagnóstico?
- ¿La entrega (60-80 empresas no vistas) se puntúa por `company_id` o por `group_id`? `AGENTS.md` lo tiene
  como pregunta abierta. ¿Debe el producto publicar **dos niveles** (grupo consolidado + entidad legal)?

**Acusación de cierre:** puntuar a la filial por su caja propia, cuando el grupo la cubre, es tan circular
como la etiqueta de Q2 — y en el sentido contrario.

## Producto del debate

`salida/consejo/debate_veredicto.md`, con una fila por pregunta:

| pregunta | veredicto del consejo | medición que lo sostiene | quién disintió | acción propuesta |
|---|---|---|---|---|

Y la lista de **preguntas nuevas** que el debate deja abiertas, para añadirlas a `premisas.jsonl`.
