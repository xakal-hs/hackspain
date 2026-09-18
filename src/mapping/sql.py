"""DuckDB view SQL for raw CSV files and their mapped counterparts."""

from __future__ import annotations

from mapping.catalogs import (
    AMORTISING_FREQUENCY,
    AMORTIZATION_TYPE,
    BALANCE_SUSPECT_ABS,
    BANK_NAME,
    COUNTERPARTY_PAD,
    COUNTRY,
    ERP_CODE,
    ERP_LABEL,
    INVOICE_STATUS,
    SERVICE,
    TXN_CATEGORY,
    TYPE_FAMILY,
    UNMAPPED,
    VALUE_DATE_MAX_GAP_DAYS,
    VALUE_DATE_SENTINEL_YEAR,
    WINDOW_END,
    WINDOW_START,
)


def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def case_from_map(
    expr: str,
    mapping: dict[str, str],
    *,
    null_to: str | None = None,
    passthrough: bool = True,
    unmapped: str = UNMAPPED,
) -> str:
    parts = ["CASE"]
    if null_to is None:
        parts.append(f"WHEN {expr} IS NULL THEN NULL")
    else:
        parts.append(f"WHEN {expr} IS NULL THEN {sql_str(null_to)}")
    inverse: dict[str, list[str]] = {}
    for src, dst in mapping.items():
        inverse.setdefault(dst, []).append(src)
    for dst, srcs in inverse.items():
        in_list = ", ".join(sql_str(s) for s in srcs)
        parts.append(f"WHEN {expr} IN ({in_list}) THEN {sql_str(dst)}")
    if passthrough:
        parts.append(f"ELSE {expr}")
    else:
        parts.append(f"ELSE {sql_str(unmapped)}")
    parts.append("END")
    return " ".join(parts)


def _trimmed(column: str) -> str:
    return f"nullif(trim(CAST({column} AS VARCHAR)), '')"


def _country_expr(column: str = "country") -> str:
    trimmed = _trimmed(column)
    mapped = case_from_map(trimmed, COUNTRY, passthrough=False)
    return (
        "CASE "
        f"WHEN {trimmed} IS NULL THEN NULL "
        f"WHEN length({trimmed}) = 2 THEN upper({trimmed}) "
        f"ELSE {mapped} "
        "END"
    )


def _erp_code_expr(column: str = "erp") -> str:
    return case_from_map(_trimmed(column), ERP_CODE, passthrough=False)


def _erp_label_expr(column: str = "erp") -> str:
    return case_from_map(_trimmed(column), ERP_LABEL, passthrough=False)


def _counterparty_expr(column: str = "counterparty_id") -> str:
    digits = f"regexp_extract(CAST({column} AS VARCHAR), '([0-9]+)$', 1)"
    return (
        "CASE "
        f"WHEN {column} IS NULL OR trim(CAST({column} AS VARCHAR)) = '' THEN NULL "
        f"WHEN {digits} = '' THEN CAST({column} AS VARCHAR) "
        f"ELSE 'COUNTERPARTY_' || lpad({digits}, {COUNTERPARTY_PAD}, '0') "
        "END"
    )


def _service_clean_expr(column: str = "service") -> str:
    stripped = f"regexp_replace({_trimmed(column)}, '^_', '')"
    mapped = case_from_map(stripped, SERVICE, passthrough=True)
    return mapped


def _service_kind_expr(raw_col: str = "service_raw", clean_col: str = "service") -> str:
    return (
        "CASE "
        f"WHEN {clean_col} IS NULL THEN NULL "
        f"WHEN {clean_col} = 'custom' THEN 'custom' "
        f"WHEN CAST({raw_col} AS VARCHAR) LIKE 'ins_%' THEN 'connector_id' "
        f"WHEN {clean_col} LIKE 'ins_%' THEN 'connector_id' "
        "ELSE 'bank_service' "
        "END"
    )


def _type_family_expr(column: str = "type") -> str:
    return case_from_map(
        f"CAST({column} AS VARCHAR)",
        TYPE_FAMILY,
        passthrough=False,
    )


def groups_mapped_sql() -> str:
    return f"""
    CREATE OR REPLACE VIEW groups_mapped AS
    SELECT
        group_id,
        erp AS erp_raw,
        {_erp_code_expr("erp")} AS erp_code,
        {_erp_label_expr("erp")} AS erp_label,
        {_erp_code_expr("erp")} AS erp,
        n_companies_in_sample,
        ({_erp_code_expr("erp")} = {sql_str(UNMAPPED)}) AS dq_erp_unmapped
    FROM raw_groups
    """


def companies_mapped_sql() -> str:
    country = _country_expr("country")
    erp_code = _erp_code_expr("erp")
    return f"""
    CREATE OR REPLACE VIEW companies_mapped AS
    WITH checking AS (
        SELECT DISTINCT company_id
        FROM raw_banking_products
        WHERE type = 'checking'
    ),
    invoiced AS (
        SELECT DISTINCT company_id FROM raw_invoices
    ),
    balanced AS (
        SELECT DISTINCT company_id FROM raw_balances
    )
    SELECT
        c.company_id,
        c.group_id,
        c.country AS country_raw,
        {country} AS country,
        c.currency,
        c.erp AS erp_raw,
        {erp_code} AS erp_code,
        {_erp_label_expr("c.erp")} AS erp_label,
        {erp_code} AS erp,
        c.created_at,
        greatest(
            DATE {sql_str(WINDOW_START)},
            CAST(date_trunc('month', CAST(c.created_at AS TIMESTAMP)) AS DATE)
        ) AS observation_start,
        checking.company_id IS NOT NULL AS has_checking,
        invoiced.company_id IS NOT NULL AS has_invoices,
        invoiced.company_id IS NOT NULL AS erp_connected,
        balanced.company_id IS NULL AS balance_missing,
        ({country} = {sql_str(UNMAPPED)}) AS dq_country_unmapped,
        ({erp_code} = {sql_str(UNMAPPED)}) AS dq_erp_unmapped
    FROM raw_companies c
    LEFT JOIN checking USING (company_id)
    LEFT JOIN invoiced USING (company_id)
    LEFT JOIN balanced USING (company_id)
    """


def banking_products_mapped_sql() -> str:
    bank = case_from_map(_trimmed("bank_name"), BANK_NAME, passthrough=True)
    service = _service_clean_expr("service")
    return f"""
    CREATE OR REPLACE VIEW banking_products_mapped AS
    WITH base AS (
        SELECT
            product_id,
            company_id,
            label,
            type,
            {_type_family_expr("type")} AS type_family,
            bank_name AS bank_name_raw,
            {bank} AS bank_name,
            service AS service_raw,
            {service} AS service,
            currency,
            created_at,
            CAST(created_at AS TIMESTAMP) > TIMESTAMP {sql_str(WINDOW_END)}
                AS connected_after_cutoff,
            greatest(
                DATE {sql_str(WINDOW_START)},
                CAST(date_trunc('month', CAST(created_at AS TIMESTAMP)) AS DATE)
            ) AS observation_start
        FROM raw_banking_products
    )
    SELECT
        base.*,
        {_service_kind_expr("service_raw", "service")} AS service_kind
    FROM base
    """


def debt_products_mapped_sql() -> str:
    bank = case_from_map(_trimmed("bank_name"), BANK_NAME, passthrough=True)
    service = _service_clean_expr("service")
    kind = (
        "CASE "
        f"WHEN ({service}) IS NULL THEN NULL "
        f"WHEN ({service}) = 'custom' THEN 'custom' "
        "WHEN CAST(service AS VARCHAR) LIKE 'ins_%' THEN 'connector_id' "
        f"WHEN ({service}) LIKE 'ins_%' THEN 'connector_id' "
        "ELSE 'bank_service' "
        "END"
    )
    return f"""
    CREATE OR REPLACE VIEW debt_products_mapped AS
    SELECT
        product_id,
        company_id,
        label,
        type,
        {_type_family_expr("type")} AS type_family,
        bank_name AS bank_name_raw,
        {bank} AS bank_name,
        service AS service_raw,
        {service} AS service,
        {kind} AS service_kind,
        currency,
        created_at,
        granted,
        outstanding,
        granted AS granted_raw,
        outstanding AS outstanding_raw,
        abs(granted) AS granted_liability,
        abs(outstanding) AS outstanding_liability,
        liquidity,
        CAST(created_at AS TIMESTAMP) > TIMESTAMP {sql_str(WINDOW_END)} AS connected_after_cutoff,
        greatest(
            DATE {sql_str(WINDOW_START)},
            CAST(date_trunc('month', CAST(created_at AS TIMESTAMP)) AS DATE)
        ) AS observation_start,
        (outstanding > 0) AS dq_positive_outstanding,
        (
            granted IS NOT NULL AND outstanding IS NOT NULL
            AND granted <> 0 AND outstanding <> 0
            AND sign(granted) <> sign(outstanding)
        ) AS dq_granted_outstanding_sign_mismatch,
        (
            granted IS NOT NULL AND outstanding IS NOT NULL
            AND abs(outstanding) > abs(granted)
        ) AS dq_outstanding_exceeds_granted
    FROM raw_debt_products
    """


def debt_schedule_config_mapped_sql() -> str:
    amort = case_from_map(
        _trimmed("amortization_type"), AMORTIZATION_TYPE, passthrough=True
    )
    freq = case_from_map(
        _trimmed("amortising_frequency"), AMORTISING_FREQUENCY, passthrough=True
    )
    return f"""
    CREATE OR REPLACE VIEW debt_schedule_config_mapped AS
    WITH catalog AS (
        SELECT product_id FROM raw_banking_products
        UNION
        SELECT product_id FROM raw_debt_products
    )
    SELECT
        s.product_id,
        s.company_id,
        s.settlement_product_id AS settlement_product_id_raw,
        CASE
            WHEN s.settlement_product_id IS NULL THEN NULL
            WHEN catalog.product_id IS NULL THEN NULL
            ELSE s.settlement_product_id
        END AS settlement_product_id,
        (s.settlement_product_id IS NOT NULL AND catalog.product_id IS NULL)
            AS dq_settlement_orphan,
        s.currency,
        s.amortization_type AS amortization_type_raw,
        {amort} AS amortization_type,
        s.interest_calc_method,
        s.amortising_frequency AS amortising_frequency_raw,
        {freq} AS amortising_frequency,
        s.granted_balance,
        s.outstanding_balance,
        s.total_periods,
        s.next_payment_date,
        s.last_payment_date,
        s.annual_interest_rate_or_spread,
        s.interest_type,
        (
            d.product_id IS NOT NULL
            AND (
                (
                    s.granted_balance IS NOT NULL AND d.granted IS NOT NULL
                    AND abs(abs(s.granted_balance) - abs(d.granted)) > 0.015
                )
                OR (
                    s.outstanding_balance IS NOT NULL AND d.outstanding IS NOT NULL
                    AND abs(abs(s.outstanding_balance) - abs(d.outstanding)) > 0.015
                )
            )
        ) AS dq_schedule_amount_mismatch
    FROM raw_debt_schedule_config s
    LEFT JOIN raw_debt_products d USING (product_id)
    LEFT JOIN catalog ON catalog.product_id = s.settlement_product_id
    """


def balances_mapped_sql() -> str:
    return f"""
    CREATE OR REPLACE VIEW balances_mapped AS
    SELECT
        product_id,
        company_id,
        date,
        balance,
        available,
        granted,
        liquidity,
        countable,
        CASE
            WHEN balance IS NOT NULL AND abs(balance) > {BALANCE_SUSPECT_ABS}
            THEN 'suspect'
            ELSE 'ok'
        END AS balance_quality,
        (balance IS NOT NULL AND abs(balance) > {BALANCE_SUSPECT_ABS}) AS dq_balance_suspect
    FROM raw_balances
    """


def invoices_mapped_sql() -> str:
    status = case_from_map(
        _trimmed("status"), INVOICE_STATUS, passthrough=True
    )
    return f"""
    CREATE OR REPLACE VIEW invoices_mapped AS
    WITH base AS (
        SELECT
            operation_id,
            company_id,
            document_type,
            issuance_date,
            due_date,
            payment_date AS payment_date_raw,
            amount,
            pending_amount,
            currency,
            accounting_currency,
            CASE
                WHEN exchange_rate IS NULL THEN NULL
                WHEN exchange_rate <= 0 THEN NULL
                ELSE exchange_rate
            END AS exchange_rate,
            exchange_rate AS exchange_rate_raw,
            status AS status_raw,
            {status} AS status,
            concept,
            counterparty_id AS counterparty_id_raw,
            {_counterparty_expr("counterparty_id")} AS counterparty_id,
            (
                lower(trim(CAST(status AS VARCHAR))) = 'overdue'
                AND payment_date IS NOT NULL
                AND due_date IS NOT NULL
                AND CAST(payment_date AS DATE) = CAST(due_date AS DATE)
            ) AS payment_date_was_due_alias,
            (due_date IS NOT NULL AND issuance_date IS NOT NULL
                AND CAST(due_date AS DATE) < CAST(issuance_date AS DATE)
            ) AS dq_due_before_issuance,
            (
                payment_date IS NOT NULL AND issuance_date IS NOT NULL
                AND CAST(payment_date AS DATE) < CAST(issuance_date AS DATE)
            ) AS dq_paid_before_issuance,
            (
                pending_amount IS NOT NULL AND amount IS NOT NULL
                AND abs(pending_amount) > abs(amount)
            ) AS dq_pending_exceeds_amount,
            (
                pending_amount IS NOT NULL AND amount IS NOT NULL
                AND pending_amount <> 0 AND amount <> 0
                AND sign(pending_amount) <> sign(amount)
            ) AS dq_pending_sign_mismatch
        FROM raw_invoices
    )
    SELECT
        operation_id,
        company_id,
        document_type,
        issuance_date,
        due_date,
        CASE WHEN payment_date_was_due_alias THEN NULL ELSE payment_date_raw END
            AS payment_date,
        payment_date_raw,
        payment_date_was_due_alias,
        amount,
        pending_amount,
        currency,
        accounting_currency,
        exchange_rate,
        exchange_rate_raw,
        status,
        status_raw,
        concept,
        counterparty_id,
        counterparty_id_raw,
        dq_due_before_issuance,
        dq_paid_before_issuance,
        dq_pending_exceeds_amount,
        dq_pending_sign_mismatch
    FROM base
    """


def transactions_mapped_sql() -> str:
    category = case_from_map(
        _trimmed("category"),
        TXN_CATEGORY,
        null_to="uncategorized",
        passthrough=True,
    )
    return f"""
    CREATE OR REPLACE VIEW transactions_mapped AS
    SELECT
        transaction_id,
        company_id,
        product_id,
        date,
        value_date AS value_date_raw,
        CASE
            WHEN value_date IS NULL THEN date
            WHEN year(CAST(value_date AS TIMESTAMP)) >= {VALUE_DATE_SENTINEL_YEAR}
                THEN date
            WHEN abs(date_diff(
                'day',
                CAST(date AS DATE),
                CAST(value_date AS DATE)
            )) > {VALUE_DATE_MAX_GAP_DAYS}
                THEN date
            ELSE value_date
        END AS value_date_clean,
        amount,
        exchange_rate AS exchange_rate_raw,
        CASE
            WHEN exchange_rate IS NULL THEN NULL
            WHEN exchange_rate <= 0 THEN NULL
            ELSE exchange_rate
        END AS exchange_rate,
        status,
        accounting_status,
        category AS category_raw,
        {category} AS category,
        description,
        counterparty_id AS counterparty_id_raw,
        {_counterparty_expr("counterparty_id")} AS counterparty_id
    FROM raw_transactions
    """


def products_mapped_sql() -> str:
    return """
    CREATE OR REPLACE VIEW products_mapped AS
    WITH catalog AS (
        SELECT
            product_id,
            company_id,
            'banking' AS product_class,
            type,
            currency,
            created_at
        FROM raw_banking_products
        UNION ALL
        SELECT
            product_id,
            company_id,
            'debt' AS product_class,
            type,
            currency,
            created_at
        FROM raw_debt_products
    ),
    ids AS (
        SELECT product_id FROM catalog
        UNION
        SELECT product_id FROM raw_balances
        UNION
        SELECT product_id FROM raw_transactions
        UNION
        SELECT settlement_product_id AS product_id
        FROM raw_debt_schedule_config
        WHERE settlement_product_id IS NOT NULL
    ),
    from_bal AS (
        SELECT product_id, any_value(company_id) AS company_id
        FROM raw_balances
        GROUP BY 1
    ),
    from_txn AS (
        SELECT product_id, any_value(company_id) AS company_id
        FROM raw_transactions
        GROUP BY 1
    ),
    from_sched AS (
        SELECT settlement_product_id AS product_id, any_value(company_id) AS company_id
        FROM raw_debt_schedule_config
        WHERE settlement_product_id IS NOT NULL
        GROUP BY 1
    )
    SELECT
        ids.product_id,
        coalesce(
            catalog.company_id,
            from_txn.company_id,
            from_bal.company_id,
            from_sched.company_id
        ) AS company_id,
        catalog.product_class,
        catalog.type,
        catalog.currency,
        catalog.created_at,
        CASE
            WHEN catalog.product_id IS NOT NULL THEN 'in_catalog'
            WHEN from_txn.product_id IS NOT NULL THEN 'txn_only'
            WHEN from_bal.product_id IS NOT NULL THEN 'balance_only'
            ELSE 'settlement_only'
        END AS catalog_status
    FROM ids
    LEFT JOIN catalog USING (product_id)
    LEFT JOIN from_bal USING (product_id)
    LEFT JOIN from_txn USING (product_id)
    LEFT JOIN from_sched USING (product_id)
    """


def public_alias_sql(name: str) -> str:
    return f"CREATE OR REPLACE VIEW {name} AS SELECT * FROM {name}_mapped"


def mapped_view_statements() -> list[str]:
    return [
        groups_mapped_sql(),
        banking_products_mapped_sql(),
        debt_products_mapped_sql(),
        debt_schedule_config_mapped_sql(),
        balances_mapped_sql(),
        invoices_mapped_sql(),
        transactions_mapped_sql(),
        companies_mapped_sql(),
        products_mapped_sql(),
        public_alias_sql("groups"),
        public_alias_sql("companies"),
        public_alias_sql("banking_products"),
        public_alias_sql("debt_products"),
        public_alias_sql("debt_schedule_config"),
        public_alias_sql("balances"),
        public_alias_sql("invoices"),
        public_alias_sql("transactions"),
        "CREATE OR REPLACE VIEW products AS SELECT * FROM products_mapped",
    ]
