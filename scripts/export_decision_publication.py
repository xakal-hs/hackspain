"""Publica la capa de decisión y el catálogo del modelo como contrato de datos.

La nota ya está publicada (``supabase/export/company_health_monthly.csv``, linaje
``xray-v7``). Este script **no la recalcula**: la lee y le pone encima la decisión del
prestamista de ``backend/decision.py``, que solo necesita nota, banda y confianza más
los hechos de hoy del panel (vetos y observabilidad). Así la acción que se enseña no
puede divergir de la nota que se enseña.

    python3 scripts/export_decision_publication.py

Genera en ``supabase/export/``:

* ``company_decision_monthly.csv``: acción, vetos, avisos y razones por empresa-mes.
* ``score_catalog.json``: pesos, escala, bandas, anclas de evento y catálogo de vetos.

Después: ``python3 scripts/load_decision_publication.py``.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "src"))

import joblib  # noqa: E402
import pandas as pd  # noqa: E402

import polars as pl  # noqa: E402

import decision as dcs  # noqa: E402  (research/src/decision.py)
import targets  # noqa: E402  (research/src/targets.py: los hechos que veta decide())
from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402

EXPORT = ROOT / "supabase" / "export"
HEALTH_CSV = EXPORT / "company_health_monthly.csv"
PANEL = ROOT / "research" / "data" / "panel.parquet"
ARTIFACT = ROOT / "research" / "artifacts" / "xray.joblib"

# Columnas del panel que mira `decide()`: los vetos, más lo que dice si se ve la empresa.
DECIDE_COLUMNS = [
    *targets.VETOS,
    "n_tx", "has_erp", "uncat_share", "month_idx",
    "dq_cash_sentinel", "dq_cash_implausible", "has_drift", "months_since_last_tx",
]


def published_health() -> pd.DataFrame:
    """La nota publicada, con los nombres que espera `decide()`."""
    if not HEALTH_CSV.exists():
        raise SystemExit(
            f"Falta {HEALTH_CSV}. Genera antes la publicación de salud:\n"
            "  cd research && uv run python src/export_health_publication.py --out ../supabase/export"
        )
    health = pd.read_csv(HEALTH_CSV)
    health["month"] = pd.to_datetime(health["month"])
    return health.rename(columns={"health_score": "score", "health_band": "band"})[
        ["company_id", "month", "score", "band", "confidence", "score_version"]
    ]


def decisions(health: pd.DataFrame) -> pd.DataFrame:
    """Una decisión por empresa-mes. El panel aporta los hechos; la nota, el orden."""
    panel = (add_events(add_features(pl.read_parquet(PANEL)))
             .to_pandas().sort_values(["company_id", "month"]).reset_index(drop=True))
    facts = panel[[c for c in ["company_id", "month", *DECIDE_COLUMNS] if c in panel.columns]]
    rows = health.merge(facts, on=["company_id", "month"], how="left", indicator=True)

    missing = int((rows._merge != "both").sum())
    if missing:
        raise SystemExit(
            f"{missing} filas de salud sin fila de panel: la nota publicada y el panel no "
            "vienen del mismo corte. Regenera uno de los dos antes de publicar la decisión."
        )

    out = [dcs.decide(row) for _, row in rows.iterrows()]
    return pd.DataFrame({
        "company_id": rows.company_id,
        "month": rows.month.dt.strftime("%Y-%m-%d"),
        "accion": [o["accion"] for o in out],
        "accion_label": [o["accion_label"] for o in out],
        # la primera razón es la que manda: el veto bloqueante, o la banda
        "razon": [o["razones"][0]["texto"] if o.get("razones") else "" for o in out],
        "vetos": [json.dumps(veto_objects(o.get("vetos", [])), ensure_ascii=False) for o in out],
        "avisos": [json.dumps(veto_objects(o.get("avisos", [])), ensure_ascii=False) for o in out],
        "razones": [json.dumps(o.get("razones", []), ensure_ascii=False) for o in out],
        "importe_max_meses": [o.get("importe_max_meses") for o in out],
        "score_version": rows.score_version,
    })


def veto_objects(codes) -> list[dict]:
    """Código -> veto con su etiqueta y su explicación. El texto viaja con la regla."""
    objects = []
    for code in codes:
        etiqueta, texto = dcs.VETOS.get(code, (code, ""))
        objects.append({
            "codigo": code, "etiqueta": etiqueta, "texto": texto,
            "bloquea": code in dcs.BLOQUEAN, "levantable": code in dcs.LEVANTABLES,
        })
    return objects


def catalog(score_version: str) -> dict:
    """Todo lo que el modelo aprendió, más los textos de las reglas que van encima."""
    import xray  # noqa: F401  (research/src/xray.py: necesario para deserializar el artefacto)

    if not ARTIFACT.exists():
        raise SystemExit(f"Falta {ARTIFACT}; es de donde salen los pesos publicados.")
    scorer = joblib.load(ARTIFACT)["scorer"]
    spec = xray.SPEC

    return {
        "score_version": score_version,
        "target": scorer.target,
        "alpha_ewma": float(scorer.smooth_alpha),
        "weights": {k: round(float(v), 4) for k, v in
                    sorted(scorer.weights_.items(), key=lambda kv: -kv[1])},
        "scale": {"a": round(float(scorer.scale_[0]), 3), "b": round(float(scorer.scale_[1]), 3)},
        "bands": [{"desde": lo, "hasta": hi, "banda": name} for lo, hi, name in xray.BANDS],
        "dormant_cap": float(scorer.dormant_cap),
        "features": {
            f: {"label": spec[f][3], "pilar": spec[f][0], "formula": spec[f][4],
                "sentido": "suma" if spec[f][1] > 0 else "resta"}
            for f in scorer.features_ if f in spec
        },
        "pillars": xray.PILLARS,
        "anclas": list(scorer.proba_),
        "probabilities": {k: {"a": round(float(a), 3), "b": round(float(b), 3),
                              "tasa_base": round(float(r), 4)}
                          for k, (a, b, r) in scorer.proba_.items()},
        "vetos": [
            {"codigo": code, "etiqueta": etiqueta, "texto": texto,
             "bloquea": code in dcs.BLOQUEAN, "levantable": code in dcs.LEVANTABLES}
            for code, (etiqueta, texto) in dcs.VETOS.items()
        ],
        "acciones": dcs.ACCIONES,
    }


def main() -> None:
    EXPORT.mkdir(parents=True, exist_ok=True)
    health = published_health()
    version = str(health.score_version.iloc[0])

    table = decisions(health)
    path = EXPORT / "company_decision_monthly.csv"
    table.to_csv(path, index=False, quoting=csv.QUOTE_MINIMAL)

    catalog_path = EXPORT / "score_catalog.json"
    catalog_path.write_text(json.dumps(catalog(version), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")

    counts = table.accion.value_counts().to_dict()
    print(f"{len(table)} decisiones ({version}) -> {path}")
    print(f"  acciones: {counts}")
    print(f"  filas con algún veto bloqueante: {int((table.vetos != '[]').sum())}")
    print(f"catálogo del modelo -> {catalog_path}")


if __name__ == "__main__":
    main()
