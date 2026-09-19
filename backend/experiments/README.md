# experiments · ¿los pesos del catálogo a priori son mejores?

`docs/explicacion_pesos.md` describe **42 variables en 7 pilares con pesos a priori**
(criticidad × evidencia × cobertura × persistencia). El backend puntúa **17 features con pesos
calibrados**. Poner lo uno en lugar de lo otro mezcla dos cambios, así que se miden por separado.

**Resultado: no.** Con los pesos del doc el ancla del sistema (tensión de caja) cae de 0,848 a
0,719 de AUC — **−9,7 σ** en bootstrap pareado — y la anticipación cae 4,8 σ. El PM no lo ve
(0,6285 → 0,6303), que es la razón por la que el PM se reporta y no decide. Lo que sí sobrevive
son **dos** variables sueltas: `tax_miss` y `payroll_continuity_6m` (brazo G).

El informe completo, con las tablas y el diagnóstico: [`pesos_2x2.html`](pesos_2x2.html).

| brazo | qué es | ancla | PM | avisos cubiertos |
|---|---|---:|---:|---:|
| A | 17 features · pesos calibrados (el backend) | **0,848** | 0,6285 | 18,6 % |
| B | 17 features · **pesos del doc** | 0,719 | 0,6303 | 22,9 % |
| C | **42 features del doc · pesos del doc** | 0,740 | 0,6086 | 24,4 % |
| D | **42 features del doc** · pesos calibrados | 0,835 | 0,6199 | 22,9 % |
| E | 17 features · mezcla 50/50 | 0,819 | 0,6386 | 18,9 % |
| F | 17 + 7 features nuevas · calibradas | 0,849 | 0,6288 | 20,3 % |
| **G** | **17 + 2 features nuevas · calibradas** | **0,848** | 0,6243 | **22,6 %** |

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
