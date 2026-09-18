"""Explorador interactivo del histórico de caja reconstruido.

    .venv/Scripts/python.exe -m streamlit run analysis/app.py

Monta el mismo panel que alimenta el informe (`cash_history.setup_cash_panel`) y lo deja
navegable: cohorte filtrable, ficha por empresa, vista de grupo, estacionalidad por segmento
y una consola SQL sobre las tablas ya calculadas.
"""

from __future__ import annotations

import math
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from cash_history import MONTH_NAMES, QUARTER_START_MONTHS, setup_cash_panel

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PANEL_DB = ROOT / "analysis" / "cash.duckdb"
SOURCE_TABLES = (
    "groups",
    "companies",
    "banking_products",
    "debt_products",
    "debt_schedule_config",
    "balances",
    "invoices",
    "transactions",
)
COLORS = {
    "navy": "#102a43",
    "blue": "#1463ff",
    "cyan": "#27b3c2",
    "green": "#22a06b",
    "amber": "#f59e0b",
    "red": "#e5484d",
    "slate": "#64748b",
}
DIAGNOSIS_COLORS = {
    "caja negativa": COLORS["red"],
    "colchón crítico": COLORS["amber"],
    "deterioro estructural": "#b4232c",
    "bache recuperado": COLORS["cyan"],
    "mejora": COLORS["green"],
    "estable": COLORS["slate"],
    "serie con deriva": "#cbd5e1",
}

st.set_page_config(page_title="X-Ray · Explorador de caja", page_icon="◔", layout="wide")


@st.cache_resource(show_spinner=False)
def get_connection() -> tuple[duckdb.DuckDBPyConnection, bool]:
    """Abre el panel ya materializado; si no existe, lo reconstruye en memoria.

    En solo lectura: así varias sesiones o scripts pueden abrir el mismo fichero a la vez.
    Con acceso de escritura DuckDB lo bloquea y el resto falla con un error de E/S opaco. Las
    tablas temporales del filtro siguen funcionando porque viven en memoria.
    """
    if PANEL_DB.exists():
        connection = duckdb.connect(str(PANEL_DB), read_only=True)
        connection.execute("PRAGMA threads=4")
        return connection, True

    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    for name in SOURCE_TABLES:
        path = (DATA / f"{name}.csv").as_posix()
        connection.execute(
            f"CREATE VIEW {name} AS SELECT * FROM read_csv_auto('{path}', sample_size=-1)"
        )
    setup_cash_panel(connection)
    return connection, False


def query(sql: str, params: list | None = None):
    return get_connection()[0].execute(sql, params or []).df()


def missing(value) -> bool:
    """Los agregados devuelven NaN cuando no hay historia suficiente, no None."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def style_figure(figure: go.Figure, height: int = 380) -> go.Figure:
    figure.update_layout(
        height=height,
        # El margen superior tiene que alojar el título y la leyenda horizontal, que puede
        # ocupar dos líneas cuando hay tres series y el panel es estrecho. Con menos hueco la
        # leyenda se monta encima del título.
        margin=dict(l=48, r=22, t=86, b=44),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        hoverlabel=dict(bgcolor=COLORS["navy"], font_color="white"),
        title=dict(x=0, xanchor="left", y=1, yanchor="top", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    figure.update_xaxes(gridcolor="#e8eef6", zeroline=False)
    figure.update_yaxes(gridcolor="#e8eef6", zeroline=False)
    return figure


def euro(value, decimals: int = 0) -> str:
    if missing(value):
        return "—"
    absolute = abs(value)
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:,.1f} M €".replace(",", ".")
    if absolute >= 1_000:
        return f"{value / 1_000:,.1f} K €".replace(",", ".")
    return f"{value:,.{decimals}f} €".replace(",", ".")


# --------------------------------------------------------------------------------- filtros
with st.spinner("Reconstruyendo el histórico de caja desde los movimientos…"):
    connection, from_cache = get_connection()

options = {
    "diagnosis": [row[0] for row in connection.execute(
        "SELECT DISTINCT diagnosis FROM cash_summary ORDER BY 1").fetchall()],
    "profile": [row[0] for row in connection.execute(
        "SELECT DISTINCT profile FROM company_profile ORDER BY 1").fetchall()],
    "currency": [row[0] for row in connection.execute(
        "SELECT DISTINCT currency FROM cash_summary WHERE currency IS NOT NULL ORDER BY 1"
    ).fetchall()],
    "country": [row[0] for row in connection.execute(
        """
        SELECT DISTINCT coalesce(country, 'sin informar')
        FROM cash_summary ORDER BY 1
        """
    ).fetchall()],
}

st.sidebar.title("◔ X-Ray · Caja")
st.sidebar.caption(
    "Histórico mensual reconstruido hacia atrás desde el saldo del 2026-09-01 y validado "
    "contra él. Importes en EUR."
)
selected_diagnosis = st.sidebar.multiselect("Diagnóstico", options["diagnosis"])
selected_profile = st.sidebar.multiselect("Sector inferido", options["profile"])
selected_country = st.sidebar.multiselect("País", options["country"])
selected_currency = st.sidebar.multiselect("Moneda de la empresa", options["currency"])
erp_choice = st.sidebar.radio("ERP", ["Todas", "Con ERP conectado", "Sin ERP conectado"])
min_months = st.sidebar.slider("Meses observados mínimos", 1, 24, 6)
exclude_unreliable = st.sidebar.checkbox(
    "Excluir series con deriva", value=True,
    help="Empresas donde el back-cast exige mantener más de un mes entero de pagos en "
         "descubierto: indica cuentas no conectadas, no tensión real.",
)

conditions = ["s.n_valid_months >= ?"]
params: list = [min_months]
if selected_diagnosis:
    conditions.append(f"s.diagnosis IN ({', '.join('?' * len(selected_diagnosis))})")
    params.extend(selected_diagnosis)
if selected_profile:
    conditions.append(f"p.profile IN ({', '.join('?' * len(selected_profile))})")
    params.extend(selected_profile)
if selected_country:
    conditions.append(
        "coalesce(s.country, 'sin informar') IN "
        f"({', '.join('?' * len(selected_country))})"
    )
    params.extend(selected_country)
if selected_currency:
    conditions.append(f"s.currency IN ({', '.join('?' * len(selected_currency))})")
    params.extend(selected_currency)
if erp_choice == "Con ERP conectado":
    conditions.append("s.erp IS NOT NULL AND trim(s.erp) <> ''")
elif erp_choice == "Sin ERP conectado":
    conditions.append("(s.erp IS NULL OR trim(s.erp) = '')")
if exclude_unreliable:
    conditions.append("NOT s.has_drift")

selection_sql = f"""
    SELECT s.*, p.profile
    FROM cash_summary s LEFT JOIN company_profile p USING (company_id)
    WHERE {' AND '.join(conditions)}
"""
selection = query(selection_sql, params)
connection.execute("CREATE OR REPLACE TEMP TABLE selected AS " + selection_sql, params)

st.sidebar.metric("Empresas seleccionadas", f"{len(selection):,}".replace(",", "."))
if not from_cache:
    st.sidebar.info(
        "Panel reconstruido en memoria. Ejecuta `scripts/build_cash_db.py` una vez para que "
        "el arranque sea inmediato."
    )
if selection.empty:
    st.warning("Ninguna empresa cumple los filtros. Amplía la selección en la barra lateral.")
    st.stop()

cohort_tab, company_tab, group_tab, season_tab, sql_tab = st.tabs(
    ["Cohorte", "Empresa", "Grupo", "Estacionalidad", "SQL"]
)

# --------------------------------------------------------------------------------- cohorte
with cohort_tab:
    st.subheader("La cohorte seleccionada, mes a mes")
    totals = connection.execute(
        """
        SELECT median(cash_eur), median(coverage), median(trend_6m),
               avg(CASE WHEN cash_eur < 0 THEN 1 ELSE 0 END),
               median(median_outflow)
        FROM selected
        """
    ).fetchone()
    columns = st.columns(5)
    columns[0].metric("Caja mediana", euro(totals[0]))
    columns[1].metric(
        "Colchón mediano", "—" if missing(totals[1]) else f"{totals[1]:.2f} meses",
        help="Caja dividida entre el pago mensual mediano de la propia empresa.",
    )
    columns[2].metric(
        "Tendencia a 6 meses", "—" if missing(totals[2]) else f"×{totals[2]:.2f}",
        help="Caja típica de los últimos 3 meses contra la de hace medio año.",
    )
    columns[3].metric("En caja negativa", f"{totals[3]:.1%}")
    columns[4].metric("Pago mensual mediano", euro(totals[4]))

    monthly = query(
        """
        SELECT strftime(m.month_start, '%Y-%m') AS mes,
               count(*) AS empresas,
               median(m.cash_eur) AS caja_mediana,
               quantile_cont(m.cash_eur, 0.25) AS p25,
               quantile_cont(m.cash_eur, 0.75) AS p75,
               count(*) FILTER (WHERE m.cash_eur < 0) AS en_negativo
        FROM cash_metrics m JOIN selected USING (company_id)
        GROUP BY 1 ORDER BY 1
        """
    )
    evolution = go.Figure()
    evolution.add_trace(
        go.Scatter(x=monthly["mes"], y=monthly["p75"], line=dict(width=0), showlegend=False,
                   hoverinfo="skip")
    )
    evolution.add_trace(
        go.Scatter(x=monthly["mes"], y=monthly["p25"], name="Banda P25–P75", fill="tonexty",
                   fillcolor="rgba(20,99,255,.13)", line=dict(width=0),
                   hovertemplate="P25 %{y:,.0f} €<extra></extra>")
    )
    evolution.add_trace(
        go.Scatter(x=monthly["mes"], y=monthly["caja_mediana"], name="Caja mediana",
                   line=dict(color=COLORS["blue"], width=3),
                   hovertemplate="%{x}: %{y:,.0f} €<extra></extra>")
    )
    evolution.update_layout(title="Caja reconstruida (EUR)", yaxis_tickformat="~s")
    st.plotly_chart(style_figure(evolution, 420), use_container_width=True)

    left, right = st.columns(2)
    with left:
        diagnosis = query(
            "SELECT diagnosis, count(*) AS empresas FROM selected GROUP BY 1 ORDER BY 2"
        )
        figure = go.Figure(
            go.Bar(
                x=diagnosis["empresas"], y=diagnosis["diagnosis"], orientation="h",
                marker_color=[DIAGNOSIS_COLORS.get(name, COLORS["slate"])
                              for name in diagnosis["diagnosis"]],
                text=diagnosis["empresas"], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}: %{x} empresas<extra></extra>",
            )
        )
        figure.update_layout(title="Diagnóstico en el último mes observado")
        st.plotly_chart(style_figure(figure), use_container_width=True)
    with right:
        scatter = query(
            """
            SELECT company_id, diagnosis, cash_eur, coverage, median_outflow, n_valid_months
            FROM selected WHERE median_outflow > 0
            """
        )
        figure = go.Figure()
        for name, block in scatter.groupby("diagnosis"):
            figure.add_trace(
                go.Scatter(
                    x=block["median_outflow"], y=block["coverage"], mode="markers", name=name,
                    marker=dict(size=7, opacity=0.72,
                                color=DIAGNOSIS_COLORS.get(name, COLORS["slate"])),
                    customdata=block["company_id"],
                    hovertemplate="%{customdata}<br>Pago mensual %{x:,.0f} €"
                                  "<br>Colchón %{y:.2f} meses<extra></extra>",
                )
            )
        figure.update_layout(
            title="Colchón frente a tamaño de los pagos",
            xaxis_title="Pago mensual mediano (EUR, escala log)",
            yaxis_title="Meses de pagos cubiertos",
            xaxis_type="log",
        )
        figure.update_yaxes(range=[-2, 12])
        st.plotly_chart(style_figure(figure), use_container_width=True)

    st.markdown("**Empresas de la selección**")
    st.dataframe(
        selection[[
            "company_id", "group_id", "diagnosis", "profile", "cash_eur", "coverage",
            "trend_6m", "drawdown", "negative_months", "n_valid_months", "country", "currency",
        ]].sort_values("cash_eur"),
        use_container_width=True,
        hide_index=True,
        column_config={
            "company_id": "Empresa",
            "group_id": "Grupo",
            "diagnosis": "Diagnóstico",
            "profile": "Sector inferido",
            "cash_eur": st.column_config.NumberColumn("Caja (EUR)", format="%.0f"),
            "coverage": st.column_config.NumberColumn("Colchón (meses)", format="%.2f"),
            "trend_6m": st.column_config.NumberColumn("Tendencia 6m", format="%.2f"),
            "drawdown": st.column_config.NumberColumn("Drawdown", format="%.0f%%"),
            "negative_months": "Meses en negativo",
            "n_valid_months": "Meses observados",
            "country": "País",
            "currency": "Moneda",
        },
    )
    st.download_button(
        "Descargar selección en CSV",
        selection.to_csv(index=False).encode("utf-8"),
        file_name="caja_seleccion.csv",
        mime="text/csv",
    )

# ---------------------------------------------------------------------------------- empresa
with company_tab:
    ordered = selection.sort_values("cash_eur")["company_id"].tolist()
    company_id = st.selectbox(
        "Empresa", ordered,
        help="La lista respeta los filtros de la barra lateral y empieza por la caja más baja.",
    )
    detail = connection.execute(
        "SELECT * FROM selected WHERE company_id = ?", [company_id]
    ).df().iloc[0]

    badge = DIAGNOSIS_COLORS.get(detail["diagnosis"], COLORS["slate"])
    st.markdown(
        f"### {company_id} · <span style='color:{badge}'>{detail['diagnosis']}</span>",
        unsafe_allow_html=True,
    )
    columns = st.columns(6)
    columns[0].metric("Caja", euro(detail["cash_eur"]))
    columns[1].metric(
        "Colchón",
        "—" if missing(detail["coverage"]) else f"{detail['coverage']:.2f} m",
        help="Caja dividida entre el pago mensual mediano de la propia empresa.",
    )
    columns[2].metric(
        "Tendencia 6m",
        "—" if missing(detail["trend_6m"]) else f"×{detail['trend_6m']:.2f}",
        help="Necesita al menos 9 meses observados; en blanco si no hay historia suficiente.",
    )
    columns[3].metric(
        "Drawdown",
        "—" if missing(detail["drawdown"]) else f"{detail['drawdown']:.0%}",
        help="Caída desde el máximo de los últimos 12 meses.",
    )
    columns[4].metric("Meses en negativo", int(detail["negative_months"] or 0))
    columns[5].metric("Meses observados", int(detail["n_valid_months"]))

    series = query(
        """
        SELECT strftime(month_start, '%Y-%m') AS mes, cash_eur, net_flow_eur,
               inflow_eur, outflow_eur, cash_peak_12m, runway_months, drawdown, n_tx
        FROM cash_metrics WHERE company_id = ? ORDER BY month_index
        """,
        [company_id],
    )
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_trace(
        go.Bar(x=series["mes"], y=series["net_flow_eur"], name="Flujo neto del mes",
               marker_color=[COLORS["green"] if value >= 0 else COLORS["red"]
                             for value in series["net_flow_eur"]],
               opacity=0.45, hovertemplate="%{x}: %{y:,.0f} €<extra></extra>"),
        secondary_y=True,
    )
    figure.add_trace(
        go.Scatter(x=series["mes"], y=series["cash_eur"], name="Caja",
                   line=dict(color=COLORS["navy"], width=3),
                   hovertemplate="%{x}: %{y:,.0f} €<extra></extra>"),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(x=series["mes"], y=series["cash_peak_12m"], name="Máximo 12 meses",
                   line=dict(color=COLORS["slate"], width=1.5, dash="dot"),
                   hovertemplate="%{x}: %{y:,.0f} €<extra></extra>"),
        secondary_y=False,
    )
    figure.add_hline(y=0, line_color=COLORS["red"], line_width=1)
    figure.update_layout(title=f"Trayectoria de caja · {company_id}")
    figure.update_yaxes(title_text="Caja (EUR)", tickformat="~s", secondary_y=False)
    figure.update_yaxes(title_text="Flujo neto (EUR)", tickformat="~s", secondary_y=True,
                        showgrid=False)
    st.plotly_chart(style_figure(figure, 430), use_container_width=True)

    st.markdown("#### Por qué se movió")
    month_options = series["mes"].tolist()
    target_month = st.select_slider(
        "Mes a explicar", options=month_options, value=month_options[-1]
    )
    explain = query(
        """
        WITH monthly AS (
            SELECT category, date_trunc('month', booking_date)::DATE AS month_start,
                   sum(amount / units_per_eur) AS net_eur
            FROM tx_cash
            WHERE company_id = ? AND NOT is_sentinel
            GROUP BY 1, 2
        ), habitual AS (
            SELECT category, median(net_eur) AS habitual_eur FROM monthly GROUP BY 1
        )
        SELECT coalesce(nullif(m.category, '-'), 'sin categoría') AS categoria,
               m.net_eur AS mes_actual, h.habitual_eur AS habitual,
               m.net_eur - h.habitual_eur AS desviacion
        FROM monthly m JOIN habitual h USING (category)
        WHERE strftime(m.month_start, '%Y-%m') = ?
        ORDER BY abs(m.net_eur - h.habitual_eur) DESC
        LIMIT 12
        """,
        [company_id, target_month],
    )
    left, right = st.columns([3, 2])
    with left:
        figure = go.Figure(
            go.Bar(
                x=explain["desviacion"], y=explain["categoria"], orientation="h",
                marker_color=[COLORS["green"] if value >= 0 else COLORS["red"]
                              for value in explain["desviacion"]],
                hovertemplate="%{y}: %{x:,.0f} € frente a su mes típico<extra></extra>",
            )
        )
        figure.update_layout(
            title=f"Desviación por categoría en {target_month}",
            xaxis_title="Diferencia contra el mes habitual de esta empresa (EUR)",
        )
        st.plotly_chart(style_figure(figure, 400), use_container_width=True)
    with right:
        st.dataframe(
            explain, use_container_width=True, hide_index=True,
            column_config={
                "categoria": "Categoría",
                "mes_actual": st.column_config.NumberColumn("Este mes", format="%.0f"),
                "habitual": st.column_config.NumberColumn("Habitual", format="%.0f"),
                "desviacion": st.column_config.NumberColumn("Desviación", format="%.0f"),
            },
        )
        st.caption(
            "El mes habitual es la mediana de esa categoría en la historia de la propia "
            "empresa, así que la desviación aísla el movimiento real del nivel de actividad."
        )

    left, right = st.columns(2)
    with left:
        st.markdown("#### Serie mensual")
        st.dataframe(
            series, use_container_width=True, hide_index=True, height=320,
            column_config={
                "mes": "Mes",
                "cash_eur": st.column_config.NumberColumn("Caja", format="%.0f"),
                "net_flow_eur": st.column_config.NumberColumn("Flujo neto", format="%.0f"),
                "inflow_eur": st.column_config.NumberColumn("Cobros", format="%.0f"),
                "outflow_eur": st.column_config.NumberColumn("Pagos", format="%.0f"),
                "cash_peak_12m": st.column_config.NumberColumn("Máximo 12m", format="%.0f"),
                "runway_months": st.column_config.NumberColumn("Colchón", format="%.2f"),
                "drawdown": st.column_config.NumberColumn("Drawdown", format="%.2f"),
                "n_tx": "Movimientos",
            },
        )
    with right:
        st.markdown("#### Cuentas que forman la caja")
        st.dataframe(
            query(
                """
                SELECT product_id AS cuenta, currency AS divisa, anchor_date AS fecha_ancla,
                       anchor_balance AS saldo_ancla, anchor_balance_eur AS saldo_eur,
                       is_artifact AS centinela
                FROM cash_product WHERE company_id = ? ORDER BY abs(anchor_balance_eur) DESC
                """,
                [company_id],
            ),
            use_container_width=True, hide_index=True, height=150,
        )
        st.markdown("#### Contrapartes con más volumen")
        st.dataframe(
            query(
                """
                SELECT coalesce(counterparty_id, 'sin contraparte') AS contraparte,
                       count(*) AS movimientos,
                       sum(amount / units_per_eur) AS neto_eur
                FROM tx_cash WHERE company_id = ? AND NOT is_sentinel
                GROUP BY 1 ORDER BY sum(abs(amount / units_per_eur)) DESC LIMIT 8
                """,
                [company_id],
            ),
            use_container_width=True, hide_index=True, height=150,
        )

# ------------------------------------------------------------------------------------ grupo
with group_tab:
    group_options = query(
        """
        SELECT group_id,
               count(*) AS sociedades,
               sum(cash_eur) AS caja_grupo,
               count(*) FILTER (WHERE cash_eur < 0) AS en_negativo,
               sum(CASE WHEN cash_eur < 0 THEN -cash_eur ELSE 0 END) AS deficit
        FROM cash_summary WHERE NOT has_drift
        GROUP BY 1 HAVING count(*) > 1 ORDER BY deficit DESC, caja_grupo DESC
        """
    )
    st.subheader("Tesorería dentro del grupo")
    st.caption(
        "Los grupos aparecen ordenados por déficit interno: los primeros tienen filiales en "
        "descubierto mientras el grupo suma caja positiva. Se excluyen las series con deriva, "
        "porque un descubierto reconstruido de millones inventaría el déficit del grupo entero."
    )
    group_id = st.selectbox("Grupo", group_options["group_id"].tolist())
    group_row = group_options[group_options["group_id"] == group_id].iloc[0]
    columns = st.columns(4)
    columns[0].metric("Sociedades", int(group_row["sociedades"]))
    columns[1].metric("Caja del grupo", euro(group_row["caja_grupo"]))
    columns[2].metric("Filiales en negativo", int(group_row["en_negativo"]))
    columns[3].metric("Déficit interno", euro(group_row["deficit"]))

    members = query(
        """
        SELECT company_id, diagnosis, cash_eur, coverage, median_outflow, n_valid_months
        FROM cash_summary WHERE group_id = ? AND NOT has_drift ORDER BY cash_eur
        """,
        [group_id],
    )
    figure = go.Figure(
        go.Bar(
            x=members["cash_eur"], y=members["company_id"], orientation="h",
            marker_color=[DIAGNOSIS_COLORS.get(name, COLORS["slate"])
                          for name in members["diagnosis"]],
            hovertemplate="%{y}: %{x:,.0f} €<extra></extra>",
        )
    )
    figure.update_layout(title=f"Caja por sociedad · {group_id}", xaxis_tickformat="~s")

    stacked = query(
        """
        SELECT strftime(m.month_start, '%Y-%m') AS mes, m.company_id, m.cash_eur
        FROM cash_metrics m JOIN cash_summary s USING (company_id)
        WHERE s.group_id = ? AND NOT s.has_drift ORDER BY m.month_index
        """,
        [group_id],
    )
    trajectory = go.Figure()
    for member, block in stacked.groupby("company_id"):
        trajectory.add_trace(
            go.Scatter(x=block["mes"], y=block["cash_eur"], name=member, mode="lines",
                       hovertemplate=f"{member}<br>%{{x}}: %{{y:,.0f}} €<extra></extra>")
        )
    trajectory.update_layout(title="Trayectoria de cada sociedad", yaxis_tickformat="~s")

    left, right = st.columns(2)
    left.plotly_chart(style_figure(figure, 400), use_container_width=True)
    right.plotly_chart(style_figure(trajectory, 400), use_container_width=True)
    st.dataframe(
        members, use_container_width=True, hide_index=True,
        column_config={
            "company_id": "Empresa",
            "diagnosis": "Diagnóstico",
            "cash_eur": st.column_config.NumberColumn("Caja", format="%.0f"),
            "coverage": st.column_config.NumberColumn("Colchón (meses)", format="%.2f"),
            "median_outflow": st.column_config.NumberColumn("Pago mensual", format="%.0f"),
            "n_valid_months": "Meses observados",
        },
    )

# --------------------------------------------------------------------------- estacionalidad
with season_tab:
    st.subheader("Cuándo aprieta la caja")
    st.caption(
        "Cada mes se divide entre el pago mensual mediano de la propia empresa, así que el "
        "tamaño y la incorporación progresiva al dataset no se confunden con el ciclo. Los "
        "meses de cierre trimestral aparecen resaltados."
    )
    dimension = st.radio(
        "Segmentar por", ["Sector inferido", "ERP", "País", "Diagnóstico"], horizontal=True
    )
    expression = {
        "Sector inferido": "coalesce(p.profile, 'sin perfil')",
        "ERP": "CASE WHEN s.erp IS NULL OR trim(s.erp) = '' THEN 'Sin ERP' ELSE 'Con ERP' END",
        "País": "coalesce(s.country, 'sin informar')",
        "Diagnóstico": "s.diagnosis",
    }[dimension]

    heat = query(
        f"""
        WITH base AS (
            SELECT {expression} AS segmento, m.company_id, month(m.month_start) AS moy,
                   m.outflow_eur / s.median_outflow AS ratio
            FROM cash_metrics m
            JOIN selected s USING (company_id)
            LEFT JOIN company_profile p USING (company_id)
            WHERE s.median_outflow > 0 AND s.n_valid_months >= 12
        )
        SELECT segmento, moy, median(ratio) AS ratio,
               count(DISTINCT company_id) AS empresas
        FROM base GROUP BY 1, 2
        HAVING count(DISTINCT company_id) >= 10
        ORDER BY 1, 2
        """
    )
    if heat.empty:
        st.info("No hay suficientes empresas con 12 meses observados para este corte.")
    else:
        segments = sorted(heat["segmento"].unique())
        matrix = [
            [
                next(
                    (row["ratio"] for _, row in heat.iterrows()
                     if row["segmento"] == segment and row["moy"] == month),
                    None,
                )
                for month in range(1, 13)
            ]
            for segment in segments
        ]
        figure = go.Figure(
            go.Heatmap(
                z=matrix, x=list(MONTH_NAMES), y=segments, zmid=1,
                colorscale=[[0, "#1463ff"], [0.5, "#f8fafc"], [1, "#b4232c"]],
                text=[["" if value is None else f"{value:.2f}" for value in row]
                      for row in matrix],
                texttemplate="%{text}",
                hovertemplate="%{y} · %{x}: ×%{z:.2f}<extra></extra>",
            )
        )
        figure.update_layout(
            title="Pagos del mes ÷ pago mensual típico de cada empresa",
        )
        st.plotly_chart(style_figure(figure, 120 + 46 * len(segments)), use_container_width=True)

        uplift = query(
            f"""
            WITH base AS (
                SELECT {expression} AS segmento, m.company_id,
                       month(m.month_start) IN {QUARTER_START_MONTHS} AS cierre,
                       m.outflow_eur / s.median_outflow AS ratio
                FROM cash_metrics m
                JOIN selected s USING (company_id)
                LEFT JOIN company_profile p USING (company_id)
                WHERE s.median_outflow > 0 AND s.n_valid_months >= 12
            )
            SELECT segmento, count(DISTINCT company_id) AS empresas,
                   median(CASE WHEN cierre THEN ratio END) AS cierre_trimestral,
                   median(CASE WHEN NOT cierre THEN ratio END) AS resto,
                   median(CASE WHEN cierre THEN ratio END)
                     / nullif(median(CASE WHEN NOT cierre THEN ratio END), 0) - 1 AS sobrecoste
            FROM base GROUP BY 1 HAVING count(DISTINCT company_id) >= 10
            ORDER BY sobrecoste DESC
            """
        )
        st.dataframe(
            uplift, use_container_width=True, hide_index=True,
            column_config={
                "segmento": dimension,
                "empresas": "Empresas",
                "cierre_trimestral": st.column_config.NumberColumn(
                    "Ene/Abr/Jul/Oct", format="%.2f"),
                "resto": st.column_config.NumberColumn("Resto de meses", format="%.2f"),
                "sobrecoste": st.column_config.NumberColumn("Sobrecoste", format="%.1f%%"),
            },
        )

# -------------------------------------------------------------------------------------- SQL
with sql_tab:
    st.subheader("Consola SQL sobre el panel ya calculado")
    tables = query(
        """
        SELECT table_name AS tabla, column_count AS columnas, estimated_size AS filas
        FROM duckdb_tables() WHERE schema_name LIKE '%temp%'
        UNION ALL
        SELECT view_name, column_count, NULL FROM duckdb_views() WHERE NOT internal
        ORDER BY 1
        """
    )
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(tables, use_container_width=True, hide_index=True, height=420)
        st.caption(
            "`panel_product` y `panel_company` son la caja reconstruida; `cash_metrics` añade "
            "colchón, drawdown y tendencia; `cash_summary` resume cada empresa en su último "
            "mes; `tx_cash` son los movimientos de las cuentas de caja con la marca de "
            "centinela; `selected` es tu filtro actual."
        )
    with right:
        default_sql = (
            "SELECT s.diagnosis, count(*) AS empresas,\n"
            "       round(median(s.coverage), 2) AS colchon_meses,\n"
            "       round(median(s.trend_6m), 2) AS tendencia_6m\n"
            "FROM cash_summary s\n"
            "GROUP BY 1\n"
            "ORDER BY empresas DESC"
        )
        user_sql = st.text_area("Consulta", value=default_sql, height=220)
        if st.button("Ejecutar", type="primary"):
            try:
                result = query(user_sql)
                st.success(f"{len(result):,} filas".replace(",", "."))
                st.dataframe(result, use_container_width=True, hide_index=True)
                st.download_button(
                    "Descargar resultado",
                    result.to_csv(index=False).encode("utf-8"),
                    file_name="consulta.csv",
                    mime="text/csv",
                )
            except Exception as error:  # la consola es para explorar: el error es la respuesta
                st.error(str(error))
