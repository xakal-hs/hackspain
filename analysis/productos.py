#!/usr/bin/env python3
"""Prioridad de los 5 SKUs de la SPA: bases medidas, take incremental, HTML autónomo.

Reproduce el análisis de ``notebooks/02_productos.ipynb`` y escribe
``analysis/productos.html``. Netea excedente y agujero a nivel de grupo:
el CFO mueve capital entre filiales antes de barrer o pedir crédito.
No reescribe CSVs ni el pitch de monetización.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis" / "productos.html"
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
    table,
)
from monetizacion import (  # noqa: E402
    ADOPTION,
    ARTIFACT_EUR,
    AS_OF,
    DEPOSIT_BPS,
    FX_BPS,
    WINDOW_END,
    WINDOW_START,
    connect,
    meur,
    money,
    pct,
)

YIELD_BPS = DEPOSIT_BPS
RESERVE_BPS = 0.005
FACTORING_BPS = 0.015
INSURANCE_PREM = 0.005
INSURANCE_REFERRAL = 0.20
CAP = ARTIFACT_EUR
INFLOW_START = "2025-09-01"
INFLOW_END = "2026-08-01"


def setup_need(connection) -> None:
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE fx_co AS
        WITH prod AS (
            SELECT product_id, currency FROM banking_products
            UNION ALL
            SELECT product_id, currency FROM debt_products
        )
        SELECT t.company_id,
               coalesce(sum(abs(t.amount) / coalesce(f.units_per_eur, 1)) FILTER (
                   WHERE p.currency IS NOT NULL AND p.currency <> c.currency
                     AND abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
                     AND f.currency IS NOT NULL
               ), 0) / 2 AS fx_annual_eur,
               count(*) FILTER (
                   WHERE p.currency IS NOT NULL AND p.currency <> c.currency
                     AND abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
                     AND f.currency IS NOT NULL
               ) AS n_fx
        FROM transactions t
        JOIN companies c USING (company_id)
        LEFT JOIN prod p ON p.product_id = t.product_id
        LEFT JOIN cash.fx f ON f.currency = coalesce(p.currency, c.currency)
        WHERE t.date >= DATE '{WINDOW_START}' AND t.date < DATE '{WINDOW_END}'
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE ar_co AS
        SELECT i.company_id,
               coalesce(sum(greatest(i.pending_amount, 0) / coalesce(f.units_per_eur, 1)) FILTER (
                   WHERE i.amount > 0
                     AND i.pending_amount > 0
                     AND i.status NOT IN ('paid', 'cancelled')
                     AND i.document_type IN ('invoice', 'invoiceGroup')
                     AND i.due_date < DATE '{AS_OF}'
                     AND abs(i.pending_amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
               ), 0) AS overdue_ar_eur,
               count(*) FILTER (
                   WHERE i.amount > 0
                     AND i.document_type IN ('invoice', 'invoiceGroup')
                     AND i.due_date < DATE '{AS_OF}'
                     AND i.due_date >= DATE '2015-01-01'
                     AND i.status <> 'cancelled'
               ) AS n_ar_due,
               count(*) FILTER (
                   WHERE i.amount > 0
                     AND i.pending_amount > 0
                     AND i.status NOT IN ('paid', 'cancelled')
                     AND i.document_type IN ('invoice', 'invoiceGroup')
                     AND i.due_date < DATE '{AS_OF}'
                     AND abs(i.pending_amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
               ) AS n_ar_overdue
        FROM invoices i
        LEFT JOIN cash.fx f ON f.currency = coalesce(i.currency, 'EUR')
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE inflow12 AS
        SELECT company_id, sum(inflow_eur) AS inflow_12m_eur
        FROM cash.cash_metrics
        WHERE month_start >= DATE '{INFLOW_START}' AND month_start <= DATE '{INFLOW_END}'
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE debt_flags AS
        SELECT company_id,
               bool_or(type = 'factoring') AS has_factoring,
               bool_or(type = 'lineofcredit') AS has_line,
               bool_or(type = 'confirming') AS has_confirming
        FROM debt_products
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE saving_flags AS
        SELECT DISTINCT company_id, TRUE AS has_saving
        FROM banking_products WHERE type = 'saving'
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE need AS
        SELECT
            c.company_id,
            c.group_id,
            coalesce(c.has_invoices, FALSE) AS has_invoices,
            s.company_id IS NOT NULL AS has_cash,
            coalesce(s.has_drift, TRUE) AS has_drift,
            s.cash_eur,
            s.median_outflow,
            s.coverage,
            s.diagnosis,
            coalesce(fx.fx_annual_eur, 0) AS fx_annual_eur,
            coalesce(ar.overdue_ar_eur, 0) AS overdue_ar_eur,
            CASE WHEN ar.n_ar_due > 0 THEN ar.n_ar_overdue::DOUBLE / ar.n_ar_due ELSE 0 END AS late_share_ar,
            coalesce(inf.inflow_12m_eur, 0) AS inflow_12m_eur,
            coalesce(d.has_factoring, FALSE) AS has_factoring,
            coalesce(d.has_line, FALSE) AS has_line,
            coalesce(d.has_confirming, FALSE) AS has_confirming,
            coalesce(sv.has_saving, FALSE) AS has_saving,
            coalesce(s.company_id IS NOT NULL AND NOT s.has_drift
                     AND s.median_outflow > 0 AND s.cash_eur > 2 * s.median_outflow, FALSE) AS elig_yield,
            CASE WHEN s.median_outflow > 0 AND NOT s.has_drift
                 THEN greatest(s.cash_eur - 2 * s.median_outflow, 0) ELSE 0 END AS excess_eur,
            coalesce(fx.fx_annual_eur, 0) > 0 AS elig_fx,
            coalesce(s.company_id IS NOT NULL AND NOT s.has_drift AND (
                         s.cash_eur < 0 OR s.coverage < 6
                         OR s.diagnosis IN ('caja negativa', 'colchón crítico', 'deterioro estructural')
                     ), FALSE) AS elig_reserve_broad,
            coalesce(s.company_id IS NOT NULL AND NOT s.has_drift
                     AND NOT (s.median_outflow > 0 AND s.cash_eur > 2 * s.median_outflow)
                     AND (s.cash_eur < 0 OR s.coverage < 2
                          OR s.diagnosis IN ('caja negativa', 'colchón crítico', 'deterioro estructural')),
                     FALSE) AS elig_reserve,
            CASE WHEN s.median_outflow > 0
                 THEN s.median_outflow * least(greatest(6 - coalesce(s.coverage, 6), 0.5), 6) * 0.5
                 ELSE 0 END AS linea_eur,
            coalesce(c.has_invoices AND coalesce(ar.overdue_ar_eur, 0) > 50000, FALSE) AS elig_factoring,
            coalesce(c.has_invoices AND (
                         (CASE WHEN ar.n_ar_due > 0 THEN ar.n_ar_overdue::DOUBLE / ar.n_ar_due ELSE 0 END) > 0.15
                         OR coalesce(ar.overdue_ar_eur, 0) > 200000
                     ), FALSE) AS elig_credit
        FROM companies c
        LEFT JOIN cash.cash_summary s USING (company_id)
        LEFT JOIN fx_co fx USING (company_id)
        LEFT JOIN ar_co ar USING (company_id)
        LEFT JOIN inflow12 inf USING (company_id)
        LEFT JOIN debt_flags d USING (company_id)
        LEFT JOIN saving_flags sv USING (company_id)
        """
    )
    # Tesorería de grupo: el excedente de una filial cubre el agujero de otra
    # antes de barrer o pedir crédito. FX no se netea (es flujo, no saldo).
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE gnet AS
        SELECT
            group_id,
            count(*) AS n_cos,
            count(*) FILTER (WHERE elig_yield) AS n_surplus,
            count(*) FILTER (WHERE NOT has_drift AND cash_eur < 0) AS n_hole,
            coalesce(sum(excess_eur) FILTER (WHERE elig_yield), 0) AS excess_pool,
            coalesce(-sum(cash_eur) FILTER (WHERE NOT has_drift AND cash_eur < 0), 0) AS hole_pool,
            coalesce(sum(overdue_ar_eur) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND elig_factoring
            ), 0) AS ar_of_holes
        FROM need
        GROUP BY 1
        """
    )


def collect(connection) -> dict:
    d: dict = {}
    uni = connection.execute(
        """
        SELECT
          (SELECT count(*) FROM companies) AS n_companies,
          (SELECT count(*) FROM cash.cash_summary) AS n_panel,
          (SELECT count(*) FROM cash.cash_summary WHERE NOT has_drift) AS n_reliable,
          (SELECT count(*) FROM cash.cash_summary WHERE has_drift) AS n_drift,
          (SELECT count(*) FROM companies WHERE has_invoices) AS n_erp,
          (SELECT count(*) FROM companies WHERE NOT has_invoices) AS n_no_erp
        """
    ).fetchone()
    d.update(
        dict(
            zip(
                ("n_companies", "n_panel", "n_reliable", "n_drift", "n_erp", "n_no_erp"),
                uni,
            )
        )
    )
    d["diagnosis"] = records(
        connection,
        """
        SELECT diagnosis, count(*) AS n,
               count(*) FILTER (WHERE NOT has_drift) AS n_fiables
        FROM cash.cash_summary GROUP BY 1 ORDER BY n DESC
        """,
    )
    d["debt"] = records(
        connection,
        """
        SELECT type, count(*) AS n_productos, count(DISTINCT company_id) AS n_empresas
        FROM debt_products GROUP BY 1 ORDER BY n_empresas DESC
        """,
    )
    d["saving_n"] = connection.execute(
        "SELECT count(DISTINCT company_id) FROM banking_products WHERE type = 'saving'"
    ).fetchone()[0]

    cores = connection.execute(
        f"""
        SELECT
            count(*) FILTER (WHERE elig_yield) AS yield_n,
            sum(excess_eur) FILTER (WHERE elig_yield) AS yield_notional,
            median(excess_eur) FILTER (WHERE elig_yield) AS yield_med,
            quantile_cont(excess_eur, 0.9) FILTER (WHERE elig_yield) AS yield_p90,
            count(*) FILTER (WHERE elig_yield AND NOT has_saving) AS yield_white,
            count(*) FILTER (WHERE elig_fx) AS fx_n,
            sum(fx_annual_eur) FILTER (WHERE elig_fx) AS fx_notional,
            median(fx_annual_eur) FILTER (WHERE elig_fx) AS fx_med,
            quantile_cont(fx_annual_eur, 0.9) FILTER (WHERE elig_fx) AS fx_p90,
            count(*) FILTER (WHERE fx_annual_eur > 1e5) AS fx_n_100k,
            count(*) FILTER (WHERE elig_reserve) AS reserve_n,
            count(*) FILTER (WHERE elig_reserve_broad) AS reserve_broad_n,
            sum(linea_eur) FILTER (WHERE elig_reserve) AS linea_raw,
            sum(least(linea_eur, {CAP})) FILTER (WHERE elig_reserve) AS linea_cap,
            count(*) FILTER (WHERE elig_reserve AND has_line) AS reserve_has_line,
            count(*) FILTER (WHERE elig_reserve AND NOT has_line) AS reserve_originate,
            count(*) FILTER (WHERE NOT has_drift AND cash_eur < 0) AS hole_n,
            -sum(cash_eur) FILTER (WHERE NOT has_drift AND cash_eur < 0) AS hole_notional,
            count(*) FILTER (WHERE NOT has_drift AND cash_eur < 0 AND NOT has_line) AS hole_no_line,
            count(*) FILTER (WHERE elig_factoring) AS factoring_n,
            sum(overdue_ar_eur) FILTER (WHERE elig_factoring) AS factoring_notional,
            median(overdue_ar_eur) FILTER (WHERE elig_factoring) AS factoring_med,
            quantile_cont(overdue_ar_eur, 0.9) FILTER (WHERE elig_factoring) AS factoring_p90,
            count(*) FILTER (WHERE elig_factoring AND NOT has_factoring) AS factoring_white,
            count(*) FILTER (WHERE elig_credit) AS credit_n,
            sum(inflow_12m_eur * {INSURANCE_PREM} * late_share_ar)
                FILTER (WHERE elig_credit) AS premium_raw,
            sum(least(inflow_12m_eur, {CAP}) * {INSURANCE_PREM} * late_share_ar)
                FILTER (WHERE elig_credit) AS premium_cap,
            median(late_share_ar) FILTER (WHERE elig_credit) AS credit_late_med,
            count(*) FILTER (WHERE elig_credit AND elig_factoring) AS credit_x_factoring,
            count(*) FILTER (WHERE elig_credit AND NOT elig_factoring) AS credit_residual_n,
            count(*) FILTER (WHERE elig_yield AND elig_fx) AS yield_x_fx,
            count(*) FILTER (WHERE elig_yield AND elig_factoring) AS yield_x_fac
        FROM need
        """
    ).fetchone()
    keys = (
        "yield_n",
        "yield_notional",
        "yield_med",
        "yield_p90",
        "yield_white",
        "fx_n",
        "fx_notional",
        "fx_med",
        "fx_p90",
        "fx_n_100k",
        "reserve_n",
        "reserve_broad_n",
        "linea_raw",
        "linea_cap",
        "reserve_has_line",
        "reserve_originate",
        "hole_n",
        "hole_notional",
        "hole_no_line",
        "factoring_n",
        "factoring_notional",
        "factoring_med",
        "factoring_p90",
        "factoring_white",
        "credit_n",
        "premium_raw",
        "premium_cap",
        "credit_late_med",
        "credit_x_factoring",
        "credit_residual_n",
        "yield_x_fx",
        "yield_x_fac",
    )
    d.update(dict(zip(keys, cores)))

    d["yield_take_35"] = d["yield_notional"] * YIELD_BPS * 0.35
    d["fx_take_35"] = d["fx_notional"] * FX_BPS * 0.35
    d["factoring_take_35"] = d["factoring_notional"] * FACTORING_BPS * 0.35
    d["credit_take_raw_35"] = d["premium_raw"] * INSURANCE_REFERRAL * 0.35
    d["credit_take_cap_35"] = d["premium_cap"] * INSURANCE_REFERRAL * 0.35
    d["reserve_take_raw_35"] = d["linea_raw"] * RESERVE_BPS * 0.35
    d["reserve_take_cap_35"] = d["linea_cap"] * RESERVE_BPS * 0.35
    d["hole_take_35"] = d["hole_notional"] * RESERVE_BPS * 0.35
    d["renta_35"] = d["yield_take_35"] + d["fx_take_35"]
    residual = connection.execute(
        f"""
        SELECT coalesce(sum(least(inflow_12m_eur, {CAP}) * {INSURANCE_PREM} * late_share_ar), 0)
        FROM need WHERE elig_credit AND NOT elig_factoring
        """
    ).fetchone()[0]
    d["credit_residual_take_35"] = residual * INSURANCE_REFERRAL * 0.35

    d["yield_hist"] = records(
        connection,
        """
        SELECT CASE
                 WHEN excess_eur < 5e4 THEN '< 50 k€'
                 WHEN excess_eur < 1e5 THEN '50–100 k€'
                 WHEN excess_eur < 2.5e5 THEN '100–250 k€'
                 WHEN excess_eur < 1e6 THEN '250 k€–1 M€'
                 WHEN excess_eur < 5e6 THEN '1–5 M€'
                 ELSE '> 5 M€' END AS tramo,
               min(excess_eur) AS sort_key,
               count(*) AS n,
               sum(excess_eur) / 1e6 AS m
        FROM need WHERE elig_yield
        GROUP BY 1 ORDER BY sort_key
        """,
    )
    d["fx_hist"] = records(
        connection,
        """
        SELECT CASE
                 WHEN fx_annual_eur < 1e4 THEN '< 10 k€'
                 WHEN fx_annual_eur < 1e5 THEN '10–100 k€'
                 WHEN fx_annual_eur < 1e6 THEN '100 k€–1 M€'
                 WHEN fx_annual_eur < 1e7 THEN '1–10 M€'
                 ELSE '> 10 M€' END AS tramo,
               min(fx_annual_eur) AS sort_key,
               count(*) AS n,
               sum(fx_annual_eur) / 1e6 AS m
        FROM need WHERE elig_fx
        GROUP BY 1 ORDER BY sort_key
        """,
    )
    d["ar_hist"] = records(
        connection,
        """
        SELECT CASE
                 WHEN overdue_ar_eur < 5e4 THEN '< 50 k€'
                 WHEN overdue_ar_eur < 2e5 THEN '50–200 k€'
                 WHEN overdue_ar_eur < 1e6 THEN '200 k€–1 M€'
                 WHEN overdue_ar_eur < 5e6 THEN '1–5 M€'
                 ELSE '> 5 M€' END AS tramo,
               min(overdue_ar_eur) AS sort_key,
               count(*) AS n,
               sum(overdue_ar_eur) / 1e6 AS m
        FROM need WHERE has_invoices
        GROUP BY 1 ORDER BY sort_key
        """,
    )
    d["coverage"] = records(
        connection,
        """
        SELECT CASE
                 WHEN cash_eur < 0 THEN 'caja negativa'
                 WHEN coverage < 0.25 THEN 'colchón crítico'
                 WHEN coverage < 2 THEN 'fino 0,25–2 m'
                 WHEN coverage < 6 THEN '2–6 meses'
                 ELSE '≥ 6 meses'
               END AS tramo,
               count(*) AS n
        FROM cash.cash_summary WHERE NOT has_drift
        GROUP BY 1 ORDER BY min(coalesce(coverage, -1))
        """,
    )
    d["n_sku"] = records(
        connection,
        """
        SELECT (elig_yield::INT + elig_fx::INT + elig_reserve::INT
                + elig_factoring::INT + elig_credit::INT) AS n_sku,
               count(*) AS n
        FROM need GROUP BY 1 ORDER BY 1
        """,
    )
    flags = ["elig_yield", "elig_fx", "elig_reserve", "elig_factoring", "elig_credit"]
    labels = ["yield", "fx", "reserve", "factoring", "credit"]
    pair = []
    for flag_a, lab_a in zip(flags, labels):
        row = {"sku": lab_a}
        for flag_b, lab_b in zip(flags, labels):
            row[lab_b] = connection.execute(
                f"SELECT count(*) FROM need WHERE {flag_a} AND {flag_b}"
            ).fetchone()[0]
        pair.append(row)
    d["pair"] = pair
    d["pair_labels"] = labels

    d["reserve_outliers"] = records(
        connection,
        """
        SELECT company_id, round(median_outflow/1e6, 1) AS outflow_m,
               round(coverage, 3) AS coverage, diagnosis,
               round(linea_eur/1e6, 1) AS linea_m
        FROM need WHERE elig_reserve
        ORDER BY linea_eur DESC LIMIT 6
        """,
    )
    d["sens_yield"] = []
    for k in (1, 2, 3, 6):
        n, excess = connection.execute(
            f"""
            SELECT count(*), coalesce(sum(cash_eur - {k} * median_outflow), 0)
            FROM need
            WHERE NOT has_drift AND median_outflow > 0
              AND cash_eur > {k} * median_outflow
            """
        ).fetchone()
        d["sens_yield"].append({"k": k, "n": n, "excess_m": excess / 1e6, "take_35": excess * YIELD_BPS * 0.35 / 1e6})
    d["sens_fx"] = []
    for thr in (0, 10_000, 100_000, 1_000_000):
        n, fxn = connection.execute(
            f"""
            SELECT count(*), coalesce(sum(fx_annual_eur), 0)
            FROM need WHERE fx_annual_eur > {thr}
            """
        ).fetchone()
        d["sens_fx"].append({"thr": thr, "n": n, "fx_m": fxn / 1e6, "take_35": fxn * FX_BPS * 0.35 / 1e6})
    d["sens_fac"] = []
    for thr in (10_000, 50_000, 100_000, 200_000, 1_000_000):
        n, ar = connection.execute(
            f"""
            SELECT count(*), coalesce(sum(overdue_ar_eur), 0)
            FROM need WHERE has_invoices AND overdue_ar_eur > {thr}
            """
        ).fetchone()
        d["sens_fac"].append({"thr": thr, "n": n, "ar_m": ar / 1e6, "take_35": ar * FACTORING_BPS * 0.35 / 1e6})

    proxy = connection.execute(
        """
        WITH ntx AS (
            SELECT company_id, sum(n_tx) AS n_tx
            FROM cash.cash_metrics GROUP BY 1
        )
        SELECT
            count(*) FILTER (WHERE coalesce(n.n_tx, 0) > 50) AS proxy_spa,
            count(*) FILTER (WHERE p.elig_fx) AS fx_real,
            count(*) FILTER (WHERE coalesce(n.n_tx, 0) > 50 AND p.elig_fx) AS ambos,
            count(*) FILTER (WHERE coalesce(n.n_tx, 0) > 50 AND NOT p.elig_fx) AS proxy_sin_fx,
            count(*) FILTER (WHERE coalesce(n.n_tx, 0) <= 50 AND p.elig_fx) AS fx_sin_proxy
        FROM need p
        LEFT JOIN ntx n USING (company_id)
        """
    ).fetchone()
    d["proxy"] = dict(zip(("proxy_spa", "fx_real", "ambos", "proxy_sin_fx", "fx_sin_proxy"), proxy))

    g = connection.execute(
        """
        SELECT
            count(*) AS n_groups,
            count(*) FILTER (WHERE n_cos > 1) AS n_multi,
            count(*) FILTER (WHERE n_cos > 1 AND n_surplus > 0 AND n_hole > 0) AS n_both,
            count(*) FILTER (WHERE n_hole > 0 AND excess_pool >= hole_pool AND n_cos > 1) AS n_full,
            count(*) FILTER (WHERE n_hole > 0 AND excess_pool > 0 AND excess_pool < hole_pool) AS n_cover_part,
            count(*) FILTER (WHERE n_hole > 0 AND excess_pool = 0) AS n_no_sister,
            coalesce(sum(least(excess_pool, hole_pool)) FILTER (WHERE n_cos > 1), 0) AS moved_eur,
            coalesce(sum(excess_pool), 0) AS excess_gross,
            coalesce(sum(greatest(excess_pool - hole_pool, 0)), 0) AS excess_net,
            coalesce(sum(hole_pool), 0) AS hole_gross,
            coalesce(sum(greatest(hole_pool - excess_pool, 0)), 0) AS hole_net
        FROM gnet
        """
    ).fetchone()
    d.update(
        dict(
            zip(
                (
                    "n_groups",
                    "n_multi",
                    "n_both",
                    "n_full",
                    "n_cover_part",
                    "n_no_sister",
                    "moved_eur",
                    "excess_gross",
                    "excess_net",
                    "hole_gross",
                    "hole_net",
                ),
                g,
            )
        )
    )
    hg = connection.execute(
        """
        SELECT
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0
                  AND g.n_cos > 1 AND g.excess_pool >= g.hole_pool
            ) AS hole_full_n,
            -coalesce(sum(n.cash_eur) FILTER (
                WHERE NOT has_drift AND cash_eur < 0
                  AND g.n_cos > 1 AND g.excess_pool >= g.hole_pool
            ), 0) AS hole_full_eur,
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND g.n_cos = 1
            ) AS hole_solo_n,
            count(*) FILTER (WHERE elig_yield AND g.n_hole > 0) AS yield_sister_n,
            coalesce(sum(n.excess_eur) FILTER (WHERE elig_yield AND g.n_hole > 0), 0)
                AS yield_sister_eur,
            count(*) FILTER (
                WHERE elig_yield AND greatest(g.excess_pool - g.hole_pool, 0) > 0
            ) AS yield_n_net,
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND elig_factoring
                  AND g.n_cos > 1 AND g.excess_pool >= g.hole_pool
            ) AS fact_hole_full_n,
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND elig_factoring
                  AND g.hole_pool > g.excess_pool
            ) AS fact_hole_open_n,
            coalesce(sum(n.overdue_ar_eur) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND elig_factoring
                  AND g.hole_pool > g.excess_pool
            ), 0) AS ar_open_eur,
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND NOT has_line
                  AND g.n_cos > 1 AND g.excess_pool >= g.hole_pool
            ) AS noline_full_n,
            count(*) FILTER (
                WHERE NOT has_drift AND cash_eur < 0 AND NOT has_line
                  AND g.hole_pool > g.excess_pool
            ) AS noline_open_n,
            count(*) FILTER (
                WHERE elig_reserve AND elig_factoring AND g.n_cos > 1 AND g.n_surplus > 0
            ) AS tense_fact_sister_n
        FROM need n
        JOIN gnet g USING (group_id)
        """
    ).fetchone()
    d.update(
        dict(
            zip(
                (
                    "hole_full_n",
                    "hole_full_eur",
                    "hole_solo_n",
                    "yield_sister_n",
                    "yield_sister_eur",
                    "yield_n_net",
                    "fact_hole_full_n",
                    "fact_hole_open_n",
                    "ar_open_eur",
                    "noline_full_n",
                    "noline_open_n",
                    "tense_fact_sister_n",
                ),
                hg,
            )
        )
    )
    d["yield_take_net_35"] = d["excess_net"] * YIELD_BPS * 0.35
    d["hole_take_net_35"] = d["hole_net"] * RESERVE_BPS * 0.35
    d["renta_net_35"] = d["yield_take_net_35"] + d["fx_take_35"]
    d["mixed_groups"] = records(
        connection,
        """
        SELECT group_id, n_cos, n_surplus, n_hole,
               excess_pool / 1e6 AS excess_m,
               hole_pool / 1e6 AS hole_m,
               least(excess_pool, hole_pool) / 1e6 AS moved_m,
               CASE
                 WHEN excess_pool >= hole_pool THEN 'cubre'
                 WHEN excess_pool > 0 THEN 'cubre en parte'
                 ELSE 'sin caja hermana'
               END AS cover
        FROM gnet
        WHERE n_cos > 1 AND n_surplus > 0 AND n_hole > 0
        ORDER BY least(excess_pool, hole_pool) DESC
        """,
    )
    return d


def bar_hist(rows: list[dict], title: str, color: str, unit: str = "M€") -> str:
    fig = go.Figure(
        go.Bar(
            x=[r["tramo"] for r in rows],
            y=[r["n"] for r in rows],
            marker_color=color,
            text=[f"{r['n']} · {r['m']:.0f} {unit}" for r in rows],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{x}: %{y} empresas<extra></extra>",
        )
    )
    fig.update_layout(title=title, yaxis_title="Empresas", xaxis_title="")
    return chart_html(fig, 360)


def build_charts(d: dict) -> dict[str, str]:
    charts = {}
    charts["yield"] = bar_hist(
        d["yield_hist"], "Yield: empresas y notional por tramo de excedente", COLORS["blue"]
    )
    charts["fx"] = bar_hist(
        d["fx_hist"], "FX: empresas y notional anual por tramo", COLORS["cyan"]
    )
    charts["ar"] = bar_hist(
        d["ar_hist"], "AR vencido en empresas con ERP (umbral factoring = 50 k€)", COLORS["amber"]
    )

    fig = go.Figure(
        go.Bar(
            x=[r["tramo"] for r in d["coverage"]],
            y=[r["n"] for r in d["coverage"]],
            marker_color=COLORS["slate"],
            text=[r["n"] for r in d["coverage"]],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(title="Cobertura de caja (meses de gasto) · series fiables", yaxis_title="Empresas")
    charts["coverage"] = chart_html(fig, 320)

    labels = d["pair_labels"]
    z = [[row[lab] for lab in labels] for row in d["pair"]]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=labels,
            y=labels,
            colorscale=[[0, "#e8eef6"], [1, COLORS["blue"]]],
            text=z,
            texttemplate="%{text}",
            hovertemplate="%{y} ∩ %{x}: %{z}<extra></extra>",
        )
    )
    fig.update_layout(title="Co-elegibilidad (reserve estrecha; yield ∩ reserve = 0)")
    charts["overlap"] = chart_html(fig, 380)

    fig = go.Figure(
        go.Bar(
            x=[r["n_sku"] for r in d["n_sku"]],
            y=[r["n"] for r in d["n_sku"]],
            marker_color=COLORS["navy"],
            text=[r["n"] for r in d["n_sku"]],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(title="¿A cuántos SKUs es elegible cada empresa?", xaxis_title="SKUs", yaxis_title="Empresas")
    charts["nsku"] = chart_html(fig, 300)

    wf_x = ["Yield<br>tras grupo", "FX", "Factoring<br>(one-shot)", "Seguro<br>residual", "Agujero<br>neto"]
    wf_y = [
        d["yield_take_net_35"] / 1e6,
        d["fx_take_35"] / 1e6,
        d["factoring_take_35"] / 1e6,
        d["credit_residual_take_35"] / 1e6,
        d["hole_take_net_35"] / 1e6,
    ]
    fig = go.Figure(
        go.Waterfall(
            x=wf_x,
            y=wf_y,
            measure=["relative"] * 5,
            text=[f"{v:.2f}" for v in wf_y],
            textposition="outside",
            connector={"line": {"color": COLORS["slate"]}},
            increasing={"marker": {"color": COLORS["blue"]}},
            totals={"marker": {"color": COLORS["navy"]}},
        )
    )
    fig.update_layout(
        title="Take central incremental (M€ @ 35 %) · palos defendibles o residuales",
        yaxis_title="M€",
    )
    charts["waterfall"] = chart_html(fig, 400)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Crudo (sin tope)",
            x=["Yield", "FX", "Factoring", "Seguro", "Reserve"],
            y=[
                d["yield_take_35"] / 1e6,
                d["fx_take_35"] / 1e6,
                d["factoring_take_35"] / 1e6,
                d["credit_take_raw_35"] / 1e6,
                d["reserve_take_raw_35"] / 1e6,
            ],
            marker_color=COLORS["amber"],
        )
    )
    fig.add_trace(
        go.Bar(
            name="Robusto (tope 100 M€ / empresa en fórmulas)",
            x=["Yield", "FX", "Factoring", "Seguro", "Reserve"],
            y=[
                d["yield_take_35"] / 1e6,
                d["fx_take_35"] / 1e6,
                d["factoring_take_35"] / 1e6,
                d["credit_take_cap_35"] / 1e6,
                d["reserve_take_cap_35"] / 1e6,
            ],
            marker_color=COLORS["blue"],
        )
    )
    fig.update_layout(
        title="Take independiente @ 35 % · crudo frente a robusto",
        barmode="group",
        yaxis_title="M€",
    )
    charts["independent"] = chart_html(fig, 380)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[r["k"] for r in d["sens_yield"]],
            y=[r["take_35"] for r in d["sens_yield"]],
            mode="lines+markers",
            name="Yield take @35 %",
            line=dict(color=COLORS["blue"], width=3),
        )
    )
    fig.update_layout(
        title="Sensibilidad yield: colchón k × gasto mensual",
        xaxis_title="Meses de colchón",
        yaxis_title="M€ / año",
    )
    charts["sens_yield"] = chart_html(fig, 300)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Empresa a empresa",
            x=["Excedente (yield)", "Agujero (crédito)"],
            y=[d["excess_gross"] / 1e6, d["hole_gross"] / 1e6],
            marker_color=COLORS["amber"],
            text=[f"{d['excess_gross']/1e6:.1f}", f"{d['hole_gross']/1e6:.2f}"],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Bar(
            name="Tras movimiento de capital del grupo",
            x=["Excedente (yield)", "Agujero (crédito)"],
            y=[d["excess_net"] / 1e6, d["hole_net"] / 1e6],
            marker_color=COLORS["blue"],
            text=[f"{d['excess_net']/1e6:.1f}", f"{d['hole_net']/1e6:.2f}"],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        title="Notional colocable / financiable · bruto vs neteo de grupo (M€)",
        barmode="group",
        yaxis_title="M€",
    )
    charts["group_net"] = chart_html(fig, 360)
    return charts


def build_html(d: dict, charts: dict[str, str]) -> str:
    debt_rows = [
        [r["type"], fmt(r["n_productos"], 0), fmt(r["n_empresas"], 0)] for r in d["debt"]
    ]
    diag_rows = [
        [r["diagnosis"], fmt(r["n"], 0), fmt(r["n_fiables"], 0)] for r in d["diagnosis"]
    ]
    independent_rows = [
        [
            "yield",
            fmt(d["yield_n"], 0),
            meur(d["yield_notional"] / 1e6, 1),
            meur(d["yield_take_35"] / 1e6, 2),
            "renta medida",
            money(d["yield_med"]),
            money(d["yield_p90"]),
        ],
        [
            "yield (tras grupo)",
            fmt(d["yield_n_net"], 0),
            meur(d["excess_net"] / 1e6, 1),
            meur(d["yield_take_net_35"] / 1e6, 2),
            "excedente que no tapa un agujero hermana",
            "—",
            "—",
        ],
        [
            "fx",
            fmt(d["fx_n"], 0),
            meur(d["fx_notional"] / 1e6, 0),
            meur(d["fx_take_35"] / 1e6, 2),
            "renta medida",
            money(d["fx_med"]),
            money(d["fx_p90"]),
        ],
        [
            "factoring",
            fmt(d["factoring_n"], 0),
            meur(d["factoring_notional"] / 1e6, 0),
            meur(d["factoring_take_35"] / 1e6, 2),
            "one-shot; AR medido",
            money(d["factoring_med"]),
            money(d["factoring_p90"]),
        ],
        [
            "credit",
            fmt(d["credit_n"], 0),
            meur(d["premium_cap"] / 1e6, 2) + " prima robusta",
            meur(d["credit_take_cap_35"] / 1e6, 2),
            "hipótesis apilada",
            pct(100 * d["credit_late_med"]),
            "—",
        ],
        [
            "reserve (línea)",
            fmt(d["reserve_n"], 0),
            meur(d["linea_raw"] / 1e6, 0) + " crudo",
            meur(d["reserve_take_raw_35"] / 1e6, 1),
            "no defendible",
            "—",
            "—",
        ],
        [
            "reserve (agujero bruto)",
            fmt(d["hole_n"], 0),
            meur(d["hole_notional"] / 1e6, 2),
            meur(d["hole_take_35"] / 1e6, 3),
            "antes de pooling",
            "—",
            "—",
        ],
        [
            "reserve (agujero neto)",
            fmt(d["hole_n"] - d["hole_full_n"], 0),
            meur(d["hole_net"] / 1e6, 2),
            meur(d["hole_take_net_35"] / 1e6, 3),
            "tras movimiento de grupo",
            "—",
            "—",
        ],
    ]
    mixed_rows = [
        [
            f"<code>{r['group_id']}</code>",
            fmt(r["n_cos"], 0),
            fmt(r["n_surplus"], 0),
            fmt(r["n_hole"], 0),
            f"{r['excess_m']:.2f}",
            f"{r['hole_m']:.2f}",
            f"{r['moved_m']:.2f}",
            r["cover"],
        ]
        for r in d["mixed_groups"]
    ]
    pair_headers = ["SKU"] + d["pair_labels"]
    pair_rows = [[r["sku"]] + [fmt(r[lab], 0) for lab in d["pair_labels"]] for r in d["pair"]]
    outlier_rows = [
        [
            f"<code>{r['company_id']}</code>",
            f"{r['outflow_m']:.1f} M€",
            fmt(r["coverage"], 3),
            r["diagnosis"],
            f"{r['linea_m']:.0f} M€",
        ]
        for r in d["reserve_outliers"]
    ]
    sens_y = [[fmt(r["k"], 0), fmt(r["n"], 0), meur(r["excess_m"], 1), meur(r["take_35"], 2)] for r in d["sens_yield"]]
    sens_fx = [
        [money(r["thr"]), fmt(r["n"], 0), meur(r["fx_m"], 0), meur(r["take_35"], 2)] for r in d["sens_fx"]
    ]
    sens_fa = [
        [money(r["thr"]), fmt(r["n"], 0), meur(r["ar_m"], 0), meur(r["take_35"], 2)] for r in d["sens_fac"]
    ]
    adopt_rows = [
        [name, pct(100 * rate, 0), meur(d["renta_net_35"] / 0.35 * rate / 1e6, 2)]
        for name, rate in ADOPTION.items()
    ]
    px = d["proxy"]

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>X-Ray · Prioridad de productos</title>
  <style>{CSS}</style>
  <script>{get_plotlyjs()}</script>
</head>
<body>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">€</span><div><b>X-Ray</b><small>Productos</small></div></div>
    <nav>
      <a href="#resumen">01 · Veredicto</a>
      <a href="#metodo">02 · Método</a>
      <a href="#universo">03 · Universo</a>
      <a href="#grupo">04 · Grupo</a>
      <a href="#tam">05 · TAM vs robusto</a>
      <a href="#yield">06 · Yield</a>
      <a href="#fx">07 · FX</a>
      <a href="#factoring">08 · Factoring</a>
      <a href="#credit">09 · Seguro</a>
      <a href="#reserve">10 · Reserve</a>
      <a href="#solape">11 · Solape</a>
      <a href="#waterfall">12 · Incremental</a>
      <a href="#sensibilidad">13 · Sensibilidad</a>
      <a href="#conclusiones">14 · Orden</a>
    </nav>
    <div class="side-note">Artefacto autónomo<br>Notebook: <code>notebooks/02_productos.ipynb</code><br>Corte {AS_OF}</div>
  </aside>
  <main>
    <section class="hero" id="resumen">
      <div class="eyebrow">EMBAT X-RAY · 5 SKUS DE LA SPA</div>
      <h1>Añadir yield, luego FX.<br><em>El crédito no lidera.</em></h1>
      <p>Sobre 1.286 empresas, la renta defendible sigue siendo excedente más divisa. Antes de barrer o prestar, {fmt(d['n_both'], 0)} grupos con excedente y agujero moverían capital internamente: el TAM apenas se mueve; cambia a quién no hay que vender un SKU.</p>
      <div class="hero-meta">
        <span>Generado {datetime.now():%Y-%m-%d %H:%M}</span>
        <span>Adopción central 35 %</span>
        <span>{fmt(d['n_companies'], 0)} empresas</span>
      </div>
    </section>

    <section class="section">
      <div class="kpis">
        <div class="kpi"><small>Renta tras pooling</small><strong>{fmt(d['renta_net_35'] / 1e6, 2)} M€</strong><span>bruto {fmt(d['renta_35'] / 1e6, 2)} · 25–45 % = {fmt(d['renta_net_35'] / 0.35 * 0.25 / 1e6, 2)}–{fmt(d['renta_net_35'] / 0.35 * 0.45 / 1e6, 2)} M€</span></div>
        <div class="kpi"><small>Excedente neto</small><strong>{fmt(d['yield_n_net'], 0)}</strong><span>{meur(d['excess_net'] / 1e6, 0)} tras cubrir hermanas · {fmt(d['yield_white'], 0)} sin saving</span></div>
        <div class="kpi"><small>Divisa real (no n_tx)</small><strong>{fmt(d['fx_n'], 0)}</strong><span>{meur(d['fx_notional'] / 1e6, 0)}/año · take {meur(d['fx_take_35'] / 1e6, 2)} · no se netea</span></div>
        <div class="kpi"><small>Agujero neto de grupo</small><strong>{meur(d['hole_net'] / 1e6, 2)}</strong><span>bruto {meur(d['hole_notional'] / 1e6, 2)} en {fmt(d['hole_n'], 0)} · {fmt(d['hole_full_n'], 0)} cubiertos internamente</span></div>
      </div>
      <div class="callout insight"><b>Orden: movimiento de capital del grupo → yield → FX → factoring (acción) → seguro (upsell) → reserve (aviso).</b> Sumar take independiente de reserve ({meur(d['reserve_take_raw_35'] / 1e6, 0)}) o seguro crudo ({meur(d['credit_take_raw_35'] / 1e6, 1)}) es un error de cola, no una oportunidad.</div>
    </section>

    <section class="section" id="metodo">
      <div class="section-head"><span>02</span><div><h2>Qué es medido y qué se asume</h2><p>Misma pila que <code>analysis/monetizacion.py</code>: mapping + caja reconstruida en EUR, sin series con deriva, sin centinelas ≥ 100 M€.</p></div></div>
      {table(
          ["SKU", "Elegibilidad", "Notional", "Take Embat", "Clase"],
          [
              ["yield", "caja > 2× gasto mediano, sin deriva", "excedente EUR", "100 pb", "<span class='ok'>base medida</span>"],
              ["fx", "moneda producto ≠ moneda empresa", "flujo 24 m / 2, EUR", "15 pb", "<span class='ok'>base medida</span>"],
              ["factoring", "ERP y AR vencido > 50 k€", "pending AR EUR", "1,5 % one-shot", "AR medido; cesión hipótesis"],
              ["credit", "late_share > 15 % o AR > 200 k€", "prima = inflow × 0,5 % × late", "20 % de la prima", "elegibilidad medida; prima apilada"],
              ["reserve", "sin yield y colchón < 2 m o tensión", "línea = gasto × clip(6−cob.) × 0,5", "50 pb", "<span class='bad'>notional no defendible</span>"],
          ],
      )}
      <div class="callout">El módulo SaaS a 350 €/mes no entra en este ranking: ya está en el pitch. Yield y FX no se canibalizan. Yield y reserve sí. Factoring y seguro son la misma cola de cobros. El excedente de una sociedad del grupo cubre primero el agujero de otra: no se vende barrido ni crédito sobre esa caja.</div>
    </section>

    <section class="section" id="universo">
      <div class="section-head"><span>03</span><div><h2>Universo y cobertura</h2><p>Factoring y seguro exigen ERP. Yield y reserve exigen serie de caja fiable.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Empresas</small><strong>{fmt(d['n_companies'], 0)}</strong><span>{fmt(d['n_panel'], 0)} con caja · {fmt(d['n_reliable'], 0)} fiables</span></div>
        <div class="kpi"><small>Con ERP / facturas</small><strong>{fmt(d['n_erp'], 0)}</strong><span>{fmt(d['n_no_erp'], 0)} sin facturas = sin factoring</span></div>
        <div class="kpi"><small>Series con deriva</small><strong>{fmt(d['n_drift'], 0)}</strong><span>fuera de colas de caja</span></div>
        <div class="kpi"><small>Cuentas saving</small><strong>{fmt(d['saving_n'], 0)}</strong><span>el riel de colocación casi no existe</span></div>
      </div>
      <div class="grid two">
        <div class="panel">
          <h3>Diagnóstico de caja</h3>
          {table(["Diagnóstico", "N", "Fiables"], diag_rows)}
        </div>
        <div class="panel">
          <h3>Deuda ya contratada (foto final)</h3>
          {table(["Tipo", "Productos", "Empresas"], debt_rows)}
        </div>
      </div>
      <div class="panel">{charts['coverage']}</div>
    </section>

    <section class="section" id="grupo">
      <div class="section-head"><span>04</span><div><h2>Antes de un SKU, el grupo mueve capital</h2><p>{fmt(d['n_multi'], 0)} de {fmt(d['n_groups'], 0)} grupos tienen más de una sociedad. Donde una filial tiene excedente y otra agujero, el CFO no barre ni pide un préstamo: traspasa caja.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Grupos con ambos lados</small><strong>{fmt(d['n_both'], 0)}</strong><span>{fmt(d['n_full'], 0)} cubren el agujero · {fmt(d['n_cover_part'], 0)} en parte</span></div>
        <div class="kpi"><small>Capital que se movería</small><strong>{meur(d['moved_eur'] / 1e6, 2)}</strong><span>no es yield ni crédito: es pooling</span></div>
        <div class="kpi"><small>Excedente 344 → {fmt(d['excess_net'] / 1e6, 0)}</small><strong>{meur(d['excess_net'] / 1e6, 0)}</strong><span>{fmt(d['yield_sister_n'], 0)} empresas yield con hermana en agujero</span></div>
        <div class="kpi"><small>Agujero 11,38 → {fmt(d['hole_net'] / 1e6, 2)}</small><strong>{meur(d['hole_net'] / 1e6, 2)}</strong><span>{fmt(d['hole_full_n'], 0)} agujeros ({meur(d['hole_full_eur'] / 1e6, 2)}) cubiertos internamente</span></div>
      </div>
      <div class="panel">{charts['group_net']}</div>
      <div class="panel">
        <h3>Los {fmt(d['n_both'], 0)} grupos que no compran un producto: mueven capital</h3>
        {table(["Grupo", "Sociedades", "Con excedente", "Con agujero", "Excedente M€", "Agujero M€", "Se mueve M€", "Cobertura"], mixed_rows)}
      </div>
      <div class="callout insight"><b>El TAM casi no cambia; la acción sí.</b> De {fmt(d['hole_n'], 0)} agujeros, {fmt(d['hole_full_n'], 0)} ({meur(d['hole_full_eur'] / 1e6, 2)}) no son demanda de crédito: la hermana puede taparlos. {fmt(d['noline_full_n'], 0)} de esos no tienen póliza —tampoco la necesitan si el grupo traspasa. FX no se netea (es flujo cruzado de moneda, no saldo). El factoring de cobros estructurales sigue: {fmt(d['fact_hole_full_n'], 0)} agujeros factorables quedan cubiertos por la hermana; {fmt(d['fact_hole_open_n'], 0)} siguen abiertos con {meur(d['ar_open_eur'] / 1e6, 0)} de AR vencido.</div>
    </section>

    <section class="section" id="tam">
      <div class="section-head"><span>05</span><div><h2>TAM independiente frente a take robusto</h2><p>Sin tope, reserve y seguro ganan. Con tope 100 M€/empresa en las fórmulas, la ordenación se invierte hacia lo medido. El neteo de grupo recorta yield y agujero, no FX.</p></div></div>
      {table(
          ["SKU", "N", "Notional", "Take @35 %", "Clase", "Mediana", "P90"],
          independent_rows,
      )}
      <div class="panel">{charts['independent']}</div>
      <div class="callout warning"><b>No ordenar por la barra ámbar.</b> La línea de reserve cruda ({meur(d['linea_raw'] / 1e6, 0)}) sale de empresas con gasto mensual de cientos de millones. El umbral de 100 M€ ya se aplica por movimiento; estas series lo pasan a base de muchos movimientos grandes. Un prestamista no colocaría esa línea.</div>
    </section>

    <section class="section" id="yield">
      <div class="section-head"><span>06</span><div><h2>1. Yield · colocación de excedente</h2><p>Reproduce la base del pitch: {fmt(d['yield_n'], 0)} empresas, {meur(d['yield_notional'] / 1e6, 0)} ociosos. Tras pooling quedan {meur(d['excess_net'] / 1e6, 0)} en {fmt(d['yield_n_net'], 0)} empresas cuyo grupo no tiene un agujero que tapar primero.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Elegibles brutas</small><strong>{fmt(d['yield_n'], 0)}</strong><span>mediana {compact(d['yield_med'])}</span></div>
        <div class="kpi"><small>Take tras grupo</small><strong>{fmt(d['yield_take_net_35'] / 1e6, 2)} M€</strong><span>bruto {fmt(d['yield_take_35'] / 1e6, 2)} · 100 pb × 35 %</span></div>
        <div class="kpi"><small>Sin cuenta saving</small><strong>{fmt(d['yield_white'], 0)}</strong><span>de {fmt(d['yield_n'], 0)} · espacio en blanco</span></div>
        <div class="kpi"><small>Con hermana en agujero</small><strong>{fmt(d['yield_sister_n'], 0)}</strong><span>{meur(d['yield_sister_eur'] / 1e6, 2)} que no se barren a ciegas</span></div>
      </div>
      <div class="panel">{charts['yield']}</div>
      <div class="callout"><b>Abrir con esto, después de mirar el grupo.</b> No hay que desplazar un depósito: hay que crear el riel. El CFO mediano neto a 1,5 % gana ~{money(d['yield_med'] * 0.015)}/año. Si la hermana está en números rojos, primero se mueve capital.</div>
    </section>

    <section class="section" id="fx">
      <div class="section-head"><span>07</span><div><h2>2. FX Shield · exposición real a divisa</h2><p>Moneda del producto ≠ moneda de la empresa. El proxy de la SPA (<code>n_tx &gt; 50</code>) no vale.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Con FX &gt; 0</small><strong>{fmt(d['fx_n'], 0)}</strong><span>{fmt(d['fx_n_100k'], 0)} por encima de 100 k€/año</span></div>
        <div class="kpi"><small>Notional anual</small><strong>{fmt(d['fx_notional'] / 1e6, 0)} M€</strong><span>mediana {compact(d['fx_med'])}</span></div>
        <div class="kpi"><small>Take central</small><strong>{fmt(d['fx_take_35'] / 1e6, 2)} M€</strong><span>15 pb × 35 %</span></div>
        <div class="kpi"><small>Solape con yield</small><strong>{fmt(d['yield_x_fx'], 0)}</strong><span>se suman, no se restan</span></div>
      </div>
      <div class="panel">{charts['fx']}</div>
      <div class="callout warning"><b>Proxy SPA: {fmt(px['proxy_spa'], 0)} empresas con n_tx &gt; 50, de las que {fmt(px['proxy_sin_fx'], 0)} no tienen FX real.</b> {fmt(px['fx_sin_proxy'], 0)} tienen divisa y el proxy las deja fuera. Recomendar FX Shield con actividad bancaria es un falso positivo masivo.</div>
    </section>

    <section class="section" id="factoring">
      <div class="section-head"><span>08</span><div><h2>3. Factoring · acción sobre cobros, no renta</h2><p>{fmt(d['factoring_n'], 0)} empresas con AR vencido &gt; 50 k€. {fmt(d['factoring_white'], 0)} no tienen el producto.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Elegibles</small><strong>{fmt(d['factoring_n'], 0)}</strong><span>de {fmt(d['n_erp'], 0)} con ERP</span></div>
        <div class="kpi"><small>AR vencido</small><strong>{fmt(d['factoring_notional'] / 1e6, 0)} M€</strong><span>mediana {compact(d['factoring_med'])}</span></div>
        <div class="kpi"><small>Take @35 % one-shot</small><strong>{fmt(d['factoring_take_35'] / 1e6, 2)} M€</strong><span>no anualizar contra yield</span></div>
        <div class="kpi"><small>Sin producto hoy</small><strong>{fmt(d['factoring_white'], 0)}</strong><span>factoring en el catálogo: 19 empresas</span></div>
      </div>
      <div class="panel">{charts['ar']}</div>
      <div class="callout">501 empresas sin ERP no pueden recibir esta recomendación. Eso es cobertura, no salud. Confirming ya está en 70 empresas: el dataset está sesgado a préstamo/póliza, no a cesión de cobros. Como liquidez de agujero, {fmt(d['fact_hole_full_n'], 0)} de los {fmt(d['fact_hole_full_n'] + d['fact_hole_open_n'], 0)} agujeros factorables los cubre el grupo; el AR que sigue pidiendo anticipo es {meur(d['ar_open_eur'] / 1e6, 0)} en {fmt(d['fact_hole_open_n'], 0)} sociedades.</div>
    </section>

    <section class="section" id="credit">
      <div class="section-head"><span>09</span><div><h2>4. Seguro de impago · upsell de la misma cola</h2><p>{fmt(d['credit_x_factoring'], 0)} de {fmt(d['credit_n'], 0)} elegibles también lo son a factoring.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Elegibles</small><strong>{fmt(d['credit_n'], 0)}</strong><span>late mediana {pct(100 * d['credit_late_med'])}</span></div>
        <div class="kpi"><small>Take crudo @35 %</small><strong>{fmt(d['credit_take_raw_35'] / 1e6, 1)} M€</strong><span><span class="bad">no usar</span> · cola de inflow</span></div>
        <div class="kpi"><small>Take robusto @35 %</small><strong>{fmt(d['credit_take_cap_35'] / 1e6, 2)} M€</strong><span>inflow tope 100 M€/empresa</span></div>
        <div class="kpi"><small>Residual sin factoring</small><strong>{fmt(d['credit_residual_n'], 0)}</strong><span>take {meur(d['credit_residual_take_35'] / 1e6, 3)}</span></div>
      </div>
      <div class="callout">Tres hipótesis apiladas (prima 50 pb × late × referral 20 % × adopción). Por debajo de yield y FX una vez se tapa la cola. No es SKU de apertura.</div>
    </section>

    <section class="section" id="reserve">
      <div class="section-head"><span>10</span><div><h2>5. Reserve · aviso, no marketplace</h2><p>La regla ancha (cobertura &lt; 6 meses) coge {fmt(d['reserve_broad_n'], 0)} empresas: casi el universo. La estrecha, {fmt(d['reserve_n'], 0)}.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Tensas (estrecha)</small><strong>{fmt(d['reserve_n'], 0)}</strong><span>{fmt(d['reserve_has_line'], 0)} ya tienen póliza</span></div>
        <div class="kpi"><small>Línea cruda</small><strong>{fmt(d['linea_raw'] / 1e6, 0)} M€</strong><span>take {meur(d['reserve_take_raw_35'] / 1e6, 0)} @35 %</span></div>
        <div class="kpi"><small>Agujero bruto</small><strong>{fmt(d['hole_n'], 0)}</strong><span>{meur(d['hole_notional'] / 1e6, 2)} · {fmt(d['hole_no_line'], 0)} sin póliza</span></div>
        <div class="kpi"><small>Agujero neto de grupo</small><strong>{meur(d['hole_net'] / 1e6, 2)}</strong><span>{fmt(d['hole_full_n'], 0)} cubiertos por la hermana · take {meur(d['hole_take_net_35'] / 1e6, 3)}</span></div>
      </div>
      <div class="panel">
        <h3>Las series que rompen la fórmula de línea</h3>
        {table(["Empresa", "Gasto mens.", "Cobertura", "Diagnóstico", "Línea"], outlier_rows)}
      </div>
      <div class="callout warning"><b>La cifra defendible de demanda de crédito es {meur(d['hole_net'] / 1e6, 2)} tras pooling</b> (bruto {meur(d['hole_notional'] / 1e6, 2)} en {fmt(d['hole_n'], 0)} agujeros). {fmt(d['hole_full_n'], 0)} agujeros y {fmt(d['noline_full_n'], 0)} sin póliza no van al banco: van a tesorería de grupo. Por eso el pitch no abre con un marketplace.</div>
    </section>

    <section class="section" id="solape">
      <div class="section-head"><span>11</span><div><h2>El TAM independiente cuenta la misma tesorería varias veces</h2><p>407 empresas caen en tres o más SKUs.</p></div></div>
      <div class="grid two">
        <div class="panel">{charts['nsku']}</div>
        <div class="panel">{charts['overlap']}</div>
      </div>
      {table(pair_headers, pair_rows)}
      <div class="callout">Yield ∩ reserve = 0 por construcción. Factoring ∩ seguro = {fmt(d['credit_x_factoring'], 0)}. Un waterfall que sume 6,7 M€ + 0,76 M€ como carteras distintas está mal.</div>
    </section>

    <section class="section" id="waterfall">
      <div class="section-head"><span>12</span><div><h2>Impacto incremental, no ranking de comisiones de la SPA</h2><p>Yield y FX se suman, yield ya neto de pooling. Seguro residual = elegible a seguro y no a factoring. Reserve entra solo como agujero que el grupo no cubre.</p></div></div>
      <div class="panel">{charts['waterfall']}</div>
      {table(
          ["Paso", "SKU", "N", "Take @35 %", "Qué es"],
          [
              ["0", "pooling", fmt(d["n_both"], 0) + " grupos", meur(0, 2), "mover capital · no es un SKU"],
              ["1", "yield neto", fmt(d["yield_n_net"], 0), meur(d["yield_take_net_35"] / 1e6, 2), "renta medida tras cubrir hermanas"],
              ["2", "fx", fmt(d["fx_n"], 0), meur(d["fx_take_35"] / 1e6, 2), "renta medida · no se netea"],
              ["3", "factoring", fmt(d["factoring_n"], 0), meur(d["factoring_take_35"] / 1e6, 2), "one-shot · no sumar a la renta"],
              ["4", "credit residual", fmt(d["credit_residual_n"], 0), meur(d["credit_residual_take_35"] / 1e6, 3), "upsell · no solapar"],
              ["5", "agujero neto", fmt(d["hole_n"] - d["hole_full_n"], 0), meur(d["hole_take_net_35"] / 1e6, 3), "demanda de crédito que el grupo no tapa"],
          ],
      )}
    </section>

    <section class="section" id="sensibilidad">
      <div class="section-head"><span>13</span><div><h2>Los umbrales mueven el n, no el take de la cola</h2><p>Yield a 2 meses es estable. FX casi todo el notional está por encima de 100 k€/año. Factoring a 200 k€ deja el AR casi intacto.</p></div></div>
      <div class="grid three">
        <div class="panel">
          <h3>Yield · k meses de colchón</h3>
          {table(["k", "N", "Excedente", "Take 35 %"], sens_y)}
        </div>
        <div class="panel">
          <h3>FX · notional mínimo</h3>
          {table(["Mínimo", "N", "Notional", "Take 35 %"], sens_fx)}
        </div>
        <div class="panel">
          <h3>Factoring · umbral AR</h3>
          {table(["Umbral", "N", "AR", "Take 35 %"], sens_fa)}
        </div>
      </div>
      <div class="panel">{charts['sens_yield']}</div>
      <h3>Adopción sobre la renta medida (yield neto + FX)</h3>
      {table(["Escenario", "Adopción", "Renta anual"], adopt_rows)}
    </section>

    <section class="section conclusions" id="conclusiones">
      <div class="section-head"><span>14</span><div><h2>Qué añadir, y en qué orden</h2><p>Evidencia primero. Luego n. Luego fricción comercial. El grupo, antes que el SKU.</p></div></div>
      <div class="conclusion-list">
        <article><span>00</span><div><h3>Movimiento de capital</h3><p>{fmt(d['n_both'], 0)} grupos tienen excedente y agujero a la vez. Moverían {meur(d['moved_eur'] / 1e6, 2)}. No es un producto de la SPA: es la primera acción de tesorería. {fmt(d['hole_full_n'], 0)} agujeros y {fmt(d['yield_sister_n'], 0)} empresas yield se redirigen aquí.</p></div></article>
        <article><span>01</span><div><h3>Yield</h3><p>{fmt(d['yield_n_net'], 0)} empresas con excedente neto, {meur(d['excess_net'] / 1e6, 0)}, take {meur(d['yield_take_net_35'] / 1e6, 2)}/año (bruto {fmt(d['yield_n'], 0)} / {meur(d['yield_notional'] / 1e6, 0)}). {fmt(d['yield_white'], 0)} sin saving. Es el hueco más limpio y la primera línea del pitch de tesorería.</p></div></article>
        <article><span>02</span><div><h3>FX Shield</h3><p>{fmt(d['fx_n'], 0)} con exposición real, {meur(d['fx_notional'] / 1e6, 0)}/año, take {meur(d['fx_take_35'] / 1e6, 2)}. No se netea por grupo. No usar <code>n_tx &gt; 50</code>. Umbral útil: &gt; 100 k€/año ({fmt(d['fx_n_100k'], 0)} empresas).</p></div></article>
        <article><span>03</span><div><h3>Factoring como acción</h3><p>AR medido {meur(d['factoring_notional'] / 1e6, 0)} en {fmt(d['factoring_n'], 0)} empresas. Take one-shot {meur(d['factoring_take_35'] / 1e6, 2)} si se cede al 1,5 %. Como liquidez de agujero, el grupo ya cubre {fmt(d['fact_hole_full_n'], 0)} casos; quedan {fmt(d['fact_hole_open_n'], 0)} con {meur(d['ar_open_eur'] / 1e6, 0)} de AR. 501 empresas no tienen ERP.</p></div></article>
        <article><span>04</span><div><h3>Seguro, después</h3><p>Misma cola que factoring ({fmt(d['credit_x_factoring'], 0)}). Take robusto {meur(d['credit_take_cap_35'] / 1e6, 2)}; el crudo {meur(d['credit_take_raw_35'] / 1e6, 1)} no se presenta. Upsell, no apertura.</p></div></article>
        <article><span>05</span><div><h3>Reserve no es P&amp;L</h3><p>{fmt(d['reserve_n'], 0)} tensas es un n de aviso. Demanda de crédito neta: {meur(d['hole_net'] / 1e6, 2)} ({fmt(d['hole_n'] - d['hole_full_n'], 0)} agujeros que el grupo no tapa). La línea de {meur(d['linea_raw'] / 1e6, 0)} no se cita.</p></div></article>
        <article><span>06</span><div><h3>Demo de Productos</h3><p>No rankear por comisión simulada de la SPA. Mostrar necesidad tesorera medida, y no recomendar barrido ni crédito si hay caja hermana.</p></div></article>
      </div>
      <div class="final-note">Reproducible con <code>python analysis/productos.py</code>. Exploración viva: <code>notebooks/02_productos.ipynb</code>. Usa <code>src/mapping</code> y, si existe, <code>analysis/cash.duckdb</code>. Los CSV de <code>data/</code> no se reescriben. El módulo SaaS y las cifras 3,0 / 4,2 / 5,4 M€ siguen en <code>context/monetizacion.md</code>.</div>
    </section>
    <footer>HackSpain 2026 · X-Ray · Prioridad de productos · {datetime.now():%Y-%m-%d}</footer>
  </main>
</body>
</html>"""


def main() -> None:
    connection = connect()
    print("Caja conectada · construyendo panel de necesidad…")
    setup_need(connection)
    data = collect(connection)
    charts = build_charts(data)
    OUTPUT.write_text(build_html(data, charts), encoding="utf-8")
    print(
        f"Escrito {OUTPUT.relative_to(ROOT)} "
        f"({OUTPUT.stat().st_size / 1_000_000:.1f} MB) · "
        f"yield {data['yield_n']} / {data['yield_notional']/1e6:.0f} M€ · "
        f"FX {data['fx_n']} / {data['fx_notional']/1e6:.0f} M€ · "
        f"renta central {data['renta_net_35']/1e6:.2f} M€ "
        f"(pooling {data['moved_eur']/1e6:.2f} M€ · {data['n_both']} grupos)"
    )


if __name__ == "__main__":
    main()
