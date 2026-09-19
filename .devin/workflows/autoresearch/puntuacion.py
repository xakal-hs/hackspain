"""Puntuación única del modelo: ¿estamos mejorando el score?

Lee los `reports/metrics_<tag>.json` de `evaluate.py` y reduce el resultado a **un número** para
comparar versiones sin ambigüedad, más los guardarraíles que no deben empeorar.

    cd research && uv run python ../.devin/workflows/autoresearch/puntuacion.py reports/metrics_ar000.json reports/metrics_ar001.json
    cd research && uv run python ../.devin/workflows/autoresearch/puntuacion.py --glob 'reports/metrics_ar*.json'

**Puntuación del modelo (PM)** = media del AUC del nivel frente a los cuatro eventos ancla (E1-E4):
tensión de liquidez, incumplimiento, caída estructural y expansión. Mide si la nota significa algo,
que es la primera mitad del reto.

Guardarraíles (no deben empeorar aunque PM suba): detección de deterioro y de mejora a 3 meses
(`auc_deterioro`, `auc_mejora`), ventaja sobre el arrastre AR(1) (`skill_vs_ar1_h3`) y cobertura del
intervalo (`coverage80_h3`).
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
from pathlib import Path

EVENTOS = ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]
GUARDARRAILES = ["auc_deterioro", "auc_mejora", "skill_vs_ar1_h3", "coverage80_h3"]


def puntuacion(m: dict) -> float | None:
    aucs = [m.get(f"auc_level_vs_{e}") for e in EVENTOS]
    aucs = [a for a in aucs if a is not None]
    return sum(aucs) / len(aucs) if aucs else None


def fila(m: dict) -> dict:
    r = {"tag": m.get("tag", "?"), "PM": puntuacion(m)}
    for e in EVENTOS:
        r[e] = m.get(f"auc_level_vs_{e}")
    for k in GUARDARRAILES:
        r[k] = m.get(k)
    return r


def fmt(v, nd=3):
    if v is None:
        return "—"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("metricas", nargs="*", help="rutas a reports/metrics_<tag>.json")
    ap.add_argument("--glob", help="patrón glob, p. ej. 'reports/metrics_ar*.json'")
    args = ap.parse_args()
    rutas = [Path(p) for p in args.metricas]
    if args.glob:
        rutas += [Path(p) for p in sorted(globmod.glob(args.glob))]
    if not rutas:
        ap.error("pasa rutas o --glob")
    filas = [fila(json.loads(p.read_text())) for p in rutas if p.exists()]
    cols = ["tag", "PM", *EVENTOS, *GUARDARRAILES]
    ancho = {c: max(len(c), *(len(fmt(f.get(c))) for f in filas)) for c in cols}
    print("  ".join(c.ljust(ancho[c]) for c in cols))
    for f in filas:
        print("  ".join(fmt(f.get(c)).ljust(ancho[c]) for c in cols))
    if len(filas) == 2:
        a, b = filas
        dp = (b["PM"] or 0) - (a["PM"] or 0)
        print(f"\nΔPM = {dp:+.3f}  ({a['tag']} → {b['tag']})  " + ("MEJORA" if dp > 0 else "EMPEORA" if dp < 0 else "IGUAL"))
        malos = [k for k in GUARDARRAILES if a.get(k) is not None and b.get(k) is not None and b[k] < a[k] - 1e-9]
        print("guardarraíles que empeoran: " + (", ".join(malos) if malos else "ninguno"))


if __name__ == "__main__":
    main()
