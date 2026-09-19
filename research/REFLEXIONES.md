# Reflexiones y mejoras abiertas

Documento vivo con lo que hemos ido pensando sobre el score: dudas de fondo, mejoras posibles y lo que ya sabemos gracias a mediciones. Las decisiones ya tomadas están en `DECISIONS.md`. Aquí van las preguntas que siguen abiertas y las propuestas pendientes de probar.

**Cómo añadir una.** Usa el siguiente número libre y la misma plantilla: estado, pregunta, lo medido (con la fuente), opciones, recomendación y siguiente paso. Cuando una reflexión se resuelva, cámbiale el estado y enlaza la decisión (`Dxx`) o el commit.

Estados: **abierta** (sin propuesta), **propuesta** (hay recomendación y falta probarla), **en curso**, **decidida** o **descartada**.

## Índice

| # | Tema | Estado | Prioridad |
|---|---|---|---|
| R01 | La nota es relativa a la población de train ("con curva") | propuesta | alta |
| R02 | Anclar la nota a una probabilidad de evento (escala absoluta) | en curso (probabilidades publicadas junto a la nota) | alta |
| R03 | Sesgo de tamaño en meses de caja, peso de nóminas y volatilidad | propuesta | media |
| R04 | Desequilibrio de clases: qué afecta y qué no | decidida (no afecta al orden) | baja |
| R05 | ¿Qué eventos son la "verdad"? (panel multi-modelo) | decidida (eventos v2 en `targets.py`) | alta |
| R06 | El apagado fuera del score, como producto de retención | decidida (fuera de la calibración; producto pendiente) | alta |
| R07 | Features del brainstorming: ¿salud o desconexión? | en curso | media |
| R08 | La caja reconstruida no cuadra con los flujos en el 16 % de los meses | diagnosticada: es financiación intragrupo | alta |
| R09 | La forma del modelo no es el límite: la información sí | decidida | — |
| R10 | Cómo combinar varios eventos en una nota | decidida (dos notas, D33) | media |
| R11 | Bache frente a caída sigue sin resolverse | abierta | media |
| R12 | Alertas que se encienden y se apagan | propuesta | baja |
| R13 | Modelos generativos (TimeGPT, VAE, DeepAR) | abierta | baja |
| R14 | Empresas del test fuera de distribución | decidida en parte | media |
| R15 | Efecto de borde en agosto de 2026 | abierta | baja |
| R16 | Entre quien tiene deuda, la carga no ordena el riesgo | decidida (la cuota sale de E2, D35; `debt_burden` peso 0,005) | media |
| R17 | Premisas del consejo que resultaron incorrectas (fase 3) | decidida (registro; ampliado en la ronda 2) | — |
| R18 | La cohorte larga puntúa ~5 puntos menos a igual caja | diagnosticada (saturación de la ventana de 12 m); remedio medido y descartado | baja |
| R19 | El suavizado (α) es un dial estabilidad ↔ reacción, no información | decidida (α = 0,5; curva medida) | baja |
| R20 | Dentro de la nota adversa, liquidez ↔ impago/caída | abierta | media |

---

## R01 · La nota es relativa a la población de train ("con curva")

**Estado:** propuesta.

**Pregunta.** Si todas las empresas tienen caja positiva, ¿no deberían salir todas con nota alta en lugar de repartirse entre 0 y 100?

**Cómo funciona hoy.** Cada feature se pasa a percentil frente al train: 3 meses de caja valen 80 si el 80 % del train tiene menos. Después la escala se estira para que el 5 % peor del train saque 15 y el 5 % mejor saque 85 (D22). Por tanto, la nota mide "mejor o peor que nuestras empresas de train", no "sana en términos absolutos".

**Lo medido** (`reports/escala.md` §1, con 220 empresas que nunca tienen caja negativa y suelen cubrir 3 meses o más de gastos):

| Regla | Mediana | En riesgo | Sanas |
|---|---|---|---|
| Regla fija del train (lo que hacemos) | 63 | 4 % | 43 % |
| Regla reajustada solo con esas empresas | 46 | 23 % | 16 % |

- **Si se recalculara la regla sobre una población sana, las repartiría de todas formas.** Por eso la regla se ajusta una vez con el train y se congela; nunca se recalcula con el test.
- **Aun así, "sano" depende de cómo sea nuestro train.** Si el train fuera todo de empresas buenas, la regla sería más exigente de la cuenta.
- **Caja positiva no significa sano.** El 93 % de los meses tienen caja positiva y su reparto de notas es casi igual al del total. Lo que distingue es cuántos meses de gasto cubre esa caja.

**Opciones.**
1. Dejarlo como está y documentar que la nota es relativa al train.
2. Anclar la escala publicada a una probabilidad de evento (R02).
3. Umbrales absolutos por feature fijados con criterio experto (por ejemplo, 6 meses de caja o más = 100), en lugar de percentiles.

**Recomendación.** Opción 2. Los percentiles se quedan como pieza interna (pesos y explicaciones), pero la escala publicada pasa a ser absoluta.

**Siguiente paso.** Implementarlo en la v7 junto con los eventos nuevos (R05).

## R02 · Anclar la nota a una probabilidad de evento (escala absoluta)

**Estado:** propuesta.

**Idea.** Hacerlo como un scorecard bancario: la nota se traduce en una probabilidad de evento adverso en 6 meses y las bandas se fijan con probabilidades, no con percentiles (por ejemplo, sano = menos de un 10 %). Si todas las empresas son sanas, todas tienen probabilidad baja y todas salen altas, sin estirar la escala.

**Lo medido** (`reports/escala.md` §3, evento adverso = saldo negativo o caída de cobros, tasa base 21,8 %):

| Nota actual | 10 | 30 | 50 | 70 | 90 |
|---|---|---|---|---|---|
| Probabilidad de evento adverso | 37 % | 28 % | 21 % | 15 % | 10 % |

**Lectura.** La escala 0-100 exagera cuánto sabemos: de 10 a 90 la probabilidad solo pasa del 37 % al 10 %. Una escala absoluta sería más estrecha, pero honesta.

**Riesgos.**
- Solo tiene sentido si los eventos son buenos (R05).
- Si el test tiene otra tasa de problemas, hay que reajustar la constante de la probabilidad.
- La explicación aditiva exacta se mantiene si la escala es lineal en el logit. Si es lineal en la probabilidad, deja de ser exacta.

**Opciones de escala.**
- **Puntos para doblar la odds**, al estilo de los scorecards: nota = A − B·log(odds). Es lineal en el logit, así que la explicación sigue siendo exacta.
- **100·(1 − probabilidad)**: más fácil de leer, pero pierde la aditividad.

**Siguiente paso.** Calibrar contra E1-E4 (R05) y comparar las bandas nuevas con las actuales empresa por empresa.

**Actualización (v7).** `HealthScorer` calibra en train una logística de una sola variable (evento ~ nota) por evento y publica, junto a la nota, `prob_tension_6m`, `prob_incumplimiento_6m`, `prob_caida_6m`, `prob_expansion_6m` y `prob_adverso` (alguno de los tres adversos). La nota 0-100 y su explicación no cambian. Con los eventos v2, la probabilidad separa mucho más:

| Nota | 10 | 30 | 50 | 70 | 90 |
|---|---|---|---|---|---|
| Algún evento adverso a 6 meses | 59 % | 45 % | 31 % | 20 % | 12 % |
| Tensión de liquidez | 56 % | 40 % | 26 % | 16 % | 9 % |
| Crecimiento autofinanciado | 4 % | 5 % | 6 % | 7 % | 9 % |

Pendiente: decidir si la nota publicada pasa a ser absoluta (puntos para doblar la odds) y fijar las bandas por probabilidad.

## R03 · Sesgo de tamaño en meses de caja, peso de nóminas y volatilidad

**Estado:** propuesta.

**Lo medido** (`reports/escala.md` §2). La correlación entre nota y tamaño es casi nula (−0,07), pero por dentro hay diferencias:

| Quintil de tamaño | Meses de caja (mediana) | Nota (mediana) | Saldo negativo en 6 meses | Caída de cobros en 6 meses |
|---|---|---|---|---|
| Pequeñas | 2,2 | 52 | 3,6 % | 20 % |
| Grandes | 0,2 | 46 | 5,7 % | 17 % |

- **Las grandes tienen diez veces menos meses de caja, pero sus eventos apenas aumentan.** Es probable que trabajen con menos colchón (pólizas, cobros más regulares) sin estar peor.
- **Features que dependen del tamaño:** `runway` (−0,35), `payroll_burden` (−0,46), `net_vol_6m` (−0,37), `transfer_dep` (+0,34) y `growth_vs_12m` (+0,20).

**Opciones.**
1. Calcular el percentil de esas features dentro de cada banda de tamaño.
2. Añadir el tamaño a la calibración de los pesos.
3. No tocar nada: el efecto sobre la nota final es pequeño.

**Recomendación.** Probar la opción 1 y quedarse con ella solo si mejora el AUC frente a E1-E4 fuera de grupo. Hay que vigilar que en el test haya empresas de tamaños que no vimos en el train (R14).

## R04 · Desequilibrio de clases: qué afecta y qué no

**Estado:** decidida (no afecta al orden).

- **Los eventos son raros (3-17 %), pero eso no sesga el orden de la nota ni el AUC.** El AUC no depende de la tasa de eventos.
- **Los pesos no dependen de la tasa.** Se normalizan por evento antes de promediar, así que un evento frecuente no pesa más que uno raro (D12).
- **Sí importa en dos casos:**
  - Si se publica una probabilidad (R02), la constante depende de la tasa base.
  - La precisión de las alertas depende de cuántos eventos haya en el test.

## R05 · ¿Qué eventos son la "verdad"? (panel multi-modelo)

**Estado:** en curso. La implementación experimental está en `src/events_v2.py` y la medición en `reports/eventos_v2.md`.

**Fuentes.** Hubo 17 respuestas de 4 familias de modelos no-Claude (GLM 5.3, DeepSeek V4, Qwen 3.6 y un agente de Cursor con acceso a los datos). La síntesis la hizo GLM 5.3 y está en `brainstorm/eventos/SINTESIS_glm5.3.md`. Se usaron modelos de otras familias para evitar el sesgo de familia de modelo.

**Consenso.**
- El apagado no es salud (R06).
- El saldo negativo tiene que medirse como transición, no como estado.
- La caída de cobros está contaminada por apagados y baches.
- El incumplimiento solo sirve en versión estricta.
- La unión de todos los eventos adversos (`adverse_6m`) no debe usarse para calibrar.

**Eventos propuestos y lo que se ha medido:**

| Evento | Papel | Tasa (empresa-mes) | Observación |
|---|---|---|---|
| E1 · Entrada en tensión de caja persistente | ancla adversa principal | 2,7 % | Solo el 38 % de los arranques se confirma en los meses siguientes. Ver R08. |
| E2 · Incumplimiento estricto | co-ancla de crédito | 29,6 % | **Demasiado amplio.** La deuda >90 días con proveedores sola suma un 17 %, y el 39 % de las nóminas o cuotas "impagadas" reaparecen al mes siguiente. |
| E3 · Caída estructural de cobros sin apagado ni rebote | co-ancla de trayectoria | 10,2 % | El filtro de "sin rebote" quita el 36 % de las caídas brutas. |
| E4 · Expansión sostenida autofinanciada | ancla positiva | 5,9 % | Los filtros quitan el 67 % de los crecimientos brutos. |
| E5 bache, E6 sano sostenido, E7 recuperación | clasificación y validación | — | E6: 7,9 % de las empresas. |

**Pendiente.**
1. **Estrechar E2.** Exigir dos meses seguidos sin la nómina o la cuota, y separar la deuda con proveedores como otro evento.
2. **Tratar E1 como riesgo condicionado.** El 0,68 de la tabla y el 0,32 del §6 son el mismo número con el signo cambiado: cuantos más meses de caja tiene hoy la empresa, más probable es E1, porque el evento exige partir de una situación sana y las empresas ya en tensión no pueden tenerlo. Si se calibra así, `runway` recibiría peso 0. E1 hay que evaluarlo y calibrarlo solo sobre las empresas que pueden tenerlo (≥ 3 meses sanos), o combinarlo con el estado actual.
3. **Recalibrar los pesos contra E1-E4 y medir la matriz completa de AUC.**
4. **Hacer las preguntas a la organización** (lista priorizada en §6 de la síntesis). Las más importantes: qué es el apagado en el generador y contra qué puntúa el leaderboard.

**Actualización (v7): implementado en `src/targets.py`.** Los pesos se calibran ahora con cuatro eventos, y los v1 se conservan para comparar:

| Evento | Definición final | Tasa | Empresas |
|---|---|---|---|
| `tension_6m` | Estará en tensión de liquidez persistente (≥2 de 3 meses con <0,25 meses de liquidez o liquidez negativa), contando la póliza disponible y excluyendo los meses con financiación del grupo | 27,4 % | 37,8 % |
| `incumplimiento_6m` | Nómina o cuota regulares ausentes 2 meses seguidos con el feed activo, o IVA ausente 2 trimestres seguidos. Solo para empresas con alguna obligación regular | 12,3 % | 22,8 % |
| `caida_6m` | E3: caída estructural de cobros, censurada por apagado y sin rebote | 10,2 % | 26,6 % |
| `expansion_6m` | E4: expansión autofinanciada (cara positiva) | 5,9 % | 21,9 % |
| `tension_entrada_6m` | E1 como **transición** en el conjunto en riesgo (hoy sanas). Solo mide la antelación; no calibra | 2,3 % | 5,1 % |

Decisiones tomadas al implementarlo, con la evidencia que las motivó:
1. **La tensión calibra como estado persistente y no como entrada.** Calibrada como entrada, la caja recibía peso 0,03, porque dentro del conjunto en riesgo el nivel de caja no predice la entrada. Pero a un prestamista una empresa que ya está en tensión y va a seguir en ella le importa. La entrada se reserva para medir la antelación.
2. **El incumplimiento se restringe a empresas con obligaciones.** Sin la restricción, la "carga de deuda" subía de 0,03 a 0,14 por elegibilidad: solo puede dejar de pagar una cuota quien tiene cuotas.
3. **La tensión excluye la financiación intragrupo** (ver R08) **y cuenta la póliza disponible.**

Resultado en los pesos: la caja pesa 0,18 (0,16 en v6), la tendencia de actividad 0,20 y el uso de póliza 0,09. Los pagos tardíos a proveedores bajan a 0: su peso venía del apagado.

**Validación fuera de muestra** (GroupKFold por grupo × 3 cortes; `metrics_v6b.json` es la v6 medida contra los eventos nuevos y `metrics_v7.json` la versión nueva). AUC del nivel del score frente a cada evento a 6 meses:

| Evento | v6 (calibra con v1) | v7 (calibra con v2) |
|---|---|---|
| Tensión de liquidez | 0,604 | **0,657** |
| Incumplimiento | 0,607 | 0,603 |
| Caída estructural de cobros | **0,613** | 0,587 |
| Expansión autofinanciada | 0,607 | 0,607 |
| Apagado (ya no calibra) | 0,586 | 0,565 |

La trayectoria cambia poco: el AUC de deterioro baja de 0,742 a 0,725, el de mejora sube de 0,715 a 0,730 y la ventaja frente a AR(1) pasa del 3,8 % al 2,0 % de MAE.

**Lectura.** La v7 gana donde más importa a un prestamista (la liquidez, +0,05) y pierde algo en la caída de cobros (−0,03). Promediar los pesos de cuatro eventos sigue diluyendo cada uno (R10). Como ahora la probabilidad de cada evento se publica por separado (R02), cada comprador puede mirar el riesgo que le importa.

## R06 · El apagado fuera del score, como producto de retención

**Estado:** propuesta.

**Lo medido.**
- **Parece desconexión, no cierre.** Las empresas que se apagan tienen de mediana 0,59 meses de caja, frente a 0,48 de las que siguen activas, y solo el 9 % se va con caja ≤ 0.
- **Clasificación del auditor de datos (Cursor):** 52 % desconexiones, 36 % casos ambiguos y 12 % cierres plausibles.
- **Borde del dataset:** el 36 % se apaga en julio de 2026.

**Propuesta.**
- Sacar el apagado de la calibración de pesos.
- Usarlo como censura: no contar los demás eventos cuando la empresa se apaga dentro de la ventana.
- Ofrecerlo como producto aparte para Embat, un riesgo de baja con su propio comprador (equipo de éxito de cliente).

**Actualización (v7):** fuera de la calibración (`evaluate.EVENTS`) y usado como censura en todos los eventos v2. El producto de retención sigue pendiente.

## R07 · Features del brainstorming: ¿salud o desconexión?

**Estado:** en curso.

**Duda.** Las mejores features del brainstorming (`payee_concentration`, con AUC 0,76 frente al apagado, y `lost_accel`, con 0,74) destacaban frente al apagado, que es sobre todo desconexión (R06).

**Lo medido** (`reports/eventos_v2.md` §5):
- La mayoría conserva señal frente a E1-E4, aunque bastante menor. `lost_accel` es la mejor, con distancia 0,16 frente a E1.
- `tax_miss` y `billing_to_cash` se quedan débiles.

**Siguiente paso.** Validarlas de forma incremental, añadiendo una cada vez al score, con AUC fuera de grupo frente a E1-E4. Solo entra la que mejore.

**Actualización (autoresearch, fase 3).** Medidas sobre el panel actual (`.devin/workflows/autoresearch/salida/iteraciones/diag_candidatas.py`): entran `payroll_cv` **a la baja** (D28, en sustitución de `payroll_burden`) y `oper_persistence_6m` (D30). `lost_accel` y `yoy_inflow` son demasiado ruidosas (17-25 puntos de percentil al mes) y de poca cobertura. `payee_concentration` y `hhi_ap_6m` exigen rehacer el panel y siguen pendientes; por su perfil (señal adversa sin cara positiva) es probable que choquen con la expansión (R10).

## R08 · La caja reconstruida no cuadra con los flujos en el 16 % de los meses

**Estado:** abierta. Hallazgo nuevo, encontrado al revisar a mano casos de E1.

**Lo medido** (`reports/escala.md` §4). Para cada mes se compara la variación de caja con cobros menos pagos:
- En la mitad de los meses cuadran casi exactamente (descuadre mediano del 1 %).
- En el 15,6 % de los meses el descuadre supera el 50 % del flujo.
- El 10,8 % de las empresas descuadran en más de la mitad de sus meses.

**Ejemplo.** COMP_1155 mueve millones al mes y su caja se queda clavada en 13.756 durante siete meses. Todos esos movimientos son internos e intragrupo.

**Hipótesis.**
- Los flujos pasan por productos que no entran en la reconstrucción de la caja (tarjetas, pólizas, cuentas sin saldo final).
- Las cuentas de grupo o de cash pooling no están en `balances`.

**Impacto.**
- **Meses de caja**, la feature con más peso, está mal para esas empresas.
- **E1 y el saldo negativo** pueden dispararse, o dejar de dispararse, por un artefacto.

**Siguiente paso.**
1. Diagnosticar el descuadre por tipo de producto.
2. Marcar las empresas con caja no fiable y tratar su `runway` como dato ausente (vale 50, neutro).
3. Excluir esos meses de E1.
4. Preguntar a la organización qué productos suma `cash_end` (pregunta 8 de la síntesis).

**Actualización: diagnosticado.** No es un error de reconstrucción, es financiación intragrupo (cash pooling).
- **La caja es correcta.** En los meses con descuadre superior al 50 % del flujo externo (11,2 %), la caja cuadra al céntimo con **todos** los movimientos de sus cuentas en el 97 % de los casos (residuo mediano del 0,00 %).
- **El hueco lo explican los traspasos intragrupo** en el 87 % de esos meses, y los intragrupo junto con los movimientos de inversión en el 92 %. El panel excluye los intragrupo de cobros y pagos, pero la caja sí los incluye.
- **Hipótesis descartada:** que hubiera flujos en productos sin saldo reconstruido. El 99 % del volumen pasa por cuentas corrientes con saldo final.
- **Consecuencia.** Estas filiales operan con la caja justa porque su grupo cubre los huecos, y su riesgo de liquidez es del grupo. `tension_6m` y `tension_entrada_6m` excluyen los meses con más del 20 % del flujo intragrupo.
- **Pendiente:** una feature de "financiación neta del grupo" y la liquidez a nivel de grupo.

**Actualización (autoresearch, fase 3).** La caja **centinela** (`dq_cash_sentinel`, 9 empresas) ya no puntúa: `runway` es «sin dato» (D31). La caja **implausible** (`dq_cash_implausible`, 55 empresas activas) resultó ser riqueza real (holdings con mucha caja y poco flujo: unión adversa 13 % frente a 32 %) y **no** se toca. La **deriva** (`has_drift`, 45 empresas, 791 filas) sigue pendiente: es un flag de empresa (marca todos los meses aunque solo los primeros estén mal) y su etiqueta de tensión (52 %) sale de la misma caja, así que neutralizar `runway` bajaría la PM sin que eso signifique nada. Hace falta un flag por fila y la exclusión simétrica en `targets.py`.

## R09 · La forma del modelo no es el límite: la información sí

**Estado:** decidida.

- **Una logística lineal y un LightGBM** sobre las 17 features dan el mismo AUC frente a cada evento.
- **Versiones no lineales de cada feature** (por tramos) aportan poco.
- **Conclusión:** para mejorar hacen falta mejores eventos (R05) y mejores features (R07, R08), no un modelo más complejo.

## R10 · Cómo combinar varios eventos en una nota

**Estado:** abierta.

**Hoy.** Se ajusta una logística por evento, con pesos no negativos, y se promedian los pesos normalizados. Es sencillo y explicable, pero una empresa con riesgo de caja y otra con caída de cobros acaban en la misma escala sin que sepamos si son comparables.

**Opciones.**
1. Varias notas (riesgo de caja, riesgo de impago, momentum) y la nota global como su media.
2. Un índice latente con etiquetas blandas (Dawid-Skene o Snorkel). La síntesis propone dos factores, tensión y momentum.
3. Un modelo multitarea.

**Recomendación.** Empezar por la opción 1, porque encaja con las preguntas del reto y con el producto. La 2 solo si hay tiempo.

**Actualización (autoresearch, fase 3): el trade-off está medido y es estructural.** Tres veces apareció el mismo choque entre liquidez y crecimiento (`salida/iteraciones/iter_001`, `iter_002`, `iter_008`):

| cambio | tensión | expansión | caída | PM |
|---|---|---|---|---|
| peso ×2 al evento de tensión al promediar (`EVENT_W`) | **+0,059** | −0,028 | −0,017 | +0,003 |
| CV total de nómina (penaliza también contratar) | +0,009 | −0,025 (OOF) | +0,021 | +0,011 |
| regla «< 0,5 meses de liquidez → no sano» | +0,006 a +0,019 | −0,008 a −0,025 | −0,003 | −0,001 a −0,003 |

Las empresas «sanas» con menos de medio mes de liquidez tienen 4× más unión adversa (41,8 % frente a 11,3 %) **y** 2,3× más expansión (15,5 % frente a 6,7 %): gastan la caja en crecer. Un score que también deba ordenar la expansión no puede darles la criticidad que exige el prestamista (P120, P122, P173, P175, P176 quedan en `falla` por eso, no por error del modelo). Además, cada feature nueva reparte peso y baja el de la caja (`runway` 0,169 → 0,157 en el bucle).

**Propuesta concreta para la fase 4:** publicar junto a la nota general una **nota del prestamista** con la misma explicación aditiva: `EVENT_W = {tension_6m: 2}` (3 líneas en `HealthScorer.fit`, medidas en iter_001: AUC frente a tensión 0,718 en vez de 0,659) más la regla de banda de liquidez. Es la opción 1 de esta reflexión, con números.

**Resolución (ronda 2, D33, `salida/iteraciones/iter_102`).** Se implementa la opción 1 con dos notas y sin pesos escondidos: `HealthScorer(target="adversa")` promedia solo E1-E3 y es la nota publicada; `HealthScorer(target="expansion")` calibra con E4. Fuera de grupo: tensión 0,749 → **0,796** (+2,9 se), juez no circular 0,772 → 0,818, entrada en estrés a 2 meses 0,576 → 0,609; la nota de expansión ordena la expansión con 0,597 (0,638 tras D34) frente a 0,568 de la nota única, **y es la mejor para la caída de cobros (0,635)**. Coste declarado: `auc_deterioro` −0,023 en iter_102 (la serie tiene menos saltos), recuperado en iter_105/107 (0,722 final > 0,717 base). La regla de banda «< 0,5 meses de caja → no sano» que la ronda 1 descartó por la expansión entra en D36 sin coste medible. Queda pendiente servir la nota de expansión en la API/SPA.

## R11 · Bache frente a caída sigue sin resolverse

**Estado:** abierta. AUC 0,53; la regla actual acierta el 74 % solo porque casi todo son caídas.

**Ideas.**
- Caja mínima dentro del mes (medida: AUC 0,79 frente a saldo negativo).
- Cobros que entran después del mes malo.
- Migración entre tramos de mora (30/60/90 días) y tasas de cura.
- Definir el bache con E5 del panel.

## R12 · Alertas que se encienden y se apagan

**Estado:** propuesta.

- **El 23 % de las alertas parpadea** (se enciende y se apaga).
- **Histéresis:** exigir dos meses seguidos para encender una alerta y otros dos para apagarla. Cuesta un mes de antelación.
- **Siguiente paso:** medirlo con `src/anticipation.py`.

## R13 · Modelos generativos (TimeGPT, VAE, DeepAR)

**Estado:** abierta.

**Ideas.**
- Clasificador generativo por evento.
- Un VAE sobre las trayectorias.
- DeepAR o TimeGPT para simular trayectorias futuras y leer la nota como probabilidad de acabar por debajo de un umbral.

**Límite.** R09 indica que la información disponible pone el techo. Un modelo más potente difícilmente sube el AUC. Donde sí podría aportar es en los intervalos y en simular escenarios.

**Requisitos.** TimeGPT necesita una clave de Nixtla y aceptar que los datos salgan a un servicio externo.

## R14 · Empresas del test fuera de distribución

**Estado:** decidida en parte.

**Lo que ya hacemos.**
- Regla congelada del train.
- Los percentiles ya acotan cualquier valor extremo entre 0 y 100. Los valores fuera del rango 0,5-99,5 % del train se marcan en `ood_features` (D16).
- Un dato ausente cuenta como 50 (neutro).
- `coverage` y `ood_share` bajan la confianza de la nota.
- Con menos de 3 meses de historia, la trayectoria usa AR(1) como respaldo.

**Pendiente.** Comprobar qué pasa con empresas grandes fuera del rango del train (R03) y con historia muy corta. Preguntar si el test se parece al train (pregunta 3 de la síntesis).

## R15 · Efecto de borde en agosto de 2026

**Estado:** abierta.

**Lo medido.** Agosto de 2026 tiene el doble de caídas que la media y un 25 % menos de facturas sincronizadas. Además, el 36 % de los apagados cae en julio de 2026.

**Opciones.**
- Excluir los dos últimos meses de las etiquetas.
- Marcarlos como de baja confianza.

## R16 · Entre quien tiene deuda, la carga no ordena el riesgo

**Estado:** abierta (medido en `salida/iteraciones/iter_005`).

**Lo medido.** Con `runway` 0,3-0,7: sin deuda, unión adversa 25,8 % (nota 55,4); deuda < 10 % de las entradas, 34,5 % (51,6); deuda ≥ 10 %, **34,2 % (39,1)**. La deuda pesada cobra −12 puntos frente a la ligera con la misma tasa de eventos. Entre las 8 632 filas con deuda, `debt_burden` tiene AUC 0,462 / 0,440 / 0,479 frente a tensión / incumplimiento / caída (más carga → *menos* eventos). La señal vive en «tiene cuotas o no» (binaria: AUC 0,615 frente a incumplimiento, contra 0,592 de la continua).

**Probado y descartado.** `has_debt` binaria (sin deuda 100, con deuda 50): incumplimiento +0,028 OOF, pero los cuatro guardarraíles de trayectoria empeoran a la vez (la nota salta 100 → 50 al aparecer la primera cuota), la tensión del 20 % peor baja y el sesgo de tamaño pasa de −0,014 a −0,058.

**Opciones.** (1) Aplanar el percentil de los positivos con transición suave (p. ej. sub-score = 100 − 50·min(1, carga/0,02)). (2) Carga de deuda relativa a la **caja** (`debt3 / cash_end`) en lugar de a las entradas. (3) Dejarlo: el efecto sobre la PM es pequeño.

**Resolución (ronda 2, D35, `iter_105`).** El hueco no estaba en la feature sino en la **etiqueta**: el 49 % de los positivos de `incumplimiento_6m` venían solo de la cuota de deuda, que va al revés (más caja y menos carga → más «impago»: `runway` 0,404, `debt_burden` 0,339, `debt3/cash` 0,314), el 43 % vuelve a pagar en 6 meses, la caja no cae y solo el 3 % de las empresas tiene calendario de cuotas (Q8). Con la cuota fuera de E2, `debt_burden` queda en **0,005** de peso (la calibración la apaga sola), P152 pasa (a igual caja, sin deuda ya no vale más: 1,115 → 0,971) y la nota ordena el incumplimiento con 0,624 (0,606 juez + 0,017 modelo). `impago_cuota_6m` se publica aparte como marca no verificable.

## R17 · Premisas del consejo que resultaron incorrectas (fase 3)

**Estado:** decidida (registro; el detalle está en `salida/premisas.jsonl` → `diagnostico` y en `salida/iteraciones/iter_003`, `iter_005`).

Esto es aprendizaje, no fracaso: cada una se contrastó con los eventos antes de tocar código.

| premisa | decía | los datos dicen |
|---|---|---|
| P168 | ninguna fila con caja implausible puede ser sana | son holdings con mucha caja y poco flujo: unión adversa 13 % frente a 32 %; publicarlas sanas es correcto, la confianza ya es menor |
| P157 | ≥ 20 % de flags llegan a sano = rotura | es un hecho, no una rotura: el 63 % de las implausibles son sanas de verdad |
| P159 | ≤ 2 % de sano con confianza < 0,3 | 685 de 688 son los dos primeros meses de cada empresa (`min(1, n/6)`); es un requisito de producto (nota provisional, P191), no de modelo |
| P158 | cobertura < 0,55 no puede subir la nota | composición: las filas con poca cobertura tienen más caja; a igual quintil de caja la nota es igual (D17/D21 se sostiene) |
| P182 | sesgo de arranque +11 % a igual caja | confundida con el calendario: dentro del mismo semestre los meses 0-2 puntúan igual o menos que los 3-12; lo que baja es la cohorte de 2024-09 (R18) |
| P150 | póliza sin usar no debe valer más que no tener póliza | a igual caja, tensión 5,8 % frente a 24,6 %: la póliza disponible es liquidez real (el evento la cuenta) |
| P152 | sin deuda no debe valer más que con deuda | a igual caja, unión adversa 25,8 % frente a 34,5 %; el hallazgo real es otro (R16) |
| P172 | `payroll_burden` debe pesar | tenía el signo contrario a los eventos; la intención (nombrar la nómina ausente) era correcta y se cumple con `payroll_cv` (D28) |
| P177 | AUC directo frente a incumplimiento > 0,44 | documentaba el estado: al mejorar la separación baja de 0,44 y «falla» |
| P008 / P010 (semilla) | volatilidad a la baja y tendencia de actividad anticipan tensión / apagado | ya diagnosticadas en la fase 2 (AUC 0,33 y 0,41); sin cambio |

Y las que son **correctas para el prestamista pero el modelo de una sola nota no puede cumplir** (R10): P120, P122, P173, P175, P176. **Ronda 2:** con dos notas P120 pasa (D36) y P173 se queda a 0,002 de pasar.

**Ronda 2 (rama `autoresearch/2026-09-19-r2`).** Veredictos que cambian y premisas nuevas que resultaron incorrectas o que documentaban el estado:

| premisa | decía | los datos dicen |
|---|---|---|
| **P152 (revocada)** | sin deuda no debe valer más que con deuda | era **correcta**: la etiqueta de incumplimiento premiaba tener deuda (solo quien tiene cuotas puede dejar de pagarlas); con la cuota fuera (D35) pasa (0,971) |
| P150 | la póliza sin usar no debe valer más que no tener póliza | sigue fallando (1,25) también con la etiqueta no censurada; calibrar sin póliza (iter_108) rompe la neutralidad al tamaño. La póliza disponible es liquidez real para el prestamista; **decisión del dueño** |
| P206 | el primer mes sin movimientos publica ≤ 30 | **incorrecta en su literal**: un mes inactivo tiene lift de tensión 0,89 y de caída 2,15; C7 del consejo pide «vigilar», que es lo que hace la nota publicada (0 % sano, máximo 62) |
| P233 | el tope de inactividad no tiene base en la tensión | parcialmente correcta: la base es la caída (×2,15), no la tensión (×0,89) |
| P216 / P226 | tener ERP no debe cambiar la nota a igual caja | parcialmente correctas: ~+1,9 puntos son mecánicos (neutro 50 frente a la media 53-71 de las *zero_best*) y ~+1,1 son señal (menos incumplimiento y caída con ERP a igual caja); el neutro «medio» (iter_106) no mueve eventos y traslada el sesgo a las filas con poca cobertura |
| P327 | ventana fija de 12 meses para la tendencia | remedio medido y descartado (iter_103): cumple el criterio de sesgo (−1,76 → −0,74) pero deja sin dato al 61 % de las filas y la nota de expansión cae 0,05 |
| P330 | `activity_trend` solo suma a expansión con euros ≥ 0 | correcta en el fondo, no en el remedio: el gate no aporta (0,605 = 0,605); la señal de euros está en los cobros operativos 3m/12m (0,649), que entran como `oper_growth_12m` (D34) |
| P002, P148, P203, P112, P113, P143, P144, P146, P147, P155, P163, P192, P283, P025, P179, P224 | umbrales que describían las etiquetas viejas o umbrales al filo | fallan por construcción tras D32/D35 o oscilan ±0,01; anotadas en `premisas.jsonl` como «documentaba el estado» / «umbral frágil» |
| `docs/eventos.md:3` (dueño) | «usamos `tension_np_raw` (caja propia) como estrés de liquidez» | vale como **juez y para anticipación** (así se usa: 0,807 OOF), no como ancla de calibración: calibrar con ella (iter_108) rompe P180 (Spearman tamaño-nota −0,117) y cuesta caída e impago |

## R18 · La cohorte larga puntúa ~5 puntos menos a igual caja

**Estado:** abierta (hallazgo de `iter_003`).

Con `runway` 0,3-0,7 y dentro del mismo semestre, las empresas con ≥ 13 meses de historia (las 369 que arrancan en 2024-09) puntúan 48-52 frente a 53-56 del resto. Hipótesis: con 12 meses se hacen visibles señales que casi siempre restan (`lost_share`, `hhi_ar_6m`, `growth_vs_12m` con base anual completa), o la cohorte inicial es distinta (más grande, más antigua). Importa para el test oculto: si las 60-80 empresas nuevas llegan con historia completa, se parecerán a esta cohorte.

**Actualización (consejo Q7 + ronda 2, `iter_103`).** El mecanismo está zanjado: **saturación de la ventana de 12 meses** (`features.py:12-14`, `min_samples=1`), no imputación ni cohorte. Intra-empresa, a igual decil de `runway`, la nota adversa cae **−1,76 ± 0,39** puntos entre los meses 10-12 y 13-15 (801 pares; `ec_activity_trend` −0,77). El remedio del consejo (ventana fija `min_periods = 12`) lo reduce a −0,74 pero deja la tendencia sin dato hasta el mes 12 (cobertura 0,88 → 0,39) y la nota de expansión cae de 0,597 a 0,545: **descartado**. Con dos notas el sesgo vive sobre todo en la nota de expansión. Opciones que quedan: `min_samples = 6` (cobertura 0,69), o declarar el sesgo en la ficha de los meses 0-11 (la nota ya es provisional).

## R19 · El suavizado (α) es un dial estabilidad ↔ reacción, no información

**Estado:** decidida (α = 0,5; medido en `salida/iteraciones/iter_109`).

**Lo medido.** Nota adversa fuera de grupo con α ∈ {0,7; 0,5; 0,35; 0,25}: la caja y la anticipación desde sana mejoran de forma monótona al suavizar más (tensión 0,782 → 0,808, entrada a 2 m 0,582 → 0,633) y el incumplimiento empeora (0,629 → 0,605): la nómina que falta es una señal brusca. Ninguna diferencia supera 1,5 se. Los guardarraíles de trayectoria «mejoran» mucho (deterioro 0,722 → 0,787, skill ×3) con la referencia AR(1) plana: es la predictibilidad de un filtro más lento (saltos ≥ 15 a 3 m 22 % → 9 %), no más información. Costes: la nota cae −7,3 (α 0,35) o −5,5 (α 0,25) en los dos meses hasta el arranque confirmado de la tensión, frente a −10,4 con α 0,5; con α 0,35 cuatro meses inactivos se publican «sanos» (P019) porque el tope 30 se aplica al bruto; la cura también se ve más tarde (P252 0,91 → 0,85).

**Consecuencias.** (1) α se queda en 0,5. (2) Los guardarraíles de trayectoria **solo comparan cambios con α fijo**. (3) Si el producto prefiere una nota más estable, hay que mover el tope de inactividad a la nota suavizada (como la regla de liquidez, D36) y aceptar −30 % de reacción.

## R20 · Dentro de la nota adversa, liquidez ↔ impago/caída

**Estado:** abierta.

Resuelto el trade-off con la expansión (D33), queda uno más suave dentro de la nota adversa: cada cambio que la hace «más caja» cuesta impago y caída, y al revés. Medido tres veces en la ronda 2: sacar la cuota de E2 (iter_105: incumplimiento +0,017 de modelo, caída +0,020, tensión −0,010, juez no circular −0,018); calibrar con la caja propia (iter_108: tensión +0,018, entrada +0,026, pero incumplimiento −0,016, caída −0,013 y P180 rota); los topes duros de liquidez (iter_107: tensión +0,04, incumplimiento −0,015, caída −0,013, circulares con la etiqueta).

**Lectura.** Una nota que debe cubrir tensión, impago y caída no puede ser solo caja. La liquidez pura ya está en la ficha (`runway`, `mc`), en la regla de banda (D36) y en los vetos C1/C2/C4 (fase 4). **No** se propone una tercera nota: se propone que el prestamista lea nota adversa + vetos, y que la aseguradora / el CFO lean la nota de expansión (que también es la mejor para la caída).

---

## Hoja de ruta propuesta (v7)

1. **Eventos.** Sacar el apagado de la calibración, implementar E1 y E3-E4 y rehacer E2 más estrecho (R05, R06).
2. **Caja fiable.** Diagnosticar el descuadre y marcar las empresas cuya caja no es fiable (R08).
3. **Recalibrar pesos** contra los eventos nuevos y rehacer la validación fuera de grupo.
4. **Escala absoluta** anclada a probabilidad, con bandas fijas (R01, R02).
5. **Features:** probar los percentiles por tamaño (R03) y añadir las del brainstorming de una en una (R07).
6. **Alertas:** histéresis (R12) y bache frente a caída (R11).
