"""Análisis exploratorio data-lead del workflow autoresearch.

Estrategia del reto: **los datos primero**. Antes de formular una hipótesis (una premisa),
hay que mirar los datos. Este script produce la **base de evidencia** sobre la que el consejo
(fase 2) redacta premisas falsables: distribuciones, patrones temporales, correlaciones, outliers
y, sobre todo, **la asociación observada de cada candidato con cada evento**.

Dos salidas (en `.devin/workflows/autoresearch/salida/`):
- `analisis_datos.md`   — legible para el consejo (con las tablas y los hechos).
- `hechos_datos.jsonl`  — una línea por *hecho*: patrón observado, con n, tasa en el grupo,
  tasa base, lift y AUC. Es lo que una premisa debe **citar** como `evidencia`.

Uso (desde `research/`):
    uv run python ../.devin/workflows/autoresearch/analisis_datos.py
    uv run python ../.devin/workflows/autoresearch/analisis_datos.py --out ../.devin/.../salida/analisis_datos.md
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
WF = Path(__file__).parent
OUT = WF / "salida"
PANEL = RES / "data" / "panel.parquet"

sys.path.insert(0, str(RES / "src"))
from features import add_features, SCORE_FEATURES, DRIVERS  # noqa: E402
from targets import add_events  # noqa: E402

EVENTOS = ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]
# Condiciones candidatas: lo que un prestamista miraría primero. Cada una es un «hecho» a medir.
CANDIDATOS = [
    ("caja_negativa", "cash_end < 0", "liquidez"),
    ("caja_negativa_3m", "cash_end < 0 and dec_cash_neg_3m == 1", "liquidez"),
    ("runway_bajo", "runway < 0", "liquidez"),
    ("poliza_agotada", "lc_util > 0.9", "liquidez"),
    ("margen_negativo", "net_margin_6m < 0", "rentabilidad"),
    ("ingresos_caen", "growth_vs_12m < -0.2", "actividad"),
    ("actividad_cae", "activity_trend < -0.3", "actividad"),
    ("carga_deuda_alta", "debt_burden > 0.3", "deuda"),
    ("mora_pagos_alta", "ap_late_share > 0.2", "pagos"),
    ("mora_cobros_alta", "ar_late_share > 0.2", "cobros"),
    ("vencido_pagos_alto", "ap_overdue_ratio > 0.1", "pagos"),
    ("vencido_90_cobros", "ar_overdue_90_ratio > 0.1", "cobros"),
    ("devoluciones_altas", "refund_rate > 0.1", "comportamiento"),
    ("clientes_perdidos", "lost_share > 0.5", "cobros"),
    ("concentracion_alta", "hhi_ar_6m > 0.5", "cobros"),
    ("volatilidad_baja", "net_vol_6m > 0.5", "estabilidad"),
    ("dependencia_transferencias", "transfer_dep > 0.3", "estabilidad"),
    ("intragrupo_alto", "intragroup_flow > 0.2 * gross_flow", "observabilidad"),
    ("dormido", "dormant == 1", "observabilidad"),
    ("sin_erp", "has_erp == 0", "observabilidad"),
    ("sin_divisa_fx", "fx_share > 0.5", "observabilidad"),
    ("sin_categorizar", "uncat_share > 0.1", "observabilidad"),
]


def _lift(d: pl.DataFrame, cond: str, evento: str) -> dict:
    """Tasa del evento dentro y fuera de la condición, con lift y n."""
    sub = d.select([pl.col(evento).alias("y"), pl.sql_expr(cond).fill_null(False).alias("c")]).drop_nulls("y")
    n = sub.height
    if n == 0 or sub["y"].n_unique() < 2:
        return {"n": n, "tasa_grupo": None, "tasa_base": None, "lift": None, "auc": None}
    p1 = sub.filter(pl.col("c"))["y"].mean()
    p0 = sub.filter(~pl.col("c"))["y"].mean()
    base = sub["y"].mean()
    try:
        from sklearn.metrics import roc_auc_score
        auc = float(roc_auc_score(sub["y"], sub["c"].cast(pl.Int8)))
    except Exception:
        auc = None
    return {"n": n, "n_grupo": int(sub.filter(pl.col("c")).height),
            "tasa_grupo": float(p1) if p1 is not None else None,
            "tasa_base": float(base) if base is not None else None,
            "lift": float(p1 / p0) if p1 is not None and p0 else None, "auc": auc}


def _auc_features(d: pl.DataFrame, evento: str) -> list[dict]:
    """AUC de cada feature continua contra el evento (un hecho por feature)."""
    from sklearn.metrics import roc_auc_score
    out = []
    for c in SCORE_FEATURES:
        if c not in d.columns:
            continue
        sub = d.select([pl.col(evento).alias("y"), pl.col(c).alias("s")]).drop_nulls()
        if sub.height < 50 or sub["y"].n_unique() < 2:
            continue
        out.append({"feature": c, "n": sub.height, "auc": float(roc_auc_score(sub["y"], sub["s"]))})
    return sorted(out, key=lambda x: -abs(x["auc"] - 0.5))


def analizar() -> tuple[str, list[dict]]:
    f = add_events(add_features(pl.read_parquet(PANEL)))
    # condición auxiliar: 3 meses seguidos de caja negativa (para el «hecho» de racha)
    f = f.sort("company_id", "month").with_columns(
        neg=(pl.col("cash_end") < 0).cast(pl.Int8).over("company_id"))
    f = f.with_columns(
        dec_cash_neg_3m=(pl.col("neg").rolling_sum(3, min_samples=3).over("company_id", order_by="month") == 3).cast(pl.Int8))
    hechos: list[dict] = []
    md: list[str] = ["# Análisis exploratorio data-lead (base de evidencia de las premisas)", ""]

    md.append("## 0 · Tamaño y tasas base\n")
    md.append(f"- Panel: **{f.height}** filas empresa×mes · **{f['company_id'].n_unique()}** empresas · "
              f"**{f['group_id'].n_unique()}** grupos.")
    md.append(f"- Ventana: {f['month'].min()} → {f['month'].max()}.")
    for e in EVENTOS:
        s = f.select(pl.col(e)).drop_nulls()
        if s.height:
            md.append(f"- `{e}`: tasa base **{float(s.mean().item()):.3f}** (n={s.height}).")
    md.append("")

    md.append("## 1 · Asociación observada candidato → evento (lo que dicen los datos)\n")
    md.append("Tasa del evento **dentro** de la condición vs **fuera**, con lift y AUC de la condición. "
              "Esto es lo que una premisa debe citar como evidencia; el test confirmatorio (con umbral "
              "congelado) va en la fase 2.\n")
    for nombre, cond, ambito in CANDIDATOS:
        fila = [f"### `{nombre}` — `{cond}`  ·  ámbito {ambito}\n",
                "| evento | tasa grupo | tasa base | lift | AUC | n |", "|---|---|---|---|---|---|"]
        for e in EVENTOS:
            if e not in f.columns:
                continue
            r = _lift(f, cond, e)
            hechos.append({"id": f"H{len(hechos)+1:03d}", "nombre": nombre, "condicion": cond,
                           "ambito": ambito, "evento": e, **r})
            tv = lambda x: f"{x:.3f}" if isinstance(x, float) else "—"
            fila.append(f"| {e} | {tv(r['tasa_grupo'])} | {tv(r['tasa_base'])} | {tv(r['lift'])} | {tv(r['auc'])} | {r['n']} |")
        md += fila + [""]

    md.append("## 2 · Poder discriminante de cada feature (AUC vs evento)\n")
    for e in EVENTOS:
        if e not in f.columns:
            continue
        md.append(f"### {e}\n")
        md.append("| feature | AUC | n |  | feature | AUC | n |")
        md.append("|---|---|---|---|---|---|---|")
        rows = _auc_features(f, e)
        for h in rows:
            hechos.append({"id": f"H{len(hechos)+1:03d}", "nombre": f"auc_{h['feature']}_{e}",
                           "condicion": h["feature"], "ambito": "feature", "evento": e,
                           "n": h["n"], "auc": h["auc"], "tasa_grupo": None, "tasa_base": None, "lift": None})
        for i in range(0, len(rows), 2):
            a = rows[i]
            b = rows[i + 1] if i + 1 < len(rows) else None
            left = f"| {a['feature']} | {a['auc']:.3f} | {a['n']} "
            right = f"| {b['feature']} | {b['auc']:.3f} | {b['n']} |" if b else "| | | |"
            md.append(left + right)
        md.append("")

    md.append("## 3 · Distribuciones y nulos de features\n")
    desc = f.select(SCORE_FEATURES).describe(percentiles=[0.05, 0.5, 0.95])
    md.append("```\n" + str(desc) + "\n```")
    nulls = f.select([pl.col(c).is_null().mean().alias(c) for c in SCORE_FEATURES])
    md.append("Tasa de nulos por feature:\n```\n" + str(nulls.transpose(include_header=True)) + "\n```\n")

    md.append("## 4 · Patrones temporales\n")
    activas = f.group_by("month").agg(pl.col("company_id").n_unique().alias("n")).sort("month")
    md.append("Empresas activas por mes (panel desbalanceado):\n```\n" + str(activas) + "\n```")
    neg = f.group_by("month").agg((pl.col("cash_end") < 0).mean().alias("frac_caja_neg")).sort("month")
    md.append("Fracción de empresas con caja negativa por mes:\n```\n" + str(neg) + "\n```\n")

    md.append("## 5 · Correlaciones (Spearman) entre features\n")
    X = f.select(SCORE_FEATURES).to_pandas()
    corr = X.corr(method="spearman")
    pairs = corr.where(np.triu(np.ones(corr.shape), 1).astype(bool)).stack().sort_values(key=abs, ascending=False)
    md.append("Top correlaciones (posible redundancia):\n```\n" + pairs.head(15).to_string() + "\n```\n")

    md.append("## 6 · Persistencia (autocorrelación lag-1)\n")
    ac = {c: f.select(pl.corr(pl.col(c), pl.col(c).shift(1).over("company_id", order_by="month"),
                              method="spearman")).item() for c in SCORE_FEATURES}
    md.append("```\n" + "\n".join(f"{k}: {v:.2f}" for k, v in ac.items() if v is not None) + "\n```\n")

    return "\n".join(md), hechos


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT / "analisis_datos.md"))
    ap.add_argument("--hechos", default=str(OUT / "hechos_datos.jsonl"))
    args = ap.parse_args()
    md, hechos = analizar()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md)
    with Path(args.hechos).open("w") as fh:
        for h in hechos:
            fh.write(json.dumps(h, ensure_ascii=False) + "\n")
    print(f"{len(hechos)} hechos → {args.hechos}")
    print(f"informe → {args.out}")


if __name__ == "__main__":
    main()
