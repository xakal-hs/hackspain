#!/usr/bin/env python3
"""Infiere régimen operativo y producto vs servicio por empresa.

El dataset no trae NACE/CNAE. Agrupa la huella de tesorería (cuotas de
categoría, nómina, TPV, ciclo de cobro/pago, albaranes) sin usar caja ni
runway como features: eso mezclaría salud con sector.

Artefactos:
  analysis/cluster_sector.html
  data/processed/company_sector.csv

No reescribe los CSV de data/ ni cablea el score.
"""

from __future__ import annotations

import csv
import html
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.offline.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "analysis" / "cluster_sector.html"
TABLE = ROOT / "data" / "processed" / "company_sector.csv"
PANEL = ROOT / "data" / "processed" / "panel_monthly.csv"
ANALYSIS = Path(__file__).resolve().parent
for _p in (str(ANALYSIS), str(ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from generate_report import (  # noqa: E402
    COLORS,
    CSS,
    chart_html,
    fmt,
    table,
)
from mapping.load import attach  # noqa: E402

MIN_CAT_TX = 24
K_RANGE = range(4, 9)
MIN_CLUSTER_SHARE = 0.03
KIND_MARGIN = 0.07
RANDOM_ITERS = 60

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

CLUSTER_FEATURES = PROFILE_CATEGORIES + (
    "payroll_share",
    "pos_cash_share",
    "collection_cv",
    "season_amp",
    "dso",
    "dpo",
    "n_customers",
    "hhi_ar",
    "goods_docs",
    "has_tpv",
    "has_confirming",
    "service_tokens",
)

KIND_GOODS = ("payment_share", "bulk_payment_share", "pos_cash_share", "goods_docs", "has_confirming")
KIND_SERVICES = ("payroll_share", "collection_recurrence", "service_tokens")


def _cat_sql() -> str:
    return "(" + ", ".join(f"'{c}'" for c in PROFILE_CATEGORIES) + ")"


def records(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    cursor = connection.execute(sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


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


def rank_column(values: list[float | None]) -> list[float]:
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda item: item[1])
    ranks = [0.5] * len(values)
    n = len(indexed)
    if n <= 1:
        return ranks
    for rank, (i, _) in enumerate(indexed):
        ranks[i] = rank / (n - 1)
    return ranks


def euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@dataclass
class KMeansResult:
    k: int
    assignments: list[int]
    centroids: list[list[float]]
    labels: dict[int, str]
    silhouette: float
    sizes: dict[int, int]


def kmeans(points: list[list[float]], k: int) -> tuple[list[int], list[list[float]]]:
    if len(points) < k:
        return [0] * len(points), [points[0][:]] if points else []
    centroids = [points[0][:]]
    while len(centroids) < k:
        far = max(
            range(len(points)),
            key=lambda i: min(euclidean(points[i], c) for c in centroids),
        )
        centroids.append(points[far][:])
    assignments = [0] * len(points)
    dims = len(points[0])
    for _ in range(RANDOM_ITERS):
        moved = False
        for i, point in enumerate(points):
            best = min(range(k), key=lambda j: euclidean(point, centroids[j]))
            if best != assignments[i]:
                assignments[i] = best
                moved = True
        for j in range(k):
            members = [points[i] for i, a in enumerate(assignments) if a == j]
            if members:
                centroids[j] = [sum(m[d] for m in members) / len(members) for d in range(dims)]
            else:
                far = max(
                    range(len(points)),
                    key=lambda i: min(euclidean(points[i], c) for c in centroids),
                )
                centroids[j] = points[far][:]
        if not moved:
            break
    return assignments, centroids


def silhouette(
    points: list[list[float]],
    assignments: list[int],
    sample: int | None = 400,
) -> float:
    n = len(points)
    if n < 3:
        return 0.0
    by_cluster: dict[int, list[int]] = defaultdict(list)
    for i, own in enumerate(assignments):
        by_cluster[own].append(i)
    if len(by_cluster) < 2:
        return 0.0
    if sample is None or n <= sample:
        probe = range(n)
    else:
        step = max(n // sample, 1)
        probe = range(0, n, step)
    scores = []
    for i in probe:
        point = points[i]
        own = assignments[i]
        same_idx = by_cluster[own]
        if len(same_idx) <= 1:
            continue
        a = sum(euclidean(point, points[j]) for j in same_idx if j != i) / (len(same_idx) - 1)
        other_means = []
        for other, idxs in by_cluster.items():
            if other == own or not idxs:
                continue
            other_means.append(sum(euclidean(point, points[j]) for j in idxs) / len(idxs))
        if not other_means:
            continue
        b = min(other_means)
        denom = max(a, b) or 1e-9
        scores.append((b - a) / denom)
    return sum(scores) / len(scores) if scores else 0.0


def pca_2d(points: list[list[float]]) -> list[tuple[float, float]]:
    n = len(points)
    d = len(points[0])
    means = [sum(p[j] for p in points) / n for j in range(d)]
    centered = [[p[j] - means[j] for j in range(d)] for p in points]
    cov = [[0.0] * d for _ in range(d)]
    for i in range(d):
        for j in range(i, d):
            value = sum(row[i] * row[j] for row in centered) / max(n - 1, 1)
            cov[i][j] = cov[j][i] = value

    def power(exclude: list[float] | None = None) -> list[float]:
        vector = [1.0 / math.sqrt(d)] * d
        if exclude is not None:
            vector = [vector[i] - exclude[i] * (1.0 / math.sqrt(d)) for i in range(d)]
            norm = math.sqrt(sum(x * x for x in vector)) or 1.0
            vector = [x / norm for x in vector]
        for _ in range(80):
            next_v = [sum(cov[i][j] * vector[j] for j in range(d)) for i in range(d)]
            if exclude is not None:
                proj = sum(next_v[i] * exclude[i] for i in range(d))
                next_v = [next_v[i] - proj * exclude[i] for i in range(d)]
            norm = math.sqrt(sum(x * x for x in next_v)) or 1.0
            vector = [x / norm for x in next_v]
        return vector

    v1 = power()
    v2 = power(v1)
    return [
        (
            sum(row[j] * v1[j] for j in range(d)),
            sum(row[j] * v2[j] for j in range(d)),
        )
        for row in centered
    ]


def setup_features(connection: duckdb.DuckDBPyConnection) -> None:
    cats = _cat_sql()
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE tx_agg AS
        SELECT
            company_id,
            count(*) AS n_tx,
            count(*) FILTER (WHERE category IN {cats}) AS n_cat_tx,
            coalesce(sum(abs(amount)), 0) AS vol_all,
            coalesce(sum(abs(amount)) FILTER (WHERE category = 'uncategorized'), 0) AS vol_uncat,
            coalesce(sum(abs(amount)) FILTER (WHERE category IN {cats}), 0) AS vol_cat,
            coalesce(sum(-amount) FILTER (WHERE amount < 0), 0) AS outflow,
            coalesce(sum(amount) FILTER (WHERE amount > 0), 0) AS inflow,
            coalesce(sum(-amount) FILTER (
                WHERE amount < 0 AND category IN ('salary', 'social_security')
            ), 0) AS payroll_out,
            coalesce(sum(abs(amount)) FILTER (
                WHERE category IN ('pos_settlement', 'cash_settlement', 'cash_withdrawal')
            ), 0) AS pos_cash_vol,
            coalesce(sum(abs(amount)) FILTER (WHERE category = 'payment'), 0) AS payment_vol,
            coalesce(sum(abs(amount)) FILTER (WHERE category = 'bulk_payment'), 0) AS bulk_payment_vol
        FROM transactions
        WHERE status = 'booked'
        GROUP BY 1
        """
    )
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE cat_share AS
        WITH scoped AS (
            SELECT company_id, category, abs(amount) AS volume
            FROM transactions
            WHERE status = 'booked' AND category IN {cats}
        ), totals AS (
            SELECT company_id, sum(volume) AS total_volume
            FROM scoped GROUP BY 1
        )
        SELECT s.company_id, s.category, sum(s.volume) / nullif(any_value(t.total_volume), 0) AS share
        FROM scoped s JOIN totals t USING (company_id)
        GROUP BY 1, 2
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE monthly_flow AS
        SELECT
            company_id,
            date_trunc('month', date) AS month,
            sum(CASE WHEN amount > 0 THEN amount ELSE 0 END) AS inflow,
            sum(CASE WHEN amount > 0 AND category IN (
                'collection', 'bulk_collection', 'pos_settlement', 'cash_settlement'
            ) THEN amount ELSE 0 END) AS collection
        FROM transactions
        WHERE status = 'booked'
        GROUP BY 1, 2
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE flow_shape AS
        SELECT
            company_id,
            count(*) AS n_months,
            stddev_pop(collection) / nullif(avg(collection), 0) AS collection_cv,
            max(inflow) / nullif(median(inflow), 0) AS season_amp
        FROM monthly_flow
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE inv_cycle AS
        SELECT
            company_id,
            count(*) AS n_invoices,
            count(*) FILTER (WHERE document_type IN ('deliveryNote', 'purchaseOrder')) AS n_goods_docs,
            count(*) FILTER (
                WHERE concept IS NOT NULL AND regexp_matches(
                    lower(concept),
                    'servic|suscrip|software|consultor|alquil|honor'
                )
            ) AS n_service_tokens,
            count(DISTINCT counterparty_id) FILTER (WHERE amount > 0) AS n_customers,
            median(date_diff('day', issuance_date, payment_date)) FILTER (
                WHERE amount > 0
                  AND document_type IN ('invoice', 'invoiceGroup')
                  AND payment_date IS NOT NULL
                  AND issuance_date IS NOT NULL
                  AND date_diff('day', issuance_date, payment_date) BETWEEN 0 AND 365
            ) AS dso,
            median(date_diff('day', issuance_date, payment_date)) FILTER (
                WHERE amount < 0
                  AND document_type IN ('invoice', 'invoiceGroup')
                  AND payment_date IS NOT NULL
                  AND issuance_date IS NOT NULL
                  AND date_diff('day', issuance_date, payment_date) BETWEEN 0 AND 365
            ) AS dpo
        FROM invoices
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE ar_hhi AS
        WITH ar AS (
            SELECT company_id, counterparty_id, sum(amount) AS vol
            FROM invoices
            WHERE amount > 0 AND document_type IN ('invoice', 'invoiceGroup')
            GROUP BY 1, 2
        ), tot AS (
            SELECT company_id, sum(vol) AS tot FROM ar GROUP BY 1
        )
        SELECT a.company_id, sum(pow(a.vol / nullif(t.tot, 0), 2)) AS hhi_ar
        FROM ar a JOIN tot t USING (company_id)
        WHERE t.tot > 0
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE product_flags AS
        SELECT
            c.company_id,
            max(CASE WHEN lower(coalesce(b.type, '')) = 'tpv' THEN 1 ELSE 0 END) AS has_tpv,
            max(CASE WHEN lower(coalesce(d.type, '')) = 'confirming' THEN 1 ELSE 0 END) AS has_confirming,
            max(CASE WHEN lower(coalesce(d.type, '')) = 'factoring' THEN 1 ELSE 0 END) AS has_factoring
        FROM companies c
        LEFT JOIN banking_products b USING (company_id)
        LEFT JOIN debt_products d USING (company_id)
        GROUP BY 1
        """
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE company_base AS
        SELECT
            c.company_id,
            c.group_id,
            coalesce(t.n_tx, 0) AS n_tx,
            coalesce(t.n_cat_tx, 0) AS n_cat_tx,
            CASE WHEN t.vol_all > 0 THEN t.vol_uncat / t.vol_all END AS uncat_share,
            CASE WHEN t.outflow > 0 THEN t.payroll_out / t.outflow END AS payroll_share,
            CASE WHEN t.vol_cat > 0 THEN t.pos_cash_vol / t.vol_cat END AS pos_cash_share,
            CASE WHEN t.vol_cat > 0 THEN t.payment_vol / t.vol_cat END AS payment_share,
            CASE WHEN t.vol_cat > 0 THEN t.bulk_payment_vol / t.vol_cat END AS bulk_payment_share,
            f.collection_cv,
            f.season_amp,
            f.n_months,
            i.n_invoices,
            CASE WHEN i.n_invoices > 0 THEN i.n_goods_docs * 1.0 / i.n_invoices END AS goods_docs,
            CASE WHEN i.n_invoices > 0 THEN i.n_service_tokens * 1.0 / i.n_invoices END AS service_tokens,
            i.n_customers,
            i.dso,
            i.dpo,
            h.hhi_ar,
            coalesce(p.has_tpv, 0) AS has_tpv,
            coalesce(p.has_confirming, 0) AS has_confirming,
            coalesce(p.has_factoring, 0) AS has_factoring,
            (i.n_invoices IS NOT NULL AND i.n_invoices > 0) AS has_invoices
        FROM companies c
        LEFT JOIN tx_agg t USING (company_id)
        LEFT JOIN flow_shape f USING (company_id)
        LEFT JOIN inv_cycle i USING (company_id)
        LEFT JOIN ar_hhi h USING (company_id)
        LEFT JOIN product_flags p USING (company_id)
        """
    )


def load_panel_overlay() -> dict[str, dict]:
    if not PANEL.exists():
        return {}
    overlay: dict[str, dict] = {}
    with PANEL.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            company_id = row.get("company_id")
            month = row.get("month")
            if not company_id or not month:
                continue
            current = overlay.get(company_id)
            if current is None or month > current["month"]:
                overlay[company_id] = {
                    "month": month,
                    "runway_m": _finite(row.get("runway_m")),
                    "cash_end": _finite(row.get("cash_end")),
                    "dso_panel": _finite(row.get("dso")),
                }
    return overlay


def pivot_shares(connection: duckdb.DuckDBPyConnection) -> dict[str, dict[str, float]]:
    mix: dict[str, dict[str, float]] = defaultdict(dict)
    for row in records(connection, "SELECT company_id, category, share FROM cat_share"):
        share = _finite(row["share"])
        if share is None:
            continue
        mix[row["company_id"]][row["category"]] = share
    return mix


def assemble_rows(connection: duckdb.DuckDBPyConnection) -> list[dict]:
    mix = pivot_shares(connection)
    overlay = load_panel_overlay()
    rows = []
    for base in records(connection, "SELECT * FROM company_base"):
        company_id = base["company_id"]
        shares = mix.get(company_id, {})
        row = dict(base)
        for cat in PROFILE_CATEGORIES:
            row[cat] = shares.get(cat, 0.0 if row["n_cat_tx"] else None)
        extra = overlay.get(company_id, {})
        row["runway_m"] = extra.get("runway_m")
        row["cash_end"] = extra.get("cash_end")
        if row.get("dso") is None:
            row["dso"] = extra.get("dso_panel")
        cv = _finite(row.get("collection_cv"))
        row["collection_recurrence"] = None if cv is None else 1.0 / (1.0 + max(cv, 0.0))
        row["eligible"] = int(row.get("n_cat_tx") or 0) >= MIN_CAT_TX
        rows.append(row)
    rows.sort(key=lambda item: item["company_id"])
    return rows


def mean_rank(row: dict, names: tuple[str, ...], ranked: dict[str, dict[str, float]]) -> float | None:
    company_id = row["company_id"]
    values = [ranked[name][company_id] for name in names if row.get(name) is not None]
    if not values:
        return None
    return sum(values) / len(values)


def classify_kind(rows: list[dict]) -> None:
    eligible = [row for row in rows if row["eligible"]]
    ranked: dict[str, dict[str, float]] = {}
    for name in KIND_GOODS + KIND_SERVICES:
        values = [_finite(row.get(name)) for row in eligible]
        ranks = rank_column(values)
        ranked[name] = {row["company_id"]: ranks[i] for i, row in enumerate(eligible)}
    for row in rows:
        if not row["eligible"]:
            row["business_kind"] = "insuficiente"
            row["goods_score"] = None
            row["service_score"] = None
            row["kind_score"] = None
            continue
        goods = mean_rank(row, KIND_GOODS, ranked)
        services = mean_rank(row, KIND_SERVICES, ranked)
        row["goods_score"] = goods
        row["service_score"] = services
        if goods is None or services is None:
            row["kind_score"] = None
            row["business_kind"] = "mixto"
            continue
        delta = services - goods
        row["kind_score"] = delta
        if abs(delta) < KIND_MARGIN:
            row["business_kind"] = "mixto"
        elif delta > 0:
            row["business_kind"] = "servicio"
        else:
            row["business_kind"] = "producto"


def feature_matrix(rows: list[dict]) -> tuple[list[str], list[list[float]]]:
    companies = [row["company_id"] for row in rows]
    raw: list[list[float | None]] = []
    for row in rows:
        raw.append([_finite(row.get(name)) for name in CLUSTER_FEATURES])
    ranked_cols = [rank_column([row[j] for row in raw]) for j in range(len(CLUSTER_FEATURES))]
    points = [[ranked_cols[j][i] for j in range(len(CLUSTER_FEATURES))] for i in range(len(rows))]
    return companies, points


def name_clusters(points: list[list[float]], assignments: list[int], k: int) -> dict[int, str]:
    """Nombra con las dos categorías de tesorería más altas en percentil.

    El clustering usa DSO, albaranes y flags; el nombre sale solo del mix de
    movimientos, que es lo que un tesorero reconoce.
    """
    name_idx = [i for i, name in enumerate(CLUSTER_FEATURES) if name in PROFILE_CATEGORIES]
    labels: dict[int, str] = {}
    for cluster in range(k):
        members = [points[i] for i, a in enumerate(assignments) if a == cluster]
        if not members:
            labels[cluster] = f"Perfil {cluster + 1}"
            continue
        means = {j: sum(m[j] for m in members) / len(members) for j in name_idx}
        ranked = sorted(means, key=lambda j: means[j], reverse=True)
        names = []
        for j in ranked:
            if means[j] < 0.55 and names:
                break
            names.append(CATEGORY_LABELS[CLUSTER_FEATURES[j]])
            if len(names) == 2:
                break
        labels[cluster] = " + ".join(names) if names else f"Perfil {cluster + 1}"
    seen: dict[str, int] = {}
    for cluster in range(k):
        base = labels[cluster]
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            labels[cluster] = f"{base} ({seen[base]})"
    return labels


def cluster_regimes(rows: list[dict]) -> dict:
    eligible = [row for row in rows if row["eligible"]]
    companies, points = feature_matrix(eligible)
    search = []
    best: KMeansResult | None = None
    for k in K_RANGE:
        assignments, centroids = kmeans(points, k)
        sil = silhouette(points, assignments)
        sizes = dict(Counter(assignments))
        min_share = min(sizes.values()) / len(points)
        candidate = KMeansResult(
            k=k,
            assignments=assignments,
            centroids=centroids,
            labels={},
            silhouette=sil,
            sizes=sizes,
        )
        search.append(
            {
                "k": k,
                "silhouette": sil,
                "min_share": min_share,
                "sizes": sizes,
            }
        )
        if min_share < MIN_CLUSTER_SHARE:
            continue
        if best is None or sil > best.silhouette:
            best = candidate
    if best is None:
        k = 5
        assignments, centroids = kmeans(points, k)
        best = KMeansResult(
            k=k,
            assignments=assignments,
            centroids=centroids,
            labels={},
            silhouette=silhouette(points, assignments),
            sizes=dict(Counter(assignments)),
        )
    best.labels = name_clusters(points, best.assignments, best.k)
    coords = pca_2d(points)
    index = {cid: i for i, cid in enumerate(companies)}
    for row in rows:
        if not row["eligible"]:
            row["regime_id"] = None
            row["regime_label"] = "sin cobertura"
            row["confidence"] = None
            row["pc1"] = None
            row["pc2"] = None
            continue
        i = index[row["company_id"]]
        cluster = best.assignments[i]
        point = points[i]
        dists = [euclidean(point, c) for c in best.centroids]
        ordered = sorted(dists)
        best_d = ordered[0]
        second = ordered[1] if len(ordered) > 1 else ordered[0]
        row["regime_id"] = cluster
        row["regime_label"] = best.labels[cluster]
        row["confidence"] = None if second <= 0 else max(0.0, min(1.0, 1.0 - best_d / second))
        row["pc1"], row["pc2"] = coords[i]
    return {"result": best, "search": search, "n": len(eligible)}


def write_table(rows: list[dict]) -> None:
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "company_id",
        "group_id",
        "business_kind",
        "kind_score",
        "goods_score",
        "service_score",
        "regime_id",
        "regime_label",
        "confidence",
        "n_tx",
        "n_cat_tx",
        "has_invoices",
        "uncat_share",
        "has_tpv",
        "has_confirming",
        "payroll_share",
        "pos_cash_share",
        "dso",
        "dpo",
        "n_customers",
        "hhi_ar",
        "goods_docs",
        "service_tokens",
        "runway_m",
    ]
    with TABLE.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda item: item["company_id"]):
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


def kind_counts(rows: list[dict]) -> Counter:
    return Counter(row["business_kind"] for row in rows)


def pct(part: int, whole: int) -> str:
    if not whole:
        return "—"
    return f"{part / whole:.1%}".replace(".", ",")


def median(values: list[float | None]) -> float | None:
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    mid = len(clean) // 2
    if len(clean) % 2:
        return clean[mid]
    return (clean[mid - 1] + clean[mid]) / 2


def mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def kind_figure(rows: list[dict]) -> go.Figure:
    eligible = [row for row in rows if row["eligible"] and row["goods_score"] is not None]
    colors = {
        "producto": COLORS["blue"],
        "servicio": COLORS["cyan"],
        "mixto": COLORS["amber"],
    }
    figure = go.Figure()
    for kind, color in colors.items():
        subset = [row for row in eligible if row["business_kind"] == kind]
        figure.add_trace(
            go.Scatter(
                x=[row["goods_score"] for row in subset],
                y=[row["service_score"] for row in subset],
                mode="markers",
                name=kind,
                marker=dict(size=7, color=color, opacity=0.7),
                hovertemplate="%{text}<extra></extra>",
                text=[row["company_id"] for row in subset],
            )
        )
    figure.update_layout(
        title="Producto vs servicio · índices 0–1",
        xaxis_title="Huella de producto (pagos, albaranes, TPV, confirming)",
        yaxis_title="Huella de servicio (nómina, cobros regulares, conceptos)",
        xaxis=dict(range=[-0.02, 1.02]),
        yaxis=dict(range=[-0.02, 1.02]),
    )
    return figure


def pca_figure(rows: list[dict]) -> go.Figure:
    clustered = [row for row in rows if row.get("pc1") is not None]
    labels = sorted({row["regime_label"] for row in clustered})
    palette = [COLORS["blue"], COLORS["cyan"], COLORS["green"], COLORS["amber"], COLORS["red"], "#7c3aed", "#0f766e"]
    figure = go.Figure()
    for i, label in enumerate(labels):
        subset = [row for row in clustered if row["regime_label"] == label]
        figure.add_trace(
            go.Scatter(
                x=[row["pc1"] for row in subset],
                y=[row["pc2"] for row in subset],
                mode="markers",
                name=label,
                marker=dict(size=7, color=palette[i % len(palette)], opacity=0.75),
                hovertemplate="%{text}<extra></extra>",
                text=[f"{row['company_id']}<br>{row['business_kind']}" for row in subset],
            )
        )
    figure.update_layout(
        title="Régimen operativo · proyección PCA",
        xaxis_title="Componente 1",
        yaxis_title="Componente 2",
    )
    return figure


def silhouette_figure(search: list[dict]) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=[row["k"] for row in search],
            y=[row["silhouette"] for row in search],
            marker_color=COLORS["blue"],
            text=[f"{row['silhouette']:.3f}" for row in search],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="k=%{x}<br>silueta=%{y:.3f}<extra></extra>",
        )
    )
    figure.update_layout(title="Silueta por número de clústeres", xaxis_title="k", yaxis_title="Silueta")
    return figure


def kind_profile_rows(rows: list[dict]) -> list[list]:
    out = []
    for kind in ("producto", "servicio", "mixto", "insuficiente"):
        subset = [row for row in rows if row["business_kind"] == kind]
        if not subset:
            continue
        med_goods = median([row.get("goods_docs") for row in subset])
        med_dso = median([row.get("dso") for row in subset])
        out.append(
            [
                kind,
                fmt(len(subset), 0),
                f"{median([row.get('payroll_share') for row in subset]) or 0:.1%}".replace(".", ","),
                f"{median([row.get('pos_cash_share') for row in subset]) or 0:.1%}".replace(".", ","),
                (fmt(med_dso, 0) + " d") if med_dso is not None else "—",
                (fmt(med_goods * 100, 1) + " %") if med_goods is not None else "—",
                fmt(sum(int(row.get("has_tpv") or 0) for row in subset), 0),
            ]
        )
    return out


def regime_profile_rows(rows: list[dict], labels: dict[int, str]) -> list[list]:
    out = []
    for cluster, label in sorted(labels.items(), key=lambda item: item[0]):
        subset = [row for row in rows if row.get("regime_id") == cluster]
        n = len(subset)
        kinds = Counter(row["business_kind"] for row in subset)
        product_share = kinds.get("producto", 0) / n if n else 0
        service_share = kinds.get("servicio", 0) / n if n else 0
        med_runway = median([row.get("runway_m") for row in subset])
        med_dso = median([row.get("dso") for row in subset])
        out.append(
            [
                html.escape(label),
                fmt(n, 0),
                f"{product_share:.0%} prod · {service_share:.0%} serv".replace(".", ","),
                f"{median([row.get('payroll_share') for row in subset]) or 0:.1%}".replace(".", ","),
                f"{median([row.get('pos_cash_share') for row in subset]) or 0:.1%}".replace(".", ","),
                fmt(med_dso, 0) if med_dso is not None else "—",
                f"{med_runway:.2f} m" if med_runway is not None else "—",
                f"{mean([row.get('confidence') for row in subset]) or 0:.2f}".replace(".", ","),
            ]
        )
    return out


def group_homogeneity(rows: list[dict]) -> tuple[int, int, float]:
    by_group: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.get("regime_id") is None:
            continue
        by_group[row["group_id"]].append(row["regime_label"])
    multi = {g: labels for g, labels in by_group.items() if len(labels) >= 2}
    if not multi:
        return 0, 0, 0.0
    same = sum(1 for labels in multi.values() if len(set(labels)) == 1)
    return same, len(multi), same / len(multi)


def tpv_check(rows: list[dict]) -> tuple[int, int]:
    tpv = [row for row in rows if int(row.get("has_tpv") or 0) == 1 and row["eligible"]]
    ok = sum(1 for row in tpv if row["business_kind"] in {"producto", "mixto"})
    return ok, len(tpv)


def payroll_check(rows: list[dict]) -> tuple[int, int]:
    heavy = [
        row
        for row in rows
        if row["eligible"]
        and (row.get("payroll_share") or 0) >= 0.25
        and (row.get("goods_docs") or 0) < 0.01
        and int(row.get("has_tpv") or 0) == 0
    ]
    ok = sum(1 for row in heavy if row["business_kind"] in {"servicio", "mixto"})
    return ok, len(heavy)


def build_report(rows: list[dict], clustering: dict) -> str:
    result: KMeansResult = clustering["result"]
    search = clustering["search"]
    n_all = len(rows)
    n_fit = clustering["n"]
    counts = kind_counts(rows)
    same, multi, _homo = group_homogeneity(rows)
    tpv_ok, tpv_n = tpv_check(rows)
    pay_ok, pay_n = payroll_check(rows)
    n_invoices = sum(1 for row in rows if row.get("has_invoices"))
    n_uncat = mean([row.get("uncat_share") for row in rows]) or 0
    conf = mean([row.get("confidence") for row in rows if row.get("confidence") is not None]) or 0
    k_rows = [
        [
            fmt(item["k"], 0),
            f"{item['silhouette']:.3f}".replace(".", ","),
            f"{item['min_share']:.1%}".replace(".", ","),
            ", ".join(str(item["sizes"].get(i, 0)) for i in range(item["k"])),
        ]
        for item in search
    ]
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sector inferido · huella de tesorería</title>
  <script>{get_plotlyjs()}</script>
  <style>{CSS}</style>
</head>
<body>
  <aside class="sidebar">
    <div class="brand"><span class="brand-mark">X</span><div><b>X-Ray</b><small>Sector inferido</small></div></div>
    <nav>
      <a href="#por-que">Por qué</a>
      <a href="#cobertura">Cobertura</a>
      <a href="#producto-servicio">Producto o servicio</a>
      <a href="#regimen">Régimen operativo</a>
      <a href="#caja">Régimen y caja</a>
      <a href="#limites">Límites</a>
    </nav>
    <p class="side-note">Sin NACE. k={result.k} · silueta {result.silhouette:.3f}. No entra al score.</p>
  </aside>
  <main>
    <header class="hero">
      <div class="eyebrow">HackSpain 2026 · análisis</div>
      <h1>El dataset no trae sector.<br><em>La tesorería sí deja huella.</em></h1>
      <p>1.286 empresas, cero etiquetas de industria. Inferimos dos cosas que un prestamista puede usar: si vive de vender producto o de prestar un servicio, y el régimen de cobros y pagos con el que opera. Caja y runway no entran: no queremos agrupar empresas enfermas.</p>
      <div class="hero-meta">
        <span>{fmt(n_fit, 0)} empresas con huella</span>
        <span>{fmt(n_all - n_fit, 0)} sin cobertura</span>
        <span>k = {result.k}</span>
        <span>margen producto/servicio {KIND_MARGIN:.0%}</span>
      </div>
    </header>

    <section class="section" id="por-que">
      <div class="section-head"><span>01</span><div><h2>Por qué inferir y no inventar CNAE</h2><p>Embat pide modular la criticidad de la liquidez por régimen. Capchase cruza ese régimen con el plazo del préstamo.</p></div></div>
      <div class="callout insight"><b>No hay sector en los ficheros.</b> <code>companies.csv</code> trae país (vacío en el 82 %), moneda y ERP. El k-means de caja ya agrupaba por mix de categorías; aquí se añade el corte producto/servicio y señales de ciclo (DSO, albaranes, TPV) que ese recuadro no usaba.</div>
      <div class="grid two">
        <div class="panel narrative"><h3>Qué sale</h3>
          <ul>
            <li><b>Producto vs servicio vs mixto</b> — índice explícito, no caja negra. Pagos a proveedor, albaranes, TPV y confirming empujan a producto; nómina, cobros regulares y conceptos de servicio, a servicio.</li>
            <li><b>Régimen operativo</b> — k-means sobre la huella rank-transformada. El nombre son las dos señales que más sobresalen, en lenguaje de prestamista.</li>
            <li>Tabla persistida en <code>data/processed/company_sector.csv</code> para usarla después en umbrales de runway. Esta entrega no toca el score.</li>
          </ul>
        </div>
        <div class="panel narrative"><h3>Qué no entra</h3>
          <ul>
            <li>Runway, caja negativa, drawdown: son salud, no sector.</li>
            <li>Nombres tipo Alimentación o Metalurgia: el texto de facturas está anonimizado y fingir CNAE es un demo, no un hallazgo.</li>
            <li>País y ERP: observabilidad, no industria.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="section" id="cobertura">
      <div class="section-head"><span>02</span><div><h2>Cobertura de la huella</h2><p>Hace falta un mínimo de movimientos categorizados. El resto queda marcado, no imputado.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Con huella (≥{MIN_CAT_TX} tx)</small><strong>{fmt(n_fit, 0)}</strong><span>{pct(n_fit, n_all)} de las empresas</span></div>
        <div class="kpi"><small>Con facturas ERP</small><strong>{fmt(n_invoices, 0)}</strong><span>DSO, albaranes y clientes solo aquí</span></div>
        <div class="kpi"><small>Sin categorizar</small><strong>{n_uncat:.1%}</strong><span>volumen medio uncategorized</span></div>
        <div class="kpi"><small>Sin cobertura</small><strong>{fmt(n_all - n_fit, 0)}</strong><span>régimen = sin cobertura</span></div>
      </div>
      <div class="callout warning"><b>El hueco no es un sector.</b> Quien no llega a {MIN_CAT_TX} movimientos categorizados no se fuerza a un clúster. En la tabla sale <code>insuficiente</code> / <code>sin cobertura</code>. Uncategorized es cobertura, no salud.</div>
    </section>

    <section class="section" id="producto-servicio">
      <div class="section-head"><span>03</span><div><h2>Producto o servicio</h2><p>Separación básica: dos índices 0–1 y un margen de {KIND_MARGIN:.0%} para no fingir certeza en el centro.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>Producto</small><strong>{fmt(counts.get("producto", 0), 0)}</strong><span>{pct(counts.get("producto", 0), n_all)}</span></div>
        <div class="kpi"><small>Servicio</small><strong>{fmt(counts.get("servicio", 0), 0)}</strong><span>{pct(counts.get("servicio", 0), n_all)}</span></div>
        <div class="kpi"><small>Mixto</small><strong>{fmt(counts.get("mixto", 0), 0)}</strong><span>empate dentro del margen</span></div>
        <div class="kpi"><small>Insuficiente</small><strong>{fmt(counts.get("insuficiente", 0), 0)}</strong><span>sin huella mínima</span></div>
      </div>
      <div class="panel">{chart_html(kind_figure(rows), 460)}</div>
      <div class="grid two">
        <div class="panel"><h3>Perfil de cada lado</h3>
          {table(["Tipo", "Empresas", "Nómina", "TPV/efectivo", "DSO", "Albaranes", "Con TPV"], kind_profile_rows(rows))}
          <p class="caption">Medianas. Nómina y TPV son cuotas de tesorería; albaranes, cuota de documentos ERP.</p>
        </div>
        <div class="panel narrative"><h3>Cómo se corta</h3>
          <ul>
            <li>Cada señal pasa a percentil dentro de la cohorte con huella. Producto = media de pagos, pagos masivos, TPV/efectivo, albaranes/pedidos y confirming. Servicio = media de peso de nómina, recurrencia de cobros y conceptos de servicio.</li>
            <li>Si |servicio − producto| &lt; {KIND_MARGIN:.0%} → mixto. Un supermercado con plantilla y un holding de tesorería no son CNAE, son mixtos.</li>
            <li>Check TPV: {tpv_ok} de {tpv_n} empresas con terminal caen en producto o mixto. Check nómina alta sin albaranes: {pay_ok} de {pay_n} caen en servicio o mixto.</li>
          </ul>
        </div>
      </div>
    </section>

    <section class="section" id="regimen">
      <div class="section-head"><span>04</span><div><h2>Régimen operativo</h2><p>K-means determinista sobre la huella en percentiles. k se elige por silueta, descartando particiones con un clúster &lt; {MIN_CLUSTER_SHARE:.0%}.</p></div></div>
      <div class="kpis compact-kpis">
        <div class="kpi"><small>k elegido</small><strong>{result.k}</strong><span>silueta {result.silhouette:.3f}</span></div>
        <div class="kpi"><small>Clúster más pequeño</small><strong>{fmt(min(result.sizes.values()), 0)}</strong><span>{min(result.sizes.values()) / n_fit:.1%} de la huella</span></div>
        <div class="kpi"><small>Grupos homogéneos</small><strong>{pct(same, multi)}</strong><span>{fmt(same, 0)} de {fmt(multi, 0)} grupos con ≥2 sociedades</span></div>
        <div class="kpi"><small>Confianza media</small><strong>{conf:.2f}</strong><span>1 − d1/d2 al centroide</span></div>
      </div>
      <div class="grid two">
        <div class="panel">{chart_html(silhouette_figure(search), 360)}</div>
        <div class="panel"><h3>Búsqueda de k</h3>
          {table(["k", "Silueta", "Mín. tamaño", "Tamaños"], k_rows)}
          <p class="caption">Inicialización farthest-point, 60 iteraciones, misma transformación por rango que el k-means de caja.</p>
        </div>
      </div>
      <div class="panel">{chart_html(pca_figure(rows), 480)}</div>
      <div class="panel"><h3>Qué sobresale en cada régimen</h3>
        {table(["Régimen", "Empresas", "Producto / servicio", "Nómina", "TPV/efectivo", "DSO", "Runway*", "Confianza"], regime_profile_rows(rows, result.labels))}
        <p class="caption">* El runway se mira después, no se usó para agrupar. Sirve para ver si el régimen cambia el colchón típico —la tesis de Embat— sin circularidad.</p>
      </div>
      <div class="callout"><b>Los nombres no son CNAE.</b> Son las dos señales más sobre-representadas frente al conjunto. Un régimen “liquidación TPV + efectivo” es comercio de cobro inmediato; “pagos a proveedor + ciclo de cobro” es un mayorista. El prestamista necesita eso, no el código de actividad.</div>
    </section>

    <section class="section" id="caja">
      <div class="section-head"><span>05</span><div><h2>El régimen cambia el colchón, no el score</h2><p>Runway mediano por clúster, leído a posteriori desde el panel mensual ya construido.</p></div></div>
      <div class="callout insight"><b>Para el score, más adelante.</b> Si dos regímenes con el mismo runway no tienen la misma tasa de tensión, el umbral global está mal. Esa prueba (E1/E3) no vive en este informe: primero hace falta la etiqueta, que es lo que se persiste ahora.</div>
      <div class="panel narrative">
        <h3>Cómo leerlo</h3>
        <ul>
          <li>Un mayorista a 90 días puede operar con menos meses de caja que un negocio de cobro TPV: el circulante está en la factura, no en la cuenta. El mismo percentil de runway no es la misma criticidad.</li>
          <li>La homogeneidad de grupos ({pct(same, multi)}) no es un objetivo. Un holding puede mezclar tesorería y operativa; forzar el mismo régimen contaminaría la huella.</li>
          <li><code>operating_regime</code> sigue siendo overlay en el catálogo de pesos: no suma puntos, fija el listón.</li>
        </ul>
      </div>
    </section>

    <section class="section" id="limites">
      <div class="section-head"><span>06</span><div><h2>Límites</h2><p>Qué no afirma este clustering.</p></div></div>
      <div class="limitations">
        <article><b>No es NACE</b><p>No hay etiqueta externa. Los nombres son huella operativa. Un demo que ponga “Alimentación” estaría inventando.</p></article>
        <article><b>Texto anonimizado</b><p>Los tokens de factura (servicio, suscripción) son corroboración débil. El eje duro es tesorería y tipo documental.</p></article>
        <article><b>Sin categorizar</b><p>Una de cada cuatro unidades de volumen no tiene categoría. Eso recorta la huella; no se imputa a cobros o pagos.</p></article>
        <article><b>No es el score</b><p>Esta entrega no cambia umbrales ni el frontend. La tabla está lista para el overlay de runway cuando se mida contra E1/E3.</p></article>
      </div>
    </section>
    <footer>HackSpain 2026 · X-Ray · generado desde <code>analysis/cluster_sector.py</code> · {n_fit} empresas clusterizadas</footer>
  </main>
</body>
</html>"""


def main() -> None:
    connection = duckdb.connect()
    connection.execute("PRAGMA threads=4")
    attach(connection, DATA)
    print("Building company footprint…", flush=True)
    setup_features(connection)
    rows = assemble_rows(connection)
    classify_kind(rows)
    clustering = cluster_regimes(rows)
    write_table(rows)
    OUTPUT.write_text(build_report(rows, clustering), encoding="utf-8")
    counts = kind_counts(rows)
    result: KMeansResult = clustering["result"]
    print(
        f"kind {dict(counts)} | k={result.k} silhouette={result.silhouette:.3f} "
        f"| wrote {OUTPUT} ({OUTPUT.stat().st_size / 1_000:.0f} KB) and {TABLE}"
    )


if __name__ == "__main__":
    main()
