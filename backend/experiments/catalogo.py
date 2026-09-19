"""Las 42 variables del catálogo a priori (docs/explicacion_pesos.md) como features puntuables.

El backend puntúa 17 features con pesos CALIBRADOS (logística con signo restringido).
El documento divulgativo describe otra cosa: 42 variables en 7 pilares puntuables con
pesos A PRIORI (criticidad × evidencia × cobertura × persistencia). Este módulo
implementa ese catálogo con el mismo contrato que `preprocessing.FEATURES`, para poder
medir las dos cosas por separado:

    features del doc  x  pesos del doc     -> 2x2 con el backend actual (medir.py)

Reglas que me impongo para que la comparación sea limpia:

1. Las features COMPARTIDAS se reutilizan tal cual de `preprocessing.add_features`.
   Ni una redefinición: si `runway` cambiara, el 2x2 dejaría de medir lo que dice medir.
2. Las nuevas se calculan sobre las ventanas que ya trae el panel (in3, out3, oper3...),
   no con ventanas propias.
3. Donde el doc no puede implementarse literalmente, se implementa lo más cerca posible
   y queda anotado en DESVIACIONES. Nada se inventa en silencio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
PESOS = HERE / "pesos_doc.json"
sys.path.insert(0, str(HERE.parent))        # el backend es el paquete; esto es un experimento

import preprocessing as pre  # noqa: E402

# El doc llama `debt_service_burden` a lo que el score llama `debt_burden` (misma variable,
# explicacion_pesos.md:433). Y agrupa los cuatro impagos en una sola fila.
ALIAS = {"debt_service_burden": "debt_burden", "impago_nomina / ss / iva / cuota": "impagos_ausentes"}

# Mapeo para el brazo B (pesos del doc sobre las 17 features actuales). Las dos features del
# backend que el doc no tiene: `oper_growth_12m` es el mismo concepto que `growth_vs_12m`
# (cobros 3m vs 12m, uno operativo y el otro total); `transfer_dep` vive en OBS, que NO puntúa.
B_MAP = {"oper_growth_12m": "growth_vs_12m", "transfer_dep": None}

DESVIACIONES = [
    ("payee_concentration", "el doc lo saca del counterparty_id de las transacciones de salida, "
                            "pero solo el 10,4 % de esas filas lo trae. Se usa el HHI de los "
                            "counterparties de las facturas RECIBIDAS (98,9 % de cobertura, 783 "
                            "empresas) y se cae a las transacciones cuando no hay ERP."),
    ("debt_utilization", "debt_products.csv es una foto sin fecha: la variable es constante en el "
                         "tiempo para cada empresa. Aporta ordenación entre empresas, cero trayectoria."),
    ("factoring_confirming", "misma foto estática que debt_utilization."),
    ("interest_rate", "media del annual_interest_rate_or_spread del calendario (3 % de cobertura), "
                      "también estática."),
    ("schedule_pressure", "cuota estimada = outstanding_balance / total_periods, y vence en el mes "
                          "si next_payment_date cae dentro de los 3 meses siguientes. 40 empresas."),
    ("credit_notes", "invoices.document_type == 'note' sobre el lado AR."),
    ("cash_end", "el doc la define como nivel de caja. Se convierte a EUR con el tipo real; sigue "
                 "siendo un nivel, es decir en buena parte un proxy de tamaño."),
    ("burn_rate", "igual: nivel de gasto mensual en EUR, proxy de tamaño con signo negativo."),
    ("impagos_ausentes", "suma de los cuatro hechos de impago del mes (nómina/SS/IVA/cuota) tal como "
                         "los calcula el backend para los vetos. Como feature es el veto metido en "
                         "la nota, que es justo lo que el propio doc dice que NO hay que hacer."),
]


# ------------------------------------------------------------------ pesos del doc
def doc_weights() -> dict[str, float]:
    """var -> peso (%) del catálogo. Suma 99,9 por el redondeo a un decimal del generador."""
    raw = json.loads(PESOS.read_text())["vars"]
    return {ALIAS.get(v["var"], v["var"]): v["w"] for v in raw if v["w"] > 0}


def doc_weights_17() -> dict[str, float]:
    """Brazo B: los pesos del doc proyectados sobre las 17 features del backend."""
    W = doc_weights()
    out = {}
    for f in pre.SCORE_FEATURES:
        src = B_MAP.get(f, f)
        out[f] = W.get(src, 0.0) if src else 0.0
    return out


# ------------------------------------------------- columnas que no están en el panel
def _extras() -> pd.DataFrame:
    """Lo que el catálogo necesita y el panel no trae. Un escaneo por fichero.

    Devuelve columnas por (company_id, month) para las mensuales y por company_id para
    las que en el dataset son una foto estática (deuda).
    """
    inv = pl.read_parquet(DATA / "invoices.parquet", columns=[
        "company_id", "issuance_date", "amount", "document_type", "counterparty_id"])
    inv = inv.with_columns(month=pl.col("issuance_date").dt.truncate("1mo").cast(pl.Datetime("us")))

    # notas de crédito (lado AR): pueden anular facturas ya emitidas
    notas = (inv.filter((pl.col("document_type") == "note") & (pl.col("amount") > 0))
             .group_by("company_id", "month").agg(credit_note_amt=pl.col("amount").abs().sum()))

    # concentración de proveedores: HHI de los counterparties de las facturas RECIBIDAS (6m
    # rodantes se hace después en pandas; aquí el detalle mensual por contraparte)
    ap = (inv.filter((pl.col("amount") < 0) & pl.col("counterparty_id").is_not_null())
          .group_by("company_id", "month", "counterparty_id").agg(amt=pl.col("amount").abs().sum()))

    tx = pl.read_parquet(DATA / "transactions.parquet",
                         columns=["company_id", "date", "amount", "counterparty_id"])
    txn = (tx.filter((pl.col("amount") < 0) & pl.col("counterparty_id").is_not_null())
           .with_columns(month=pl.col("date").dt.truncate("1mo").cast(pl.Datetime("us")))
           .group_by("company_id", "month", "counterparty_id").agg(amt=pl.col("amount").abs().sum()))

    # deuda: foto estática, sin dimensión temporal en el dataset
    dp = pl.read_parquet(DATA / "debt_products.parquet")
    deuda = dp.group_by("company_id").agg(
        granted_all=pl.col("granted").abs().sum(),
        outstanding_all=pl.col("outstanding").abs().sum(),
        granted_fact=pl.col("granted").abs().filter(pl.col("type").is_in(["factoring", "confirming"])).sum())
    dsc = pl.read_parquet(DATA / "debt_schedule_config.parquet")
    cuota = dsc.with_columns(
        cuota=pl.col("outstanding_balance").abs() / pl.max_horizontal(pl.col("total_periods"), pl.lit(1))
    ).group_by("company_id").agg(
        cuota_prox=pl.col("cuota").sum(), next_pay=pl.col("next_payment_date").min(),
        tipo_interes=pl.col("annual_interest_rate_or_spread").mean())
    return {"notas": notas.to_pandas(), "ap_cp": ap.to_pandas(), "tx_cp": txn.to_pandas(),
            "deuda": deuda.to_pandas(), "cuota": cuota.to_pandas()}


def _hhi_rolling(cp: pd.DataFrame, months: list[pd.Timestamp], win: int = 6) -> pd.DataFrame:
    """HHI por (empresa, mes) sobre una ventana de `win` meses de importes por contraparte."""
    cp = cp.copy()
    cp["month"] = pd.to_datetime(cp["month"])
    idx = {m: i for i, m in enumerate(months)}
    cp["mi"] = cp["month"].map(idx)
    cp = cp.dropna(subset=["mi"])
    rows = []
    for (cid, cpid), g in cp.groupby(["company_id", "counterparty_id"], sort=False):
        for mi, amt in zip(g.mi.astype(int), g.amt):
            for k in range(win):                       # cada mes contribuye a los `win` siguientes
                if mi + k < len(months):
                    rows.append((cid, mi + k, cpid, amt))
    if not rows:
        return pd.DataFrame(columns=["company_id", "month", "hhi"])
    v = pd.DataFrame(rows, columns=["company_id", "mi", "cp", "amt"])
    v = v.groupby(["company_id", "mi", "cp"], as_index=False)["amt"].sum()
    tot = v.groupby(["company_id", "mi"])["amt"].transform("sum")
    v["sh2"] = (v["amt"] / tot.replace(0, np.nan)) ** 2
    out = v.groupby(["company_id", "mi"], as_index=False)["sh2"].sum().rename(columns={"sh2": "hhi"})
    out["month"] = [months[i] for i in out.mi]
    return out.drop(columns="mi")


# ------------------------------------------------------------------- las features
def _g(d: pd.DataFrame, col: str):
    return d.groupby("company_id")[col]


def add_catalog(d: pd.DataFrame) -> pd.DataFrame:
    """Panel ya procesado por preprocessing.build() -> + las variables nuevas del catálogo."""
    d = d.sort_values(["company_id", "month"]).reset_index(drop=True).copy()
    E = d["eps"]
    burn = np.maximum(d.out3 / 3, d.out12 / 12) + E
    to_eur = d.get("to_eur", pd.Series(1.0, index=d.index)).fillna(1.0)
    cash_ok = ~d.get("dq_cash_sentinel", pd.Series(False, index=d.index)).fillna(False)

    # --- LIQ
    d["cash_end_eur"] = (d.cash_end * to_eur).where(cash_ok)
    d["burn_rate"] = burn * to_eur
    d["cash_negative"] = (d.cash_end < 0).astype(float).where(cash_ok)
    d["cash_trend_3m"] = (d.cash_end - _g(d, "cash_end").shift(3)).where(cash_ok) / burn
    avail = (d.lc_limit - d.lc_drawn).clip(lower=0).where(d.lc_limit > 0, 0).fillna(0)
    d["liquidity_available"] = avail / burn

    # --- CF (oper_share, net_margin_6m, growth_vs_12m ya vienen de add_features como contexto)
    # --- AR
    ar3 = _g(d, "ar_issued").transform(lambda x: x.rolling(3, min_periods=1).sum())
    d["billing_to_cash"] = ar3 / (d.oper3 + E)
    d["overdue_ar_ratio"] = d.overdue_ar / (d.in3 / 3 + E)
    d["lost_accel"] = d.lost_share - _g(d, "lost_share").shift(3)

    # --- AP
    d["payroll_burden"] = d.pay3 / (d.in3 + E)

    # --- DEBT
    pay_pos = (d.payroll > 0).astype(float)
    d["payroll_continuity_6m"] = (pay_pos.groupby(d.company_id).transform(lambda x: x.rolling(6, min_periods=3).mean())
                                  .where(_g(d, "payroll").transform(lambda x: x.rolling(6, min_periods=3).max()) > 0))
    vetos = ["veto_nomina_ausente", "veto_ss_ausente", "veto_iva_ausente", "veto_cuota_ausente"]
    d["impagos_ausentes"] = sum(d[v].astype(float) for v in vetos if v in d.columns)
    fisc = d.month.dt.month.isin(pre.FISCAL)
    tax_miss = (fisc & (d.tax <= 0)).astype(float).where(fisc)
    d["tax_miss"] = (tax_miss.groupby(d.company_id).transform(lambda x: x.ffill())
                     .where(_g(d, "tax").transform(lambda x: x.rolling(12, min_periods=1).max()) > 0))
    dlc = (d.lc_drawn - _g(d, "lc_drawn").shift(3)).fillna(0)
    dcash = (d.cash_end - _g(d, "cash_end").shift(3))
    d["new_debt_vs_cash"] = (dlc.clip(lower=0) / burn).where(dcash < 0, 0.0)

    # --- SOLV
    d["interest_coverage"] = d.in3 / (d.debt3 + E)
    d["self_funding"] = (dcash - dlc) / burn

    # --- STAB
    down = (d.net_vol_6m * burn)                      # semidesviación a la baja en euros
    d["shock_vs_usual"] = (-np.minimum(d.net, 0)) / (down + E)
    up2 = np.maximum(d.net, 0) ** 2
    ups = up2.groupby(d.company_id).transform(lambda x: x.rolling(6, min_periods=3).mean()) ** 0.5
    d["vol_asymmetry"] = ups / (down + E)
    flags = [(d.oper_growth_12m < -0.2), (d.activity_trend < -0.2),
             (d.cust_trend < -0.1) | (d.lost_share > 0.2), (d.cash_trend_3m < -0.25) | (d.runway < np.log1p(0.5))]
    d["multi_signal_stress"] = sum(f.fillna(False).astype(float) for f in flags)

    # --- lo que viene de fuera del panel
    ex = _extras()
    months = sorted(d.month.unique())
    hhi_ap = _hhi_rolling(ex["ap_cp"], months).rename(columns={"hhi": "hhi_ap"})
    hhi_tx = _hhi_rolling(ex["tx_cp"], months).rename(columns={"hhi": "hhi_tx"})
    d = d.merge(hhi_ap, on=["company_id", "month"], how="left").merge(hhi_tx, on=["company_id", "month"], how="left")
    d["payee_concentration"] = d.hhi_ap.fillna(d.hhi_tx)

    notas = ex["notas"].rename(columns={"credit_note_amt": "nota_amt"})
    notas["month"] = pd.to_datetime(notas["month"])
    d = d.merge(notas, on=["company_id", "month"], how="left")
    d["nota_amt"] = d["nota_amt"].fillna(0.0)
    nota3 = _g(d, "nota_amt").transform(lambda x: x.rolling(3, min_periods=1).sum())
    d["credit_notes"] = (nota3 / (ar3 + E)).where(ar3 > 0)

    deu = ex["deuda"]
    d = d.merge(deu, on="company_id", how="left")
    d["debt_utilization"] = (d.outstanding_all / d.granted_all.replace(0, np.nan))
    d["factoring_confirming"] = (d.granted_fact / d.granted_all.replace(0, np.nan))
    cu = ex["cuota"]
    d = d.merge(cu, on="company_id", how="left")
    prox = (d.next_pay - d.month).dt.days
    d["schedule_pressure"] = (d.cuota_prox / burn).where(prox.between(-31, 92))
    d["interest_rate"] = d.tipo_interes

    return d.sort_values(["company_id", "month"]).reset_index(drop=True)


# --------------------------------------------- catálogo con el contrato de FEATURES
def _spec(pilar, dir_, zero_best, label):
    return dict(pilar=pilar, dir=dir_, zero_best=zero_best, label=label, formula="catálogo a priori")


CATALOG: dict[str, dict] = {
    # LIQ 24,2
    "cash_end_eur": _spec("LIQ", +1, False, "Dinero en la cuenta"),
    "runway": _spec("LIQ", +1, False, "Meses de caja"),
    "cash_trend_3m": _spec("LIQ", +1, False, "La cuenta se vacía (3m)"),
    "burn_rate": _spec("LIQ", -1, False, "Gasto mensual"),
    "cash_negative": _spec("LIQ", -1, True, "Cuenta en números rojos"),
    "liquidity_available": _spec("LIQ", +1, False, "Póliza sin usar"),
    # AR 20,2
    "lost_accel": _spec("AR", -1, False, "La pérdida de clientes se acelera"),
    "lost_share": _spec("AR", -1, True, "Facturación de clientes perdidos"),
    "cust_trend": _spec("AR", +1, False, "Amplitud de clientes"),
    "ar_overdue_90_ratio": _spec("AR", -1, True, "Clientes morosos >60 días"),
    "overdue_ar_ratio": _spec("AR", -1, True, "Facturas de clientes vencidas"),
    "hhi_ar_6m": _spec("AR", -1, False, "Concentración de clientes"),
    "billing_to_cash": _spec("AR", +1, False, "Cobros respaldados por factura"),
    "ar_late_share": _spec("AR", -1, True, "Tarda en cobrar (DSO)"),
    # DEBT 18,2
    "impagos_ausentes": _spec("DEBT", -1, True, "Deja de pagar algo que pagaba siempre"),
    "payroll_cv": _spec("DEBT", -1, False, "Nómina irregular"),
    "payroll_continuity_6m": _spec("DEBT", +1, False, "Paga la nómina todos los meses"),
    "lc_util": _spec("DEBT", -1, True, "Uso de la póliza"),
    "debt_burden": _spec("DEBT", -1, True, "Carga de deuda"),
    "new_debt_vs_cash": _spec("DEBT", -1, True, "Crédito nuevo con la caja cayendo"),
    "debt_utilization": _spec("DEBT", -1, False, "Deuda viva sobre concedida"),
    "schedule_pressure": _spec("DEBT", -1, False, "Vencimientos próximos"),
    "tax_miss": _spec("DEBT", -1, True, "Deja de pagar impuestos"),
    "factoring_confirming": _spec("DEBT", -1, True, "Adelanto de facturas con el banco"),
    "interest_rate": _spec("DEBT", -1, False, "Interés que le cobran"),
    # CF 14,1
    "oper_share": _spec("CF", +1, False, "Qué parte de lo que entra es cobro real"),
    "activity_trend": _spec("CF", +1, False, "Tendencia de actividad"),
    "oper_persistence_6m": _spec("CF", +1, False, "Persistencia de cobros"),
    "growth_vs_12m": _spec("CF", +1, False, "Factura más que su media anual"),
    "net_margin_6m": _spec("CF", +1, False, "Cobra más de lo que gasta"),
    # AP 9,6
    "payee_concentration": _spec("AP", -1, False, "Concentración de proveedores"),
    "ap_overdue_ratio": _spec("AP", -1, True, "Deuda vencida con proveedores"),
    "payroll_burden": _spec("AP", -1, False, "Peso de la nómina"),
    "ap_late_share": _spec("AP", -1, True, "Tarda en pagar (DPO)"),
    # STAB 10,1
    "multi_signal_stress": _spec("STAB", -1, True, "Señales encendidas a la vez"),
    "net_vol_6m": _spec("STAB", -1, False, "Volatilidad a la baja"),
    "vol_asymmetry": _spec("STAB", +1, False, "Volatilidad de ciclo, no de caída"),
    "shock_vs_usual": _spec("STAB", -1, False, "El golpe frente a sus meses malos"),
    "credit_notes": _spec("STAB", -1, True, "Notas de crédito"),
    "refund_rate": _spec("STAB", -1, True, "Devoluciones"),
    # SOLV 3,5
    "self_funding": _spec("SOLV", +1, False, "Crece sin pedir más crédito"),
    "interest_coverage": _spec("SOLV", +1, False, "Cobros sobre cuotas"),
}
# nombre en el doc -> nombre de la columna implementada
DOC_TO_COL = {"cash_end": "cash_end_eur", "overdue_ar": "overdue_ar_ratio"}
CATALOG_PILLARS = ["LIQ", "AR", "DEBT", "CF", "AP", "STAB", "SOLV"]


def catalog_weights() -> dict[str, float]:
    """Pesos del doc con los nombres de columna implementados. Suma 1 tras normalizar en fit()."""
    W = doc_weights()
    out = {DOC_TO_COL.get(k, k): v for k, v in W.items()}
    falta = set(CATALOG) - set(out)
    if falta:
        raise AssertionError(f"features del catálogo sin peso: {sorted(falta)}")
    sobra = set(out) - set(CATALOG)
    if sobra:
        raise AssertionError(f"pesos sin feature implementada: {sorted(sobra)}")
    return {f: out[f] for f in CATALOG}


def build() -> pd.DataFrame:
    return add_catalog(pre.build())


if __name__ == "__main__":
    d = build()
    W = catalog_weights()
    print(f"{len(d):,} filas · {len(CATALOG)} features del catálogo · peso total {sum(W.values()):.1f}")
    cob = pd.DataFrame({"peso": pd.Series(W), "cobertura": d[list(CATALOG)].notna().mean().round(3),
                        "pilar": pd.Series({f: s["pilar"] for f, s in CATALOG.items()})})
    print(cob.sort_values("peso", ascending=False).to_string())
    print("\nsin dato en ninguna fila:", [f for f in CATALOG if d[f].notna().sum() == 0])
