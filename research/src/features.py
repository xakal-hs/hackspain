"""Features adimensionales por empresa x mes.

No se recortan aquí: el scorer las convierte en percentiles (saturan en 0/100) y el
indicador OOD necesita ver el valor crudo (D16). Decisiones en research/DECISIONS.md.
"""
import polars as pl

EPS = 1.0
KEY = dict(partition_by="company_id", order_by="month")


def _roll(col: str, w: int) -> pl.Expr:
    # suma equivalente a w meses aunque haya menos historia (evita artefacto de arranque, D06)
    return pl.col(col).rolling_mean(w, min_samples=1).over(**KEY) * w


def _safe_log_ratio(num: pl.Expr, den: pl.Expr, eps: pl.Expr | float = EPS) -> pl.Expr:
    return ((num + eps) / (den + eps)).log()


STICKY = ["late_share_ap", "late_share_ar", "hhi_ar_6m"]  # sin facturas que venzan en la ventana: se arrastra el último dato (D19)


def add_features(p: pl.DataFrame) -> pl.DataFrame:
    p = p.sort("company_id", "month").with_columns(
        [pl.col(c).fill_null(strategy="forward", limit=3).over("company_id", order_by="month") for c in STICKY if c in p.columns])
    p = p.with_columns(
        in3=_roll("inflow", 3), out3=_roll("outflow", 3), oper3=_roll("oper_in", 3), tr3=_roll("transfer_in", 3),
        pay3=_roll("payroll", 3), debt3=_roll("debt_service", 3), ref3=_roll("refunds", 3), n3=_roll("n_tx", 3),
        in6=_roll("inflow", 6), out6=_roll("outflow", 6), in12=_roll("inflow", 12), out12=_roll("outflow", 12),
        n12=_roll("n_tx", 12), ff3=_roll("foreign_flow", 3), gf3=_roll("gross_flow", 3), gf12=_roll("gross_flow", 12),
        un3=_roll("uncat_in", 3),
        month_idx=pl.int_range(pl.len()).over(**KEY), net=pl.col("inflow") - pl.col("outflow"),
    )
    # suelo relativo a la escala de la empresa (0,1 % del volumen mensual medio): invariancia de escala real (D16)
    p = p.with_columns(eps=pl.max_horizontal(pl.lit(1e-9), pl.col("gf12") / 12 * 1e-3))
    EPSC = pl.col("eps")
    # base de gasto robusta: la mayor entre la media reciente y la anual -> encogerse no infla la liquidez (D09)
    burn = pl.max_horizontal(pl.col("out3") / 3, pl.col("out12") / 12) + EPSC
    pay6 = pl.col("payroll").rolling_mean(6, min_samples=3).over(**KEY)
    f = p.with_columns(
        # Liquidez
        runway=pl.col("cash_end").sign() * (pl.col("cash_end").abs() / burn + 1).log(),
        lc_util=pl.when(pl.col("lc_limit") > 0).then(pl.col("lc_drawn") / pl.col("lc_limit")),
        # Rentabilidad (ventanas largas: menos reversión a la media, D08); el margen ya no puntúa (D27)
        net_margin_6m=(pl.col("in6") - pl.col("out6")) / (pl.col("in6") + pl.col("out6") + EPSC),
        growth_vs_12m=pl.when(pl.col("month_idx") >= 2).then(_safe_log_ratio(pl.col("in3") / 3, pl.col("in12") / 12, EPSC)),
        # Solvencia: en deuda y reembolsos cero es bueno (two-part en el scorer). La nómina puntúa por su regularidad,
        # no por su peso: nóminas/entradas dependía del tamaño (rho −0,46) y su signo contradecía a los eventos (D26)
        debt_burden=pl.col("debt3") / (pl.col("in3") + EPSC),
        pay6=pay6,
        # Disciplina (ERP)
        ap_late_share=pl.col("late_share_ap"), ar_late_share=pl.col("late_share_ar"),
        ap_overdue_ratio=pl.col("overdue_ap") / (pl.col("out3") / 3 + EPSC),
        ar_overdue_90_ratio=pl.col("overdue_90_ar") / (pl.col("in3") / 3 + EPSC),
        refund_rate=pl.col("ref3") / (pl.col("oper3") + EPSC),
        # Estabilidad y actividad
        activity_trend=pl.when(pl.col("month_idx") >= 2).then(_safe_log_ratio(pl.col("n3") / 3, pl.col("n12") / 12)),
        transfer_dep=pl.col("tr3") / (pl.col("in3") + EPSC),
        uncat_share=pl.col("un3") / (pl.col("in3") + EPSC),
        hhi_ar_6m=pl.col("hhi_ar_6m"),
        oper_share=pl.col("oper3") / (pl.col("in3") + EPSC),
        cust_trend=pl.when(pl.col("n_cust_12m") > 0).then(((pl.col("n_cust_3m").fill_null(0) + 1) / (pl.col("n_cust_12m") + 1)).log()),
        lost_share=pl.col("lost_share"),
        # Contexto (no puntúa, alimenta OOD/confianza y el forecaster)
        log_scale=(pl.col("gf3") / 3 * pl.col("to_eur") + 1).log10(),  # tamaño en EUR con tipo real (D03)
        fx_share=pl.col("ff3") / (pl.col("gf3") + EPSC),
        activity_log=(pl.col("n3") + 1).log(),
        dormant=(pl.col("months_since_last_tx") > 0).cast(pl.Float64),
    )
    # volatilidad a la baja: semidesviación de los meses con flujo neto negativo / gasto mensual (D25)
    f = f.with_columns(neg2=pl.min_horizontal(pl.col("net"), pl.lit(0.0)) ** 2,
                       payneg2=pl.min_horizontal(pl.col("payroll") - pl.col("pay6"), pl.lit(0.0)) ** 2)
    med12 = pl.col("oper_in").rolling_median(12, min_samples=6).over(**KEY)
    f = f.with_columns(
        # persistencia operativa: meses de los últimos 6 con cobros operativos ≥ 50 % de su mediana anual (R07)
        oper_persistence_6m=pl.when(med12.is_not_null()).then((pl.col("oper_in") >= 0.5 * med12).cast(pl.Float64))
                            .rolling_mean(6, min_samples=3).over(**KEY),
        net_vol_6m=(pl.col("neg2").rolling_mean(6, min_samples=3).over(**KEY).sqrt()
                    / (pl.max_horizontal(pl.col("out3") / 3, pl.col("out12") / 12) + pl.col("eps"))),
        # nóminas que faltan o bajan frente a su media 6m (semidesviación a la baja / media); la subida (contratar) no penaliza
        payroll_cv=pl.when(pl.col("pay6") > 0).then(pl.col("payneg2").rolling_mean(6, min_samples=3).over(**KEY).sqrt() / pl.col("pay6")),
    )
    # 0/0 (empresa sin flujos) = sin dato, no NaN numérico
    return f.with_columns([pl.col(c).fill_nan(None) for c in SCORE_FEATURES + CONTEXT_FEATURES
                           if c in f.columns and f.schema[c] in (pl.Float64, pl.Float32)])


SCORE_FEATURES = ["runway", "lc_util", "growth_vs_12m", "debt_burden", "payroll_cv",
                  "ap_late_share", "ar_late_share", "ap_overdue_ratio", "ar_overdue_90_ratio", "refund_rate",
                  "activity_trend", "transfer_dep", "hhi_ar_6m", "net_vol_6m", "cust_trend", "lost_share", "oper_persistence_6m"]
# net_margin_6m sale del score (AUC 0,47-0,53 frente a E1-E4, peso 0; D27) y queda como contexto para el forecaster
CONTEXT_FEATURES = ["net_margin_6m", "log_scale", "fx_share", "uncat_share", "activity_log", "month_idx", "dormant", "months_since_last_tx"]
DRIVERS = ["inflow", "outflow", "cash_end", "payroll", "debt_service", "overdue_ap", "overdue_ar",
           "late_share_ap", "late_share_ar", "n_tx", "refunds", "lc_drawn"]
