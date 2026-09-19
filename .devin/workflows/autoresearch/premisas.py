"""Runner de premisas del agent council (workflow autoresearch).

Evalúa las premisas *verificables* del consejo contra el panel y los eventos del sistema,
y marca las de juicio humano/modelo. Es la pieza que hace que el bucle de autoresearch
sea medible en vez de opinable.

Uso (desde `research/`):
    uv run python ../.devin/workflows/autoresearch/premisas.py build   # cachea panel+features+eventos
    uv run python ../.devin/workflows/autoresearch/premisas.py run     # evalúa y escribe el informe
    uv run python ../.devin/workflows/autoresearch/premisas.py run --premisas salida/premisas.jsonl

Entrada: `salida/premisas.jsonl` si existe, si no `premisas.seed.jsonl` del workflow.
Salida:  `salida/premisas_resultado.jsonl` y `salida/premisas_resultado.md`.

Esquema de cada premisa (una por línea):
{
  "id": "P001", "rol": "prestamista", "ambito": "liquidez",
  "premisa": "...", "por_que": "...", "condicion": "...",
  "verificable": true,
  "test": {
    "tipo": "tasa_evento|auc|condicional|correlacion|cobertura|estadistico|banda|probabilidad|contribucion|ranking",
    "filtro": "expresión polars opcional",
    "objetivo": "columna 0/1 (tasa_evento, auc, condicional, ranking)",
    "variable": "columna (auc, correlacion, cobertura, estadistico, probabilidad)",
    "variable_b": "columna (correlacion)",
    "expr": "expresión polars alternativa a variable (estadistico, cobertura)",
    "condicion": "expresión polars que define el grupo (condicional)",
    "sobre": "p1|p0|lift (condicional); top1|top2|negativo (contribucion)",
    "banda": "riesgo|vigilar|sano (banda)",
    "razon": "feature cuya contribución debe explicar el movimiento (contribucion)",
    "orden": "columna de orden (ranking; por defecto score)",
    "n": "entero top-N o \"5%\" (ranking)",
    "ascendente": "true para orden ascendente (ranking)",
    "funcion": "mean|median|std|min|max (estadistico; por defecto mean)",
    "esperado": ">0.6 | <=0.25 | ==0 | !=0 | ~0.5 | entre 0.2 y 0.35"
  }
}

Columnas disponibles: las 40 del panel, las 17 features de `features.py`, los eventos de `targets.py`,
y las del score: `score`, `score_raw`, `band`, `confidence`, `coverage`, `ood_share`, `prob_*`,
`ec_<feature>` (contribución suavizada) y `dec_<feature>` (su cambio mes a mes). Con `--oof` también
`score_oof` (score fuera de grupo, para verificar en empresas no vistas).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import roc_auc_score

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
WF = Path(__file__).parent
OUT = WF / "salida"
PANEL = RES / "data" / "panel.parquet"
DERIVADO = OUT / "derivado.parquet"
SEED = WF / "premisas.seed.jsonl"
ART = RES / "artifacts" / "xray.joblib"

sys.path.insert(0, str(RES / "src"))
from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402
from xray import HealthScorer, band_of  # noqa: E402

EVENTOS = ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m", "tension_entrada_6m",
           "churn_6m", "cash_stress_6m", "decline_6m", "adverse_6m", "positive_6m"]


def _scorer() -> HealthScorer:
    """El scorer servido (artefacto) o, si no existe, uno entrenado como en service.train_and_save."""
    if ART.exists():
        import joblib
        return joblib.load(ART)["scorer"]
    from evaluate import EVENTS
    p = add_events(add_features(pl.read_parquet(PANEL))).to_pandas()
    obs = p.month <= p.month.max() - pd.DateOffset(months=6)
    return HealthScorer().fit(p, p[EVENTS].where(obs, axis=0))


def _score_frame(fp: pd.DataFrame, scorer: HealthScorer) -> pd.DataFrame:
    """Score, banda, probabilidades y contribuciones suavizadas (ec_*) por empresa-mes."""
    s = scorer.score_panel(fp)
    keep = ["company_id", "month", "score", "score_raw", "confidence", "coverage", "ood_share"]
    keep += [c for c in s.columns if c.startswith(("prob_", "ec_"))]
    return s[keep]


def _oof(f: pl.DataFrame, fp: pd.DataFrame, n_splits: int = 5) -> pl.DataFrame:
    """score_oof: score fuera de grupo (GroupKFold por group_id). Para verificar premisas en empresas no vistas."""
    from sklearn.model_selection import GroupKFold
    from evaluate import EVENTS
    parts = []
    for tr, te in GroupKFold(n_splits=n_splits).split(fp, groups=fp["group_id"].to_numpy()):
        obs = fp.iloc[tr].month <= fp.iloc[tr].month.max() - pd.DateOffset(months=6)
        sc = HealthScorer().fit(fp.iloc[tr], fp.iloc[tr][EVENTS].where(obs, axis=0))
        parts.append(sc.score_panel(fp.iloc[te])[["company_id", "month", "score"]].rename(columns={"score": "score_oof"}))
    return pl.from_pandas(pd.concat(parts, ignore_index=True))


def build(force: bool = False, oof: bool = False) -> pl.DataFrame:
    if DERIVADO.exists() and not force and not oof:
        return pl.read_parquet(DERIVADO)
    if not PANEL.exists():
        sys.exit(f"falta {PANEL}; ejecuta antes `uv run python src/panel.py` en research/")
    OUT.mkdir(parents=True, exist_ok=True)
    print("construyendo features, eventos y score...", flush=True)
    f = add_features(pl.read_parquet(PANEL))
    f = add_events(f)
    fp = f.to_pandas()
    scored = _score_frame(fp, _scorer())
    s = pl.from_pandas(scored)
    f = f.join(s, on=["company_id", "month"], how="left")
    f = f.with_columns(band=pl.when(pl.col("score") < 35).then(pl.lit("riesgo"))
                       .when(pl.col("score") < 65).then(pl.lit("vigilar")).otherwise(pl.lit("sano")))
    # delta mes a mes de cada contribución suavizada (para las premisas sobre la explicación)
    ecs = [c for c in f.columns if c.startswith("ec_")]
    f = f.sort("company_id", "month").with_columns(
        [(pl.col(c) - pl.col(c).shift(1).over("company_id")).alias("dec_" + c[3:]) for c in ecs])
    if oof:
        print("calculando score_oof (GroupKFold)...", flush=True)
        f = f.join(_oof(f, fp), on=["company_id", "month"], how="left")
    f.write_parquet(DERIVADO)
    return f


# ---------------------------------------------------------------- comparación
def cumple(valor, esperado) -> bool | None:
    if valor is None:
        return None
    e = str(esperado).strip()
    m = re.match(r"^entre\s+(-?[\d.]+)\s+y\s+(-?[\d.]+)$", e)
    if m:
        return float(m.group(1)) <= valor <= float(m.group(2))
    m = re.match(r"^(>=|<=|==|!=|>|<|~)\s*(-?[\d.]+)$", e)
    if not m:
        raise ValueError(f"esperado no reconocido: {e!r}")
    op, v = m.group(1), float(m.group(2))
    if op == "~":
        return abs(valor - v) <= 0.05
    if op == ">":
        return valor > v
    if op == "<":
        return valor < v
    if op == ">=":
        return valor >= v
    if op == "<=":
        return valor <= v
    if op == "==":
        return valor == v
    return valor != v


def _expr(test: dict) -> pl.Expr:
    return pl.sql_expr(test["expr"]) if test.get("expr") else pl.col(test["variable"])


def evaluar(df: pl.DataFrame, test: dict) -> dict:
    tipo = test.get("tipo")
    d = df.filter(pl.sql_expr(test["filtro"])) if test.get("filtro") else df
    extra: dict = {}

    if tipo == "tasa_evento":
        s = d.select(pl.col(test["objetivo"])).drop_nulls()
        valor, n = (float(s.mean().item()) if s.height else None), s.height
    elif tipo == "auc":
        sub = d.select([pl.col(test["objetivo"]).alias("y"), pl.col(test["variable"]).alias("s")]).drop_nulls()
        valor = float(roc_auc_score(sub["y"], sub["s"])) if sub["y"].n_unique() == 2 else None
        n = sub.height
    elif tipo == "condicional":
        col = test["objetivo"]
        mask = pl.sql_expr(test["condicion"])
        p1 = d.filter(mask).select(pl.col(col)).drop_nulls().mean().item()
        p0 = d.filter(~mask).select(pl.col(col)).drop_nulls().mean().item()
        p1, p0 = (float(p1) if p1 is not None else None), (float(p0) if p0 is not None else None)
        extra = {"p1": p1, "p0": p0, "lift": (p1 / p0) if p1 is not None and p0 else None}
        valor = extra[test.get("sobre", "p1")]
        n = d.drop_nulls(col).height
    elif tipo == "correlacion":
        sub = d.select([pl.col(test["variable"]).alias("a"), pl.col(test["variable_b"]).alias("b")]).drop_nulls()
        valor = float(sub.select(pl.corr(pl.col("a").rank(), pl.col("b").rank())).item()) if sub.height > 2 else None
        n = sub.height
    elif tipo == "cobertura":
        valor = float(d.select(_expr(test).is_not_null().mean()).item())
        n = d.height
    elif tipo == "estadistico":
        s = d.select(_expr(test).cast(pl.Float64, strict=False).alias("v")).drop_nulls()
        fn = test.get("funcion", "mean")
        valor = float(getattr(s["v"], fn)()) if s.height else None
        n = s.height
    elif tipo == "banda":
        s = d.select(pl.col("band")).drop_nulls()
        valor = float((s == test["banda"]).mean().item()) if s.height else None
        n = s.height
    elif tipo == "probabilidad":
        s = d.select(pl.col(test["variable"])).drop_nulls()
        valor = float(s.mean().item()) if s.height else None
        n = s.height
    elif tipo == "contribucion":
        # ¿la explicación del modelo señala la razón esperada? sobre = top1 | top2 | negativo
        razon, sobre = test["razon"], test.get("sobre", "top1")
        decs = [c for c in d.columns if c.startswith("dec_")]
        target = f"dec_{razon}"
        if target not in decs:
            raise ValueError(f"sin columna {target} (features: {[c[4:] for c in decs]})")
        M = d.select([pl.col(c).fill_null(0).alias(c) for c in decs]).to_numpy()
        ti = decs.index(target)
        if sobre == "negativo":
            valor = float((M[:, ti] < 0).mean())
        else:
            order = np.argsort(-np.abs(M), axis=1)
            k = 1 if sobre == "top1" else 2
            valor = float((order[:, :k] == ti).any(axis=1).mean())
        n = len(M)
    elif tipo == "ranking":
        # ¿la lista ordenada por `orden` separa el evento? n = entero (top-N) o "5%" (cuantil)
        orden, objetivo = test.get("orden", "score"), test["objetivo"]
        sub = d.drop_nulls([orden, objetivo])
        nreq = test["n"]
        k = max(1, int(len(sub) * float(nreq[:-1]) / 100)) if isinstance(nreq, str) and nreq.endswith("%") else int(nreq)
        sub = sub.sort(orden, descending=not test.get("ascendente", False))
        top = sub.head(k)
        valor = float(top.select(pl.col(objetivo)).mean().item()) if top.height else None
        base = float(sub.select(pl.col(objetivo)).mean().item()) if sub.height else None
        extra = {"base": base, "lift": (valor / base) if valor is not None and base else None, "k": k}
        n = len(sub)
    else:
        raise ValueError(f"tipo de test no reconocido: {tipo!r}")

    return {"valor": valor, "n": n, "extra": extra, "cumple": cumple(valor, test["esperado"])}


def _ejemplos(df: pl.DataFrame, test: dict, n: int = 6) -> list[dict]:
    """Hasta n filas empresa-mes que ejemplifican la situación, para inspeccionarla en la UI."""
    d = df.filter(pl.sql_expr(test["filtro"])) if test.get("filtro") else df
    if test.get("tipo") == "condicional":
        d = d.filter(pl.sql_expr(test["condicion"]))
    cols = ["company_id", "month"]
    for c in (test.get("objetivo"), test.get("variable"), test.get("orden"), "band"):
        if c and c in d.columns and c not in cols:
            cols.append(c)
    obj, var = test.get("objetivo"), test.get("variable") or test.get("orden")
    if test.get("tipo") == "contribucion" and f"dec_{test.get('razon')}" in d.columns:
        d = d.sort(pl.col(f"dec_{test['razon']}").abs().fill_null(0), descending=True, nulls_last=True)
    elif obj and obj in d.columns:
        d = d.sort(pl.col(obj).fill_null(0).cast(pl.Int8, strict=False), descending=True, nulls_last=True)
    elif var and var in d.columns:
        d = d.sort(pl.col(var).abs().fill_null(0), descending=True, nulls_last=True)
    out = []
    for row in d.select(cols).head(n).iter_rows(named=True):
        m = row["month"]
        row["month"] = m.strftime("%Y-%m") if hasattr(m, "strftime") else str(m)
        out.append(row)
    return out


def evaluar_premisa(df: pl.DataFrame, p: dict) -> dict:
    out = dict(p)
    if not p.get("verificable") or not p.get("test"):
        out.update(estado="no_verificable", resultado=None)
        return out
    try:
        r = evaluar(df, p["test"])
        out.update(estado=("pasa" if r["cumple"] else "falla") if r["cumple"] is not None else "no_verificable",
                   resultado={"valor": r["valor"], "n": r["n"], **r["extra"], "ejemplos": _ejemplos(df, p["test"])})
    except Exception as exc:  # una premisa mal formada no debe tumbar el informe
        out.update(estado="error", resultado={"error": f"{type(exc).__name__}: {exc}"})
    return out


def cargar_premisas(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"no existe {path}; pasa --premisas o crea premisas.seed.jsonl")
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def informe(resultados: list[dict]) -> str:
    from collections import Counter
    cuenta = Counter(r["estado"] for r in resultados)
    líneas = ["# Resultado de las premisas del consejo", "",
              f"Total: {len(resultados)} · " + " · ".join(f"{k}: {v}" for k, v in sorted(cuenta.items())), "",
              "| id | rol | ámbito | central | premisa | valor | esperado | n | estado |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in resultados:
        val = r.get("resultado") or {}
        v = val.get("valor")
        v = f"{v:.3f}" if isinstance(v, float) else ("" if v is None else str(v))
        exp = (r.get("test") or {}).get("esperado", "")
        prem = r["premisa"].replace("|", "/")
        prem = prem if len(prem) <= 90 else prem[:87] + "..."
        líneas.append(f"| {r['id']} | {r.get('rol','')} | {r.get('ambito','')} | {'sí' if r.get('central') else ''} | {prem} | {v} | {exp} | {val.get('n','')} | {r['estado']} |")
    return "\n".join(líneas) + "\n"


def cmd_build(args):
    df = build(force=True, oof=getattr(args, "oof", False))
    print(f"derivado: {df.shape[0]} filas × {df.shape[1]} columnas → {DERIVADO}")
    print("\ntasas base de los eventos (filas con etiqueta observable):")
    for e in EVENTOS:
        if e in df.columns:
            s = df.select(pl.col(e)).drop_nulls()
            if s.height:
                print(f"  {e:22s} {float(s.mean().item()):6.3f}  (n={s.height})")


def _fuente(args) -> Path:
    src = Path(args.premisas) if getattr(args, "premisas", None) else (OUT / "premisas.jsonl")
    return src if src.exists() else SEED


def cmd_run(args):
    df = build(force=False)
    src = _fuente(args)
    resultados = [evaluar_premisa(df, p) for p in cargar_premisas(src)]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "premisas_resultado.jsonl").open("w") as fh:
        for r in resultados:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / "premisas_resultado.md").write_text(informe(resultados))
    fallan = [r["id"] for r in resultados if r["estado"] == "falla"]
    print(f"{len(resultados)} premisas · {len(fallan)} fallan: {', '.join(fallan) or '—'}")
    print(f"informe: {OUT / 'premisas_resultado.md'}")


def cmd_export(args):
    """Escribe salida/situaciones.json (array) listo para servir en la UI."""
    df = build(force=False)
    resultados = [evaluar_premisa(df, p) for p in cargar_premisas(_fuente(args))]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "situaciones.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=1))
    print(f"{len(resultados)} situaciones → {OUT / 'situaciones.json'}")


TIPOS = {"tasa_evento", "auc", "condicional", "correlacion", "cobertura", "estadistico",
         "banda", "probabilidad", "contribucion", "ranking"}
REQ = {"tasa_evento": ["objetivo"], "auc": ["objetivo", "variable"], "condicional": ["objetivo", "condicion"],
       "correlacion": ["variable", "variable_b"], "cobertura": ["variable"], "estadistico": [],
       "banda": ["banda"], "probabilidad": ["variable"], "contribucion": ["razon"], "ranking": ["objetivo", "n"]}


def cmd_validate(args):
    """Valida el formato de las premisas SIN evaluarlas: congela los umbrales antes de ver resultados."""
    df = build(force=False)
    cols = set(df.columns)
    premisas = cargar_premisas(_fuente(args))
    ids = [p.get("id") for p in premisas]
    problemas, avisos = [], []
    for p in premisas:
        pid = p.get("id", "?")
        for k in ("premisa", "rol", "ambito"):
            if not p.get(k):
                problemas.append(f"{pid}: falta '{k}'")
        if not p.get("evidencia"):
            avisos.append(f"{pid}: sin 'evidencia' (data-lead: cada premisa cita su hecho de datos)")
        if not p.get("verificable"):
            if p.get("test"):
                problemas.append(f"{pid}: no verificable pero tiene test")
            continue
        t = p.get("test")
        if not t:
            problemas.append(f"{pid}: verificable sin test")
            continue
        tipo = t.get("tipo")
        if tipo not in TIPOS:
            problemas.append(f"{pid}: tipo desconocido {tipo!r}")
            continue
        for k in REQ[tipo]:
            if k not in t:
                problemas.append(f"{pid}: test.{tipo} sin '{k}'")
        if "esperado" not in t:
            problemas.append(f"{pid}: test sin 'esperado'")
        for k in ("objetivo", "variable", "variable_b", "orden"):
            c = t.get(k)
            if c and c not in cols:
                problemas.append(f"{pid}: columna desconocida '{c}'")
        if tipo == "contribucion" and f"dec_{t.get('razon')}" not in cols:
            problemas.append(f"{pid}: razón desconocida '{t.get('razon')}'")
        if tipo == "banda" and t.get("banda") not in ("riesgo", "vigilar", "sano"):
            problemas.append(f"{pid}: banda inválida {t.get('banda')!r}")
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        problemas.append(f"ids duplicados: {dup}")
    nver = sum(1 for p in premisas if p.get("verificable"))
    nev = sum(1 for p in premisas if p.get("evidencia"))
    print(f"{len(premisas)} premisas · {nver} verificables · {nev} con evidencia · {len(problemas)} problemas de formato")
    for x in problemas:
        print("  ✗", x)
    for x in avisos:
        print("  ⚠", x)
    sys.exit(1 if problemas else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="cachea panel+features+eventos+score en salida/derivado.parquet")
    b.add_argument("--oof", action="store_true", help="añade score_oof (GroupKFold, más lento)")
    for name, help_ in (("run", "evalúa las premisas y escribe el informe"),
                        ("export", "escribe salida/situaciones.json para la UI"),
                        ("validate", "solo valida el formato, sin evaluar (congela umbrales)")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--premisas", help="ruta al JSONL de premisas (por defecto salida/premisas.jsonl o la semilla)")
    args = ap.parse_args()
    {"build": cmd_build, "run": cmd_run, "export": cmd_export, "validate": cmd_validate}[args.cmd](args)


if __name__ == "__main__":
    main()
