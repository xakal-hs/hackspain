"""Los pesos del catálogo a priori, tal como los calcula su propio generador.

    uv run --with duckdb python dump_pesos_doc.py > pesos_doc.json

No se copian a mano de `docs/explicacion_pesos.md`: se importa
`analysis/back_engineering_variables.py` y se le pide el reparto. La cobertura se mide sobre
`output/` (los CSV de verdad), no sobre `data/`, donde `invoices.csv` y `transactions.csv` son
punteros LFS de 134 bytes que DuckDB leería como ficheros vacíos sin avisar.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN = ROOT / "analysis/back_engineering_variables.py"

spec = importlib.util.spec_from_file_location("beg", GEN)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.DATA = ROOT / "output"

cov = m.compute_coverage()
if not cov:
    raise SystemExit("sin coberturas (¿falta duckdb?): todos los pesos saldrían aplastados")

by_pillar = {p["id"]: [] for p in m.PILLARS}
for it in m.ITEMS:
    by_pillar[it["pillar"]].append(it)
var_w, pillar_w = m.pillar_weights(by_pillar, cov)

print(json.dumps({
    "generador": str(GEN.relative_to(ROOT)),
    "cov": cov,
    "pillar_w": pillar_w,
    "vars": [{"var": it["var"], "pillar": it["pillar"], "tier": it["tier"], "w": var_w[it["var"]],
              "prio": m.priority(it, cov)[0], "comp": m.priority(it, cov)[1],
              "item": it.get("item"), "dir": it.get("dir")} for it in m.ITEMS],
}, indent=1, ensure_ascii=False, default=str))
