"""Recupera los ficheros de `.devin/workflows/autoresearch/salida/` desde la base de sesiones de la CLI.

`salida/` está gitignorado, así que al borrarse el worktree `hackspain-council` no quedó copia en git.
Pero cada escritura pasó por una tool call, y `sessions.db` guarda los diffs (`oldText`/`newText`).
Este script los reproduce en orden cronológico y reconstruye el contenido final de cada fichero.

Escribe en un directorio de STAGING; no pisa nada. Revisa y copia después.

    python3 scripts/recuperar_salida.py [--staging <dir>]
"""
import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path.home() / ".local/share/devin/cli/sessions.db"
MARCA = "/.devin/workflows/autoresearch/salida/"


def diffs_por_fichero(db: Path):
    """[(rel, oldText, newText)] en orden cronológico (row_id de la tabla)."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    q = "select session_id, tool_call_json from tool_call_state where tool_call_json is not null order by rowid"
    for sid, tcj in con.execute(q):
        try:
            d = json.loads(tcj)
        except Exception:
            continue
        for item in d.get("content") or []:
            if item.get("type") != "diff":
                continue
            p = item.get("path") or ""
            if MARCA not in p:
                continue
            yield p.split(MARCA, 1)[1], item.get("oldText") or "", item.get("newText") or "", sid


def heredocs(db: Path):
    """Segunda vía: ficheros escritos con `cat > ruta <<'EOF' ... EOF` dentro de un comando."""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    pat = re.compile(r"cat\s*>\s*['\"]?([^\s'\"]*" + re.escape(MARCA[1:]) + r"[^\s'\"]+)['\"]?\s*<<\s*'?(\w+)'?\n(.*?)\n\2",
                     re.DOTALL)
    q = "select tool_call_json from tool_call_state where tool_call_json like '%salida/%' order by rowid"
    for (tcj,) in con.execute(q):
        for m in pat.finditer(tcj or ""):
            ruta, _, cuerpo = m.groups()
            if MARCA in "/" + ruta:
                rel = ("/" + ruta).split(MARCA, 1)[1]
                yield rel, cuerpo.encode().decode("unicode_escape", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default=str(Path.cwd() / ".devin/workflows/autoresearch/salida_recuperado"))
    ap.add_argument("--base", default=str(Path.cwd() / ".devin/workflows/autoresearch/salida"),
                    help="salida/ superviviente: siembra la base para poder aplicar ediciones parciales")
    a = ap.parse_args()
    out = Path(a.staging)
    out.mkdir(parents=True, exist_ok=True)

    # siembra: los ficheros que sobrevivieron son la base sobre la que se aplicaron las ediciones de la tarde
    estado: dict[str, str] = {}
    base = Path(a.base)
    if base.is_dir():
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in {".md", ".jsonl", ".py", ".json", ".sh", ".txt"}:
                try:
                    estado[str(p.relative_to(base))] = p.read_text()
                except Exception:
                    pass
        print(f"sembrados {len(estado)} ficheros de {base}")
    fallos: dict[str, int] = defaultdict(int)
    n_ops = 0
    for rel, old, new, _sid in diffs_por_fichero(DB):
        n_ops += 1
        if not old:                       # creación / sobrescritura completa
            estado[rel] = new
        elif rel in estado and old in estado[rel]:
            estado[rel] = estado[rel].replace(old, new, 1)
        elif not new:                      # borrado de un trozo sin base: se ignora
            fallos[rel] += 1
        else:
            # edición parcial sin base conocida: se guarda aparte para revisión manual
            fallos[rel] += 1
            estado.setdefault(rel, "")
            estado[rel] += ("\n\n<<<< FRAGMENTO RECUPERADO SIN BASE >>>>\n" + new)

    for rel, cuerpo in heredocs(DB):
        estado.setdefault(rel, cuerpo)

    escritos = 0
    for rel, cuerpo in sorted(estado.items()):
        if not cuerpo.strip():
            continue
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(cuerpo)
        escritos += 1

    print(f"{n_ops} operaciones de diff procesadas")
    print(f"{escritos} ficheros reconstruidos en {out}")
    if fallos:
        print(f"\n{len(fallos)} ficheros con ediciones parciales sin base completa (revisar):")
        for rel, k in sorted(fallos.items(), key=lambda x: -x[1])[:25]:
            print(f"  {rel}: {k} fragmento(s)")


if __name__ == "__main__":
    main()
