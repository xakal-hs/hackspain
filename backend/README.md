# backend · el score X-Ray

Seis ficheros, y el primero es el ETL: desde los CSV del reto todo está aquí dentro.
El modelo es un **scorecard aditivo**: media ponderada de 17 percentiles,
suavizada con EWMA. No es una caja negra, y esa es la decisión de producto central — la nota
se descompone al céntimo en las features que la movieron. Encima va una capa de **vetos**,
que son hechos de hoy y mandan sobre la nota.

| fichero | qué hace |
|---|---|
| `etl.py` | CSV crudos → `data/panel.parquet`: una fila por (empresa, mes) |
| `preprocessing.py` | panel → 17 features (polars) + eventos + vetos |
| `predict.py` | `fit` → percentiles → pesos → escala → EWMA. `score_panel`, `explain` |
| `decision.py` | de la nota a prestar / vigilar / no prestar. Los vetos y su evidencia |
| `metrics.py` | validación fuera de grupo, AUC por evento, bootstrap pareado, anticipación |
| `main.py` | FastAPI para el frontend Nuxt |

```bash
cd backend
uv run --project ../research python etl.py                # CSV → panel (12 s)
uv run --project ../research python predict.py            # entrena e imprime pesos y bandas
uv run --project ../research python decision.py           # informe de vetos
uv run --project ../research python metrics.py           # validación completa (~3 min)
uv run --project ../research uvicorn main:app --port 8000
```

---

## 1 · De dónde salen los datos

```
output_hackspain_data.zip
  └─ output/*.csv                 8 ficheros, los del reto
      └─ etl.py ingest            → data/*.parquet        las mismas tablas
          └─ etl.py panel         → data/panel.parquet    21.538 × 49
              └─ preprocessing.py → features + eventos + vetos
```

`etl.py` lee de `output/` y **rechaza los punteros LFS** de `data/` del repo (ahí
`invoices.csv` y `transactions.csv` son punteros de 134 bytes que se leerían como CSV vacíos
sin avisar). Verificado al regenerar: 2.556.437 transacciones, 897.894 facturas, 7.996
saldos, 1.286 empresas, 250 grupos.

Tres cosas que el ETL hace y no son obvias:

- **La caja histórica no existe en el dataset.** `balances.csv` es solo la foto de 2026-09;
  el saldo de cada mes se reconstruye hacia atrás producto a producto, restando los flujos
  posteriores, y se **redondea a céntimos**: sin redondear, las cuentas que vuelven a cero
  quedan en ±1e-13 y cambian el signo de «caja negativa» entre ejecuciones.
- **Los tipos de cambio son reales**, descargados del BCE y de currency-api. El tipo del
  fichero se acepta solo si está a ±10 % del real (98,7 % de los casos); el resto viene con
  `fx = 1` o `0`. `to_eur` existe porque los umbrales absolutos (centinelas > 1e8) hay que
  medirlos en EUR: en moneda cruda, 478 de las 491 transacciones > 1e8 son AOA/COP/VND/CLP.
- **La disciplina de facturas se recalcula mes a mes**, no sobre la foto final: cada cierre
  ve solo las facturas ya emitidas. Es el bucle que hace que el ETL tarde 12 s en vez de 1.

Panel: **21.538 empresa-mes**, 2024-09 → 2026-08. Reproducible salvo ~1e-16 en `hhi_ar_6m` y
`lost_share`, que es el orden de suma multihilo de polars y no afecta a ninguna nota.

---

## 2 · La decisión más importante: qué es «estrés de liquidez»

El ancla que calibra los pesos es **la tensión con la caja propia** (`tension_np_raw_6m`),
no caja + póliza. Es la directiva de `docs/eventos.md:3`, y sumar la póliza tenía dos
problemas:

1. **Premiaba estar endeudado.** Cuanta más póliza tienes dispuesta, más «liquidez» se te
   contaba, más sano parecías y más te queríamos prestar. Al revés de lo que debe hacer un
   prestamista.
2. **No predecía nada en el 65,6 % de los casos**, porque la empresa ya estaba en tensión.

Medido con bootstrap pareado (mismos grupos remuestreados en los dos brazos). Los valores
absolutos de esta tabla y de las dos siguientes son de la validación **anterior** (la que veía
el futuro de los demás, §3); el cambio de ancla se midió antes de corregir el método. Las
diferencias se sostienen con la validación nueva — el ancla de caja propia da 0,848 frente a los
0,833 de aquí — pero los números de §4 son los buenos.

| juez | caja + póliza | **caja propia** | σ pareadas |
|---|---:|---:|---:|
| `tension_np_raw_6m` (juez limpio) | 0,800 | **0,833** | **+10,3** |
| `entrada_estres_2m` (anticipación) | 0,597 | **0,621** | **+5,0** |
| `tension_6m` (la etiqueta vieja, con póliza) | 0,785 | **0,803** | **+4,7** |
| `rompe_caja_2m` | 0,609 | **0,632** | **+2,7** |
| `recaida_6m` | 0,521 | 0,533 | +2,0 |
| `incumplimiento_6m` | 0,633 | 0,617 | −2,2 |
| `impago_ap_6m` | 0,568 | 0,558 | −2,1 |

Que **suba incluso la etiqueta vieja** (+4,7σ) es la prueba de que no es un juez que se
premia a sí mismo: el ancla de caja propia es sencillamente mejor profesora.

**La prueba más limpia está en los pesos.** Al quitar la póliza del ancla:

| feature | con póliza | caja propia |
|---|---:|---:|
| `runway` (meses de caja) | 0,213 | **0,271** |
| `lc_util` (uso de la póliza) | 0,100 | **0,023** |
| `debt_burden` | 0,000 | 0,026 |

`lc_util` pesaba porque la etiqueta **contenía la póliza**: la feature estaba prediciendo
una parte de sí misma. Quitada la circularidad, el peso se va a la caja de verdad.

**El precio, declarado.** La neutralidad al tamaño empeora: Spearman(tamaño, nota) pasa de
−0,132 a −0,199. Las empresas grandes tienen diez veces menos meses de caja, así que un
ancla de caja propia las castiga más. Es un trade-off real, no un efecto secundario que se
pueda esconder, y la vía para arreglarlo (percentiles por tramo de tamaño) sigue abierta.

### Lo que se midió y NO se cambió

| propuesta (`docs/eventos.md`) | medido | decisión |
|---|---|---|
| caída → `caida_3m_corto` como ancla | +3,6σ en su propio juez, **−5,3σ en mora AP** | descartado |
| crecimiento → `expansion_3m` como ancla | **0,000** sobre la nota adversa (no la calibra); empate en la de expansión (0,631 → 0,622) | descartado |
| percentiles por mes calendario | con el ancla nueva, ≤ 0,005 de AUC en todo. Con el ancla vieja daba +0,017/+0,025/+0,033 | **descartado — y explica por qué**: aquella «estacionalidad» era en gran parte un parche al ancla mal puesta. No queda código de la opción |

---

## 3 · Cómo se mide

**AUC**: probabilidad de que, cogiendo una empresa que sufrió el evento y otra que no, la
nota ordene bien el par. Se usa AUC y no precisión porque no hay umbral fijo: el prestamista
decide dónde corta.

**Fuera de grupo**: se esconden **grupos empresariales completos**. Una matriz y su filial
comparten tesorería y se filtrarían la respuesta.

**Fuera del futuro, y también del futuro de los demás**: un scorer por **(fold, mes)**, ~120
ajustes. Para puntuar el mes `m`, percentiles, pesos y escala se reconstruyen solo con los
grupos de train y solo con meses ≤ `m`.

Esconder grupos no basta, y esta fue una corrección de método sobre la versión anterior. Una
referencia de percentiles construida con los 24 meses ya le cuenta al modelo **cómo se va a
distribuir el año siguiente**, y en este panel eso no es inocuo: la nota media de la cartera
cae de 54,5 a 49,3 en dos años. Medido en pareado, quitar ese futuro **no baja el AUC, lo
sube** donde importa:

| evento | veía el futuro | **solo el pasado** | σ pareadas |
|---|---:|---:|---:|
| `tension_6m` | 0,803 | **0,822** | **+2,9** |
| `tension_np_raw_6m` (ancla) | 0,833 | **0,848** | **+2,4** |
| `caida_6m` | 0,607 | 0,572 | **−2,3** |
| `incumplimiento_6m` | 0,617 | 0,588 | −1,4 |

Una referencia de percentiles es una **distribución marginal**, no una respuesta: lo que se
aprende del futuro es «cuánto runway suele tener una empresa», y los cuantiles de 10.000
valores ya son casi los de 21.000. La fuga sería grave si el modelo aprendiera el desenlace de
esas filas; aquí aprendía la forma de la nube. Se quita igual, porque es indefendible ante un
jurado y porque la alternativa sale gratis.

**Error típico por grupo**: bootstrap remuestreando grupos enteros, 200 réplicas. El `se` iid
es 2-4× menor y te haría celebrar ruido.

**Al comparar dos modelos, bootstrap pareado**: los mismos grupos en los dos brazos, midiendo
la distribución de la **diferencia**. Dividir por el `se` de cada AUC aislada es el error
clásico — la incertidumbre es casi toda común y se cancela al restar, así que una mejora real
de 5σ parece de 1.

---

## 4 · Los números

Todos salen de la misma validación: fuera de grupo, fuera del futuro, sobre las **20.547
filas activas** puntuadas por un scorer que no vio ni el grupo ni el mes.

### 4.1 · Las cuatro anclas (la cifra oficial)

| evento | qué significa | AUC | se | n | positivos |
|---|---|---:|---:|---:|---:|
| `tension_np_raw_6m` | tensión de liquidez con caja propia (< 0,25 meses de gasto, ≥2 de 3 meses) | **0,848** | 0,014 | 10.926 | 4.822 |
| `incumplimiento_6m` | deja de pagar nómina 2 meses o IVA 2 trimestres | **0,588** | 0,029 | 6.263 | 408 |
| `caida_6m` | caída estructural de cobros (< 50 % de su mediana anual) sin rebote | **0,572** | 0,026 | 5.583 | 552 |
| `expansion_6m` | expansión sostenida y autofinanciada | 0,506 | 0,033 | 8.013 | 468 |

**PM = 0,629** (media de los cuatro). Se reporta, no decide: promediar esconde que un cambio
mejore la tensión y estropee la caída. Y **no es comparable** con los PM anteriores (0,658,
0,659), porque cambió una etiqueta *y* cambió la validación.

La lectura honesta de esta tabla es que **el modelo sabe de liquidez y poco más**. 0,848 en
tensión es fuerte; 0,506 en expansión es azar. Detectar que una empresa va a crecer con datos
de tesorería es un problema distinto y no resuelto — por eso hay una segunda nota (§4.4) y por
eso no se publica probabilidad de expansión.

### 4.2 · El precio del arranque en frío

Los primeros meses no tienen aún eventos a 6 meses observados, así que el scorer se queda con
los **pesos a priori del prestamista** (`PRIOR_W`). No se excluyen esas filas: es literalmente
lo que haría el sistema con una cartera nueva, y conviene saber cuánto vale.

| evento | frío (< 2025-05, 4.401 filas) | calibrado (16.146 filas) |
|---|---:|---:|
| `tension_np_raw_6m` | **0,848** | **0,848** |
| `incumplimiento_6m` | **0,464** | 0,613 |
| `expansion_6m` | **0,401** | 0,528 |

El resultado más útil de todo el README: **con pesos a priori la liquidez se ordena igual de
bien (0,848 = 0,848), y el incumplimiento y la expansión no se ordenan en absoluto** (0,464 y
0,401, peor que una moneda). El juicio experto acierta en qué manda la caja y se equivoca en
todo lo fino: `payroll_cv` pesa 0,029 a priori y 0,148 calibrado, y es justo la feature que
predice el incumplimiento.

Traducido a producto: a una empresa nueva se le puede dar nota de liquidez desde el mes 1, pero
la parte de disciplina de pagos hay que ganársela con historia.

### 4.3 · Los 14 jueces (se miden, nunca calibran)

| evento | AUC | se | n | positivos |
|---|---:|---:|---:|---:|
| **`tension_np_raw_6m`** (ancla y juez limpio) | **0,848** | 0,014 | 10.926 | 4.822 |
| `tension_6m` (la vieja, con póliza) | 0,822 | 0,013 | 8.453 | 3.000 |
| `tension_grupo_6m` (diagnóstico de grupo) | 0,700 | 0,026 | 13.000 | 5.472 |
| **`rompe_caja_2m`** (anticipación dura) | **0,656** | 0,034 | 9.198 | 62 |
| **`entrada_estres_2m`** (anticipación) | **0,637** | 0,021 | 9.198 | 550 |
| `impago_iva_6m` | 0,599 | 0,046 | 4.637 | 123 |
| `incumplimiento_6m` | 0,588 | 0,029 | 6.263 | 408 |
| `impago_ss_6m` | 0,578 | 0,049 | 4.400 | 230 |
| `caida_6m` | 0,572 | 0,026 | 5.583 | 552 |
| `recaida_6m` | 0,566 | 0,024 | 649 | 494 |
| `tension_entrada_6m` | 0,562 | 0,041 | 5.918 | 130 |
| `impago_ap_6m` (mora crónica, 60 % de las filas) | 0,538 | 0,031 | 8.595 | 5.106 |
| `caida_3m_corto` | 0,538 | 0,013 | 14.260 | 2.513 |
| `impago_nomina_6m` | 0,526 | 0,050 | 3.563 | 347 |
| `expansion_3m` (con la nota adversa) | 0,519 | 0,018 | 14.260 | 2.302 |
| `expansion_6m` (con la nota adversa, que no es su trabajo) | 0,506 | 0,033 | 8.013 | 468 |
| `impago_cuota_6m` | **0,408** | 0,040 | 2.688 | 376 |
| `cura_3m` | **0,325** | 0,022 | 16.986 | 442 |

Las dos últimas están por debajo de 0,50 y no es un bug:

- **`impago_cuota_6m` ordena al revés.** Sin calendario de cuotas (3 % de cobertura) no se
  distingue un impago de un vencimiento o un cambio de periodicidad: el 43 % vuelve a pagar
  en 6 meses y la caja no cae. Por eso la cuota salió del evento de incumplimiento. Es una
  etiqueta mala, no un modelo malo — y lo mismo la degrada de veto a aviso (§5).
- **`cura_3m` es mecánico**: para curarte tienes que estar enfermo, y los enfermos tienen
  nota baja. Se deja en la tabla por transparencia.

### 4.4 · Dos notas, no una

Las mismas 17 features con los pesos calibrados contra la cara positiva. Promediar los pesos
de la tensión con los de la expansión dejaba la caja sin peso.

| evento | nota adversa | **nota de expansión** | expansión, solo meses calibrados |
|---|---:|---:|---:|
| `expansion_6m` | 0,506 | **0,583** (se 0,032) | **0,610** |
| `expansion_3m` | 0,519 | 0,553 | 0,566 |
| `tension_np_raw_6m` | 0,848 | 0,694 | 0,604 |

La tercera columna existe por honestidad: en los meses de arranque en frío la nota de expansión
cae a `PRIOR_W`, que son **pesos adversos**, y por eso aparece ordenando tensión (0,694). Con
historia suficiente se separa de verdad: 0,604 en tensión, casi azar, que es lo que debe. Se ve
en sus pesos — la manda `oper_growth_12m` (0,317) y `runway` pesa **0,000**.

### 4.5 · Anticipación

Medida contra el **estado mensual** de estrés (`estres_mes`), no contra las etiquetas `*_6m`:
esas ya son ventanas futuras y regalarían hasta 6 meses de ventaja ficticia. Solo cuentan las
349 empresas que empiezan sanas y entran en estrés. Aviso = la nota baja de 35.

| | veía el futuro | **solo el pasado** |
|---|---:|---:|
| filas avisadas (del total activo) | 21,8 % | 25,3 % |
| cobertura (avisadas / entradas) | 9,5 % | **18,6 %** |
| mediana de antelación | 4 meses | **4 meses** |
| avisadas con ≥ 2 meses | 70 % | **83 %** |

La cobertura se duplica, y la primera fila obliga a preguntar si es solo que la nota bajó y
salta más la alarma. No lo es — a **tasa de alarma igualada**:

| % de filas avisadas | veía el futuro | **solo el pasado** |
|---|---|---|
| 10 % | 0,040 · 2 meses | 0,049 · 2 meses |
| 15 % | 0,066 · 2 meses | 0,074 · 3 meses |
| 20 % | 0,092 · 2 meses | **0,135 · 3 meses** |
| 25 % | 0,120 · 3 meses | **0,181 · 4 meses** |

Avisando al mismo número de empresas, la versión honesta **coge un 47 % más de entradas en
estrés y un mes antes**. Refitear la referencia y la escala cada mes hace la nota más sensible
al cambio reciente, que es exactamente para lo que se vende.

Sigue avisando poco en términos absolutos: 18,6 % de cobertura al umbral 35. Bajar el umbral la
sube (27,2 % al umbral 40) a cambio de avisar a un tercio de la cartera. Es la palanca de
producto más clara que queda abierta.

### 4.6 · Probabilidades publicadas

Segunda calibración, sobre la nota **publicada**: una logística de una sola variable. Dos
empresas con la misma nota tienen la misma probabilidad, siempre. Solo se publica si la nota
separa ese evento con AUC ≥ 0,60 — una probabilidad bien calibrada en media pero que ordena
mal es peor que ninguna. Por eso `expansion_6m` no publica probabilidad con la nota adversa.

### 4.7 · El modelo, entero

| feature | peso adversa | peso expansión |
|---|---:|---:|
| `runway` | **0,271** | 0,000 |
| `payroll_cv` | 0,148 | 0,000 |
| `activity_trend` | 0,121 | 0,170 |
| `oper_persistence_6m` | 0,102 | 0,052 |
| `lost_share` | 0,072 | 0,131 |
| `ap_overdue_ratio` | 0,048 | 0,000 |
| `ar_late_share` | 0,042 | 0,054 |
| `hhi_ar_6m` | 0,032 | 0,001 |
| `ap_late_share` | 0,031 | 0,000 |
| `debt_burden` | 0,026 | 0,093 |
| `lc_util` | 0,023 | 0,039 |
| `transfer_dep` | 0,020 | 0,000 |
| `net_vol_6m` | 0,019 | 0,074 |
| `cust_trend` | 0,016 | 0,000 |
| `refund_rate` | 0,014 | 0,044 |
| `ar_overdue_90_ratio` | 0,008 | 0,025 |
| `oper_growth_12m` | 0,006 | **0,317** |

- **Escala**: `nota = −59,80 + 2,10 × compuesto` (P5 → 15, P95 → 85).
- **EWMA** α = 0,5 sobre las contribuciones, no sobre la nota: así la descomposición
  sobrevive al suavizado.

---

## 5 · Los vetos: la capa que decide

La nota ordena el riesgo; **no decide**. Encima van los vetos de `docs/eventos.md:19`, que
son hechos de hoy:

> nota 78 «sano» + este mes no ha salido la nómina que paga siempre → **no prestar**

Separarlos de la nota no es cosmética:

- Un veto es **verificable y discutible**: el CFO enseña el justificante y se cae. Un peso
  dentro de una media ponderada, no.
- Un veto es **asimétrico**: solo bloquea, nunca mejora. Meterlo en la nota obligaría a que
  su ausencia sumase puntos — que es exactamente el error de sumar la póliza a la liquidez.
- La nota mira a 6 meses; el veto mira a este mes.

### Cuáles se ganan el puesto

`lift` = tasa de tensión futura de las filas vetadas / tasa base (0,439).

| veto | filas | lift | sanas vetadas | |
|---|---:|---:|---:|---|
| `veto_caja_negativa` | 706 | **2,17** | 0 | bloquea |
| `veto_poliza_agotada` | 390 | **2,12** | 0 | bloquea |
| `veto_iva_ausente` | 176 | 1,24 | 20 | bloquea |
| `veto_nomina_ausente` | 291 | 1,13 | 22 | bloquea |
| `veto_ss_ausente` | 247 | 1,10 | 26 | bloquea |
| `veto_grupo_en_estres` | 6.748 | 1,67 | 688 | **aviso** |
| `veto_cuota_ausente` | 394 | **0,98** | 52 | **aviso** |

Dos degradaciones, medidas:

- **`veto_grupo_en_estres`** ordena bien (1,67) pero toca el **31 % del panel**. Vetar a un
  tercio de la cartera no es una regla de crédito, es no dar crédito. Y `eventos.md` lo llama
  explícitamente diagnóstico. Mueve a «vigilar», no bloquea.
- **`veto_cuota_ausente`** tiene lift **0,98**: las filas que bloquea no acaban peor que la
  media. Misma conclusión que sacó el council al echar la cuota del evento de incumplimiento.

La caja negativa **no es veto automático**: el 54 % de las rachas se cura en un mes, así que
veta a partir del **segundo mes seguido** (`eventos.md:17`).

Y la calidad de dato no es un veto, es `sin_nota`: saldo centinela, reconstrucción que no
cierra, 2+ meses sin movimientos o menos de 5 apuntes. No se puntúa lo que no se ve.

Reparto del último mes de las 1.286 empresas: **157 prestar · 736 vigilar · 120 no prestar ·
273 sin nota**. Con veto bloqueante: 54. Con aviso: 441.

---

## 6 · La API

| endpoint | qué devuelve |
|---|---|
| `GET /api/companies` | cartera: nota, nota de expansión, acción, vetos, avisos, tendencia |
| `GET /api/companies/{id}` | ficha: serie, pilares, probabilidades, señales, decisión |
| `GET /api/companies/{id}/explain` | Δnota del mes, descompuesto por feature (suma exacta) |
| `GET /api/companies/{id}/decision` | prestar / vigilar / no prestar, con los motivos en texto |
| `GET /api/model` | pesos de las dos notas, escala, anclas, calibración |
| `GET /api/vetos` | catálogo de vetos con su evidencia (`lift`, filas, sanas vetadas) |

---

## 7 · Qué NO hace este backend

- **No hay forecaster.** El `TrajectoryForecaster` (MLForecast + LightGBM cuantílico, bandas
  q10/q50/q90) se quedó fuera, y con él sus métricas (`auc_deterioro` 0,722, `auc_mejora`
  0,757, cobertura 81 %). La API sirve `delta3`: la trayectoria **observada**, nota de hoy
  menos nota de hace 3 meses. Es un hecho, no una predicción. El frontend Nuxt espera
  `delta3_q10/q50/q90`: hay que decidir si se recupera el forecaster o se ajusta el contrato.
- **No hay motor proactivo** (proyección aritmética de caja para factoring/refi).
- **Bache frente a caída** sigue sin resolverse (AUC 0,53 en la versión anterior).
- **La neutralidad al tamaño empeoró** con el ancla nueva (−0,199). Pendiente: percentiles por
  tramo de tamaño.
- La nota es **relativa** a la población de entrenamiento; las `prob_*` dan la escala absoluta.
