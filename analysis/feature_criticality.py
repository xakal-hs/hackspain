#!/usr/bin/env python3
"""Analiza las features usables de ``data/`` y su criticidad segun ``context/scoring.md``.

El catalogo no inventa features: mapea los campos reales de los CSV (via la capa de
mapeo en ``src/mapping``) a la pregunta de prestamista que responde cada uno, y las
ordena con la criticidad del marco de scoring (critica / alta / media / bache / no es
salud). Cada fila se enriquece con evidencia calculada en DuckDB sobre los datos.

Genera un artefacto autocontenido que se abre sin servidor:
``analysis/features_analisis_automatico.html``.
"""

from __future__ import annotations

import html
import sys
from datetime import datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = ROOT / "analysis" / "features_analisis_automatico.html"
_SRC = ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from mapping.load import attach  # noqa: E402

AS_OF = "2026-09-01"

# ---------------------------------------------------------------------------
# Catalogo de criticidad. La clave es la pregunta de consumidor -> empresa de
# context/scoring.md. El orden de los grupos reproduce la prioridad del marco:
# primero la caja que se evapora, despues cobros, pagos y deuda.
# ---------------------------------------------------------------------------

CRITICALITY = {
    "critica": ("Crítica", "#e5484d", "La caja disponible se evapora en poco tiempo."),
    "alta": ("Alta", "#f59e0b", "Deja de cobrar de forma persistente o paga solo con deuda nueva."),
    "media": ("Media", "#1463ff", "DSO o DPO se mueven un poco."),
    "bache": ("Bache", "#27b3c2", "Un mal mes con recuperación."),
    "cobertura": ("No es salud", "#64748b", "Hueco de observabilidad: cobertura, no riesgo."),
}

# Cada pregunta: (id, titulo consumidor, traduccion empresa, fuente de datos)
QUESTIONS = [
    (
        "caja",
        "¿Se le acaba el dinero de la cuenta en pocas semanas?",
        "Caja disponible que se evapora",
        "balances · transactions (reconstrucción hacia atrás)",
    ),
    (
        "cobro",
        "¿Cobra tarde o deja de cobrar?",
        "Medio de cobro / DSO",
        "invoices · transactions · counterparty_id",
    ),
    (
        "pago",
        "¿Paga cada vez más tarde a quien le fía?",
        "Medio de pago / DPO",
        "invoices · transactions",
    ),
    (
        "sueldo",
        "¿El sueldo se corta o es irregular?",
        "Cobros que caen o se vuelven erráticos",
        "transactions (collection, salary)",
    ),
    (
        "tarjeta",
        "¿Vive al límite de la tarjeta?",
        "Líneas de crédito agotadas",
        "debt_products · banking_products",
    ),
    (
        "prestamo",
        "¿Pide un préstamo para tapar el agujero?",
        "Deuda nueva mientras la caja cae",
        "debt_products · debt_schedule_config · transactions",
    ),
    (
        "mentira",
        "¿Miente o no se deja ver las cuentas?",
        "Cobertura / observabilidad",
        "companies · groups · transactions.accounting_status",
    ),
    (
        "bache",
        "¿Fue un gasto puntual o algo estructural?",
        "Bache frente a caída estructural",
        "transactions · invoices (notas de crédito)",
    ),
]

# Pregunta de consumidor a la que responde cada feature.
QUESTION_OF = {
    "cash_end": "caja", "burn_rate": "caja", "runway": "caja", "cash_trend_3m": "caja",
    "liquidity_available": "caja",
    "collections_trend": "cobro", "lost_share": "cobro", "overdue_ar": "cobro",
    "overdue_90_ar": "cobro", "ar_late_share": "cobro", "hhi_ar": "cobro",
    "customer_trend": "cobro",
    "ap_late_share": "pago", "ap_overdue_ratio": "pago",
    "payroll_burden": "sueldo", "inflow_regularity": "sueldo", "activity_trend": "sueldo",
    "dormant": "sueldo",
    "lc_util": "tarjeta", "debt_utilization": "tarjeta", "factoring_confirming": "tarjeta",
    "debt_service_burden": "prestamo", "new_debt_vs_cash": "prestamo",
    "schedule_pressure": "prestamo", "interest_rate": "prestamo",
    "erp_connected": "mentira", "uncategorized_share": "mentira", "reconciliation": "mentira",
    "history_length": "mentira", "currency_exposure": "mentira", "internal_flow": "mentira",
    "refunds": "bache", "credit_notes": "bache", "tax_seasonality": "bache",
    "transfer_dependency": "bache",
}

# name, plain, source, crit, dir, viewers, evidence, note
CATALOG = [
    # --- Caja -----------------------------------------------------------------
    ("cash_end", "El dinero que le queda en la cuenta", "balances.balance/available + roll-back con transactions", "critica",
     "Más caja = mejor", "Banco, CFO, Embat", "balance_negative_share",
     "balances.csv es solo la foto del 2026-09-01; el histórico se reconstruye hacia atrás por producto y divisa."),
    ("burn_rate", "Lo que gasta al mes", "transactions (salidas, ventana 3/12m)", "critica",
     "Menos quema = mejor", "Banco, CFO", "internal_share",
     "Hay que excluir traspasos internos e intragrupo antes de medir la quema real."),
    ("runway", "Meses que aguanta con el dinero que tiene", "cash_end / burn (signo × log)", "critica",
     "Más meses = mejor", "Banco, CFO, Embat", "checking_companies",
     "Base de gasto robusta: máx(3m, 12m) para que encogerse no infle el runway (D09)."),
    ("cash_trend_3m", "Si la cuenta se está vaciando", "Δcash_end a 3 meses", "critica",
     "Caja al alza = mejor", "Banco, Embat", "balance_negative_companies",
     "Es la señal que el marco exige que pese más que un DSO que empeora 3 días."),
    ("liquidity_available", "Crédito que aún puede disponer", "debt_products.liquidity", "critica",
     "Más disponible = mejor", "Banco", "lc_companies",
     "Casi nunca reportado por el proveedor: tratarlo como cobertura, no como cero."),
    # --- Cobro / AR -----------------------------------------------------------
    ("collections_trend", "Si le entra menos dinero de clientes", "transactions categorías collection/bulk_collection/pos", "alta",
     "Cobros crecientes = mejor", "Banco, CFO, Embat", "collection_share",
     "Es el 'sueldo' de la empresa: una caída persistente anticipa el apagado."),
    ("lost_share", "La facturación de clientes que ya no le compran", "invoices AR (counterparty_id, 3 vs 3-12m)", "alta",
     "Menos perdido = mejor", "Banco, Aseguradora", "ar_issued_share",
     "La señal más temprana de apagado y declive (D11, D24)."),
    ("overdue_ar", "Facturas de clientes vencidas y sin cobrar", "invoices pending_amount≠0 con due_date pasado (lado AR)", "alta",
     "Menos vencido = mejor", "Banco, Aseguradora, CFO", "overdue_ar_bn",
     "Impagada = pending_amount≠0 y status≠paid; payment_date no es fiable (D05)."),
    ("overdue_90_ar", "Lo vencido hace más de 90 días", "invoices AR con due_date > 2m respecto al cierre", "alta",
     "Menos vencido = mejor", "Banco, Aseguradora", "overdue_ar_share",
     "Separa mora reciente de un stock que ya no se cobra."),
    ("ar_late_share", "Cuánto tarda en cobrar (DSO)", "invoices due_date vs payment_date (ventana 3m)", "media",
     "Cobrar antes = mejor", "CFO, Aseguradora", "late_share_ar",
     "Unos días más no debe dominar el ranking; la caja manda."),
    ("hhi_ar", "Si depende de pocos clientes", "invoices AR (HHI 6m por counterparty_id)", "alta",
     "Más diversificado = mejor", "Aseguradora, Banco", "n_counterparties",
     "Clave para la aseguradora: concentración de contraparte = prima de impago."),
    ("customer_trend", "Si factura a más o menos clientes", "invoices AR (nº contrapartes 3m vs 12m)", "alta",
     "Más clientes = mejor", "CFO, Embat", "ar_counterparties",
     "Amplitud de cartera: contratar a menos clientes avisa antes que la caja."),
    # --- Pago / AP ------------------------------------------------------------
    ("ap_late_share", "Cuánto tarda en pagar a proveedores (DPO)", "invoices due_date vs payment_date (ventana 3m)", "media",
     "Pagar en plazo = mejor", "CFO", "late_share_ap",
     "Pagar tarde puede ser tensión de caja o abuso de posición; se lee con la caja."),
    ("ap_overdue_ratio", "Lo que debe y ya venció", "invoices AP vencido / salidas medias 3m", "media",
     "Menos vencido = mejor", "Banco, CFO", "overdue_ap_bn",
     "Con la caja cayendo, el vencido a proveedores es señal de que no llega."),
    ("payroll_burden", "Cuánto de lo que entra se va en nóminas", "transactions salary+social_security / entradas", "alta",
     "Menos carga = mejor", "Banco, CFO", "salary_share",
     "Coste rígido: si no se cubre con cobros, la empresa vive de deuda o de caja."),
    # --- Sueldo / regularidad -------------------------------------------------
    ("inflow_regularity", "Si el dinero entra de forma irregular", "transactions net flow semidesviación a la baja 6m", "media",
     "Más estable = mejor", "Banco, CFO", "active_company_share",
     "Cuenta caótica = gasto impredecible; se ancla al gasto, no a la caja (D25)."),
    ("activity_trend", "Si se mueve menos dinero que antes", "transactions nº de movimientos 3m vs 12m", "alta",
     "Más actividad = mejor", "Banco, Embat", "active_company_share",
     "La caída de actividad precede al apagado; es un lead indicator de cierre."),
    ("dormant", "Meses seguidos sin movimientos", "transactions contador causal months_since_last_tx", "alta",
     "Operar = mejor", "Banco, Embat", "active_company_share",
     "Sin movimientos, la regla de negocio limita el score aunque no haya impago."),
    # --- Tarjeta / líneas -----------------------------------------------------
    ("lc_util", "Cuánto tiene dispuesto de su póliza", "debt_products.outstanding / granted (lineofcredit)", "alta",
     "Menos dispuesto = mejor", "Banco", "lc_util_median",
     "Vivir al límite de la tarjeta: dispuesto cerca del concedido es señal de ahogo."),
    ("debt_utilization", "Cuánto de su deuda total está viva", "debt_products outstanding/granted (todos los tipos)", "alta",
     "Menos utilización = mejor", "Banco", "debt_util_median",
     "granted/outstanding vienen con signo sucio; la capa de mapeo pasa a pasivo canónico."),
    ("factoring_confirming", "Cuánto anticipa o confirma con bancos", "debt_products type factoring/confirming", "media",
     "Menos dependencia = mejor", "Banco, CFO", "debt_companies",
     "Uso intensivo de factoring puede ser financiar el circulante que no cobra."),
    # --- Préstamo para tapar ------------------------------------------------
    ("debt_service_burden", "Lo que paga de cuotas sobre lo que ingresa", "transactions debt_repayment+interest / entradas", "alta",
     "Menos carga = mejor", "Banco", "debt_repay_share",
     "Pagar deuda con deuda nueva es la tarjeta que tapa el agujero."),
    ("new_debt_vs_cash", "Pide crédito nuevo mientras la caja cae", "debt_products granted por fecha vs Δcash", "alta",
     "No financiar el agujero = mejor", "Banco", "debt_companies",
     "La foto de deuda es final; proyectarla hacia atrás filtra información, se usa con cuidado (D11)."),
    ("schedule_pressure", "Cuánto le vence próximamente", "debt_schedule_config next_payment_date, total_periods", "alta",
     "Menos vencimiento próximo = mejor", "Banco, CFO", "schedule_rows",
     "Cuotas y calendario contractual: la caja tiene que llegar a cada vencimiento."),
    ("interest_rate", "El interés que le cobran", "debt_schedule_config annual_interest_rate_or_spread", "media",
     "Menos coste = mejor", "Banco", "schedule_companies",
     "El coste financiero anticipa tensión si el margen es estrecho."),
    # --- Observabilidad -------------------------------------------------------
    ("erp_connected", "Si deja ver sus facturas", "companies.erp / groups.erp o presencia de invoices", "cobertura",
     "Con ERP = más cobertura, no más salud", "Embat, Banco", "erp_share",
     "ERP ausente es cobertura, no riesgo: baja la confianza, no el nivel."),
    ("uncategorized_share", "Cuánto movimiento no está etiquetado", "transactions.category = uncategorized", "cobertura",
     "Menos huecos = más cobertura", "Embat", "uncat_share",
     "Una cuarta parte de los movimientos entra sin categoría: no imputar salud a ese hueco."),
    ("reconciliation", "Si lleva la contabilidad al día", "transactions.accounting_status", "cobertura",
     "Conciliado = más cobertura", "Embat, CFO", "recon_share",
     "Solo una quinta parte figura como conciliación completada; es proceso, no solvencia."),
    ("history_length", "Cuánto tiempo lleva en la plataforma", "companies.created_at / products.created_at", "cobertura",
     "Más historia = más cobertura", "Embat", "history_share",
     "Historia corta: percentiles congelados, neutro y confianza publicada (D16, D17)."),
    ("currency_exposure", "Cuánto mueve en otra divisa", "transactions/product currency vs company.currency, exchange_rate", "cobertura",
     "Neutro: exige conversión", "CFO, Embat", "currency_count",
     "No agregar sin conversión justificada; hay filas con fx=1 o 0 corregidas con tipo real (D03)."),
    ("internal_flow", "Traspasos entre sus propias cuentas", "transactions pares mismo día/importe opuesto (+ intragrupo)", "cobertura",
     "Neutro: hay que excluirlo", "Embat", "internal_share",
     "La categoría transfer es ~19 % del volumen; los pares internos reales (misma empresa/grupo) llegan al 26,8 % (D04)."),
    # --- Bache ---------------------------------------------------------------
    ("refunds", "Reembolsos y devoluciones", "transactions collection_refund / payment_refund", "bache",
     "Menos devoluciones = mejor", "CFO, Embat", "refund_share",
     "Pico puntual no es deterioro estructural: se separa con la trayectoria."),
    ("credit_notes", "Notas de crédito emitidas", "invoices document_type=note/refund", "bache",
     "Menos = mejor", "Aseguradora", "credit_note_share",
     "Puede revertir facturación ya emitida; se lee aparte del declive."),
    ("tax_seasonality", "Impuestos trimestrales", "transactions category=tax (ene/abr/jul/oct)", "bache",
     "Neutro dentro del trimestre", "CFO, Embat", "tax_share",
     "La estacionalidad se absorbe con ventanas de 6/12m (D08), no como deterioro."),
    ("transfer_dependency", "Vive de que le transfieran dinero", "transactions categoría transfer / entradas", "bache",
     "Menos dependencia = mejor", "Banco, CFO", "transfer_share",
     "Depender de transferencias del grupo disfraza de cobro lo que no es negocio."),
]

# Evidencia: nombre -> (etiqueta, SQL). Se calcula una vez y se reutiliza.
EVIDENCE_SQL = {
    "companies_total": ("Empresas en el dataset", "SELECT count(*) FROM companies", "int"),
    "groups_total": ("Grupos empresariales", "SELECT count(*) FROM groups", "int"),
    "currency_count": ("Divisas distintas de empresa", "SELECT count(DISTINCT currency) FROM companies", "int"),
    "erp_share": ("Empresas con ERP", "SELECT 100.0*count(*) FILTER (WHERE erp IS NOT NULL)/count(*) FROM companies", "pct"),
    "invoices_share": ("Empresas con facturas ERP", "SELECT 100.0*count(DISTINCT company_id)/(SELECT count(*) FROM companies) FROM invoices", "pct"),
    "balance_negative_share": ("Productos con saldo negativo (foto final)", "SELECT 100.0*count(*) FILTER (WHERE balance<0)/count(*) FROM balances", "pct"),
    "balance_negative_companies": ("Empresas con algún saldo negativo", "SELECT count(DISTINCT company_id) FROM balances WHERE balance<0", "int"),
    "collection_share": ("Empresas que cobran (categoría collection)", "SELECT count(DISTINCT company_id) FROM transactions WHERE category IN ('collection','bulk_collection','pos_settlement','cash_settlement','cash_settlements')", "int"),
    "salary_share": ("Empresas con nóminas registradas", "SELECT count(DISTINCT company_id) FROM transactions WHERE category IN ('salary','social_security')", "int"),
    "debt_repay_share": ("Empresas pagando deuda (categoría)", "SELECT count(DISTINCT company_id) FROM transactions WHERE category IN ('debt_repayment','interest_charge')", "int"),
    "active_company_share": ("Empresas con movimientos en 24m", "SELECT count(DISTINCT company_id) FROM transactions", "int"),
    "checking_companies": ("Empresas con cuenta corriente conectada", "SELECT count(DISTINCT company_id) FROM banking_products WHERE type='checking'", "int"),
    "ar_counterparties": ("Clientes distintos en facturas emitidas", "SELECT count(DISTINCT counterparty_id) FROM invoices WHERE amount>0 AND counterparty_id IS NOT NULL", "int"),
    "debt_companies": ("Empresas con producto de deuda", "SELECT count(DISTINCT company_id) FROM debt_products", "int"),
    "lc_companies": ("Empresas con línea de crédito", "SELECT count(DISTINCT company_id) FROM debt_products WHERE type='lineofcredit'", "int"),
    "schedule_rows": ("Préstamos con calendario contractual", "SELECT count(*) FROM debt_schedule_config", "int"),
    "schedule_companies": ("Empresas con calendario de deuda", "SELECT count(DISTINCT company_id) FROM debt_schedule_config", "int"),
    "debt_util_median": ("Utilización mediana de deuda (outstanding/granted)", "SELECT 100.0*median(abs(outstanding)/nullif(abs(granted),0)) FROM debt_products WHERE granted<>0", "pct"),
    "lc_util_median": ("Utilización mediana de póliza", "SELECT 100.0*median(abs(outstanding)/nullif(abs(granted),0)) FROM debt_products WHERE type='lineofcredit' AND granted<>0", "pct"),
    "overdue_ar_bn": ("Facturación AR vencida y abierta (miles de millones)", "SELECT sum(abs(pending_amount))/1e9 FROM invoices WHERE amount>0 AND pending_amount<>0 AND status<>'paid'", "bn"),
    "overdue_ap_bn": ("Facturación AP vencida y abierta (miles de millones)", "SELECT sum(abs(pending_amount))/1e9 FROM invoices WHERE amount<0 AND pending_amount<>0 AND status<>'paid'", "bn"),
    "overdue_ar_share": ("Peso del AR vencido sobre el AR emitido", "SELECT 100.0*(SELECT sum(abs(pending_amount)) FROM invoices WHERE amount>0 AND pending_amount<>0 AND status<>'paid')/(SELECT sum(abs(amount)) FROM invoices WHERE amount>0)", "pct"),
    "ar_issued_share": ("Peso de la facturación AR sobre el total ERP", "SELECT 100.0*sum(abs(amount)) FILTER (WHERE amount>0)/sum(abs(amount)) FROM invoices", "pct"),
    "ap_issued_share": ("Peso de la facturación AP sobre el total ERP", "SELECT 100.0*sum(abs(amount)) FILTER (WHERE amount<0)/sum(abs(amount)) FROM invoices", "pct"),
    "n_counterparties": ("Contrapartes distintas en facturas", "SELECT count(DISTINCT counterparty_id) FROM invoices WHERE counterparty_id IS NOT NULL", "int"),
    "uncat_share": ("Movimientos sin categoría", "SELECT 100.0*count(*) FILTER (WHERE category IS NULL OR lower(category) IN ('-','uncategorized'))/count(*) FROM transactions", "pct"),
    "recon_share": ("Transacciones conciliadas", "SELECT 100.0*count(*) FILTER (WHERE accounting_status='RECONCILIATION_COMPLETED')/count(*) FROM transactions", "pct"),
    "internal_share": ("Volumen en transferencias internas (categoría)", "SELECT 100.0*sum(abs(amount)) FILTER (WHERE category='transfer')/sum(abs(amount)) FROM transactions", "pct"),
    "transfer_share": ("Peso de la categoría transfer sobre las entradas", "SELECT 100.0*sum(amount) FILTER (WHERE category='transfer' AND amount>0)/sum(amount) FILTER (WHERE amount>0) FROM transactions", "pct"),
    "refund_share": ("Movimientos de reembolso", "SELECT 100.0*count(*) FILTER (WHERE category IN ('collection_refund','payment_refund'))/count(*) FROM transactions", "pct"),
    "tax_share": ("Peso de impuestos sobre las salidas", "SELECT 100.0*abs(sum(amount) FILTER (WHERE category='tax'))/sum(abs(amount)) FILTER (WHERE amount<0) FROM transactions", "pct"),
    "history_share": ("Empresas creadas antes del inicio de ventana", "SELECT count(*) FROM companies WHERE created_at < TIMESTAMP '2024-09-01'", "int"),
    "country_missing": ("Empresas sin país", "SELECT 100.0*count(*) FILTER (WHERE country IS NULL OR trim(country)='')/count(*) FROM companies", "pct"),
    "late_share_ar": ("Tasa bruta de pago tardío AR (payment_date)", "SELECT 100.0*avg(CASE WHEN payment_date>due_date THEN 1.0 ELSE 0 END) FROM invoices WHERE amount>0 AND status='paid' AND payment_date IS NOT NULL AND due_date IS NOT NULL", "pct"),
    "late_share_ap": ("Tasa bruta de pago tardío AP (payment_date)", "SELECT 100.0*avg(CASE WHEN payment_date>due_date THEN 1.0 ELSE 0 END) FROM invoices WHERE amount<0 AND status='paid' AND payment_date IS NOT NULL AND due_date IS NOT NULL", "pct"),
    "credit_note_share": ("Documentos no-factura sobre el total ERP", "SELECT 100.0*count(*) FILTER (WHERE document_type NOT IN ('invoice','invoiceGroup','paymentDocument'))/count(*) FROM invoices", "pct"),
}


def scalar(connection: duckdb.DuckDBPyConnection, sql: str):
    return connection.execute(sql).fetchone()[0]


def collect_metrics(connection: duckdb.DuckDBPyConnection) -> dict[str, float | int]:
    metrics: dict[str, float | int] = {}
    for name, (_, sql, _kind) in EVIDENCE_SQL.items():
        try:
            value = scalar(connection, sql)
        except Exception:  # pragma: no cover - defensive: a single query must not break the report
            value = None
        metrics[name] = value
    return metrics


def fmt_metric(value, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "pct":
        return f"{value:.1f} %"
    if kind == "bn":
        return f"{value:.1f} B"
    if isinstance(value, float):
        return f"{value:,.0f}"
    return f"{value:,}".replace(",", ".")


def fmt_count(value) -> str:
    if value is None:
        return "—"
    return f"{value:,}".replace(",", ".")


def crit_badge(key: str) -> str:
    label, color, _ = CRITICALITY[key]
    return f'<span class="crit" style="--c:{color}">{label}</span>'


def evidence_cell(key: str, metrics: dict[str, float | int]) -> str:
    label, _sql, kind = EVIDENCE_SQL[key]
    value = fmt_metric(metrics.get(key), kind)
    return f'<span class="ev"><b>{value}</b><small>{html.escape(label)}</small></span>'


def build_html(metrics: dict[str, float | int]) -> str:
    groups_html = []
    for qid, plain_q, company_q, source in QUESTIONS:
        features = CATALOG_BY_QUESTION[qid]
        body = "".join(
            f"""<tr>
              <td><b>{html.escape(name)}</b><small>{html.escape(plain)}</small></td>
              <td>{crit_badge(crit)}</td>
              <td class="dir">{html.escape(direction)}</td>
              <td>{html.escape(source_feature)}</td>
              <td class="viewers">{html.escape(viewers)}</td>
              <td>{evidence_cell(evidence, metrics)}{f'<small class="note">{html.escape(note)}</small>' if note else ''}</td>
            </tr>"""
            for name, plain, source_feature, crit, direction, viewers, evidence, note in features
        )
        groups_html.append(
            f"""<section class="qgroup">
              <div class="qhead">
                <div><span class="qtag">{html.escape(plain_q)}</span><h3>{html.escape(company_q)}</h3></div>
                <div class="qsrc">{html.escape(source)}</div>
              </div>
              <div class="table-wrap"><table>
                <thead><tr><th>Feature</th><th>Criticidad</th><th>Dirección sana</th><th>Derivación</th><th>Quién lo usa</th><th>Evidencia en los datos</th></tr></thead>
                <tbody>{body}</tbody>
              </table></div>
            </section>"""
        )

    legend = "".join(
        f'<div class="leg" style="--c:{color}"><b>{html.escape(label)}</b><p>{html.escape(desc)}</p></div>'
        for label, color, desc in CRITICALITY.values()
    )

    viewer_rows = [
        ("Banco / tesorería", "Prestar o recortar exposición", "Caja que se evapora, impago, líneas agotadas", "critica"),
        ("Aseguradora", "Prima sobre impago de clientes", "DSO, vencido persistente, concentración de contraparte", "alta"),
        ("CFO de la empresa", "Tesorería y negociar con el banco", "Runway, bache frente a caída, qué cobro o pago mover", "media"),
        ("Embat", "Retener y vender el producto", "Anticipación, cobertura de datos, quién mejora de verdad", "cobertura"),
    ]
    viewer_html = "".join(
        f"<tr><td><b>{html.escape(a)}</b></td><td>{html.escape(b)}</td><td>{html.escape(c)}</td><td>{crit_badge(d)}</td></tr>"
        for a, b, c, d in viewer_rows
    )

    kpi = [
        ("Empresas", fmt_count(metrics.get("companies_total"))),
        ("Grupos", fmt_count(metrics.get("groups_total"))),
        ("Divisas", fmt_count(metrics.get("currency_count"))),
        ("Empresas con ERP", fmt_metric(metrics.get("erp_share"), "pct")),
        ("Sin categoría", fmt_metric(metrics.get("uncat_share"), "pct")),
        ("Sin país", fmt_metric(metrics.get("country_missing"), "pct")),
    ]
    kpi_html = "".join(f'<div class="kpi"><small>{html.escape(a)}</small><strong>{b}</strong></div>' for a, b in kpi)

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>X-Ray · Features usables y criticidad</title>
<style>{CSS}</style>
</head>
<body>
<header class="hero">
  <div class="eyebrow">EMBAT X-RAY · ANÁLISIS AUTOMÁTICO DE FEATURES</div>
  <h1>Qué señales nos da <code>data/</code><br>y cuánto debe pesar cada una.</h1>
  <p>Catálogo de features usables a partir de los ocho CSV, ordenadas por la pregunta de prestamista de <code>context/scoring.md</code>: primero la caja que se evapora, después cobros, pagos y deuda. La observabilidad es cobertura, no salud.</p>
  <div class="hero-meta"><span>Generado el {datetime.now():%Y-%m-%d %H:%M}</span><span>Corte {AS_OF}</span><span>Artefacto autocontenido</span></div>
  <div class="kpis">{kpi_html}</div>
</header>

<main>
  <section class="block">
    <h2>La criticidad no es uniforme</h2>
    <p class="lead">Una empresa que reduce la caja disponible muy rápido debe mover el score mucho más que una que empeora el medio de cobro unos días. Un modelo plano (todas las features al mismo peso) pierde justo el matiz que un prestamista siente en la tripa.</p>
    <div class="legend">{legend}</div>
  </section>

  <section class="block">
    <h2>Catálogo por pregunta de prestamista</h2>
    <p class="lead">Cada fila enlaza el campo real de <code>data/</code> con la señal derivada, su criticidad, hacia dónde suma salud y qué comprador la usa. La columna de evidencia se calcula sobre la capa de mapeo.</p>
    {''.join(groups_html)}
  </section>

  <section class="block">
    <h2>La misma huella, distinto peso según quién mira</h2>
    <table class="matrix">
      <thead><tr><th>Quién lo ve</th><th>Qué ofrece / quiere</th><th>Qué manda en su score</th><th>Criticidad dominante</th></tr></thead>
      <tbody>{viewer_html}</tbody>
    </table>
  </section>

  <section class="block warning">
    <h2>Lo que <em>no</em> es una feature de salud</h2>
    <div class="grid2">
      <div><h3>Cobertura</h3><p>ERP ausente ({fmt_metric(metrics.get('erp_share'),'pct')} con ERP), movimientos sin categoría ({fmt_metric(metrics.get('uncat_share'),'pct')}), sin país ({fmt_metric(metrics.get('country_missing'),'pct')}), conciliación parcial ({fmt_metric(metrics.get('recon_share'),'pct')}). Son huecos de observabilidad: bajan la confianza, no el nivel.</p></div>
      <div><h3>Trampas de medición</h3><p>Transferencias internas ({fmt_metric(metrics.get('internal_share'),'pct')} del volumen por categoría) inflan cobros y pagos. La foto de <code>balances.csv</code> es del {AS_OF} y hay que reconstruirla hacia atrás. La deuda viene con signo sucio y <code>payment_date</code> no es fiable en vencidas.</p></div>
    </div>
  </section>

  <footer>
    <p>Reproducible con <code>python analysis/feature_criticality.py</code>. Marco: <a href="../context/scoring.md">context/scoring.md</a>. Reglas de mapeo: <a href="../src/mapping/ISSUES.md">src/mapping/ISSUES.md</a>. Decisiones del modelo: <a href="../research/DECISIONS.md">research/DECISIONS.md</a>.</p>
  </footer>
</main>
</body>
</html>"""


CSS = """
:root{--navy:#102a43;--blue:#1463ff;--cyan:#27b3c2;--green:#22a06b;--amber:#f59e0b;--red:#e5484d;--slate:#64748b;--line:#e2e8f0;--bg:#f6f8fc;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--navy);font:15px/1.55 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.85em;background:#eef3fb;padding:1px 5px;border-radius:4px}
a{color:var(--blue)}
.hero{background:linear-gradient(135deg,#0b1f36,#102a43 55%,#12406b);color:#fff;padding:48px clamp(20px,5vw,72px) 40px}
.eyebrow{letter-spacing:.18em;font-size:12px;font-weight:700;color:#7fb0ff}
.hero h1{font-size:clamp(28px,4.2vw,46px);line-height:1.1;margin:14px 0 14px;font-weight:800}
.hero h1 code{background:rgba(255,255,255,.12);color:#bcd6ff}
.hero p{max-width:820px;color:#c7d6ea;font-size:16px}
.hero-meta{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
.hero-meta span{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);padding:5px 12px;border-radius:999px;font-size:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin-top:26px}
.kpi{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.16);border-radius:12px;padding:14px 16px}
.kpi small{display:block;color:#9db4d0;font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.kpi strong{font-size:26px;font-weight:800}
main{max-width:1180px;margin:0 auto;padding:8px clamp(16px,4vw,40px) 60px}
.block{background:#fff;border:1px solid var(--line);border-radius:16px;padding:26px clamp(16px,3vw,32px);margin-top:26px;box-shadow:0 10px 30px -24px rgba(16,42,67,.5)}
.block h2{margin:0 0 6px;font-size:22px}
.lead{color:#486581;max-width:900px;margin:0 0 18px}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.leg{border-left:5px solid var(--c);background:#f8fafc;border-radius:8px;padding:12px 14px}
.leg b{color:var(--c)}
.leg p{margin:4px 0 0;font-size:13px;color:#486581}
.qgroup{border-top:1px solid var(--line);padding-top:20px;margin-top:22px}
.qhead{display:flex;justify-content:space-between;gap:16px;align-items:flex-end;flex-wrap:wrap;margin-bottom:12px}
.qtag{display:inline-block;font-size:12px;font-weight:700;color:var(--blue);text-transform:uppercase;letter-spacing:.05em}
.qhead h3{margin:2px 0 0;font-size:18px}
.qsrc{font-size:12.5px;color:var(--slate);text-align:right}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{width:100%;border-collapse:collapse;font-size:13.5px;min-width:860px}
thead th{background:#f1f5fb;text-align:left;padding:10px 12px;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:#486581;border-bottom:1px solid var(--line)}
td{padding:11px 12px;border-bottom:1px solid #eef2f7;vertical-align:top}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafcff}
td small{display:block;color:#6b7c93;font-size:12px;margin-top:2px}
td b{font-size:13.5px}
td.dir{white-space:nowrap}
td.viewers{color:#486581}
.crit{display:inline-block;background:color-mix(in srgb,var(--c) 14%,#fff);color:var(--c);border:1px solid color-mix(in srgb,var(--c) 40%,#fff);font-weight:700;font-size:12px;padding:3px 10px;border-radius:999px;white-space:nowrap}
.ev b{color:var(--navy)}
.ev small{color:#6b7c93}
.note{color:#8a97a8;font-style:italic}
.matrix{min-width:720px}
.warning{background:linear-gradient(180deg,#fff,#fff8ef);border-color:#f6dfbe}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.grid2 h3{margin:0 0 6px}
.grid2 p{margin:0;color:#486581;font-size:14px}
footer{padding:24px 6px 0;color:#6b7c93;font-size:13px;text-align:center}
@media(max-width:720px){.grid2{grid-template-columns:1fr}.qsrc{text-align:left}}
"""

# Reparto explicito de features por pregunta (mantiene el catalogo legible).
CATALOG_BY_QUESTION: dict[str, list] = {qid: [] for qid, *_ in QUESTIONS}
for _row in CATALOG:
    CATALOG_BY_QUESTION[QUESTION_OF[_row[0]]].append(_row)


def main() -> None:
    connection = duckdb.connect()
    attach(connection, DATA)
    metrics = collect_metrics(connection)
    OUTPUT.write_text(build_html(metrics), encoding="utf-8")
    print(f"Escrito {OUTPUT.relative_to(ROOT)} ({len(CATALOG)} features en {len(QUESTIONS)} preguntas)")


if __name__ == "__main__":
    main()
