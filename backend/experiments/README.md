# experiments · ¿los pesos del catálogo a priori son mejores?

`docs/explicacion_pesos.md` describe **42 variables en 7 pilares con pesos a priori**
(criticidad × evidencia × cobertura × persistencia). El backend puntúa **17 features con pesos
calibrados**. Poner lo uno en lugar de lo otro mezcla dos cambios, así que se miden por separado.

**Resultado: no.** Con los pesos del doc el ancla del sistema (tensión de caja) cae de 0,848 a
0,719 de AUC — **−9,7 σ** en bootstrap pareado — y la anticipación cae 4,8 σ. El PM no lo ve
(0,6285 → 0,6303), que es la razón por la que el PM se reporta y no decide.

De las 42 variables sobrevive **una**: `payroll_continuity_6m` (brazo H), ya adoptada en
`preprocessing.py` como la feature 18. La otra candidata, `tax_miss`, se descartó al aislarla
(brazo I): `veto_iva_ausente` es un subconjunto estricto suyo —es el veto con memoria, no una
feature— y su ganancia es en buena parte autocorrelación, porque el evento `impago_iva_6m` se
calcula con casi la misma fórmula. Además se lleva todo el daño a la expansión (−4,2 σ).

El informe completo, con las tablas y el diagnóstico: [`pesos_2x2.html`](pesos_2x2.html).

## El enfoque escalonado, por separado

El catálogo tiene dos escaleras y conviene no juzgarlas juntas:

1. **La criticidad declarada a mano** — P0 1,00 · P1 0,72 · P2 0,45 · P3 0,25 · COV 0,05.
2. **El reparto** `peso = peso_del_pilar × (prioridad / Σ prioridades del pilar)`.

El brazo B las mide juntas y pierde 9,7σ, pero **la culpa es de la segunda**: repartir el 24 %
de liquidez entre seis variables impide que ninguna pase del 4,8 %, mientras la calibración
pone 27 % en `runway` sola. La escalera dice «la caja es P0» y el reparto se lo quita acto
seguido. Con las 42 variables del doc y pesos calibrados (brazo D) el ancla vuelve a 0,835.

Así que se probó la primera **sola**, como **cota inferior** sobre el peso calibrado
(`w_f ≥ 0,02 × criticidad_f`, renormalizado antes de ajustar la escala). Resultado:

| evento | calibrado | con piso | σ pareadas |
|---|---:|---:|---:|
| `tension_np_raw_6m` (ancla) | 0,849 | 0,848 | **−2,6** |
| `tension_6m` | 0,823 | 0,821 | **−3,0** |
| `caida_3m_corto` | 0,538 | 0,543 | +8,3 |
| `impago_ap_6m` | 0,539 | 0,544 | +4,5 |
| `caida_6m` | 0,577 | 0,583 | +3,6 |

**No se adopta, y el motivo es que las sigmas engañan aquí.** El piso solo mueve dos features
—`oper_growth_12m` 0,005 → 0,009 y `ar_overdue_90_ratio` 0,008 → 0,009—, así que los dos brazos
son casi el mismo modelo: el error típico de la diferencia se hace minúsculo y cualquier cambio
de 0,005 de AUC sale con muchas sigmas. Es el error de celebrar sigmas, con el signo cambiado.

Y sobre todo: **no hay nada que rescatar**. El piso existía para evitar que una feature crítica
acabase en peso 0, y con el ancla de caja propia eso ya no pasa — `debt_burden` (P1) calibra a
0,026, muy por encima de su piso de 0,014. La patología que justificaba la escalera era del
ancla vieja con póliza. Añadir 18 juicios de criticidad a mano y un parámetro `PISO` para
comprar ±0,005 de AUC en las dos direcciones no se paga.

| brazo | qué es | ancla | PM | avisos cubiertos |
|---|---|---:|---:|---:|
| A | 17 features · pesos calibrados (el backend) | **0,848** | 0,6285 | 18,6 % |
| B | 17 features · **pesos del doc** | 0,719 | 0,6303 | 22,9 % |
| C | **42 features del doc · pesos del doc** | 0,740 | 0,6086 | 24,4 % |
| D | **42 features del doc** · pesos calibrados | 0,835 | 0,6199 | 22,9 % |
| E | 17 features · mezcla 50/50 | 0,819 | 0,6386 | 18,9 % |
| F | 17 + 7 features nuevas · calibradas | 0,849 | 0,6288 | 20,3 % |
| G | 17 + 2 features nuevas · calibradas | 0,848 | 0,6243 | 22,6 % |
| **H** | **17 + `payroll_continuity_6m`** (la adoptada) | **0,851** | 0,6300 | 18,6 % |
| I | 17 + `tax_miss` (descartada) | 0,846 | 0,6224 | 22,9 % |

`Aexp` y `Gexp` repiten A y G calibrando contra la cara positiva (la nota de expansión), porque
el único coste de G se mide ahí y con los pesos adversos salía cuatro veces más grande.

## Ficheros

| fichero | qué hace |
|---|---|
| `dump_pesos_doc.py` | ejecuta el generador del doc y vuelca sus pesos exactos a `pesos_doc.json` |
| `catalogo.py` | las 42 variables del catálogo con el contrato de `preprocessing.FEATURES`, más las columnas que el panel no trae (contrapartes, deuda, notas de crédito, calendario) |
| `medir.py` | los brazos: parchea `predict` y mide con `metrics.oof` / `auc_table` / `compare` |
| `informe_html.py` | `salida/*.json` → `pesos_2x2.html` |

```bash
cd backend/experiments
uv run --project ../../research --with duckdb python dump_pesos_doc.py > pesos_doc.json
uv run --project ../../research python catalogo.py          # cobertura de las 42
uv run --project ../../research python medir.py A           # ...B C D E F G Aexp Gexp
uv run --project ../../research python medir.py informe
uv run --project ../../research python informe_html.py
```

## Lo que hace honesta la comparación

- **Las features compartidas no se redefinen**: salen de `preprocessing.add_features` tal cual.
  Solo cambian las features nuevas y los pesos; percentiles, escala P5/P95, EWMA, reglas y
  probabilidades son el mismo código en todos los brazos.
- **El banco de pruebas está validado**: el brazo A reproduce el README del backend (PM 0,6285,
  ancla 0,848, cobertura de aviso 18,6 %, mediana 4 meses) y `Aexp` reproduce su nota de
  expansión (0,583).
- **Las desviaciones están declaradas** en `catalogo.DESVIACIONES`: dónde el catálogo no se puede
  implementar literalmente (contrapartes ausentes en el 89,6 % de las salidas, ficheros de deuda
  sin fecha, calendario con 40 empresas) y con qué se sustituye.
- `salida/oof_*.parquet` no se versiona; los `metrics_*.json` y `pareado_*.json` sí, porque son
  lo que lee el informe.
