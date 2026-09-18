"""Comprueba que el panel de caja sale idéntico en tres construcciones independientes.

La reconstrucción suma importes en coma flotante y DuckDB agrega en paralelo, así que el orden
de la suma cambia entre ejecuciones. Cuando el resultado ronda el cero, el signo baila y con él
el diagnóstico. Este script existe para que esa clase de fuga no vuelva a pasar desapercibida:
si un recuento cambia entre construcciones, hay un umbral apoyado en ruido binario.
"""

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from cash_history import load_sources, setup_cash_panel  # noqa: E402

CHECKS = {
    "empresas": "SELECT count(*) FROM cash_summary",
    "en negativo": "SELECT count(*) FROM cash_summary WHERE cash_eur < 0",
    "con deriva": "SELECT count(*) FROM cash_summary WHERE has_drift",
    "suma de caja": "SELECT round(sum(cash_eur), 2) FROM cash_summary",
    "filas del panel": "SELECT count(*) FROM panel_company",
    "suma del panel": "SELECT round(sum(cash_eur), 2) FROM panel_company",
    "diagnósticos": (
        "SELECT string_agg(diagnosis || ':' || n, ' ') FROM ("
        "SELECT diagnosis, count(*) AS n FROM cash_summary GROUP BY 1 ORDER BY 1)"
    ),
}


def build() -> dict[str, object]:
    connection = duckdb.connect()
    load_sources(connection)
    setup_cash_panel(connection)
    return {key: connection.execute(sql).fetchone()[0] for key, sql in CHECKS.items()}


def main() -> None:
    runs = [build() for _ in range(3)]
    stable = True
    for key in CHECKS:
        values = [run[key] for run in runs]
        same = len({str(value) for value in values}) == 1
        stable &= same
        mark = "ok " if same else "DIF"
        print(f"{mark} {key}: {' | '.join(str(value) for value in values)}")

    if not stable:
        raise SystemExit("El panel no es reproducible: revisa los umbrales sobre importes.")


if __name__ == "__main__":
    main()
