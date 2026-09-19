"""Motor proactivo de X-Ray: proyección de tesorería determinista y explicable línea a línea (fase 4).

    caja(T+h) = caja(T)
              + cobros pendientes con vencimiento en (T, T+h]   (facturas emitidas, pendientes a cierre de T, por due_date)
              − pagos pendientes con vencimiento en (T, T+h]    (facturas recibidas, pendientes a cierre de T, por due_date)
              − nóminas recurrentes × h                         (mediana de los últimos 6 meses, no la del último mes)
              − cuotas de deuda × h                             (cuadro de amortización; si falta, la mediana de debt_service 6m)

La «rotura» es el primer h con caja(T+h) < 0; la «tensión» el primer h con caja + póliza disponible < 0,25 meses de
gasto (umbral de la política de la fase 1 = targets.py:87). La recomendación usa la tensión: en el panel la caja casi
nunca baja de cero (1,3 % de las empresa-mes desde caja ≥ 0), la pyme retrasa pagos antes; la tensión sí se anticipa.

Variante «completa» (`completa=True`): añade ± flujos bancarios recurrentes que ninguna factura, nómina ni cuota
explica (impuestos, suministros, tarjetas). Medida en el fold held-out fue PEOR que la fórmula estricta (precisión
0,23 frente a 0,30 al anticipar la tensión desde sana; error mediano 0,65 frente a 0,57 meses de gasto), así que la
estricta es la que se sirve y la completa queda como referencia.

Sin ERP no hay facturas: los dos términos de facturas se sustituyen por los cobros y pagos bancarios recurrentes
(medianas de 6 meses) y la proyección queda marcada como modo «bancario». No usa LGBM ni TrajectoryForecaster:
cada término es una suma sobre el panel y las facturas que se puede señalar en la UI. La decisión (prestar /
vigilar / no prestar) y el producto (factoring, confirming, línea, refinanciación) siguen la política de la fase 1
(.devin/workflows/autoresearch/salida/politica_prestamo.md §3-§5). El factoring se decide sobre las facturas
emitidas pendientes que AÚN NO HAN VENCIDO: lo ya vencido casi nunca se descuenta.

    uv run python src/proactive.py recommend COMP_0004 2026-06
    uv run python src/proactive.py validate          # empresas held-out por group_id → precisión a 2 meses
"""
from __future__ import annotations
import argparse, json, sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import add_features  # noqa: E402
from xray import SPEC, band_of, explain, fmt_feature, es  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SALIDA = ROOT.parent / ".devin" / "workflows" / "autoresearch" / "salida" / "demo"
SNAPSHOT = pd.Timestamp("2026-09-01")
STRESS_MONTHS = 0.25        # umbral de tensión de la política de la fase 1 (= targets.py:87)
ADVANCE_RATE = 0.80         # anticipo habitual del factoring sobre el nominal de la factura
EFECTOS_RE = r"(?i)pagar[ée]|efecto|remesa"
FREQ_MONTHS = {"monthly": 1, "quarterly": 3, "semiannually": 6, "annually": 12}
PRODUCTOS = {"factoring": "Factoring / anticipo de facturas", "confirming": "Confirming", "linea": "Línea de circulante",
             "refi": "Refinanciación / consolidación", "ninguna": "Ninguna"}
ACCIONES = {"lend": "Prestar", "watch": "Vigilar", "decline": "No prestar", "sin_nota": "Sin nota"}


# ---------------------------------------------------------------- carga de datos crudos (facturas, cuadro, efectos)
def _fx_last(data_dir: Path) -> pd.Series:
    import fx as FX
    f = FX.load()
    return f[f.month == f.month.max()].set_index("currency").per_eur


def load_invoices(data_dir: Path = DATA) -> pd.DataFrame:
    """Facturas (invoice / invoiceGroup, no canceladas) en la moneda de la empresa, con el estado «pendiente» de la foto.

    Misma regla de FX que panel._invoices_monthly (D03): tipo del fichero si está a ±10 % del real, si no el real."""
    p = data_dir / "invoices.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["company_id", "side", "issuance_date", "due_date", "payment_date", "abs_amt", "pendiente", "counterparty_id"])
    inv = pl.read_parquet(p).filter(pl.col("status") != "cancel", pl.col("document_type").is_in(["invoice", "invoiceGroup"]))
    lo, snap = pl.datetime(2015, 1, 1), pl.datetime(SNAPSHOT.year, SNAPSHOT.month, SNAPSHOT.day)
    inv = inv.filter(pl.col("due_date").is_between(lo, pl.datetime(2028, 12, 31)), pl.col("issuance_date").is_between(lo, snap))
    comp = pl.read_parquet(data_dir / "companies.parquet").select("company_id", pl.col("currency").alias("ccur"))
    fxm = pl.from_pandas(_fx_table_pd())
    inv = (inv.join(comp, on="company_id", how="left").with_columns(im=pl.col("issuance_date").dt.truncate("1mo"))
              .join(fxm.rename({"per_eur": "p_pe", "month": "im"}), on=["im", "currency"], how="left")
              .join(fxm.rename({"currency": "ccur", "per_eur": "c_pe", "month": "im"}), on=["im", "ccur"], how="left")
              .with_columns(real_fx=pl.col("p_pe") / pl.col("c_pe")))
    same = pl.col("currency") == pl.col("ccur")
    ok = (pl.col("exchange_rate") > 0) & ((pl.col("exchange_rate") / pl.col("real_fx") - 1).abs() < 0.10)
    fxv = (pl.when(same).then(1.0).when(ok).then(pl.col("exchange_rate"))
             .otherwise(pl.col("real_fx").fill_null(pl.when(pl.col("exchange_rate") > 0).then(pl.col("exchange_rate")).otherwise(1.0))))
    unpaid = (pl.col("pending_amount").abs() > 0) & (pl.col("status") != "paid")
    out = inv.select(
        "company_id", "counterparty_id", "issuance_date", "due_date",
        side=pl.when(pl.col("amount") > 0).then(pl.lit("ar")).otherwise(pl.lit("ap")),
        payment_date=pl.when(unpaid | (pl.col("payment_date") > snap)).then(None).otherwise(pl.col("payment_date")),
        abs_amt=pl.col("amount").abs() / fxv,
        # importe que seguía pendiente: el pendiente de la foto si no se ha pagado; el nominal si se pagó después
        pendiente=pl.when(unpaid).then(pl.col("pending_amount").abs() / fxv).otherwise(pl.col("amount").abs() / fxv),
    )
    return out.to_pandas()


def _fx_table_pd() -> pd.DataFrame:
    import fx as FX
    f = FX.load()[["month", "currency", "per_eur"]].copy()
    f["month"] = pd.to_datetime(f.month).astype("datetime64[us]")
    return f


def load_schedule(data_dir: Path = DATA) -> pd.DataFrame:
    """Cuota mensual implícita por empresa desde debt_schedule_config, en la moneda de la empresa."""
    p = data_dir / "debt_schedule_config.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["company_id", "cuota_mensual", "n_productos"])
    ds = pd.read_parquet(p)
    if ds.empty:
        return pd.DataFrame(columns=["company_id", "cuota_mensual", "n_productos"])
    comp = pd.read_parquet(data_dir / "companies.parquet")[["company_id", "currency"]].rename(columns={"currency": "ccur"})
    ds = ds.merge(comp, on="company_id", how="left")
    fx = _fx_last(data_dir)
    rate = (ds.currency.map(fx) / ds.ccur.map(fx)).where(ds.currency != ds.ccur, 1.0).fillna(1.0)
    fm = ds.amortising_frequency.map(FREQ_MONTHS).fillna(1)
    periods = pd.to_numeric(ds.total_periods, errors="coerce").replace(0, np.nan)
    principal = pd.to_numeric(ds.granted_balance, errors="coerce").abs() / periods
    outstanding = pd.to_numeric(ds.outstanding_balance, errors="coerce").abs().fillna(0)
    interest = outstanding * pd.to_numeric(ds.annual_interest_rate_or_spread, errors="coerce").fillna(0) * fm / 12
    ds["cuota_mensual"] = ((principal.fillna(0) + interest) / fm) / rate
    return ds.groupby("company_id", as_index=False).agg(cuota_mensual=("cuota_mensual", "sum"), n_productos=("product_id", "size"))


def load_efectos(data_dir: Path = DATA) -> pd.DataFrame:
    """Movimientos con «pagaré / efecto / remesa» en la descripción, por empresa y mes: cobro aplazado e instrumentos
    descontables. Importes en la moneda del producto (solo se usan como indicador y cuota sobre los cobros)."""
    p = data_dir / "transactions.parquet"
    if not p.exists():
        return pd.DataFrame(columns=["company_id", "month", "n_efectos", "efectos_in", "efectos_out"])
    t = pl.scan_parquet(p).select("company_id", "date", "amount", "description")
    e = (t.filter(pl.col("description").str.contains(EFECTOS_RE)).with_columns(month=pl.col("date").dt.truncate("1mo"))
          .group_by("company_id", "month").agg(n_efectos=pl.len(), efectos_in=pl.col("amount").filter(pl.col("amount") > 0).sum(),
                                                efectos_out=-pl.col("amount").filter(pl.col("amount") < 0).sum()).collect())
    return e.to_pandas()


def load_debt_types(data_dir: Path = DATA) -> dict[str, set]:
    p = data_dir / "debt_products.parquet"
    if not p.exists():
        return {}
    dp = pd.read_parquet(p)[["company_id", "type"]].dropna()
    return dp.groupby("company_id")["type"].agg(set).to_dict()


# ---------------------------------------------------------------- utilidades
def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) or np.isinf(v) else round(v, 2) + 0.0


def _month(m) -> pd.Timestamp:
    return pd.Timestamp(m).to_period("M").to_timestamp()


def _add_months(t: pd.Timestamp, k: int) -> pd.Timestamp:
    return (t.to_period("M") + k).to_timestamp()


def _midx(t) -> int:
    return t.year * 12 + t.month


def _robust_mean(s: pd.Series) -> float:
    """Mediana de los últimos meses con dato (mínimo 3); con menos historia, la media de lo que hay; sin nada, 0."""
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) == 0:
        return 0.0
    return float(s.median()) if len(s) >= 3 else float(s.mean())


def _meses(n) -> str:
    return "1 mes" if n == 1 else f"{n} meses"


def _money(v, cur) -> str:
    if v is None:
        return "sin dato"
    a = abs(v)
    s = f"{a / 1e6:.1f} M" if a >= 1e6 else f"{a / 1e3:.0f} k" if a >= 1e4 else f"{a:.0f}"
    return ("−" if v < 0 else "") + s.replace(".", ",") + f" {cur}"


# ---------------------------------------------------------------- motor
class ProactiveEngine:
    """Proyección aritmética + política de la fase 1 sobre un panel ya construido (panel.py) y sus facturas crudas."""

    def __init__(self, panel: pl.DataFrame | pd.DataFrame, scorer=None, data_dir: Path = DATA,
                 feats: pd.DataFrame | None = None, scored: pd.DataFrame | None = None):
        raw = panel if isinstance(panel, pl.DataFrame) else pl.from_pandas(panel)
        self.feats = (feats if feats is not None else add_features(raw).to_pandas()).sort_values(["company_id", "month"]).reset_index(drop=True)
        self.feats["month"] = pd.to_datetime(self.feats.month)
        self.scorer = scorer
        self.scored = scored if scored is not None else (scorer.score_panel(self.feats) if scorer is not None else None)
        if self.scored is not None:
            self.scored = self.scored.sort_values(["company_id", "month"]).reset_index(drop=True)
            self.scored["month"] = pd.to_datetime(self.scored.month)
        self.inv = load_invoices(data_dir)
        self.schedule = load_schedule(data_dir).set_index("company_id")
        self.efectos = load_efectos(data_dir)
        self.debt_types = load_debt_types(data_dir)
        comp = pd.read_parquet(data_dir / "companies.parquet")
        self.currency = comp.set_index("company_id").currency.to_dict()
        self._inv_by = {k: g for k, g in self.inv.groupby("company_id")} if len(self.inv) else {}
        self._feat_by = {k: g.reset_index(drop=True) for k, g in self.feats.groupby("company_id")}
        self._ef_by = {k: g for k, g in self.efectos.groupby("company_id")} if len(self.efectos) else {}
        # liquidaciones de facturas por mes de pago: lo que del banco ya explica una factura
        paid = self.inv[self.inv.payment_date.notna()] if len(self.inv) else self.inv
        if len(paid):
            pm = paid.assign(month=paid.payment_date.dt.to_period("M").dt.to_timestamp())
            liq = pm.pivot_table(index=["company_id", "month"], columns="side", values="abs_amt", aggfunc="sum", fill_value=0.0).reset_index()
            for c in ("ar", "ap"):
                if c not in liq:
                    liq[c] = 0.0
            self._paid_by = {k: g.set_index("month")[["ar", "ap"]] for k, g in liq.groupby("company_id")}
        else:
            self._paid_by = {}

    # ------------------------------------------------------------ acceso
    def months(self, cid: str) -> list[pd.Timestamp]:
        return list(self._feat_by[cid].month) if cid in self._feat_by else []

    def _row(self, cid: str, T: pd.Timestamp) -> pd.Series:
        f = self._feat_by.get(cid)
        if f is None:
            raise KeyError(f"Empresa {cid} no encontrada")
        r = f[f.month == T]
        if r.empty:
            raise KeyError(f"{cid} no tiene datos en {T:%Y-%m}")
        return r.iloc[0]

    def _hist(self, cid: str, T: pd.Timestamp, n: int = 6) -> pd.DataFrame:
        f = self._feat_by[cid]
        return f[f.month <= T].tail(n)

    # ------------------------------------------------------------ proyección (aritmética, sin modelo)
    def project(self, cid: str, T, horizon: int = 6, completa: bool = False) -> dict:
        """`completa=False` es la fórmula estricta de cuatro términos (la que se sirve); `completa=True` añade los
        flujos bancarios recurrentes que ninguna factura, nómina ni cuota explica (medida peor, ver cabecera)."""
        T = _month(T)
        r = self._row(cid, T)
        cur = self.currency.get(cid, "EUR")
        hist = self._hist(cid, T, 6)
        T_end = _add_months(T, 1)
        cash0 = float(r.cash_end) if pd.notna(r.cash_end) else 0.0
        lim, drawn = float(r.lc_limit or 0) if pd.notna(r.lc_limit) else 0.0, float(r.lc_drawn or 0) if pd.notna(r.lc_drawn) else 0.0
        avail = max(lim - drawn, 0.0) if lim > 0 else 0.0
        burn = float(max(r.out3 / 3, r.out12 / 12)) if pd.notna(r.out3) else 0.0
        payroll_m = _robust_mean(hist.payroll)
        has_inv = cid in self._inv_by and bool(r.has_erp) if "has_erp" in r else cid in self._inv_by
        modo = "facturas" if has_inv else "bancario"
        H = list(range(1, horizon + 1))
        zeros = lambda: [0.0] * horizon

        lineas = []
        ar_m, ap_m, n_ar, n_ap = zeros(), zeros(), 0, 0
        anticipable = {"total": 0.0, "por_vencer_h": 0.0, "n": 0, "anticipo_estimado": 0.0, "n_contrapartes": 0}
        ap_pend = {"total": 0.0, "n": 0}
        if has_inv:
            g = self._inv_by[cid]
            # pendiente a cierre de T: emitida antes del cierre y no cobrada/pagada antes del cierre
            pend = g[(g.issuance_date < T_end) & (g.payment_date.isna() | (g.payment_date >= T_end))]
            k = (pend.due_date.dt.year * 12 + pend.due_date.dt.month) - _midx(T)
            fut = pend[k >= 1]                      # no vencidas a T (lo vencido no se proyecta ni se descuenta)
            kf = k[k >= 1]
            for kk, grp in fut.groupby(kf):
                if kk <= horizon:
                    ar_m[kk - 1] = float(grp.loc[grp.side == "ar", "pendiente"].sum())
                    ap_m[kk - 1] = float(grp.loc[grp.side == "ap", "pendiente"].sum())
            ar_all = fut[fut.side == "ar"]
            n_ar, n_ap = int((fut.side == "ar").sum() if len(fut) else 0), int((fut.side == "ap").sum() if len(fut) else 0)
            anticipable = {"total": float(ar_all.pendiente.sum()), "por_vencer_h": float(sum(ar_m)), "n": int(len(ar_all)),
                           "anticipo_estimado": float(ar_all.pendiente.sum()) * ADVANCE_RATE,
                           "n_contrapartes": int(ar_all.counterparty_id.nunique())}
            ap_pend = {"total": float(fut.loc[fut.side == "ap", "pendiente"].sum()), "n": n_ap}
            lineas.append({"clave": "cobros_pendientes", "signo": 1, "label": "Cobros pendientes (facturas emitidas, no vencidas)",
                           "fuente": "invoices: issuance ≤ T, sin pagar a T, due_date en (T, T+h]", "por_mes": ar_m, "total": float(sum(ar_m)), "n": n_ar})
            lineas.append({"clave": "pagos_pendientes", "signo": -1, "label": "Pagos pendientes (facturas recibidas, no vencidas)",
                           "fuente": "invoices: issuance ≤ T, sin pagar a T, due_date en (T, T+h]", "por_mes": ap_m, "total": float(sum(ap_m)), "n": n_ap})
            if completa:
                # banco − lo que ya explica una factura liquidada ese mes − nóminas − cuotas, mes a mes; mediana 6m
                paid = self._paid_by.get(cid)
                hp = hist.set_index("month")
                ar_p = paid.ar.reindex(hp.index).fillna(0.0) if paid is not None else pd.Series(0.0, index=hp.index)
                ap_p = paid.ap.reindex(hp.index).fillna(0.0) if paid is not None else pd.Series(0.0, index=hp.index)
                otros_in = _robust_mean((hp.inflow - ar_p).clip(lower=0))
                otros_out = _robust_mean((hp.outflow - ap_p - hp.payroll - hp.debt_service).clip(lower=0))
                lineas.append({"clave": "otros_cobros", "signo": 1, "label": "Otros cobros recurrentes no facturados",
                               "fuente": "panel.inflow − facturas emitidas cobradas en el mes, mediana 6m × h", "por_mes": [otros_in] * horizon, "total": otros_in * horizon, "n": None})
                lineas.append({"clave": "otros_pagos", "signo": -1, "label": "Otros pagos recurrentes no facturados (impuestos, suministros, tarjetas)",
                               "fuente": "panel.outflow − facturas recibidas pagadas − payroll − debt_service, mediana 6m × h", "por_mes": [otros_out] * horizon, "total": otros_out * horizon, "n": None})
        else:
            # sin ERP: cobros y pagos bancarios recurrentes (medianas 6m), fuera de nóminas y deuda
            cob = _robust_mean(hist.inflow)
            otros = max(_robust_mean(hist.outflow - hist.payroll - hist.debt_service), 0.0)
            lineas.append({"clave": "cobros_recurrentes", "signo": 1, "label": "Cobros bancarios recurrentes (mediana 6m, sin ERP)",
                           "fuente": "panel.inflow mediana 6m × h", "por_mes": [cob] * horizon, "total": cob * horizon, "n": None})
            lineas.append({"clave": "pagos_recurrentes", "signo": -1, "label": "Otros pagos recurrentes (mediana 6m, sin nóminas ni deuda)",
                           "fuente": "panel.outflow − payroll − debt_service, mediana 6m × h", "por_mes": [otros] * horizon, "total": otros * horizon, "n": None})
        lineas.append({"clave": "nominas", "signo": -1, "label": "Nóminas y seguridad social recurrentes", "fuente": "panel.payroll mediana 6m × h",
                       "por_mes": [payroll_m] * horizon, "total": payroll_m * horizon, "n": None})
        if cid in self.schedule.index and self.schedule.loc[cid, "cuota_mensual"] > 0:
            cuota, fuente = float(self.schedule.loc[cid, "cuota_mensual"]), f"debt_schedule_config ({int(self.schedule.loc[cid, 'n_productos'])} productos): principal/periodos + interés"
        else:
            cuota, fuente = _robust_mean(hist.debt_service), "panel.debt_service mediana 6m × h (sin cuadro de amortización)"
        lineas.append({"clave": "cuotas_deuda", "signo": -1, "label": "Cuotas de deuda", "fuente": fuente,
                       "por_mes": [cuota] * horizon, "total": cuota * horizon, "n": None})

        # camino de caja
        meses, caja, rotura_h, tension_h = [], cash0, None, None
        umbral = STRESS_MONTHS * burn
        for h in H:
            caja += sum(l["signo"] * l["por_mes"][h - 1] for l in lineas)
            liq = caja + avail
            rot, ten = caja < 0, liq < umbral
            rotura_h = rotura_h or (h if rot else None)
            tension_h = tension_h or (h if ten else None)
            meses.append({"h": h, "month": f"{_add_months(T, h):%Y-%m}", "caja": _num(caja), "liquidez": _num(liq), "rotura": bool(rot), "tension": bool(ten)})
        def _hueco(ms):
            if not ms:
                return 0.0
            min_caja, min_liq = min(m["caja"] for m in ms), min(m["liquidez"] for m in ms)
            return max(-min_caja, 0.0) if any(m["rotura"] for m in ms) else max(umbral - min_liq, 0.0) if any(m["tension"] for m in ms) else 0.0
        hueco, hueco_2m = _hueco(meses), _hueco(meses[:2])

        ef = self._ef_by.get(cid)
        efectos = {"n_6m": 0, "importe_6m": 0.0, "share_cobros_6m": None}
        if ef is not None:
            e6 = ef[(ef.month <= T) & (ef.month > _add_months(T, -6))]
            inflow6 = float(hist.inflow.sum())
            efectos = {"n_6m": int(e6.n_efectos.sum()), "importe_6m": float(e6.efectos_in.sum()),
                       "share_cobros_6m": _num(min(float(e6.efectos_in.sum()) / inflow6, 1.0)) if inflow6 > 0 else None}
        # fiabilidad: qué parte del banco explican las facturas liquidadas en los últimos 6 meses (held-out: precisión
        # 0,37 con cobertura < 0,2; 0,50-0,64 entre 0,4 y 1,0; 0,21 por encima de 1 = facturas que no cuadran con el banco)
        cobertura, fiabilidad = None, "sin facturas"
        if has_inv:
            paid = self._paid_by.get(cid)
            hp = hist.set_index("month")
            banco6 = float(hp.inflow.sum() + hp.outflow.sum())
            fact6 = float(paid.ar.reindex(hp.index).fillna(0).sum() + paid.ap.reindex(hp.index).fillna(0).sum()) if paid is not None else 0.0
            cobertura = _num(fact6 / banco6) if banco6 > 0 else None
            fiabilidad = "sin dato" if cobertura is None else "alta" if 0.4 <= cobertura <= 1.0 else "media" if 0.2 <= cobertura < 0.4 or 1.0 < cobertura <= 1.5 else "baja"
        for l in lineas:
            l["total"], l["por_mes"] = _num(l["total"]), [_num(x) for x in l["por_mes"]]
        return {"company_id": cid, "month": f"{T:%Y-%m}", "horizon": horizon, "modo": modo, "variante": "completa" if completa else "estricta", "currency": cur,
                "caja_inicial": _num(cash0), "poliza_disponible": _num(avail), "gasto_mensual": _num(burn), "umbral_tension": _num(umbral),
                "meses_caja": _num((cash0 + avail) / burn) if burn > 0 else None,
                "cobertura_facturas": cobertura, "fiabilidad": fiabilidad,
                "lineas": lineas, "meses": meses, "rotura_h": rotura_h, "tension_h": tension_h, "hueco": _num(hueco), "hueco_2m": _num(hueco_2m),
                "anticipable": {k: (_num(v) if isinstance(v, float) else v) for k, v in anticipable.items()},
                "ap_pendiente": {k: (_num(v) if isinstance(v, float) else v) for k, v in ap_pend.items()},
                "efectos": efectos, "productos_contratados": sorted(self.debt_types.get(cid, set())),
                "formula": "caja(T+h) = caja(T) + cobros pendientes(T,T+h] − pagos pendientes(T,T+h] − nóminas×h − cuotas×h"}

    # ------------------------------------------------------------ política de la fase 1
    def decide(self, cid: str, T, proj: dict | None = None, horizon: int = 6) -> dict:
        T = _month(T)
        r = self._row(cid, T)
        proj = proj or self.project(cid, T, horizon)
        cur = proj["currency"]
        razones, accion, regla = [], None, None
        v = lambda k: float(r[k]) if k in r and pd.notna(r[k]) else None
        def razon(codigo, senal, valor, texto):
            razones.append({"codigo": codigo, "senal": senal, "valor": valor, "texto": texto})

        # C0 · dato no fiable → sin nota
        dq = [k for k in ("dq_cash_sentinel", "has_drift", "dq_cash_implausible") if k in r and bool(r[k])]
        n_tx, dorm = int(r.n_tx) if pd.notna(r.n_tx) else 0, int(r.months_since_last_tx) if pd.notna(r.months_since_last_tx) else 0
        if dq:
            accion, regla = "sin_nota", "C0"
            razon("C0", "Caja no fiable", ", ".join(dq), "El saldo reconstruido no es creíble (centinela, deriva o importe implausible): no se da nota, se pide el dato.")
        elif dorm >= 2:
            accion, regla = "sin_nota", "C0"
            razon("C0", "Sin movimientos", f"{dorm} meses", f"Lleva {dorm} meses sin movimientos bancarios: no se ve la empresa, no se puntúa.")
        elif n_tx < 5:
            accion, regla = "sin_nota", "C0"
            razon("C0", "Micro-actividad", f"{n_tx} movimientos", "Menos de 5 movimientos en el mes: no hay base para leer la caja.")

        mc, burn = proj["meses_caja"], proj["gasto_mensual"] or 0.0
        cash = float(r.cash_end) if pd.notna(r.cash_end) else 0.0
        hist = self._hist(cid, T, 12)
        racha = 0
        for c in reversed(list(hist.cash_end)):
            if pd.notna(c) and c < 0:
                racha += 1
            else:
                break
        pay6, payroll = v("pay6"), v("payroll") or 0.0
        growth, act, lcu = v("growth_vs_12m"), v("activity_trend"), v("lc_util")
        mc_txt = f"{es(mc, 1)} meses" if mc is not None else "sin dato"
        if accion is None:
            # C1 · caja rota
            if cash < 0:
                accion, regla = "decline", "C1"
                razon("C1", "Dinero en la cuenta", _money(cash, cur),
                      f"La cuenta está en negativo{f' desde hace {racha} meses' if racha >= 2 else ''}: no se presta deuda nueva. "
                      + ("Solo con colateral (facturas identificables o garantía del grupo)." if racha >= 3 else "El 54 % de estas rachas se cura en un mes: revisar a 30 días."))
            # C5 · nómina habitual ausente
            elif pay6 and pay6 > 0 and payroll <= 0.10 * pay6 and dorm == 0:
                accion, regla = "decline", "C5"
                razon("C5", "Nómina habitual ausente", f"{_money(payroll, cur)} frente a {_money(pay6, cur)} de media",
                      "Este mes no ha salido la nómina que paga cada mes: es la primera evidencia de un impago, llega antes que la caja negativa. No prestar hasta ver la siguiente.")
            # C2 · caja corta
            elif mc is not None and mc < 0.25 and growth is not None and growth < -0.2:
                accion, regla = "decline", "C2"
                razon("C2", "Meses de caja + cobros cayendo", f"{mc_txt}; cobros {fmt_feature('growth_vs_12m', growth)}",
                      f"Le queda menos de una semana de gasto ({mc_txt}) y cobra un {es(100 * (1 - np.exp(growth)), 0)} % menos que su media anual: sin colchón, la caída de cobros es grave (tensión 45 %). Circulante solo con colateral.")
            elif mc is not None and mc < 0.25:
                accion, regla = "watch", "C2"
                razon("C2", "Meses de caja", mc_txt, f"Vive al día: {mc_txt} de gasto en la cuenta (+ póliza). Tensión del 60 % en este tramo; si se presta, poco y con covenant de liquidez ≥ 0,5 meses.")
            elif mc is not None and mc < 0.5:
                accion, regla = "watch", "C2"
                razon("C2", "Meses de caja", mc_txt, f"Colchón corto: {mc_txt} de gasto. Tensión del 38 %: vigilar y prestar poco (≤ 0,5 meses de gasto).")
            # C4 · póliza agotada
            if accion in (None, "watch") and lcu is not None and lcu > 0.9 and mc is not None and mc < 0.5:
                accion, regla = "decline", "C4"
                razon("C4", "Uso de la póliza", fmt_feature("lc_util", lcu), "Lleva gastado más del 90 % de la tarjeta con la caja corta: no ampliar ni prestar nuevo; convertir la póliza en préstamo a plazo si la cuota lo permite.")
            # C3 · cobros que caen con colchón
            if accion is None and growth is not None and growth < -0.2 and mc is not None and mc >= 2:
                if act is not None and act < -0.3:
                    accion, regla = "watch", "C3"
                    razon("C3", "Cobros y actividad cayendo", f"cobros {fmt_feature('growth_vs_12m', growth)}; movimientos {fmt_feature('activity_trend', act)}",
                          "Tiene colchón, pero cobra y se mueve cada vez menos: caída estructural del 28 % en este perfil. Vigilar, no ampliar.")
                else:
                    accion, regla = "lend", "C3"
                    razon("C3", "Cobros cayendo con colchón", f"cobros {fmt_feature('growth_vs_12m', growth)}; {mc_txt} de caja",
                          "Cobra menos que hace un año pero tiene más de dos meses de gasto en la cuenta: riesgo bajo para el banco (tensión 4 %), aviso para el CFO.")
            # C7 · un mes sin movimientos
            if accion is None and dorm == 1:
                accion, regla = "watch", "C7"
                razon("C7", "Sin movimientos", "1 mes", "Un mes sin movimientos: el 68 % vuelve al mes siguiente, pero la caja no puntúa mientras no se mueve.")
            # C9 · cara positiva / tramo intermedio
            if accion is None:
                if mc is not None and mc >= 2:
                    accion, regla = "lend", "C9"
                    razon("C9", "Meses de caja", mc_txt, f"Tiene {mc_txt} de gasto entre cuenta y póliza: tensión del 5 % en este tramo. Prestar, mejor precio.")
                else:
                    accion, regla = "lend", "C2"
                    razon("C2", "Meses de caja", mc_txt, f"Colchón razonable ({mc_txt} de gasto). Prestar con línea ≤ 0,5 meses de gasto y covenant de liquidez ≥ 0,5 meses.")

        # la proyección solo puede endurecer (la primera regla que aplica manda). Manda la tensión (umbral de la política);
        # la rotura (caja < 0) se informa, pero en el panel casi nunca ocurre: la pyme retrasa pagos antes de entrar en negativo
        rot, ten = proj["rotura_h"], proj["tension_h"]
        fiab = proj.get("fiabilidad", "")
        fiab_txt = {"alta": " Las facturas explican bien el banco: proyección fiable.", "media": " Las facturas explican solo parte del banco: proyección orientativa.",
                    "baja": " Las facturas explican poco del banco: proyección poco fiable.", "sin facturas": " Sin ERP: medianas bancarias, proyección orientativa."}.get(fiab, "")
        umbral_txt = f"{es(STRESS_MONTHS, 2)} meses de gasto ({_money(proj['umbral_tension'], cur)})"
        if ten is not None and ten <= 2:
            if accion == "lend":
                accion = "watch"
            que = f"la cuenta se queda en negativo en {_meses(rot)}" if rot is not None and rot <= 2 else f"la liquidez baja de {umbral_txt} en {_meses(ten)}"
            razon("P", "Proyección de caja", f"tensión en {_meses(ten)}", f"Con los cobros y pagos ya comprometidos, {que}: hueco de {_money(proj['hueco_2m'], cur)} a 2 meses"
                  + (f" y de {_money(proj['hueco'], cur)} a {proj['horizon']}" if proj["horizon"] > 2 else "") + ". Cubrir el hueco con producto, no con deuda a ciegas." + fiab_txt)
        elif ten is not None:
            razon("P", "Proyección de caja", f"tensión en {_meses(ten)}", f"Con lo comprometido a día de hoy, la liquidez bajaría de {umbral_txt} dentro de {_meses(ten)}"
                  + (f" y la cuenta entraría en negativo en {rot}" if rot is not None else "") + f": hueco de {_money(proj['hueco'], cur)}." + fiab_txt)
        else:
            razon("P", "Proyección de caja", f"sin tensión en {proj['horizon']} meses", f"Con lo comprometido a día de hoy la liquidez se mantiene por encima de {umbral_txt} durante {proj['horizon']} meses." + fiab_txt)

        # C8 · cobertura: recorta importe, no nota
        recorte = []
        if "has_erp" in r and not bool(r.has_erp):
            recorte.append("sin ERP: no se ven facturas ni clientes (importe × 0,5)")
        if v("uncat_share") is not None and v("uncat_share") > 0.5:
            recorte.append("más de la mitad de los cobros sin categoría (importe × 0,5)")
        if r.month_idx < 3:
            recorte.append("menos de 3 meses de historia (importe ≤ 0,5 meses de gasto)")

        producto, prod_txt = self._producto(r, proj, accion, cur)
        necesita = ten is not None and ten <= 2
        meses_antelacion = ten
        return {"accion": accion, "accion_label": ACCIONES[accion], "regla": regla, "producto": producto, "producto_label": PRODUCTOS[producto],
                "producto_texto": prod_txt, "necesita_deuda_2m": bool(necesita), "meses_antelacion": meses_antelacion,
                "razones": razones, "recorte_importe": recorte,
                # C3/C9: circulante ≤ 1 mes de gasto; C2: ≤ 0,5 meses; C8 recorta a la mitad
                "importe_max": _num((1.0 if (mc or 0) >= 2 else 0.5) * burn * (0.5 if recorte else 1.0)) if accion == "lend" else None}

    def _producto(self, r, proj: dict, accion: str, cur: str) -> tuple[str, str]:
        """Producto según §5 de la política. Factoring SOLO sobre facturas emitidas pendientes NO vencidas."""
        v = lambda k: float(r[k]) if k in r and pd.notna(r[k]) else None
        ant, app = proj["anticipable"], proj["ap_pendiente"]
        mc = proj["meses_caja"]
        rot, ten = proj["rotura_h"], proj["tension_h"]
        necesidad = rot is not None or ten is not None
        cov = v("ar_id_coverage")
        contratados = set(proj["productos_contratados"])
        if accion == "sin_nota":
            return "ninguna", "Sin dato fiable no se recomienda producto: primero el dato."
        if accion == "decline":
            if ant["total"] > 0 and (cov or 0) >= 0.8:
                return "ninguna", (f"No se concede deuda. Única salida: anticipo con recurso sobre {ant['n']} facturas emitidas no vencidas "
                                   f"({_money(ant['total'], cur)}, clientes identificados al {es(100 * cov, 0)} %), que el financiador evaluará factura a factura.")
            return "ninguna", "No se concede deuda nueva. Sin facturas identificables que anticipar; solo garantía real o del grupo."
        ar_late, ar90, ap_late = v("ar_late_share"), v("ar_overdue_90_ratio"), v("ap_late_share")
        cobro_lento = (ar_late is not None and ar_late > 0.3) or (ar90 is not None and ar90 > 0.1)
        if ant["total"] > 0 and (necesidad or cobro_lento) and (mc is None or mc < 1):
            ya = " Ya tiene factoring contratado: ampliar la línea." if "factoring" in contratados else ""
            recurso = "con recurso" if (v("lost_share") or 0) > 0.5 else "sin recurso" if (v("hhi_ar_6m") or 1) < 0.3 else "con recurso"
            cobertura = f" Clientes identificados al {es(100 * cov, 0)} %." if cov is not None else ""
            hueco = proj.get("hueco_2m") or proj.get("hueco") or 0.0
            if hueco > 0:
                ratio = ant["anticipo_estimado"] / hueco
                cubre = (f" Cubre el hueco proyectado a 2 meses ({_money(hueco, cur)})." if ratio >= 1 else
                         f" Cubre el {es(100 * ratio, 0)} % del hueco proyectado a 2 meses ({_money(hueco, cur)}); el resto, línea o aplazar pagos no críticos.")
            else:
                cubre = ""
            return "factoring", (f"Anticipar {ant['n']} facturas emitidas pendientes que aún no han vencido: {_money(ant['total'], cur)} nominal, "
                                 f"≈{_money(ant['anticipo_estimado'], cur)} de anticipo al {int(ADVANCE_RATE * 100)} %, {recurso}.{cobertura}{cubre}{ya}")
        if ap_late is not None and ap_late > 0.3 and app["total"] > 0:
            ya = " Ya tiene confirming: revisar el límite." if "confirming" in contratados else ""
            return "confirming", (f"Paga tarde {es(100 * ap_late, 0)} % de las facturas de proveedores y tiene {app['n']} facturas recibidas por vencer "
                                  f"({_money(app['total'], cur)}): confirming pagado por el comprador, antes de que la mora llegue a la caja.{ya}")
        lim = float(r.lc_limit) if "lc_limit" in r and pd.notna(r.lc_limit) else 0.0
        growth = v("growth_vs_12m")
        nomina_ok = not (v("pay6") and float(r.payroll or 0) <= 0.1 * v("pay6"))
        db, lcu = v("debt_burden"), v("lc_util")
        if (db is not None and db > 0.1 and ("loan" in contratados or "mortgage" in contratados)) or (lcu is not None and lcu > 0.9):
            return "refi", (f"La cuota se lleva el {es(100 * (db or 0), 0)} % de los cobros" + (f" y la póliza va al {es(100 * lcu, 0)} %" if lcu else "")
                            + ": consolidar en préstamo a plazo para bajar la cuota mensual.")
        limite = _money(0.5 * (proj["gasto_mensual"] or 0), cur)
        if (mc is not None and mc < 1 or necesidad) and (growth is None or growth >= -0.2) and nomina_ok:
            if lim <= 0:
                return "linea", (f"Vive al día ({es(mc, 1)} meses de caja) sin póliza, cobra estable y paga la nómina: línea de circulante "
                                 f"≤ 0,5 meses de gasto ({limite}) con covenant de liquidez ≥ 0,5 meses.")
            if necesidad:
                return "linea", (f"Tiene póliza ({_money(lim, cur)}) pero el disponible no cubre el hueco proyectado de {_money(proj['hueco'], cur)}: "
                                 f"ampliarla hasta ≤ 0,5 meses de gasto ({limite}) con covenant de liquidez ≥ 0,5 meses.")
        if necesidad:
            motivo = "cobra un " + es(100 * (1 - np.exp(growth)), 0) + " % menos que su media anual" if growth is not None and growth < -0.2 else "no paga la nómina habitual" if not nomina_ok else "no hay facturas por vencer ni mora a proveedores que financiar"
            return "ninguna", (f"Hueco proyectado de {_money(proj['hueco'], cur)} pero ningún producto encaja sin colateral: {motivo}. "
                               "Opciones: anticipo sobre cobros bancarios conciliados, garantía del grupo o aplazar pagos no críticos.")
        if accion == "lend" and (v("activity_trend") or 0) > 0.2:
            return "ninguna", "No necesita deuda: la actividad crece (candidata a ampliar si pide)."
        return "ninguna", "No necesita producto ahora: la proyección no muestra hueco y cobra y paga a tiempo."

    # ------------------------------------------------------------ score vigente y explicación
    def score_at(self, cid: str, T, scored: pd.DataFrame | None = None) -> dict:
        scored = scored if scored is not None else self.scored
        if scored is None:
            return {}
        s = scored[(scored.company_id == cid)].sort_values("month")
        row = s[s.month == _month(T)]
        if row.empty:
            return {}
        row = row.iloc[0]
        f = self._row(cid, T)
        contrib = []
        if self.scorer is not None and hasattr(self.scorer, "weights_"):
            a, b = getattr(self.scorer, "scale_", (0.0, 1.0))
            for feat, w in self.scorer.weights_.items():
                c = f"ec_{feat}"
                if c not in row or pd.isna(row[c]):
                    continue
                neutro = b * 50.0 * float(w) + a * float(w)
                val = f[feat] if feat in f else None
                val = None if val is None or pd.isna(val) else float(val) + 0.0  # + 0.0: sin −0
                contrib.append({"feature": feat, "label": SPEC[feat][3], "pillar": SPEC[feat][0], "puntos": round(float(row[c]) - neutro, 2),
                                "valor": _num(val), "valor_texto": fmt_feature(feat, val)})
            # reglas de negocio (D15 inactividad, D36 liquidez): contribución aditiva sin neutro, solo si actúan
            for key, label in (("regla_inactividad", "Regla: sin movimientos"), ("regla_liquidez", "Regla: menos de medio mes de caja no es sano")):
                c = f"ec_{key}"
                if c in row and pd.notna(row[c]) and abs(float(row[c])) >= 0.05:
                    contrib.append({"feature": key, "label": label, "pillar": "regla", "puntos": round(float(row[c]), 2), "valor": None, "valor_texto": "activa"})
            contrib.sort(key=lambda x: -abs(x["puntos"]))
        try:
            exp = explain(scored, self.feats, cid, month=_month(T), scorer=self.scorer)
        except Exception:
            exp = None
        return {"score": round(float(row.score), 2), "band": band_of(float(row.score)), "confidence": _num(row.get("confidence")),
                "contribuciones": contrib, "explicacion": exp}

    # ------------------------------------------------------------ desenlace real (solo si T+2 está en el panel)
    def outcome(self, cid: str, T, h: int = 2, scored: pd.DataFrame | None = None) -> dict:
        T = _month(T)
        f = self._feat_by[cid]
        fut = f[(f.month > T) & (f.month <= _add_months(T, h))].sort_values("month")
        if len(fut) < h:
            return {"disponible": False, "motivo": f"T+{h} no está en el panel"}
        scored = scored if scored is not None else self.scored
        meses = []
        for x in fut.itertuples():
            burn = float(max(x.out3 / 3, x.out12 / 12)) if pd.notna(x.out3) else 0.0
            lim, drawn = (float(x.lc_limit) if pd.notna(x.lc_limit) else 0.0), (float(x.lc_drawn) if pd.notna(x.lc_drawn) else 0.0)
            avail = max(lim - drawn, 0.0) if lim > 0 else 0.0
            cash = float(x.cash_end) if pd.notna(x.cash_end) else 0.0
            liq = cash + avail
            sc = None
            if scored is not None:
                q = scored[(scored.company_id == cid) & (scored.month == x.month)]
                sc = round(float(q.score.iloc[0]), 2) if len(q) else None
            meses.append({"month": f"{x.month:%Y-%m}", "caja_real": _num(cash), "liquidez_real": _num(liq), "rotura": bool(cash < 0),
                          "tension": bool(liq < STRESS_MONTHS * burn), "cobros_reales": _num(x.inflow), "pagos_reales": _num(x.outflow),
                          "nominas_reales": _num(x.payroll), "cuotas_reales": _num(x.debt_service), "score": sc})
        return {"disponible": True, "meses": meses, "rotura_real": any(m["rotura"] for m in meses), "tension_real": any(m["tension"] for m in meses)}

    # ------------------------------------------------------------ todo junto
    def recommend(self, cid: str, T=None, horizon: int = 6, scored: pd.DataFrame | None = None) -> dict:
        if cid not in self._feat_by:
            raise KeyError(f"Empresa {cid} no encontrada")
        T = _month(T) if T is not None else self.months(cid)[-1]
        proj = self.project(cid, T, horizon)
        dec = self.decide(cid, T, proj, horizon)
        sc = self.score_at(cid, T, scored)
        out = self.outcome(cid, T, 2, scored)
        r = self._row(cid, T)
        panel_T = {k: _num(r[k]) for k in ("cash_end", "inflow", "outflow", "oper_in", "payroll", "debt_service", "tax", "lc_drawn", "lc_limit",
                                            "overdue_ar", "overdue_ap", "n_tx") if k in r}
        senales = {k: {"valor": _num(r[k]), "texto": fmt_feature(k, None if pd.isna(r[k]) else float(r[k]) + 0.0), "label": SPEC[k][3]}
                   for k in SPEC if k in r}
        senales["mc"] = {"valor": proj["meses_caja"], "texto": f"{es(proj['meses_caja'], 2)} meses" if proj["meses_caja"] is not None else "sin dato", "label": "Meses de caja (lineal, con póliza)"}
        return {"company_id": cid, "month": f"{T:%Y-%m}", "currency": proj["currency"], "has_erp": bool(r.has_erp) if "has_erp" in r else None,
                "meses_disponibles": [f"{m:%Y-%m}" for m in self.months(cid)],
                "score": sc.get("score"), "band": sc.get("band"), "confidence": sc.get("confidence"),
                "accion": dec["accion"], "producto": dec["producto"], "meses_antelacion": dec["meses_antelacion"],
                "decision": dec, "proyeccion": proj, "panel_T": panel_T, "senales": senales,
                "contribuciones": sc.get("contribuciones", []), "explicacion": sc.get("explicacion"), "desenlace": out}


# ---------------------------------------------------------------- validación no circular (empresas held-out por grupo)
def validate(n_splits: int = 5, fold: int = 0, h: int = 2, out_dir: Path = SALIDA, write: bool = True) -> dict:
    """Empresas de un fold de GroupKFold por group_id, nunca vistas por el scorer que las puntúa. En cada mes T la
    proyección recomienda sin ver el futuro; se comprueba en T+1..T+h si la caja se rompió o entró en tensión."""
    from sklearn.model_selection import GroupKFold
    from targets import add_events
    from evaluate import EVENTS
    from xray import HealthScorer
    raw = pl.read_parquet(ROOT / "data/panel.parquet")
    fp = add_events(add_features(raw)).to_pandas().sort_values(["company_id", "month"]).reset_index(drop=True)
    splits = list(GroupKFold(n_splits=n_splits).split(fp, groups=fp["group_id"].to_numpy()))
    tr, te = splits[fold]
    train, test = fp.iloc[tr], fp.iloc[te]
    obs = train.month <= train.month.max() - pd.DateOffset(months=6)
    scorer = HealthScorer().fit(train, train[EVENTS].where(obs, axis=0))
    held = sorted(test.company_id.unique())
    eng = ProactiveEngine(raw, scorer, feats=fp, scored=scorer.score_panel(fp))   # scorer ajeno al fold held-out
    rows = []
    for cid in held:
        ms = eng.months(cid)
        for T in ms:
            if _add_months(T, h) > ms[-1]:
                break
            r = eng._row(cid, T)
            dorm = int(r.months_since_last_tx) if pd.notna(r.months_since_last_tx) else 0
            ntx = int(r.n_tx) if pd.notna(r.n_tx) else 0
            if any(bool(r[k]) for k in ("dq_cash_sentinel", "has_drift", "dq_cash_implausible") if k in r) or dorm > 0 or ntx < 5:
                continue
            proj = eng.project(cid, T, h)                       # fórmula estricta (la servida)
            completa = eng.project(cid, T, h, completa=True)    # variante de referencia
            dec = eng.decide(cid, T, proj, h)
            out = eng.outcome(cid, T, h, eng.scored)
            sc = eng.scored[(eng.scored.company_id == cid) & (eng.scored.month == T)]
            rows.append({"company_id": cid, "group_id": r.group_id, "month": f"{T:%Y-%m}", "modo": proj["modo"], "fiabilidad": proj["fiabilidad"],
                         "caja_T": proj["caja_inicial"], "gasto_T": proj["gasto_mensual"] or 0.0, "mc_T": proj["meses_caja"],
                         "pred_rotura": proj["rotura_h"] is not None, "pred_tension": proj["tension_h"] is not None,
                         "pred_rotura_completa": completa["rotura_h"] is not None, "pred_tension_completa": completa["tension_h"] is not None,
                         "necesita_deuda": dec["necesita_deuda_2m"], "accion": dec["accion"], "producto": dec["producto"],
                         "real_rotura": out["rotura_real"], "real_tension": out["tension_real"], "hueco": proj["hueco"],
                         "caja_proj_h": proj["meses"][-1]["caja"], "caja_proj_h_completa": completa["meses"][-1]["caja"], "caja_real_h": out["meses"][-1]["caja_real"],
                         "score_oof": round(float(sc.score.iloc[0]), 2) if len(sc) else None, "to_eur": float(r.to_eur) if "to_eur" in r else 1.0,
                         "baseline_mc05": (proj["meses_caja"] is not None and proj["meses_caja"] < 0.5)})
    df = pd.DataFrame(rows)
    res = {"fold": fold, "n_splits": n_splits, "h": h, "n_empresas": int(df.company_id.nunique()), "n_grupos": int(df.group_id.nunique()),
           "n_empresa_mes": int(len(df)), "metricas": {}, "por_modo": {}, "por_fiabilidad": {}, "casos": [],
           "lectura": ("«sanas_hoy» = liquidez ≥ 0,5 meses de gasto y caja ≥ 0 en T (la condición healthy de targets.py:88): es donde la "
                       "proyección aporta, porque el nivel actual (baseline mc<0,5) no predice nada ahí. La rotura (caja<0) es tan rara "
                       "(≈1 % desde caja ≥ 0) que ni la proyección ni el nivel la aciertan: la pyme retrasa pagos antes de entrar en negativo.")}

    def _m(d: pd.DataFrame, pred: str, real: str) -> dict:
        p, y = d[pred].astype(bool), d[real].astype(bool)
        tp, fp_, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
        prec = tp / (tp + fp_) if tp + fp_ else None
        base = float(y.mean()) if len(d) else None
        return {"n": int(len(d)), "positivos_pred": int(p.sum()), "positivos_real": int(y.sum()), "tasa_base": round(base, 4) if base is not None else None,
                "precision": round(prec, 4) if prec is not None else None, "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                "npv": round(tn / (tn + fn), 4) if tn + fn else None, "lift": round(prec / base, 2) if prec is not None and base else None,
                "tp": tp, "fp": fp_, "fn": fn, "tn": tn}
    sano = df[(df.mc_T >= 0.5) & (df.caja_T >= 0)]
    res["metricas"] = {
        "tension_2m_sanas_hoy": _m(sano, "pred_tension", "real_tension"),
        "tension_2m_todas": _m(df, "pred_tension", "real_tension"),
        "necesita_deuda_2m_vs_tension": _m(df, "necesita_deuda", "real_tension"),
        "rotura_2m_sanas_hoy": _m(sano, "pred_rotura", "real_rotura"),
        "rotura_2m_todas": _m(df[df.caja_T >= 0], "pred_rotura", "real_rotura"),
        "variante_completa_tension_2m_sanas_hoy": _m(sano, "pred_tension_completa", "real_tension"),
        "baseline_mc<0.5_tension_2m_todas": _m(df, "baseline_mc05", "real_tension"),
        "baseline_mc<0.5_tension_2m_sanas_hoy": _m(sano, "baseline_mc05", "real_tension"),
    }
    for modo, d in df.groupby("modo"):
        s = d[(d.mc_T >= 0.5) & (d.caja_T >= 0)]
        res["por_modo"][modo] = {"tension_2m_sanas_hoy": _m(s, "pred_tension", "real_tension"), "tension_2m_todas": _m(d, "pred_tension", "real_tension")}
    for fiab, d in sano.groupby("fiabilidad"):
        res["por_fiabilidad"][fiab] = _m(d, "pred_tension", "real_tension")
    if len(df):
        for k, col in (("estricta", "caja_proj_h"), ("completa", "caja_proj_h_completa")):
            err = (df[col] - df.caja_real_h) * df.to_eur
            rel = (df[col] - df.caja_real_h).abs() / df.gasto_T.replace(0, np.nan)
            res[f"error_caja_h_eur_{k}"] = {"mediana_abs": _num(err.abs().median()), "p75_abs": _num(err.abs().quantile(0.75)), "mediana": _num(err.median()),
                                            "mediana_abs_en_meses_de_gasto": _num(rel.median())}
    # casos para la demo: anticipaciones desde sana con facturas fiables, controles sanos y errores (honestidad)
    df["hueco_eur"] = df.hueco.fillna(0) * df.to_eur
    tp = df[(df.mc_T >= 0.5) & (df.caja_T >= 0) & df.pred_tension & df.real_tension & (df.modo == "facturas")].copy()
    # primero los casos con producto que encaja (la demo enseña el factoring), luego por fiabilidad y tamaño del hueco
    tp["orden"] = tp.fiabilidad.map({"alta": 0, "media": 1}).fillna(2) + (tp.producto == "ninguna").astype(int) * 3
    tp = tp.sort_values(["orden", "hueco_eur"], ascending=[True, False]).drop_duplicates("company_id").head(6)
    tn = df[(df.mc_T >= 2) & ~df.pred_tension & ~df.real_tension & ~df.real_rotura & (df.accion == "lend")].drop_duplicates("company_id").head(3)
    fp_ = df[(df.mc_T >= 0.5) & (df.caja_T >= 0) & df.pred_tension & ~df.real_tension].sort_values("hueco_eur", ascending=False).drop_duplicates("company_id").head(2)
    fn = df[(df.mc_T >= 0.5) & (df.caja_T >= 0) & ~df.pred_tension & df.real_tension].drop_duplicates("company_id").head(2)
    for tipo, d in (("acierto", tp), ("control_sano", tn), ("falsa_alarma", fp_), ("no_detectada", fn)):
        for x in d.itertuples():
            res["casos"].append({"tipo": tipo, "company_id": x.company_id, "group_id": x.group_id, "month": x.month, "modo": x.modo, "fiabilidad": x.fiabilidad,
                                 "accion": x.accion, "producto": x.producto, "mc_T": x.mc_T, "hueco": x.hueco, "score_oof": x.score_oof,
                                 "pred_tension": bool(x.pred_tension), "pred_rotura": bool(x.pred_rotura), "real_rotura": bool(x.real_rotura), "real_tension": bool(x.real_tension)})
    res["empresas_held_out"] = held
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "validacion_proactiva.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
        df.to_parquet(out_dir / "validacion_proactiva.parquet", index=False)
    return res


# ---------------------------------------------------------------- CLI
def _engine_from_args(a) -> ProactiveEngine:
    import joblib
    if a.csv_dir:
        import panel as P
        pq = Path(a.csv_dir) / "_parquet"; pq.mkdir(parents=True, exist_ok=True)
        for f in Path(a.csv_dir).glob("*.csv"):
            pl.read_csv(f, infer_schema_length=100000, try_parse_dates=True).write_parquet(pq / f"{f.stem}.parquet")
        P.DATA = pq
        raw, data_dir = P.build_panel(), pq
    else:
        raw, data_dir = pl.read_parquet(ROOT / "data/panel.parquet"), DATA
    art = ROOT / "artifacts" / "xray.joblib"
    scorer = joblib.load(art)["scorer"] if art.exists() else None
    return ProactiveEngine(raw, scorer, data_dir=data_dir)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recommend", help="recomendación para una empresa en un mes T")
    r.add_argument("company_id"); r.add_argument("month", nargs="?"); r.add_argument("--horizon", type=int, default=6)
    r.add_argument("--csv-dir", help="carpeta con CSV del esquema del reto (empresas nuevas)")
    v = sub.add_parser("validate", help="precisión a 2 meses sobre empresas held-out por group_id")
    v.add_argument("--fold", type=int, default=0); v.add_argument("--splits", type=int, default=5); v.add_argument("--h", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "recommend":
        eng = _engine_from_args(a)
        print(json.dumps(eng.recommend(a.company_id, a.month, a.horizon), ensure_ascii=False, indent=1, default=str))
    else:
        res = validate(a.splits, a.fold, a.h)
        m = res["metricas"]
        print(f"held-out: {res['n_empresas']} empresas / {res['n_grupos']} grupos · {res['n_empresa_mes']} empresa-mes")
        for k, x in m.items():
            print(f"  {k}: n={x['n']} base={x['tasa_base']} precisión={x['precision']} recall={x['recall']} npv={x['npv']}")
        print(f"→ {SALIDA / 'validacion_proactiva.json'}")


if __name__ == "__main__":
    main()
