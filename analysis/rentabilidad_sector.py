#!/usr/bin/env python3
"""Rentabilidad por SKU cruzada con el sector inferido.

El take de Embat solo se imputa si (1) el SKU está en la mesa sectorial,
(2) hay una base medida en tesorería/ERP y (3) el grupo no tapa el hueco
antes. La persistencia se cuenta en meses con esa necesidad, no se inventa
un LTV. Confirming no tiene take publicado en el repo: no se fabrica.

Artefactos:
  analysis/rentabilidad_sector.html
  data/processed/rentabilidad_sku.csv
"""

from __future__ import annotations

import csv
import html
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis" / "rentabilidad_sector.html"
BOOK = ROOT / "data" / "processed" / "rentabilidad_sku.csv"
SECTOR_TABLE = ROOT / "data" / "processed" / "company_sector.csv"
ANALYSIS = Path(__file__).resolve().parent
for _p in (str(ANALYSIS), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cluster_sector import (  # noqa: E402
    SECTOR_COLORS,
    SECTOR_SHORT,
    SKU_LABELS,
    SKU_ORDER,
)
from generate_report import (  # noqa: E402
    COLORS,
    CSS,
    chart_html,
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
from productos import (  # noqa: E402
    FACTORING_BPS,
    INSURANCE_PREM,
    INSURANCE_REFERRAL,
    RESERVE_BPS,
    setup_need,
)

HORIZON = 3
ADOPT = ADOPTION["central"]
WINDOW_MONTHS = 24

# Confirming no tiene bps en productos.py / monetizacion.md. No se inventa.
SKU_BPS = {
    "yield": DEPOSIT_BPS,
    "fx": FX_BPS,
    "factoring": FACTORING_BPS,
    "confirming": None,
    "reserve": RESERVE_BPS,
    "credit": INSURANCE_REFERRAL,
}

SKU_NATURE = {
    "yield": "recurrente · stock aparcado",
    "fx": "recurrente · flujo anual",
    "factoring": "origination · ciclo de AR",
    "confirming": "sin take medido",
    "reserve": "híbrido · agujero neto",
    "credit": "referral · prima residual",
}

SKU_COLOR = {
    "yield": COLORS["blue"],
    "fx": COLORS["cyan"],
    "factoring": COLORS["amber"],
    "confirming": COLORS["slate"],
    "reserve": COLORS["red"],
    "credit": COLORS["green"],
}


def _finite(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def persistence(months_need, months_obs, *, calendar: bool = False) -> float:
    if calendar:
        denom = WINDOW_MONTHS
    else:
        denom = months_obs or 0
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, (months_need or 0) / denom))


def retained_take(year1: float, persist: float, sku: str, horizon: int = HORIZON) -> float:
    """Take a 3 años. Recurrente se alarga; origination solo un ciclo más.

    Yield/FX/reserve: year1 × (1 + p + p²). Factoring/seguro: year1 × (1 + p).
    p es la fracción medida de meses con la necesidad, no un LTV.
    """
    if sku in {"factoring", "credit"}:
        return year1 * (1 + persist)
    total = 0.0
    weight = 1.0
    for _ in range(horizon):
        total += year1 * weight
        weight *= persist
    return total


def setup_sector_book(connection) -> None:
    path = SECTOR_TABLE.as_posix().replace("'", "''")
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE sector_co AS
        SELECT
            company_id,
            group_id,
            business_kind AS tipo,
            coalesce(top_sector, '') AS sector,
            coalesce(sector_set, '') AS sector_set,
            coalesce(tenor, '') AS tenor,
            coalesce(product_fit, '') AS product_fit,
            product_fit ILIKE '%Yield%' AS mesa_yield,
            product_fit ILIKE '%FX Shield%' AS mesa_fx,
            product_fit ILIKE '%Factoring%' AS mesa_factoring,
            product_fit ILIKE '%Confirming%' AS mesa_confirming,
            product_fit ILIKE '%Reserve%' AS mesa_reserve,
            product_fit ILIKE '%Seguro%' AS mesa_credit
        FROM read_csv_auto('{path}', HEADER=TRUE)
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE persist AS
        SELECT
            m.company_id,
            count(*) AS months_obs,
            count(*) FILTER (
                WHERE s.median_outflow > 0 AND m.cash_eur > 2 * s.median_outflow
            ) AS months_yield,
            count(*) FILTER (
                WHERE m.cash_eur < 0
                   OR (s.median_outflow > 0 AND m.cash_eur < 2 * s.median_outflow)
            ) AS months_tight
        FROM cash.cash_metrics m
        JOIN cash.cash_summary s USING (company_id)
        WHERE NOT s.has_drift
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE fx_months AS
        WITH prod AS (
            SELECT product_id, currency FROM banking_products
            UNION ALL
            SELECT product_id, currency FROM debt_products
        )
        SELECT t.company_id, count(DISTINCT date_trunc('month', t.date)) AS months_fx
        FROM transactions t
        JOIN companies c USING (company_id)
        LEFT JOIN prod p ON p.product_id = t.product_id
        LEFT JOIN cash.fx f ON f.currency = coalesce(p.currency, c.currency)
        WHERE t.date >= DATE '{WINDOW_START}' AND t.date < DATE '{WINDOW_END}'
          AND p.currency IS NOT NULL AND p.currency <> c.currency
          AND abs(t.amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
          AND f.currency IS NOT NULL
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE ar_months AS
        SELECT
            i.company_id,
            count(DISTINCT date_trunc('month', i.due_date)) AS months_ar
        FROM invoices i
        LEFT JOIN cash.fx f ON f.currency = coalesce(i.currency, 'EUR')
        WHERE i.amount > 0
          AND i.pending_amount > 0
          AND i.status NOT IN ('paid', 'cancelled')
          AND i.document_type IN ('invoice', 'invoiceGroup')
          AND i.due_date < DATE '{AS_OF}'
          AND i.due_date >= DATE '2015-01-01'
          AND abs(i.pending_amount / coalesce(f.units_per_eur, 1)) < {ARTIFACT_EUR}
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE base AS
        SELECT
            n.company_id,
            n.group_id,
            coalesce(sc.sector, '') AS sector,
            coalesce(sc.tipo, '') AS tipo,
            coalesce(sc.tenor, '') AS tenor,
            coalesce(sc.mesa_yield, FALSE) AS mesa_yield,
            coalesce(sc.mesa_fx, FALSE) AS mesa_fx,
            coalesce(sc.mesa_factoring, FALSE) AS mesa_factoring,
            coalesce(sc.mesa_confirming, FALSE) AS mesa_confirming,
            coalesce(sc.mesa_reserve, FALSE) AS mesa_reserve,
            coalesce(sc.mesa_credit, FALSE) AS mesa_credit,
            n.elig_yield, n.elig_fx, n.elig_factoring, n.elig_reserve, n.elig_credit,
            n.has_saving, n.has_factoring, n.has_line, n.has_confirming, n.has_invoices,
            n.has_drift, n.cash_eur, n.excess_eur, n.fx_annual_eur, n.overdue_ar_eur,
            n.inflow_12m_eur, n.late_share_ar,
            g.excess_pool, g.hole_pool, g.n_cos,
            CASE WHEN n.elig_yield AND g.excess_pool > 0
                 THEN n.excess_eur * greatest(g.excess_pool - g.hole_pool, 0) / g.excess_pool
                 ELSE 0 END AS excess_net,
            CASE WHEN NOT n.has_drift AND n.cash_eur < 0 AND g.hole_pool > 0
                 THEN (-n.cash_eur) * greatest(g.hole_pool - g.excess_pool, 0) / g.hole_pool
                 ELSE 0 END AS hole_net,
            (NOT n.has_drift AND n.cash_eur < 0 AND g.n_cos > 1
             AND g.excess_pool >= g.hole_pool) AS hole_covered,
            coalesce(p.months_obs, 0) AS months_obs,
            coalesce(p.months_yield, 0) AS months_yield,
            coalesce(p.months_tight, 0) AS months_tight,
            coalesce(fx.months_fx, 0) AS months_fx,
            coalesce(ar.months_ar, 0) AS months_ar
        FROM need n
        JOIN gnet g USING (group_id)
        LEFT JOIN sector_co sc USING (company_id)
        LEFT JOIN persist p USING (company_id)
        LEFT JOIN fx_months fx USING (company_id)
        LEFT JOIN ar_months ar USING (company_id)
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE book_raw AS
        SELECT company_id, group_id, sector, tipo, tenor, 'yield' AS sku,
               mesa_yield AS on_mesa,
               (elig_yield AND NOT has_saving AND excess_net > 1) AS in_book,
               excess_net AS notional,
               months_yield AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        UNION ALL
        SELECT company_id, group_id, sector, tipo, tenor, 'fx' AS sku,
               mesa_fx AS on_mesa,
               (elig_fx AND fx_annual_eur > 1) AS in_book,
               fx_annual_eur AS notional,
               months_fx AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        UNION ALL
        SELECT company_id, group_id, sector, tipo, tenor, 'factoring' AS sku,
               mesa_factoring AS on_mesa,
               (elig_factoring AND NOT hole_covered AND overdue_ar_eur > 1) AS in_book,
               overdue_ar_eur AS notional,
               months_ar AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        UNION ALL
        SELECT company_id, group_id, sector, tipo, tenor, 'confirming' AS sku,
               mesa_confirming AS on_mesa,
               FALSE AS in_book,
               0 AS notional,
               0 AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        UNION ALL
        SELECT company_id, group_id, sector, tipo, tenor, 'reserve' AS sku,
               mesa_reserve AS on_mesa,
               (hole_net > 1 AND NOT has_line) AS in_book,
               least(hole_net, {ARTIFACT_EUR}) AS notional,
               months_tight AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        UNION ALL
        SELECT company_id, group_id, sector, tipo, tenor, 'credit' AS sku,
               mesa_credit AS on_mesa,
               (elig_credit AND NOT elig_factoring
                AND least(inflow_12m_eur, {ARTIFACT_EUR}) * {INSURANCE_PREM} * late_share_ar > 1) AS in_book,
               least(inflow_12m_eur, {ARTIFACT_EUR}) * {INSURANCE_PREM} * late_share_ar AS notional,
               months_ar AS months_need,
               {WINDOW_MONTHS} AS months_obs,
               TRUE AS calendar_persist
        FROM base
        """
    )


def price_book(rows: list[dict]) -> list[dict]:
    priced = []
    for row in rows:
        sku = row["sku"]
        bps = SKU_BPS[sku]
        notional = _finite(row.get("notional")) or 0.0
        persist = persistence(
            row.get("months_need"),
            row.get("months_obs"),
            calendar=bool(row.get("calendar_persist")),
        )
        in_book = bool(row.get("in_book")) and bool(row.get("on_mesa"))
        if bps is None or not in_book:
            take_100 = 0.0
            take_35 = 0.0
            take_kept = 0.0
        else:
            take_100 = notional * bps
            take_35 = take_100 * ADOPT
            take_kept = retained_take(take_35, persist, sku)
        priced.append(
            {
                **row,
                "in_book": in_book,
                "notional": notional if in_book else 0.0,
                "bps": bps,
                "persist": persist,
                "take_y1_100": take_100,
                "take_y1_35": take_35,
                "take_y1_25": take_100 * ADOPTION["conservador"] if bps is not None and in_book else 0.0,
                "take_y1_45": take_100 * ADOPTION["agresivo"] if bps is not None and in_book else 0.0,
                "take_3y_35": take_kept,
            }
        )
    return priced


def sku_rollup(book: list[dict]) -> list[dict]:
    out = []
    for sku in SKU_ORDER:
        subset = [row for row in book if row["sku"] == sku]
        booked = [row for row in subset if row["in_book"]]
        n = len(booked)
        notionals = [row["notional"] for row in booked]
        takes = [row["take_y1_35"] for row in booked]
        kept = [row["take_3y_35"] for row in booked]
        persists = [row["persist"] for row in booked]
        takes_sorted = sorted(takes, reverse=True)
        top10 = sum(takes_sorted[:10])
        total = sum(takes)
        out.append(
            {
                "sku": sku,
                "label": SKU_LABELS[sku],
                "nature": SKU_NATURE[sku],
                "bps": SKU_BPS[sku],
                "n": n,
                "n_mesa": sum(1 for row in subset if row["on_mesa"]),
                "n_eligible_off_mesa": sum(1 for row in subset if row["in_book"] is False and row.get("on_mesa") is False),
                "notional": sum(notionals),
                "median_notional": sorted(notionals)[len(notionals) // 2] if notionals else 0.0,
                "take_y1_25": sum(row["take_y1_25"] for row in booked),
                "take_y1_35": total,
                "take_y1_45": sum(row["take_y1_45"] for row in booked),
                "take_3y_35": sum(kept),
                "persist_med": sorted(persists)[len(persists) // 2] if persists else 0.0,
                "top10_share": (top10 / total) if total else 0.0,
            }
        )
    return out


def sector_sku_matrix(book: list[dict]) -> tuple[list[str], list[str], list[list[float]]]:
    booked = [row for row in book if row["in_book"] and row["take_y1_35"] > 0]
    sectors = [
        name
        for name, _n in Counter(row["sector"] or "sin sector" for row in booked).most_common()
        if name
    ]
    skus = [sku for sku in SKU_ORDER if SKU_BPS[sku] is not None]
    z = []
    for sector in sectors:
        z.append(
            [
                sum(
                    row["take_y1_35"]
                    for row in booked
                    if (row["sector"] or "sin sector") == sector and row["sku"] == sku
                )
                / 1e6
                for sku in skus
            ]
        )
    return sectors, skus, z


def tipo_rollup(book: list[dict]) -> list[dict]:
    out = []
    for tipo in ("producto", "servicio", "mixto", "insuficiente"):
        subset = [row for row in book if row["in_book"] and row["tipo"] == tipo]
        if not subset:
            continue
        by_sku = Counter()
        take = defaultdict(float)
        for row in subset:
            by_sku[row["sku"]] += 1
            take[row["sku"]] += row["take_y1_35"]
        out.append(
            {
                "tipo": tipo,
                "n": len({row["company_id"] for row in subset}),
                "take": sum(take.values()),
                "kept": sum(row["take_3y_35"] for row in subset),
                "top": SKU_LABELS[max(take, key=take.get)] if take else "—",
            }
        )
    return out


def write_book(book: list[dict]) -> None:
    BOOK.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "company_id",
        "group_id",
        "sector",
        "tipo",
        "tenor",
        "sku",
        "on_mesa",
        "in_book",
        "notional",
        "persist",
        "take_y1_35",
        "take_3y_35",
    ]
    with BOOK.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(book, key=lambda item: (item["company_id"], item["sku"])):
            if not row["in_book"]:
                continue
            out = {}
            for field in fields:
                value = row.get(field)
                if isinstance(value, bool):
                    out[field] = "true" if value else "false"
                elif isinstance(value, float):
                    out[field] = f"{value:.6g}"
                elif value is None:
                    out[field] = ""
                else:
                    out[field] = value
            writer.writerow(out)


def take_bar(roll: list[dict]) -> go.Figure:
    priced = [row for row in roll if row["bps"] is not None]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            name="Año 1 @ 35 %",
            x=[row["label"] for row in priced],
            y=[row["take_y1_35"] / 1e6 for row in priced],
            marker_color=COLORS["blue"],
            text=[f"{row['take_y1_35']/1e6:.2f}" for row in priced],
            textposition="outside",
            cliponaxis=False,
        )
    )
    figure.add_trace(
        go.Bar(
            name="3 años con persistencia medida",
            x=[row["label"] for row in priced],
            y=[row["take_3y_35"] / 1e6 for row in priced],
            marker_color=COLORS["cyan"],
            text=[f"{row['take_3y_35']/1e6:.2f}" for row in priced],
            textposition="outside",
            cliponaxis=False,
        )
    )
    figure.update_layout(
        title="Take de Embat · escenario 35 % (M€)",
        barmode="group",
        yaxis_title="M€",
        showlegend=True,
    )
    return figure


def persist_bar(roll: list[dict]) -> go.Figure:
    priced = [row for row in roll if row["bps"] is not None]
    figure = go.Figure(
        go.Bar(
            x=[row["persist_med"] for row in priced],
            y=[row["label"] for row in priced],
            orientation="h",
            marker_color=[SKU_COLOR[row["sku"]] for row in priced],
            text=[f"{row['persist_med']:.0%}".replace(".", ",") for row in priced],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: persistencia mediana %{x:.0%}<extra></extra>",
        )
    )
    figure.update_layout(
        title="Stickiness medida: fracción de meses con la necesidad",
        xaxis=dict(title="Meses con necesidad / meses observados", range=[0, 1.05]),
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    return figure


def heatmap(sectors: list[str], skus: list[str], z: list[list[float]]) -> go.Figure:
    figure = go.Figure(
        go.Heatmap(
            z=z,
            x=[SKU_LABELS[sku] for sku in skus],
            y=[SECTOR_SHORT.get(name, name) for name in sectors],
            colorscale=[
                [0, "#f5f7fa"],
                [0.4, "#c5dcff"],
                [0.75, "#1463ff"],
                [1, "#102a43"],
            ],
            text=[[f"{v:.2f}" if v >= 0.01 else "" for v in row] for row in z],
            texttemplate="%{text}",
            hovertemplate="%{y} × %{x}: %{z:.2f} M€ / año<extra></extra>",
            colorbar=dict(title="M€/año", thickness=10, len=0.7),
        )
    )
    figure.update_layout(
        title="Take año 1 @ 35 % por sector × SKU (M€)",
        yaxis=dict(autorange="reversed"),
        xaxis=dict(side="top", tickangle=-25),
        showlegend=False,
    )
    return figure


def quadrant(book: list[dict], roll: list[dict]) -> go.Figure:
    figure = go.Figure()
    for sku in SKU_ORDER:
        if SKU_BPS[sku] is None:
            continue
        row = next(item for item in roll if item["sku"] == sku)
        if row["n"] == 0:
            continue
        figure.add_trace(
            go.Scatter(
                x=[row["persist_med"]],
                y=[row["take_y1_35"] / 1e6],
                mode="markers+text",
                name=row["label"],
                text=[row["label"].split(" · ")[0]],
                textposition="top center",
                marker=dict(
                    size=12 + min(40, row["n"] / 8),
                    color=SKU_COLOR[sku],
                    opacity=0.85,
                    line=dict(width=1, color="white"),
                ),
                hovertemplate=(
                    f"{row['label']}<br>persistencia mediana {row['persist_med']:.0%}"
                    f"<br>take año 1 {row['take_y1_35']/1e6:.2f} M€"
                    f"<br>{row['n']} empresas<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        title="Dónde está el dinero y cuánto se queda",
        xaxis=dict(title="Stickiness mediana", range=[-0.05, 1.05]),
        yaxis_title="Take año 1 @ 35 % (M€)",
        showlegend=False,
    )
    return figure


def sector_table(book: list[dict]) -> list[list]:
    booked = [row for row in book if row["in_book"]]
    sectors = [
        name for name, _ in Counter(row["sector"] or "sin sector" for row in booked).most_common()
    ]
    out = []
    for sector in sectors:
        subset = [row for row in booked if (row["sector"] or "sin sector") == sector]
        take = sum(row["take_y1_35"] for row in subset)
        kept = sum(row["take_3y_35"] for row in subset)
        by_sku = defaultdict(float)
        for row in subset:
            by_sku[row["sku"]] += row["take_y1_35"]
        top = max(by_sku, key=by_sku.get) if by_sku else ""
        persists = [row["persist"] for row in subset]
        med_p = sorted(persists)[len(persists) // 2] if persists else 0.0
        out.append(
            [
                html.escape(SECTOR_SHORT.get(sector, sector)),
                fmt(len({row["company_id"] for row in subset}), 0),
                f"{take/1e6:.2f}".replace(".", ","),
                f"{kept/1e6:.2f}".replace(".", ","),
                html.escape(SKU_LABELS.get(top, "—")),
                f"{med_p:.0%}".replace(".", ","),
            ]
        )
    return out


def sku_table(roll: list[dict]) -> list[list]:
    out = []
    for row in roll:
        bps = row["bps"]
        bps_txt = "—" if bps is None else (f"{bps*10_000:.0f} pb" if bps < 0.05 else f"{bps:.0%}")
        if bps == INSURANCE_REFERRAL:
            bps_txt = f"{INSURANCE_PREM:.1%} prima × {INSURANCE_REFERRAL:.0%} referral"
        out.append(
            [
                html.escape(row["label"]),
                html.escape(row["nature"]),
                bps_txt,
                fmt(row["n"], 0),
                f"{row['notional']/1e6:.1f}".replace(".", ",") if row["notional"] else "—",
                f"{row['take_y1_35']/1e6:.2f}".replace(".", ",") if row["bps"] is not None else "—",
                f"{row['take_3y_35']/1e6:.2f}".replace(".", ",") if row["bps"] is not None else "—",
                f"{row['persist_med']:.0%}".replace(".", ",") if row["n"] else "—",
                f"{row['top10_share']:.0%}".replace(".", ",") if row["take_y1_35"] else "—",
            ]
        )
    return out


def tipo_table(rows: list[dict]) -> list[list]:
    return [
        [
            row["tipo"],
            fmt(row["n"], 0),
            f"{row['take']/1e6:.2f}".replace(".", ","),
            f"{row['kept']/1e6:.2f}".replace(".", ","),
            html.escape(row["top"]),
        ]
        for row in rows
    ]


def build_report(book: list[dict], roll: list[dict], extras: dict) -> str:
    booked = [row for row in book if row["in_book"]]
    y1 = sum(row["take_y1_35"] for row in booked)
    y3 = sum(row["take_3y_35"] for row in booked)
    n_co = len({row["company_id"] for row in booked})
    yield_row = next(item for item in roll if item["sku"] == "yield")
    fx_row = next(item for item in roll if item["sku"] == "fx")
    fac_row = next(item for item in roll if item["sku"] == "factoring")
    res_row = next(item for item in roll if item["sku"] == "reserve")
    sectors, skus, z = sector_sku_matrix(book)
    tipos = tipo_rollup(book)
    n_mesa = extras["n_mesa"]
    n_cut = extras["n_elig_not_mesa"]
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Rentabilidad por producto · sector inferido</title>
  <script>{get_plotlyjs()}</script>
  <style>{CSS}</style>
</head>
<body>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">X</span><div><b>X-Ray</b><small>Rentabilidad × sector</small></div></div>
    <nav>
      <a href="#rigor">Rigor</a>
      <a href="#ranking">Take por SKU</a>
      <a href="#stickiness">Stickiness</a>
      <a href="#sector">Por sector</a>
      <a href="#tipo">Producto o servicio</a>
      <a href="#limites">Límites</a>
    </nav>
    <p class="side-note">Adopción {ADOPT:.0%} y bps son supuestos. La base y los meses con necesidad están medidos.</p>
  </aside>
  <main>
    <header class="hero">
      <div class="eyebrow">HackSpain 2026 · análisis</div>
      <h1>El sector no cambia el bps.<br><em>Cambia quién entra en el libro.</em></h1>
      <p>Misma mesa sectorial, mismas bases de <code>productos.py</code>. El ingreso año 1 es notional × bps publicados × adopción 35 %. La stickiness es la fracción de meses en los que esa necesidad estuvo presente, no un LTV.</p>
      <div class="hero-meta">
        <span>{fmt(n_co, 0)} empresas en el libro</span>
        <span>Año 1 @ 35 % · {y1/1e6:.2f} M€</span>
        <span>3 años con persistencia · {y3/1e6:.2f} M€</span>
        <span>Pooling de grupo antes del SKU</span>
      </div>
    </header>

    <section class="section" id="rigor">
      <div class="section-head"><span>01</span><div><h2>Qué cifra es medida y cuál no</h2><p>Una fila de take mezcla tres capas. Solo la primera se ha visto en el dataset.</p></div></div>
      <div class="grid three">
        <div class="panel narrative"><h3>Medido</h3>
          <ul>
            <li>Excedente neto de pooling, AR vencido, flujo en divisa, agujero que el grupo no tapa.</li>
            <li>Meses con caja &gt; 2× gasto, meses con caja tensa, meses con FX, meses de facturas vencidas.</li>
            <li>Quién tiene already-have: saving, factoring, póliza.</li>
          </ul>
        </div>
        <div class="panel narrative"><h3>Supuesto, declarado</h3>
          <ul>
            <li>100 pb yield, 15 pb FX, 1,5 % factoring, 50 pb sobre agujero neto, 0,5 % prima × 20 % referral.</li>
            <li>Adopción 25 / 35 / 45 %. El central es 35 %, el de <code>monetizacion.md</code>.</li>
            <li>Que la frecuencia pasada se mantenga 3 años.</li>
          </ul>
        </div>
        <div class="panel narrative"><h3>Fuera del libro</h3>
          <ul>
            <li>Confirming: está en la mesa, no hay bps en el repo. Take = 0.</li>
            <li>Reserve sobre fórmula de gasto: cola del generador. Solo agujero neto.</li>
            <li>Seguro si ya hay factoring: se solapa. Solo residual.</li>
            <li>Barrido si la hermana tiene agujero: primero se traspasa caja.</li>
          </ul>
        </div>
      </div>
      <div class="callout insight"><b>El sector recorta el TAM, no lo inventa.</b> {fmt(n_mesa, 0)} empresas tienen mesa. {fmt(n_cut, 0)} serían elegibles por tesorería y el sector no las pone en ese SKU (comercio con AR no recibe factoring; holding no lidera crédito). Eso es el filtro, no un multiplicador.</div>
    </section>

    <section class="section" id="ranking">
      <div class="section-head"><span>02</span><div><h2>Take por producto, con el sector aplicado</h2><p>Año 1 es el escenario comercial. La barra a 3 años solo alarga lo que la persistencia medida sostiene.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Yield año 1</small><strong>{yield_row['take_y1_35']/1e6:.2f} M€</strong><span>{fmt(yield_row['n'], 0)} empresas · persistencia {yield_row['persist_med']:.0%}</span></div>
        <div class="kpi"><small>FX año 1</small><strong>{fx_row['take_y1_35']/1e6:.2f} M€</strong><span>{fmt(fx_row['n'], 0)} empresas · persistencia {fx_row['persist_med']:.0%}</span></div>
        <div class="kpi"><small>Factoring año 1</small><strong>{fac_row['take_y1_35']/1e6:.2f} M€</strong><span>origination · se queda poco si el atraso es un mes</span></div>
        <div class="kpi"><small>Póliza año 1</small><strong>{res_row['take_y1_35']/1e6:.2f} M€</strong><span>agujero neto tras pooling, no la línea simulada</span></div>
      </div>
      <div class="panel">{chart_html(take_bar(roll), 420)}</div>
      <div class="panel"><h3>Libro por SKU</h3>
        {table(["SKU", "Naturaleza", "Bps", "N", "Notional M€", "Año 1 @35%", "3 años", "Stickiness mediana", "Top 10"], sku_table(roll))}
        <p class="caption">Top 10 = cuota de take año 1 que concentran las diez empresas más grandes de ese SKU. Si pasa del 40 %, la cifra no es una cartera, es una cola.</p>
      </div>
      <div class="callout warning"><b>El factoring infla el año 1.</b> Es un 1,5 % sobre AR vencido hoy. A 3 años solo se suma un ciclo más ponderado por persistencia, no una anualidad. Yield y FX sí se alargan: el stock y el flujo vuelven a aparecer en el histórico. La renta (yield + FX) es la línea que se queda; el factoring es origination.</div>
    </section>

    <section class="section" id="stickiness">
      <div class="section-head"><span>03</span><div><h2>Stickiness medida, no un LTV</h2><p>Capchase pide retención. Aquí retención = la necesidad estuvo presente qué fracción del histórico de 24 meses.</p></div></div>
      <div class="grid two">
        <div class="panel">{chart_html(persist_bar(roll), 380, margin=dict(l=140, r=36, t=48, b=48))}</div>
        <div class="panel">{chart_html(quadrant(book, roll), 380)}</div>
      </div>
      <div class="panel narrative">
        <h3>Cómo se cuenta cada pegamento</h3>
        <ul>
          <li><b>Yield.</b> Meses con caja &gt; 2× gasto mediano. El depósito se aparca: si el excedente es estructural, el take se repite. Quien pide crédito con caja, ese depósito es colateral —pegamento, no solo 100 pb.</li>
          <li><b>FX.</b> Meses del recorte con movimiento en otra moneda / 24. La PM: el riel asusta y el agente no se usa. Una persistencia baja aquí es evidencia, no un fallo del recuento.</li>
          <li><b>Factoring.</b> Meses distintos de vencimiento de las facturas aún impagadas. Un atraso de un mes no es un libro; un AR repartido en muchos vencimientos sí lo es.</li>
          <li><b>Reserve.</b> Meses con caja negativa o cobertura &lt; 2. El take solo se cobra sobre el agujero que el grupo no tapa y que no tiene póliza.</li>
        </ul>
      </div>
    </section>

    <section class="section" id="sector">
      <div class="section-head"><span>04</span><div><h2>Dónde el sector mueve el P&amp;L</h2><p>Misma comisión. Distinta mesa. Un mayorista financia el ciclo; un comercio de TPV no adelanta cobros que ya tiene en caja.</p></div></div>
      <div class="panel">{chart_html(heatmap(sectors, skus, z), 520, margin=dict(l=88, r=48, t=96, b=36))}</div>
      <div class="panel"><h3>Sector, take y pegamento</h3>
        {table(["Sector", "Empresas", "Año 1 M€", "3 años M€", "SKU que más paga", "Stickiness mediana"], sector_table(book))}
      </div>
    </section>

    <section class="section" id="tipo">
      <div class="section-head"><span>05</span><div><h2>Producto, servicio o mixto</h2><p>El corte producto/servicio no es un CNAE. Cambia el mix de SKU que el libro puede cobrar.</p></div></div>
      <div class="panel">
        {table(["Tipo", "Empresas en el libro", "Año 1 M€", "3 años M€", "SKU líder"], tipo_table(tipos))}
        <p class="caption">Una empresa cuenta en todos los SKUs de su mesa que pasan el filtro. El líder es el de más take año 1 dentro de ese tipo.</p>
      </div>
    </section>

    <section class="section" id="limites">
      <div class="section-head"><span>06</span><div><h2>Límites</h2><p>Qué no afirma esta cuenta.</p></div></div>
      <div class="limitations">
        <article><b>No es P&amp;L de Embat</b><p>Adopción, bps y que el pasado se repita 3 años son supuestos. El pitch de suscripción (350 €/mes) vive en monetización, no aquí.</p></article>
        <article><b>Cola del generador</b><p>La columna top 10 avisa. Un notional de AR o FX en cuatro empresas no se presenta como cartera.</p></article>
        <article><b>Confirming sin precio</b><p>Cabe en la mesa de mayorista e industria. Sin bps publicado no hay ingreso. Fabricarlo sería lo contrario de rigor.</p></article>
        <article><b>El sector es un conjunto</b><p>Se usa el sector principal de la huella. Un comercio|hostelería hereda la mesa unida, no un CNAE único.</p></article>
      </div>
    </section>
    <footer>HackSpain 2026 · X-Ray · generado desde <code>analysis/rentabilidad_sector.py</code> · escenario central {ADOPT:.0%}</footer>
  </main>
</body>
</html>"""


def main() -> None:
    if not SECTOR_TABLE.exists():
        raise SystemExit(f"Falta {SECTOR_TABLE}. Corre antes analysis/cluster_sector.py")
    print("Connecting and building need…", flush=True)
    connection = connect()
    setup_need(connection)
    setup_sector_book(connection)
    raw = records(connection, "SELECT * FROM book_raw")
    book = price_book(raw)
    roll = sku_rollup(book)
    extras = {
        "n_mesa": connection.execute(
            "SELECT count(*) FROM sector_co WHERE product_fit IS NOT NULL AND product_fit <> ''"
        ).fetchone()[0],
        "n_elig_not_mesa": sum(
            1
            for row in raw
            if row["in_book"] and not row["on_mesa"] and row["sku"] != "confirming"
        ),
    }
    write_book(book)
    OUTPUT.write_text(build_report(book, roll, extras), encoding="utf-8")
    y1 = sum(row["take_y1_35"] for row in book if row["in_book"])
    y3 = sum(row["take_3y_35"] for row in book if row["in_book"])
    print(
        " | ".join(
            f"{row['sku']} n={row['n']} y1={row['take_y1_35']/1e6:.2f}M p={row['persist_med']:.2f}"
            for row in roll
            if row["bps"] is not None
        ),
        flush=True,
    )
    print(
        f"total y1@35% {y1/1e6:.2f} M€ · 3y {y3/1e6:.2f} M€ · wrote {OUTPUT} "
        f"({OUTPUT.stat().st_size/1_000:.0f} KB) and {BOOK}",
        flush=True,
    )


if __name__ == "__main__":
    main()
