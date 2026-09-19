"""Volcado de los números reales del score, desde el artefacto entrenado.

Para que el documento técnico no sea prosa inventada: extrae del scorer servido
(`research/artifacts/xray.joblib`) las features, sus pesos, la calibración por evento, la escala
publicada, las bandas y los coeficientes de probabilidad, y los imprime en Markdown o JSON.

    cd research && uv run python ../.devin/workflows/autoresearch/score_datos.py            # markdown
    cd research && uv run python ../.devin/workflows/autoresearch/score_datos.py --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import joblib

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
ART = RES / "artifacts" / "xray.joblib"
sys.path.insert(0, str(RES / "src"))
from xray import SPEC, PRIOR_W, BANDS, PILLARS, DORMANT_CAP  # noqa: E402


def datos() -> dict:
    if not ART.exists():
        sys.exit(f"falta {ART}; entrena con `uv run python src/service.py` en research/")
    sc = joblib.load(ART)["scorer"]
    feats = []
    for f in sc.features_:
        pilar, direccion, zero_best, label, desc = SPEC[f]
        feats.append({
            "feature": f, "pilar": pilar, "direccion": "más es mejor" if direccion > 0 else "menos es mejor",
            "cero_es_lo_mejor": bool(zero_best), "etiqueta": label, "descripcion": desc,
            "peso": round(float(sc.weights_.get(f, 0.0)), 4), "peso_previo": PRIOR_W.get(f),
            "sub_score_sin_dato": 50.0,
        })
    feats.sort(key=lambda x: -x["peso"])
    a, b = sc.scale_
    calib = {}
    for k, info in (getattr(sc, "calibration_", None) or {}).items():
        calib[k] = {"n": info.get("n"), "tasa_evento": round(info.get("event_rate", 0), 4),
                    "convergio": info.get("converged"),
                    "coef": {f: v for f, v in sorted(info.get("coef", {}).items(), key=lambda kv: -kv[1]) if v > 0}}
    proba = {k: {"intercepto": round(v[0], 4), "coef_score": round(v[1], 4), "tasa_base": round(v[2], 4)}
             for k, v in (getattr(sc, "proba_", None) or {}).items()}
    return {
        "artefacto": str(ART.relative_to(ROOT)),
        "features": feats,
        "pilares": PILLARS,
        "suma_pesos": round(sum(x["peso"] for x in feats), 6),
        "escala_publicada": {"a": round(float(a), 4), "b": round(float(b), 6),
                             "formula": "score_bruto = recorte(0,100, a + b * Σ peso_f · sub_f)"},
        "bandas": [{"desde": lo, "hasta": hi, "banda": name} for lo, hi, name in BANDS],
        "suavizado_ewma_alpha": sc.smooth_alpha,
        "tope_inactividad": DORMANT_CAP,
        "calibracion_por_evento": calib,
        "probabilidad_por_evento": proba,
    }


def md(d: dict) -> str:
    L = ["# Números del score (del artefacto entrenado)", "", f"Artefacto: `{d['artefacto']}`", "",
         f"Suma de pesos: **{d['suma_pesos']}** (debe ser 1). Escala publicada: a = {d['escala_publicada']['a']}, "
         f"b = {d['escala_publicada']['b']}. EWMA α = {d['suavizado_ewma_alpha']}. Tope inactividad = {d['tope_inactividad']}.", "",
         "## Features y pesos", "", "| feature | pilar | dirección | cero=mejor | peso | peso previo | etiqueta |",
         "|---|---|---|---|---|---|---|"]
    for f in d["features"]:
        L.append(f"| `{f['feature']}` | {f['pilar']} | {f['direccion']} | {f['cero_es_lo_mejor']} | {f['peso']} | {f['peso_previo']} | {f['etiqueta']} |")
    L += ["", "## Bandas", "", "| desde | hasta | banda |", "|---|---|---|"]
    for b in d["bandas"]:
        L.append(f"| {b['desde']} | {b['hasta']} | {b['banda']} |")
    L += ["", "## Calibración por evento (logística de signo restringido)", ""]
    for k, v in d["calibracion_por_evento"].items():
        top = ", ".join(f"`{f}` {c}" for f, c in list(v["coef"].items())[:6])
        L.append(f"- **{k}** (n={v['n']}, tasa={v['tasa_evento']}, convergió={v['convergio']}): {top}")
    L += ["", "## Probabilidad publicada (score → evento a 6 meses)", ""]
    for k, v in d["probabilidad_por_evento"].items():
        L.append(f"- **{k}**: P = σ({v['intercepto']} + {v['coef_score']} · score/100); tasa base {v['tasa_base']}")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", help="escribe a un fichero (por defecto, stdout)")
    args = ap.parse_args()
    d = datos()
    txt = json.dumps(d, ensure_ascii=False, indent=2) if args.json else md(d)
    if args.out:
        Path(args.out).write_text(txt)
        print(f"escrito {args.out}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
