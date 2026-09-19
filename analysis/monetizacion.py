#!/usr/bin/env python3
"""Reproduce y corrige las bases de ``context/monetizacion.md``.

El brief suma importes en crudo (sin FX) y solo aparta el centinela de 100.000 M€.
Este script recalcula las mismas colas —excedente ocioso, exposición a divisa,
demanda de financiación— con la capa de mapeo, tipos de cambio derivados del
dataset y la caja reconstruida de ``cash_history.py``.

Artefacto: ``analysis/monetizacion.html``.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "analysis" / "monetizacion.html"
CASH_DB = ROOT / "analysis" / "cash.duckdb"
ANALYSIS = Path(__file__).resolve().parent
for _p in (str(ANALYSIS), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from generate_report import (  # noqa: E402
    COLORS,
    CSS,
    chart_html,
    compact,
    fmt,
    records,
    scalar,
    table,
)
from mapping.load import attach  # noqa: E402

ARTIFACT_EUR = 100_000_000
WINDOW_START = "2024-09-01"
WINDOW_END = "2026-09-01"  # exclusive; 24 months
AS_OF = "2026-09-01"
ADOPTION = {"conservador": 0.25, "central": 0.35, "agresivo": 0.45}
DEPOSIT_BPS = 0.01
FX_BPS = 0.0015
MODULE_EUR_MONTH = 350
N_COMPANIES = 1286
N_EMBAT_CLIENTS = 400

CLAIMED = {
    "flow_annual_m": 275_160.0,
    "fx_annual_m": 19_812.0,
    "fx_pct": 7.2,
    "checking_m": 8_057.0,
    "investment_m": 242.0,
    "saving_m": 82.0,
    "checking_n": 3_612,
    "investment_n": 147,
    "saving_n": 8,
    "idle_ratio": 24.8,
    "excess_m": 2_378.0,
    "surplus_n": 375,
    "excess_median": 120_658.0,
    "deficit_n": 313,
    "financing_m": 19.2,
    "rev_central_m": 12.1,
    "rev_low_m": 4.3,
    "rev_high_m": 28.5,
}


def connect() -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    attach(connection, DATA)
    if CASH_DB.exists():
        connection.execute(f"ATTACH '{CASH_DB.as_posix()}' AS cash (READ_ONLY)")
    else:
        from cash_history import setup_cash_panel

        setup_cash_panel(connection)
        connection.execute("CREATE SCHEMA IF NOT EXISTS cash")
        for name in (
            "fx",
            "cash_product",
            "cash_summary",
            "cash_metrics",
            "panel_company",
            "company_flags",
        ):
            connection.execute(f"CREATE OR REPLACE VIEW cash.{name} AS SELECT * FROM {name}")
    return connection


def meur(value, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{fmt(value, decimals)} M€"


def pct(value, decimals: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{decimals}f} %"


def money(value) -> str:
    if value is None:
        return "—"
    return f"{fmt(value, 0)} €"


def signed_delta(measured, claimed, relative: bool = True) -> str:
    if claimed in (0, None) or measured is None:
        return "—"
    if relative:
        change = 100.0 * (measured - claimed) / claimed
        return f"{change:+.0f} %"
    return compact(measured - claimed)


def collect(connection: duckdb.DuckDBPyConnection) -> dict:
    """All figures used in the report, computed once."""
    d: dict = {}

    # --- FX table already in the cash panel
    d["fx"] = records(
        connection,
        """
        SELECT currency, units_per_eur, n_obs
        FROM cash.fx WHERE currency <> 'EUR'
        ORDER BY n_obs DESC NULLS LAST
        """,
    )

    # --- Snapshot by type: raw (brief) vs EUR cleaned
    d["snap_raw"] = records(
        connection,
        """
        SELECT bp.type,
               count(*) AS n,
               count(*) FILTER (WHERE b.balance > 0) AS n_pos,
               sum(greatest(b.balance, 0)) / 1e6 AS pos_m,
               sum(greatest(b.balance, 0)) FILTER (WHERE b.balance < 5e10) / 1e6 AS pos_ex100bn_m
        FROM balances b
        JOIN banking_products bp USING (product_id)
        GROUP BY 1
        ORDER BY pos_m DESC
        """,
    )
    d["snap_eur"] = records(
        connection,
        """
        SELECT bp.type,
               count(*) AS n,
               count(*) FILTER (WHERE b.balance / f.units_per_eur > 0) AS n_pos,
               sum(greatest(b.balance / f.units_per_eur, 0))
                   FILTER (WHERE abs(b.balance / f.units_per_eur) < 1e8) / 1e6 AS pos_eur_m
        FROM balances b
        JOIN banking_products bp USING (product_id)
        JOIN cash.fx f ON f.currency = bp.currency
        GROUP BY 1
        ORDER BY pos_eur_m DESC
        """,
    )

    d["saving_positive"] = scalar(
        connection,
        """
        SELECT count(*) FROM balances b
        JOIN banking_products bp USING (product_id)
        WHERE bp.type = 'saving' AND b.balance > 0
        """,
    )

    # --- Sentinels that inflate the brief
    d["sentinels"] = records(
        connection,
        """
        SELECT b.product_id, b.company_id, bp.type, bp.currency,
               b.balance, b.balance / f.units_per_eur AS eur
        FROM balances b
        JOIN banking_products bp USING (product_id)
        JOIN cash.fx f ON f.currency = bp.currency
        WHERE abs(b.balance / f.units_per_eur) >= 1e8
        ORDER BY abs(eur) DESC
        """,
    )

    # --- Flow 24m raw vs EUR
    flow = connection.execute(
        f"""
        WITH prod AS (
            SELECT product_id, currency FROM banking_products
            UNION ALL
            SELECT product_id, currency FROM debt_products
        )
        SELECT
            sum(abs(t.amount)) / 1e6 AS flow_raw_m,
            sum(abs(t.amount)) FILTER (
                WHERE p.currency IS NOT NULL AND p.currency <> c.currency
            ) / 1e6 AS fx_raw_m,
            sum(abs(t.amount) / coalesce(f.units_per_eur, 1))
                FILTER (WHERE abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}) / 1e6
                AS flow_eur_m,
            sum(abs(t.amount) / coalesce(f.units_per_eur, 1))
                FILTER (
                    WHERE p.currency IS NOT NULL AND p.currency <> c.currency
                      AND abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
                      AND f.currency IS NOT NULL
                ) / 1e6 AS fx_eur_m,
            count(*) AS n_tx,
            count(*) FILTER (WHERE p.currency IS NOT NULL AND p.currency <> c.currency) AS n_fx
        FROM transactions t
        JOIN companies c USING (company_id)
        LEFT JOIN prod p ON p.product_id = t.product_id
        LEFT JOIN cash.fx f ON f.currency = coalesce(p.currency, c.currency)
        WHERE t.date >= DATE '{WINDOW_START}' AND t.date < DATE '{WINDOW_END}'
        """
    ).fetchone()
    d["flow_raw_24_m"] = flow[0]
    d["fx_raw_24_m"] = flow[1]
    d["flow_eur_24_m"] = flow[2]
    d["fx_eur_24_m"] = flow[3]
    d["n_tx"] = flow[4]
    d["n_fx"] = flow[5]
    d["flow_raw_annual_m"] = flow[0] / 2
    d["fx_raw_annual_m"] = flow[1] / 2
    d["flow_eur_annual_m"] = flow[2] / 2
    d["fx_eur_annual_m"] = flow[3] / 2
    d["fx_raw_pct"] = 100.0 * flow[1] / flow[0]
    d["fx_eur_pct"] = 100.0 * flow[3] / flow[2]

    d["fx_month"] = records(
        connection,
        f"""
        WITH prod AS (
            SELECT product_id, currency FROM banking_products
            UNION ALL
            SELECT product_id, currency FROM debt_products
        )
        SELECT strftime(date_trunc('month', t.date), '%Y-%m') AS month_label,
               sum(abs(t.amount) / coalesce(f.units_per_eur, 1))
                   FILTER (WHERE abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}) / 1e6
                   AS flow_eur_m,
               sum(abs(t.amount) / coalesce(f.units_per_eur, 1))
                   FILTER (
                       WHERE p.currency IS NOT NULL AND p.currency <> c.currency
                         AND abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
                         AND f.currency IS NOT NULL
                   ) / 1e6 AS fx_eur_m
        FROM transactions t
        JOIN companies c USING (company_id)
        LEFT JOIN prod p ON p.product_id = t.product_id
        LEFT JOIN cash.fx f ON f.currency = coalesce(p.currency, c.currency)
        WHERE t.date >= DATE '{WINDOW_START}' AND t.date < DATE '{WINDOW_END}'
        GROUP BY 1 ORDER BY 1
        """,
    )

    # --- Reconstructed cash tails (canonical)
    tails = connection.execute(
        """
        SELECT
            count(*) AS n_panel,
            count(*) FILTER (WHERE NOT has_drift) AS n_reliable,
            count(*) FILTER (WHERE NOT has_drift AND median_outflow > 0
                             AND cash_eur > 2 * median_outflow) AS surplus_n,
            count(*) FILTER (WHERE NOT has_drift AND cash_eur < 0) AS deficit_now_n,
            count(*) FILTER (WHERE NOT has_drift AND min_cash < 0) AS deficit_ever_n,
            count(*) FILTER (WHERE NOT has_drift AND median_outflow > 0
                             AND cash_eur < 2 * median_outflow AND cash_eur >= 0) AS thin_n,
            sum(greatest(cash_eur - 2 * median_outflow, 0))
                FILTER (WHERE NOT has_drift AND median_outflow > 0) / 1e6 AS excess_m,
            median(cash_eur - 2 * median_outflow)
                FILTER (WHERE NOT has_drift AND median_outflow > 0
                        AND cash_eur > 2 * median_outflow) AS excess_median,
            quantile_cont(cash_eur - 2 * median_outflow, 0.9)
                FILTER (WHERE NOT has_drift AND median_outflow > 0
                        AND cash_eur > 2 * median_outflow) AS excess_p90,
            -sum(cash_eur) FILTER (WHERE NOT has_drift AND cash_eur < 0) / 1e6 AS hole_now_m,
            sum(cash_eur) FILTER (WHERE NOT has_drift) / 1e6 AS cash_reliable_m,
            median(cash_eur) FILTER (WHERE NOT has_drift) AS cash_median
        FROM cash.cash_summary
        """
    ).fetchone()
    keys = (
        "n_panel",
        "n_reliable",
        "surplus_n",
        "deficit_now_n",
        "deficit_ever_n",
        "thin_n",
        "excess_m",
        "excess_median",
        "excess_p90",
        "hole_now_m",
        "cash_reliable_m",
        "cash_median",
    )
    d.update(dict(zip(keys, tails)))

    d["diagnosis"] = records(
        connection,
        """
        SELECT diagnosis, count(*) AS n,
               sum(cash_eur) / 1e6 AS cash_m,
               median(cash_eur) AS med_cash
        FROM cash.cash_summary
        GROUP BY 1 ORDER BY n DESC
        """,
    )

    d["excess_hist"] = records(
        connection,
        """
        SELECT CASE
                 WHEN excess < 5e4 THEN '< 50 k€'
                 WHEN excess < 1e5 THEN '50–100 k€'
                 WHEN excess < 2.5e5 THEN '100–250 k€'
                 WHEN excess < 1e6 THEN '250 k€–1 M€'
                 WHEN excess < 5e6 THEN '1–5 M€'
                 ELSE '> 5 M€' END AS bucket,
               min(excess) AS sort_key,
               count(*) AS n,
               sum(excess) / 1e6 AS excess_m
        FROM (
            SELECT cash_eur - 2 * median_outflow AS excess
            FROM cash.cash_summary
            WHERE NOT has_drift AND median_outflow > 0
              AND cash_eur > 2 * median_outflow
        )
        GROUP BY 1 ORDER BY sort_key
        """,
    )

    d["cash_month"] = records(
        connection,
        """
        WITH tagged AS (
            SELECT m.company_id, m.month_start, m.cash_eur,
                   CASE
                     WHEN s.median_outflow > 0 AND s.cash_eur > 2 * s.median_outflow
                          AND NOT s.has_drift THEN 'excedente'
                     WHEN s.cash_eur < 0 AND NOT s.has_drift THEN 'déficit'
                     ELSE 'resto'
                   END AS tail
            FROM cash.cash_metrics m
            JOIN cash.cash_summary s USING (company_id)
        )
        SELECT strftime(month_start, '%Y-%m') AS month_label,
               tail,
               count(*) AS n,
               median(cash_eur) AS med_cash,
               sum(cash_eur) / 1e6 AS sum_m
        FROM tagged
        GROUP BY 1, 2
        ORDER BY 1, 2
        """,
    )

    d["scatter"] = records(
        connection,
        """
        SELECT company_id, group_id, cash_eur, median_outflow,
               cash_eur - 2 * median_outflow AS excess,
               diagnosis, n_valid_months
        FROM cash.cash_summary
        WHERE NOT has_drift AND median_outflow > 0 AND n_valid_months >= 6
        """,
    )

    d["group_excess"] = records(
        connection,
        """
        SELECT s.group_id,
               count(*) AS n_cos,
               sum(greatest(s.cash_eur - 2 * s.median_outflow, 0))
                   FILTER (WHERE s.median_outflow > 0) / 1e6 AS excess_m,
               count(*) FILTER (WHERE s.median_outflow > 0
                                AND s.cash_eur > 2 * s.median_outflow) AS surplus_n,
               count(*) FILTER (WHERE s.cash_eur < 0) AS deficit_n
        FROM cash.cash_summary s
        WHERE NOT s.has_drift
        GROUP BY 1
        ORDER BY excess_m DESC NULLS LAST
        LIMIT 12
        """,
    )

    d["corr"] = connection.execute(
        """
        SELECT
            corr(cash_eur, median_outflow) AS cash_opex,
            corr(cash_eur, n_valid_months) AS cash_history,
            corr(greatest(cash_eur - 2 * median_outflow, 0), median_outflow) AS excess_opex
        FROM cash.cash_summary
        WHERE NOT has_drift AND median_outflow > 0
        """
    ).fetchone()

    # Brief-style snapshot excess (raw, drop only the 100 bn product)
    brief_excess = connection.execute(
        f"""
        WITH spend AS (
            SELECT company_id,
                   sum(CASE WHEN amount < 0 THEN -amount ELSE 0 END) / 24.0 AS monthly_out
            FROM transactions
            WHERE date >= DATE '{WINDOW_START}' AND date < DATE '{WINDOW_END}'
            GROUP BY 1
        ), snap AS (
            SELECT b.company_id,
                   sum(greatest(b.balance, 0)) FILTER (
                       WHERE bp.type IN ('checking', 'saving', 'investment')
                         AND b.balance < 5e10
                   ) AS cash
            FROM balances b
            JOIN banking_products bp USING (product_id)
            GROUP BY 1
        )
        SELECT
            count(*) FILTER (WHERE s.cash > 2 * sp.monthly_out) AS surplus_n,
            sum(greatest(s.cash - 2 * sp.monthly_out, 0)) / 1e6 AS excess_m,
            median(s.cash - 2 * sp.monthly_out)
                FILTER (WHERE s.cash > 2 * sp.monthly_out) AS excess_median
        FROM snap s JOIN spend sp USING (company_id)
        """
    ).fetchone()
    d["brief_surplus_n"] = brief_excess[0]
    d["brief_excess_m"] = brief_excess[1]
    d["brief_excess_median"] = brief_excess[2]

    checking = next(r for r in d["snap_raw"] if r["type"] == "checking")
    investment = next(r for r in d["snap_raw"] if r["type"] == "investment")
    saving = next(r for r in d["snap_raw"] if r["type"] == "saving")
    d["claimed_checking_m"] = checking["pos_ex100bn_m"]
    d["claimed_investment_m"] = investment["pos_m"]
    d["claimed_saving_m"] = saving["pos_m"]
    d["claimed_checking_n"] = checking["n_pos"]
    d["claimed_investment_n"] = investment["n_pos"]
    d["claimed_saving_n"] = d["saving_positive"]
    rem = (investment["pos_m"] or 0) + (saving["pos_m"] or 0)
    d["claimed_idle_ratio"] = (checking["pos_ex100bn_m"] or 0) / rem if rem else None

    check_eur = next((r for r in d["snap_eur"] if r["type"] == "checking"), {})
    inv_eur = next((r for r in d["snap_eur"] if r["type"] == "investment"), {})
    sav_eur = next((r for r in d["snap_eur"] if r["type"] == "saving"), {})
    d["eur_checking_m"] = check_eur.get("pos_eur_m") or 0
    d["eur_investment_m"] = inv_eur.get("pos_eur_m") or 0
    d["eur_saving_m"] = sav_eur.get("pos_eur_m") or 0
    rem_eur = d["eur_investment_m"] + d["eur_saving_m"]
    d["eur_idle_ratio"] = d["eur_checking_m"] / rem_eur if rem_eur else None

    d["erp_surplus"] = records(
        connection,
        """
        SELECT coalesce(c.erp, 'sin ERP') AS erp,
               count(*) AS n,
               count(*) FILTER (WHERE NOT s.has_drift AND s.median_outflow > 0
                                AND s.cash_eur > 2 * s.median_outflow) AS surplus_n,
               sum(greatest(s.cash_eur - 2 * s.median_outflow, 0))
                   FILTER (WHERE NOT s.has_drift AND s.median_outflow > 0) / 1e6 AS excess_m
        FROM cash.cash_summary s
        JOIN companies c USING (company_id)
        GROUP BY 1
        ORDER BY n DESC
        """,
    )
    return d


def revenue_rows(excess_m: float, fx_annual_m: float, n_companies: int) -> list[dict]:
    rows = []
    for name, adopt in ADOPTION.items():
        deposit = excess_m * DEPOSIT_BPS * adopt
        fx = fx_annual_m * FX_BPS * adopt
        module = n_companies * MODULE_EUR_MONTH * 12 / 1e6 * adopt
        rows.append(
            {
                "name": name,
                "deposit": deposit,
                "fx": fx,
                "module": module,
                "intl": 0.0,
                "origination": 0.0,
                "total": deposit + fx + module,
            }
        )
    return rows


def build_charts(d: dict) -> dict[str, str]:
    charts = {}

    raw_types = [r for r in d["snap_raw"] if r["type"] in {"checking", "investment", "saving"}]
    eur_map = {r["type"]: r["pos_eur_m"] for r in d["snap_eur"]}
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Brief (crudo, −100.000 M€)",
            x=[r["type"] for r in raw_types],
            y=[
                r["pos_ex100bn_m"] if r["type"] == "checking" else r["pos_m"]
                for r in raw_types
            ],
            marker_color=COLORS["amber"],
            hovertemplate="%{x}: %{y:,.1f} M€<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Corregido (EUR, −centinelas)",
            x=[r["type"] for r in raw_types],
            y=[eur_map.get(r["type"], 0) for r in raw_types],
            marker_color=COLORS["blue"],
            hovertemplate="%{x}: %{y:,.1f} M€<extra></extra>",
        )
    )
    fig.update_layout(
        title="Saldo positivo por tipo de cuenta · brief frente a EUR limpio",
        barmode="group",
        yaxis_title="Saldo positivo (M€)",
        xaxis_title="Tipo de producto",
    )
    charts["snap"] = chart_html(fig, 380)

    fig = go.Figure(
        go.Bar(
            x=[r["bucket"] for r in d["excess_hist"]],
            y=[r["n"] for r in d["excess_hist"]],
            marker_color=COLORS["blue"],
            text=[f"{r['n']} · {r['excess_m']:.0f} M€" for r in d["excess_hist"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y} empresas<extra></extra>",
        )
    )
    fig.update_layout(
        title="Distribución del excedente real (caja − 2 meses de gasto)",
        xaxis_title="Tramo de excedente",
        yaxis_title="Empresas",
    )
    charts["excess_hist"] = chart_html(fig, 360)

    months = sorted({r["month_label"] for r in d["cash_month"]})
    fig = go.Figure()
    colors = {"excedente": COLORS["green"], "déficit": COLORS["red"], "resto": COLORS["slate"]}
    for tail, color in colors.items():
        series = {r["month_label"]: r["med_cash"] for r in d["cash_month"] if r["tail"] == tail}
        fig.add_trace(
            go.Scatter(
                x=months,
                y=[series.get(m) for m in months],
                name=tail.capitalize(),
                line=dict(color=color, width=3),
                hovertemplate="%{x}: %{y:,.0f} €<extra></extra>",
            )
        )
    fig.update_layout(
        title="Caja mediana reconstruida por cola (clasificación al corte)",
        xaxis_title="Mes",
        yaxis_title="Caja mediana (EUR)",
        yaxis_tickformat="~s",
    )
    charts["tails"] = chart_html(fig, 380)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=[r["month_label"] for r in d["fx_month"]],
            y=[r["flow_eur_m"] for r in d["fx_month"]],
            name="Flujo total (EUR)",
            marker_color=COLORS["light"],
            hovertemplate="%{x}: %{y:,.1f} M€<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[r["month_label"] for r in d["fx_month"]],
            y=[
                100 * r["fx_eur_m"] / r["flow_eur_m"] if r["flow_eur_m"] else 0
                for r in d["fx_month"]
            ],
            name="% en divisa distinta",
            yaxis="y2",
            line=dict(color=COLORS["cyan"], width=3),
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        title="Flujo mensual en EUR y peso de la divisa distinta a la de la empresa",
        xaxis_title="Mes",
        yaxis=dict(title="Flujo (M€)"),
        yaxis2=dict(title="% divisa", overlaying="y", side="right", rangemode="tozero"),
    )
    charts["fx"] = chart_html(fig, 380)

    sample = [r for r in d["scatter"] if r["median_outflow"] < 5_000_000 and r["cash_eur"] < 20_000_000]
    fig = go.Figure()
    by_diag: dict[str, list] = {}
    for row in sample:
        by_diag.setdefault(row["diagnosis"], []).append(row)
    diag_color = {
        "caja negativa": COLORS["red"],
        "colchón crítico": COLORS["amber"],
        "deterioro estructural": "#b4232c",
        "serie con deriva": "#cbd5e1",
        "bache recuperado": COLORS["cyan"],
        "mejora": COLORS["green"],
        "estable": COLORS["slate"],
    }
    for diag, rows in by_diag.items():
        fig.add_trace(
            go.Scatter(
                x=[r["median_outflow"] for r in rows],
                y=[r["cash_eur"] for r in rows],
                mode="markers",
                name=diag,
                marker=dict(color=diag_color.get(diag, COLORS["slate"]), size=7, opacity=0.7),
                hovertemplate="%{text}<extra></extra>",
                text=[f"{r['company_id']}: caja {r['cash_eur']:,.0f} €" for r in rows],
            )
        )
    max_opex = max((r["median_outflow"] for r in sample), default=1)
    fig.add_trace(
        go.Scatter(
            x=[0, max_opex],
            y=[0, 2 * max_opex],
            mode="lines",
            name="Colchón = 2 meses de gasto",
            line=dict(color=COLORS["navy"], width=2, dash="dash"),
            hoverinfo="skip",
        )
    )
    fig.update_layout(
        title="Caja frente a gasto mensual típico · cada punto es una empresa",
        xaxis_title="Gasto mensual mediano (EUR)",
        yaxis_title="Caja al corte (EUR)",
        xaxis_tickformat="~s",
        yaxis_tickformat="~s",
    )
    charts["scatter"] = chart_html(fig, 420)

    fig = go.Figure(
        go.Bar(
            y=[r["group_id"] for r in reversed(d["group_excess"])],
            x=[r["excess_m"] for r in reversed(d["group_excess"])],
            orientation="h",
            marker_color=COLORS["blue"],
            text=[f"{r['surplus_n']} emp." for r in reversed(d["group_excess"])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{x:.1f} M€<extra></extra>",
        )
    )
    fig.update_layout(
        title="Excedente concentrado en pocos grupos",
        xaxis_title="Excedente (M€)",
        yaxis_title="Grupo",
    )
    charts["groups"] = chart_html(fig, 400)

    claimed_rev = [4.3, 12.1, 28.5]
    corr = revenue_rows(d["excess_m"], d["fx_eur_annual_m"], N_COMPANIES)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Brief (bases crudas)",
            x=["Conservador", "Central", "Agresivo"],
            y=claimed_rev,
            marker_color=COLORS["amber"],
            hovertemplate="%{x}: %{y:.1f} M€/año<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Recalculado (EUR + caja reconstruida)",
            x=["Conservador", "Central", "Agresivo"],
            y=[r["total"] for r in corr],
            marker_color=COLORS["blue"],
            hovertemplate="%{x}: %{y:.1f} M€/año<extra></extra>",
        )
    )
    fig.update_layout(
        title="Ingreso anual imputado · mismas hipótesis, distintas bases",
        barmode="group",
        yaxis_title="M€ / año",
        xaxis_title="Escenario de adopción (25 / 35 / 45 %)",
    )
    charts["revenue"] = chart_html(fig, 360)

    stacked = revenue_rows(d["excess_m"], d["fx_eur_annual_m"], N_COMPANIES)
    central = next(r for r in stacked if r["name"] == "central")
    fig = go.Figure(
        go.Bar(
            x=["Excedente (100 pb)", "Divisa (15 pb)", "Módulo (350 €/mes)"],
            y=[central["deposit"], central["fx"], central["module"]],
            marker_color=[COLORS["green"], COLORS["cyan"], COLORS["blue"]],
            text=[f"{v:.2f} M€" for v in (central["deposit"], central["fx"], central["module"])],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y:.2f} M€<extra></extra>",
        )
    )
    fig.update_layout(
        title="Mix del escenario central corregido · adopción 35 %",
        yaxis_title="Ingreso (M€ / año)",
        xaxis_title="Línea de producto",
    )
    charts["mix"] = chart_html(fig, 340)
    return charts


def build_html(d: dict, charts: dict[str, str]) -> str:
    corr_rev = revenue_rows(d["excess_m"], d["fx_eur_annual_m"], N_COMPANIES)
    central = next(r for r in corr_rev if r["name"] == "central")
    low = next(r for r in corr_rev if r["name"] == "conservador")
    high = next(r for r in corr_rev if r["name"] == "agresivo")
    embat400 = revenue_rows(d["excess_m"], d["fx_eur_annual_m"], N_EMBAT_CLIENTS)
    central400 = next(r for r in embat400 if r["name"] == "central")

    compare_rows = [
        [
            "Flujo anual (suma |importe| / 2)",
            meur(CLAIMED["flow_annual_m"], 0),
            meur(d["flow_raw_annual_m"], 0),
            meur(d["flow_eur_annual_m"], 0),
            signed_delta(d["flow_eur_annual_m"], CLAIMED["flow_annual_m"]),
        ],
        [
            "Expuesto a divisa, anual",
            meur(CLAIMED["fx_annual_m"], 0),
            meur(d["fx_raw_annual_m"], 0),
            meur(d["fx_eur_annual_m"], 0),
            signed_delta(d["fx_eur_annual_m"], CLAIMED["fx_annual_m"]),
        ],
        [
            "Peso de la divisa",
            pct(CLAIMED["fx_pct"]),
            pct(d["fx_raw_pct"]),
            pct(d["fx_eur_pct"]),
            signed_delta(d["fx_eur_pct"], CLAIMED["fx_pct"]),
        ],
        [
            "Caja en corriente (positivo)",
            meur(CLAIMED["checking_m"], 0),
            meur(d["claimed_checking_m"], 0),
            meur(d["eur_checking_m"], 0),
            signed_delta(d["eur_checking_m"], CLAIMED["checking_m"]),
        ],
        [
            "Cuentas de ahorro con saldo",
            f"{CLAIMED['saving_n']} · {meur(CLAIMED['saving_m'], 0)}",
            f"{d['claimed_saving_n']} · {meur(d['claimed_saving_m'], 0)}",
            f"{d['claimed_saving_n']} · {meur(d['eur_saving_m'], 1)}",
            signed_delta(d["eur_saving_m"], CLAIMED["saving_m"]),
        ],
        [
            "Inversión (positivo)",
            f"{CLAIMED['investment_n']} · {meur(CLAIMED['investment_m'], 0)}",
            f"{d['claimed_investment_n']} · {meur(d['claimed_investment_m'], 0)}",
            f"{d['claimed_investment_n']} · {meur(d['eur_investment_m'], 0)}",
            signed_delta(d["eur_investment_m"], CLAIMED["investment_m"]),
        ],
        [
            "Ratio ocioso / remunerado",
            f"{CLAIMED['idle_ratio']:.1f}×",
            f"{d['claimed_idle_ratio']:.1f}×",
            f"{d['eur_idle_ratio']:.1f}×" if d["eur_idle_ratio"] else "—",
            signed_delta(d["eur_idle_ratio"], CLAIMED["idle_ratio"]),
        ],
        [
            "Excedente sobre 2 meses de gasto",
            meur(CLAIMED["excess_m"], 0),
            meur(d["brief_excess_m"], 0),
            meur(d["excess_m"], 0),
            signed_delta(d["excess_m"], CLAIMED["excess_m"]),
        ],
        [
            "Empresas con excedente",
            fmt(CLAIMED["surplus_n"], 0),
            fmt(d["brief_surplus_n"], 0),
            fmt(d["surplus_n"], 0),
            signed_delta(d["surplus_n"], CLAIMED["surplus_n"]),
        ],
        [
            "Excedente mediano",
            money(CLAIMED["excess_median"]),
            money(d["brief_excess_median"]),
            money(d["excess_median"]),
            signed_delta(d["excess_median"], CLAIMED["excess_median"]),
        ],
        [
            "Empresas en déficit de caja",
            fmt(CLAIMED["deficit_n"], 0),
            "— (no reproducible)",
            f"{fmt(d['deficit_now_n'], 0)} ahora / {fmt(d['deficit_ever_n'], 0)} alguna vez",
            "—",
        ],
        [
            "Demanda de financiación (agujero actual)",
            meur(CLAIMED["financing_m"], 1),
            "—",
            meur(d["hole_now_m"], 2),
            signed_delta(d["hole_now_m"], CLAIMED["financing_m"]),
        ],
    ]

    rev_rows = []
    label = {"conservador": "Conservador", "central": "Central", "agresivo": "Agresivo"}
    claimed_split = {
        "conservador": (1.8, 1.2, 1.1, 4.3),
        "central": (5.4, 3.7, 2.7, 12.1),
        "agresivo": (10.7, 11.9, 5.4, 28.5),
    }
    for row in corr_rev:
        cdep, cfx, cmod, ctot = claimed_split[row["name"]]
        rev_rows.append(
            [
                label[row["name"]],
                meur(cdep, 1),
                meur(row["deposit"], 2),
                meur(cfx, 1),
                meur(row["fx"], 2),
                meur(cmod, 1),
                meur(row["module"], 2),
                meur(ctot, 1),
                meur(row["total"], 2),
            ]
        )

    sentinel_rows = [
        [
            f"<code>{r['product_id']}</code>",
            f"<code>{r['company_id']}</code>",
            r["type"],
            r["currency"],
            compact(r["balance"]),
            compact(r["eur"]),
        ]
        for r in d["sentinels"]
    ]
    fx_rows = [
        [
            r["currency"],
            fmt(r["units_per_eur"], 2),
            fmt(r["n_obs"] or 0, 0),
            '<span class="ok">suficiente</span>'
            if (r["n_obs"] or 0) >= 50
            else '<span class="bad">frágil</span>',
        ]
        for r in d["fx"]
    ]
    diag_rows = [
        [r["diagnosis"], fmt(r["n"], 0), meur(r["cash_m"], 1), money(r["med_cash"])]
        for r in d["diagnosis"]
    ]
    group_rows = [
        [
            f"<code>{r['group_id']}</code>",
            fmt(r["n_cos"], 0),
            fmt(r["surplus_n"], 0),
            fmt(r["deficit_n"], 0),
            meur(r["excess_m"], 2),
        ]
        for r in d["group_excess"]
    ]
    erp_rows = [
        [r["erp"], fmt(r["n"], 0), fmt(r["surplus_n"], 0), meur(r["excess_m"], 2)]
        for r in d["erp_surplus"][:10]
    ]

    top3_excess = sum(r["excess_m"] or 0 for r in d["group_excess"][:3])
    top3_share = 100 * top3_excess / d["excess_m"] if d["excess_m"] else 0
    cash_opex, cash_hist, excess_opex = d["corr"]

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>X-Ray · Monetización medida sobre la cartera</title>
  <style>{CSS}</style>
  <script>{get_plotlyjs()}</script>
</head>
<body>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">€</span><div><b>X-Ray</b><small>Monetización</small></div></div>
    <nav>
      <a href="#resumen">01 · Qué sobrevive</a>
      <a href="#metodo">02 · Método</a>
      <a href="#replica">03 · Réplica del brief</a>
      <a href="#caja">04 · Caja ociosa</a>
      <a href="#excedente">05 · Excedente real</a>
      <a href="#divisa">06 · Divisa</a>
      <a href="#financiacion">07 · Financiación</a>
      <a href="#ingreso">08 · Ingreso</a>
      <a href="#outliers">09 · Centinelas</a>
      <a href="#conclusiones">10 · Pitch</a>
    </nav>
    <div class="side-note">Artefacto autónomo<br>Capa de mapeo + caja reconstruida<br>Corte {AS_OF}</div>
  </aside>
  <main>
    <section class="hero" id="resumen">
      <div class="eyebrow">EMBAT X-RAY · FILA DEL CFO, MEDIDA</div>
      <h1>Los 12,1 M€<br><em>bajan a {fmt(central['total'], 1)} M€</em><br>cuando se convierte la divisa.</h1>
      <p>El brief de <code>context/monetizacion.md</code> acierta el diagnóstico —ocho cuentas de ahorro, la caja ociosa existe, el crédito es la cola pequeña— y se equivoca en la unidad. Suma importes en crudo y deja pasar 16 centinelas de más de 100 M€. Con EUR y la caja reconstruida, el producto sigue en pie; el mix cambia.</p>
      <div class="hero-meta">
        <span>Generado {datetime.now():%Y-%m-%d %H:%M}</span>
        <span>24 meses · {WINDOW_START} → {WINDOW_END}</span>
        <span>{fmt(N_COMPANIES, 0)} empresas</span>
      </div>
    </section>

    <section class="section">
      <div class="kpis">
        <div class="kpi"><small>Ingreso central corregido</small><strong>{fmt(central['total'], 1)} M€</strong><span>banda {fmt(low['total'], 1)} – {fmt(high['total'], 1)}</span></div>
        <div class="kpi"><small>Excedente real</small><strong>{fmt(d['excess_m'], 0)} M€</strong><span>{fmt(d['surplus_n'], 0)} empresas · mediana {compact(d['excess_median'])}</span></div>
        <div class="kpi"><small>Divisa anual, en EUR</small><strong>{fmt(d['fx_eur_annual_m'], 0)} M€</strong><span>{pct(d['fx_eur_pct'])} del flujo · brief {pct(CLAIMED['fx_pct'])}</span></div>
        <div class="kpi"><small>Agujero de caja ahora</small><strong>{fmt(d['hole_now_m'], 1)} M€</strong><span>{fmt(d['deficit_now_n'], 0)} empresas · {fmt(d['deficit_ever_n'], 0)} la tocaron</span></div>
      </div>
      <div class="callout insight"><b>La tesis no se cae; se reordena.</b> El módulo (350 €/mes) pasa a ser la línea grande porque no depende de sumar yenes con pesos. El excedente sigue existiendo —{fmt(d['surplus_n'], 0)} empresas por encima de dos meses de gasto— pero vale {fmt(d['excess_m'], 0)} M€, no {fmt(CLAIMED['excess_m'], 0)}. La financiación sigue siendo la cola: {fmt(d['hole_now_m'], 1)} M€ de agujero frente a {fmt(d['excess_m'], 0)} M€ de excedente.</div>
      <div class="grid two">
        <div class="panel">{charts['revenue']}</div>
        <div class="panel">{charts['mix']}</div>
      </div>
    </section>

    <section class="section" id="metodo">
      <div class="section-head"><span>02</span><div><h2>Cómo se ha medido</h2><p>Mismas colas que el brief, unidad distinta.</p></div></div>
      <div class="grid three">
        <article class="panel narrative"><h3>Qué replica el brief</h3>
          <ul>
            <li>Suma de <code>|amount|</code> en 24 meses, anualizada ÷ 2.</li>
            <li>Divisa = moneda del producto ≠ moneda de la empresa.</li>
            <li>Corriente ociosa frente a <code>saving</code> + <code>investment</code>.</li>
            <li>Colchón = dos meses de gasto. Adopción 25 / 35 / 45 %, 100 pb de depósito, 15 pb de divisa, 350 €/mes el módulo.</li>
          </ul>
        </article>
        <article class="panel narrative"><h3>Qué se corrige</h3>
          <ul>
            <li>Cada importe se divide por <code>units_per_eur</code> (mediana de <code>exchange_rate</code> ≠ 1).</li>
            <li>Se apartan movimientos y saldos con |EUR| ≥ 100 M: no son caja de pyme.</li>
            <li>El excedente se calcula sobre la <b>caja reconstruida</b> (checking + saving + wallet), no sobre la foto cruda.</li>
            <li>Las series con deriva (<code>has_drift</code>) salen de los agregados de cola.</li>
          </ul>
        </article>
        <article class="panel narrative"><h3>Qué no se inventa</h3>
          <ul>
            <li>La adopción, el margen y el precio del módulo son supuestos del brief. Aquí no se tocan.</li>
            <li>Pagos internacionales y originación (212 k€ y 105 k€) son residuales: no merecen un recálculo.</li>
            <li>Los 313 «que tocan déficit» del brief no salen de ninguna cola limpia. Se reportan las que sí: {fmt(d['deficit_now_n'], 0)} ahora, {fmt(d['deficit_ever_n'], 0)} en algún mes.</li>
          </ul>
        </article>
      </div>
    </section>

    <section class="section" id="replica">
      <div class="section-head"><span>03</span><div><h2>Réplica: qué números del brief son ciertos</h2><p>Columna «crudo» = su método. Columna «corregido» = EUR + centinelas + caja reconstruida.</p></div></div>
      {table(
          ["Base", "Brief", "Réplica cruda", "Corregido", "Δ vs brief"],
          compare_rows,
      )}
      <div class="callout"><b>Reproducible al céntimo.</b> Corriente 8.057 M€ = saldo positivo de <code>checking</code> menos el único producto de 99.999 M€ (<code>PRODUCT_00001</code>). Inversión 242 M€ y 147 cuentas en positivo: exacto. Ahorro: 8 cuentas con saldo &gt; 0 (hay 10 productos; dos están a cero). Flujo 275.160 M€ = suma de |importe| de todo el fichero ÷ 2. Ratio 24,8× = corriente / (inversión + ahorro).</div>
      <div class="callout warning"><b>No reproducible.</b> Las 313 empresas en demanda de financiación y los 19,2 M€ anualizados no salen ni de la foto, ni de la caja reconstruida, ni del vencido ERP (AR abierto ≈ 18.800 M€, otra escala). El brief suma 313 + 375 = 688; aquí las dos colas limpias son {fmt(d['deficit_now_n'], 0)} + {fmt(d['surplus_n'], 0)} = {fmt(d['deficit_now_n'] + d['surplus_n'], 0)}.</div>
    </section>

    <section class="section" id="caja">
      <div class="section-head"><span>04</span><div><h2>La caja que no se mueve</h2><p>El brief mira el extremo contrario a la criticidad de scoring.md. Eso se sostiene; el saldo de 8.057 M€ no.</p></div></div>
      <div class="panel">{charts['snap']}</div>
      <div class="grid two">
        <div class="panel narrative">
          <h3>Qué queda en corriente</h3>
          <p>Quitar un centinela de 100.000 M€ deja 8.057 M€. Quitar los otros dieciséis de más de 100 M€ deja <b>{meur(d['eur_checking_m'], 0)}</b> en EUR. La foto sigue siendo desequilibrada: {fmt(d['claimed_saving_n'], 0)} cuentas de ahorro remuneradas frente a {fmt(d['claimed_checking_n'], 0)} corrientes. El ratio ocioso/remunerado pasa de 24,8× a <b>{d['eur_idle_ratio']:.1f}×</b> porque la corriente se desinfla más que el ahorro.</p>
        </div>
        <div class="panel narrative">
          <h3>Por qué el brief se veía redondo</h3>
          <p>Los 16 centinelas restantes suman miles de millones en la foto cruda. Un prestamista no prestaría sobre <code>PRODUCT_00001</code>; tampoco debería vender un barrido de excedentes sobre él. La capa de mapeo ya los marca (<code>dq_balance_suspect</code>). El producto de excedente tiene que heredar ese filtro.</p>
        </div>
      </div>
    </section>

    <section class="section" id="excedente">
      <div class="section-head"><span>05</span><div><h2>Excedente de verdad: por encima de dos meses de gasto</h2><p>Caja reconstruida al corte, gasto = outflow mediano de la empresa, series con deriva fuera.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Empresas en el panel</small><strong>{fmt(d['n_panel'], 0)}</strong><span>{fmt(d['n_reliable'], 0)} sin deriva</span></div>
        <div class="kpi"><small>Con excedente</small><strong>{fmt(d['surplus_n'], 0)}</strong><span>mediana {compact(d['excess_median'])}</span></div>
        <div class="kpi"><small>Colchón fino (0–2 meses)</small><strong>{fmt(d['thin_n'], 0)}</strong><span>ni cola ni agujero</span></div>
        <div class="kpi"><small>P90 del excedente</small><strong>{compact(d['excess_p90'])}</strong><span>la cola es ancha</span></div>
      </div>
      <div class="grid two">
        <div class="panel">{charts['excess_hist']}</div>
        <div class="panel">{charts['scatter']}</div>
      </div>
      <div class="panel">{charts['tails']}</div>
      <div class="callout"><b>Correlación.</b> Caja frente a gasto mensual: r = {cash_opex:.2f}. Excedente frente a gasto: r = {excess_opex:.2f}. Las empresas grandes no son automáticamente las ociosas; el colchón de dos meses ya escala con el tamaño. Historia observada vs caja: r = {cash_hist:.2f} — cobertura, no salud.</div>
      <div class="grid two">
        <div class="panel">
          <h3>Concentración por grupo</h3>
          {charts['groups']}
          <p class="caption">Los tres grupos de más excedente concentran {pct(top3_share)} del total. El split de validación tiene que ser por <code>group_id</code> también aquí: un solo holding no puede inflar el caso de negocio.</p>
        </div>
        <div class="panel">
          <h3>Top grupos</h3>
          {table(["Grupo", "Empresas", "Excedente", "Déficit", "M€"], group_rows)}
        </div>
      </div>
      <div class="panel">
        <h3>ERP: más cobertura, no más excedente automático</h3>
        {table(["ERP", "Empresas", "Con excedente", "Excedente M€"], erp_rows)}
      </div>
    </section>

    <section class="section" id="divisa">
      <div class="section-head"><span>06</span><div><h2>La divisa pesa menos de lo que el crudo promete</h2><p>Sumar CLP, ARS y JPY como si fueran euros multiplica el flujo por diez.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Flujo 24 m crudo</small><strong>{fmt(d['flow_raw_24_m'], 0)} M</strong><span>anualizado {fmt(d['flow_raw_annual_m'], 0)} M</span></div>
        <div class="kpi"><small>Flujo 24 m en EUR</small><strong>{fmt(d['flow_eur_24_m'], 0)} M€</strong><span>anualizado {fmt(d['flow_eur_annual_m'], 0)} M€</span></div>
        <div class="kpi"><small>Divisa cruda anual</small><strong>{fmt(d['fx_raw_annual_m'], 0)} M</strong><span>{pct(d['fx_raw_pct'])} · brief 7,2 %</span></div>
        <div class="kpi"><small>Divisa EUR anual</small><strong>{fmt(d['fx_eur_annual_m'], 0)} M€</strong><span>{pct(d['fx_eur_pct'])} del flujo limpio</span></div>
      </div>
      <div class="panel">{charts['fx']}</div>
      <div class="grid two">
        <div class="panel">
          <h3>Tipos usados (mediana de exchange_rate ≠ 1)</h3>
          {table(["Divisa", "Unidades / EUR", "Obs.", "Calidad"], fx_rows)}
        </div>
        <div class="panel narrative">
          <h3>Por qué el 7,2 % engaña</h3>
          <p>El porcentaje crudo es cierto como <em>fracción de filas-importe nativo</em>. Un peso argentino y un euro entran al numerador con la misma unidad. Convertido, la exposición real es el {pct(d['fx_eur_pct'])} de un flujo anual de {meur(d['flow_eur_annual_m'], 0)}, no el 7,2 % de 275.160 M€.</p>
          <p>El producto de anticipar la divisa sigue existiendo: {fmt(d['n_fx'], 0)} movimientos cruzan moneda. Cambia el notional sobre el que se cobran 15 pb.</p>
        </div>
      </div>
    </section>

    <section class="section" id="financiacion">
      <div class="section-head"><span>07</span><div><h2>La conversación incómoda, ahora con el agujero medido</h2><p>El brief decía 105 k€ de originación sobre 19,2 M€ de demanda. La demanda limpia es más pequeña, no más grande.</p></div></div>
      {table(
          ["Diagnóstico al corte", "Empresas", "Caja neta", "Caja mediana"],
          diag_rows,
      )}
      <div class="callout warning"><b>No liderar el bloque de Valor con un marketplace de crédito.</b> Hoy hay {fmt(d['deficit_now_n'], 0)} empresas con caja reconstruida negativa ({meur(d['hole_now_m'], 2)} de agujero) y {fmt(d['deficit_ever_n'], 0)} que la tocaron en algún mes. Frente a {fmt(d['surplus_n'], 0)} con excedente de {meur(d['excess_m'], 0)}. El score del prestamista no cambia; el producto que se enseña primero, sí.</div>
    </section>

    <section class="section" id="ingreso">
      <div class="section-head"><span>08</span><div><h2>Ingreso: mismas hipótesis, bases nuevas</h2><p>25 / 35 / 45 % de adopción, 100 pb, 15 pb, 350 €/mes. No se ha tocado el pricing.</p></div></div>
      {table(
          ["Escenario", "Depósito brief", "Depósito corr.", "Divisa brief", "Divisa corr.", "Módulo brief", "Módulo corr.", "Total brief", "Total corr."],
          rev_rows,
      )}
      <div class="grid two">
        <div class="panel narrative">
          <h3>Sobre 1.286 empresas</h3>
          <p>Central corregido: <b>{meur(central['total'], 2)}/año</b> ({money(1e6 * central['total'] / N_COMPANIES)} por empresa). El módulo aporta {meur(central['module'], 2)}, el excedente {meur(central['deposit'], 2)}, la divisa {meur(central['fx'], 2)}.</p>
        </div>
        <div class="panel narrative">
          <h3>Sobre 400 clientes de Embat</h3>
          <p>El brief argumentaba que el 76 % del ingreso iba con el flujo, no con las cabezas. Con bases limpias el módulo pesa más, así que recortar a 400 clientes duele: central ≈ <b>{meur(central400['total'], 2)}</b>. Sigue siendo expansión sobre instalada, no captación.</p>
        </div>
      </div>
      <div class="callout"><b>El cliente sigue ganando.</b> Una empresa con el excedente mediano corregido ({money(d['excess_median'])}) coloca al 2–3 % y paga 100 pb. Neto +1.200 a +2.400 €/año sobre ~{money(d['excess_median'] * DEPOSIT_BPS)} de margen. La objeción de precio no aparece. Lo que desaparece es vender 2.378 M€ de notional que no están.</div>
    </section>

    <section class="section" id="outliers">
      <div class="section-head"><span>09</span><div><h2>Los 17 saldos que no se prestan ni se barren</h2><p>Umbral |EUR| ≥ 100 M, el mismo que <code>cash_history.py</code>.</p></div></div>
      {table(
          ["Producto", "Empresa", "Tipo", "Divisa", "Saldo nativo", "EUR"],
          sentinel_rows,
      )}
      <div class="callout warning"><b>PRODUCT_00001 = 99.999.990.850.</b> Es el único que el brief restó. Los otros dieciséis —tres de ellos negativos en −1.000 M— siguen dentro de los 8.057 M€. Cualquier agregación de tesorería que no herede <code>dq_balance_suspect</code> vuelve a inflar el pitch.</div>
    </section>

    <section class="section conclusions" id="conclusiones">
      <div class="section-head"><span>10</span><div><h2>Qué decir delante del jurado</h2><p>El colchón dinámico se sostiene. La cifra de 12,1 M€ no.</p></div></div>
      <div class="conclusion-list">
        <article><span>01</span><div><h3>Abrir con el producto, no con el 12,1</h3><p>Cada mes la caja se parte en lo que va a hacer falta y lo que no. Lo primero se queda. Lo segundo trabaja. Si sale negativo, se avisa con meses. Eso responde al titular del reto y no depende de sumar pesos con euros.</p></div></article>
        <article><span>02</span><div><h3>Citar las colas limpias</h3><p>{fmt(d['surplus_n'], 0)} empresas con excedente de {meur(d['excess_m'], 0)} (mediana {money(d['excess_median'])}). {fmt(d['deficit_now_n'], 0)} con caja negativa ahora ({meur(d['hole_now_m'], 2)}). Ocho cuentas de ahorro con saldo. El crédito no lidera el bloque de Valor.</p></div></article>
        <article><span>03</span><div><h3>Si preguntan por el ingreso</h3><p>Con las hipótesis del brief y las bases convertidas: {meur(low['total'], 1)} – {meur(central['total'], 1)} – {meur(high['total'], 1)} /año sobre esta cartera. El módulo es la línea más robusta; excedente y divisa siguen, más pequeños.</p></div></article>
        <article><span>04</span><div><h3>No cambiar el score</h3><p>La criticidad de la caja que se evapora sigue mandando. Esto es la otra cola de la misma señal, leída para el CFO. El prestamista de 100.000 € no se toca.</p></div></article>
      </div>
      <div class="final-note">Reproducible con <code>python analysis/monetizacion.py</code>. Usa <code>src/mapping</code> y, si existe, <code>analysis/cash.duckdb</code>. Marco: <code>context/monetizacion.md</code> y <code>context/scoring.md</code>. Los CSV de <code>data/</code> no se reescriben.</div>
    </section>
    <footer>HackSpain 2026 · X-Ray · Monetización medida · {datetime.now():%Y-%m-%d}</footer>
  </main>
</body>
</html>"""


def main() -> None:
    connection = connect()
    data = collect(connection)
    charts = build_charts(data)
    OUTPUT.write_text(build_html(data, charts), encoding="utf-8")
    print(
        f"Escrito {OUTPUT.relative_to(ROOT)} "
        f"({OUTPUT.stat().st_size / 1_000_000:.1f} MB) · "
        f"excedente {data['excess_m']:.1f} M€ · "
        f"divisa anual {data['fx_eur_annual_m']:.1f} M€ · "
        f"central {next(r['total'] for r in revenue_rows(data['excess_m'], data['fx_eur_annual_m'], N_COMPANIES)):.2f} M€"
    )


if __name__ == "__main__":
    main()
