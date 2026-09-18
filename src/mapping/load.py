"""Load raw CSVs as DuckDB views and attach the mapping layer on top.

CSV files under ``data/`` are never modified. Callers should read the
public view names (``companies``, ``transactions``, …) or the explicit
``*_mapped`` / ``raw_*`` variants.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from mapping.catalogs import RAW_TABLES
from mapping.sql import mapped_view_statements

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "data"


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def raw_view_sql(name: str, data_dir: Path) -> str:
    csv_path = data_dir / f"{name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing dataset file: {csv_path}")
    escaped = _sql_path(csv_path)
    return (
        f"CREATE OR REPLACE VIEW raw_{name} AS "
        f"SELECT * FROM read_csv_auto('{escaped}', sample_size=-1)"
    )


def attach(
    connection: duckdb.DuckDBPyConnection,
    data_dir: str | Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Register ``raw_*``, ``*_mapped`` and public aliases on ``connection``."""
    directory = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    for name in RAW_TABLES:
        connection.execute(raw_view_sql(name, directory))
    for statement in mapped_view_statements():
        connection.execute(statement)
    return connection


def connect(data_dir: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    return attach(duckdb.connect(), data_dir)
