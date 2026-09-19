"""¿La nota significa algo? Medición fuera de grupo, con incertidumbre honesta.

    uv run python metrics.py                 # tabla de AUC por evento (~3 min)
    uv run python metrics.py --comparar a.parquet b.parquet   # bootstrap PAREADO

Tres reglas que no se negocian aquí:

1. FUERA DE GRUPO. Se esconden grupos empresariales completos, no empresas sueltas:
   una matriz y su filial comparten tesorería y se filtrarían la respuesta.
2. SIN FUTURO, NI EL DE LOS DEMÁS. Para puntuar el mes m, el scorer solo ha visto
   meses <= m: ni los percentiles de referencia ni los pesos conocen lo que viene
   después. Esconder grupos no basta, porque una referencia construida con los 24
   meses ya le cuenta al modelo cómo se va a distribuir el año siguiente.
3. ERROR TÍPICO POR GRUPO. Se remuestrean grupos enteros, no filas. El se iid es
   2-4x más pequeño y te haría celebrar ruido.

Y al comparar dos variantes del modelo, el se que importa es el de la DIFERENCIA
(bootstrap pareado, mismos grupos en los dos brazos). Dividir por el se de cada AUC
aislada es el error clásico: como la incertidumbre es casi toda común, se cancela al
restar, y una mejora real de 5 sigmas parece de 1.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

import preprocessing as pre
import predict as prd

NREP, SEED = 200, 7
POSITIVE = ("expansion", "positive", "cura")


def _auc(y: np.ndarray, s: np.ndarray) -> float:
    """AUC = P(el score ordena bien un par al azar). Rangos, sin dependencias."""
    r = pd.Series(s).rank().to_numpy()
    n1, n0 = y.sum(), len(y) - y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _oriented(event: str, score: np.ndarray) -> np.ndarray:
    """Para un evento adverso la nota ordena al revés: se invierte el signo."""
    return score if event.startswith(POSITIVE) else -score


# ------------------------------------------------------------------- OOF
def oof(d: pd.DataFrame, n_splits: int = 5, target: str = "adversa") -> pd.Series:
    """Nota de cada fila puntuada por un scorer que no vio ni su grupo ni su futuro.

    Un scorer por (fold, mes): para el mes m se reconstruyen percentiles, pesos y escala
    solo con los grupos de train y solo con meses <= m. Son ~120 ajustes, y es la
    simulación honesta del test oculto: el día 1 nadie conoce la distribución del día 400.

    Los primeros meses no tienen aún eventos a 6 meses observados, así que `_fit_weights`
    se queda con los pesos a priori del prestamista (PRIOR_W). No es un caso degenerado
    que haya que excluir: es literalmente el arranque en frío de una cartera nueva.
    """
    d = d.sort_values(["company_id", "month"]).reset_index(drop=True)
    cg = d.drop_duplicates("company_id").set_index("company_id")["group_id"]
    ids = cg.index.to_numpy()
    out = pd.Series(np.nan, index=d.index, name="score_oof")
    for tr, va in GroupKFold(n_splits=n_splits).split(ids, groups=cg.values):
        tr_ids, va_ids = set(ids[tr]), set(ids[va])
        for m in sorted(d.month.unique()):
            hist = d[d.month <= m]
            train = hist[hist.company_id.isin(tr_ids)]
            sc = prd.fit(train, pre.labels(train, cutoff=m), target=target)
            # se puntúa toda la historia de validación para que el EWMA llegue bien a m,
            # pero solo se guarda la fila del mes m
            val = hist[hist.company_id.isin(va_ids)]
            s = prd.score_panel(sc, val)
            s = s[s.month == m].set_index("company_id")["score"]
            rows = d.index[(d.month == m) & d.company_id.isin(va_ids)]
            out.loc[rows] = s.reindex(d.loc[rows, "company_id"]).to_numpy()
    return out


# ------------------------------------------------------------- tabla de AUC
def auc_table(d: pd.DataFrame, score_col: str = "score_oof", events: list[str] | None = None,
              nrep: int = NREP, seed: int = SEED) -> pd.DataFrame:
    """AUC por evento con error típico e IC 95 % por bootstrap de grupos."""
    events = events or [e for e in pre.EVENTS + pre.JUDGES if e in d.columns]
    rng = np.random.default_rng(seed)
    rows = []
    for e in events:
        sub = d[[e, score_col, "group_id"]].dropna()
        if sub.empty or sub[e].nunique() < 2:
            continue
        y, s, g = sub[e].to_numpy(), _oriented(e, sub[score_col].to_numpy()), sub["group_id"].to_numpy()
        groups = np.unique(g)
        idx = {gr: np.flatnonzero(g == gr) for gr in groups}
        reps = []
        for _ in range(nrep):
            ii = np.concatenate([idx[gr] for gr in rng.choice(groups, len(groups), replace=True)])
            if len(np.unique(y[ii])) > 1:
                reps.append(_auc(y[ii], s[ii]))
        reps = np.array(reps)
        rows.append({"evento": e, "auc": _auc(y, s), "se": reps.std(ddof=1),
                     "ic95_lo": np.percentile(reps, 2.5), "ic95_hi": np.percentile(reps, 97.5),
                     "n": len(y), "positivos": int(y.sum()), "grupos": len(groups)})
    return pd.DataFrame(rows).set_index("evento")


def compare(a: pd.DataFrame, b: pd.DataFrame, score_col: str = "score_oof",
            events: list[str] | None = None, nrep: int = NREP, seed: int = SEED) -> pd.DataFrame:
    """Bootstrap PAREADO de dos variantes puntuadas sobre las mismas filas.

    Los mismos grupos se remuestrean para los dos brazos y se mide la distribución de
    la DIFERENCIA de AUC. `delta_se` es el número que decide, no el se de cada AUC.
    """
    key = ["company_id", "month"]
    m = a.merge(b[key + [score_col]], on=key, suffixes=("_a", "_b"))
    events = events or [e for e in pre.EVENTS + pre.JUDGES if e in m.columns]
    rng = np.random.default_rng(seed)
    rows = []
    for e in events:
        sub = m[[e, f"{score_col}_a", f"{score_col}_b", "group_id"]].dropna()
        if sub.empty or sub[e].nunique() < 2:
            continue
        y = sub[e].to_numpy()
        sa, sb = (_oriented(e, sub[f"{score_col}_{k}"].to_numpy()) for k in "ab")
        g = sub["group_id"].to_numpy()
        groups = np.unique(g)
        idx = {gr: np.flatnonzero(g == gr) for gr in groups}
        diffs = []
        for _ in range(nrep):
            ii = np.concatenate([idx[gr] for gr in rng.choice(groups, len(groups), replace=True)])
            if len(np.unique(y[ii])) > 1:
                diffs.append(_auc(y[ii], sb[ii]) - _auc(y[ii], sa[ii]))   # mismas filas en los dos
        diffs = np.array(diffs)
        delta = _auc(y, sb) - _auc(y, sa)
        rows.append({"evento": e, "auc_a": _auc(y, sa), "auc_b": _auc(y, sb), "delta": delta,
                     "delta_se": diffs.std(ddof=1), "sigmas": delta / max(diffs.std(ddof=1), 1e-9),
                     "p_no_mejora": float((diffs <= 0).mean())})
    return pd.DataFrame(rows).set_index("evento")


def anticipation(d: pd.DataFrame, score_col: str = "score_oof", threshold: float = 35.0) -> dict:
    """Meses de antelación del aviso frente al ESTADO mensual de estrés (`estres_mes`).

    Se mide contra el estado del mes, no contra las etiquetas *_6m: esas ya son ventanas
    futuras y te regalarían hasta 6 meses de ventaja ficticia.

    Solo cuentan las empresas que empiezan sanas y acaban entrando en estrés: avisar sobre
    quien ya estaba mal no tiene mérito. `cobertura` es la fracción de esas entradas que
    llegan avisadas; `meses_*` se calcula solo sobre las avisadas.
    """
    if "estres_mes" not in d.columns:
        return {}
    d = d.sort_values(["company_id", "month"])
    lead, n_onsets = [], 0
    for _, g in d.groupby("company_id"):
        st = g["estres_mes"].fillna(0).to_numpy()
        onsets = np.flatnonzero((st == 1) & (np.r_[0, st[:-1]] == 0))
        if not len(onsets) or onsets[0] == 0:      # ya empieza en estrés: no hay nada que anticipar
            continue
        t = onsets[0]
        n_onsets += 1
        alert = np.flatnonzero(g[score_col].to_numpy()[:t] < threshold)   # avisos ANTES de la entrada
        if len(alert):
            lead.append(t - alert[0])
    if not n_onsets:
        return {}
    lead = np.array(lead)
    return {"entradas_en_estres": n_onsets, "avisadas": len(lead), "cobertura": round(len(lead) / n_onsets, 3),
            "meses_mediana": float(np.median(lead)) if len(lead) else None,
            "meses_media": round(float(lead.mean()), 2) if len(lead) else None,
            "con_2m_o_mas": round(float((lead >= 2).mean()), 3) if len(lead) else None}


def _fmt(t: pd.DataFrame) -> str:
    cols = {"auc": 3, "se": 3, "ic95_lo": 3, "ic95_hi": 3, "delta": 4, "delta_se": 4, "sigmas": 1, "p_no_mejora": 3,
            "auc_a": 3, "auc_b": 3}
    return t.assign(**{c: t[c].round(n) for c, n in cols.items() if c in t}).to_string()


if __name__ == "__main__":
    d = pre.build()
    if "--comparar" in sys.argv:
        pa, pb = sys.argv[sys.argv.index("--comparar") + 1:][:2]
        print(_fmt(compare(pd.read_parquet(pa), pd.read_parquet(pb))))
        raise SystemExit

    d["score_oof"] = oof(d)
    d[["company_id", "group_id", "month", "score_oof", *pre.EVENTS,
       *[e for e in pre.JUDGES if e in d.columns]]].to_parquet("oof.parquet")
    activo = d[d.months_since_last_tx == 0]
    print("== AUC fuera de grupo y fuera del futuro (filas activas) ==")
    print(_fmt(auc_table(activo)))
    print("\n== anticipación ==", anticipation(activo))
