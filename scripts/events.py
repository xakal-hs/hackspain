"""Framework de eventos de estrés: registro de eventos candidatos + diagnóstico de los filtros.

Un evento es una regla observable, calculada con datos <= fin del mes t (sin fuga), que dice si en ese
mes la empresa sufre un episodio concreto de estrés. Cada evento declara:
  - applicable: en qué filas se puede evaluar (si no, el valor es NaN, no 0);
  - fn:         la regla (True = evento);
  - dimension / severity: metadatos para la explicación.

Los eventos se añaden con @register. `diagnose` calcula los filtros de admisión (tasa base, cobertura,
persistencia, co-ocurrencia) para decidir cuáles entran en el evento final. Los umbrales se fijan por
criterio de dominio y tasa base, NUNCA por lo bien que el score los prediga.

Uso:  python scripts/events.py      -> data/processed/events_candidates.csv + informe por consola
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data" / "processed"
MIN_HISTORY = 6                       # meses de historia para evaluar (mismo criterio que el resto del track)


@dataclass
class Event:
    name: str
    dimension: str
    severity: str                     # baja | media | alta
    description: str
    applicable: Callable[[pd.DataFrame], pd.Series]
    fn: Callable[[pd.DataFrame], pd.Series]
    params: dict = field(default_factory=dict)


REGISTRY: list[Event] = []


def register(**kw):
    def deco(pair):
        app, fn = pair
        REGISTRY.append(Event(applicable=app, fn=fn, **kw))
        return pair
    return deco


def _g(p):
    return p.groupby("company_id")


def _prev(p, col, n, fn="median"):
    """estadístico de los n meses anteriores (sin incluir el actual)."""
    return _g(p)[col].transform(lambda s: getattr(s.shift(1).rolling(n, min_periods=n), fn)())


# ------------------------------------------------------------------ eventos candidatos
P_REG = dict(lookback=6, min_present=5)


def _reg_missing(p):
    """Falta la nómina, la SS o el impuesto que solía pagarse cada mes."""
    ev = pd.Series(False, index=p.index)
    reg = pd.Series(False, index=p.index)
    for col in ("out_salary", "out_social_security", "out_tax"):
        present = (p[col] > 0).astype(float)
        p_ = p.assign(_x=present)
        usual = _g(p_)["_x"].transform(lambda s: s.shift(1).rolling(P_REG["lookback"], min_periods=P_REG["lookback"]).sum()) >= P_REG["min_present"]
        reg |= usual
        ev |= usual & (present == 0)
    return ev, reg


register(name="obligacion_regular_falta", dimension="pago", severity="alta",
         description="falta una nómina/SS/impuesto que se pagaba al menos 5 de los 6 meses previos",
         params=P_REG)((lambda p: _reg_missing(p)[1] & (p.n_tx > 0), lambda p: _reg_missing(p)[0]))

P_PAY = dict(share_of_outflow=0.25)
register(name="factura_recibida_vencida_90d", dimension="pago", severity="media",
         description="facturas de proveedores vencidas 90-180 días y sin pagar >= 25% de las salidas mensuales",
         params=P_PAY)((
    lambda p: p.tiene_facturas & (p.outflow_op_3m > 0),
    lambda p: p.payables_overdue90_recent >= P_PAY["share_of_outflow"] * (p.outflow_op_3m / 3)))

P_NEG = dict(days=5)
register(name="saldo_negativo", dimension="liquidez", severity="alta",
         description="saldo de cuentas de banco negativo >= 5 días del mes",
         params=P_NEG)((
    lambda p: p.days_negative.notna(),
    lambda p: p.days_negative >= P_NEG["days"]))

P_BURN = dict(runway=1.0)
register(name="caja_agotandose", dimension="caja", severity="alta",
         description="flujo operativo negativo 3 meses y saldo cubre menos de 1 mes de salidas",
         params=P_BURN)((
    lambda p: p.runway_m.notna() & p.margin_3m.notna(),
    lambda p: (p.net_op_3m < 0) & (p.runway_m < P_BURN["runway"])))

P_FIN = dict(mult=3.0, min_share=0.02)


def _fin(p):
    med = _prev(p, "out_fin_cost", 6)
    return (p.out_fin_cost > P_FIN["mult"] * med) & (p.out_fin_cost > P_FIN["min_share"] * p.outflow_op) & (med > 0)


register(name="coste_financiero_disparado", dimension="deuda", severity="media",
         description="intereses+comisiones > 3x su mediana de 6 meses y > 2% de las salidas",
         params=P_FIN)((lambda p: _prev(p, "out_fin_cost", 6).notna() & (p.outflow_op > 0), _fin))


# ------------------------------------------------------------------ cálculo y diagnóstico
def load_panel():
    p = pd.read_csv(D / "panel_monthly.csv").sort_values(["company_id", "month"]).reset_index(drop=True)
    return p[p.hist_months >= MIN_HISTORY].reset_index(drop=True)


def compute_events(p: pd.DataFrame) -> pd.DataFrame:
    out = p[["company_id", "month"]].copy()
    for e in REGISTRY:
        app = e.applicable(p).fillna(False).astype(bool)
        val = e.fn(p).fillna(False).astype(float)
        out[e.name] = np.where(app, val, np.nan)
    return out


def forward(ev: pd.DataFrame, cols, h: int) -> pd.DataFrame:
    """y_h = 1 si hay evento en algún mes de t+1..t+h (NaN si el horizonte no está completo)."""
    g = ev.groupby("company_id")
    res = ev[["company_id", "month"]].copy()
    for c in cols:
        fut = pd.concat([g[c].shift(-k) for k in range(1, h + 1)], axis=1)
        y = fut.max(axis=1, skipna=True)
        res[f"{c}_y{h}"] = y.where(fut.notna().all(axis=1))
    return res


def diagnose(p: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for e in REGISTRY:
        x = ev[e.name]
        app = x.notna()
        prev = ev.groupby("company_id")[e.name].shift(1)
        both = (prev == 1) & app
        ever = ev.assign(v=x).groupby("company_id").v.max()
        rows.append({
            "evento": e.name, "dimension": e.dimension, "gravedad": e.severity,
            "filas_aplicables_%": round(100 * app.mean(), 1),
            "tasa_base_%": round(100 * x[app].mean(), 2),
            "empresas_alguna_vez_%": round(100 * (ever.dropna() == 1).mean(), 1),
            "persistencia_%": round(100 * (x[both] == 1).mean(), 1) if both.any() else np.nan,
        })
    return pd.DataFrame(rows)


def cooccurrence(ev: pd.DataFrame) -> pd.DataFrame:
    names = [e.name for e in REGISTRY]
    m = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            both = ev[a].notna() & ev[b].notna()
            x, y = ev.loc[both, a] == 1, ev.loc[both, b] == 1
            m.loc[a, b] = round((x & y).sum() / max((x | y).sum(), 1), 3)   # Jaccard
    return m


def aggregate(ev: pd.DataFrame, names=None) -> pd.Series:
    names = names or [e.name for e in REGISTRY]
    sub = ev[names]
    any_app = sub.notna().any(axis=1)
    return (sub.max(axis=1)[any_app] == 1)


if __name__ == "__main__":
    pd.set_option("display.width", 200, "display.max_columns", 20)
    p = load_panel()
    ev = compute_events(p)
    ev.to_csv(D / "events_candidates.csv", index=False)
    print(f"panel: {len(p)} filas, {p.company_id.nunique()} empresas (hist >= {MIN_HISTORY} meses)\n")
    print(diagnose(p, ev).to_string(index=False))
    print("\nCo-ocurrencia (Jaccard):\n", cooccurrence(ev).to_string())
    agg = aggregate(ev)
    print(f"\nOR de todos: tasa base {100*agg.mean():.1f}% de {len(agg)} filas")
    for e in REGISTRY:
        rest = [x.name for x in REGISTRY if x.name != e.name]
        print(f"  sin {e.name}: {100*aggregate(ev, rest).mean():.1f}%")
