"""Eventos observables que anclan el score (D12): no hay etiquetas, pero sí hechos futuros medibles.

Se definen contra una base ANUAL (in12) para no confundir con reversión a la media de picos mensuales.
"""
import polars as pl

KEY = dict(partition_by="company_id", order_by="month")


def add_events(f: pl.DataFrame, horizon: int = 6) -> pl.DataFrame:
    fut = lambda e, k: e.shift(-k).over(**KEY)
    base = pl.col("in12") / 12 + 1.0
    churn = pl.lit(False); cash = pl.lit(False)
    for k in range(1, horizon + 1):
        churn = churn | (fut(pl.col("months_since_final_tx"), k) > 0)  # apagado definitivo (etiqueta, no feature)
        cash = cash | (fut(pl.col("cash_end"), k) < 0)
    fut_in6 = fut(pl.col("in6"), horizon) / 6
    # declive robusto a picos: mediana de las entradas de los próximos 6 meses < 50 % de la mediana de los 12 anteriores
    med12 = pl.col("inflow").rolling_median(12, min_samples=3).over(**KEY)
    fut_med6 = pl.col("inflow").rolling_median(horizon, min_samples=horizon).over(**KEY).shift(-horizon).over(**KEY)
    decline = fut_med6 < 0.5 * med12
    growth = (fut_in6 > 1.3 * base) & (fut(pl.col("cash_end"), horizon) > pl.col("cash_end"))
    ok = fut(pl.col("month"), horizon).is_not_null() & (pl.col("months_since_last_tx") == 0) & (pl.col("month_idx") >= 5)
    cash_ok = ok & (pl.col("cash_end") >= 0)
    w = lambda cond, e: pl.when(cond).then(e.cast(pl.Float64))
    return f.with_columns(**{
        f"churn_{horizon}m": w(ok, churn),
        f"cash_stress_{horizon}m": w(cash_ok, cash),
        f"decline_{horizon}m": w(ok, decline),
        f"adverse_{horizon}m": w(ok, churn | decline | (cash & (pl.col("cash_end") >= 0))),
        f"positive_{horizon}m": w(ok, growth),
    })
