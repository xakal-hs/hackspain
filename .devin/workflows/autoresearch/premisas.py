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
    "tipo": "tasa_evento|auc|condicional|correlacion|cobertura|estadistico",
    "filtro": "expresión polars opcional",
    "objetivo": "columna 0/1 (tasa_evento, auc, condicional)",
    "variable": "columna (auc, correlacion, cobertura, estadistico)",
    "variable_b": "columna (correlacion)",
    "expr": "expresión polars alternativa a variable (estadistico, cobertura)",
    "condicion": "expresión polars que define el grupo (condicional)",
    "sobre": "p1|p0|lift (condicional; por defecto p1)",
    "funcion": "mean|median|std|min|max (estadistico; por defecto mean)",
    "esperado": ">0.6 | <=0.25 | ==0 | !=0 | ~0.5 | entre 0.2 y 0.35"
  }
}
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import polars as pl
from sklearn.metrics import roc_auc_score

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
WF = Path(__file__).parent
OUT = WF / "salida"
PANEL = RES / "data" / "panel.parquet"
DERIVADO = OUT / "derivado.parquet"
SEED = WF / "premisas.seed.jsonl"

sys.path.insert(0, str(RES / "src"))
from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402

EVENTOS = ["tension_6m", "incumplimiento_6m", "caida_6m", "expansion_6m", "tension_entrada_6m",
           "churn_6m", "cash_stress_6m", "decline_6m", "adverse_6m", "positive_6m"]


def build(force: bool = False) -> pl.DataFrame:
    if DERIVADO.exists() and not force:
        return pl.read_parquet(DERIVADO)
    if not PANEL.exists():
        sys.exit(f"falta {PANEL}; ejecuta antes `uv run python src/panel.py` en research/")
    OUT.mkdir(parents=True, exist_ok=True)
    print("construyendo features y eventos...", flush=True)
    f = add_features(pl.read_parquet(PANEL))
    f = add_events(f)
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
    else:
        raise ValueError(f"tipo de test no reconocido: {tipo!r}")

    return {"valor": valor, "n": n, "extra": extra, "cumple": cumple(valor, test["esperado"])}


def _ejemplos(df: pl.DataFrame, test: dict, n: int = 6) -> list[dict]:
    """Hasta n filas empresa-mes que ejemplifican la situación, para inspeccionarla en la UI."""
    d = df.filter(pl.sql_expr(test["filtro"])) if test.get("filtro") else df
    if test.get("tipo") == "condicional":
        d = d.filter(pl.sql_expr(test["condicion"]))
    cols = ["company_id", "month"]
    for c in (test.get("objetivo"), test.get("variable")):
        if c and c in d.columns and c not in cols:
            cols.append(c)
    obj, var = test.get("objetivo"), test.get("variable")
    if obj and obj in d.columns:
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
    df = build(force=True)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="cachea panel+features+eventos en salida/derivado.parquet")
    for name, help_ in (("run", "evalúa las premisas y escribe el informe"),
                        ("export", "escribe salida/situaciones.json para la UI")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--premisas", help="ruta al JSONL de premisas (por defecto salida/premisas.jsonl o la semilla)")
    args = ap.parse_args()
    {"build": cmd_build, "run": cmd_run, "export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    main()
