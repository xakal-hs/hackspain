"""Mide los eventos v2 del panel multi-modelo y re-mide las features contra ellos.

    cd research && uv run python src/measure_events_v2.py   ->  reports/eventos_v2.md
"""
from __future__ import annotations
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd, polars as pl
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import add_features, SCORE_FEATURES  # noqa: E402
from targets import add_events  # noqa: E402
import events_v2 as EV  # noqa: E402
import panel as P  # noqa: E402

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/eventos_v2.md"
LAST = pd.Timestamp("2026-08-01")


# ---------------------------------------------------------------- features del brainstorming
def brainstorm_features(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("company_id")
    r = lambda c, w, fn: g[c].transform(lambda x: getattr(x.rolling(w, min_periods=max(2, w // 2)), fn)())
    pm = r("payroll", 6, "mean")
    d["payroll_cv"] = (r("payroll", 6, "std") / pm).where(pm > 0)
    d["payroll_continuity_6m"] = g["payroll"].transform(lambda x: (x > 0).rolling(6, min_periods=3).mean())
    exp_tax = g["tax"].transform(lambda x: x.rolling(12, min_periods=6).sum()) / 4
    d["tax_miss"] = ((exp_tax - d.tax).clip(lower=0) / exp_tax).where(d.month.dt.month.isin([1, 4, 7, 10]) & (exp_tax > 0))
    ar3 = g["ar_issued"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    op3 = g["oper_in"].transform(lambda x: x.rolling(3, min_periods=1).sum())
    d["billing_to_cash"] = (ar3 / (op3 + 1)).where(d.has_erp & ar3.notna())
    med12 = g["oper_in"].transform(lambda x: x.rolling(12, min_periods=6).median())
    d["oper_persistence_6m"] = (d.oper_in >= 0.5 * med12).astype(float).where(med12.notna()).groupby(d.company_id).transform(
        lambda x: x.rolling(6, min_periods=3).mean())
    d["yoy_inflow"] = np.log((d.inflow + 1) / (g["inflow"].shift(12) + 1))
    d["lost_accel"] = d.lost_share - g["lost_share"].shift(3)
    dcash = (d.cash_end - g["cash_end"].shift(3)) / d.burn
    flags = [(d.growth_vs_12m < -0.2), (d.activity_trend < -0.2), (d.cust_trend < -0.2), (dcash < -1)]
    d["multi_signal_stress"] = sum(f.fillna(False).astype(int) for f in flags)
    return d


def payee_concentration(d: pd.DataFrame) -> pd.DataFrame:
    t = P.load_transactions()
    t = t.filter(~pl.col("internal") & ~pl.col("intragroup") & (pl.col("amount") < 0) & pl.col("counterparty_id").is_not_null())
    h = (t.group_by("company_id", "month", "counterparty_id").agg(a=pl.col("amount").abs().sum())
          .with_columns(s=pl.col("a") / pl.col("a").sum().over("company_id", "month"))
          .group_by("company_id", "month").agg(hhi=(pl.col("s") ** 2).sum())).to_pandas()
    d = d.merge(h, on=["company_id", "month"], how="left")
    d["payee_concentration"] = d.groupby("company_id").hhi.transform(lambda x: x.rolling(3, min_periods=1).mean())
    return d.drop(columns="hhi")


def hhi_ap(d: pd.DataFrame) -> pd.DataFrame:
    inv = pl.read_parquet(ROOT / "data/invoices.parquet").filter(pl.col("amount") < 0, pl.col("status") != "cancel",
                                                                 pl.col("counterparty_id").is_not_null())
    inv = inv.with_columns(m=pl.col("issuance_date").dt.truncate("1mo"), a=pl.col("amount").abs())
    rows = []
    for m in sorted(d.month.unique()):
        m = pd.Timestamp(m)
        w = inv.filter(pl.col("m") <= m, pl.col("m") > m - pd.DateOffset(months=6))
        h = (w.group_by("company_id", "counterparty_id").agg(pl.col("a").sum())
              .with_columns(s=pl.col("a") / pl.col("a").sum().over("company_id"))
              .group_by("company_id").agg(hhi_ap_6m=(pl.col("s") ** 2).sum()).to_pandas())
        h["month"] = m
        rows.append(h)
    return d.merge(pd.concat(rows), on=["company_id", "month"], how="left")


# ---------------------------------------------------------------- utilidades
def auc(y, x):
    m = pd.notna(y) & pd.notna(x)
    y, x = np.asarray(y)[m].astype(int), np.asarray(x)[m].astype(float)
    if len(np.unique(y)) < 2 or m.sum() < 200:
        return np.nan, int(m.sum())
    return roc_auc_score(y, x), int(m.sum())


def pct(x):
    return "—" if pd.isna(x) else f"{100 * x:.1f} %".replace(".", ",")


def num(x, nd=2):
    return "—" if pd.isna(x) else f"{x:.{nd}f}".replace(".", ",")


def main():
    raw = pl.read_parquet(ROOT / "data/panel.parquet")
    f = add_events(add_features(raw)).to_pandas()   # features actuales + eventos v1
    d = EV.build(f)
    d = brainstorm_features(d)
    d = payee_concentration(d)
    d = hhi_ap(d)
    comp = EV.company_level(d)
    d["final_in3"] = d.groupby("company_id").months_since_final_tx.shift(-3) > 0

    out = ["# Eventos v2: medición\n",
           "Definiciones del panel multi-modelo (`research/brainstorm/eventos/SINTESIS_glm5.3.md`), implementadas en `src/events_v2.py`. "
           "Etiqueta a 6 meses: 1 si el evento ocurre en (m, m+6], vacía si el futuro no es observable o la empresa se apaga en la ventana (censura).\n"]

    # 1. frecuencia y cobertura
    evs = [("E1", "Entrada en tensión de caja persistente (solo caja)"), ("E1_liq", "E1 contando la póliza disponible como liquidez"),
           ("E2", "Incumplimiento estricto (cualquier componente)"), ("E2_nomina_6m", "  · nómina regular que desaparece"),
           ("E2_cuota_6m", "  · cuota de deuda regular que desaparece"), ("E2_iva_6m", "  · IVA ausente 2 trimestres seguidos"),
           ("E2_ap90_6m", "  · deuda >90 días con proveedores que se dispara (ERP)"), ("E3", "Caída estructural de cobros (sin apagado ni rebote)"),
           ("E3_raw", "  · sin exigir 'sin rebote'"), ("E4", "Expansión sostenida autofinanciada"), ("E4_raw", "  · sin filtros de autofinanciación ni puntualidad"),
           ("churn_6m", "v1 · Apagado"), ("cash_stress_6m", "v1 · Saldo negativo"), ("decline_6m", "v1 · Caída de cobros"), ("positive_6m", "v1 · Crecimiento")]
    out.append("\n## 1. Frecuencia y cobertura\n\n| Evento | Filas etiquetadas | Tasa (empresa-mes) | Empresas con ≥1 evento |\n|---|---|---|---|\n")
    for c, lab in evs:
        s = d[c]; lab_rows = s.notna()
        comp_ever = d[lab_rows].groupby("company_id")[c].max().mean()
        out.append(f"| {lab} | {int(lab_rows.sum())} | {pct(s[lab_rows].mean())} | {pct(comp_ever)} |\n")

    # 2. calidad: persistencia, artefactos, borde
    out.append("\n## 2. ¿Son eventos reales? Persistencia, rebote y posibles artefactos\n\n")
    on = d[d.E1_onset_raw]
    conf = d[d.E1_onset]
    out.append(f"- **E1 (arranques de tensión)**: {len(on)} arranques en bruto; {len(conf)} confirmados (≥2 de los 3 meses siguientes en tensión) = "
               f"{pct(len(conf) / max(len(on), 1))}. De los confirmados: en jul/ago-2026 (borde) {pct((conf.month >= '2026-07-01').mean())}; "
               f"empresa con póliza {pct((conf.lc_limit > 0).mean())}; con póliza disponible que cubriría el hueco (E1 no se daría con liquidez) "
               f"{pct((~conf.E1_liq_stress).mean())}; empresa que se apaga en los 3 meses siguientes {pct(conf.final_in3.mean())}.\n")
    rec = d[d.E1_onset_raw]
    out.append(f"- **E7 recuperación tras E1**: {pct(rec.E7_recupera.mean())} de los arranques de tensión se recuperan con 3 meses seguidos de ≥0,5 meses de caja.\n")
    e2m = d[d.E2_any]
    out.append(f"- **E2 (incumplimientos, meses)**: {len(e2m)} meses con incumplimiento. Por componente: nómina {int(d.E2_nomina.sum())}, cuota {int(d.E2_cuota.sum())}, "
               f"IVA {int(d.E2_iva.sum())}, AP>90 {int(d.E2_ap90.sum())}. Nómina o cuota que **se retoma al mes siguiente** (posible ruido de calendario o categoría): "
               f"{pct(e2m[e2m.E2_nomina | e2m.E2_cuota].E2_resumed_next.mean())}. En jul/ago-2026: {pct((e2m.month >= '2026-07-01').mean())}.\n")
    out.append(f"- **E3 (caídas limpias)**: {int((d.E3 == 1).sum())} filas; rebotan después del horizonte (m+7..m+9 ≥ 80 % de la base): {pct(d.E3_postrebound.mean())}. "
               f"Exigir 'sin rebote' quita {pct(1 - (d.E3 == 1).sum() / max((d.E3_raw == 1).sum(), 1))} de las caídas brutas.\n")
    out.append(f"- **E4 (expansiones limpias)**: {int((d.E4 == 1).sum())} filas; revierten después (m+7..m+9 < 1,1× base): {pct(d.E4_reverts.mean())}. "
               f"Los filtros quitan {pct(1 - (d.E4 == 1).sum() / max((d.E4_raw == 1).sum(), 1))} de las expansiones brutas.\n")
    ge12 = d.groupby("company_id").size() >= 12
    b = d[d.company_id.isin(ge12[ge12].index)].groupby("company_id")
    out.append(f"- **E5 bache** (cobros < 70 % de su mediana y recuperan ≥ 80 % en ≤ 2 meses): {pct(b.E5_bache.any().mean())} de las empresas con ≥ 12 meses tienen alguno; "
               f"meses con caída que NO se recupera en 2 meses: {pct(b.E5_caida_mes.any().mean())} de las empresas. Ratio bache/caída de meses: "
               f"{num(d.E5_bache.sum() / max(d.E5_caida_mes.sum(), 1))}.\n")
    out.append(f"- **E6 sano sostenido**: {pct(comp.E6_sano.mean())} de las empresas ({int(comp.E6_sano.sum())}); con ERP {pct(comp[comp.has_erp].E6_sano.mean())}, "
               f"sin ERP {pct(comp[~comp.has_erp].E6_sano.mean())}.\n")

    # 3. solapamientos
    cols = ["E1", "E1_liq", "E2", "E3", "E4", "churn_6m"]
    sub = d.dropna(subset=cols)
    out.append(f"\n## 3. Solapamiento: P(columna = 1 | fila = 1), en {len(sub)} filas con todos observables\n\n| | " + " | ".join(cols) + " |\n|---|" + "---|" * len(cols) + "\n")
    for a in cols:
        row = [pct(sub[b][sub[a] == 1].mean()) if (sub[a] == 1).any() else "—" for b in cols]
        out.append(f"| **{a}** | " + " | ".join(row) + " |\n")
    # churn en la ventana completa (antes de censurar) para ver cuánto del E3 bruto era apagado
    out.append(f"\nCensura por apagado: {pct(d.decline_6m[d.decline_6m == 1].index.isin(d[d.churn_6m == 1].index).mean())} de las caídas de cobros v1 eran apagados; "
               f"en E3 esa fracción es 0 por construcción.\n")

    # 4. matriz de AUC
    feats = SCORE_FEATURES + ["payee_concentration", "lost_accel", "payroll_cv", "payroll_continuity_6m", "tax_miss", "billing_to_cash",
                              "oper_persistence_6m", "yoy_inflow", "multi_signal_stress", "hhi_ap_6m"]
    targets = ["E1", "E1_liq", "E2", "E3", "E4", "churn_6m"]
    out.append("\n## 4. AUC de cada feature frente a cada evento\n\nAUC de la feature tal cual (>0,5: más valor → más evento; <0,5: más valor → menos evento). "
               "**Negrita**: |AUC − 0,5| ≥ 0,10. Entre paréntesis, la distancia a 0,5 orientada, para leer la fuerza sin mirar el signo. "
               "Las filas son empresa-mes con etiqueta observable; n entre 1.000 y 9.000 según feature y evento.\n\n| Feature | " + " | ".join(targets) + " |\n|---|" + "---|" * len(targets) + "\n")
    strength = {}
    for c in feats:
        cells = []
        for t in targets:
            a, n = auc(d[t], d[c])
            strength[(c, t)] = abs(a - 0.5) if not np.isnan(a) else np.nan
            txt = num(a)
            cells.append(f"**{txt}**" if not np.isnan(a) and abs(a - 0.5) >= 0.10 else txt)
        tag = " *(brainstorming)*" if c not in SCORE_FEATURES else ""
        out.append(f"| `{c}`{tag} | " + " | ".join(cells) + " |\n")

    # 5. brainstorming: antes (apagado) vs ahora
    out.append("\n## 5. Features del brainstorming: ¿su señal era desconexión?\n\n| Feature | AUC frente a apagado | Mejor |AUC−0,5| frente a E1-E4 | ¿Sobrevive? |\n|---|---|---|---|\n")
    for c in feats[len(SCORE_FEATURES):]:
        a_ch = strength.get((c, "churn_6m"))
        best = np.nanmax([strength.get((c, t), np.nan) for t in ["E1", "E1_liq", "E2", "E3", "E4"]])
        verdict = "sí" if best >= 0.08 else ("débil" if best >= 0.05 else "no")
        out.append(f"| `{c}` | {num(0.5 + a_ch if a_ch == a_ch else np.nan)} (fuerza {num(a_ch)}) | {num(best)} | {verdict} |\n")

    # 6. circularidad: la propia variable del evento
    out.append("\n## 6. Circularidad\n\n")
    a1, _ = auc(d.E1, -d.runway_m); a1b, _ = auc(d.cash_stress_6m, -d.runway_m)
    out.append(f"- Meses de caja de hoy frente a E1: AUC {num(a1)} (frente a 'saldo negativo' v1: {num(a1b)}). "
               "Si baja, el nuevo evento es menos circular: exige entrar en tensión desde una situación sana.\n")
    a3, _ = auc(d.E3, -d.growth_vs_12m); a3b, _ = auc(d.decline_6m, -d.growth_vs_12m)
    out.append(f"- Tendencia de cobros de hoy frente a E3: AUC {num(a3)} (frente a 'caída de cobros' v1: {num(a3b)}).\n")

    # 7. casos para revisión manual
    out.append("\n## 7. Casos para revisar a mano (3 por evento, aleatorios)\n\n")
    rng = np.random.default_rng(7)
    show = ["month", "inflow", "outflow", "cash_end", "runway_m", "lc_limit", "lc_drawn", "payroll", "debt_service", "tax", "n_tx", "months_since_final_tx"]
    for flag, lab in [("E1_onset", "E1 arranque confirmado"), ("E2_any", "E2 incumplimiento"), ("E3", "E3 caída limpia (fila de referencia m)"),
                      ("E4", "E4 expansión limpia (fila de referencia m)")]:
        idx = d.index[(d[flag] == 1) | (d[flag] == True)]  # noqa: E712
        for i in rng.choice(idx, size=min(3, len(idx)), replace=False):
            cid, m = d.at[i, "company_id"], d.at[i, "month"]
            w = d[(d.company_id == cid) & (d.month >= m - pd.DateOffset(months=4)) & (d.month <= m + pd.DateOffset(months=7))][show].copy()
            for c in ["inflow", "outflow", "cash_end", "lc_limit", "lc_drawn", "payroll", "debt_service", "tax"]:
                w[c] = (w[c] / 1e3).round(0)
            w["runway_m"] = w.runway_m.round(2)
            w["month"] = w.month.dt.strftime("%Y-%m")
            out.append(f"\n**{lab}** · {cid} · {m:%Y-%m} (importes en miles)\n\n```\n{w.to_string(index=False)}\n```\n")

    OUT.write_text("".join(out))
    d[["company_id", "month"] + [c for c, _ in evs if c in d] + ["E1_onset", "E2_any", "E5_bache"]].to_parquet(ROOT / "reports/eventos_v2.parquet")
    print("".join(out[:40]))


if __name__ == "__main__":
    main()
