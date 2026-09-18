"""Canonical value maps for the X-Ray dataset.

Raw CSVs are never rewritten. These dictionaries are applied at load time.
Closed vocabularies (country, ERP) send unknown non-null values to
``UNMAPPED`` so audit can catch new dirt. Open fields (bank_name, service)
apply known aliases and otherwise pass through after trim.
"""

from __future__ import annotations

UNMAPPED = "_unmapped"

WINDOW_START = "2024-09-01"
WINDOW_END = "2026-09-01"
BALANCE_SUSPECT_ABS = 1e8
VALUE_DATE_MAX_GAP_DAYS = 30
VALUE_DATE_SENTINEL_YEAR = 2090
COUNTERPARTY_PAD = 6

# Dirty or mixed labels → ISO-3166 alpha-2. Already-canonical 2-letter codes
# are accepted by the SQL layer via length=2, not only via this dict.
COUNTRY: dict[str, str] = {
    "ESPAÑA": "ES",
    "España": "ES",
    "ESPANYA": "ES",
    "Espanya": "ES",
    "Spain": "ES",
    "Portugal": "PT",
    "Italia": "IT",
    "Alemania": "DE",
    "Malaysia": "MY",
}

# Any observed group label or company code → company-style erp_code.
ERP_CODE: dict[str, str] = {
    "Microsoft Business Central": "businessCentral",
    "businessCentral": "businessCentral",
    "Netsuite": "netsuite",
    "netsuite": "netsuite",
    "Microsoft Navision": "navision",
    "navision": "navision",
    "SAP Business One": "businessOne",
    "businessOne": "businessOne",
    "Sage 200": "sage200",
    "sage200": "sage200",
    "Sage X3": "sageX3",
    "sageX3": "sageX3",
    "Sage 50": "sage50",
    "sage50": "sage50",
    "SAP R3 / S4": "r3",
    "r3": "r3",
    "A3 ERP": "a3",
    "a3": "a3",
    "Microsoft Dynamics - F&O": "fo",
    "fo": "fo",
    "Microsoft Dynamics - AX 2012": "dynamicsAx",
    "Microsoft Dynamics - AX 2009": "dynamicsAx",
    "dynamicsAx": "dynamicsAx",
    "LIBRA": "libra",
    "libra": "libra",
    "Desarrollo propio": "inHouse",
    "inHouse": "inHouse",
    "MOVEX": "m3Rosetta",
    "Infor M3": "m3Rosetta",
    "m3Rosetta": "m3Rosetta",
    "Distrito K": "distritoK",
    "distritoK": "distritoK",
    "Odoo": "odoo",
    "odoo": "odoo",
    "Oracle Cloud": "oracleCloud",
    "oracleCloud": "oracleCloud",
    "Holded": "holded",
    "holded": "holded",
    "Etendo": "etendo",
    "etendo": "etendo",
    "Sage Intacct": "sageIntacct",
    "sageIntacct": "sageIntacct",
    "Ekon": "ekon",
    "ekon": "ekon",
    "DATEV": "datev",
    "datev": "datev",
    "SAP ByDesign": "sapByd",
    "sapByd": "sapByd",
}

# Any observed label or code → stable display name.
ERP_LABEL: dict[str, str] = {
    "Microsoft Business Central": "Microsoft Business Central",
    "businessCentral": "Microsoft Business Central",
    "Netsuite": "Netsuite",
    "netsuite": "Netsuite",
    "Microsoft Navision": "Microsoft Navision",
    "navision": "Microsoft Navision",
    "SAP Business One": "SAP Business One",
    "businessOne": "SAP Business One",
    "Sage 200": "Sage 200",
    "sage200": "Sage 200",
    "Sage X3": "Sage X3",
    "sageX3": "Sage X3",
    "Sage 50": "Sage 50",
    "sage50": "Sage 50",
    "SAP R3 / S4": "SAP R3 / S4",
    "r3": "SAP R3 / S4",
    "A3 ERP": "A3 ERP",
    "a3": "A3 ERP",
    "Microsoft Dynamics - F&O": "Microsoft Dynamics - F&O",
    "fo": "Microsoft Dynamics - F&O",
    "Microsoft Dynamics - AX 2012": "Microsoft Dynamics - AX",
    "Microsoft Dynamics - AX 2009": "Microsoft Dynamics - AX",
    "dynamicsAx": "Microsoft Dynamics - AX",
    "LIBRA": "LIBRA",
    "libra": "LIBRA",
    "Desarrollo propio": "Desarrollo propio",
    "inHouse": "Desarrollo propio",
    "MOVEX": "Infor M3",
    "Infor M3": "Infor M3",
    "m3Rosetta": "Infor M3",
    "Distrito K": "Distrito K",
    "distritoK": "Distrito K",
    "Odoo": "Odoo",
    "odoo": "Odoo",
    "Oracle Cloud": "Oracle Cloud",
    "oracleCloud": "Oracle Cloud",
    "Holded": "Holded",
    "holded": "Holded",
    "Etendo": "Etendo",
    "etendo": "Etendo",
    "Sage Intacct": "Sage Intacct",
    "sageIntacct": "Sage Intacct",
    "Ekon": "Ekon",
    "ekon": "Ekon",
    "DATEV": "DATEV",
    "datev": "DATEV",
    "SAP ByDesign": "SAP ByDesign",
    "sapByd": "SAP ByDesign",
}

TXN_CATEGORY: dict[str, str] = {
    "-": "uncategorized",
    "cash_settlements": "cash_settlement",
}

INVOICE_STATUS: dict[str, str] = {
    "cancel": "cancelled",
    "paymentOrder": "payment_order",
}

BANK_NAME: dict[str, str] = {
    "Paypal": "PayPal",
    "iberCaja": "Ibercaja",
    "BANCO SANTANDER TOTTA SA": "Banco Santander Totta SA",
    "Otros": "Other (customer-defined)",
}

SERVICE: dict[str, str] = {
    "others": "custom",
    "_others": "custom",
}

AMORTIZATION_TYPE: dict[str, str] = {
    "constant quote": "constant_installment",
}

AMORTISING_FREQUENCY: dict[str, str] = {
    "semiannually": "semi_annual",
}

# Banking extras (wallet, risk, lineofcomex) stay as type; family groups them.
TYPE_FAMILY: dict[str, str] = {
    "checking": "cash_like",
    "saving": "cash_like",
    "wallet": "cash_like",
    "expensesPlatform": "cash_like",
    "card": "operating",
    "tpv": "operating",
    "investment": "operating",
    "risk": "credit_adjacent",
    "lineofcomex": "credit_adjacent",
    "loan": "term_debt",
    "leasing": "term_debt",
    "mortgage": "term_debt",
    "renting": "term_debt",
    "lineofcredit": "working_capital",
    "factoring": "working_capital",
    "confirming": "working_capital",
    "guarantee": "contingent",
}

RAW_TABLES = (
    "groups",
    "companies",
    "banking_products",
    "debt_products",
    "debt_schedule_config",
    "balances",
    "invoices",
    "transactions",
)
