"""Red de seguridad de la reestructuración: la salida del sistema no debe cambiar.

    python verificar.py baseline   # en main, ANTES de tocar nada
    python verificar.py check      # después de cada paquete de trabajo

Ejecuta los tests, reentrena el modelo, puntúa el train y compara con la línea base:
scores, probabilidades, pilares y previsión deben coincidir (tolerancia 1e-6).
Si un paquete mueve ficheros, actualiza TRAIN/PREDICT/TESTS aquí (y solo aquí) para apuntar a la nueva ruta.
"""
import subprocess, sys
from pathlib import Path
import pandas as pd

ROOT = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
RES = ROOT / "research"
OUT = Path(__file__).parent / "salida"
TESTS = ["uv", "run", "pytest", "-q", "tests"]
TRAIN = ["uv", "run", "python", "src/service.py"]
PREDICT = ["uv", "run", "python", "src/predict_submission.py", "--out"]
FILES = ["scores_monthly.csv", "forecast_latest.csv"]


def run(cmd):
    print("$", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, cwd=RES, check=True)


def main(mode: str) -> int:
    dest = OUT / ("baseline" if mode == "baseline" else "check")
    run(TESTS)
    run(TRAIN)
    run([*PREDICT, str(dest)])
    if mode == "baseline":
        print("línea base guardada en", dest)
        return 0
    bad = 0
    for f in FILES:
        a, b = pd.read_csv(OUT / "baseline" / f), pd.read_csv(dest / f)
        key = [c for c in ("company_id", "month") if c in a.columns and c in b.columns]
        a, b = a.sort_values(key), b.sort_values(key)
        if list(a.columns) != list(b.columns) or len(a) != len(b):
            print(f"✗ {f}: columnas o filas distintas ({a.shape} vs {b.shape})"); bad += 1; continue
        a, b = a.reset_index(drop=True), b.reset_index(drop=True)
        num = a.select_dtypes("number").columns
        diff = (a[num] - b[num]).abs().max().max() if len(num) else 0
        txt = [c for c in a.columns if c not in num and not a[c].fillna("").equals(b[c].fillna(""))]
        ok = diff <= 1e-6 and not txt
        print(("✓" if ok else "✗"), f, f"máx |Δ| numérico = {diff:.2e}", f"columnas de texto distintas: {txt}" if txt else "")
        bad += not ok
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check"))
