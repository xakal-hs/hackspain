# Plan de desarrollo por fases — X Ray

**Para el equipo · escrito desde producto · 19-sep-2026**

Este documento dice **en qué trabaja cada persona y en qué orden**, para que nadie
espere a nadie y para que el reloj no nos pille con medio producto abierto.

El estado técnico está en [`research/ESTADO.md`](research/ESTADO.md); las dudas
abiertas, en [`research/REFLEXIONES.md`](research/REFLEXIONES.md). Aquí no se
repiten: esto es el reparto.

---

## La regla que hace que esto sea escalonado

Cada fase termina en un **estado entregable**. No en «código avanzado»: en algo que
se puede presentar tal cual.

Una fase está cerrada cuando se cumplen las tres a la vez, y se verifica en diez
minutos:

1. **La demo arranca de cero y se navega** sin tocar código ni explicar nada.
2. **Hay una submission válida** en el leaderboard.
3. **El guion de cinco minutos cuenta la historia con lo que hay hoy**, sin
   prometer lo que falta.

**No se empieza una fase sin la anterior cerrada.** Si el tiempo aprieta, se
recorta el alcance de la fase en curso hasta que cierre; nunca se deja a medias
para avanzar a la siguiente. Al cerrar cada fase se mergea a `main` y se etiqueta.

Las cuatro fases no son cuatro trozos distintos del producto: son **el mismo
producto, cada vez más hondo**. Las tres patas que puntúan (el score, la
anticipación y el producto vendible) están presentes desde la fase 0. Por eso
parar en la fase 2 deja algo coherente y no un esqueleto.

| Fase | Qué significa | Si el reloj se para aquí, enseñamos |
|---|---|---|
| **F0** | Existe | Score en leaderboard, demo que abre, producto con comprador y cifra |
| **F1** | Aguanta preguntas | Lo anterior, y el número resiste al jurado técnico |
| **F2** | Se usa | Lo anterior, y una decisión de crédito completa sobre una empresa nueva |
| **F3** | Convence | Lo anterior, ensayado, con plan B y sin aristas |

---

## Quién es quién

Deducido del historial del repositorio. Si algo no encaja con lo que cada uno
quiere hacer, se cambia: el reparto sirve para no pisarnos, no para encasillar.

| Persona | De dónde viene, según el repo | Su terreno |
|---|---|---|
| **Álvaro** (`balalo`) | `xray.py`, `targets.py`, `evaluate.py`, `predict_submission.py`, los workflows de `.devin/` | **El motor.** Score, eventos, previsión, submission |
| **Andrés** | Capa de mapeo, informe exploratorio, ERD, catálogo de features, `context/scoring.md` | **Datos y evidencia.** Features, validación, métricas, el marco del prestamista |
| **César** | `app/DESIGN.md`, skills de frontend, README | **La demo.** SPA, lenguaje visual, que aquello abra |
| **Manel** | Histórico de caja, `monetizacion.py`, productos financieros sobre el score | **Producto y pitch.** Qué se vende, a quién, por cuánto |

---

## Fase 0 · Existe — el seguro de entrega

**Unas 3 horas. Es la única fase innegociable.** Al acabarla tenemos una entrega
completa aunque modesta, y a partir de ahí todo es mejora, no rescate.

### Álvaro — la submission, de punta a punta

Es lo primero del día porque es **binario**: o nuestra fila está en el leaderboard
o no está, y no lo sabremos hasta intentarlo. Hoy `predict_submission.py` existe
pero no hay rastro de que haya corrido contra los CSV reales del test.

- Descargar el test oculto y el script de scoring, correr
  `predict_submission.py --csv-dir <test> --out submission` y **validar el formato
  exacto que espera el script**, no el que suponemos.
- Subir una primera puntuación aunque sea mediocre. La nota se mejora después; el
  formato roto a las once de la noche no se arregla.
- Dejar el comando exacto en `research/README.md`.

**Hecho cuando:** hay una fila nuestra en el leaderboard y cualquiera del equipo
puede reproducir la submission con un comando copiado.

### César — que la demo abra en una máquina limpia

Ahora mismo `data/` y `artifacts/` están en `.gitignore`, y arrancar son seis
pasos encadenados. Uno de ellos, `fx.py`, **sale a internet** a por los tipos de
cambio: si el wifi del aula falla, no hay demo.

- Un único `research/run_demo.sh` que haga ingest → fx → panel → service →
  decisions → uvicorn.
- **Cachear los tipos de cambio en disco** y versionarlos, para que el arranque no
  dependa de la red.
- Cinco líneas en el README: clonar, un comando, abrir el navegador.

**Hecho cuando:** en un portátil que no es el tuyo, sin wifi, sale la demo.

### Andrés — que la SPA no enseñe números viejos

La pestaña de métricas sirve `reports/metrics_app.json`, que va por iteraciones
**hasta la v6**. El modelo vivo es la v7. Es decir: hoy le enseñaríamos al jurado
unas métricas que no son las del modelo que estamos presentando.

- Regenerar `decisions.json` y `metrics_app.json` con la v7.
- Actualizar `METRICS.md` y `research/README.md`, que siguen describiendo eventos
  v1 y resultados v6.

**Hecho cuando:** lo que se ve en pantalla coincide con `metrics_v7.json`.

### Manel — el guion, escrito

- `context/pitch.md`: minuto a minuto, qué pantalla se enseña y qué se dice
  encima. Quién compra, qué ve, qué decide.
- Las cifras salen de `context/monetizacion.md`, no de la cabeza.

**Hecho cuando:** otra persona del equipo puede dar el pitch leyéndolo.

> **Corte limpio F0** — Score que puntúa en empresas nunca vistas, señal en las dos
> direcciones, trayectoria, explicación, producto con comprador identificado y demo
> navegable. Los siete requisitos obligatorios del enunciado, cubiertos.

---

## Fase 1 · Aguanta preguntas — la credibilidad del número

**Unas 5 horas.** Aquí atacamos lo que el jurado va a preguntar y hoy no está
resuelto. Las dos primeras tareas no son perfeccionismo: son **literalmente
criterios del enunciado**.

### Álvaro — bache o caída, y que el monitor deje de parpadear

- **Bache frente a caída está en AUC 0,53**, o sea, una moneda al aire. Es la
  pregunta 4 del reto y el criterio «Estabilidad» de la evaluación. Camino
  propuesto: persistencia de la señal (meses consecutivos por debajo del umbral) y
  recuperación de caja a dos meses como discriminante, medido en `anticipation.py`.
- **El 23 % de las alertas se enciende y se apaga.** Histéresis: umbral distinto
  para encender que para apagar, y mínimo de dos meses antes de cambiar de estado.
  Esto se ve en vivo durante la demo, así que se nota mucho si sigue.

**Hecho cuando:** bache-vs-caída por encima de 0,65 y parpadeo por debajo del 10 %,
con el número en `METRICS.md`.

### Andrés — la antelación, medida y en pantalla

Es **bonus explícito** del enunciado y el titular más vendible que tenemos: «lo
vimos venir con N meses». El dato actual (48 % de las caídas, mediana 3 meses) es
de la v5/v6.

- Regenerar antelación con la v7 y publicarla en la UI como titular, no escondida
  en una tabla.
- Si sobra tiempo: meter las features del brainstorming que ya tienen señal
  (`payee_concentration`, `lost_accel`, `payroll_cv`, `hhi_ap_6m`,
  `oper_persistence_6m`) **de una en una**, con ficha de evidencia. Entra solo la
  que mejore el AUC out-of-fold y no rompa la monotonía.

### César — las seis preguntas, literales, en la ficha de empresa

El reto se evalúa contra seis preguntas. Que la ficha las responda **con esas
mismas palabras** (sano / mejora / se tuerce / bache o caída / por qué / cuándo se
vio venir) le ahorra al jurado el trabajo de buscar dónde está cada cosa.

### Manel — primer ensayo cronometrado

Con lo que haya. El objetivo no es que salga bien: es descubrir qué sobra.

> **Corte limpio F1** — El motor resiste el interrogatorio técnico y la anticipación
> está medida. Bonus cubierto.

---

## Fase 2 · Se usa — el producto deja de ser una pantalla

**Unas 5 horas.** Un producto cerrado vale más que tres esbozados.

### Manel y César — un solo producto, de punta a punta

Recomendación: **la línea de circulante con límite y precio recalculados cada
mes**, porque ya hay `/api/products/*` funcionando contra el HealthScorer real.

La pantalla tiene que decir cuatro cosas: **cuánto** financiamos, **a qué precio**,
**por qué ese precio** y **cuándo reducimos exposición**. El precio sale del score y
se mueve con él; ahí está el argumento de venta.

### Álvaro — la demo proactiva

Cuatro a seis empresas nuevas que no están en el dataset, puntuadas con el modelo
vigente **sin reentrenar** (el guion está en `.devin/workflows/autoresearch/fase4_demo.md`).
El momento que cierra el pitch: *«tres empresas nuevas van a necesitar deuda; esta
necesita factoring, score X, por Y, Z y K»*. Prueba generalización y producto en la
misma frase.

### Andrés — la explicación, en castellano

Para las tres empresas que salen en el pitch, que el «por qué» se lea sin jerga.
Una caja negra no vale para prestar, y un tecnicismo tampoco.

> **Corte limpio F2** — El jurado ve una decisión de crédito completa sobre una
> empresa que el modelo no había visto nunca.

---

## Fase 3 · Convence — artesanía y ensayo

**Unas 4 horas, y no se recortan.** El enunciado lo dice sin rodeos: si en cinco
minutos no queda claro quién compra y por qué, la propuesta está incompleta.

- Tres ensayos cronometrados. Con reloj de verdad.
- **Plan B offline**: vídeo y capturas de las cuatro pantallas del guion, por si la
  demo no arranca delante del jurado.
- Móvil y modo oscuro, estados vacíos, y que ninguna de esas cuatro pantallas tarde
  más de un segundo.
- La sala de situaciones (`fase4_demo.md`), **solo si la F2 cerró**.

**Congelación a T-2h:** nadie toca `research/src/` ni `index.html`. Las dos últimas
horas son para ensayar, no para programar.

---

## Lo que no vamos a hacer

Por si a alguien le pica. Todo esto es correcto y ninguna de las dos cosas puntúa
este fin de semana:

| No hacer | Por qué |
|---|---|
| La reestructura del repo (`.devin/workflows/reestructura/`) | Es deuda técnica bien diagnosticada, pero no suma un punto en la rúbrica. El lunes |
| Unificar las dos reconstrucciones de caja, los dos entornos, las features en tres sitios | Igual. Para la demo, la canónica es `research/src`, y se dice en una línea del README |
| Un modelo más grande | Ya está medido: una logística y un LightGBM dan el mismo AUC. El límite está en la información, no en el modelo |
| Enseñar el Streamlit de `analysis/app.py` en el pitch | Hay dos apps; el jurado ve una |
| Features nuevas sin evidencia out-of-fold | Entra la que mejora el número. Las demás, a `REFLEXIONES.md` |

---

## Para no pisarnos

`research/app/static/index.html` son 1.846 líneas en un único fichero: si lo tocan
dos personas a la vez, se pierde media hora en un conflicto.

| Fichero | Lo escribe |
|---|---|
| `research/src/xray.py`, `targets.py`, `evaluate.py`, `predict_submission.py`, `proactive.py` | Álvaro |
| `research/src/features.py`, `anticipation.py`, `analysis/*`, `reports/*`, `METRICS.md` | Andrés |
| `research/app/static/index.html`, `DESIGN.md` | **Solo César** |
| `analysis/monetizacion.py`, `context/*` | Manel |

- A César se le pasa **el contrato de datos** (`API_CONTRACT.md`), no el HTML.
- `research/app/server.py` lo tocan tres personas: endpoints nuevos **al final del
  fichero** y un PR pequeño por endpoint.
- Ramas cortas, PR pequeño, merge el mismo día. Nada de ramas de ocho horas.

---

## Los cinco riesgos, con dueño

| # | Riesgo | Dueño | Cuándo |
|---|---|---|---|
| 1 | La submission nunca se ha probado contra el test real. Es binario | Álvaro | F0 |
| 2 | La demo depende de la red y de artefactos no versionados | César | F0 |
| 3 | La SPA enseña métricas de la v6 con un modelo v7 | Andrés | F0 |
| 4 | Bache frente a caída en 0,53: el jurado preguntará justo por eso | Álvaro | F1 |
| 5 | El 23 % de alertas parpadea, y se ve durante la demo | Álvaro | F1 |

---

## El calendario

Las horas son estimaciones y suponen la presentación el domingo a mediodía;
ajústalas al reloj real. Lo que no se mueve es **el orden** y la regla de no
empezar una fase con la anterior abierta.

| Bloque | Fase | Estado al terminar |
|---|---|---|
| ahora → +3 h | F0 · Existe | Entregable completo |
| +3 h → +8 h | F1 · Aguanta preguntas | Entregable creíble |
| +8 h → +13 h | F2 · Se usa | Entregable vendible |
| +13 h → T-2h | F3 · Convence | Entregable ensayado |
| T-2h → demo | Congelado | Solo ensayo |
