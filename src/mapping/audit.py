"""Report residual dirt after the mapping layer is applied.

Usage (from repo root):

    PYTHONPATH=src python -m mapping.audit
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

from mapping.load import DEFAULT_DATA_DIR, attach


def _count(connection: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(connection.execute(sql).fetchone()[0])


def collect(connection: duckdb.DuckDBPyConnection) -> dict[str, object]:
    leftover_banks = connection.execute(
        """
        SELECT bank_name_raw, count(*) AS n
        FROM (
            SELECT bank_name_raw FROM banking_products_mapped
            UNION ALL
            SELECT bank_name_raw FROM debt_products_mapped
        )
        WHERE bank_name_raw IN ('Paypal', 'iberCaja', 'Otros', 'BANCO SANTANDER TOTTA SA')
           OR bank_name_raw LIKE '% '
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchall()
    unmapped_countries = connection.execute(
        """
        SELECT country_raw, count(*) AS n
        FROM companies_mapped
        WHERE dq_country_unmapped
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchall()
    unmapped_erp = connection.execute(
        """
        SELECT source, erp_raw, n FROM (
            SELECT 'companies' AS source, erp_raw, count(*) AS n
            FROM companies_mapped WHERE dq_erp_unmapped GROUP BY 2
            UNION ALL
            SELECT 'groups', erp_raw, count(*)
            FROM groups_mapped WHERE dq_erp_unmapped GROUP BY 2
        )
        ORDER BY n DESC
        """
    ).fetchall()
    catalog = connection.execute(
        """
        SELECT catalog_status, count(*) AS n
        FROM products_mapped
        GROUP BY 1
        ORDER BY n DESC
        """
    ).fetchall()
    return {
        "country_unmapped": unmapped_countries,
        "erp_unmapped": unmapped_erp,
        "txn_category_dash": _count(
            connection,
            "SELECT count(*) FROM transactions_mapped WHERE category_raw = '-'",
        ),
        "txn_category_still_dash": _count(
            connection,
            "SELECT count(*) FROM transactions_mapped WHERE category = '-'",
        ),
        "txn_uncategorized": _count(
            connection,
            "SELECT count(*) FROM transactions_mapped WHERE category = 'uncategorized'",
        ),
        "txn_cash_settlements_raw": _count(
            connection,
            "SELECT count(*) FROM transactions_mapped WHERE category_raw = 'cash_settlements'",
        ),
        "invoice_overdue_due_alias": _count(
            connection,
            "SELECT count(*) FROM invoices_mapped WHERE payment_date_was_due_alias",
        ),
        "schedule_amount_mismatch": _count(
            connection,
            "SELECT count(*) FROM debt_schedule_config_mapped WHERE dq_schedule_amount_mismatch",
        ),
        "settlement_orphans": _count(
            connection,
            "SELECT count(*) FROM debt_schedule_config_mapped WHERE dq_settlement_orphan",
        ),
        "balance_suspect": _count(
            connection,
            "SELECT count(*) FROM balances_mapped WHERE dq_balance_suspect",
        ),
        "companies_without_checking": _count(
            connection,
            "SELECT count(*) FROM companies_mapped WHERE NOT has_checking",
        ),
        "companies_balance_missing": _count(
            connection,
            "SELECT count(*) FROM companies_mapped WHERE balance_missing",
        ),
        "companies_without_invoices": _count(
            connection,
            "SELECT count(*) FROM companies_mapped WHERE NOT has_invoices",
        ),
        "catalog_status": catalog,
        "leftover_bank_raw": leftover_banks,
    }


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    data_dir = Path(args[0]) if args else DEFAULT_DATA_DIR
    connection = attach(duckdb.connect(), data_dir)
    report = collect(connection)
    printable = {
        key: (
            [list(row) for row in value]
            if isinstance(value, list) and value and isinstance(value[0], tuple)
            else value
        )
        for key, value in report.items()
    }
    json.dump(printable, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
