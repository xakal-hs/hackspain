#!/usr/bin/env python3
"""Generate a self-contained exploratory report for the HackSpain X-Ray dataset."""

from __future__ import annotations

import html
import json
from pathlib import Path

from types import SimpleNamespace

import duckdb
import plotly.graph_objects as go
from plotly.io import to_html
from plotly.offline.offline import get_plotlyjs
from plotly.subplots import make_subplots

from cash_history import build_cash_sections, setup_cash_panel


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "analysis" / "report.html"
AS_OF = "2026-09-01"
COLORS = {
    "navy": "#102a43",
    "blue": "#1463ff",
    "cyan": "#27b3c2",
    "green": "#22a06b",
    "amber": "#f59e0b",
    "red": "#e5484d",
    "slate": "#64748b",
    "light": "#e8eef6",
}

DATASET_PURPOSES = {
    "groups": "Jerarquía empresarial y tamaño del grupo",
    "companies": "Maestro de empresas, moneda y contexto operativo",
    "banking_products": "Cuentas y productos bancarios conectados",
    "debt_products": "Financiación concedida, dispuesta y disponible",
    "debt_schedule_config": "Condiciones y calendario contractual de deuda",
    "balances": "Foto de saldos por producto al cierre",
    "invoices": "Ciclo documental ERP: emisión, vencimiento y pago",
    "transactions": "Flujos bancarios históricos con signo y categoría",
}

FIELD_MEANINGS = {
    "group_id": "Grupo empresarial al que pertenece la sociedad",
    "company_id": "Empresa; clave principal para cruzar tablas",
    "product_id": "Cuenta o producto financiero",
    "settlement_product_id": "Cuenta bancaria usada para liquidar la deuda",
    "counterparty_id": "Contraparte estable compartida entre movimientos y facturas",
    "transaction_id": "Identificador único del movimiento",
    "operation_id": "Identificador único del documento ERP",
    "n_companies_in_sample": "Sociedades del grupo presentes en la muestra",
    "country": "País declarado; incompleto y no normalizado",
    "currency": "Moneda del registro o entidad",
    "accounting_currency": "Moneda contable de la factura",
    "erp": "Sistema ERP conectado",
    "created_at": "Fecha de alta o conexión en plataforma",
    "label": "Etiqueta legible asignada al producto",
    "type": "Tipo de producto o documento según la tabla",
    "bank_name": "Entidad bancaria o producto definido por el cliente",
    "service": "Código del servicio de conexión; custom si es manual",
    "granted": "Importe original concedido",
    "outstanding": "Principal pendiente actual",
    "liquidity": "Importe disponible reportado",
    "amortization_type": "Sistema de amortización contractual",
    "interest_calc_method": "Convención usada para calcular intereses",
    "amortising_frequency": "Frecuencia de amortización",
    "granted_balance": "Principal concedido según el calendario",
    "outstanding_balance": "Principal pendiente según el calendario",
    "total_periods": "Número total de cuotas",
    "next_payment_date": "Próximo vencimiento contractual",
    "last_payment_date": "Último vencimiento contractual",
    "annual_interest_rate_or_spread": "Tipo anual o diferencial vigente",
    "interest_type": "Tipo fijo o variable",
    "date": "Fecha contable del movimiento o de la foto de saldo",
    "value_date": "Fecha valor bancaria",
    "issuance_date": "Fecha de emisión del documento",
    "due_date": "Fecha de vencimiento",
    "payment_date": "Fecha efectiva de cobro o pago",
    "amount": "Importe: positivo entrada y negativo salida en transacciones",
    "pending_amount": "Importe aún pendiente según el ERP",
    "exchange_rate": "Tipo de cambio aplicado; dirección no documentada",
    "status": "Estado operativo del registro",
    "accounting_status": "Estado de conciliación contable",
    "category": "Categoría automática del movimiento",
    "description": "Narrativa bancaria anonimizada",
    "document_type": "Clase de documento ERP",
    "concept": "Concepto de factura anonimizado",
    "balance": "Saldo contable al cierre",
    "available": "Saldo disponible informado por el proveedor",
    "countable": "Componente contable del saldo reportado",
}


def variable_role(name: str, sql_type: str) -> str:
    if name.endswith("_id"):
        return "Identificador"
    if "DATE" in sql_type or "TIMESTAMP" in sql_type:
        return "Temporal"
    if name in {
        "amount",
        "pending_amount",
        "balance",
        "available",
        "granted",
        "outstanding",
        "liquidity",
        "countable",
        "granted_balance",
        "outstanding_balance",
    }:
        return "Monetaria"
    if name == "exchange_rate":
        return "Factor"
    if sql_type in {"DOUBLE", "FLOAT", "DECIMAL", "BIGINT", "INTEGER"}:
        return "Numérica"
    if name in {"description", "concept", "label"}:
        return "Texto"
    return "Categórica"


def records(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def scalar(connection: duckdb.DuckDBPyConnection, sql: str):
    return connection.execute(sql).fetchone()[0]


def fmt(value, decimals: int = 1) -> str:
    if value is None:
        return "—"
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def compact(value) -> str:
    if value is None:
        return "—"
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}K"
    return fmt(value)


def chart_html(figure: go.Figure, height: int = 380) -> str:
    figure.update_layout(
        height=height,
        margin=dict(l=48, r=22, t=48, b=48),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=COLORS["navy"], size=12),
        hoverlabel=dict(bgcolor="#102a43", font_color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    figure.update_xaxes(gridcolor="#e8eef6", zeroline=False)
    figure.update_yaxes(gridcolor="#e8eef6", zeroline=False)
    return to_html(
        figure,
        include_plotlyjs=False,
        full_html=False,
        config={"displayModeBar": False, "responsive": True},
    )


def horizontal_bar(rows: list[dict], label: str, value: str, title: str, color: str) -> go.Figure:
    rows = list(reversed(rows))
    figure = go.Figure(
        go.Bar(
            x=[row[value] for row in rows],
            y=[row[label] or "Sin informar" for row in rows],
            orientation="h",
            marker_color=color,
            text=[compact(row[value]) for row in rows],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(title=title)
    return figure


def table(headers: list[str], rows: list[list], classes: str = "") -> str:
    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>" for row in rows
    )
    return f'<div class="table-wrap {classes}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def setup(connection: duckdb.DuckDBPyConnection) -> None:
    for name in (
        "groups",
        "companies",
        "banking_products",
        "debt_products",
        "debt_schedule_config",
        "balances",
        "invoices",
        "transactions",
    ):
        path = (DATA / f"{name}.csv").as_posix().replace("'", "''")
        connection.execute(
            f"CREATE VIEW {name} AS SELECT * FROM read_csv_auto('{path}', sample_size=-1)"
        )

    connection.execute(
        """
        CREATE TEMP TABLE company_features AS
        WITH tx_month AS (
            SELECT company_id, date_trunc('month', date) AS month_start,
                   sum(CASE WHEN amount > 0 THEN amount ELSE 0 END) inflow,
                   -sum(CASE WHEN amount < 0 THEN amount ELSE 0 END) outflow,
                   sum(amount) net_flow,
                   count(*) tx_count
            FROM transactions WHERE status = 'booked' GROUP BY 1, 2
        ), tx AS (
            SELECT company_id, sum(inflow) inflow, sum(outflow) outflow,
                   sum(net_flow) net_flow, avg(tx_count) avg_monthly_tx,
                   stddev_pop(net_flow) net_flow_volatility,
                   count(*) active_months
            FROM tx_month GROUP BY 1
        ), inv AS (
            SELECT company_id, count(*) invoice_count,
                   sum(abs(amount)) invoice_volume,
                   sum(CASE WHEN status = 'overdue' THEN greatest(pending_amount, 0) ELSE 0 END) overdue_pending,
                   sum(greatest(pending_amount, 0)) invoice_pending,
                   median(CASE WHEN payment_date IS NOT NULL AND issuance_date IS NOT NULL
                               THEN date_diff('day', issuance_date, payment_date) END) median_days_to_pay
            FROM invoices GROUP BY 1
        ), debt AS (
            SELECT company_id, sum(greatest(outstanding, 0)) debt_outstanding,
                   sum(greatest(granted, 0)) debt_granted,
                   count(*) debt_products
            FROM debt_products GROUP BY 1
        ), bal AS (
            SELECT company_id, sum(coalesce(balance, 0)) current_balance,
                   count(*) balance_products,
                   sum(CASE WHEN balance < 0 THEN 1 ELSE 0 END) negative_balance_products
            FROM balances GROUP BY 1
        )
        SELECT c.company_id, c.group_id, c.currency,
               coalesce(tx.inflow, 0) inflow, coalesce(tx.outflow, 0) outflow,
               coalesce(tx.net_flow, 0) net_flow, tx.avg_monthly_tx,
               tx.net_flow_volatility, coalesce(tx.active_months, 0) active_months,
               coalesce(inv.invoice_count, 0) invoice_count,
               coalesce(inv.invoice_volume, 0) invoice_volume,
               coalesce(inv.overdue_pending, 0) overdue_pending,
               coalesce(inv.invoice_pending, 0) invoice_pending,
               inv.median_days_to_pay,
               coalesce(debt.debt_outstanding, 0) debt_outstanding,
               coalesce(debt.debt_granted, 0) debt_granted,
               coalesce(debt.debt_products, 0) debt_products,
               coalesce(bal.current_balance, 0) current_balance,
               coalesce(bal.balance_products, 0) balance_products,
               coalesce(bal.negative_balance_products, 0) negative_balance_products,
               CASE WHEN debt.debt_granted > 0 THEN debt.debt_outstanding / debt.debt_granted END debt_utilization,
               CASE WHEN inv.invoice_volume > 0 THEN inv.overdue_pending / inv.invoice_volume END overdue_ratio,
               CASE WHEN tx.outflow > 0 THEN tx.inflow / tx.outflow END inflow_outflow_ratio
        FROM companies c
        LEFT JOIN tx USING (company_id)
        LEFT JOIN inv USING (company_id)
        LEFT JOIN debt USING (company_id)
        LEFT JOIN bal USING (company_id)
        """
    )

    setup_cash_panel(connection)


def build_report(connection: duckdb.DuckDBPyConnection) -> str:
    counts = {
        name: scalar(connection, f"SELECT count(*) FROM {name}")
        for name in (
            "groups",
            "companies",
            "banking_products",
            "debt_products",
            "debt_schedule_config",
            "balances",
            "invoices",
            "transactions",
        )
    }
    variable_rows = []
    for dataset, purpose in DATASET_PURPOSES.items():
        for column in records(connection, f"DESCRIBE {dataset}"):
            name = column["column_name"]
            variable_rows.append(
                [
                    f"<b>{dataset}.csv</b><small>{html.escape(purpose)}</small>",
                    f"<code>{html.escape(name)}</code>",
                    variable_role(name, column["column_type"]),
                    html.escape(FIELD_MEANINGS.get(name, "Campo descriptivo del registro")),
                ]
            )
    tx_dates = connection.execute("SELECT min(date), max(date) FROM transactions").fetchone()
    invoice_dates = connection.execute(
        "SELECT min(issuance_date), max(issuance_date) FROM invoices"
    ).fetchone()

    coverage = records(
        connection,
        """
        SELECT 'Con transacciones' metric, count(*) FILTER (WHERE active_months > 0) n FROM company_features
        UNION ALL SELECT 'Con facturas', count(*) FILTER (WHERE invoice_count > 0) FROM company_features
        UNION ALL SELECT 'Con deuda', count(*) FILTER (WHERE debt_products > 0) FROM company_features
        UNION ALL SELECT 'Con saldo final', count(*) FILTER (WHERE balance_products > 0) FROM company_features
        """
    )
    country = records(
        connection,
        """
        SELECT coalesce(country_norm(country), 'Sin informar') AS "label", count(*) AS n
        FROM companies GROUP BY 1 ORDER BY n DESC LIMIT 10
        """
    )
    currency = records(
        connection,
        'SELECT coalesce(currency, \'Sin informar\') AS "label", count(*) AS n FROM companies GROUP BY 1 ORDER BY n DESC LIMIT 10',
    )
    erp = records(
        connection,
        'SELECT coalesce(erp, \'Sin ERP\') AS "label", count(*) AS n FROM companies GROUP BY 1 ORDER BY n DESC LIMIT 10',
    )
    group_sizes = records(
        connection,
        "SELECT n_companies_in_sample AS size, count(*) AS group_count FROM groups GROUP BY 1 ORDER BY 1",
    )

    bank_types = records(
        connection,
        'SELECT type AS "label", count(*) AS n FROM banking_products GROUP BY 1 ORDER BY n DESC',
    )
    debt_types = records(
        connection,
        """
        SELECT type AS "label", count(*) AS n, sum(outstanding) AS outstanding_total,
               sum(granted) AS granted_total,
               median(CASE WHEN granted > 0 THEN outstanding / granted END) AS utilization
        FROM debt_products GROUP BY 1 ORDER BY n DESC
        """,
    )
    top_banks = records(
        connection,
        """
        SELECT bank_name AS "label", count(*) AS n FROM (
          SELECT bank_name FROM banking_products UNION ALL SELECT bank_name FROM debt_products
        ) GROUP BY 1 ORDER BY n DESC LIMIT 12
        """,
    )

    monthly_tx = records(
        connection,
        """
        SELECT strftime(date_trunc('month', date), '%Y-%m') AS month_label,
               count(*) transactions,
               sum(CASE WHEN amount > 0 THEN amount ELSE 0 END) inflow,
               -sum(CASE WHEN amount < 0 THEN amount ELSE 0 END) outflow,
               sum(amount) net_flow,
               count(DISTINCT company_id) active_companies
        FROM transactions WHERE status = 'booked' GROUP BY 1 ORDER BY 1
        """,
    )
    tx_categories = records(
        connection,
        """
        SELECT coalesce(nullif(category, ''), 'Sin categoría') AS "label", count(*) AS n,
               sum(abs(amount)) volume, sum(amount) net
        FROM transactions GROUP BY 1 ORDER BY n DESC LIMIT 15
        """,
    )
    tx_status = records(
        connection,
        'SELECT coalesce(status, \'Sin informar\') AS "label", count(*) AS n FROM transactions GROUP BY 1 ORDER BY n DESC',
    )
    reconciled = scalar(
        connection,
        """
        SELECT avg(CASE WHEN accounting_status = 'RECONCILIATION_COMPLETED' THEN 1 ELSE 0 END)
        FROM transactions
        """,
    )

    invoice_status = records(
        connection,
        """
        SELECT status AS "label", count(*) AS n, sum(greatest(pending_amount, 0)) pending
        FROM invoices GROUP BY 1 ORDER BY n DESC
        """,
    )
    monthly_invoices = records(
        connection,
        """
        SELECT strftime(date_trunc('month', issuance_date), '%Y-%m') AS month_label,
               count(*) n, sum(abs(amount)) volume,
               sum(greatest(pending_amount, 0)) pending
        FROM invoices GROUP BY 1 ORDER BY 1
        """,
    )
    payment_delay = records(
        connection,
        """
        SELECT CASE
          WHEN date_diff('day', due_date, payment_date) <= 0 THEN 'En plazo'
          WHEN date_diff('day', due_date, payment_date) <= 15 THEN '1–15 días'
          WHEN date_diff('day', due_date, payment_date) <= 30 THEN '16–30 días'
          WHEN date_diff('day', due_date, payment_date) <= 60 THEN '31–60 días'
          WHEN date_diff('day', due_date, payment_date) <= 90 THEN '61–90 días'
          ELSE '>90 días' END AS "label", count(*) AS n
        FROM invoices
        WHERE status = 'paid' AND payment_date IS NOT NULL AND due_date IS NOT NULL
        GROUP BY 1 ORDER BY CASE "label" WHEN 'En plazo' THEN 1 WHEN '1–15 días' THEN 2
          WHEN '16–30 días' THEN 3 WHEN '31–60 días' THEN 4 WHEN '61–90 días' THEN 5 ELSE 6 END
        """,
    )

    balance_summary = records(
        connection,
        """
        WITH products AS (
          SELECT product_id, type FROM banking_products
          UNION ALL SELECT product_id, type FROM debt_products
        )
        SELECT coalesce(p.type, 'Sin producto') AS "label", count(*) AS n,
               sum(b.balance) balance, count(*) FILTER (WHERE b.balance < 0) negative_n
        FROM balances b LEFT JOIN products p USING(product_id)
        GROUP BY 1 ORDER BY n DESC
        """,
    )

    feature_names = [
        "inflow",
        "outflow",
        "net_flow",
        "net_flow_volatility",
        "invoice_pending",
        "overdue_pending",
        "debt_outstanding",
        "debt_utilization",
        "current_balance",
        "inflow_outflow_ratio",
    ]
    corr_rows = records(
        connection,
        f"""
        SELECT {", ".join(feature_names)}
        FROM company_features WHERE currency = 'EUR'
        """
    )
    correlations: list[list[float | None]] = []
    for left in feature_names:
        row = []
        for right in feature_names:
            value = scalar(
                connection,
                f"""
                SELECT corr({left}, {right}) FROM company_features
                WHERE currency = 'EUR' AND {left} IS NOT NULL AND {right} IS NOT NULL
                """,
            )
            row.append(value)
        correlations.append(row)

    outlier_metrics = {
        "current_balance": "Saldo final",
        "net_flow": "Flujo neto 24m",
        "net_flow_volatility": "Volatilidad mensual",
        "overdue_pending": "Pendiente vencido",
        "debt_outstanding": "Deuda pendiente",
        "inflow_outflow_ratio": "Ratio cobros/pagos",
    }
    outlier_rows = []
    for column, label in outlier_metrics.items():
        stats = connection.execute(
            f"""
            SELECT quantile_cont({column}, 0.25), quantile_cont({column}, 0.5),
                   quantile_cont({column}, 0.75)
            FROM company_features WHERE currency = 'EUR' AND {column} IS NOT NULL
            """
        ).fetchone()
        q1, median, q3 = stats
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        count = scalar(
            connection,
            f"""
            SELECT count(*) FROM company_features
            WHERE currency = 'EUR' AND {column} IS NOT NULL
              AND ({column} < {low} OR {column} > {high})
            """,
        )
        total = scalar(
            connection,
            f"SELECT count(*) FROM company_features WHERE currency = 'EUR' AND {column} IS NOT NULL",
        )
        outlier_rows.append(
            {
                "metric": label,
                "median": median,
                "low": low,
                "high": high,
                "count": count,
                "share": count / total if total else 0,
            }
        )
    top_outliers = records(
        connection,
        """
        WITH ranked AS (
          SELECT company_id, current_balance, net_flow, overdue_pending, debt_outstanding,
                 greatest(
                   abs((current_balance - median(current_balance) OVER ()) /
                     nullif(mad(current_balance) OVER (), 0)),
                   abs((net_flow - median(net_flow) OVER ()) /
                     nullif(mad(net_flow) OVER (), 0)),
                   abs((overdue_pending - median(overdue_pending) OVER ()) /
                     nullif(mad(overdue_pending) OVER (), 0)),
                   abs((debt_outstanding - median(debt_outstanding) OVER ()) /
                     nullif(mad(debt_outstanding) OVER (), 0))
                 ) robust_score
          FROM company_features WHERE currency = 'EUR'
        )
        SELECT * FROM ranked ORDER BY robust_score DESC NULLS LAST LIMIT 12
        """,
    )

    quality = records(
        connection,
        f"""
        SELECT * FROM (VALUES
          ('Empresas sin país', (SELECT count(*) FROM companies WHERE country IS NULL OR trim(country) = ''), {counts['companies']}),
          ('Empresas sin ERP', (SELECT count(*) FROM companies WHERE erp IS NULL OR trim(erp) = ''), {counts['companies']}),
          ('Transacciones sin categoría', (SELECT count(*) FROM transactions WHERE category IS NULL OR category = '-'), {counts['transactions']}),
          ('Transacciones sin contraparte', (SELECT count(*) FROM transactions WHERE counterparty_id IS NULL), {counts['transactions']}),
          ('Facturas sin fecha de pago', (SELECT count(*) FROM invoices WHERE payment_date IS NULL), {counts['invoices']}),
          ('Facturas sin contraparte', (SELECT count(*) FROM invoices WHERE counterparty_id IS NULL), {counts['invoices']}),
          ('Saldos sin available', (SELECT count(*) FROM balances WHERE available IS NULL OR available = ''), {counts['balances']}),
          ('País escrito en texto libre', (SELECT count(*) FROM companies WHERE country_norm(country) IS NOT NULL AND country_norm(country) <> trim(country)), {counts['companies']})
        ) AS t(issue, affected, total)
        """,
    )
    integrity = records(
        connection,
        """
        SELECT * FROM (VALUES
          ('Transacciones → empresa inexistente',
            (SELECT count(*) FROM transactions t LEFT JOIN companies c USING(company_id) WHERE c.company_id IS NULL)),
          ('Facturas → empresa inexistente',
            (SELECT count(*) FROM invoices i LEFT JOIN companies c USING(company_id) WHERE c.company_id IS NULL)),
          ('Deuda → empresa inexistente',
            (SELECT count(*) FROM debt_products d LEFT JOIN companies c USING(company_id) WHERE c.company_id IS NULL)),
          ('Saldos → empresa inexistente',
            (SELECT count(*) FROM balances b LEFT JOIN companies c USING(company_id) WHERE c.company_id IS NULL)),
          ('IDs de transacción duplicados',
            (SELECT count(*) - count(DISTINCT transaction_id) FROM transactions)),
          ('IDs de factura duplicados',
            (SELECT count(*) - count(DISTINCT operation_id) FROM invoices))
        ) AS t(check_name, failures)
        """,
    )

    # Figures
    coverage_fig = horizontal_bar(coverage, "metric", "n", "Cobertura por empresa", COLORS["blue"])
    coverage_fig.update_xaxes(range=[0, counts["companies"] * 1.12])

    profile_fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("País declarado", "Moneda de empresa", "ERP"),
        horizontal_spacing=0.15,
    )
    for index, (rows, color) in enumerate(
        ((country[:7], COLORS["blue"]), (currency[:7], COLORS["cyan"]), (erp[:7], COLORS["green"])),
        start=1,
    ):
        figure_rows = list(reversed(rows))
        profile_fig.add_trace(
            go.Bar(
                x=[row["n"] for row in figure_rows],
                y=[row["label"] for row in figure_rows],
                orientation="h",
                marker_color=color,
                hovertemplate="%{y}: %{x}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=index,
        )

    products_fig = make_subplots(
        rows=1, cols=2, subplot_titles=("Productos bancarios", "Productos de deuda")
    )
    products_fig.add_trace(
        go.Bar(
            x=[row["label"] for row in bank_types],
            y=[row["n"] for row in bank_types],
            marker_color=COLORS["blue"],
            name="Bancarios",
        ),
        row=1,
        col=1,
    )
    products_fig.add_trace(
        go.Bar(
            x=[row["label"] for row in debt_types],
            y=[row["n"] for row in debt_types],
            marker_color=COLORS["amber"],
            name="Deuda",
        ),
        row=1,
        col=2,
    )

    tx_fig = go.Figure()
    tx_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in monthly_tx],
            y=[row["inflow"] for row in monthly_tx],
            name="Entradas",
            line=dict(color=COLORS["green"], width=3),
        )
    )
    tx_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in monthly_tx],
            y=[row["outflow"] for row in monthly_tx],
            name="Salidas (abs.)",
            line=dict(color=COLORS["red"], width=3),
        )
    )
    tx_fig.add_trace(
        go.Bar(
            x=[row["month_label"] for row in monthly_tx],
            y=[row["net_flow"] for row in monthly_tx],
            name="Flujo neto",
            marker_color=[
                COLORS["blue"] if row["net_flow"] >= 0 else COLORS["red"] for row in monthly_tx
            ],
            opacity=0.42,
        )
    )
    tx_fig.update_layout(
        title="Actividad mensual agregada · importes reportados, multimoneda",
        yaxis_tickformat="~s",
        barmode="relative",
    )

    category_fig = horizontal_bar(
        tx_categories[:12], "label", "n", "Categorías con más movimientos", COLORS["blue"]
    )

    invoice_fig = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "domain"}, {"type": "xy"}]],
        subplot_titles=("Estado de las facturas", "Puntualidad de facturas pagadas"),
    )
    invoice_fig.add_trace(
        go.Pie(
            labels=[row["label"] for row in invoice_status],
            values=[row["n"] for row in invoice_status],
            hole=0.62,
            marker_colors=[
                COLORS["green"],
                COLORS["red"],
                COLORS["amber"],
                COLORS["slate"],
                COLORS["cyan"],
                COLORS["blue"],
            ],
            textinfo="percent",
            hovertemplate="%{label}: %{value:,}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    invoice_fig.add_trace(
        go.Bar(
            x=[row["label"] for row in payment_delay],
            y=[row["n"] for row in payment_delay],
            marker_color=COLORS["cyan"],
            hovertemplate="%{x}: %{y:,}<extra></extra>",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    invoice_time_fig = go.Figure(
        go.Scatter(
            x=[row["month_label"] for row in monthly_invoices],
            y=[row["n"] for row in monthly_invoices],
            fill="tozeroy",
            line=dict(color=COLORS["blue"], width=3),
            fillcolor="rgba(20,99,255,.12)",
            name="Facturas emitidas",
            hovertemplate="%{x}: %{y:,}<extra></extra>",
        )
    )
    invoice_time_fig.update_layout(title="Documentos ERP por mes")

    balance_fig = horizontal_bar(
        balance_summary[:12], "label", "n", "Saldos finales por tipo de producto", COLORS["cyan"]
    )

    corr_labels = [
        "Entradas",
        "Salidas",
        "Flujo neto",
        "Volatilidad",
        "Pendiente facturas",
        "Vencido",
        "Deuda",
        "Uso deuda",
        "Saldo final",
        "Cobros/pagos",
    ]
    corr_fig = go.Figure(
        go.Heatmap(
            z=correlations,
            x=corr_labels,
            y=corr_labels,
            zmin=-1,
            zmax=1,
            colorscale=[
                [0, "#b4232c"],
                [0.5, "#f8fafc"],
                [1, "#1463ff"],
            ],
            text=[
                ["" if value is None else f"{value:.2f}" for value in row]
                for row in correlations
            ],
            texttemplate="%{text}",
            hovertemplate="%{x} × %{y}: %{z:.3f}<extra></extra>",
        )
    )
    corr_fig.update_layout(title="Correlación de señales a nivel empresa · cohorte EUR")

    outlier_fig = go.Figure(
        go.Bar(
            x=[row["share"] * 100 for row in outlier_rows],
            y=[row["metric"] for row in outlier_rows],
            orientation="h",
            marker_color=COLORS["red"],
            text=[f'{row["share"]:.1%}' for row in outlier_rows],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        )
    )
    outlier_fig.update_layout(title="Empresas fuera de la banda IQR", xaxis_title="% de empresas")

    group_fig = go.Figure(
        go.Bar(
            x=[row["size"] for row in group_sizes],
            y=[row["group_count"] for row in group_sizes],
            marker_color=COLORS["blue"],
            hovertemplate="%{x} empresas: %{y} grupos<extra></extra>",
        )
    )
    group_fig.update_layout(title="Tamaño de los grupos empresariales")

    # Derived observations
    overdue_count = next(row["n"] for row in invoice_status if row["label"] == "overdue")
    paid_count = next(row["n"] for row in invoice_status if row["label"] == "paid")
    missing_country = scalar(
        connection, "SELECT count(*) FROM companies WHERE country IS NULL OR trim(country) = ''"
    )
    negative_balances = scalar(connection, "SELECT count(*) FROM balances WHERE balance < 0")
    debt_totals = connection.execute(
        "SELECT sum(outstanding), sum(granted), median(CASE WHEN granted > 0 THEN outstanding/granted END) FROM debt_products"
    ).fetchone()
    # September 2026 contains only the extraction day; compare the last two complete months.
    latest_month = monthly_tx[-2]
    previous_month = monthly_tx[-3]
    tx_change = (
        (latest_month["transactions"] / previous_month["transactions"] - 1)
        if previous_month["transactions"]
        else 0
    )

    quality_rows = [
        [
            html.escape(row["issue"]),
            fmt(row["affected"], 0),
            f'{row["affected"] / row["total"]:.1%}',
        ]
        for row in quality
    ]
    integrity_rows = [
        [
            html.escape(row["check_name"]),
            f'<span class="{"ok" if row["failures"] == 0 else "bad"}">{fmt(row["failures"], 0)}</span>',
        ]
        for row in integrity
    ]
    debt_rows = [
        [
            html.escape(row["label"]),
            fmt(row["n"], 0),
            compact(row["granted_total"]),
            compact(row["outstanding_total"]),
            "—" if row["utilization"] is None else f'{row["utilization"]:.1%}',
        ]
        for row in debt_types
    ]
    outlier_table = [
        [
            html.escape(row["metric"]),
            compact(row["median"]),
            f'{compact(row["low"])} → {compact(row["high"])}',
            fmt(row["count"], 0),
            f'{row["share"]:.1%}',
        ]
        for row in outlier_rows
    ]
    top_outlier_table = [
        [
            f"<code>{row['company_id']}</code>",
            compact(row["current_balance"]),
            compact(row["net_flow"]),
            compact(row["overdue_pending"]),
            compact(row["debt_outstanding"]),
            fmt(row["robust_score"], 1),
        ]
        for row in top_outliers
    ]

    date_range = f"{tx_dates[0]:%b %Y} — {tx_dates[1]:%b %Y}"

    cash_sections = build_cash_sections(
        connection,
        SimpleNamespace(
            records=records,
            scalar=scalar,
            fmt=fmt,
            compact=compact,
            table=table,
            chart_html=chart_html,
            colors=COLORS,
        ),
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HackSpain X-Ray · Exploración financiera</title>
  <style>{CSS}</style>
  <script>{get_plotlyjs()}</script>
</head>
<body>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">X</span><div><b>HackSpain</b><small>X-Ray · EDA</small></div></div>
    <nav>
      <a href="#resumen">01 · Resumen</a><a href="#variables">02 · Variables</a>
      <a href="#universo">03 · Universo</a><a href="#tesoreria">04 · Tesorería</a>
      <a href="#caja-metodo">05 · Caja: método</a><a href="#caja-evolucion">06 · Caja: evolución</a>
      <a href="#caja-temporalidad">07 · Temporalidad</a><a href="#caja-grupos">08 · Grupos</a>
      <a href="#caja-problemas">09 · Problemas de caja</a>
      <a href="#facturas">10 · Facturas</a><a href="#deuda">11 · Deuda y saldos</a>
      <a href="#relaciones">12 · Relaciones</a><a href="#outliers">13 · Outliers</a>
      <a href="#calidad">14 · Calidad</a><a href="#conclusiones">15 · Conclusiones</a>
    </nav>
    <div class="side-note">Artefacto autónomo<br>Generado sobre los 8 CSV<br>Fecha de corte: {AS_OF}</div>
  </aside>
  <main>
    <section class="hero" id="resumen">
      <div class="eyebrow">EXPLORATORY DATA ANALYSIS · EMBAT X-RAY</div>
      <h1>La huella financiera<br><em>antes del score.</em></h1>
      <p>Lectura estructural, temporal y relacional de 24 meses de tesorería sintética. El objetivo no es puntuar todavía, sino entender qué señales pueden separar nivel, trayectoria, bache y deterioro.</p>
      <div class="hero-meta"><span>{date_range}</span><span>Datos sintéticos</span><span>Sin dependencias externas</span></div>
    </section>

    <section class="section">
      <div class="section-head"><span>01</span><div><h2>Resumen del dataset</h2><p>La unidad candidata del score es la empresa; el grupo debe conservarse para evitar fuga de información.</p></div></div>
      <div class="kpis">
        <div class="kpi"><small>Empresas</small><strong>{fmt(counts['companies'], 0)}</strong><span>en {fmt(counts['groups'], 0)} grupos</span></div>
        <div class="kpi"><small>Movimientos</small><strong>{compact(counts['transactions'])}</strong><span>{date_range}</span></div>
        <div class="kpi"><small>Documentos ERP</small><strong>{compact(counts['invoices'])}</strong><span>{overdue_count / counts['invoices']:.1%} vencidos</span></div>
        <div class="kpi"><small>Productos conectados</small><strong>{compact(counts['banking_products'] + counts['debt_products'])}</strong><span>bancarios + deuda</span></div>
      </div>
      <div class="callout insight"><b>Lectura clave.</b> Hay suficiente profundidad longitudinal para construir trayectorias mensuales, pero <code>balances.csv</code> solo aporta una foto final. El histórico de caja deberá reconstruirse hacia atrás con transacciones y validarse contra el saldo del {AS_OF}.</div>
      <div class="grid two"><div class="panel">{chart_html(coverage_fig)}</div><div class="panel model">
        <h3>Modelo relacional</h3>
        <div class="model-flow"><span>Grupo</span><i>1 → N</i><span>Empresa</span><i>1 → N</i><span>Producto</span></div>
        <div class="model-branches"><div>Transacciones<br><b>{compact(counts['transactions'])}</b></div><div>Facturas<br><b>{compact(counts['invoices'])}</b></div><div>Saldos finales<br><b>{compact(counts['balances'])}</b></div><div>Deuda<br><b>{compact(counts['debt_products'])}</b></div></div>
        <p class="caption">Las contrapartes conectan transacciones y facturas. Los IDs son claves, no variables numéricas ni magnitudes ordenables.</p>
      </div></div>
    </section>

    <section class="section" id="variables">
      <div class="section-head"><span>02</span><div><h2>Inventario y significado de variables</h2><p>Todos los campos disponibles, clasificados por función analítica. Los identificadores se excluyen de estadísticas, correlaciones y outliers.</p></div></div>
      <div class="panel variable-panel">
        {table(["Dataset", "Variable", "Rol", "Significado"], variable_rows, "variable-table")}
      </div>
      <div class="callout"><b>Regla semántica.</b> Los importes solo se agregan cuando comparten moneda y contexto; las fechas representan eventos distintos; <code>status</code>, <code>type</code> y <code>category</code> son categorías; y ningún campo terminado en <code>_id</code> expresa magnitud.</div>
    </section>

    <section class="section" id="universo">
      <div class="section-head"><span>03</span><div><h2>Universo empresarial</h2><p>Composición, cobertura y heterogeneidad operativa.</p></div></div>
      <div class="panel">{chart_html(profile_fig, 410)}</div>
      <div class="grid two">
        <div class="panel">{chart_html(group_fig)}</div>
        <div class="panel narrative"><h3>Qué significa para el modelado</h3>
          <ul><li><b>{missing_country / counts['companies']:.1%}</b> de las empresas no tiene país informado; no debe imputarse España de forma automática.</li>
          <li>EUR domina ({scalar(connection, "SELECT count(*) FROM companies WHERE currency='EUR'") / counts['companies']:.1%}), pero existen {scalar(connection, "SELECT count(DISTINCT currency) FROM companies")} monedas. Los agregados monetarios globales son descriptivos, no comparables sin normalización.</li>
          <li>Un grupo puede contener hasta {scalar(connection, "SELECT max(n_companies_in_sample) FROM groups")} sociedades. Train y validación deben separarse por <code>group_id</code>, no solo por <code>company_id</code>.</li>
          <li>ERP y antigüedad de conexión pueden explicar diferencias de cobertura; son señales de observabilidad, no necesariamente de salud.</li></ul>
        </div>
      </div>
    </section>

    <section class="section" id="tesoreria">
      <div class="section-head"><span>04</span><div><h2>Tesorería y comportamiento transaccional</h2><p>Flujos, volumen operativo, estacionalidad y calidad de clasificación.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Booked</small><strong>{tx_status[0]['n'] / counts['transactions']:.1%}</strong><span>del total</span></div>
        <div class="kpi"><small>Conciliación completa</small><strong>{reconciled:.1%}</strong><span>de movimientos</span></div>
        <div class="kpi"><small>Empresas activas último mes</small><strong>{fmt(latest_month['active_companies'], 0)}</strong><span>con movimientos</span></div>
        <div class="kpi"><small>Cambio mensual de actividad</small><strong>{tx_change:+.1%}</strong><span>último mes completo vs anterior</span></div>
      </div>
      <div class="panel">{chart_html(tx_fig, 440)}</div>
      <div class="grid two"><div class="panel">{chart_html(category_fig, 440)}</div><div class="panel narrative">
        <h3>Interpretación</h3><ul>
          <li>Los signos sí tienen semántica: positivo es entrada y negativo salida. Para el score conviene separar entradas, salidas y flujo neto; usar importe absoluto perdería dirección.</li>
          <li>La categoría <code>-</code> concentra {next(row['n'] for row in tx_categories if row['label'] == '-') / counts['transactions']:.1%} de los movimientos. La ausencia de categoría debe convertirse en indicador de calidad, no en categoría económica.</li>
          <li><code>transfer</code> puede inflar entradas y salidas sin representar actividad operativa. Debe distinguirse de <code>collection</code>/<code>payment</code>.</li>
          <li>El último mes termina el día de corte y puede estar incompleto. No debe interpretarse como deterioro sin corregir exposición temporal.</li>
        </ul></div></div>
    </section>

    {cash_sections}

    <section class="section" id="facturas">
      <div class="section-head"><span>10</span><div><h2>Facturas y ciclo de cobro/pago</h2><p>Estado documental, puntualidad y presión de circulante.</p></div></div>
      <div class="grid two"><div class="panel">{chart_html(invoice_fig, 430)}</div><div class="panel">{chart_html(invoice_time_fig, 430)}</div></div>
      <div class="callout warning"><b>No confundir estado con dirección.</b> El fichero no marca explícitamente factura emitida vs recibida. El signo, tipo documental y contexto de contraparte requieren validación antes de llamar “cuentas a cobrar” a todo pendiente.</div>
      <div class="insight-grid">
        <div><strong>{paid_count / counts['invoices']:.1%}</strong><span>documentos pagados</span></div>
        <div><strong>{overdue_count / counts['invoices']:.1%}</strong><span>marcados overdue</span></div>
        <div><strong>{compact(sum(max(row['pending'] or 0, 0) for row in invoice_status))}</strong><span>pendiente reportado · multimoneda</span></div>
        <div><strong>{fmt(scalar(connection, "SELECT median(date_diff('day', issuance_date, payment_date)) FROM invoices WHERE payment_date IS NOT NULL"), 0)} días</strong><span>mediana emisión → pago</span></div>
      </div>
    </section>

    <section class="section" id="deuda">
      <div class="section-head"><span>11</span><div><h2>Productos, deuda y saldo final</h2><p>Capacidad financiera y foto de liquidez al cierre.</p></div></div>
      <div class="grid two"><div class="panel">{chart_html(products_fig, 420)}</div><div class="panel">{chart_html(balance_fig, 420)}</div></div>
      <div class="grid two">
        <div class="panel"><h3>Deuda por tipo</h3>{table(["Tipo", "N", "Concedido*", "Pendiente*", "Uso mediano"], debt_rows)}<p class="caption">* Importes reportados mezclan monedas; comparar dentro de moneda/empresa.</p></div>
        <div class="panel narrative"><h3>Señales útiles para salud</h3><ul>
          <li><b>{fmt(negative_balances, 0)}</b> productos presentan saldo negativo al corte. Debe interpretarse según tipo: no equivale siempre a insolvencia.</li>
          <li>Uso mediano de financiación: <b>{debt_totals[2]:.1%}</b> en productos con concedido positivo. El nivel y su evolución aportan señales distintas.</li>
          <li>Solo {fmt(counts['debt_schedule_config'], 0)} de {fmt(counts['debt_products'], 0)} productos tienen calendario formal: la ausencia no implica falta de deuda.</li>
          <li>Para caja histórica: saldo mensual = saldo final − movimientos posteriores. Hay que hacerlo por producto y moneda.</li>
        </ul></div>
      </div>
    </section>

    <section class="section" id="relaciones">
      <div class="section-head"><span>12</span><div><h2>Relaciones entre señales</h2><p>Correlaciones de Pearson sobre agregados por empresa, limitadas a compañías cuya moneda declarada es EUR.</p></div></div>
      <div class="panel">{chart_html(corr_fig, 620)}</div>
      <div class="callout"><b>Cómo leerla.</b> Entradas y salidas elevadas suelen medir tamaño, no salud. La correlación no demuestra causalidad y queda dominada por colas largas. Para el score conviene usar ratios, tendencias y cambios intraempresa, además de transformaciones logarítmicas robustas.</div>
    </section>

    <section class="section" id="outliers">
      <div class="section-head"><span>13</span><div><h2>Outliers con significado financiero</h2><p>Detección IQR sobre señales agregadas por empresa en la cohorte EUR; no sobre IDs ni tipos categóricos.</p></div></div>
      <div class="grid two"><div class="panel"><h3>Extremos por métrica</h3>{table(["Métrica", "Mediana", "Banda IQR", "Fuera", "% empresas"], outlier_table)}</div><div class="panel">{chart_html(outlier_fig, 390)}</div></div>
      <div class="panel"><h3>Empresas más extremas · puntuación robusta multiseñal</h3>{table(["Empresa", "Saldo final", "Flujo neto", "Vencido", "Deuda", "Score robusto"], top_outlier_table)}<p class="caption">Un outlier no es un error ni una empresa enferma. Puede ser una empresa grande, un evento real, una moneda/producto mal interpretado o un problema de calidad. Debe revisarse su trayectoria mensual y su grupo.</p></div>
    </section>

    <section class="section" id="calidad">
      <div class="section-head"><span>14</span><div><h2>Calidad, cobertura y límites</h2><p>Qué puede sesgar el análisis y el futuro score.</p></div></div>
      <div class="grid two"><div class="panel"><h3>Campos incompletos o no normalizados</h3>{table(["Incidencia", "Filas", "%"], quality_rows)}</div><div class="panel"><h3>Integridad referencial y unicidad</h3>{table(["Comprobación", "Fallos"], integrity_rows)}</div></div>
      <div class="limitations">
        <article><b>Multimoneda</b><p><code>exchange_rate</code> existe, pero el diccionario no define de forma inequívoca la dirección de conversión. No se presenta un total “EUR” falso.</p></article>
        <article><b>Foto vs trayectoria</b><p>Los saldos son del corte final. No deben correlacionarse con meses históricos como si fueran contemporáneos.</p></article>
        <article><b>Sin etiqueta objetivo</b><p>El dataset no contiene una variable de salud observada. El EDA informa un score no supervisado o una estrategia de pseudoetiquetas, no valida acierto.</p></article>
        <article><b>Datos sintéticos</b><p>Las distribuciones imitan pymes reales, pero las conclusiones describen este generador y deben validarse fuera de muestra.</p></article>
      </div>
    </section>

    <section class="section conclusions" id="conclusiones">
      <div class="section-head"><span>15</span><div><h2>Conclusiones y siguiente diseño</h2><p>Qué debería salir de este EDA hacia el motor X-Ray.</p></div></div>
      <div class="conclusion-list">
        <article><span>01</span><div><h3>Construir panel empresa × mes</h3><p>Reconstruir saldo, entradas/salidas operativas, concentración de contraparte, puntualidad, pendiente y utilización de deuda. Conservar cobertura y calidad como features separadas.</p></div></article>
        <article><span>02</span><div><h3>Separar nivel, tendencia y estabilidad</h3><p>Para cada señal: nivel robusto, pendiente 3/6 meses, variación intermensual, volatilidad y persistencia. Así se distingue un bache de un deterioro estructural.</p></div></article>
        <article><span>03</span><div><h3>Normalizar sin borrar contexto</h3><p>Transformación log-sign para importes, ratios dentro de empresa y comparación con pares de tamaño/moneda. Nunca usar IDs como números.</p></div></article>
        <article><span>04</span><div><h3>Validar por grupo y tiempo</h3><p>Holdout completo por <code>group_id</code> y validación temporal. Medir estabilidad, anticipación y sensibilidad en ambas direcciones, no solo clasificación estática.</p></div></article>
      </div>
      <div class="final-note">Este informe caracteriza los datos; no asigna salud ni diagnostica empresas. Esa separación evita convertir volumen, ausencia de datos u outliers en riesgo sin evidencia.</div>
    </section>
    <footer>HackSpain 2026 · X-Ray Track · Informe generado de forma reproducible desde <code>analysis/generate_report.py</code></footer>
  </main>
</body>
</html>"""


CSS = """
@font-face{font-family:Inter;src:local("Arial")}*{box-sizing:border-box}:root{--navy:#102a43;--ink:#243b53;--muted:#627d98;--line:#d9e2ec;--paper:#fff;--bg:#f5f7fa;--blue:#1463ff;--cyan:#27b3c2;--green:#22a06b;--amber:#f59e0b;--red:#e5484d}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.sidebar{position:fixed;inset:0 auto 0 0;width:232px;padding:28px 22px;background:#0b1f33;color:#fff;display:flex;flex-direction:column;z-index:5}.brand{display:flex;align-items:center;gap:12px;margin-bottom:42px}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:11px;background:var(--blue);font-size:20px;font-weight:900}.brand b,.brand small{display:block}.brand small{color:#9fb3c8;font-size:11px;text-transform:uppercase;letter-spacing:.12em}.sidebar nav{display:grid;gap:3px}.sidebar nav a{padding:8px 10px;border-radius:7px;color:#bcccdc;text-decoration:none;font-size:12px}.sidebar nav a:hover{background:#173b5f;color:#fff}.side-note{margin-top:auto;color:#829ab1;font-size:11px;line-height:1.7}main{margin-left:232px}.hero{min-height:510px;padding:84px clamp(34px,7vw,110px);background:radial-gradient(circle at 86% 20%,rgba(39,179,194,.24),transparent 27%),linear-gradient(135deg,#102a43,#153e75);color:#fff}.eyebrow{color:#63d5df;font-size:11px;font-weight:800;letter-spacing:.18em}.hero h1{margin:30px 0 22px;max-width:850px;font-size:clamp(48px,7vw,84px);line-height:.98;letter-spacing:-.055em}.hero h1 em{color:#74d8e2;font-style:normal}.hero p{max-width:760px;color:#d9e2ec;font-size:17px}.hero-meta{display:flex;gap:12px;flex-wrap:wrap;margin-top:42px}.hero-meta span{padding:7px 11px;border:1px solid rgba(255,255,255,.2);border-radius:99px;color:#bcccdc;font-size:11px}.section{max-width:1280px;margin:auto;padding:68px clamp(28px,5vw,72px);border-bottom:1px solid var(--line)}.section-head{display:flex;gap:20px;align-items:flex-start;margin-bottom:28px}.section-head>span{color:var(--blue);font-size:12px;font-weight:900;letter-spacing:.12em}.section-head h2{margin:-7px 0 4px;color:var(--navy);font-size:30px;letter-spacing:-.03em}.section-head p{margin:0;color:var(--muted)}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}.kpi,.panel{background:var(--paper);border:1px solid var(--line);border-radius:14px;box-shadow:0 7px 24px rgba(16,42,67,.055)}.kpi{padding:21px}.kpi small,.kpi span{display:block;color:var(--muted)}.kpi strong{display:block;margin:5px 0;color:var(--navy);font-size:30px;letter-spacing:-.04em}.kpi span{font-size:11px}.compact-kpis .kpi strong{font-size:25px}.grid{display:grid;gap:18px;margin:18px 0}.grid.two{grid-template-columns:1fr 1fr}.panel{padding:18px;overflow:hidden}.panel h3{margin:5px 0 16px;color:var(--navy)}.callout{margin:18px 0;padding:18px 20px;border-left:4px solid var(--blue);border-radius:6px;background:#eaf2ff}.callout.warning{border-color:var(--amber);background:#fff7e8}.callout.insight{border-color:var(--cyan);background:#e9fbfc}.model{padding:28px}.model-flow{display:flex;align-items:center;gap:12px}.model-flow span{padding:12px 18px;border-radius:9px;background:#eaf2ff;color:#0b52cc;font-weight:800}.model-flow i{color:var(--muted);font-style:normal}.model-branches{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:22px}.model-branches div{padding:13px;border:1px solid var(--line);border-radius:9px}.model-branches b{font-size:18px;color:var(--navy)}.caption{color:var(--muted);font-size:11px}.narrative{padding:28px}.narrative ul{padding-left:19px}.narrative li{margin:0 0 13px}.insight-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}.insight-grid div{padding:20px;border-top:3px solid var(--cyan);background:#fff}.insight-grid strong,.insight-grid span{display:block}.insight-grid strong{font-size:24px;color:var(--navy)}.insight-grid span{color:var(--muted);font-size:11px}.table-wrap{overflow:auto;max-height:480px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:right}th{position:sticky;top:0;background:#f8fafc;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.08em}th:first-child,td:first-child{text-align:left}td small{display:block;max-width:250px;color:var(--muted);font-size:10px}.variable-table td:nth-child(2),.variable-table th:nth-child(2),.variable-table td:nth-child(3),.variable-table th:nth-child(3),.variable-table td:nth-child(4),.variable-table th:nth-child(4){text-align:left}.variable-panel{padding:0}.ok{color:var(--green);font-weight:800}.bad{color:var(--red);font-weight:800}code{padding:2px 5px;border-radius:4px;background:#edf2f7;color:#334e68}.limitations{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.limitations article{padding:20px;border:1px solid var(--line);border-radius:12px;background:#fff}.limitations b{color:var(--navy)}.limitations p{margin:8px 0 0;color:var(--muted);font-size:12px}.conclusions{background:#fff}.conclusion-list{display:grid;grid-template-columns:1fr 1fr;gap:12px}.conclusion-list article{display:flex;gap:18px;padding:24px;border:1px solid var(--line);border-radius:12px}.conclusion-list article>span{color:var(--blue);font-weight:900}.conclusion-list h3{margin:0 0 7px;color:var(--navy)}.conclusion-list p{margin:0;color:var(--muted)}.final-note{margin-top:28px;padding:24px;border-radius:12px;background:var(--navy);color:#d9e2ec}footer{padding:28px 6vw;color:var(--muted);font-size:11px;text-align:center}@media(max-width:980px){.sidebar{display:none}main{margin-left:0}.grid.two,.limitations{grid-template-columns:1fr 1fr}.kpis{grid-template-columns:1fr 1fr}}@media(max-width:680px){.hero{padding:55px 24px;min-height:auto}.section{padding:48px 18px}.grid.two,.limitations,.conclusion-list,.insight-grid{grid-template-columns:1fr}.kpis{grid-template-columns:1fr 1fr}.model-flow{flex-wrap:wrap}.hero h1{font-size:46px}}
"""


def main() -> None:
    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    setup(connection)
    OUTPUT.write_text(build_report(connection), encoding="utf-8")
    print(f"Generated {OUTPUT} ({OUTPUT.stat().st_size / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
