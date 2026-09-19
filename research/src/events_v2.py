"""Eventos v2 (propuesta del panel multi-modelo, research/brainstorm/eventos/SINTESIS_glm5.3.md).

Etiquetas a 6 meses por empresa-mes: vale 1 si el evento ocurre en (m, m+6], 0 si no, y NaN si el futuro
no es observable (fin del dataset o la empresa se apaga en la ventana: censura por apagado).

E1  Entrada en tensión de caja persistente (transición, con variante que cuenta la póliza disponible)
E2  Incumplimiento de obligación recurrente. `e2` es la versión ancha (incluye AP>90d, circular);
    `e2_strict` es la que se usa: 2 meses seguidos sin pagar con feed vivo, IVA a 2 trimestres, sin AP>90d.
E3  Caída estructural de cobros sin apagado ni rebote
E4  Expansión sostenida autofinanciada
Además, a nivel de mes o empresa: E5 bache, E6 sano sostenido, E7 recuperación.
Módulo experimental: no sustituye a targets.py hasta que se decida.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

H = 6
FISCAL = {1, 4, 7, 10}


def _g(d: pd.DataFrame, col: str):
    return d.groupby("company_id")[col]


def _fwd_any(d: pd.DataFrame, flag: pd.Series, h: int = H) -> pd.Series:
    """1 si flag ocurre en alguno de los meses m+1..m+h (por empresa)."""
    f = flag.astype(float).fillna(0)
    out = sum(f.groupby(d.company_id).shift(-k).fillna(0) for k in range(1, h + 1))
    return (out > 0).astype(float)


def prepare(p: pd.DataFrame) -> pd.DataFrame:
    d = p.sort_values(["company_id", "month"]).reset_index(drop=True).copy()
    g = d.groupby("company_id")
    roll = lambda c, w, fn="mean": g[c].transform(lambda x: getattr(x.rolling(w, min_periods=1), fn)())
    d["out3m"] = roll("outflow", 3); d["out12m"] = roll("outflow", 12)
    d["burn"] = np.maximum(d.out3m, d.out12m) + 1e-9
    d["runway_m"] = d.cash_end / d.burn                                   # meses de caja (con signo)
    avail = (d.lc_limit - d.lc_drawn).clip(lower=0).where(d.lc_limit > 0, 0).fillna(0)
    d["runway_liq"] = (d.cash_end + avail) / d.burn                         # meses de liquidez (caja + póliza)
    d["gf12m"] = roll("gross_flow", 12)
    d["implausible"] = d.cash_end.abs() > 50 * (d.gf12m + 1)
    d["feed_ok"] = (d.n_tx >= 5) & (d.outflow > 0)
    d["idx"] = g.cumcount()
    d["month_num"] = d.month.dt.month
    # observable hasta m+6 y la empresa sigue viva al final de la ventana (censura por apagado)
    fut_final = g["months_since_final_tx"].shift(-H)
    d["obs6"] = fut_final.notna() & (fut_final == 0)
    return d


def _group_funded(d: pd.DataFrame, thr: float = 0.20, w: int = 3) -> pd.Series:
    """True si en los últimos `w` meses (incluido el actual) más del `thr` del flujo es intragrupo.

    `gross_flow` sólo agrega movimientos externos y `intragroup_flow` los de dentro del grupo,
    así que la cuota es intragrupo / (externo + intragrupo). Una empresa así no se queda sin caja
    por su negocio: la tesorería la reparte la matriz (cash pooling), y su E1 no es comparable
    con el de una empresa que se financia sola.
    """
    ig = d.intragroup_flow.fillna(0).abs()
    ex = d.gross_flow.fillna(0).abs()
    ig_w = sum(ig.groupby(d.company_id).shift(k).fillna(0) for k in range(w))
    ex_w = sum(ex.groupby(d.company_id).shift(k).fillna(0) for k in range(w))
    return ig_w > thr * (ig_w + ex_w + 1e-9)


def e1(d: pd.DataFrame, liquidity: bool = False) -> pd.DataFrame:
    r = d.runway_liq if liquidity else d.runway_m
    cash = (d.cash_end + ((d.lc_limit - d.lc_drawn).clip(lower=0).where(d.lc_limit > 0, 0).fillna(0))) if liquidity else d.cash_end
    stress = (cash < 0) | (r < 0.25)
    healthy = (r >= 0.5) & (cash >= 0)
    gs = stress.groupby(d.company_id); gh = healthy.groupby(d.company_id)
    prior_ok = sum(gh.shift(k).fillna(False).astype(int) for k in (1, 2, 3)) == 3
    onset = stress & prior_ok & ~d.implausible
    nxt = sum(gs.shift(-k).fillna(False).astype(int) for k in (1, 2, 3))
    known = gs.shift(-3).notna()
    confirmed = onset & (nxt >= 2) & known
    name = "E1_liq" if liquidity else "E1"
    d[f"{name}_onset_raw"] = onset
    d[f"{name}_onset"] = confirmed
    d[f"{name}_stress"] = stress
    # cash pooling: el arranque es real, pero la caja la mueve el grupo, no el negocio (se excluye del limpio)
    pooled = _group_funded(d)
    d[f"{name}_group_funded"] = confirmed & pooled
    d[f"{name}_clean_onset"] = confirmed & ~pooled
    # para confirmar el último arranque posible (m+6) hace falta ver hasta m+9
    obs = d.obs6 & d.groupby("company_id").month.shift(-(H + 3)).notna()
    d[name] = _fwd_any(d, confirmed).where(obs)
    d[f"{name}_clean"] = _fwd_any(d, confirmed & ~pooled).where(obs)
    return d


def e2(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("company_id")
    def regular(col):
        pos = (d[col] > 0).astype(int)
        return sum(pos.groupby(d.company_id).shift(k).fillna(0) for k in range(1, 7)) >= 4
    guard = d.feed_ok & ((d.uncat_in / (d.inflow + 1e-9)) < 0.8)
    miss_pay = regular("payroll") & (d.payroll <= 0) & guard
    miss_debt = regular("debt_service") & (d.debt_service <= 0) & guard
    # IVA: en mes fiscal, empresa que pagó en ≥2 de los 3 meses fiscales previos y no paga en este ni en el anterior fiscal
    fisc = d.month_num.isin(FISCAL)
    taxpos = (d.tax > 0).where(fisc)
    tprev = [taxpos.groupby(d.company_id).shift(3 * k) for k in (1, 2, 3)]
    reg_tax = sum(t.fillna(False).astype(int) for t in tprev) >= 2
    miss_tax = fisc & reg_tax & (d.tax <= 0) & (tprev[0].fillna(True) == False) & guard  # noqa: E712
    ap90 = d.overdue_90_ap
    miss_ap = d.has_erp & (ap90 >= 1.5 * g["overdue_90_ap"].shift(3)) & (ap90 > 0.5 * d.out12m) & ap90.notna()
    d["E2_nomina"], d["E2_cuota"], d["E2_iva"], d["E2_ap90"] = miss_pay, miss_debt, miss_tax, miss_ap
    ev = miss_pay | miss_debt | miss_tax | miss_ap
    d["E2_any"] = ev
    # ¿se retoma el pago al mes siguiente? (si sí, más probable ruido de categorización o calendario)
    d["E2_resumed_next"] = ((miss_pay & (g["payroll"].shift(-1) > 0)) | (miss_debt & (g["debt_service"].shift(-1) > 0)))
    d["E2"] = _fwd_any(d, ev).where(d.obs6)
    for c in ["E2_nomina", "E2_cuota", "E2_iva", "E2_ap90"]:
        d[c + "_6m"] = _fwd_any(d, d[c]).where(d.obs6)
    return d


def e2_strict(d: pd.DataFrame) -> pd.DataFrame:
    """E2 estricto: impago de una obligación recurrente, no un hueco de un mes.

    Frente a `e2`, tres cambios pensados para que la etiqueta signifique lo que dice:

    1. **Dos meses seguidos sin pagar.** Un mes suelto sin nómina o sin cuota es casi siempre
       calendario (la paga cae el 1 y se contabiliza el 31), cambio de banco o una categoría mal
       puesta. Exigir el segundo mes consecutivo elimina ese ruido: `e2` marcaba muchos meses cuyo
       pago se retomaba al mes siguiente (ver `E2_resumed_next`).
    2. **Regularidad medida antes del hueco.** La ventana de 6 meses se evalúa en el primer mes
       impagado, no en el segundo, para que los propios impagos no erosionen la regularidad que
       se usa para decidir si esa obligación existía.
    3. **Sin el componente AP>90.** `E2_ap90` usaba el vencido a más de 90 días del ERP, que es
       prácticamente la misma información que el target de riesgo que queremos predecir: el modelo
       aprendía a leer la etiqueta en lugar de anticiparla. Circular, fuera.

    El feed tiene que estar vivo en los dos meses (`feed_ok`) o no distinguimos "no paga" de
    "no vemos sus movimientos"; y se descartan meses con >80 % de entradas sin categorizar.
    El IVA se mantiene trimestral: dos trimestres fiscales seguidos sin pagar.
    """
    g = d.groupby("company_id")
    gc = d.company_id
    guard = d.feed_ok & ((d.uncat_in / (d.inflow + 1e-9)) < 0.8)

    def regular(col):
        pos = (d[col] > 0).astype(int)
        return sum(pos.groupby(gc).shift(k).fillna(0) for k in range(1, 7)) >= 4

    def streak2(col):
        """Impago confirmado: mes m y m-1 sin pago, feed vivo en ambos, regularidad previa a m-1."""
        miss = ((d[col] <= 0) & guard).astype(bool)
        prev_miss = miss.groupby(gc).shift(1).astype("boolean").fillna(False).astype(bool)
        reg_before = regular(col).astype(bool).groupby(gc).shift(1).astype("boolean").fillna(False).astype(bool)
        return miss & prev_miss & reg_before

    miss_pay, miss_debt = streak2("payroll"), streak2("debt_service")

    # IVA: sólo meses fiscales. Regular = pagó en ≥2 de los 3 trimestres previos;
    # impago = no paga ni en este trimestre ni en el anterior (dos trimestres seguidos).
    fisc = d.month_num.isin(FISCAL)
    taxpos = (d.tax > 0).where(fisc)
    tprev = [taxpos.groupby(gc).shift(3 * k) for k in (1, 2, 3)]
    reg_tax = sum(t.astype("boolean").fillna(False).astype(int) for t in tprev) >= 2
    prev_fisc_miss = (tprev[0] == False).astype("boolean").fillna(False).astype(bool)  # noqa: E712
    guard_prev = guard.astype(bool).groupby(gc).shift(3).astype("boolean").fillna(False).astype(bool)
    miss_tax = fisc & reg_tax & (d.tax <= 0) & prev_fisc_miss & guard & guard_prev

    d["E2s_nomina"], d["E2s_cuota"], d["E2s_iva"] = miss_pay, miss_debt, miss_tax
    ev = miss_pay | miss_debt | miss_tax
    d["E2_strict_any"] = ev
    d["E2_strict"] = _fwd_any(d, ev).where(d.obs6)
    for c in ["E2s_nomina", "E2s_cuota", "E2s_iva"]:
        d[c + "_6m"] = _fwd_any(d, d[c]).where(d.obs6)
    return d


def e3(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("company_id")["inflow"]
    base = g.transform(lambda x: x.rolling(12, min_periods=9).median())
    fut = [g.shift(-k) for k in range(1, H + 1)]
    F = pd.concat(fut, axis=1)
    med_f = F.median(axis=1, skipna=False)
    first3, last3 = F.iloc[:, :3].median(axis=1), F.iloc[:, 3:].median(axis=1)
    drop = med_f < 0.5 * base
    no_rebound = last3 <= first3
    d["E3_raw"] = drop.astype(float).where(d.obs6 & base.notna() & med_f.notna())
    d["E3"] = (drop & no_rebound).astype(float).where(d.obs6 & base.notna() & med_f.notna())
    # rebote posterior al horizonte (m+7..m+9 ≥ 0,8·base) entre las caídas limpias
    post = pd.concat([g.shift(-k) for k in (7, 8, 9)], axis=1).median(axis=1)
    d["E3_postrebound"] = (post >= 0.8 * base).where(d.E3 == 1)
    return d


def e4(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("company_id")
    base = g["oper_in"].transform(lambda x: x.rolling(12, min_periods=6).mean())
    F = pd.concat([g["oper_in"].shift(-k) for k in range(1, H + 1)], axis=1)
    mean_f = F.mean(axis=1, skipna=False)
    grow = mean_f > 1.3 * base
    cash_up = g["cash_end"].shift(-H) > d.cash_end
    lc_up = (g["lc_drawn"].shift(-H) - d.lc_drawn).fillna(0)
    self_funded = lc_up <= 0.5 * (g["cash_end"].shift(-H) - d.cash_end).clip(lower=0)
    incr = (F.sum(axis=1) - H * base)
    one_off = (F.max(axis=1) - base) > 0.5 * incr
    ok = d.obs6 & base.notna() & mean_f.notna() & (d.idx >= 5)
    lab = (grow & cash_up & self_funded & ~one_off & (d.get("E3", 0).fillna(0) == 0))
    d["E4_raw"] = (grow & cash_up).astype(float).where(ok)
    d["E4"] = lab.astype(float).where(ok)
    # reversión: 6 meses después de la ventana, ¿vuelve por debajo de 1,1× base?
    rev = pd.concat([g["oper_in"].shift(-k) for k in range(7, 10)], axis=1).mean(axis=1) < 1.1 * base
    d["E4_reverts"] = rev.where(d.E4 == 1)
    return d


def e5_e6_e7(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("company_id")["inflow"]
    med12 = g.transform(lambda x: x.shift(1).rolling(12, min_periods=6).median())
    dip = d.inflow < 0.7 * med12
    rec = (g.shift(-1) >= 0.8 * med12) | (g.shift(-2) >= 0.8 * med12)
    alive = d.months_since_final_tx == 0
    d["E5_bache"] = dip & rec & alive
    d["E5_caida_mes"] = dip & ~rec & alive & g.shift(-2).notna()
    # recuperación tras E1: 3 meses seguidos con runway ≥0,5
    ok = (d.runway_m >= 0.5).astype(int)
    run3 = sum(ok.groupby(d.company_id).shift(-k).fillna(0) for k in (1, 2, 3)) == 3
    d["E7_recupera"] = d.E1_onset_raw & run3
    return d


def company_level(d: pd.DataFrame) -> pd.DataFrame:
    """E6 sano sostenido: ≥9 meses de historia sin E1/E2/E3, mediana de runway ≥1 y actividad ≥3 mov/mes."""
    g = d.groupby("company_id")
    c = pd.DataFrame({
        "n": g.size(),
        "any_e1": g.E1_onset_raw.any(), "any_e2": g.E2_any.any(),
        "any_e3": g.apply(lambda x: (x.E3 == 1).any()),
        "med_runway": g.runway_m.median(), "min_ntx": g.n_tx.min(),
        "has_erp": g.has_erp.first(),
    })
    c["E6_sano"] = (c.n >= 9) & ~c.any_e1 & ~c.any_e2 & ~c.any_e3 & (c.med_runway >= 1) & (c.min_ntx >= 3)
    return c


def build(p: pd.DataFrame) -> pd.DataFrame:
    d = prepare(p)
    d = e1(d); d = e1(d, liquidity=True); d = e2(d); d = e2_strict(d); d = e3(d); d = e4(d); d = e5_e6_e7(d)
    return d
