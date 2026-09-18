"""Comprueba la reconstrucción del histórico de caja contra el saldo de 2026-09-01.

    .venv\\Scripts\\python.exe scripts\\validate_cash.py

Imprime las comprobaciones que respaldan las secciones de caja del informe: cuadre con el
ancla, impacto de los valores centinela, cobertura de divisas y deriva del back-cast.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))

from cash_history import setup_cash_panel  # noqa: E402

TABLES = ("groups", "companies", "banking_products", "debt_products", "balances", "transactions")


def show(connection: duckdb.DuckDBPyConnection, title: str, sql: str, limit: int = 30) -> None:
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)
    cursor = connection.execute(sql)
    print(" | ".join(column[0] for column in cursor.description))
    for row in cursor.fetchall()[:limit]:
        print(" | ".join("NULL" if value is None else str(value) for value in row))


def main() -> None:
    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    for name in TABLES:
        path = (ROOT / "data" / f"{name}.csv").as_posix()
        connection.execute(
            f"CREATE VIEW {name} AS SELECT * FROM read_csv_auto('{path}', sample_size=-1)"
        )
    setup_cash_panel(connection)

    show(
        connection,
        "Cuadre con el saldo ancla",
        """
        WITH final_month AS (
            SELECT product_id, cash_native FROM panel_product
            WHERE month_start = DATE '2026-09-01'
        )
        SELECT count(*) AS productos,
               count(*) FILTER (WHERE abs(f.cash_native - cp.anchor_balance) < 0.01) AS cuadran,
               max(abs(f.cash_native - cp.anchor_balance)) AS desvio_max
        FROM final_month f JOIN cash_product cp USING (product_id)
        """,
    )
    show(
        connection,
        "Valores centinela retirados y empresas afectadas",
        """
        SELECT (SELECT count(*) FROM tx_cash WHERE is_sentinel) AS movimientos_centinela,
               (SELECT count(*) FROM sentinel_tx) AS empresas_con_movimiento,
               (SELECT count(*) FROM cash_product WHERE is_artifact) AS cuentas_centinela,
               (SELECT count(*) FROM company_flags WHERE NOT is_reliable) AS empresas_no_fiables,
               (SELECT count(*) FROM cash_summary WHERE has_drift) AS empresas_con_deriva
        """,
    )
    show(
        connection,
        "Divisas sin evidencia de tipo de cambio (excluidas del panel en EUR)",
        "SELECT * FROM fx_gap ORDER BY n_products DESC",
    )
    show(
        connection,
        "Panel mensual: cobertura, nivel y caja negativa",
        """
        SELECT strftime(month_start, '%Y-%m') AS mes, count(*) AS empresas,
               round(median(cash_eur), 0) AS caja_mediana,
               count(*) FILTER (WHERE cash_eur < 0) AS en_negativo
        FROM cash_metrics GROUP BY 1 ORDER BY 1
        """,
    )
    show(
        connection,
        "Diagnóstico en el último mes observado",
        """
        SELECT diagnosis, count(*) AS empresas, round(median(coverage), 2) AS colchon_meses
        FROM cash_summary GROUP BY 1 ORDER BY empresas DESC
        """,
    )


if __name__ == "__main__":
    main()
