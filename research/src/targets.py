"""Eventos observables que anclan el score: no hay etiquetas, pero sí hechos futuros medibles.

Todas las etiquetas son a 6 meses: 1 si el evento ocurre en (m, m+6], 0 si no, y vacía (NaN) si el futuro
no es observable.

**v2 (los que calibran el score).** Salen del panel multi-modelo y se midieron en reports/eventos_v2.md:
- `tension_6m`: la empresa estará en tensión de liquidez persistente en algún momento de los próximos 6 meses
  (≥2 de 3 meses seguidos con <0,25 meses de liquidez o liquidez negativa). Calibra la nota, porque es la
  visión del prestamista: estar ya en tensión y seguir en ella también es riesgo. Cuenta la póliza disponible
  como liquidez y excluye los meses de empresas financiadas por su grupo (cash pooling: la caja cuadra, pero el
  hueco lo tapa el grupo).
- `tension_entrada_6m`: entrada en esa tensión desde una situación sana (E1). Solo se define para empresas hoy
  sanas, que son el conjunto en riesgo. Sirve para medir la anticipación, no para calibrar: el nivel actual de
  caja no la predice.
- `incumplimiento_6m`: una obligación recurrente deja de pagarse (E2 estricto). Es una nómina o una cuota
  regulares que faltan 2 meses seguidos con el feed activo, o un IVA que falta 2 trimestres seguidos. Solo se
  define para empresas con alguna obligación regular: quien no tiene cuotas no puede dejar de pagarlas, y si no
  se restringe, la etiqueta premia tener deuda.
- `caida_6m`: caída estructural de cobros sin apagado ni rebote (E3).
- `expansion_6m`: expansión sostenida y autofinanciada (E4), la cara positiva.

**v1 (se mantienen para comparar).** Son `churn_6m`, `cash_stress_6m`, `decline_6m`, `adverse_6m` y
`positive_6m`. El apagado (`churn_6m`) ya no calibra: el 52 % son desconexiones de la plataforma, no cierres.

**v3 (docs/eventos.md, learnings del consejo C1-C3).** Se añaden sin tocar las v2 (comparabilidad):
- `tension_np_raw_6m`: tensión con la **caja propia** (sin sumar la póliza) y **sin censurar** a las
  empresas financiadas por su grupo. Quita la circularidad de `lc_util` y el intragrupo (C1/C2).
- `entrada_estres_2m` / `rompe_caja_2m`: anticipación desde **sana hoy** (caja ≥ 0,5 meses de gasto):
  entra en tensión persistente / rompe caja (caja < 0) en m+1..m+2 (C1/C3).
- `impago_{nomina,ss,iva,cuota,ap}_6m`: el impago **por tipo** — nómina, Seguridad Social, IVA, cuota y
  mora AP estructural (saldo vencido ≥ 25 % del gasto; es estado, no impago puntual) (C2/C3).
- `cura_3m` / `recaida_6m`: salir del estrés (3 meses limpios) y volver a entrar (C1).
- `caida_3m_corto` / `expansion_3m`: variantes de **historia corta** (base con 3 meses) para que
  existan en empresas nuevas (C1/Q3).
- `tension_grupo_mes` / `tension_grupo_6m`: tensión **agregada del grupo** (caja sumada del grupo),
  solo como diagnóstico, no sustituye a la entidad (Q12).
"""
import numpy as np
import pandas as pd
import polars as pl

KEY = dict(partition_by="company_id", order_by="month")
H = 6
FISCAL = {1, 4, 7, 10}
ADVERSE_V2 = ["tension_6m", "incumplimiento_6m", "caida_6m"]
POSITIVE_V2 = ["expansion_6m"]


def add_events(f: pl.DataFrame, horizon: int = H) -> pl.DataFrame:
    """Eventos v1 (polars) + v2 (pandas, ver add_events_v2)."""
    fut = lambda e, k: e.shift(-k).over(**KEY)
    base = pl.col("in12") / 12 + 1.0
    churn = pl.lit(False); cash = pl.lit(False)
    for k in range(1, horizon + 1):
        churn = churn | (fut(pl.col("months_since_final_tx"), k) > 0)  # apagado definitivo (etiqueta, no feature)
        cash = cash | (fut(pl.col("cash_end"), k) < 0)
    fut_in6 = fut(pl.col("in6"), horizon) / 6
    med12 = pl.col("inflow").rolling_median(12, min_samples=3).over(**KEY)
    fut_med6 = pl.col("inflow").rolling_median(horizon, min_samples=horizon).over(**KEY).shift(-horizon).over(**KEY)
    decline = fut_med6 < 0.5 * med12
    growth = (fut_in6 > 1.3 * base) & (fut(pl.col("cash_end"), horizon) > pl.col("cash_end"))
    ok = fut(pl.col("month"), horizon).is_not_null() & (pl.col("months_since_last_tx") == 0) & (pl.col("month_idx") >= 5)
    cash_ok = ok & (pl.col("cash_end") >= 0)
    w = lambda cond, e: pl.when(cond).then(e.cast(pl.Float64))
    f = f.with_columns(**{
        f"churn_{horizon}m": w(ok, churn),
        f"cash_stress_{horizon}m": w(cash_ok, cash),
        f"decline_{horizon}m": w(ok, decline),
        f"adverse_{horizon}m": w(ok, churn | decline | (cash & (pl.col("cash_end") >= 0))),
        f"positive_{horizon}m": w(ok, growth),
    })
    return pl.from_pandas(add_events_v2(f.to_pandas()))


# ---------------------------------------------------------------- v2
def _fwd_any(d: pd.DataFrame, flag: pd.Series, h: int = H) -> pd.Series:
    """1 si flag ocurre en alguno de los meses m+1..m+h de la misma empresa."""
    f = flag.astype(float).fillna(0).groupby(d.company_id)
    return (sum(f.shift(-k).fillna(0) for k in range(1, h + 1)) > 0).astype(float)


def _shift_bool(s: pd.Series, by: pd.Series, k: int) -> pd.Series:
    return s.groupby(by).shift(k).fillna(False).astype(bool)


def add_events_v2(d: pd.DataFrame) -> pd.DataFrame:
    """Requiere las columnas del panel y de features.add_features (out3, out12, month_idx...)."""
    d = d.sort_values(["company_id", "month"]).reset_index(drop=True)
    # tensión del grupo (Q12, docs/eventos.md): caja agregada del grupo, diagnóstico — no sustituye a la entidad
    if "group_id" in d.columns:
        _burn0 = (np.maximum(d.out3 / 3, d.out12 / 12) + 1e-9).values
        gg = (pd.DataFrame({"group_id": d.group_id.values, "month": d.month.values,
                             "cash": d.cash_end.values, "burn": _burn0})
              .groupby(["group_id", "month"], as_index=False).agg(cash_g=("cash", "sum"), burn_g=("burn", "sum")))
        gg["tension_grupo_mes"] = (gg.cash_g < 0) | (gg.cash_g / (gg.burn_g + 1e-9) < 0.25)
        d = d.merge(gg[["group_id", "month", "tension_grupo_mes"]], on=["group_id", "month"], how="left")
        d = d.sort_values(["company_id", "month"]).reset_index(drop=True)
        d["tension_grupo_mes"] = d["tension_grupo_mes"].fillna(False).astype(bool)
    cid = d.company_id
    g = d.groupby("company_id")
    # observable hasta m+6 y la empresa sigue viva al final de la ventana (censura por apagado)
    fut_final = g["months_since_final_tx"].shift(-H)
    obs6 = fut_final.notna() & (fut_final == 0)

    # --- E1 · tensión de liquidez persistente
    burn = np.maximum(d.out3 / 3, d.out12 / 12) + 1e-9
    avail = (d.lc_limit - d.lc_drawn).clip(lower=0).where(d.lc_limit > 0, 0).fillna(0)
    liq = d.cash_end + avail
    runway_liq = liq / burn
    stress = (liq < 0) | (runway_liq < 0.25)
    healthy = (runway_liq >= 0.5) & (liq >= 0)
    gf12 = g["gross_flow"].transform(lambda x: x.rolling(12, min_periods=1).mean())
    implausible = d.cash_end.abs() > 50 * (gf12 + 1)
    ig3 = g["intragroup_flow"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    gross3 = g["gross_flow"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    group_funded = ig3 / (gross3 + ig3 + 1) > 0.2
    prior_ok = sum(_shift_bool(healthy, cid, k).astype(int) for k in (1, 2, 3)) == 3
    onset = stress & prior_ok & ~implausible & ~group_funded
    confirmed = onset & (sum(_shift_bool(stress, cid, -k).astype(int) for k in (1, 2, 3)) >= 2) & g["month"].shift(-3).notna()
    risk_set = healthy & obs6 & g["month"].shift(-(H + 3)).notna()   # sanas hoy y con ventana de confirmación observable
    d["tension_onset"] = confirmed
    d["tension_entrada_6m"] = _fwd_any(d, confirmed).where(risk_set)
    # estado persistente (visión del prestamista): tensión en ≥2 de 3 meses seguidos que arrancan en t.
    # La financiación del grupo no censura la tensión futura como 0 (eso declaraba sanas 2 513 filas con la caja
    # tapada por el grupo, Q2/Q12): la fila financiada hoy queda sin etiqueta (null), y los meses futuros cuentan.
    valid = stress & ~implausible
    persist = valid & (sum(_shift_bool(valid, cid, -k).astype(int) for k in (1, 2)) >= 1) & g["month"].shift(-2).notna()
    d["tension_6m"] = _fwd_any(d, persist).where(obs6 & g["month"].shift(-(H + 2)).notna() & ~group_funded)

    # --- E2 · incumplimiento estricto de obligación recurrente
    feed = (d.n_tx >= 5) & (d.outflow > 0) & ((d.uncat_in / (d.inflow + 1e-9)) < 0.8)
    def regular(col):
        pos = (d[col] > 0).astype(int).groupby(cid)
        return sum(pos.shift(k).fillna(0) for k in range(1, 7)) >= 4
    def missed_twice(col):
        miss = regular(col) & (d[col] <= 0) & feed
        return miss & (g[col].shift(-1) <= 0) & _shift_bool(feed, cid, -1)
    fisc = d.month.dt.month.isin(FISCAL)
    taxpos = (d.tax > 0).where(fisc)
    tprev = [taxpos.groupby(cid).shift(3 * k) for k in (1, 2, 3)]
    reg_tax = sum(t.fillna(False).astype(int) for t in tprev) >= 2
    miss_tax = fisc & reg_tax & (d.tax <= 0) & (tprev[0] == False) & feed  # noqa: E712  (falta este trimestre y el anterior)
    breach = missed_twice("payroll") | missed_twice("debt_service") | miss_tax
    has_obligation = regular("payroll") | regular("debt_service") | reg_tax.where(fisc).groupby(cid).ffill().fillna(False).astype(bool)
    d["incumplimiento_mes"] = breach
    d["incumplimiento_6m"] = _fwd_any(d, breach).where(obs6 & has_obligation)

    # --- E3 · caída estructural de cobros, sin apagado ni rebote
    gi = g["inflow"]
    base = gi.transform(lambda x: x.rolling(12, min_periods=9).median())
    F = pd.concat([gi.shift(-k) for k in range(1, H + 1)], axis=1)
    med_f = F.median(axis=1, skipna=False)
    no_rebound = F.iloc[:, 3:].median(axis=1) <= F.iloc[:, :3].median(axis=1)
    d["caida_6m"] = ((med_f < 0.5 * base) & no_rebound).astype(float).where(obs6 & base.notna() & med_f.notna())

    # --- E4 · expansión sostenida autofinanciada (cara positiva)
    go = g["oper_in"]
    base_o = go.transform(lambda x: x.rolling(12, min_periods=6).mean())
    Fo = pd.concat([go.shift(-k) for k in range(1, H + 1)], axis=1)
    mean_f = Fo.mean(axis=1, skipna=False)
    dcash = g["cash_end"].shift(-H) - d.cash_end
    self_funded = (g["lc_drawn"].shift(-H) - d.lc_drawn).fillna(0) <= 0.5 * dcash.clip(lower=0)
    incr = Fo.sum(axis=1) - H * base_o
    one_off = (Fo.max(axis=1) - base_o) > 0.5 * incr
    ok4 = obs6 & base_o.notna() & mean_f.notna() & (d.month_idx >= 5)
    exp = (mean_f > 1.3 * base_o) & (dcash > 0) & self_funded & ~one_off & (d.caida_6m.fillna(0) == 0)
    d["expansion_6m"] = exp.astype(float).where(ok4)

    # ------------------------------------------------ v3 (docs/eventos.md, learnings C1-C3)
    # --- E1b · tensión no circular: caja propia, sin póliza, sin censura de grupo
    liq_np = d.cash_end
    runway_np = liq_np / burn
    stress_np = (liq_np < 0) | (runway_np < 0.25)
    healthy_np = (runway_np >= 0.5) & (liq_np >= 0)
    valid_np = stress_np & ~implausible
    persist_np = valid_np & (sum(_shift_bool(valid_np, cid, -k).astype(int) for k in (1, 2)) >= 1) & g["month"].shift(-2).notna()
    d["tension_np_raw_6m"] = _fwd_any(d, persist_np).where(obs6 & g["month"].shift(-(H + 2)).notna())

    # --- anticipación a 2 meses desde sana hoy
    fut2 = g["months_since_final_tx"].shift(-2)
    obs2 = fut2.notna() & (fut2 == 0)
    risk2 = healthy_np & obs2 & ~implausible & g["month"].shift(-2).notna()
    d["entrada_estres_2m"] = _fwd_any(d, persist_np, h=2).where(risk2)
    d["rompe_caja_2m"] = _fwd_any(d, d.cash_end < 0, h=2).where(risk2)

    # --- E2b · impago por tipo
    if "salary" in d.columns:
        d["impago_nomina_6m"] = _fwd_any(d, missed_twice("salary")).where(obs6 & regular("salary"))
        d["impago_ss_6m"] = _fwd_any(d, missed_twice("social_security")).where(obs6 & regular("social_security"))
    d["impago_cuota_6m"] = _fwd_any(d, missed_twice("debt_service")).where(obs6 & regular("debt_service"))
    d["impago_iva_6m"] = _fwd_any(d, miss_tax).where(obs6 & reg_tax.where(fisc).groupby(cid).ffill().fillna(False).astype(bool))
    if "overdue_ap" in d.columns:  # mora AP estructural (D1_estricto): estado crónico, no impago puntual
        mora_ap = d.overdue_ap.fillna(0) >= 0.25 * burn
        d["impago_ap_6m"] = _fwd_any(d, mora_ap).where(obs6 & d.get("has_erp", pd.Series(False, index=d.index)).fillna(False))

    # --- cura y recaída del estrés (cara positiva de la tensión no circular)
    clean_np = ~stress_np
    clean3 = (sum(_shift_bool(clean_np, cid, -k).astype(int) for k in (1, 2, 3)) == 3) & g["month"].shift(-3).notna()
    d["cura_3m"] = (stress_np & clean3).astype(float).where(g["month"].shift(-3).notna())
    exited = _shift_bool(stress_np, cid, 1) & clean_np
    d["recaida_6m"] = _fwd_any(d, stress_np).where(exited & obs6 & g["month"].shift(-H).notna())

    # --- E3b/E4b · variantes de historia corta (existen desde el mes 3)
    fut3 = g["months_since_final_tx"].shift(-3)
    obs3 = fut3.notna() & (fut3 == 0)
    base_c = gi.transform(lambda x: x.rolling(12, min_periods=3).median())
    F3 = pd.concat([gi.shift(-k) for k in range(1, 4)], axis=1)
    med_f3 = F3.median(axis=1, skipna=False)
    d["caida_3m_corto"] = (med_f3 < 0.5 * base_c).astype(float).where(obs3 & base_c.notna() & med_f3.notna())
    base_o3 = go.transform(lambda x: x.rolling(12, min_periods=3).mean())
    Fo3 = pd.concat([go.shift(-k) for k in range(1, 4)], axis=1)
    mean_f3 = Fo3.mean(axis=1, skipna=False)
    dcash3 = g["cash_end"].shift(-3) - d.cash_end
    self_funded3 = (g["lc_drawn"].shift(-3) - d.lc_drawn).fillna(0) <= 0.5 * dcash3.clip(lower=0)
    exp3 = (mean_f3 > 1.3 * base_o3) & (dcash3 > 0) & self_funded3 & (d.caida_3m_corto.fillna(0) == 0)
    d["expansion_3m"] = exp3.astype(float).where(obs3 & base_o3.notna() & mean_f3.notna() & (d.month_idx >= 2))

    # --- tensión del grupo como etiqueta a 6 m (diagnóstico)
    if "tension_grupo_mes" in d.columns:
        d["tension_grupo_6m"] = _fwd_any(d, d.tension_grupo_mes).where(obs6)
    return d
