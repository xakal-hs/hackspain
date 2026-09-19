"""Motor proactivo (fase 4): proyección aritmética, política, producto y validación.

    cd research && uv run pytest -q tests/test_proactive.py

Incluye la ruta real de empresas nuevas: CSV con el esquema del reto → panel.build_panel (P.DATA redirigido, como en
predict_submission.py --csv-dir) → ProactiveEngine. El control «sano» no dispara deuda y el «decline» no la concede.
"""
import sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

import proactive as PR  # noqa: E402
from proactive import ProactiveEngine  # noqa: E402


@pytest.fixture(scope="module")
def engine():
    return ProactiveEngine(pl.read_parquet(ROOT / "data/panel.parquet"), None)


def _sum_lines(proj):
    return sum(l["signo"] * l["total"] for l in proj["lineas"])


def test_projection_is_arithmetic(engine):
    """La caja proyectada en T+H es exactamente caja(T) + Σ signo·total de las líneas: nada oculto."""
    p = engine.project("COMP_0004", "2026-06", 6)
    assert p["variante"] == "estricta" and p["modo"] == "facturas"
    assert abs(p["meses"][-1]["caja"] - (p["caja_inicial"] + _sum_lines(p))) < 1.0
    claves = {l["clave"] for l in p["lineas"]}
    assert claves == {"cobros_pendientes", "pagos_pendientes", "nominas", "cuotas_deuda"}
    for l in p["lineas"]:
        assert len(l["por_mes"]) == 6 and abs(sum(l["por_mes"]) - l["total"]) < 1.0


def test_projection_uses_only_non_overdue_pending_invoices(engine):
    """Las facturas que suman son las emitidas antes del cierre de T, sin pagar a T y con vencimiento posterior a T."""
    cid, T = "COMP_0004", pd.Timestamp("2026-06-01")
    p = engine.project(cid, T, 3)
    g = engine._inv_by[cid]
    T_end = pd.Timestamp("2026-07-01")
    pend = g[(g.issuance_date < T_end) & (g.payment_date.isna() | (g.payment_date >= T_end))]
    k = (pend.due_date.dt.year * 12 + pend.due_date.dt.month) - (T.year * 12 + T.month)
    ar1 = pend[(k == 1) & (pend.side == "ar")].pendiente.sum()
    assert abs(p["lineas"][0]["por_mes"][0] - ar1) < 1.0
    # lo vencido a T no entra en «anticipable»
    vencidas = pend[k <= 0]
    assert p["anticipable"]["total"] <= pend[(k >= 1) & (pend.side == "ar")].pendiente.sum() + 1.0
    assert len(vencidas) >= 0


def test_no_forecaster_in_engine():
    """El motor no importa ni usa el TrajectoryForecaster ni LightGBM."""
    src = (ROOT / "src" / "proactive.py").read_text()
    assert "TrajectoryForecaster" not in src.replace("Sin ERP", "").split("import")[0] or "from xray import SPEC" in src
    assert "lightgbm" not in src and "mlforecast" not in src
    assert "TrajectoryForecaster(" not in src


def test_decision_is_policy_ordered(engine):
    """Caja negativa hoy → C1 no prestar y sin producto (colateral solo se menciona)."""
    raw = engine.feats
    clean = ~sum(raw[k].fillna(False).astype(bool) for k in ("dq_cash_sentinel", "has_drift", "dq_cash_implausible")).astype(bool)
    neg = raw[(raw.cash_end < 0) & (raw.n_tx >= 5) & (raw.months_since_last_tx == 0) & clean]
    r = neg.iloc[0]
    d = engine.decide(r.company_id, r.month)
    assert d["accion"] == "decline" and d["regla"] == "C1" and d["producto"] == "ninguna"
    assert any(x["codigo"] == "C1" for x in d["razones"]) and any(x["codigo"] == "P" for x in d["razones"])


def test_recommend_shape(engine):
    d = engine.recommend("COMP_0004", "2026-06")
    for k in ("accion", "producto", "meses_antelacion", "decision", "proyeccion", "senales", "desenlace", "meses_disponibles"):
        assert k in d
    assert d["accion"] in PR.ACCIONES and d["producto"] in PR.PRODUCTOS
    assert d["desenlace"]["disponible"] is True and len(d["desenlace"]["meses"]) == 2
    d2 = engine.recommend("COMP_0004", "2026-08")
    assert d2["desenlace"]["disponible"] is False


def test_unknown_company_and_month(engine):
    with pytest.raises(KeyError):
        engine.recommend("NOPE")
    with pytest.raises(KeyError):
        engine.recommend("COMP_0004", "2019-01")


# ---------------------------------------------------------------- empresas nuevas: CSV con el esquema del reto
def _csv_dataset(tmp: Path) -> Path:
    """Dos empresas nuevas con el esquema del reto (companies, banking_products, debt_products, balances, transactions,
    invoices, debt_schedule_config). NEW_SANA: caja holgada y cobros regulares. NEW_ROTA: caja negativa, cobros cayendo."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2025-01-01", "2026-08-01", freq="MS")
    comps = pd.DataFrame([{"company_id": "NEW_SANA", "group_id": "GROUP_NEW1", "country": "ES", "currency": "EUR", "erp": "sap", "created_at": "2024-12-01 00:00:00"},
                          {"company_id": "NEW_ROTA", "group_id": "GROUP_NEW2", "country": "ES", "currency": "EUR", "erp": "sap", "created_at": "2024-12-01 00:00:00"}])
    bank = pd.DataFrame([{"product_id": "NP_001", "company_id": "NEW_SANA", "label": "CHECKING", "type": "checking", "bank_name": "B", "service": "b", "currency": "EUR", "created_at": "2024-12-01 00:00:00"},
                         {"product_id": "NP_002", "company_id": "NEW_ROTA", "label": "CHECKING", "type": "checking", "bank_name": "B", "service": "b", "currency": "EUR", "created_at": "2024-12-01 00:00:00"}])
    debt = pd.DataFrame([{"product_id": "NP_003", "company_id": "NEW_ROTA", "label": "LOAN", "type": "loan", "bank_name": "B", "service": "b", "currency": "EUR",
                          "created_at": "2024-12-01 00:00:00", "granted": 300000.0, "outstanding": -250000.0, "liquidity": np.nan}])
    tx, inv = [], []
    tid = 0
    for cid, scale, trend in (("NEW_SANA", 100000.0, 1.0), ("NEW_ROTA", 100000.0, 0.85)):
        for i, m in enumerate(months):
            k = trend ** i
            for day, cat, amt in ((3, "collection", scale * k), (10, "collection", 0.6 * scale * k), (5, "payment", -0.45 * scale), (12, "utility", -0.05 * scale),
                                  (28, "salary", -0.30 * scale), (28, "social_security", -0.10 * scale), (15, "tax", -0.05 * scale), (20, "payment", -0.25 * scale)):
                tid += 1
                tx.append({"transaction_id": f"T{tid:06d}", "company_id": cid, "product_id": "NP_001" if cid == "NEW_SANA" else "NP_002",
                           "date": (m + pd.Timedelta(days=day - 1)).strftime("%Y-%m-%d %H:%M:%S"), "value_date": (m + pd.Timedelta(days=day - 1)).strftime("%Y-%m-%d %H:%M:%S"),
                           "amount": round(amt + rng.normal(0, 0.01 * scale), 2), "exchange_rate": 1.0, "status": "booked", "accounting_status": "RECONCILIATION_COMPLETED",
                           "category": cat, "description": f"{cat} {m:%m}", "counterparty_id": f"CP_{cat}"})
            if cid == "NEW_ROTA":
                tid += 1
                tx.append({"transaction_id": f"T{tid:06d}", "company_id": cid, "product_id": "NP_002", "date": (m + pd.Timedelta(days=24)).strftime("%Y-%m-%d %H:%M:%S"),
                           "value_date": (m + pd.Timedelta(days=24)).strftime("%Y-%m-%d %H:%M:%S"), "amount": -12000.0, "exchange_rate": 1.0, "status": "booked",
                           "accounting_status": "RECONCILIATION_COMPLETED", "category": "debt_repayment", "description": "CUOTA PRESTAMO", "counterparty_id": None})
            # facturas: emitidas (AR, +) y recibidas (AP, −); las de los últimos meses siguen pendientes
            for j in range(3):
                iss = m + pd.Timedelta(days=2 + 7 * j)
                due = iss + pd.Timedelta(days=60)
                paid = due <= pd.Timestamp("2026-08-31")
                amt_ar = round(0.5 * scale * k, 2)
                inv.append({"operation_id": f"I{cid}{i:02d}{j}a", "company_id": cid, "document_type": "invoice", "issuance_date": iss.strftime("%Y-%m-%d %H:%M:%S"),
                            "due_date": due.strftime("%Y-%m-%d %H:%M:%S"), "payment_date": due.strftime("%Y-%m-%d %H:%M:%S"), "amount": amt_ar,
                            "pending_amount": 0.0 if paid else amt_ar, "currency": "EUR", "accounting_currency": "EUR", "exchange_rate": 1.0,
                            "status": "paid" if paid else "pending", "concept": "venta", "counterparty_id": f"CUST_{j}"})
                amt_ap = -round((0.9 if cid == "NEW_ROTA" else 0.2) * scale, 2)
                inv.append({"operation_id": f"I{cid}{i:02d}{j}p", "company_id": cid, "document_type": "invoice", "issuance_date": iss.strftime("%Y-%m-%d %H:%M:%S"),
                            "due_date": due.strftime("%Y-%m-%d %H:%M:%S"), "payment_date": due.strftime("%Y-%m-%d %H:%M:%S"), "amount": amt_ap,
                            "pending_amount": 0.0 if paid else amt_ap, "currency": "EUR", "accounting_currency": "EUR", "exchange_rate": 1.0,
                            "status": "paid" if paid else "pending", "concept": "compra", "counterparty_id": f"SUP_{j}"})
    tx = pd.DataFrame(tx)
    # saldos finales (foto 2026-09-01): la sana con colchón amplio, la rota en negativo
    bal = pd.DataFrame([{"product_id": "NP_001", "company_id": "NEW_SANA", "date": "2026-09-01 00:00:00", "balance": 900000.0, "available": 900000.0, "granted": np.nan, "liquidity": np.nan, "countable": np.nan},
                        {"product_id": "NP_002", "company_id": "NEW_ROTA", "date": "2026-09-01 00:00:00", "balance": -40000.0, "available": np.nan, "granted": np.nan, "liquidity": np.nan, "countable": np.nan},
                        {"product_id": "NP_003", "company_id": "NEW_ROTA", "date": "2026-09-01 00:00:00", "balance": -250000.0, "available": np.nan, "granted": 300000.0, "liquidity": np.nan, "countable": np.nan}])
    sched = pd.DataFrame([{"product_id": "NP_003", "company_id": "NEW_ROTA", "settlement_product_id": "NP_002", "currency": "EUR", "amortization_type": "constant quote",
                           "interest_calc_method": "30/360", "amortising_frequency": "monthly", "granted_balance": 300000.0, "outstanding_balance": 250000.0, "total_periods": 25,
                           "next_payment_date": "2026-09-25 00:00:00", "last_payment_date": "2026-08-25 00:00:00", "annual_interest_rate_or_spread": 0.04, "interest_type": "fixed"}])
    for name, df in (("companies", comps), ("banking_products", bank), ("debt_products", debt), ("balances", bal), ("transactions", tx),
                     ("invoices", pd.DataFrame(inv)), ("debt_schedule_config", sched)):
        df.to_csv(tmp / f"{name}.csv", index=False)
    return tmp


def test_new_companies_via_challenge_csv(tmp_path):
    """Ruta real de empresas nuevas (predict_submission --csv-dir): CSV → parquet → panel.build_panel → motor.
    El control sano no dispara deuda; la rota no recibe producto de deuda."""
    import panel as P
    csv_dir = _csv_dataset(tmp_path)
    pq = tmp_path / "parquet"; pq.mkdir()
    for f in csv_dir.glob("*.csv"):
        pl.read_csv(f, infer_schema_length=100000, try_parse_dates=True).write_parquet(pq / f"{f.stem}.parquet")
    old = P.DATA
    try:
        P.DATA = pq
        raw = P.build_panel()
    finally:
        P.DATA = old
    assert set(raw["company_id"].unique()) == {"NEW_SANA", "NEW_ROTA"}
    eng = ProactiveEngine(raw, None, data_dir=pq)
    sana = eng.recommend("NEW_SANA", "2026-08")
    rota = eng.recommend("NEW_ROTA", "2026-08")
    # control sano: colchón amplio, sin tensión proyectada, prestar y sin producto de deuda
    assert sana["proyeccion"]["meses_caja"] > 2
    assert sana["proyeccion"]["tension_h"] is None and sana["meses_antelacion"] is None
    assert sana["accion"] == "lend" and sana["producto"] == "ninguna" and not sana["decision"]["necesita_deuda_2m"]
    # decline: caja negativa hoy → C1, no prestar y ningún producto concedido
    assert rota["proyeccion"]["caja_inicial"] < 0
    assert rota["accion"] == "decline" and rota["decision"]["regla"] == "C1" and rota["producto"] == "ninguna"
    # la proyección de la rota usa facturas (tiene ERP) y el cuadro de amortización
    assert rota["proyeccion"]["modo"] == "facturas"
    assert "debt_schedule_config" in next(l for l in rota["proyeccion"]["lineas"] if l["clave"] == "cuotas_deuda")["fuente"]
    # T+2 no observable en el último mes
    assert sana["desenlace"]["disponible"] is False


# ---------------------------------------------------------------- API
def test_api_endpoints():
    """Handlers de FastAPI llamados directamente (sin httpx): contrato de /api/situaciones y /api/proactive."""
    from fastapi import HTTPException
    sys.path.insert(0, str(ROOT))
    from app import server as S
    body = S.situaciones()
    assert "situaciones" in body and "resumen" in body and isinstance(body["situaciones"], list)
    if body["situaciones"]:
        assert len(body["situaciones"]) >= 100
        assert S.situacion(body["situaciones"][0]["id"])["id"] == body["situaciones"][0]["id"]
        assert body["resumen"]["centrales_fallan"] <= body["resumen"]["fallan"]
    else:
        assert "aviso" in body
    with pytest.raises(HTTPException) as e:
        S.situacion("NOPE")
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        S.proactive("COMP_0004", None, 40)
    assert e.value.status_code == 422
    val = S.proactive_validation()
    assert "casos" in val and "metricas" in val
    d = S.proactive("COMP_0004", "2026-06", 6)
    assert d["accion"] in ("lend", "watch", "decline", "sin_nota") and d["proyeccion"]["variante"] == "estricta"
    assert isinstance(d["score"], float) and d["band"] in ("sano", "vigilar", "riesgo")
    with pytest.raises(HTTPException) as e:
        S.proactive("NOPE", None, 6)
    assert e.value.status_code == 404
