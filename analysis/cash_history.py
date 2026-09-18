"""Reconstrucción del histórico de caja empresa × mes y diagnóstico de problemas de tesorería.

`balances.csv` solo contiene la foto final de cada producto, así que el histórico se
reconstruye hacia atrás con `transactions.csv` y se ancla en ese saldo:

    caja(p, t) = saldo_ancla(p) + Σ{importe: fecha ≤ t} − Σ{importe: fecha ≤ fecha_ancla(p)}

Cada producto se reconstruye en su propia moneda y solo después se convierte a EUR, de modo
que la validación contra el ancla es exacta y la conversión no contamina la serie.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

QUARTER_START_MONTHS = (1, 4, 7, 10)
MONTH_NAMES = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)

# Cuentas líquidas: son las únicas con saldo positivo transaccionable y movimientos propios.
CASH_TYPES = ("checking", "saving", "wallet")

# Primer mes del dataset y corte de extracción.
FIRST_MONTH = "2024-09-01"
N_MONTHS = 25  # 2024-09 … 2026-09
LAST_FULL_MONTH = "2026-08-01"  # 2026-09 solo contiene el día de extracción

# Ni un saldo ni un movimiento de esta magnitud pertenecen a una pyme: son valores centinela
# del generador (p. ej. 999.999.999 o 99.999.990.850). El percentil 99 de los movimientos está
# en 1,7 M EUR, así que el umbral deja fuera solo lo que no es interpretable.
ARTIFACT_EUR = 100_000_000

# Categorías usadas como huella operativa para el sector inferido.
PROFILE_CATEGORIES = (
    "collection",
    "bulk_collection",
    "payment",
    "bulk_payment",
    "utility",
    "salary",
    "social_security",
    "tax",
    "pos_settlement",
    "cash_settlement",
    "cash_withdrawal",
    "debt_repayment",
    "fee",
    "interest_charge",
    "transfer",
)

CATEGORY_LABELS = {
    "collection": "cobros",
    "bulk_collection": "cobros masivos",
    "payment": "pagos a proveedor",
    "bulk_payment": "pagos masivos",
    "utility": "suministros",
    "salary": "nóminas",
    "social_security": "seguridad social",
    "tax": "impuestos",
    "pos_settlement": "liquidación TPV",
    "cash_settlement": "liquidación de efectivo",
    "cash_withdrawal": "retirada de efectivo",
    "debt_repayment": "amortización de deuda",
    "fee": "comisiones",
    "interest_charge": "intereses",
    "transfer": "transferencias",
}

N_CLUSTERS = 5

# Tablas que componen el panel. Se materializan para que la app no repita el cálculo.
PANEL_TABLES = (
    "fx",
    "fx_gap",
    "cash_product",
    "cash_universe_audit",
    "months",
    "tx_cash",
    "sentinel_tx",
    "product_month_flow",
    "product_anchor_cum",
    "panel_product",
    "company_window",
    "company_flags",
    "panel_company",
    "cash_metrics",
    "cash_summary",
    "cash_lead_time",
    "company_category_mix",
    "company_profile",
)


@dataclass
class KMeansResult:
    assignments: list[int]
    labels: dict[int, str]


def setup_cash_panel(connection: duckdb.DuckDBPyConnection) -> None:
    """Crea las tablas de caja reconstruida, métricas y segmentos."""
    _build_country_norm(connection)
    _build_fx(connection)
    _build_universe(connection)
    _build_panel(connection)
    _build_metrics(connection)
    _build_segments(connection)


def persist_cash_panel(connection: duckdb.DuckDBPyConnection) -> None:
    """Copia el panel temporal a tablas persistentes de la base conectada.

    DuckDB resuelve primero el esquema temporal, así que la copia lee la tabla temporal y
    escribe la definitiva con el mismo nombre; al reabrir el fichero solo queda la persistente.
    """
    for name in PANEL_TABLES:
        connection.execute(f"CREATE OR REPLACE TABLE main.{name} AS SELECT * FROM {name}")


def build_cash_sections(connection: duckdb.DuckDBPyConnection, ui: Any) -> str:
    """Devuelve el HTML de las secciones de caja. `ui` aporta los helpers de formato."""
    records, scalar = ui.records, ui.scalar
    fmt, compact, table, chart_html = ui.fmt, ui.compact, ui.table, ui.chart_html
    colors = ui.colors

    # ---------------------------------------------------------------- método y validación
    audit = records(connection, "SELECT * FROM cash_universe_audit")
    fx_rows = records(
        connection,
        """
        SELECT currency, units_per_eur, n_obs,
               (SELECT count(*) FROM cash_product cp WHERE cp.currency = fx.currency) AS n_products
        FROM fx WHERE currency <> 'EUR'
        ORDER BY n_obs DESC NULLS LAST
        """,
    )
    fx_gaps = records(connection, "SELECT * FROM fx_gap ORDER BY n_products DESC")
    anchored = scalar(connection, "SELECT count(*) FROM cash_product WHERE NOT is_artifact")
    anchor_check = connection.execute(
        """
        WITH final_month AS (
            SELECT product_id, cash_native FROM panel_product WHERE month_start = DATE '2026-09-01'
        )
        SELECT count(*),
               count(*) FILTER (WHERE abs(f.cash_native - cp.anchor_balance) < 0.01),
               max(abs(f.cash_native - cp.anchor_balance))
        FROM final_month f JOIN cash_product cp USING (product_id)
        """
    ).fetchone()
    sentinel_tx_n = scalar(connection, "SELECT count(*) FROM tx_cash WHERE is_sentinel")
    sentinel_companies = scalar(connection, "SELECT count(*) FROM sentinel_tx")
    artifact_products = scalar(connection, "SELECT count(*) FROM cash_product WHERE is_artifact")
    unreliable = scalar(connection, "SELECT count(*) FROM company_flags WHERE NOT is_reliable")
    drift_companies = scalar(connection, "SELECT count(*) FROM cash_summary WHERE has_drift")
    n_companies_panel = scalar(connection, "SELECT count(*) FROM cash_summary")
    fx_gap_products = sum(row["n_products"] for row in fx_gaps)

    coverage_months = records(
        connection,
        """
        SELECT strftime(month_start, '%Y-%m') AS month_label,
               count(*) AS companies,
               median(cash_eur) AS med_cash,
               quantile_cont(cash_eur, 0.25) AS p25,
               quantile_cont(cash_eur, 0.75) AS p75,
               count(*) FILTER (WHERE cash_eur < 0) AS negatives,
               sum(cash_eur) AS total_cash
        FROM cash_metrics GROUP BY 1 ORDER BY 1
        """,
    )

    observed_fig = make_subplots(specs=[[{"secondary_y": True}]])
    observed_fig.add_trace(
        go.Bar(
            x=[row["month_label"] for row in coverage_months],
            y=[row["companies"] for row in coverage_months],
            name="Empresas observadas",
            marker_color=colors["light"],
            hovertemplate="%{x}: %{y} empresas<extra></extra>",
        ),
        secondary_y=False,
    )
    observed_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in coverage_months],
            y=[100 * row["negatives"] / row["companies"] for row in coverage_months],
            name="% con caja negativa",
            line=dict(color=colors["red"], width=3),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    observed_fig.update_layout(title="Cobertura del panel y caja negativa · ventana observada")
    observed_fig.update_yaxes(title_text="Empresas", secondary_y=False)
    observed_fig.update_yaxes(title_text="% negativas", secondary_y=True)

    audit_rows = [
        [
            f"<code>{html.escape(row['type'])}</code>",
            fmt(row["n_products"], 0),
            fmt(row["with_anchor"], 0),
            fmt(row["without_tx"], 0),
            compact(row["n_transactions"]),
            "Sí" if row["type"] in CASH_TYPES else "—",
        ]
        for row in audit
    ]
    fx_table_rows = [
        [
            f"<code>{html.escape(row['currency'])}</code>",
            fmt(row["units_per_eur"], 2),
            fmt(row["n_obs"] or 0, 0),
            fmt(row["n_products"], 0),
            '<span class="bad">baja</span>'
            if (row["n_obs"] or 0) < 50
            else '<span class="ok">suficiente</span>',
        ]
        for row in fx_rows
    ]

    # ------------------------------------------------------------------- evolución de caja
    cash_fig = go.Figure()
    cash_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in coverage_months],
            y=[row["p75"] for row in coverage_months],
            name="P75",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    cash_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in coverage_months],
            y=[row["p25"] for row in coverage_months],
            name="Banda P25–P75",
            fill="tonexty",
            fillcolor="rgba(20,99,255,.13)",
            line=dict(width=0),
            hovertemplate="P25 %{y:,.0f} €<extra></extra>",
        )
    )
    cash_fig.add_trace(
        go.Scatter(
            x=[row["month_label"] for row in coverage_months],
            y=[row["med_cash"] for row in coverage_months],
            name="Caja mediana",
            line=dict(color=colors["blue"], width=3),
            hovertemplate="%{x}: %{y:,.0f} €<extra></extra>",
        )
    )
    cash_fig.update_layout(
        title="Caja reconstruida por empresa · mediana y banda intercuartílica (EUR)",
        yaxis_tickformat="~s",
    )

    coverage_quantiles = connection.execute(
        """
        SELECT quantile_cont(coverage, 0.1), quantile_cont(coverage, 0.25),
               quantile_cont(coverage, 0.5), quantile_cont(coverage, 0.75),
               quantile_cont(coverage, 0.9)
        FROM cash_summary WHERE coverage IS NOT NULL
        """
    ).fetchone()
    trend_quantiles = connection.execute(
        """
        SELECT quantile_cont(trend_6m, 0.1), quantile_cont(trend_6m, 0.5),
               quantile_cont(trend_6m, 0.9),
               count(*) FILTER (WHERE trend_6m < 0.8), count(*) FILTER (WHERE trend_6m > 1.25),
               count(*)
        FROM cash_summary WHERE trend_6m IS NOT NULL
        """
    ).fetchone()

    coverage_hist = records(
        connection,
        """
        SELECT CASE
                 WHEN coverage < 0 THEN 'negativa'
                 WHEN coverage < 0.25 THEN '< 0,25 meses'
                 WHEN coverage < 0.5 THEN '0,25–0,5'
                 WHEN coverage < 1 THEN '0,5–1'
                 WHEN coverage < 3 THEN '1–3'
                 WHEN coverage < 6 THEN '3–6'
                 ELSE '> 6 meses' END AS bucket,
               count(*) AS n
        FROM cash_summary WHERE coverage IS NOT NULL
        GROUP BY 1
        ORDER BY min(coverage)
        """,
    )
    coverage_fig = go.Figure(
        go.Bar(
            x=[row["bucket"] for row in coverage_hist],
            y=[row["n"] for row in coverage_hist],
            marker_color=[
                colors["red"]
                if row["bucket"] in {"negativa", "< 0,25 meses"}
                else colors["amber"]
                if row["bucket"] in {"0,25–0,5", "0,5–1"}
                else colors["green"]
                for row in coverage_hist
            ],
            hovertemplate="%{x}: %{y} empresas<extra></extra>",
        )
    )
    coverage_fig.update_layout(
        title="Colchón de caja · meses de pagos que cubre el saldo",
        xaxis_title="Caja ÷ pago mensual mediano de la propia empresa",
    )

    # ------------------------------------------------------------------------ temporalidad
    seasonality = records(
        connection,
        """
        WITH base AS (
            SELECT m.company_id, m.month_start, m.outflow_eur, m.inflow_eur, s.median_outflow
            FROM cash_metrics m JOIN cash_summary s USING (company_id)
            WHERE s.median_outflow > 0 AND s.n_valid_months >= 12
        )
        SELECT month(month_start) AS moy, count(*) AS n,
               median(outflow_eur / median_outflow) AS out_ratio,
               median(inflow_eur / median_outflow) AS in_ratio
        FROM base GROUP BY 1 ORDER BY 1
        """,
    )
    category_seasonality = records(
        connection,
        """
        SELECT month(booking_date) AS moy,
               sum(CASE WHEN category = 'tax' THEN -amount ELSE 0 END) AS tax_out,
               sum(CASE WHEN category = 'social_security' THEN -amount ELSE 0 END) AS ss_out,
               sum(CASE WHEN category = 'salary' THEN -amount ELSE 0 END) AS salary_out
        FROM tx_cash WHERE NOT is_sentinel GROUP BY 1 ORDER BY 1
        """,
    )

    season_fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=(
            "Pagos y cobros del mes ÷ pago mensual mediano de cada empresa",
            "Volumen por categoría según el mes del año (EUR)",
        ),
    )
    season_fig.add_trace(
        go.Bar(
            x=[MONTH_NAMES[row["moy"] - 1] for row in seasonality],
            y=[row["out_ratio"] for row in seasonality],
            name="Pagos",
            marker_color=[
                colors["red"] if row["moy"] in QUARTER_START_MONTHS else colors["slate"]
                for row in seasonality
            ],
            hovertemplate="%{x}: ×%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    season_fig.add_trace(
        go.Scatter(
            x=[MONTH_NAMES[row["moy"] - 1] for row in seasonality],
            y=[row["in_ratio"] for row in seasonality],
            name="Cobros",
            line=dict(color=colors["green"], width=3),
            hovertemplate="%{x}: ×%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    for key, name, color in (
        ("tax_out", "Impuestos", colors["navy"]),
        ("salary_out", "Nóminas", colors["blue"]),
        ("ss_out", "Seguridad Social", colors["cyan"]),
    ):
        season_fig.add_trace(
            go.Bar(
                x=[MONTH_NAMES[row["moy"] - 1] for row in category_seasonality],
                y=[row[key] for row in category_seasonality],
                name=name,
                marker_color=color,
                hovertemplate="%{x}: %{y:,.0f} €<extra></extra>",
            ),
            row=2,
            col=1,
        )
    season_fig.update_layout(title="Temporalidad de la caja", barmode="group")
    season_fig.update_yaxes(tickformat="~s", row=2, col=1)

    segment_rows = _segment_seasonality(connection)
    profile_rows = records(
        connection,
        """
        SELECT p.profile,
               count(*) AS n,
               median(s.cash_eur) AS med_cash,
               median(s.coverage) AS med_coverage,
               avg(CASE WHEN s.diagnosis IN ('caja negativa', 'colchón crítico',
                                             'deterioro estructural') THEN 1 ELSE 0 END)
                   AS problem_rate
        FROM company_profile p JOIN cash_summary s USING (company_id)
        GROUP BY 1 ORDER BY n DESC
        """,
    )

    # ------------------------------------------------------------------------------ grupos
    # Las series con deriva se excluyen del agregado por grupo: un descubierto reconstruido de
    # varios millones es cobertura incompleta de cuentas y bastaría para inventar un déficit.
    group_cte = """
        WITH g AS (
            SELECT group_id, count(*) AS n_companies, sum(cash_eur) AS group_cash,
                   count(*) FILTER (WHERE cash_eur < 0) AS n_negative,
                   sum(CASE WHEN cash_eur < 0 THEN -cash_eur ELSE 0 END) AS deficit,
                   max(cash_eur) AS top_cash
            FROM cash_summary WHERE NOT has_drift GROUP BY 1
        )
    """
    group_stats = connection.execute(
        group_cte
        + """
        SELECT count(*), count(*) FILTER (WHERE n_companies > 1),
               count(*) FILTER (WHERE n_negative > 0 AND group_cash > 0),
               sum(CASE WHEN n_negative > 0 AND group_cash > 0 THEN deficit ELSE 0 END),
               median(CASE WHEN n_companies > 1 THEN top_cash / nullif(group_cash, 0) END)
        FROM g
        """
    ).fetchone()
    pooling_rows = records(
        connection,
        group_cte
        + """
        SELECT group_id, n_companies, group_cash, n_negative, deficit FROM g
        WHERE n_negative > 0 AND group_cash > 0 AND n_companies > 1
        ORDER BY deficit DESC LIMIT 10
        """,
    )

    # ------------------------------------------------------------------------ diagnóstico
    diagnosis_rows = records(
        connection,
        """
        SELECT diagnosis, count(*) AS n,
               median(cash_eur) AS med_cash, median(coverage) AS med_coverage,
               median(drawdown) AS med_drawdown, median(trend_6m) AS med_trend
        FROM cash_summary GROUP BY 1 ORDER BY n DESC
        """,
    )
    diagnosis_order = [row["diagnosis"] for row in diagnosis_rows]
    diagnosis_colors = {
        "caja negativa": colors["red"],
        "colchón crítico": colors["amber"],
        "deterioro estructural": "#b4232c",
        "bache recuperado": colors["cyan"],
        "mejora": colors["green"],
        "estable": colors["slate"],
        "serie con deriva": colors["light"],
    }
    diagnosis_fig = go.Figure(
        go.Bar(
            x=[row["n"] for row in reversed(diagnosis_rows)],
            y=[row["diagnosis"] for row in reversed(diagnosis_rows)],
            orientation="h",
            marker_color=[
                diagnosis_colors.get(row["diagnosis"], colors["slate"])
                for row in reversed(diagnosis_rows)
            ],
            text=[fmt(row["n"], 0) for row in reversed(diagnosis_rows)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x} empresas<extra></extra>",
        )
    )
    diagnosis_fig.update_layout(title="Diagnóstico de caja en el último mes observado")

    lead_rows = records(
        connection,
        """
        SELECT CASE
                 WHEN lead_months IS NULL THEN 'sin alerta previa'
                 WHEN lead_months = 0 THEN 'mismo mes'
                 WHEN lead_months <= 2 THEN '1–2 meses'
                 WHEN lead_months <= 5 THEN '3–5 meses'
                 WHEN lead_months <= 11 THEN '6–11 meses'
                 ELSE '12+ meses' END AS bucket,
               count(*) AS n
        FROM cash_lead_time
        GROUP BY 1
        ORDER BY min(coalesce(lead_months, -1))
        """,
    )
    lead_fig = go.Figure(
        go.Bar(
            x=[row["bucket"] for row in lead_rows],
            y=[row["n"] for row in lead_rows],
            marker_color=colors["blue"],
            hovertemplate="%{x}: %{y} empresas<extra></extra>",
        )
    )
    lead_fig.update_layout(
        title="Anticipación: margen entre la primera alerta y el primer mes en negativo"
    )
    lead_median = scalar(
        connection, "SELECT median(lead_months) FROM cash_lead_time WHERE lead_months IS NOT NULL"
    )
    lead_total = scalar(connection, "SELECT count(*) FROM cash_lead_time")
    lead_with_margin = scalar(
        connection, "SELECT count(*) FROM cash_lead_time WHERE lead_months >= 1"
    )

    trajectory_fig = _trajectory_figure(connection, records, colors)

    outlier_rows = records(
        connection,
        """
        WITH scored AS (
            SELECT company_id, cash_eur, coverage, net_flow_volatility, drawdown, diagnosis,
                   abs(cash_eur - median(cash_eur) OVER ())
                       / nullif(mad(cash_eur) OVER (), 0) AS z_cash,
                   abs(net_flow_volatility - median(net_flow_volatility) OVER ())
                       / nullif(mad(net_flow_volatility) OVER (), 0) AS z_vol,
                   abs(coverage - median(coverage) OVER ())
                       / nullif(mad(coverage) OVER (), 0) AS z_coverage
            FROM cash_summary
        )
        SELECT company_id, cash_eur, coverage, net_flow_volatility, drawdown, diagnosis,
               greatest(coalesce(z_cash, 0), coalesce(z_vol, 0), coalesce(z_coverage, 0))
                   AS robust_score
        FROM scored ORDER BY robust_score DESC LIMIT 12
        """,
    )

    examples = records(
        connection,
        """
        SELECT diagnosis, company_id, cash_eur, coverage, trend_6m, drawdown, n_valid_months
        FROM (
            SELECT *, row_number() OVER (PARTITION BY diagnosis ORDER BY abs(cash_eur) DESC) AS rn
            FROM cash_summary WHERE n_valid_months >= 12
        ) t WHERE rn <= 2
        ORDER BY diagnosis, rn
        """,
    )

    # -------------------------------------------------------------------------------- HTML
    total_tracked = scalar(connection, "SELECT count(DISTINCT company_id) FROM panel_company")
    first_window = coverage_months[0]
    last_window = coverage_months[-1]

    return f"""
    <section class="section" id="caja-metodo">
      <div class="section-head"><span>05</span><div><h2>Caja reconstruida: método y validación</h2><p>El histórico mensual de caja no existe en el dataset: se reconstruye hacia atrás desde la foto de saldos y se valida contra ella.</p></div></div>
      <div class="kpis">
        <div class="kpi"><small>Cuentas de caja ancladas</small><strong>{fmt(anchored, 0)}</strong><span>corriente, ahorro y wallet</span></div>
        <div class="kpi"><small>Validación contra el ancla</small><strong>{anchor_check[1] / anchor_check[0]:.1%}</strong><span>desvío máximo {anchor_check[2]:.0e} €</span></div>
        <div class="kpi"><small>Empresas con serie</small><strong>{fmt(n_companies_panel, 0)}</strong><span>de {fmt(total_tracked, 0)} con cuentas</span></div>
        <div class="kpi"><small>Centinelas retirados</small><strong>{fmt(sentinel_tx_n, 0)}</strong><span>movimientos en {fmt(sentinel_companies, 0)} empresas</span></div>
      </div>
      <div class="callout insight"><b>La fórmula.</b> Para cada producto <code>p</code> y mes <code>t</code>: <code>caja(p,t) = saldo_ancla(p) + Σ movimientos hasta t − Σ movimientos hasta la fecha del ancla</code>. Cada cuenta se reconstruye en su propia divisa y solo se convierte a EUR al agregar, así que la validación contra <code>balances.csv</code> es exacta por construcción y la divisa no contamina la serie. El ancla no es única: los saldos van del <b>2026-08-25</b> al <b>2026-09-01</b>, de modo que se usa la fecha real de cada producto.</div>
      <div class="grid two">
        <div class="panel"><h3>Qué entra y qué queda fuera</h3>{table(["Tipo de producto", "Productos", "Con saldo", "Sin movimientos", "Movimientos", "Es caja"], audit_rows)}<p class="caption">Solo las cuentas líquidas forman la caja. <code>investment</code> y <code>risk</code> no tienen ni un movimiento, así que su histórico no es reconstruible; tarjetas, TPV y plataformas de gasto miden consumo, no saldo disponible.</p></div>
        <div class="panel">{chart_html(observed_fig, 430)}</div>
      </div>
      <div class="callout warning"><b>La ventana observada manda.</b> El dataset no arranca con todas las empresas: en {first_window["month_label"]} solo {fmt(first_window["companies"], 0)} tienen actividad y en {last_window["month_label"]} son {fmt(last_window["companies"], 0)}. Antes del primer movimiento de una empresa el back-cast devuelve una línea plana que parece historia pero no lo es, así que cada serie empieza en su primer mes con movimientos y se corta en {LAST_FULL_MONTH[:7]}: septiembre de 2026 solo contiene el día de extracción.</div>
      <div class="grid two">
        <div class="panel"><h3>Tipo de cambio derivado del propio dataset</h3>{table(["Divisa", "Unidades por EUR", "Observaciones", "Cuentas", "Evidencia"], fx_table_rows)}<p class="caption">La dirección de <code>exchange_rate</code> no está documentada. Al filtrar los valores por defecto (1,0) el campo se comporta como unidades de divisa por euro y reproduce paridades reconocibles: USD 1,16, GBP 0,84, JPY 163,9. Se toma la mediana por divisa.</p></div>
        <div class="panel narrative"><h3>Límites asumidos, no escondidos</h3><ul>
          <li><b>{fmt(len(fx_gaps), 0)} divisas</b> ({fmt(fx_gap_products, 0)} cuentas) nunca informan un tipo distinto de 1,0. Convertirlas a la par inflaría los agregados —una cuenta en VND sumaría mil millones de "euros"—, así que se excluyen del panel en lugar de falsear la conversión.</li>
          <li><b>{fmt(artifact_products, 0)} cuentas</b> arrastran saldos centinela del generador (hasta 99.999.990.850 €) y <b>{fmt(sentinel_tx_n, 0)} movimientos</b> superan los 100 M €, cuando el percentil 99 real está en 1,7 M €. Un ingreso ficticio de 1.000 M deja toda la historia anterior en −1.000 M, así que se descuentan del acumulado; el ancla sigue cuadrando al céntimo.</li>
          <li><b>{fmt(unreliable, 0)} empresas</b> quedan marcadas como no fiables por esos centinelas y <b>{fmt(drift_companies, 0)}</b> más presentan deriva: el back-cast les exige mantener más de un mes entero de pagos en descubierto, algo que ninguna cuenta corriente sostiene. Apunta a cuentas no conectadas, no a tensión real, y son el 4% de la cola.</li>
          <li>La caja visible es la de las cuentas conectadas, no la de la empresa. La mediana solo cubre <b>{coverage_quantiles[2]:.2f} meses</b> de sus propios pagos, así que el nivel absoluto se lee como cobertura relativa, nunca como solvencia.</li>
        </ul></div>
      </div>
    </section>

    <section class="section" id="caja-evolucion">
      <div class="section-head"><span>06</span><div><h2>Cómo ha evolucionado la caja</h2><p>Nivel, dispersión y trayectoria de las {fmt(n_companies_panel, 0)} series reconstruidas.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Caja mediana</small><strong>{compact(last_window["med_cash"])} €</strong><span>{last_window["month_label"]}</span></div>
        <div class="kpi"><small>Colchón mediano</small><strong>{coverage_quantiles[2]:.2f} meses</strong><span>P25 {coverage_quantiles[1]:.2f} · P75 {coverage_quantiles[3]:.2f}</span></div>
        <div class="kpi"><small>Caja negativa</small><strong>{last_window["negatives"] / last_window["companies"]:.1%}</strong><span>frente al {first_window["negatives"] / first_window["companies"]:.1%} inicial</span></div>
        <div class="kpi"><small>Empeoran a 6 meses</small><strong>{trend_quantiles[3] / trend_quantiles[5]:.1%}</strong><span>y {trend_quantiles[4] / trend_quantiles[5]:.1%} mejoran</span></div>
      </div>
      <div class="panel">{chart_html(cash_fig, 430)}</div>
      <div class="grid two">
        <div class="panel">{chart_html(coverage_fig, 400)}</div>
        <div class="panel narrative"><h3>Qué dice la serie</h3><ul>
          <li>El nivel mediano se mantiene plano en torno a los {compact(last_window["med_cash"])} € durante los 24 meses: el agregado no se mueve, pero debajo hay empresas que se hunden y otras que se recuperan. Un score sobre el nivel del último mes no vería ninguna de las dos.</li>
          <li>La proporción de empresas con caja negativa baja del {first_window["negatives"] / first_window["companies"]:.1%} al {last_window["negatives"] / last_window["companies"]:.1%}. Parte de esa mejora es real y parte es efecto de la incorporación de empresas nuevas, que entran con saldo saneado.</li>
          <li>La banda intercuartílica es enorme —de {compact(last_window["p25"])} € a {compact(last_window["p75"])} €—, así que el nivel absoluto mide tamaño. La señal aprovechable es el cambio de cada empresa contra su propia historia.</li>
          <li>La tendencia a 6 meses divide la muestra en tres: {trend_quantiles[3] / trend_quantiles[5]:.1%} pierde más del 20% de su caja típica, {trend_quantiles[4] / trend_quantiles[5]:.1%} gana más del 25% y el resto se mueve dentro del ruido.</li>
        </ul></div>
      </div>
    </section>

    <section class="section" id="caja-temporalidad">
      <div class="section-head"><span>07</span><div><h2>Temporalidad: el calendario fiscal manda</h2><p>Estacionalidad normalizada dentro de cada empresa, para que el tamaño y la incorporación progresiva no se confundan con ciclo.</p></div></div>
      <div class="panel">{chart_html(season_fig, 620)}</div>
      <div class="callout insight"><b>El patrón es trimestral, no anual.</b> Los pagos se disparan en enero, abril, julio y octubre —los meses en que se liquidan los impuestos trimestrales en España— con un máximo de ×{max(row["out_ratio"] for row in seasonality):.2f} sobre el pago mensual típico, y caen a ×{min(row["out_ratio"] for row in seasonality):.2f} en agosto. El volumen de la categoría <code>tax</code> confirma la lectura: julio concentra {compact(max(row["tax_out"] for row in category_seasonality))} €. Las nóminas añaden su propio ciclo con picos en junio y diciembre, las pagas extra. Para el score esto es crítico: <b>una caída de caja en julio o en enero es calendario, no deterioro</b>, y compararla con el mes anterior genera falsos positivos sistemáticos.</div>
      <div class="grid two">
        <div class="panel"><h3>Sector inferido por huella de movimientos</h3>{table(["Perfil operativo", "Empresas", "Caja mediana", "Colchón", "% con problema"], [[html.escape(row["profile"]), fmt(row["n"], 0), compact(row["med_cash"]) + " €", f'{row["med_coverage"]:.2f} m' if row["med_coverage"] is not None else "—", f'{row["problem_rate"]:.1%}'] for row in profile_rows])}<p class="caption">El dataset no trae sector. Los perfiles salen de agrupar las empresas por la mezcla de categorías de sus movimientos (k-means determinista sobre cuotas normalizadas por rango) y se nombran con las dos categorías que más sobresalen en cada grupo.</p></div>
        <div class="panel"><h3>Presión del trimestre fiscal por segmento</h3>{table(["Segmento", "Empresas", "Pagos en mes de cierre", "Resto de meses", "Sobrecoste"], segment_rows)}<p class="caption">Cociente entre los pagos del mes y el pago mensual mediano de la propia empresa. Los meses de cierre trimestral son enero, abril, julio y octubre.</p></div>
      </div>
    </section>

    <section class="section" id="caja-grupos">
      <div class="section-head"><span>08</span><div><h2>Grupos: la caja no está donde hace falta</h2><p>La unidad de negocio es la empresa, pero la tesorería se gestiona en el grupo.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Grupos con serie</small><strong>{fmt(group_stats[0], 0)}</strong><span>{fmt(group_stats[1], 0)} con más de una sociedad</span></div>
        <div class="kpi"><small>Concentración interna</small><strong>{group_stats[4]:.0%}</strong><span>caja mediana en una sola filial</span></div>
        <div class="kpi"><small>Grupos descompensados</small><strong>{fmt(group_stats[2], 0)}</strong><span>filial en negativo y grupo en positivo</span></div>
        <div class="kpi"><small>Déficit reubicable</small><strong>{compact(group_stats[3])} €</strong><span>sin financiación externa</span></div>
      </div>
      <div class="grid two">
        <div class="panel"><h3>Grupos con déficit interno cubrible</h3>{table(["Grupo", "Sociedades", "Caja del grupo", "En negativo", "Déficit"], [[f'<code>{html.escape(row["group_id"])}</code>', fmt(row["n_companies"], 0), compact(row["group_cash"]) + " €", fmt(row["n_negative"], 0), compact(row["deficit"]) + " €"] for row in pooling_rows])}</div>
        <div class="panel narrative"><h3>Por qué importa para el producto</h3><ul>
          <li>En <b>{fmt(group_stats[2], 0)} grupos</b> hay filiales en descubierto mientras el grupo suma caja positiva. Son <b>{compact(group_stats[3])} €</b> que se podrían cubrir moviendo dinero dentro del perímetro en lugar de pagando una línea de crédito. El cálculo excluye las {fmt(drift_companies, 0)} series con deriva: una sola de ellas, con un descubierto reconstruido de millones, bastaría para inventar el déficit del grupo entero.</li>
          <li>La mediana de los grupos con varias sociedades tiene el <b>{group_stats[4]:.0%}</b> de la caja en una única filial: la tesorería está concentrada y las demás operan al límite.</li>
          <li>Un grupo puede llegar a 24 sociedades, así que la validación del score tiene que partirse por <code>group_id</code>. Dos filiales del mismo grupo comparten contrapartes, calendario y hasta movimientos espejo entre ellas.</li>
          <li>Leer la caja a nivel grupo cambia el diagnóstico de la filial: lo que aislado parece tensión puede ser una posición interna, y conviene distinguirlo antes de alertar.</li>
        </ul></div>
      </div>
    </section>

    <section class="section" id="caja-problemas">
      <div class="section-head"><span>09</span><div><h2>Problemas de caja: diagnóstico y anticipación</h2><p>Estado de cada empresa en su último mes observado, separando el bache del deterioro y midiendo con cuánto margen se veía venir.</p></div></div>
      <div class="grid two">
        <div class="panel">{chart_html(diagnosis_fig, 400)}</div>
        <div class="panel">{table(["Diagnóstico", "Empresas", "Caja mediana", "Colchón", "Drawdown", "Tendencia 6m"], [[html.escape(row["diagnosis"]), fmt(row["n"], 0), compact(row["med_cash"]) + " €", f'{row["med_coverage"]:.2f} m' if row["med_coverage"] is not None else "—", f'{row["med_drawdown"]:.0%}' if row["med_drawdown"] is not None else "—", f'×{row["med_trend"]:.2f}' if row["med_trend"] is not None else "—"] for row in diagnosis_rows])}<p class="caption">Reglas aplicadas en cascada sobre la ventana observada: deriva de reconstrucción, caja negativa, colchón por debajo de 0,25 meses de pagos, caída persistente de la caja típica a la mitad en 6 meses, bache recuperado por encima del 80% del pico y mejora superior al 50%.</p></div>
      </div>
      <div class="panel">{chart_html(trajectory_fig, 460)}</div>
      <div class="grid two">
        <div class="panel">{chart_html(lead_fig, 400)}</div>
        <div class="panel narrative"><h3>Cuánto margen daba la señal</h3><ul>
          <li>De las <b>{fmt(lead_total, 0)} empresas</b> que llegan a tener caja negativa en algún mes, <b>{lead_with_margin / lead_total:.0%}</b> encendían al menos una alerta antes de entrar en negativo, con una mediana de <b>{fmt(lead_median, 0)} meses</b> de antelación.</li>
          <li>Las alertas usadas son deliberadamente simples: caída del 25% sobre el pico de 12 meses, colchón por debajo de dos meses o pérdida del 30% de la caja en un trimestre. No hace falta un modelo complejo para ganar margen.</li>
          <li>El resto entra en negativo sin aviso previo. Suelen ser empresas con pocos meses observados o con un único movimiento grande, y marcan el suelo realista de la anticipación.</li>
          <li>La anticipación se mide contra un evento objetivo y reconstruido —el primer mes en negativo—, no contra una etiqueta de impago que el dataset no trae.</li>
        </ul></div>
      </div>
      <div class="grid two">
        <div class="panel"><h3>Extremos por puntuación robusta de caja</h3>{table(["Empresa", "Caja", "Colchón", "Volatilidad", "Diagnóstico", "Score"], [[f'<code>{html.escape(row["company_id"])}</code>', compact(row["cash_eur"]) + " €", f'{row["coverage"]:.2f} m' if row["coverage"] is not None else "—", compact(row["net_flow_volatility"]), html.escape(row["diagnosis"]), fmt(row["robust_score"], 1)] for row in outlier_rows])}<p class="caption">Desviación robusta (MAD) sobre nivel de caja, colchón y volatilidad del flujo. Un extremo no es una empresa enferma: puede ser tamaño, una operación puntual o cobertura parcial de cuentas.</p></div>
        <div class="panel"><h3>Casos concretos por diagnóstico</h3>{table(["Diagnóstico", "Empresa", "Caja", "Colchón", "Tendencia 6m", "Meses"], [[html.escape(row["diagnosis"]), f'<code>{html.escape(row["company_id"])}</code>', compact(row["cash_eur"]) + " €", f'{row["coverage"]:.2f} m' if row["coverage"] is not None else "—", f'×{row["trend_6m"]:.2f}' if row["trend_6m"] is not None else "—", fmt(row["n_valid_months"], 0)] for row in examples])}<p class="caption">Dos empresas por diagnóstico con al menos 12 meses observados. Cualquier alerta del sistema debe poder abrirse hasta este nivel: qué señal se movió, cuándo y cuánto.</p></div>
      </div>
    </section>
"""


def _segment_seasonality(connection: duckdb.DuckDBPyConnection, min_n: int = 25) -> list[list[str]]:
    """Presión del cierre trimestral por segmento declarado y por sector inferido."""
    rows = connection.execute(
        f"""
        WITH base AS (
            SELECT m.company_id, m.month_start, m.outflow_eur, s.median_outflow,
                   coalesce(p.profile, 'sin perfil') AS profile,
                   CASE WHEN s.erp IS NULL OR trim(s.erp) = '' THEN 'Sin ERP conectado'
                        ELSE 'Con ERP conectado' END AS erp_segment,
                   CASE WHEN s.country IS NULL THEN 'País sin informar'
                        WHEN s.country = 'ES' THEN 'España'
                        ELSE 'Fuera de España' END AS country_segment
            FROM cash_metrics m
            JOIN cash_summary s USING (company_id)
            LEFT JOIN company_profile p USING (company_id)
            WHERE s.median_outflow > 0 AND s.n_valid_months >= 12
        ), tagged AS (
            SELECT company_id, outflow_eur / median_outflow AS ratio,
                   month(month_start) IN {QUARTER_START_MONTHS} AS quarter_close,
                   segment, segment_kind
            FROM base,
                 LATERAL (VALUES (erp_segment, 'ERP'), (country_segment, 'País'),
                                 (profile, 'Sector inferido')) AS s(segment, segment_kind)
        )
        SELECT segment_kind, segment,
               count(DISTINCT company_id) AS companies,
               median(CASE WHEN quarter_close THEN ratio END) AS close_ratio,
               median(CASE WHEN NOT quarter_close THEN ratio END) AS other_ratio
        FROM tagged
        GROUP BY 1, 2
        HAVING count(DISTINCT company_id) >= {min_n}
        ORDER BY segment_kind, companies DESC
        """
    ).fetchall()

    output = []
    for kind, segment, companies, close_ratio, other_ratio in rows:
        uplift = (close_ratio / other_ratio - 1) if close_ratio and other_ratio else None
        output.append(
            [
                f"<b>{html.escape(segment)}</b><small>{html.escape(kind)}</small>",
                f"{companies:,}".replace(",", "."),
                f"×{close_ratio:.2f}" if close_ratio else "—",
                f"×{other_ratio:.2f}" if other_ratio else "—",
                f"{uplift:+.0%}" if uplift is not None else "—",
            ]
        )
    return output


def _trajectory_figure(connection: duckdb.DuckDBPyConnection, records, colors) -> go.Figure:
    """Trayectorias reales normalizadas a la caja típica de cada empresa."""
    picks = connection.execute(
        """
        SELECT diagnosis, company_id FROM (
            SELECT company_id, diagnosis,
                   row_number() OVER (PARTITION BY diagnosis
                                      ORDER BY n_valid_months DESC, abs(cash_eur) DESC) AS rn
            FROM cash_summary
            WHERE n_valid_months >= 18 AND median_cash > 10000
              AND diagnosis IN ('deterioro estructural', 'mejora', 'bache recuperado',
                                'caja negativa')
        ) t WHERE rn <= 2
        """
    ).fetchall()

    palette = {
        "deterioro estructural": colors["red"],
        "mejora": colors["green"],
        "bache recuperado": colors["cyan"],
        "caja negativa": colors["navy"],
    }
    figure = go.Figure()
    seen: set[str] = set()
    for diagnosis, company_id in picks:
        series = records(
            connection,
            f"""
            SELECT strftime(month_start, '%Y-%m') AS month_label,
                   cash_eur / nullif((SELECT median_cash FROM cash_summary
                                      WHERE company_id = '{company_id}'), 0) * 100 AS indexed
            FROM cash_metrics WHERE company_id = '{company_id}' ORDER BY month_index
            """,
        )
        figure.add_trace(
            go.Scatter(
                x=[row["month_label"] for row in series],
                y=[row["indexed"] for row in series],
                name=diagnosis,
                legendgroup=diagnosis,
                showlegend=diagnosis not in seen,
                line=dict(color=palette.get(diagnosis, colors["slate"]), width=2.5),
                hovertemplate=f"{company_id} · {diagnosis}<br>%{{x}}: %{{y:.0f}}<extra></extra>",
            )
        )
        seen.add(diagnosis)
    figure.add_hline(y=100, line_dash="dot", line_color=colors["slate"])
    figure.update_layout(
        title="Trayectorias reales · caja mensual indexada a 100 = caja típica de cada empresa",
        yaxis_title="Índice sobre caja mediana propia",
    )
    return figure


def _build_country_norm(connection: duckdb.DuckDBPyConnection) -> None:
    """Macro que reduce el país a ISO-2.

    `companies.country` es texto libre: España llega escrita de siete formas distintas
    (`ES`, `ESPAÑA`, `España`, `ESPANYA`, `Espanya`, `Spain` y una con espacio final), así que
    sin normalizar el mismo país se parte en varios segmentos. Los alias incluyen grafías que
    el train no trae, porque el test oculto puede escribirlo de otra manera.
    """
    aliases = {
        "ESPAÑA": "ES",
        "ESPANA": "ES",
        "ESPANYA": "ES",
        "SPAIN": "ES",
        "ALEMANIA": "DE",
        "GERMANY": "DE",
        "ITALIA": "IT",
        "ITALY": "IT",
        "PORTUGAL": "PT",
        "FRANCIA": "FR",
        "FRANCE": "FR",
        "HOLANDA": "NL",
        "PAISES BAJOS": "NL",
        "NETHERLANDS": "NL",
        "BELGICA": "BE",
        "BELGIUM": "BE",
        "REINO UNIDO": "GB",
        "UK": "GB",
        "ESTADOS UNIDOS": "US",
        "EEUU": "US",
        "USA": "US",
        "POLONIA": "PL",
        "POLAND": "PL",
        "SUECIA": "SE",
        "SWEDEN": "SE",
        "MALAYSIA": "MY",
        "MALASIA": "MY",
    }
    cases = "\n".join(f"WHEN '{alias}' THEN '{iso}'" for alias, iso in aliases.items())
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP MACRO country_norm(raw) AS
            CASE strip_accents(upper(trim(coalesce(raw, ''))))
                WHEN '' THEN NULL
                {cases}
                ELSE upper(trim(raw))
            END
        """
    )


def _build_fx(connection: duckdb.DuckDBPyConnection) -> None:
    """Tabla de cambio derivada del propio dataset.

    `exchange_rate` viene a 1.0 como valor por defecto en la mayoría de movimientos, pero
    cuando informa un valor real se comporta como unidades de divisa por euro (USD≈1.16,
    GBP≈0.84, JPY≈164). Se toma la mediana de los valores distintos de 1 y las divisas sin
    evidencia se quedan fuera de los agregados en EUR en lugar de convertirse a 1:1.
    """
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE fx AS
        WITH observed AS (
            SELECT bp.currency, t.exchange_rate AS rate
            FROM transactions t
            JOIN banking_products bp USING (product_id)
            WHERE bp.currency <> 'EUR'
              AND t.exchange_rate IS NOT NULL
              AND t.exchange_rate > 0
              AND t.exchange_rate <> 1
        )
        SELECT currency, median(rate) AS units_per_eur, count(*) AS n_obs
        FROM observed
        GROUP BY 1
        UNION ALL
        SELECT 'EUR', 1.0, NULL
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE fx_gap AS
        SELECT bp.currency, count(*) AS n_products, sum(abs(b.balance)) AS abs_balance_native
        FROM balances b
        JOIN banking_products bp USING (product_id)
        LEFT JOIN fx f ON f.currency = bp.currency
        WHERE bp.type IN {CASH_TYPES} AND f.currency IS NULL
        GROUP BY 1
        """
    )


def _build_universe(connection: duckdb.DuckDBPyConnection) -> None:
    """Productos de caja con ancla de saldo y tipo de cambio conocido."""
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE cash_product AS
        SELECT bp.product_id,
               bp.company_id,
               bp.currency,
               bp.type,
               f.units_per_eur,
               b.date::DATE AS anchor_date,
               b.balance AS anchor_balance,
               b.balance / f.units_per_eur AS anchor_balance_eur,
               abs(b.balance / f.units_per_eur) >= {ARTIFACT_EUR} AS is_artifact
        FROM banking_products bp
        JOIN balances b USING (product_id)
        JOIN fx f ON f.currency = bp.currency
        WHERE bp.type IN {CASH_TYPES}
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE cash_universe_audit AS
        WITH tx AS (SELECT product_id, count(*) AS n_tx FROM transactions GROUP BY 1)
        SELECT bp.type,
               count(*) AS n_products,
               count(b.product_id) AS with_anchor,
               count(*) FILTER (WHERE f.currency IS NULL) AS without_fx,
               count(*) FILTER (WHERE tx.n_tx IS NULL) AS without_tx,
               sum(coalesce(tx.n_tx, 0)) AS n_transactions
        FROM banking_products bp
        LEFT JOIN balances b USING (product_id)
        LEFT JOIN fx f ON f.currency = bp.currency
        LEFT JOIN tx USING (product_id)
        GROUP BY 1
        ORDER BY n_products DESC
        """
    )


def _build_panel(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE months AS
        SELECT (DATE '{FIRST_MONTH}' + INTERVAL (i) MONTH)::DATE AS month_start,
               (DATE '{FIRST_MONTH}' + INTERVAL (i + 1) MONTH - INTERVAL 1 DAY)::DATE AS month_end,
               i AS month_index
        FROM range(0, {N_MONTHS}) AS t(i)
        """
    )

    # Movimientos contabilizados de cuentas de caja, sin los importes centinela.
    #
    # Un movimiento centinela distorsiona toda la historia previa: como la serie se ancla en
    # el saldo final, un ingreso ficticio de 1.000 M deja los meses anteriores en −1.000 M.
    # Descontarlo del acumulado del mes y del acumulado hasta el ancla mantiene la validación
    # exacta contra `balances.csv` y elimina el escalón artificial.
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE tx_cash AS
        SELECT t.transaction_id, t.company_id, t.product_id, t.date::DATE AS booking_date,
               t.amount, t.category, t.counterparty_id, cp.currency, cp.units_per_eur,
               abs(t.amount / cp.units_per_eur) >= {ARTIFACT_EUR} AS is_sentinel
        FROM transactions t
        JOIN cash_product cp USING (product_id)
        WHERE t.status = 'booked'
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE sentinel_tx AS
        SELECT company_id, count(*) AS n_sentinel, max(abs(amount)) AS max_abs_amount
        FROM tx_cash WHERE is_sentinel GROUP BY 1
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE product_month_flow AS
        SELECT product_id,
               date_trunc('month', booking_date)::DATE AS month_start,
               sum(amount) AS net_flow,
               sum(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS inflow,
               sum(CASE WHEN amount < 0 THEN -amount ELSE 0 END) AS outflow,
               count(*) AS n_tx
        FROM tx_cash WHERE NOT is_sentinel
        GROUP BY 1, 2
        """
    )

    # Acumulado hasta la fecha de ancla, que cae a mitad de mes en parte de los productos.
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE product_anchor_cum AS
        SELECT cp.product_id,
               coalesce(sum(t.amount), 0) AS cum_to_anchor
        FROM cash_product cp
        LEFT JOIN tx_cash t
               ON t.product_id = cp.product_id
              AND NOT t.is_sentinel
              AND t.booking_date <= cp.anchor_date
        GROUP BY 1
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE panel_product AS
        WITH grid AS (
            SELECT cp.product_id, cp.company_id, cp.currency, cp.units_per_eur,
                   cp.anchor_balance, m.month_start, m.month_index,
                   coalesce(f.net_flow, 0) AS net_flow,
                   coalesce(f.inflow, 0) AS inflow,
                   coalesce(f.outflow, 0) AS outflow,
                   coalesce(f.n_tx, 0) AS n_tx
            FROM cash_product cp
            CROSS JOIN months m
            LEFT JOIN product_month_flow f
                   ON f.product_id = cp.product_id AND f.month_start = m.month_start
            WHERE NOT cp.is_artifact
        )
        SELECT g.product_id, g.company_id, g.currency, g.units_per_eur,
               g.month_start, g.month_index, g.n_tx,
               g.net_flow, g.inflow, g.outflow,
               -- Redondeo al céntimo, la precisión real del dinero. Sin él la suma en coma
               -- flotante deja las cuentas que vuelven a saldo cero en ±1e-13, con un signo que
               -- cambia según el orden de agregación: 28 empresas salían como 'caja negativa'
               -- con una caja de −0,0000000000002 EUR y el diagnóstico no era reproducible.
               round(g.anchor_balance
                 + sum(g.net_flow) OVER (PARTITION BY g.product_id ORDER BY g.month_index)
                 - a.cum_to_anchor, 2) AS cash_native
        FROM grid g
        JOIN product_anchor_cum a USING (product_id)
        """
    )

    # Ventana observada: la caja solo es interpretable desde el primer movimiento de la
    # empresa. Antes de esa fecha el back-cast devuelve una línea plana artificial.
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE company_window AS
        SELECT company_id,
               date_trunc('month', min(booking_date))::DATE AS first_month,
               date_trunc('month', max(booking_date))::DATE AS last_month,
               count(DISTINCT date_trunc('month', booking_date)) AS active_months
        FROM tx_cash
        WHERE NOT is_sentinel
        GROUP BY 1
        """
    )

    # Empresas cuya caja no es reconstruible con fiabilidad: saldo ancla centinela o
    # movimientos centinela. Se mantienen listadas pero fuera de los agregados de cohorte.
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE company_flags AS
        SELECT c.company_id,
               coalesce(a.n_artifact_products, 0) AS n_artifact_products,
               coalesce(s.n_sentinel, 0) AS n_sentinel_tx,
               coalesce(a.n_artifact_products, 0) = 0 AND coalesce(s.n_sentinel, 0) = 0
                 AS is_reliable
        FROM companies c
        LEFT JOIN (
            SELECT company_id, count(*) AS n_artifact_products
            FROM cash_product WHERE is_artifact GROUP BY 1
        ) a USING (company_id)
        LEFT JOIN sentinel_tx s USING (company_id)
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE panel_company AS
        SELECT p.company_id,
               p.month_start,
               p.month_index,
               -- Igual que en el producto: la conversión a EUR vuelve a introducir cola binaria
               -- y el agregado de la empresa tiene que ser estable entre ejecuciones.
               round(sum(p.cash_native / p.units_per_eur), 2) AS cash_eur,
               round(sum(p.net_flow / p.units_per_eur), 2) AS net_flow_eur,
               round(sum(p.inflow / p.units_per_eur), 2) AS inflow_eur,
               round(sum(p.outflow / p.units_per_eur), 2) AS outflow_eur,
               sum(p.n_tx) AS n_tx,
               count(*) AS n_products,
               coalesce(fl.is_reliable, TRUE) AS is_reliable,
               w.first_month,
               p.month_start >= w.first_month
                 AND p.month_start <= DATE '{LAST_FULL_MONTH}' AS in_window
        FROM panel_product p
        LEFT JOIN company_window w USING (company_id)
        LEFT JOIN company_flags fl USING (company_id)
        GROUP BY p.company_id, p.month_start, p.month_index, w.first_month, fl.is_reliable
        """
    )


def _build_metrics(connection: duckdb.DuckDBPyConnection) -> None:
    """Nivel, trayectoria, colchón y drawdown sobre la ventana observada."""
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE cash_metrics AS
        WITH valid AS (
            SELECT * FROM panel_company WHERE in_window AND is_reliable
        ), rolled AS (
            SELECT v.*,
                   row_number() OVER w AS obs_index,
                   avg(v.outflow_eur) OVER (
                       PARTITION BY v.company_id ORDER BY v.month_index
                       ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS outflow_3m,
                   median(v.cash_eur) OVER (
                       PARTITION BY v.company_id ORDER BY v.month_index
                       ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS cash_median_3m,
                   max(v.cash_eur) OVER (
                       PARTITION BY v.company_id ORDER BY v.month_index
                       ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) AS cash_peak_12m,
                   lag(v.cash_eur, 1) OVER w AS cash_prev,
                   lag(v.cash_eur, 3) OVER w AS cash_prev_3,
                   count(*) OVER (PARTITION BY v.company_id) AS n_valid_months
            FROM valid v
            WINDOW w AS (PARTITION BY v.company_id ORDER BY v.month_index)
        ), derived AS (
            SELECT company_id, month_start, month_index, obs_index, n_valid_months,
                   cash_eur, net_flow_eur, inflow_eur, outflow_eur, n_tx,
                   cash_median_3m, cash_peak_12m, outflow_3m, cash_prev, cash_prev_3,
                   CASE WHEN outflow_3m > 0 THEN least(cash_eur / outflow_3m, 60) END
                       AS runway_months,
                   CASE WHEN cash_peak_12m > 0
                        THEN greatest(0, 1 - cash_eur / cash_peak_12m) END AS drawdown,
                   CASE WHEN cash_peak_12m > 0 THEN cash_eur / cash_peak_12m END AS peak_ratio,
                   cash_eur < 0 AS is_negative,
                   CASE WHEN cash_prev_3 IS NOT NULL AND abs(cash_prev_3) > 1
                        THEN (cash_eur - cash_prev_3) / abs(cash_prev_3) END AS change_3m
            FROM rolled
        )
        SELECT d.*,
               lag(d.cash_median_3m, 6) OVER w AS cash_median_3m_lag6,
               max(d.drawdown) OVER (
                   PARTITION BY d.company_id ORDER BY d.month_index
                   ROWS BETWEEN 5 PRECEDING AND CURRENT ROW) AS drawdown_max_6m
        FROM derived d
        WINDOW w AS (PARTITION BY d.company_id ORDER BY d.month_index)
        """
    )

    # Resumen por empresa en su último mes observado + taxonomía de problemas.
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE cash_summary AS
        WITH last_obs AS (
            SELECT * FROM cash_metrics WHERE obs_index = n_valid_months
        ), streaks AS (
            SELECT company_id,
                   count(*) FILTER (WHERE is_negative) AS negative_months,
                   max(drawdown) AS max_drawdown,
                   stddev_pop(net_flow_eur) AS net_flow_volatility,
                   median(outflow_eur) AS median_outflow,
                   median(cash_eur) AS median_cash,
                   min(cash_eur) AS min_cash,
                   max(cash_eur) AS max_cash
            FROM cash_metrics GROUP BY 1
        )
        SELECT l.company_id,
               c.group_id, country_norm(c.country) AS country, c.currency, c.erp,
               l.month_start AS last_month,
               l.n_valid_months,
               l.cash_eur, l.cash_median_3m, l.runway_months, l.drawdown, l.change_3m,
               l.outflow_3m, l.peak_ratio, l.drawdown_max_6m,
               s.negative_months, s.max_drawdown, s.net_flow_volatility,
               s.median_cash, s.median_outflow, s.min_cash, s.max_cash,
               -- Meses de pagos que cubre la caja con el gasto mensual típico de la empresa.
               CASE WHEN s.median_outflow > 0 THEN l.cash_eur / s.median_outflow END AS coverage,
               -- Tendencia estructural: caja típica de los últimos 3 meses contra la de hace
               -- medio año, que separa un cambio de régimen de un mes malo.
               CASE WHEN l.cash_median_3m_lag6 > 0
                    THEN l.cash_median_3m / l.cash_median_3m_lag6 END AS trend_6m,
               -- La serie deriva cuando el back-cast exige un descubierto que ninguna cuenta
               -- corriente sostendría: más de un mes entero de pagos en negativo apunta a
               -- cuentas no conectadas, no a tensión. El corte cae en el 4% de la cola.
               CASE WHEN s.median_outflow > 0 THEN s.min_cash / s.median_outflow END AS drift_ratio,
               s.median_outflow > 0 AND s.min_cash < -s.median_outflow AS has_drift,
               CASE
                 WHEN s.median_outflow > 0 AND s.min_cash < -s.median_outflow
                      THEN 'serie con deriva'
                 WHEN l.cash_eur < 0 THEN 'caja negativa'
                 WHEN s.median_outflow > 0 AND l.cash_eur / s.median_outflow < 0.25
                      THEN 'colchón crítico'
                 WHEN l.cash_median_3m_lag6 > 0
                      AND l.cash_median_3m / l.cash_median_3m_lag6 <= 0.5
                      THEN 'deterioro estructural'
                 WHEN l.drawdown_max_6m >= 0.6 AND coalesce(l.peak_ratio, 1) >= 0.8
                      THEN 'bache recuperado'
                 WHEN l.cash_median_3m_lag6 > 0
                      AND l.cash_median_3m / l.cash_median_3m_lag6 >= 1.5 THEN 'mejora'
                 ELSE 'estable'
               END AS diagnosis
        FROM last_obs l
        JOIN companies c USING (company_id)
        LEFT JOIN streaks s USING (company_id)
        """
    )

    # Anticipación: meses entre la primera alerta y el primer mes de caja negativa.
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE cash_lead_time AS
        WITH alerts AS (
            SELECT company_id, obs_index,
                   (drawdown >= 0.25)
                     OR (runway_months IS NOT NULL AND runway_months < 2)
                     OR (change_3m IS NOT NULL AND change_3m <= -0.3) AS alert,
                   is_negative
            FROM cash_metrics
        ), first_negative AS (
            SELECT company_id, min(obs_index) AS neg_index
            FROM alerts WHERE is_negative GROUP BY 1
        ), first_alert AS (
            SELECT a.company_id, min(a.obs_index) AS alert_index
            FROM alerts a JOIN first_negative n USING (company_id)
            WHERE a.alert AND a.obs_index <= n.neg_index
            GROUP BY 1
        )
        SELECT n.company_id, n.neg_index, f.alert_index,
               n.neg_index - f.alert_index AS lead_months
        FROM first_negative n LEFT JOIN first_alert f USING (company_id)
        """
    )


def _build_segments(connection: duckdb.DuckDBPyConnection) -> None:
    """Segmento declarado (ERP/país) y sector inferido por mezcla de categorías."""
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE company_category_mix AS
        WITH scoped AS (
            SELECT t.company_id, t.category, abs(t.amount) AS volume
            FROM transactions t
            WHERE t.status = 'booked' AND t.category IN {PROFILE_CATEGORIES}
        ), total AS (
            SELECT company_id, sum(volume) AS total_volume, count(*) AS n_tx
            FROM scoped GROUP BY 1
        )
        SELECT s.company_id, s.category, sum(s.volume) / tt.total_volume AS share
        FROM scoped s JOIN total tt USING (company_id)
        WHERE tt.n_tx >= 24
        GROUP BY s.company_id, s.category, tt.total_volume
        """
    )

    rows = connection.execute(
        """
        SELECT company_id, category, share FROM company_category_mix
        WHERE company_id IN (SELECT company_id FROM cash_summary)
        """
    ).fetchall()

    mix: dict[str, dict[str, float]] = {}
    for company_id, category, share in rows:
        mix.setdefault(company_id, {})[category] = share

    result = _kmeans_profiles(mix)
    connection.execute(
        "CREATE OR REPLACE TEMP TABLE company_profile (company_id VARCHAR, profile VARCHAR)"
    )
    if result.assignments:
        connection.executemany(
            "INSERT INTO company_profile VALUES (?, ?)",
            [
                (company_id, result.labels[cluster])
                for company_id, cluster in zip(sorted(mix), result.assignments)
            ],
        )


def _kmeans_profiles(mix: dict[str, dict[str, float]]) -> KMeansResult:
    """K-means determinista sobre la huella de categorías, sin dependencias externas.

    Las cuotas se transforman con log1p y se estandarizan para que ninguna categoría
    voluminosa (cobros, pagos) domine la distancia.
    """
    companies = sorted(mix)
    if len(companies) < N_CLUSTERS:
        return KMeansResult([], {})

    raw = [[mix[c].get(cat, 0.0) for cat in PROFILE_CATEGORIES] for c in companies]

    # Transformación por rango: cada categoría pasa a su percentil dentro de la cohorte. Sin
    # ella, las categorías de mayor volumen (cobros y pagos) absorben toda la distancia y el
    # k-means devuelve un único clúster gigante.
    dims = len(PROFILE_CATEGORIES)
    points = [[0.0] * dims for _ in raw]
    for j in range(dims):
        order = sorted(range(len(raw)), key=lambda i: raw[i][j])
        for rank, i in enumerate(order):
            points[i][j] = rank / max(len(raw) - 1, 1)

    def distance(a: list[float], b: list[float]) -> float:
        return sum((x - y) ** 2 for x, y in zip(a, b))

    # Inicialización determinista tipo farthest-point.
    centroids = [points[0]]
    while len(centroids) < N_CLUSTERS:
        far_index = max(
            range(len(points)),
            key=lambda i: min(distance(points[i], centroid) for centroid in centroids),
        )
        centroids.append(points[far_index])

    assignments = [0] * len(points)
    for _ in range(60):
        moved = False
        for index, point in enumerate(points):
            best = min(range(N_CLUSTERS), key=lambda k: distance(point, centroids[k]))
            if best != assignments[index]:
                assignments[index] = best
                moved = True
        for k in range(N_CLUSTERS):
            members = [points[i] for i, a in enumerate(assignments) if a == k]
            if members:
                centroids[k] = [
                    sum(member[j] for member in members) / len(members) for j in range(dims)
                ]
        if not moved:
            break

    # Etiqueta legible: las dos categorías más sobre-representadas frente al conjunto.
    overall = [sum(row[j] for row in raw) / len(raw) for j in range(dims)]
    labels: dict[int, str] = {}
    for k in range(N_CLUSTERS):
        members = [raw[i] for i, a in enumerate(assignments) if a == k]
        if not members:
            labels[k] = f"Perfil {k + 1}"
            continue
        cluster_mean = [sum(m[j] for m in members) / len(members) for j in range(dims)]
        over = sorted(
            range(dims),
            key=lambda j: cluster_mean[j] / (overall[j] or 1e-9),
            reverse=True,
        )[:2]
        names = " + ".join(CATEGORY_LABELS[PROFILE_CATEGORIES[j]] for j in over)
        labels[k] = f"{names}"

    # Nombres únicos aunque dos clústeres compartan las mismas categorías dominantes.
    seen: dict[str, int] = {}
    for k in range(N_CLUSTERS):
        base = labels[k]
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            labels[k] = f"{base} ({seen[base]})"
    return KMeansResult(assignments, labels)
