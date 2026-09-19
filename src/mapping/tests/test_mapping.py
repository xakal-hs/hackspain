from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mapping.catalogs import COUNTRY, ERP_CODE, TXN_CATEGORY
from mapping.load import attach


def _write_csv(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def write_fixture(directory: Path) -> None:
    _write_csv(
        directory / "groups.csv",
        ["group_id", "erp", "n_companies_in_sample"],
        [
            ["GROUP_0001", "Microsoft Business Central", 1],
            ["GROUP_0002", "Infor M3 ", 1],
        ],
    )
    _write_csv(
        directory / "companies.csv",
        ["company_id", "group_id", "country", "currency", "erp", "created_at"],
        [
            ["COMP_0001", "GROUP_0001", "ESPAÑA", "EUR", "businessCentral", "2024-01-15"],
            ["COMP_0002", "GROUP_0002", "ES", "EUR", "m3Rosetta", "2025-03-01"],
        ],
    )
    _write_csv(
        directory / "banking_products.csv",
        [
            "product_id",
            "company_id",
            "label",
            "type",
            "bank_name",
            "service",
            "currency",
            "created_at",
        ],
        [
            [
                "PRODUCT_00001",
                "COMP_0001",
                "CHECKING_01",
                "checking",
                "Paypal",
                "paypal",
                "EUR",
                "2024-02-01",
            ],
            [
                "PRODUCT_00003",
                "COMP_0001",
                "WALLET_01",
                "wallet",
                "Qonto ",
                "_payhawk",
                "EUR",
                "2024-02-01",
            ],
            [
                "PRODUCT_00004",
                "COMP_0002",
                "CHECKING_COP",
                "checking",
                "Bancolombia",
                "bancolombia",
                "COP",
                "2024-02-01",
            ],
        ],
    )
    _write_csv(
        directory / "debt_products.csv",
        [
            "product_id",
            "company_id",
            "label",
            "type",
            "bank_name",
            "service",
            "currency",
            "created_at",
            "granted",
            "outstanding",
            "liquidity",
        ],
        [
            [
                "PRODUCT_00002",
                "COMP_0001",
                "LOAN_01",
                "loan",
                "Otros",
                "_others",
                "EUR",
                "2024-02-01",
                -1000,
                -800,
                0,
            ]
        ],
    )
    _write_csv(
        directory / "debt_schedule_config.csv",
        [
            "product_id",
            "company_id",
            "settlement_product_id",
            "currency",
            "amortization_type",
            "interest_calc_method",
            "amortising_frequency",
            "granted_balance",
            "outstanding_balance",
            "total_periods",
            "next_payment_date",
            "last_payment_date",
            "annual_interest_rate_or_spread",
            "interest_type",
        ],
        [
            [
                "PRODUCT_00002",
                "COMP_0001",
                "PRODUCT_09999",
                "EUR",
                "constant quote",
                "30/360",
                "semiannually",
                1500,
                800,
                12,
                "2026-10-01",
                "2026-09-01",
                0.05,
                "fixed",
            ]
        ],
    )
    _write_csv(
        directory / "balances.csv",
        [
            "product_id",
            "company_id",
            "date",
            "balance",
            "available",
            "granted",
            "liquidity",
            "countable",
        ],
        [
            [
                "PRODUCT_00001",
                "COMP_0001",
                "2026-09-01",
                500,
                500,
                "",
                "",
                500,
            ],
            [
                "PRODUCT_00099",
                "COMP_0001",
                "2026-09-01",
                1e11,
                "",
                "",
                "",
                "",
            ],
            [
                "PRODUCT_00004",
                "COMP_0002",
                "2026-09-01",
                5e8,
                5e8,
                "",
                "",
                5e8,
            ],
            [
                "PRODUCT_00002",
                "COMP_0001",
                "2026-09-01",
                -3e8,
                "",
                -3e8,
                "",
                "",
            ],
        ],
    )
    _write_csv(
        directory / "transactions.csv",
        [
            "transaction_id",
            "company_id",
            "product_id",
            "date",
            "value_date",
            "amount",
            "exchange_rate",
            "status",
            "accounting_status",
            "category",
            "description",
            "counterparty_id",
        ],
        [
            [
                "txn-1",
                "COMP_0001",
                "PRODUCT_00001",
                "2025-01-15",
                "2099-12-31",
                -10,
                0,
                "booked",
                "",
                "-",
                "test",
                "COUNTERPARTY_123",
            ],
            [
                "txn-2",
                "COMP_0001",
                "PRODUCT_08229",
                "2025-02-01",
                "2025-02-01",
                25,
                1,
                "booked",
                "",
                "cash_settlements",
                "orphan product",
                "",
            ],
            [
                "txn-3",
                "COMP_0001",
                "PRODUCT_00001",
                "2025-03-01",
                "2025-03-01",
                1e9,
                1,
                "booked",
                "",
                "collection",
                "sentinel EUR",
                "",
            ],
            [
                "txn-4",
                "COMP_0002",
                "PRODUCT_00004",
                "2025-03-01",
                "2025-03-01",
                -2e9,
                1,
                "booked",
                "",
                "payment",
                "2e9 COP ~ 450k EUR",
                "",
            ],
        ],
    )
    _write_csv(
        directory / "invoices.csv",
        [
            "operation_id",
            "company_id",
            "document_type",
            "issuance_date",
            "due_date",
            "payment_date",
            "amount",
            "pending_amount",
            "currency",
            "accounting_currency",
            "exchange_rate",
            "status",
            "concept",
            "counterparty_id",
        ],
        [
            [
                "op-1",
                "COMP_0001",
                "invoice",
                "2025-01-01",
                "2025-02-01",
                "2025-02-01",
                100,
                100,
                "EUR",
                "EUR",
                1,
                "overdue",
                "alias due",
                "COUNTERPARTY_101540",
            ],
            [
                "op-2",
                "COMP_0001",
                "invoice",
                "2025-01-01",
                "2025-03-01",
                "2025-02-15",
                50,
                0,
                "EUR",
                "EUR",
                1,
                "cancel",
                "cancelled doc",
                "COUNTERPARTY_12",
            ],
            [
                "op-3",
                "COMP_0002",
                "invoice",
                "2026-10-01",
                "2026-11-01",
                "",
                0,
                0,
                "COP",
                "EUR",
                4400,
                "paid",
                "future, zero, no counterparty",
                "",
            ],
            [
                "op-4",
                "COMP_0002",
                "invoice",
                "2025-05-01",
                "2025-06-01",
                "",
                6e11,
                6e11,
                "COP",
                "EUR",
                4400,
                "pending",
                "6e11 COP ~ 136 MEUR",
                "COUNTERPARTY_100001",
            ],
        ],
    )


class CatalogTests(unittest.TestCase):
    def test_country_aliases(self) -> None:
        self.assertEqual(COUNTRY["España"], "ES")
        self.assertEqual(COUNTRY["ESPANYA"], "ES")
        self.assertEqual(COUNTRY["Portugal"], "PT")

    def test_erp_crosswalk(self) -> None:
        self.assertEqual(ERP_CODE["Microsoft Business Central"], "businessCentral")
        self.assertEqual(ERP_CODE["Desarrollo propio"], "inHouse")
        self.assertEqual(ERP_CODE["Infor M3"], "m3Rosetta")

    def test_category_aliases(self) -> None:
        self.assertEqual(TXN_CATEGORY["-"], "uncategorized")
        self.assertEqual(TXN_CATEGORY["cash_settlements"], "cash_settlement")


class AttachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import tempfile

        cls._tmp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls._tmp.name)
        write_fixture(cls.directory)
        import duckdb

        cls.con = attach(duckdb.connect(), cls.directory)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.con.close()
        cls._tmp.cleanup()

    def test_country_and_erp(self) -> None:
        row = self.con.execute(
            """
            SELECT country, country_raw, erp_code, observation_start, has_checking
            FROM companies WHERE company_id = 'COMP_0001'
            """
        ).fetchone()
        self.assertEqual(row[0], "ES")
        self.assertEqual(row[1], "ESPAÑA")
        self.assertEqual(row[2], "businessCentral")
        self.assertEqual(str(row[3]), "2024-09-01")
        self.assertTrue(row[4])

    def test_group_erp_whitespace(self) -> None:
        row = self.con.execute(
            "SELECT erp_code, erp_label FROM groups WHERE group_id = 'GROUP_0002'"
        ).fetchone()
        self.assertEqual(row[0], "m3Rosetta")
        self.assertEqual(row[1], "Infor M3")

    def test_transaction_category_and_counterparty(self) -> None:
        row = self.con.execute(
            """
            SELECT category, category_raw, counterparty_id, exchange_rate,
                   CAST(value_date_clean AS DATE)
            FROM transactions WHERE transaction_id = 'txn-1'
            """
        ).fetchone()
        self.assertEqual(row[0], "uncategorized")
        self.assertEqual(row[1], "-")
        self.assertEqual(row[2], "COUNTERPARTY_000123")
        self.assertIsNone(row[3])
        self.assertEqual(str(row[4]), "2025-01-15")

    def test_cash_settlements_typo(self) -> None:
        category = self.con.execute(
            "SELECT category FROM transactions WHERE transaction_id = 'txn-2'"
        ).fetchone()[0]
        self.assertEqual(category, "cash_settlement")

    def test_invoice_overdue_alias_and_status(self) -> None:
        overdue = self.con.execute(
            """
            SELECT payment_date, payment_date_was_due_alias, counterparty_id
            FROM invoices WHERE operation_id = 'op-1'
            """
        ).fetchone()
        self.assertIsNone(overdue[0])
        self.assertTrue(overdue[1])
        self.assertEqual(overdue[2], "COUNTERPARTY_101540")
        status = self.con.execute(
            "SELECT status, status_raw FROM invoices WHERE operation_id = 'op-2'"
        ).fetchone()
        self.assertEqual(status[0], "cancelled")
        self.assertEqual(status[1], "cancel")
        padded = self.con.execute(
            "SELECT counterparty_id FROM invoices WHERE operation_id = 'op-2'"
        ).fetchone()[0]
        self.assertEqual(padded, "COUNTERPARTY_000012")

    def test_bank_service_and_debt(self) -> None:
        bank = self.con.execute(
            "SELECT bank_name, type_family, service_kind FROM banking_products WHERE product_id = 'PRODUCT_00001'"
        ).fetchone()
        self.assertEqual(bank[0], "PayPal")
        self.assertEqual(bank[1], "cash_like")
        self.assertEqual(bank[2], "bank_service")
        wallet = self.con.execute(
            "SELECT bank_name, type_family, service FROM banking_products WHERE product_id = 'PRODUCT_00003'"
        ).fetchone()
        self.assertEqual(wallet[0], "Qonto")
        self.assertEqual(wallet[1], "cash_like")
        self.assertEqual(wallet[2], "payhawk")
        debt = self.con.execute(
            """
            SELECT bank_name, service, granted_liability, outstanding_liability
            FROM debt_products WHERE product_id = 'PRODUCT_00002'
            """
        ).fetchone()
        self.assertEqual(debt[0], "Other (customer-defined)")
        self.assertEqual(debt[1], "custom")
        self.assertEqual(debt[2], 1000)
        self.assertEqual(debt[3], 800)

    def test_schedule_and_products_registry(self) -> None:
        sched = self.con.execute(
            """
            SELECT amortization_type, amortising_frequency, settlement_product_id,
                   dq_settlement_orphan, dq_schedule_amount_mismatch
            FROM debt_schedule_config WHERE product_id = 'PRODUCT_00002'
            """
        ).fetchone()
        self.assertEqual(sched[0], "constant_installment")
        self.assertEqual(sched[1], "semi_annual")
        self.assertIsNone(sched[2])
        self.assertTrue(sched[3])
        self.assertTrue(sched[4])
        statuses = dict(
            self.con.execute(
                "SELECT product_id, catalog_status FROM products"
            ).fetchall()
        )
        self.assertEqual(statuses["PRODUCT_00001"], "in_catalog")
        self.assertEqual(statuses["PRODUCT_08229"], "txn_only")
        self.assertEqual(statuses["PRODUCT_00099"], "balance_only")
        self.assertEqual(statuses["PRODUCT_09999"], "settlement_only")

    def test_suspect_balance(self) -> None:
        quality = self.con.execute(
            "SELECT balance_quality FROM balances WHERE product_id = 'PRODUCT_00099'"
        ).fetchone()[0]
        self.assertEqual(quality, "suspect")

    def test_sentinel_is_measured_in_eur_and_only_on_cash(self) -> None:
        rows = dict(
            self.con.execute(
                "SELECT product_id, dq_balance_suspect FROM balances"
            ).fetchall()
        )
        self.assertTrue(rows["PRODUCT_00099"])   # sin catálogo: se asume caja en EUR
        self.assertFalse(rows["PRODUCT_00004"])  # 5e8 COP ≈ 113 k€: no es centinela
        self.assertFalse(rows["PRODUCT_00002"])  # préstamo de −3e8: deuda, no caja
        eur = self.con.execute(
            "SELECT balance_eur_approx FROM balances WHERE product_id = 'PRODUCT_00004'"
        ).fetchone()[0]
        self.assertLess(eur, 2e5)
        txn = dict(
            self.con.execute(
                "SELECT transaction_id, dq_amount_sentinel FROM transactions"
            ).fetchall()
        )
        self.assertTrue(txn["txn-3"])   # 1e9 EUR
        self.assertFalse(txn["txn-4"])  # 2e9 COP
        self.assertFalse(txn["txn-1"])

    def test_invoice_quality_flags(self) -> None:
        row = self.con.execute(
            """
            SELECT dq_amount_sentinel, dq_issued_after_snapshot, dq_amount_zero,
                   dq_counterparty_missing, counterparty_id
            FROM invoices WHERE operation_id = 'op-3'
            """
        ).fetchone()
        self.assertEqual(tuple(row[:4]), (False, True, True, True))
        self.assertIsNone(row[4])
        big = self.con.execute(
            "SELECT dq_amount_sentinel, dq_issued_after_snapshot FROM invoices WHERE operation_id = 'op-4'"
        ).fetchone()
        self.assertEqual(tuple(big), (True, False))


if __name__ == "__main__":
    unittest.main()
