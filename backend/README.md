# backend · el score X-Ray

Cuatro ficheros. El modelo es un **scorecard aditivo**: media ponderada de 17 percentiles,
suavizada con EWMA. No es una caja negra, y esa es la decisión de producto central — la nota
se puede descomponer al céntimo en las features que la movieron.

| fichero | qué hace |
|---|---|
| `preprocessing.py` | panel → 17 features (polars) + todos los eventos de `docs/eventos.md` |
| `predict.py` | `fit` → percentiles → pesos → escala → EWMA. `score_panel`, `explain` |
| `metrics.py` | validación fuera de grupo, AUC por evento, bootstrap pareado, anticipación |
| `main.py` | FastAPI para el frontend Nuxt |

```bash
cd backend
uv run --project ../research python predict.py     # entrena e imprime pesos y bandas
uv run --project ../research python metrics.py --temporal
uv run --project ../research uvicorn main:app --port 8000
```

---

## 1 · De dónde salen los datos

Cadena completa, sin pasos manuales:

```
output_hackspain_data.zip
  └─ output/*.csv            8 ficheros, los del reto
      └─ research/src/ingest.py     → research/data/*.parquet
          └─ research/src/panel.py  → research/data/panel.parquet   21.538 × 49
              └─ backend/preprocessing.py  → features + eventos
```

`ingest.py` lee de `output/` y **rechaza los punteros LFS** de `data/` (ahí
`invoices.csv` y `transactions.csv` son punteros de 134 bytes, no los datos).
Verificado al regenerar:

| fichero | filas |
|---|---:|
| transactions | 2.556.437 |
| invoices | 897.894 |
| balances | 7.996 |
| banking_products | 5.987 |
| debt_products | 2.239 |
| companies | 1.286 |
| groups | 250 |
| debt_schedule_config | 87 |

Panel resultante: **21.538 empresa-mes**, 1.286 empresas en 250 grupos, 2024-09 → 2026-08.

---

## 2 · Cómo se mide (y por qué así)

### AUC
Probabilidad de que, cogiendo al azar una empresa que sufrió el evento y otra que no, la
nota ordene bien el par. 0,50 es tirar una moneda; 1,00 es perfecto. Se usa AUC y no
precisión porque **no hay un umbral fijo**: el prestamista decide dónde corta según su
apetito de riesgo, y lo que importa es el orden.

Para eventos adversos la nota ordena al revés (más nota = menos evento), así que se mide
sobre `−nota`. El código lo hace solo (`metrics._oriented`).

### Fuera de grupo (`oof`)
Se esconden **grupos empresariales completos**, no empresas sueltas: una matriz y su filial
comparten tesorería y se filtrarían la respuesta. Un scorer por fold — percentiles, pesos y
escala se reconstruyen **solo** con los grupos de train. Es la simulación del test oculto de
60-80 empresas.

### Origen móvil (`temporal_oof`)
Además de esconder grupos, se congela el reloj en tres cortes (2025-11, 2026-02, 2026-05):
el scorer solo ve meses ≤ corte, y solo calibra con filas cuyo evento a 6 meses **ya había
ocurrido** en ese corte. Es la validación más estricta que hacemos y la que contesta
«¿habría funcionado si lo hubiéramos desplegado entonces?».

### Error típico por grupo (`se`)
Bootstrap remuestreando **grupos enteros**, 200 réplicas. El `se` iid es 2-4× más pequeño y
te haría celebrar ruido. Una diferencia por debajo de ~2 `se` no es un resultado.

### Y al comparar dos modelos: bootstrap **pareado** (`compare`)
Los mismos grupos se remuestrean para los dos brazos y se mide la distribución de la
**diferencia**. Dividir por el `se` de cada AUC aislada es el error clásico: como la
incertidumbre es casi toda común a los dos, se cancela al restar, y una mejora real de
5 sigmas parece de 1. Nos pasó con el experimento de estacionalidad.

---

## 3 · Los números

### 3.1 · Validación de origen móvil — la cifra oficial

Nota en el corte frente a los eventos de los 6 meses siguientes, en grupos que el modelo
nunca vio.

| evento | qué significa | AUC | se | n | positivos |
|---|---|---:|---:|---:|---:|
| `tension_6m` | tensión de liquidez persistente (caja + póliza < 0,25 meses de gasto, ≥2 de 3 meses) | **0,746** | 0,025 | 720 | 257 |
| `incumplimiento_6m` | deja de pagar una obligación recurrente: nómina 2 meses seguidos o IVA 2 trimestres | **0,680** | 0,035 | 1.169 | 78 |
| `caida_6m` | caída estructural de cobros (< 50 % de su mediana anual) sin apagado ni rebote | **0,627** | 0,029 | 1.374 | 155 |
| `expansion_6m` | expansión sostenida y autofinanciada (> 130 % de cobros, caja arriba, sin pelotazo) | 0,583 | 0,038 | 1.560 | 87 |

**PM = 0,659** — la media de esos cuatro. Es la métrica única de comparación entre versiones;
desde la ronda 2 **se reporta pero no decide**, porque promediar cuatro AUC esconde que un
cambio mejore la tensión y estropee la caída.

### 3.2 · Sobre todas las filas activas, fuera de grupo

Más filas y más eventos: aquí entran los **jueces**, etiquetas que se miden pero nunca
calibran los pesos.

| evento | qué significa | AUC | se | n | positivos |
|---|---|---:|---:|---:|---:|
| **`tension_np_raw_6m`** | **el juez limpio**: tensión con la caja **propia**, sin sumar la póliza y sin censurar al grupo. Quita la circularidad con `lc_util`, que es una de las features que puntúan | **0,800** | 0,017 | 10.926 | 4.822 |
| `tension_6m` | la de arriba, sobre todas las filas | 0,785 | 0,016 | 8.453 | 3.000 |
| `tension_grupo_6m` | tensión agregada del grupo. Diagnóstico: no sustituye a la nota de la entidad | 0,670 | 0,026 | 13.000 | 5.472 |
| `impago_iva_6m` | falta el IVA dos trimestres seguidos | 0,635 | 0,056 | 4.637 | 123 |
| `incumplimiento_6m` | nómina o IVA | 0,633 | 0,028 | 6.263 | 408 |
| `impago_ss_6m` | falta la Seguridad Social 2 meses | 0,621 | 0,047 | 4.400 | 230 |
| `caida_6m` | caída estructural de cobros | 0,615 | 0,027 | 5.583 | 552 |
| **`rompe_caja_2m`** | **anticipación dura**: estando sana hoy, caja < 0 en m+1 o m+2 | **0,609** | 0,036 | 9.198 | 62 |
| **`entrada_estres_2m`** | **anticipación**: estando sana hoy, entra en tensión en m+1 o m+2 | **0,597** | 0,022 | 9.198 | 550 |
| `tension_entrada_6m` | entrada en tensión desde sana, a 6 meses | 0,596 | 0,037 | 5.918 | 130 |
| `caida_3m_corto` | variante de historia corta de la caída (existe desde el mes 3) | 0,581 | 0,012 | 14.260 | 2.513 |
| `impago_ap_6m` | mora AP estructural (vencido ≥ 25 % del gasto). Es un **estado crónico**, no un impago: el 60 % de las filas | 0,568 | 0,025 | 8.595 | 5.106 |
| `impago_nomina_6m` | falta la nómina 2 meses | 0,557 | 0,045 | 3.563 | 347 |
| `expansion_6m` | expansión (medida con la nota adversa, que no es su trabajo) | 0,535 | 0,038 | 8.013 | 468 |
| `recaida_6m` | vuelve a entrar en estrés tras haber salido | 0,521 | 0,024 | 649 | 494 |
| `expansion_3m` | expansión de historia corta | 0,518 | 0,017 | 14.260 | 2.302 |
| `impago_cuota_6m` | falta la cuota de deuda 2 meses | **0,450** | 0,037 | 2.688 | 376 |
| `cura_3m` | sale del estrés y aguanta 3 meses limpios | **0,337** | 0,020 | 16.986 | 442 |

**Las dos últimas están por debajo de 0,50 y no es un bug:**

- `impago_cuota_6m` (0,450) ordena **al revés**. Sin calendario de cuotas (3 % de cobertura)
  no se distingue un impago de un vencimiento o un cambio de periodicidad: el 43 % vuelve a
  pagar en 6 meses y la caja no cae. Por eso la cuota **salió** de `incumplimiento_6m` y se
  publica aparte como juez inverificable. Es una etiqueta mala, no un modelo malo.
- `cura_3m` (0,337) es mecánico: para curarte tienes que estar enfermo, y los enfermos tienen
  nota baja. La nota ordena bien *quién está mal*, y curarse correlaciona con estar mal hoy.
  Medirlo con la nota de nivel no tiene sentido; se deja en la tabla por transparencia.

### 3.3 · Nota de expansión

Las mismas 17 features con los pesos calibrados solo contra la cara positiva
(`fit(..., target="expansion")`). Son **dos notas**, no una: promediar los pesos de la tensión
con los de la expansión dejaba la caja sin peso.

| evento | AUC nota adversa | **AUC nota de expansión** |
|---|---:|---:|
| `expansion_6m` | 0,535 | **0,631** (se 0,032) |
| `expansion_3m` | 0,518 | **0,562** |
| `caida_6m` | 0,615 | 0,613 |
| `tension_np_raw_6m` | 0,800 | 0,527 |

La última fila es la comprobación de que son notas distintas de verdad: la de expansión no
sabe nada de tensión (0,527 ≈ azar), y no debe.

### 3.4 · Anticipación

Medida contra el **estado mensual** de estrés (`estres_mes`), no contra las etiquetas `*_6m`:
esas ya son ventanas futuras y regalarían hasta 6 meses de ventaja ficticia. Solo cuentan las
empresas que empiezan sanas y entran en estrés; avisar sobre quien ya estaba mal no tiene mérito.
Aviso = la nota baja de 35 (banda «riesgo»).

| | valor |
|---|---:|
| entradas en estrés observadas | 349 |
| avisadas antes de entrar | 36 |
| **cobertura** | **10,3 %** |
| mediana de antelación (de las avisadas) | **2 meses** |
| media de antelación | 3,6 meses |
| avisadas con ≥ 2 meses | 61 % |

Léelo honestamente: **cuando avisa, avisa pronto (2 meses de mediana), pero avisa poco
(1 de cada 10)**. El umbral 35 es conservador por diseño — bajar el listón sube la cobertura
y llena la cartera de falsos positivos. Es la palanca de producto más clara que queda abierta.

### 3.5 · Probabilidades publicadas

Segunda calibración, **sobre la nota publicada**: una logística de una sola variable por
evento. Dos empresas con la misma nota tienen la misma probabilidad, siempre.

| nota | tensión 6m | incumplimiento | caída | algún adverso |
|---:|---:|---:|---:|---:|
| 10 | 90 % | 14 % | 21 % | **73 %** |
| 30 | 69 % | 9 % | 14 % | 53 % |
| 50 | 37 % | 6 % | 9 % | 32 % |
| 70 | 13 % | 4 % | 6 % | 16 % |
| 90 | 4 % | 2 % | 4 % | **8 %** |

Regla de publicación: una `prob_*` **solo sale si la nota separa ese evento con AUC ≥ 0,60**.
Por eso `expansion_6m` no publica probabilidad con la nota adversa: estaría bien calibrada en
media pero ordenaría mal, y eso es peor que no publicar nada.

### 3.6 · El modelo, entero

Todo lo aprendido son 17 arrays de percentiles, 17 pesos, 2 números de escala y 2 por evento.

| feature | peso | | feature | peso |
|---|---:|---|---|---:|
| `runway` | 0,213 | | `ap_late_share` | 0,031 |
| `payroll_cv` | 0,151 | | `transfer_dep` | 0,020 |
| `activity_trend` | 0,121 | | `net_vol_6m` | 0,019 |
| `oper_persistence_6m` | 0,107 | | `cust_trend` | 0,016 |
| `lc_util` | 0,100 | | `refund_rate` | 0,014 |
| `lost_share` | 0,072 | | `oper_growth_12m` | 0,006 |
| `ap_overdue_ratio` | 0,051 | | `ar_overdue_90_ratio` | 0,003 |
| `ar_late_share` | 0,037 | | **`debt_burden`** | **0,000** |
| `hhi_ar_6m` | 0,037 | | | |

`debt_burden` en 0,000 no es un fallo: la cota `w ≥ 0` impide que el ajuste le dé signo
negativo, y en estos datos la carga de deuda no aporta señal adversa una vez conoces la caja.
Se queda con peso nulo en vez de ensuciar la nota con el signo invertido.

- **Escala**: `nota = −70,96 + 2,34 × compuesto`, que lleva P5 → 15 y P95 → 85.
- **EWMA** α = 0,5 sobre las contribuciones.
- **Bandas** del panel completo: 4.862 sano · 11.793 vigilar · 4.883 riesgo.
- **Cobertura** media 0,646 · **confianza** media 0,578.

---

## 4 · Verificación contra el modelo anterior (`ar107`)

El backend es una reescritura, así que lo primero era demostrar que **no cambió el modelo**.

**Nota, fila a fila** (mismo panel, 21.538 filas): diferencia máxima **0,0002 puntos**, media
0,00003. Es ruido de convergencia de L-BFGS. Eventos idénticos, pesos idénticos.

**Métricas de origen móvil** frente a las publicadas en `research/ESTADO.md`:

| métrica | `ar107` publicado | backend | Δ |
|---|---:|---:|---:|
| **PM** | 0,659 | **0,659** | 0,000 |
| AUC tensión | 0,746 | **0,746** | 0,000 |
| AUC incumplimiento | 0,680 | **0,680** | 0,000 |
| AUC caída | 0,627 | **0,627** | 0,000 |
| AUC expansión | 0,583 | **0,583** | 0,000 |

**Fuera de grupo, todas las filas** (`notas_oof.py` de la fase 3). Aquí hay diferencias de
milésimas porque el cálculo del OOF no es idéntico: el viejo reconstruía la nota por iteración
y corte, el nuevo usa un scorer por fold sobre todo el histórico. Todas caen **muy dentro** de
su propio error típico:

| evento | `ar107` | backend | Δ | se |
|---|---:|---:|---:|---:|
| `tension_np_raw_6m` | 0,807 | 0,800 | −0,007 | 0,017 |
| `tension_6m` | 0,791 | 0,785 | −0,006 | 0,016 |
| `incumplimiento_6m` | 0,623 | 0,633 | +0,010 | 0,028 |
| `caida_6m` | 0,618 | 0,615 | −0,003 | 0,027 |
| `entrada_estres_2m` | 0,602 | 0,597 | −0,005 | 0,022 |
| `rompe_caja_2m` | 0,607 | 0,609 | +0,002 | 0,036 |
| `impago_ap_6m` | 0,560 | 0,568 | +0,008 | 0,025 |
| nota de expansión vs `expansion_6m` | 0,628 | 0,631 | +0,003 | 0,032 |

Ninguna diferencia llega a media desviación típica. **El modelo es el mismo.**

Un matiz sobre los pesos: `ESTADO.md` publica `runway` 0,204 / `payroll_cv` 0,122 /
`lc_util` 0,113, que es la **media de los pesos de los 15 folds×cortes**. Los de arriba
(0,213 / 0,151 / 0,100) son los del ajuste sobre todo el histórico, que es el artefacto que
sirve la API. Son dos cosas distintas y las dos son correctas.

---

## 5 · Qué NO mide este backend

Honestidad sobre el alcance, porque la reescritura tiró cosas a propósito:

- **No hay forecaster.** El `TrajectoryForecaster` (MLForecast + LightGBM cuantílico, bandas
  q10/q50/q90 a 1-3 meses) se quedó fuera. Con él se iban sus métricas: `auc_deterioro` 0,722,
  `auc_mejora` 0,757, cobertura del intervalo 81 %, MAE vs AR(1). Lo que sirve hoy la API es
  `delta3`: la **trayectoria observada**, nota de hoy menos nota de hace 3 meses. Es un hecho,
  no una predicción.
- **No hay motor proactivo** (proyección aritmética de caja para decidir factoring/refi).
- **Bache frente a caída** sigue sin resolverse (AUC 0,53 en la versión anterior).
- La nota es **relativa a la población de entrenamiento**: un 50 significa «mediana de las
  21.538 filas de 2024-2026». Las `prob_*` son la escala absoluta que compensa eso.
