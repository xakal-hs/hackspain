"""Materializa el panel de caja en `analysis/cash.duckdb` para que la app arranque al instante.

    .venv/Scripts/python.exe scripts/build_cash_db.py

Reconstruir el histórico cuesta unos 30 s de escaneo sobre los CSV. Guardarlo una vez evita
pagarlo en cada arranque de Streamlit; la app lo reconstruye sola si el fichero no existe.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from cash_history import (  # noqa: E402
    PANEL_TABLES,
    load_sources,
    persist_cash_panel,
    setup_cash_panel,
)

TARGET = ROOT / "analysis" / "cash.duckdb"
# Los maestros son pequeños y se copian; movimientos y facturas se quedan como vista mapeada.
MASTER_TABLES = (
    "groups",
    "companies",
    "banking_products",
    "debt_products",
    "debt_schedule_config",
    "balances",
)


def main() -> None:
    try:
        TARGET.unlink(missing_ok=True)
    except PermissionError:
        raise SystemExit(
            f"{TARGET.name} está en uso. Cierra la app de Streamlit antes de reconstruirlo."
        ) from None

    started = time.perf_counter()
    connection = duckdb.connect(str(TARGET))
    connection.execute("PRAGMA threads=4")

    load_sources(connection)
    setup_cash_panel(connection)
    persist_cash_panel(connection)

    # Los maestros pasan de vista a tabla para no depender del CSV en cada consulta.
    for name in MASTER_TABLES:
        connection.execute(f"CREATE OR REPLACE TABLE main.{name}_t AS SELECT * FROM {name}")
        connection.execute(f"DROP VIEW {name}")
        connection.execute(f"ALTER TABLE {name}_t RENAME TO {name}")
    connection.close()

    elapsed = time.perf_counter() - started
    size = TARGET.stat().st_size / 1_000_000
    print(f"Escrito {TARGET} ({size:.0f} MB) en {elapsed:.0f} s")
    print(f"Tablas del panel: {len(PANEL_TABLES)} · maestros: {len(MASTER_TABLES)}")


if __name__ == "__main__":
    main()
