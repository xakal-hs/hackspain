"""Panel empresa x mes -> features + eventos.

El panel lo construye etl.py (CSV crudos -> data/panel.parquet). Aquí empieza el modelo.

Una sola entrada: `build()` lee `panel.parquet` y devuelve un DataFrame pandas con
una fila por (company_id, month) que contiene:

  - las 17 features que PUNTUAN (FEATURES)      -> entran en la nota
  - las features de CONTEXTO (CONTEXT)          -> OOD, confianza, reglas
  - los eventos a 6/3/2 meses (EVENTS/JUDGES)   -> 1 ocurre, 0 no ocurre, NaN no observable

Nada aquí conoce el modelo: esto es solo la tabla. El modelo vive en predict.py.

Las features NO se recortan: el scorer las convierte en percentiles (saturan solas)
y el indicador OOD necesita ver el valor crudo.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl

PANEL = Path(__file__).resolve().parent / "data/panel.parquet"

# ---------------------------------------------------------------------------
# Catálogo de features que puntúan.
#   pilar        agrupación de lectura
#   dir          +1 = más es mejor, -1 = más es peor (orienta el percentil)
#   zero_best    el cero es el mejor valor posible; los positivos se ordenan entre sí
#   label        texto para la explicación
#   formula      qué calcula, en una línea
# ---------------------------------------------------------------------------
FEATURES: dict[str, dict] = {
    "runway": dict(pilar="liquidez", dir=+1, zero_best=False, label="Meses de caja",
                   formula="log(1 + caja/gasto mensual), con signo; gasto = máx(media 3m, media 12m)"),
    "lc_util": dict(pilar="liquidez", dir=-1, zero_best=True, label="Uso de líneas de crédito",
                    formula="dispuesto / límite de las pólizas"),
    "oper_growth_12m": dict(pilar="rentabilidad", dir=+1, zero_best=False, label="Tendencia de cobros",
                            formula="log(cobros operativos 3m / cobros operativos 12m), en euros"),
    "debt_burden": dict(pilar="solvencia", dir=-1, zero_best=True, label="Carga de deuda",
                        formula="cuotas + intereses / entradas (3m)"),
    "payroll_cv": dict(pilar="solvencia", dir=-1, zero_best=False, label="Regularidad de nóminas",
                       formula="semidesviación a la baja de las nóminas / media (6m); sin nóminas = no aplica"),
    "ap_late_share": dict(pilar="disciplina", dir=-1, zero_best=True, label="Pagos tardíos a proveedores",
                          formula="% facturas recibidas vencidas >15 días sin pagar o pagadas tarde (3m)"),
    "ar_late_share": dict(pilar="disciplina", dir=-1, zero_best=True, label="Cobros tardíos de clientes",
                          formula="% facturas emitidas cobradas >15 días tarde o impagadas (3m)"),
    "ap_overdue_ratio": dict(pilar="disciplina", dir=-1, zero_best=True, label="Deuda vencida con proveedores",
                             formula="saldo AP vencido / salidas mensuales"),
    "ar_overdue_90_ratio": dict(pilar="disciplina", dir=-1, zero_best=True, label="Clientes morosos >60 días",
                                formula="saldo AR vencido >60 días / entradas mensuales"),
    "refund_rate": dict(pilar="disciplina", dir=-1, zero_best=True, label="Devoluciones de cobros",
                        formula="devoluciones / cobros operativos (3m)"),
    "activity_trend": dict(pilar="estabilidad", dir=+1, zero_best=False, label="Tendencia de actividad",
                           formula="log(movimientos 3m / movimientos medios 12m)"),
    "transfer_dep": dict(pilar="estabilidad", dir=-1, zero_best=True, label="Dependencia de transferencias",
                         formula="entradas por transferencia no operativa / entradas (3m)"),
    "hhi_ar_6m": dict(pilar="estabilidad", dir=-1, zero_best=False, label="Concentración de clientes",
                      formula="HHI de facturación a clientes (6m)"),
    "net_vol_6m": dict(pilar="estabilidad", dir=-1, zero_best=False, label="Volatilidad a la baja",
                       formula="semidesviación de los meses con flujo neto negativo / gasto mensual (6m)"),
    "cust_trend": dict(pilar="estabilidad", dir=+1, zero_best=False, label="Amplitud de clientes",
                       formula="log(clientes facturados 3m / clientes 12m)"),
    "lost_share": dict(pilar="estabilidad", dir=-1, zero_best=True, label="Facturación de clientes perdidos",
                       formula="% de la facturación de hace 3-12 meses de clientes sin facturas en los últimos 3"),
    "oper_persistence_6m": dict(pilar="estabilidad", dir=+1, zero_best=False, label="Persistencia de cobros",
                                formula="meses de los últimos 6 con cobros operativos ≥ 50 % de su mediana anual"),
}
SCORE_FEATURES = list(FEATURES)
PILLARS = ["liquidez", "rentabilidad", "solvencia", "disciplina", "estabilidad"]

# Peso a priori del prestamista, antes de calibrar. Se usa tal cual si no hay etiquetas.
PRIOR_W = {"runway": 3.0, "lc_util": 1.0, "oper_growth_12m": 1.5, "debt_burden": 1.0, "payroll_cv": 0.5,
           "ap_late_share": 1.5, "ar_late_share": 1.0, "ap_overdue_ratio": 1.0, "ar_overdue_90_ratio": 0.5,
           "refund_rate": 0.5, "activity_trend": 1.5, "transfer_dep": 0.5, "hhi_ar_6m": 0.5, "net_vol_6m": 0.5,
           "cust_trend": 1.0, "lost_share": 1.0, "oper_persistence_6m": 1.0}

# No puntúan: alimentan OOD, confianza y las reglas de banda.
CONTEXT = ["net_margin_6m", "growth_vs_12m", "log_scale", "fx_share", "uncat_share", "activity_log",
           "month_idx", "dormant", "months_since_last_tx"]
OOD_CONTEXT = ["log_scale", "fx_share", "activity_log"]  # los únicos de contexto con banda OOD

# Eventos que CALIBRAN los pesos (tres adversos + la cara positiva).
# El estrés se mide con la CAJA PROPIA, no con caja + póliza (docs/eventos.md:3): sumar la
# póliza premiaba estar ya endeudado y dejaba el 65,6 % de los casos sin nada que predecir.
# Evidencia y precio en README.md §2.
EVENTS = ["tension_np_raw_6m", "incumplimiento_6m", "caida_6m", "expansion_6m"]
POSITIVE_PREFIX = ("expansion", "cura")
# Jueces: se miden, nunca calibran.
JUDGES = ["tension_6m", "entrada_estres_2m", "rompe_caja_2m", "tension_entrada_6m",
          "impago_nomina_6m", "impago_ss_6m", "impago_iva_6m", "impago_cuota_6m", "impago_ap_6m",
          "cura_3m", "recaida_6m", "caida_3m_corto", "expansion_3m", "tension_grupo_6m"]

# Vetos: hechos de HOY que deciden por encima de la nota (docs/eventos.md:19-31).
# No predicen nada y no entran en el score; se aplican en decision.py.
VETOS = ["veto_caja_negativa", "veto_nomina_ausente", "veto_ss_ausente", "veto_iva_ausente",
         "veto_cuota_ausente", "veto_poliza_agotada", "veto_grupo_en_estres",
         "veto_dependencia_grupo"]
DEP_GRUPO = 0.5   # flujo intragrupo / flujo total (3m) por encima del cual la caja no es propia

H = 6                 # horizonte de los eventos, en meses
FISCAL = {1, 4, 7, 10}  # meses de liquidación de IVA
EPS = 1.0
KEY = dict(partition_by="company_id", order_by="month")
STICKY = ["late_share_ap", "late_share_ar", "hhi_ar_6m"]  # sin facturas que venzan: se arrastra el último dato


# ============================================================ features (polars)
def _roll(col: str, w: int) -> pl.Expr:
    """Suma equivalente a w meses aunque haya menos historia (evita el artefacto de arranque)."""
    return pl.col(col).rolling_mean(w, min_samples=1).over(**KEY) * w


def _log_ratio(num: pl.Expr, den: pl.Expr, eps: pl.Expr | float = EPS) -> pl.Expr:
    return ((num + eps) / (den + eps)).log()


def add_features(p: pl.DataFrame) -> pl.DataFrame:
    """Panel crudo -> + las 17 features y las de contexto."""
    p = p.sort("company_id", "month").with_columns(
        [pl.col(c).fill_null(strategy="forward", limit=3).over("company_id", order_by="month")
         for c in STICKY if c in p.columns])

    # ventanas móviles (el sufijo es el número de meses)
    p = p.with_columns(
        in3=_roll("inflow", 3), out3=_roll("outflow", 3), oper3=_roll("oper_in", 3), tr3=_roll("transfer_in", 3),
        pay3=_roll("payroll", 3), debt3=_roll("debt_service", 3), ref3=_roll("refunds", 3), n3=_roll("n_tx", 3),
        in6=_roll("inflow", 6), out6=_roll("outflow", 6), in12=_roll("inflow", 12), out12=_roll("outflow", 12),
        oper12=_roll("oper_in", 12), n12=_roll("n_tx", 12), ff3=_roll("foreign_flow", 3),
        gf3=_roll("gross_flow", 3), gf12=_roll("gross_flow", 12), un3=_roll("uncat_in", 3),
        month_idx=pl.int_range(pl.len()).over(**KEY),
        net=pl.col("inflow") - pl.col("outflow"),
    )
    # suelo relativo al tamaño de la empresa (0,1 % del volumen mensual): invariancia de escala real
    p = p.with_columns(eps=pl.max_horizontal(pl.lit(1e-9), pl.col("gf12") / 12 * 1e-3))
    E = pl.col("eps")
    # gasto de referencia robusto: el mayor entre el reciente y el anual -> encogerse no infla la liquidez
    burn = pl.max_horizontal(pl.col("out3") / 3, pl.col("out12") / 12) + E
    pay6 = pl.col("payroll").rolling_mean(6, min_samples=3).over(**KEY)
    # caja centinela (artefacto del generador, >1e8 €): la caja reconstruida no es fiable -> sin dato
    cash_ok = ~pl.col("dq_cash_sentinel").fill_null(False) if "dq_cash_sentinel" in p.columns else pl.lit(True)

    f = p.with_columns(
        # --- liquidez
        runway=pl.when(cash_ok).then(pl.col("cash_end").sign() * (pl.col("cash_end").abs() / burn + 1).log()),
        lc_util=pl.when(pl.col("lc_limit") > 0).then(pl.col("lc_drawn") / pl.col("lc_limit")),
        # --- rentabilidad: la tendencia que puntúa es la de los cobros OPERATIVOS en euros;
        #     las entradas totales mezclan transferencias y financiación (quedan como contexto)
        oper_growth_12m=pl.when(pl.col("month_idx") >= 2).then(_log_ratio(pl.col("oper3") / 3, pl.col("oper12") / 12, E)),
        net_margin_6m=(pl.col("in6") - pl.col("out6")) / (pl.col("in6") + pl.col("out6") + E),
        growth_vs_12m=pl.when(pl.col("month_idx") >= 2).then(_log_ratio(pl.col("in3") / 3, pl.col("in12") / 12, E)),
        # --- solvencia: la nómina puntúa por su regularidad, no por su peso
        debt_burden=pl.col("debt3") / (pl.col("in3") + E),
        pay6=pay6,
        # --- disciplina (ERP)
        ap_late_share=pl.col("late_share_ap"),
        ar_late_share=pl.col("late_share_ar"),
        ap_overdue_ratio=pl.col("overdue_ap") / (pl.col("out3") / 3 + E),
        ar_overdue_90_ratio=pl.col("overdue_90_ar") / (pl.col("in3") / 3 + E),
        refund_rate=pl.col("ref3") / (pl.col("oper3") + E),
        # --- estabilidad y actividad
        activity_trend=pl.when(pl.col("month_idx") >= 2).then(_log_ratio(pl.col("n3") / 3, pl.col("n12") / 12)),
        transfer_dep=pl.col("tr3") / (pl.col("in3") + E),
        hhi_ar_6m=pl.col("hhi_ar_6m"),
        cust_trend=pl.when(pl.col("n_cust_12m") > 0).then(
            ((pl.col("n_cust_3m").fill_null(0) + 1) / (pl.col("n_cust_12m") + 1)).log()),
        lost_share=pl.col("lost_share"),
        # --- contexto
        uncat_share=pl.col("un3") / (pl.col("in3") + E),
        oper_share=pl.col("oper3") / (pl.col("in3") + E),
        log_scale=(pl.col("gf3") / 3 * pl.col("to_eur") + 1).log10(),   # tamaño en EUR con el tipo real
        fx_share=pl.col("ff3") / (pl.col("gf3") + E),
        activity_log=(pl.col("n3") + 1).log(),
        dormant=(pl.col("months_since_last_tx") > 0).cast(pl.Float64),
    )

    # semidesviaciones a la baja: solo penaliza lo que va a peor (la subida no penaliza)
    f = f.with_columns(neg2=pl.min_horizontal(pl.col("net"), pl.lit(0.0)) ** 2,
                       payneg2=pl.min_horizontal(pl.col("payroll") - pl.col("pay6"), pl.lit(0.0)) ** 2)
    med12 = pl.col("oper_in").rolling_median(12, min_samples=6).over(**KEY)
    f = f.with_columns(
        oper_persistence_6m=pl.when(med12.is_not_null()).then((pl.col("oper_in") >= 0.5 * med12).cast(pl.Float64))
                              .rolling_mean(6, min_samples=3).over(**KEY),
        net_vol_6m=(pl.col("neg2").rolling_mean(6, min_samples=3).over(**KEY).sqrt()
                    / (pl.max_horizontal(pl.col("out3") / 3, pl.col("out12") / 12) + pl.col("eps"))),
        payroll_cv=pl.when(pl.col("pay6") > 0).then(
            pl.col("payneg2").rolling_mean(6, min_samples=3).over(**KEY).sqrt() / pl.col("pay6")),
    )
    # 0/0 (empresa sin flujos) = sin dato, no NaN numérico
    return f.with_columns([pl.col(c).fill_nan(None) for c in SCORE_FEATURES + CONTEXT
                           if c in f.columns and f.schema[c] in (pl.Float64, pl.Float32)])


# ============================================================== eventos (pandas)
def _fwd_any(d: pd.DataFrame, flag: pd.Series, h: int = H) -> pd.Series:
    """1 si `flag` ocurre en alguno de los meses m+1..m+h de la misma empresa."""
    f = flag.astype(float).fillna(0).groupby(d.company_id)
    return (sum(f.shift(-k).fillna(0) for k in range(1, h + 1)) > 0).astype(float)


def _shift(s: pd.Series, by: pd.Series, k: int) -> pd.Series:
    # `shift` sobre bool deja object con NaN en los bordes: se pasa por el bool nullable
    # de pandas para rellenar sin el downcasting silencioso (deprecado en pandas 2, roto en 3).
    return s.groupby(by).shift(k).astype("boolean").fillna(False).astype(bool)


def add_events(d: pd.DataFrame) -> pd.DataFrame:
    """Requiere las columnas de add_features (out3, out12, month_idx...).

    Convenio de TODAS las etiquetas: 1 si el evento ocurre en la ventana futura,
    0 si no ocurre, NaN si el futuro no es observable o el evento no aplica a esa
    empresa. NaN no es 0: «no lo sé» nunca cuenta como «no pasó».
    """
    d = d.sort_values(["company_id", "month"]).reset_index(drop=True)
    cid, g = d.company_id, d.groupby("company_id")

    burn = np.maximum(d.out3 / 3, d.out12 / 12) + 1e-9
    # observable hasta m+6 Y la empresa sigue viva al final de la ventana (censura por apagado)
    fut_final = g["months_since_final_tx"].shift(-H)
    obs6 = fut_final.notna() & (fut_final == 0)
    # caja implausible (>50x el flujo anual): la reconstrucción falló, no etiquetamos
    gf12 = g["gross_flow"].transform(lambda x: x.rolling(12, min_periods=1).mean())
    implausible = d.cash_end.abs() > 50 * (gf12 + 1)

    # ---------------------------------------------------------------- E1 tensión de liquidez
    # liquidez del prestamista: caja + póliza disponible
    avail = (d.lc_limit - d.lc_drawn).clip(lower=0).where(d.lc_limit > 0, 0).fillna(0)
    liq = d.cash_end + avail
    stress = (liq < 0) | (liq / burn < 0.25)
    healthy = (liq / burn >= 0.5) & (liq >= 0)
    # cash pooling: la caja cuadra porque la tapa el grupo -> la fila no se etiqueta
    ig3 = g["intragroup_flow"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    gross3 = g["gross_flow"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    group_funded = ig3 / (gross3 + ig3 + 1) > 0.2

    valid = stress & ~implausible
    # estado persistente: tensión en ≥2 de 3 meses seguidos que arrancan en t
    persist = valid & (sum(_shift(valid, cid, -k).astype(int) for k in (1, 2)) >= 1) & g["month"].shift(-2).notna()
    d["tension_6m"] = _fwd_any(d, persist).where(obs6 & g["month"].shift(-(H + 2)).notna() & ~group_funded)

    # entrada en tensión DESDE sana: mide anticipación, no calibra (el nivel actual de caja no la predice)
    prior_ok = sum(_shift(healthy, cid, k).astype(int) for k in (1, 2, 3)) == 3
    onset = stress & prior_ok & ~implausible & ~group_funded
    confirmed = onset & (sum(_shift(stress, cid, -k).astype(int) for k in (1, 2, 3)) >= 2) & g["month"].shift(-3).notna()
    risk_set = healthy & obs6 & g["month"].shift(-(H + 3)).notna()
    d["tension_entrada_6m"] = _fwd_any(d, confirmed).where(risk_set)

    # ------------------------------------------------- E2 incumplimiento de obligación recurrente
    # el feed tiene que estar vivo: si no hay movimientos, la ausencia de pago no es un impago
    feed = (d.n_tx >= 5) & (d.outflow > 0) & ((d.uncat_in / (d.inflow + 1e-9)) < 0.8)

    def regular(col: str) -> pd.Series:
        """La obligación existe: pagada en ≥4 de los 6 meses anteriores."""
        pos = (d[col] > 0).astype(int).groupby(cid)
        return sum(pos.shift(k).fillna(0) for k in range(1, 7)) >= 4

    def missed_twice(col: str) -> pd.Series:
        miss = regular(col) & (d[col] <= 0) & feed
        return miss & (g[col].shift(-1) <= 0) & _shift(feed, cid, -1)

    fisc = d.month.dt.month.isin(FISCAL)
    taxpos = (d.tax > 0).where(fisc)
    tprev = [taxpos.groupby(cid).shift(3 * k) for k in (1, 2, 3)]
    reg_tax = sum(t.astype("boolean").fillna(False).astype(int) for t in tprev) >= 2
    miss_tax = fisc & reg_tax & (d.tax <= 0) & (tprev[0] == False) & feed  # noqa: E712
    has_tax = reg_tax.where(fisc).groupby(cid).ffill().astype("boolean").fillna(False).astype(bool)

    # La cuota de deuda NO entra en E2: sin calendario de cuotas (3 % de cobertura) no se distingue
    # impago de vencimiento o cambio de periodicidad. Se publica aparte como impago_cuota_6m.
    breach = missed_twice("payroll") | miss_tax
    d["incumplimiento_6m"] = _fwd_any(d, breach).where(obs6 & (regular("payroll") | has_tax))

    # --------------------------------------------------- E3 caída estructural de cobros
    gi = g["inflow"]
    base = gi.transform(lambda x: x.rolling(12, min_periods=9).median())
    F = pd.concat([gi.shift(-k) for k in range(1, H + 1)], axis=1)
    med_f = F.median(axis=1, skipna=False)
    no_rebound = F.iloc[:, 3:].median(axis=1) <= F.iloc[:, :3].median(axis=1)   # no vale el bache que rebota
    d["caida_6m"] = ((med_f < 0.5 * base) & no_rebound).astype(float).where(obs6 & base.notna() & med_f.notna())

    # --------------------------------------------- E4 expansión sostenida y autofinanciada
    go = g["oper_in"]
    base_o = go.transform(lambda x: x.rolling(12, min_periods=6).mean())
    Fo = pd.concat([go.shift(-k) for k in range(1, H + 1)], axis=1)
    mean_f = Fo.mean(axis=1, skipna=False)
    dcash = g["cash_end"].shift(-H) - d.cash_end
    self_funded = (g["lc_drawn"].shift(-H) - d.lc_drawn).fillna(0) <= 0.5 * dcash.clip(lower=0)
    incr = Fo.sum(axis=1) - H * base_o
    one_off = (Fo.max(axis=1) - base_o) > 0.5 * incr        # un pelotazo puntual no es expansión
    exp = (mean_f > 1.3 * base_o) & (dcash > 0) & self_funded & ~one_off & (d.caida_6m.fillna(0) == 0)
    d["expansion_6m"] = exp.astype(float).where(obs6 & base_o.notna() & mean_f.notna() & (d.month_idx >= 5))

    # ================================================== jueces (se miden, no calibran)
    # --- tensión no circular: caja PROPIA (sin póliza) y sin censurar al grupo.
    #     Quita la circularidad con lc_util, que es una de las features que puntúan.
    stress_np = (d.cash_end < 0) | (d.cash_end / burn < 0.25)
    healthy_np = (d.cash_end / burn >= 0.5) & (d.cash_end >= 0)
    valid_np = stress_np & ~implausible
    persist_np = valid_np & (sum(_shift(valid_np, cid, -k).astype(int) for k in (1, 2)) >= 1) & g["month"].shift(-2).notna()
    d["tension_np_raw_6m"] = _fwd_any(d, persist_np).where(obs6 & g["month"].shift(-(H + 2)).notna())
    # estado del MES (no mira al futuro): es contra esto que se mide la antelación del aviso.
    # Las etiquetas *_6m no sirven para eso: ya son ventanas futuras y regalan meses de ventaja.
    d["estres_mes"] = persist_np.astype(float).where(~implausible)

    # --- anticipación a 2 meses desde SANA hoy: el conjunto en riesgo son las que aún están bien
    fut2 = g["months_since_final_tx"].shift(-2)
    risk2 = healthy_np & fut2.notna() & (fut2 == 0) & ~implausible & g["month"].shift(-2).notna()
    d["entrada_estres_2m"] = _fwd_any(d, persist_np, h=2).where(risk2)
    d["rompe_caja_2m"] = _fwd_any(d, d.cash_end < 0, h=2).where(risk2)

    # --- impago por tipo
    if "salary" in d.columns:
        d["impago_nomina_6m"] = _fwd_any(d, missed_twice("salary")).where(obs6 & regular("salary"))
        d["impago_ss_6m"] = _fwd_any(d, missed_twice("social_security")).where(obs6 & regular("social_security"))
    d["impago_cuota_6m"] = _fwd_any(d, missed_twice("debt_service")).where(obs6 & regular("debt_service"))
    d["impago_iva_6m"] = _fwd_any(d, miss_tax).where(obs6 & has_tax)
    if "overdue_ap" in d.columns:   # mora AP estructural: es un ESTADO crónico, no un impago puntual
        mora_ap = d.overdue_ap.fillna(0) >= 0.25 * burn
        erp = d["has_erp"] if "has_erp" in d.columns else pd.Series(False, index=d.index)
        d["impago_ap_6m"] = _fwd_any(d, mora_ap).where(obs6 & erp.fillna(False))

    # --- cura y recaída: la cara positiva de la tensión
    clean3 = (sum(_shift(~stress_np, cid, -k).astype(int) for k in (1, 2, 3)) == 3) & g["month"].shift(-3).notna()
    d["cura_3m"] = (stress_np & clean3).astype(float).where(g["month"].shift(-3).notna())
    exited = _shift(stress_np, cid, 1) & ~stress_np
    d["recaida_6m"] = _fwd_any(d, stress_np).where(exited & obs6 & g["month"].shift(-H).notna())

    # --- variantes de historia corta: existen ya en empresas nuevas (desde el mes 3)
    fut3 = g["months_since_final_tx"].shift(-3)
    obs3 = fut3.notna() & (fut3 == 0)
    base_c = gi.transform(lambda x: x.rolling(12, min_periods=3).median())
    med_f3 = pd.concat([gi.shift(-k) for k in range(1, 4)], axis=1).median(axis=1, skipna=False)
    d["caida_3m_corto"] = (med_f3 < 0.5 * base_c).astype(float).where(obs3 & base_c.notna() & med_f3.notna())
    base_o3 = go.transform(lambda x: x.rolling(12, min_periods=3).mean())
    Fo3 = pd.concat([go.shift(-k) for k in range(1, 4)], axis=1)
    mean_f3 = Fo3.mean(axis=1, skipna=False)
    dcash3 = g["cash_end"].shift(-3) - d.cash_end
    self_funded3 = (g["lc_drawn"].shift(-3) - d.lc_drawn).fillna(0) <= 0.5 * dcash3.clip(lower=0)
    exp3 = (mean_f3 > 1.3 * base_o3) & (dcash3 > 0) & self_funded3 & (d.caida_3m_corto.fillna(0) == 0)
    d["expansion_3m"] = exp3.astype(float).where(obs3 & base_o3.notna() & mean_f3.notna() & (d.month_idx >= 2))

    # ================================================== vetos (docs/eventos.md:19-31)
    # Hechos de HOY que deciden por encima del score. No son predicciones ni entran en la
    # nota: son la respuesta a «¿presto este mes?» cuando la respuesta es no, da igual la nota.
    # Aquí solo se calculan los hechos; el texto y la acción están en decision.py.
    racha_neg = d.groupby("company_id")["cash_end"].transform(
        lambda x: (x < 0).groupby((x >= 0).cumsum()).cumsum())
    d["racha_caja_negativa"] = racha_neg
    # La caja negativa NO es veto automático (eventos.md:17): el 54 % de las rachas se cura en
    # un mes. Veta a partir del segundo mes seguido, que ya es un desfase y no un despiste.
    d["veto_caja_negativa"] = (racha_neg >= 2) & ~implausible
    # Impagos de obligaciones que SÍ pagaba: la señal llega antes que la caja negativa.
    for name, col in [("nomina", "payroll"), ("ss", "social_security"), ("cuota", "debt_service")]:
        if col in d.columns:
            d[f"veto_{name}_ausente"] = regular(col) & (d[col] <= 0) & feed
    d["veto_iva_ausente"] = (fisc & reg_tax & (d.tax <= 0) & feed).fillna(False)
    # Póliza agotada con caja corta: no ampliar (eventos.md:22)
    lc_util = (d.lc_drawn / d.lc_limit).where(d.lc_limit > 0)
    d["veto_poliza_agotada"] = (lc_util > 0.9).fillna(False) & (d.cash_end / burn < 0.5)
    # Vive del grupo: más de la mitad de su flujo es intragrupo. Aviso, no bloqueo — y el
    # signo es el contrario del que se suponía: depender del grupo NO protege (README §6).
    d["veto_dependencia_grupo"] = d.intragroup_share_3m.fillna(0) > DEP_GRUPO

    # --- tensión del grupo: diagnóstico, NO sustituye a la nota de la entidad
    if "group_id" in d.columns:
        gg = (pd.DataFrame({"group_id": d.group_id.values, "month": d.month.values,
                            "cash": d.cash_end.values, "burn": burn.values})
              .groupby(["group_id", "month"], as_index=False).agg(cash_g=("cash", "sum"), burn_g=("burn", "sum")))
        gg["tension_grupo_mes"] = (gg.cash_g < 0) | (gg.cash_g / (gg.burn_g + 1e-9) < 0.25)
        d = (d.merge(gg[["group_id", "month", "tension_grupo_mes"]], on=["group_id", "month"], how="left")
               .sort_values(["company_id", "month"]).reset_index(drop=True))
        d["tension_grupo_mes"] = d["tension_grupo_mes"].fillna(False).astype(bool)
        d["tension_grupo_6m"] = _fwd_any(d, d.tension_grupo_mes).where(obs6)
        d["veto_grupo_en_estres"] = d["tension_grupo_mes"]   # el grupo no rescata si también está seco
    for v in VETOS:
        d[v] = d[v].fillna(False).astype(bool) if v in d.columns else False
    return d


# ===================================================================== entrada
def build(path: Path | str = PANEL) -> pd.DataFrame:
    """panel.parquet -> DataFrame con features + eventos, ordenado por (empresa, mes)."""
    return add_events(add_features(pl.read_parquet(path)).to_pandas())


def observable(d: pd.DataFrame, cutoff: pd.Timestamp | None = None) -> pd.Series:
    """Máscara de filas cuyo evento a 6 meses YA se había observado en `cutoff`.

    Es el único guardián contra la fuga temporal al calibrar: en el corte de 2026-02
    solo se puede aprender de meses <= 2025-08, porque su futuro ya ocurrió.
    """
    cutoff = d.month.max() if cutoff is None else pd.Timestamp(cutoff)
    return d.month <= cutoff - pd.DateOffset(months=H)


def labels(d: pd.DataFrame, cutoff: pd.Timestamp | None = None) -> pd.DataFrame:
    """Las columnas de evento enmascaradas por `observable` — lo que se le pasa a fit()."""
    return d[EVENTS].where(observable(d, cutoff), axis=0)


if __name__ == "__main__":
    d = build()
    print(f"{len(d):,} filas · {d.company_id.nunique()} empresas · {d.month.min():%Y-%m} → {d.month.max():%Y-%m}")
    cols = [c for c in EVENTS + JUDGES if c in d.columns]
    print(pd.DataFrame({"etiquetadas": d[cols].notna().sum(), "tasa": d[cols].mean().round(3)}).to_string())
