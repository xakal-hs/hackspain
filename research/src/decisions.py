"""Registro de decisiones con evidencia y gráficas calculadas sobre los datos.

    uv run python src/decisions.py   ->  reports/decisions.json, reports/metrics_app.json, DECISIONS.md
"""
from __future__ import annotations
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd, polars as pl
import lightgbm as lgb
from mlforecast import MLForecast
from sklearn.metrics import roc_auc_score
from features import add_features
from targets import add_events
from xray import SPEC, PRIOR_W, PILLARS, TrajectoryForecaster, BANDS
import evaluate as E

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "reports"
FINAL = "v7"


def chart(type_, title, x_label, y_label, labels=None, datasets=(), note=None):
    c = {"type": type_, "title": title, "x_label": x_label, "y_label": y_label, "datasets": list(datasets)}
    if labels is not None:
        c["labels"] = [str(l) for l in labels]
    if note:
        c["note"] = note
    return c


def ds(label, data):
    return {"label": label, "data": [None if (isinstance(v, float) and np.isnan(v)) else (round(float(v), 4) if isinstance(v, (int, float, np.floating, np.integer)) else v) for v in data]}


def load_metrics(tag):
    p = REP / f"metrics_{tag}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ------------------------------------------------------------------ evidencias calculadas
def ev_fx():
    import fx as FX
    D = ROOT / "data"
    t = pl.read_parquet(D / "transactions.parquet").select("company_id", "product_id", "date", "exchange_rate")
    c = pl.read_parquet(D / "companies.parquet").select("company_id", pl.col("currency").alias("ccur"))
    prod = pl.concat([pl.read_parquet(D / "banking_products.parquet").select("product_id", pl.col("currency").alias("pcur")),
                      pl.read_parquet(D / "debt_products.parquet").select("product_id", pl.col("currency").alias("pcur"))])
    x = (t.join(prod, on="product_id", how="left").join(c, on="company_id").filter(pl.col("pcur") != pl.col("ccur"))
          .with_columns(month=pl.col("date").dt.truncate("1mo")))
    fx = pl.from_pandas(FX.load()[["month", "currency", "per_eur"]]).with_columns(pl.col("month").cast(pl.Datetime("us")))
    x = (x.join(fx.rename({"currency": "pcur", "per_eur": "a"}), on=["month", "pcur"], how="left")
          .join(fx.rename({"currency": "ccur", "per_eur": "b"}), on=["month", "ccur"], how="left")
          .with_columns(ratio=pl.col("exchange_rate") / (pl.col("a") / pl.col("b"))))
    g = (x.with_columns(pair=pl.col("pcur") + "→" + pl.col("ccur")).group_by("pair")
          .agg(n=pl.len(), ok=((pl.col("ratio") - 1).abs() < 0.1).mean(), one=(pl.col("exchange_rate") == 1).mean())
          .sort("n", descending=True).head(10).to_pandas())
    total_ok = float(((x["ratio"] - 1).abs() < 0.1).mean())
    return g, total_ok, x.height


def ev_internal(panel):
    ext = float(panel.gross_flow.sum()); internal = float(panel.internal_flow.sum())
    return internal / (ext + internal)


def ev_invoices():
    inv = pl.read_parquet(ROOT / "data/invoices.parquet")
    g = (inv.filter(pl.col("status").is_in(["paid", "overdue", "pending"]))
            .group_by("status").agg(same=(pl.col("payment_date") == pl.col("due_date")).mean(),
                                    pend=(pl.col("pending_amount").abs() > 0).mean()).sort("status").to_pandas())
    return g


def ev_startup(raw: pl.DataFrame, f: pd.DataFrame):
    old = raw.sort("company_id", "month").with_columns(
        out3=pl.col("outflow").rolling_sum(3, min_samples=1).over("company_id", order_by="month"),
        idx=pl.int_range(pl.len()).over("company_id", order_by="month"))
    old = old.with_columns(r=(pl.col("cash_end").clip(0, None) / (pl.col("out3") / 3 + 1) + 1).log()).to_pandas()
    a = old.groupby("idx").r.median().head(10)
    b = f.assign(r=f.runway.clip(lower=0)).groupby("month_idx").r.median().head(10)
    return a, b


def ev_churn_profile(f: pd.DataFrame):
    last = f[f.months_since_final_tx == 0].groupby("company_id").month.max()
    churned = last[last < f.month.max()].index
    f = f.assign(rel=f.inflow / (f.groupby("company_id").inflow.transform("mean") + 1))
    f = f.merge(last.rename("last"), on="company_id")
    f["to_end"] = ((f["last"].dt.year - f.month.dt.year) * 12 + (f["last"].dt.month - f.month.dt.month))
    c = f[f.company_id.isin(churned) & f.to_end.between(0, 8)].groupby("to_end").rel.median()
    a = f[~f.company_id.isin(churned)]
    a = a.assign(to_end=((a.month.max().year - a.month.dt.year) * 12 + (a.month.max().month - a.month.dt.month)))
    a = a[a.to_end.between(0, 8)].groupby("to_end").rel.median()
    return c.sort_index(ascending=False), a.sort_index(ascending=False), len(churned)


def ev_persistence(f: pd.DataFrame):
    f = f.sort_values(["company_id", "month"])
    f["nm3"] = (f.in3 - f.out3) / (f.in3 + f.out3 + 1)
    f["g3"] = np.log((f.in3 + 1) / (f.groupby("company_id").in3.shift(3) + 1))
    out = {}
    for c in ["nm3", "net_margin_6m", "g3", "growth_vs_12m"]:
        out[c] = f[c].corr(f.groupby("company_id")[c].shift(1), method="spearman")
    return out


def ev_tax_seasonality(f: pd.DataFrame):
    s = f.assign(moy=f.month.dt.month, share=f.tax / (f.outflow + 1))
    return s.groupby("moy").share.mean()


def ev_zeros(f: pd.DataFrame):
    cols = ["debt_burden", "refund_rate", "lc_util", "ap_overdue_ratio", "ar_overdue_90_ratio", "ap_late_share", "transfer_dep"]
    return {c: float((f[c] == 0).mean() / f[c].notna().mean()) for c in cols}


def ev_feature_auc(f: pd.DataFrame):
    rows = {}
    for c in SPEC:
        r = {}
        for t in ["churn_6m", "cash_stress_6m", "decline_6m"]:
            m = f[c].notna() & f[t].notna()
            r[t] = roc_auc_score(f.loc[m, t], f.loc[m, c]) if f.loc[m, t].nunique() > 1 else np.nan
        rows[c] = r
    return pd.DataFrame(rows).T


def ev_old_event_def(f: pd.DataFrame):
    """Evento 'caída de cobros >50 %' relativo al trimestre actual (definición inicial) vs base anual (actual)."""
    f = f.sort_values(["company_id", "month"]).copy()
    g = f.groupby("company_id").in3
    drop_old = pd.concat([g.shift(-k) < 0.5 * f.in3 for k in range(1, 7)], axis=1).any(axis=1).astype(float)
    obs = f.groupby("company_id").month.shift(-6).notna() & (f.month_idx >= 5)
    out = {}
    for c in ["net_margin_6m", "growth_vs_12m"]:
        m = obs & f[c].notna()
        out[c] = (roc_auc_score(drop_old[m], f.loc[m, c]), roc_auc_score(f.loc[m & f.decline_6m.notna(), "decline_6m"], f.loc[m & f.decline_6m.notna(), c]))
    return out


def ev_alignment():
    rng = np.random.default_rng(0); rows = []
    for u in range(200):
        x = rng.normal(size=30); y = np.r_[0, x[:-1]] * 5 + rng.normal(size=30) * 0.3
        rows.append(pd.DataFrame({"unique_id": u, "ds": pd.date_range("2020-01-01", periods=30, freq="MS"), "y": y, "x": x}))
    df = pd.concat(rows); T = pd.Timestamp("2022-03-01"); out = {}
    for s in [0, 1, 2, 3]:
        d = df.sort_values(["unique_id", "ds"]).copy()
        for h in range(1, 4):
            d[f"x_h{h}"] = d.groupby("unique_id")["x"].shift(s)
        hist = d[d.ds <= T]
        m = MLForecast(models={"lgb": lgb.LGBMRegressor(verbose=-1, n_estimators=200)}, freq="MS", lags=[1])
        m.fit(hist.drop(columns="x"), static_features=[], max_horizon=3, horizon_feature_templates=["x_h{h}"])
        fut = d[(d.ds > T) & (d.ds <= T + pd.DateOffset(months=3))].drop(columns=["x", "y"])
        p = m.predict(3, new_df=hist.drop(columns="x"), X_df=fut).merge(df, on=["unique_id", "ds"])
        out[s] = float((p.y - p.lgb).abs().mean())
    return out


def ev_alpha(scored: pd.DataFrame):
    g = scored.groupby("company_id")
    out = {}
    for a in [0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
        e = g.score_raw.transform(lambda x: x.ewm(alpha=a, adjust=False).mean())
        out[a] = (float(e.groupby(scored.company_id).diff().abs().mean()),
                  float((e.groupby(scored.company_id).diff(3).abs() >= 10).mean()))
    return out


def ev_cqr(panel):
    from sklearn.model_selection import GroupKFold
    cg = panel.drop_duplicates("company_id").set_index("company_id")["group_id"]
    ids = cg.index.to_numpy(); tr, va = next(GroupKFold(5).split(ids, groups=cg.values))
    tr_ids, va_ids = set(ids[tr]), set(ids[va]); cut = pd.Timestamp("2026-02-01")
    sc = E.fit_scorer(panel[(panel.month <= cut) & panel.company_id.isin(tr_ids)], cut, True)
    s = E.build_series(sc.score_panel(panel), panel); sh = s[s.ds <= cut]
    out = {}
    for conf in [False, True]:
        fc = TrajectoryForecaster(conformal=conf).fit(sh[sh.unique_id.isin(tr_ids)][["unique_id", "ds", "y"]])
        p = fc.predict(sh[sh.unique_id.isin(va_ids)][["unique_id", "ds", "y"]]).merge(s[["unique_id", "ds", "y"]], on=["unique_id", "ds"])
        out[conf] = p.assign(c=(p.y >= p.q10) & (p.y <= p.q90)).groupby("h").c.mean()
    return out


# ------------------------------------------------------------------ construcción
def build():
    raw = pl.read_parquet(ROOT / "data/panel.parquet")
    f = add_events(add_features(raw)).to_pandas()
    import joblib
    art = joblib.load(ROOT / "artifacts/xray.joblib")
    scorer = art["scorer"]
    scored = scorer.score_panel(f)
    fm = load_metrics(FINAL) or {}
    D = []

    def add(**k):
        k.setdefault("chart", None); k.setdefault("status", "decidido"); k.setdefault("alternatives", ""); k.setdefault("evidence", "")
        D.append({"id": f"D{len(D) + 1:02d}", **k})

    comp = pl.read_parquet(ROOT / "data/companies.parquet").to_pandas()
    gs = comp.groupby("group_id").size().value_counts().sort_index()
    add(category="producto", title="El score se calcula por empresa, no por grupo",
        question="¿Score por company_id o por grupo empresarial? El enunciado habla de 250 empresas y hay 1286 en 250 grupos.",
        decision="Score, trayectoria y alertas por company_id. La validación separa por group_id para que ningún grupo esté a la vez en train y test.",
        why="Todos los ficheros se cruzan por company_id y cada empresa tiene su propia caja y sus propias facturas. Un grupo mezcla negocios distintos (holdings de hasta 24 empresas). Separar por grupo en la validación evita la fuga que avisa el enunciado.",
        alternatives="Agregar por grupo (ponderando por volumen). Se puede hacer después sobre los scores de empresa si el leaderboard lo pide.",
        evidence=f"{len(comp)} empresas en {comp.group_id.nunique()} grupos; mediana de {int(comp.groupby('group_id').size().median())} empresas por grupo.",
        status="a confirmar con la organización",
        chart=chart("bar", "Tamaño de los grupos empresariales", "empresas por grupo", "nº de grupos", gs.index.tolist(), [ds("grupos", gs.values)]))

    add(category="modelo", title="Sin etiquetas: score anclado a hechos observables",
        question="¿Hay variable objetivo? El dataset no trae etiquetas de impago ni de salud.",
        decision="El nivel es un score interpretable (percentiles ponderados). Sus pesos se calibran con eventos futuros observables: apagado (la empresa deja de operar), tensión de caja (saldo negativo) y declive (cobros <50 % de su media anual). La trayectoria es una previsión supervisada del propio score.",
        why="Un score sin ancla externa puede estar al revés sin que ninguna métrica lo detecte. Eso nos pasó en la v1: AUC de 0,37 frente al apagado. Con eventos observables, el nivel del score significa algo y se puede medir.",
        alternatives="Score totalmente no supervisado (clustering, PCA): no es interpretable ni verificable. Predecir directamente el evento: sería una caja negra y solo daría una cara del problema.",
        evidence=f"Tasas de evento a 6 meses: apagado {f.churn_6m.mean():.1%}, tensión de caja {f.cash_stress_6m.mean():.1%}, declive {f.decline_6m.mean():.1%}. AUC del score final frente a evento adverso: {fm.get('auc_level_vs_adverse_6m', float('nan')):.2f}.",
        status="a confirmar con la organización")

    fxg, fx_ok, fx_n = ev_fx()
    add(category="datos", title="Tipos de cambio: los del dataset, validados contra BCE y currency-api",
        question="¿Qué tipo de cambio usar para las cuentas en otra moneda?",
        decision="Se descargan tipos reales mensuales: BCE (oficial, 30 monedas) y fawazahmed0/currency-api (13 monedas que el BCE no publica: ARS, CLP, COP, AOA, MZN...). En transacciones y en facturas se usa el tipo del fichero si está a ±10 % del real y, si no, el real del mes. El tamaño de la empresa (log_scale) se pasa a EUR con el tipo real.",
        why="El 4 % de los movimientos está en productos con una moneda distinta de la de la empresa. Sin convertir, un movimiento en CLP pesa unas mil veces más. Los tipos del dataset son correctos casi siempre, pero hay filas con fx=1 (MZN, parte de GBP) o 0 (VND redondeado), que darían importes absurdos o una división por cero.",
        alternatives="Usar siempre el tipo real: perdería el tipo efectivo del banco. Usar siempre el del dataset: rompe con fx=1 o fx=0.",
        evidence=f"{fx_ok:.1%} de las {fx_n} transacciones en otra moneda tienen un tipo a ±10 % del real. El resto se corrige con el tipo real del mes (fx=1 no informado, fx=0 por redondeo en VND).",
        chart=chart("bar", "Transacciones con el tipo del dataset a ±10 % del real (top pares)", "par de monedas", "% de filas",
                    fxg.pair.tolist(), [ds("tipo dentro de ±10 % del real", fxg.ok * 100), ds("tipo = 1 (no informado)", fxg.one * 100)]))

    ish = ev_internal(f)
    add(category="datos", title="Transferencias internas fuera de los flujos",
        question="¿Cuentan como cobros o pagos los traspasos entre cuentas de la misma empresa?",
        decision="Un par del mismo día, con el mismo importe y signo opuesto entre dos productos de la empresa se marca como interno. Lo mismo con los pares entre dos empresas del mismo grupo (intragrupo, >100). Ambos se excluyen de entradas y salidas, igual que investment_deployment/return.",
        why="Inflan los denominadores (entradas, salidas) sin actividad económica real y diluyen ratios como el margen o la carga de deuda. Los intragrupo además hacían pasar por 'dependencia de transferencias' lo que es tesorería del grupo.",
        evidence=f"El {ish:.1%} del volumen bruto son traspasos internos o intragrupo.",
        chart=chart("bar", "Composición del volumen bruto", "tipo de flujo", "% del volumen", ["externo", "interno"], [ds("volumen", [100 * (1 - ish), 100 * ish])]))

    ig = ev_invoices()
    add(category="datos", title="Facturas: impagadas según pending_amount, no según payment_date",
        question="¿Cómo saber si una factura estaba impagada a fin de cada mes?",
        decision="Impagada = pending_amount ≠ 0 y status ≠ paid. En ese caso se ignora payment_date. Si hoy está impagada, estuvo impagada en todos los cierres anteriores (sin fuga). Los pagos tardíos se miden a fecha de cierre, sin mirar pagos posteriores. Se descartan las fechas imposibles (año 7025).",
        why="En las facturas vencidas, payment_date es igual a due_date en el 96 % de los casos. Usar payment_date las daba por pagadas en plazo y la morosidad real (unas 170 000 facturas) no se veía.",
        evidence="; ".join(f"{r.status}: payment_date = due_date en el {r.same:.0%}, con pendiente > 0 en el {r.pend:.0%}" for r in ig.itertuples()),
        chart=chart("bar", "payment_date = due_date según estado de la factura", "estado", "% de facturas", ig.status.tolist(),
                    [ds("payment_date = due_date", ig.same * 100), ds("pending_amount > 0", ig.pend * 100)]))

    a, b = ev_startup(raw, f)
    add(category="datos", title="Primer mes parcial fuera y ventanas escaladas: sin artefacto de arranque",
        question="¿Por qué las empresas recién incorporadas parecían más sanas?",
        decision="Se descarta el primer mes si la primera transacción cae después del día 5 (mes parcial). Las sumas móviles se escalan a w meses (media × w) en vez de sumar lo que haya.",
        why="Con rolling_sum(min_samples=1) el gasto de 3 meses con solo 1 mes de historia se infraestimaba y el runway salía inflado. Todas las empresas nuevas parecían líquidas y 'se deterioraban' al madurar.",
        evidence=f"Mediana del runway en el mes 0: {a.iloc[0]:.2f} con el método antiguo y {b.iloc[0]:.2f} con el nuevo; en el mes 6: {a.iloc[6]:.2f} y {b.iloc[6]:.2f}.",
        chart=chart("line", "Mediana del runway según los meses de historia", "meses desde el alta", "runway (log)", list(range(len(a))),
                    [ds("método antiguo (rolling_sum min_samples=1)", a.values), ds("método actual", b.reindex(range(len(a))).values)]))

    c, act, nch = ev_churn_profile(f)
    add(category="datos", title="Las empresas que dejan de operar siguen en el panel",
        question="¿Qué hacer con las empresas cuyas transacciones terminan antes de agosto de 2026?",
        decision="La rejilla llega siempre hasta el último mes completo. Los meses sin movimientos tienen flujos a 0 y un contador CAUSAL de meses consecutivos sin movimientos (months_since_last_tx), que se reinicia al volver a operar. Regla de negocio: sin movimientos, el score no puede pasar de 30. El apagado definitivo (months_since_final_tx, que mira el futuro) se usa solo como etiqueta, nunca como feature.",
        why="Dejar de operar es la señal de deterioro más fuerte y antes desaparecía del panel (sesgo de supervivencia). Sus entradas caen mucho antes del final, así que es anticipable.",
        evidence=f"{nch} empresas se apagan antes de 2026-08. El review de la v5 detectó que el contador anterior (meses desde la última transacción del dataset) no era causal: 429 meses sin movimientos en mitad de la serie figuraban como activos. Con el contador causal hay 991 meses de inactividad frente a 498. Queda por confirmar con la organización si el apagado es cierre o baja de Embat.",
        status="a confirmar con la organización",
        chart=chart("line", "Entradas relativas a la media propia antes del último mes", "meses hasta el final", "entradas / media",
                    [str(i) for i in c.index], [ds("empresas que se apagan", c.values), ds("empresas activas", act.reindex(c.index).values)]))

    per = ev_persistence(f)
    tax = ev_tax_seasonality(f)
    add(category="score", title="Ventanas de 6 y 12 meses en vez de 3 (estacionalidad y ruido)",
        question="¿Qué ventana usar para el margen y el crecimiento?",
        decision="Margen de caja a 6 meses y tendencia de cobros como media de 3 meses frente a media de 12 meses. Los impuestos trimestrales (enero, abril, julio y octubre) quedan absorbidos.",
        why="Con ventanas de 3 meses el margen y el crecimiento revertían a la media: eran ruido que movía más de la mitad del score. Comparar trimestres distintos mezclaba estacionalidad.",
        evidence=f"Persistencia mes a mes (Spearman): margen 3m {per['nm3']:.2f} frente a 6m {per['net_margin_6m']:.2f}; crecimiento trimestral {per['g3']:.2f} frente a 3m/12m {per['growth_vs_12m']:.2f}.",
        chart=chart("bar", "Peso de los impuestos en las salidas por mes del año", "mes", "impuestos / salidas", [str(m) for m in tax.index], [ds("media", tax.values)],
                    note="Picos trimestrales: por eso se usan ventanas de 6 y 12 meses"))

    fa = ev_feature_auc(f)
    add(category="score", title="Runway con base de gasto robusta: encogerse no mejora la liquidez",
        question="¿Por qué las empresas que se apagaban tenían más 'meses de caja'?",
        decision="Runway = signo(caja) × log(1 + |caja| / gasto), con gasto = máx(media de 3 meses, media de 12 meses). La caja negativa da un runway negativo, así que la feature binaria sobra.",
        why="Si el gasto se desploma, caja/gasto sube aunque la empresa se esté apagando. Con la base anual el denominador no cae y se premia la caja real.",
        evidence=f"AUC del runway frente a tensión de caja a 6 meses: {fa.loc['runway', 'cash_stress_6m']:.2f} (menos de 0,5 = protege).",
        chart=chart("bar", "AUC de cada feature frente a eventos a 6 meses (0,5 = sin señal)", "feature", "AUC",
                    [SPEC[k][3] for k in fa.index], [ds("apagado", fa.churn_6m), ds("tensión de caja", fa.cash_stress_6m), ds("declive", fa.decline_6m)],
                    note="AUC < 0,5 significa que valores altos protegen"))

    z = ev_zeros(f)
    add(category="score", title="Masa en cero: el cero es 'lo mejor' o 'no aplica', nunca un empate en el percentil 0",
        question="¿Cómo puntuar features donde la mayoría de filas vale exactamente 0?",
        decision="Deuda, devoluciones, vencidos, retrasos, uso de póliza y transferencias: el 0 vale 100 y los positivos se ordenan entre sí (continuo en 0+). Nóminas = 0 se trata como 'no aplica' (NaN). En el resto, los empates van al rango medio.",
        why="Con el primer índice del cuantil, el 88 % de filas con refund_rate = 0 caía al percentil 0 y un reembolso de 0,1 % hundía el score 90 puntos. Una empresa sin nóminas no está 'más sana' por eso, simplemente la feature no aplica.",
        evidence="Proporción de ceros entre las filas con dato: " + ", ".join(f"{k} {v:.0%}" for k, v in z.items()),
        chart=chart("bar", "Filas con valor exactamente 0 (entre las que tienen dato)", "feature", "% de ceros", list(z.keys()), [ds("% ceros", [v * 100 for v in z.values()])]))

    add(category="score", title="Nuevas señales: póliza de crédito, clientes perdidos, amplitud de cartera y volatilidad a la baja",
        question="¿Qué variables añadir tras el review?",
        decision="Se añaden estas señales: lc_util (dispuesto/límite de pólizas, reconstruido hacia atrás), lost_share (% de la facturación de hace 3-12 meses de clientes a los que ya no se factura), cust_trend (clientes facturados en 3 meses frente a 12) y hhi_ar_6m (concentración). net_vol_6m pasa a medir solo la volatilidad a la baja (semidesviación de los meses con flujo negativo, sobre el gasto). transfer_dep se queda solo con las transferencias reales: la categoría '-' (sin categorizar) pasa a contexto. No se usan debt_products ni debt_schedule_config como features mensuales porque son una foto final y proyectarlos hacia atrás filtraría información.",
        why="Perder clientes es la señal más temprana de apagado y de declive. El review de la v5 mostró que transfer_dep medía sobre todo cobros sin categorizar, y que la volatilidad total penalizaba a las empresas con mucha caja: lo que daña es la volatilidad a la baja.",
        evidence=f"AUC frente a apagado: lost_share {fa.loc['lost_share', 'churn_6m']:.2f}, cust_trend {fa.loc['cust_trend', 'churn_6m']:.2f}. Frente a tensión de caja: lc_util {fa.loc['lc_util', 'cash_stress_6m']:.2f}. transfer_dep sin '-' frente a apagado: {fa.loc['transfer_dep', 'churn_6m']:.2f}, casi sin señal.")

    w = pd.Series(scorer.weights_)
    prior = pd.Series(PRIOR_W)[w.index]; prior = prior / prior.sum()
    add(category="score", title="Pesos calibrados por evento con signo económico restringido",
        question="¿Cómo fijar los pesos del score sin etiquetas y sin perder interpretabilidad?",
        decision="Para cada evento (apagado, tensión de caja, declive) se ajusta una logística P(evento) = σ(b − Σ w·s) con w ≥ 0, sobre filas cuyo evento ya era observable. Los pesos normalizados se promedian para que cada tipo de deterioro cuente igual. Si los datos contradicen la dirección económica de una feature, su peso queda en 0.",
        why="Calibrar contra el evento compuesto dejaba que el declive (20 % de las filas) dominara, y la disciplina de pagos, que predice los apagados, quedaba en 0. Restringir el signo mantiene la monotonía: mejorar una señal nunca baja el score.",
        alternatives="Pesos a priori (v4a): funcionan peor frente a eventos. Logística sin restricción: pesos negativos e inexplicables.",
        evidence="Pesos por debajo del 1 %: " + (", ".join(SPEC[k][3] for k, v in w.items() if v < 0.01) or "ninguno") + ". Los datos no respaldan su dirección. Mayores pesos: " + ", ".join(f"{SPEC[k][3]} {v:.0%}" for k, v in w.sort_values(ascending=False).head(4).items()) + ".",
        chart=chart("bar", "Pesos por feature: a priori frente a calibrados", "feature", "peso", [SPEC[k][3] for k in w.index],
                    [ds("a priori", prior.values), ds("calibrado (modelo final)", w.values)]))

    al = ev_alignment()
    add(category="modelo", title="Exógenas por horizonte retardadas h meses (horizon_feature_templates)",
        question="¿Cómo pasar señales actuales al forecaster directo de mlforecast sin fuga de información?",
        decision="Por cada exógena c se crea c_h{h} = c retardada h meses y se usa horizon_feature_templates. El modelo del horizonte h lee en la fila de la fecha objetivo T+h el valor de T, que es conocido.",
        why="En la estrategia directa, cada modelo h usa la exógena en la fecha objetivo. Pasar c sin retardar sería una fuga y retardarla 3 meses para todos los horizontes da información vieja a h1 y h2. Lo verificamos con datos sintéticos (y_t = 5·x_{t−1}): con desplazamiento 1 el error es casi 0 en todos los horizontes.",
        evidence="MAE en el experimento sintético según el desplazamiento de la exógena: " + ", ".join(f"{k}: {v:.2f}" for k, v in al.items()),
        chart=chart("bar", "Experimento de alineación temporal (y_t = 5·x_{t−1})", "desplazamiento de x en la fila objetivo", "MAE", [str(k) for k in al], [ds("MAE", list(al.values()))]))

    alpha = ev_alpha(scored)
    add(category="score", title="Suavizado EWMA α = 0,5 con explicación exacta",
        question="¿Cuánto suavizar el score publicado?",
        decision="Score publicado = EWMA(α = 0,5) del score bruto. Como el EWMA es lineal, se suaviza cada contribución por separado y el score sigue siendo la suma exacta de contribuciones: explain() cuadra al céntimo.",
        why="Con α = 0,5 un bache de un mes pesa la mitad y una caída estructural se refleja al 87,5 % en 3 meses. Es el equilibrio entre estabilidad ante baches (lo pide el enunciado) y retraso en la detección.",
        evidence="Cambio medio mensual |Δ| y proporción de movimientos ≥10 a 3 meses según α: " + "; ".join(f"α={a}: {v[0]:.2f} / {v[1]:.0%}" for a, v in alpha.items()),
        chart=chart("line", "Estabilidad del score según α", "α", "valor", [str(a) for a in alpha],
                    [ds("|Δ| medio mensual", [v[0] for v in alpha.values()]), ds("% movimientos ≥10 en 3m", [100 * v[1] for v in alpha.values()])]))

    add(category="score", title="Features de facturas: se arrastra el último dato hasta 3 meses",
        question="¿Por qué el score saltaba cuando no vencían facturas en un trimestre?",
        decision="late_share_ap, late_share_ar y hhi_ar_6m arrastran el último valor conocido durante un máximo de 3 meses. Las tendencias se calculan desde el tercer mes de historia.",
        why="Cuando una feature aparecía o desaparecía, los pesos se renormalizaban y el score bruto saltaba 8,9 puntos de media, frente a 4,7 sin cambio de disponibilidad.",
        evidence="Medido antes del cambio: |Δ score bruto| de 8,9 con cambio de disponibilidad frente a 4,7 sin él (19 % de las filas).")

    seg = fm.get("mae_h3_by_segment", {})
    add(category="ood", title="Robustez para empresas nunca vistas: ratios, percentiles congelados, OOD sobre valores crudos y confianza",
        question="¿Cómo se comporta el sistema con empresas del test oculto, quizá muy fuera de distribución?",
        decision="Features adimensionales (independientes de moneda y tamaño), con un suelo EPS relativo a la escala de la empresa (0,1 % de su volumen mensual) en lugar de 1 unidad fija: el score no varía más de 1 punto al multiplicar los importes por 1e-6..1e6 (test). Los percentiles se congelan en train y saturan en 0 o 100, sin extrapolar. El OOD se mide sobre valores crudos antes de recortar, más el contexto (tamaño en EUR, actividad, % en divisa). Se publica una confianza = cobertura × (1 − OOD) × historia. Con menos de 3 meses, respaldo AR(1) con intervalo ×1,5. Columnas ausentes = NaN (baja la cobertura, no falla).",
        why="El test son 60-80 empresas nuevas, con historia corta, sin ERP o con escalas nunca vistas. Mejor un score con confianza baja y explícita que uno que extrapola.",
        evidence="MAE h3 por segmento (modelo / AR(1)): " + "; ".join(f"{k}: {v['mae']:.1f} / {v['mae_ar1']:.1f} (n={v['n']})" for k, v in seg.items() if v.get("mae") is not None),
        chart=chart("bar", "Error a 3 meses por segmento (validación out-of-group)", "segmento", "MAE h3", list(seg.keys()),
                    [ds("modelo", [v["mae"] for v in seg.values()]), ds("AR(1)", [v["mae_ar1"] for v in seg.values()])]) if seg else None)

    # sin dato = neutro frente a renormalizar: sesgo de arranque
    W = pd.Series(scorer.weights_)
    Smat = scored[[f"s_{k}" for k in W.index]]
    a_, b_ = scorer.scale_
    renorm = a_ + b_ * (Smat.fillna(0).to_numpy() @ W.values) / np.where(Smat.notna().to_numpy() @ W.values > 0, Smat.notna().to_numpy() @ W.values, np.nan)
    tmp = scored[["company_id", "month", "score_raw"]].assign(renorm=renorm).merge(f[["company_id", "month", "month_idx", "months_since_last_tx"]], on=["company_id", "month"])
    tmp = tmp[tmp.months_since_last_tx == 0]
    by = tmp.groupby("month_idx")[["score_raw", "renorm"]].median().head(12)
    add(category="score", title="Sin dato = valor neutro (50), no renormalizar",
        question="¿Cómo puntuar una feature sin dato (sin ERP, historia corta)?",
        decision="Una feature sin dato contribuye con su peso × 50, el valor neutro. No se redistribuye su peso entre las demás. La cobertura (peso con dato) reduce la confianza publicada.",
        why="Al renormalizar, una empresa con 2 meses de historia se puntuaba casi solo por su caja y salía más sana que la media (sesgo de arranque, grave para el test oculto de empresas nuevas). Además, el score saltaba cuando aparecía una feature. Con el neutro, lo que no sabemos tira al centro y la confianza lo refleja.",
        alternatives="Renormalizar (v5b): +9,4 % frente a AR(1) pero con sesgo de arranque y un 24 % de movimientos grandes. Neutro (v5e): +5,2 % frente a AR(1), sin sesgo y con un 15 % de movimientos grandes. Se prioriza la estabilidad y la justicia con las empresas nuevas.",
        evidence=f"Mediana del score bruto en el mes 0 frente al mes 11: renormalizando {by.renorm.iloc[0]:.1f} → {by.renorm.iloc[-1]:.1f}; con neutro {by.score_raw.iloc[0]:.1f} → {by.score_raw.iloc[-1]:.1f}.",
        chart=chart("line", "Mediana del score bruto según los meses de historia", "meses desde el alta", "score bruto", by.index.tolist(),
                    [ds("renormalizando pesos", by.renorm.values), ds("sin dato = neutro (final)", by.score_raw.values)]))

    comp_ = scorer._composite(f)
    act_ = f.months_since_last_tx.to_numpy() == 0
    qs = [5, 25, 50, 75, 95]
    add(category="score", title="Escala publicada: transformación lineal P5→15, P95→85",
        question="¿Cómo hacer legible el score (del estilo '82 → 68') sin perder la explicación exacta?",
        decision=f"Score publicado = a + b × compuesto, con a = {a_:.1f} y b = {b_:.2f}, calibrados en train para llevar el P5 del compuesto a 15 y el P95 a 85. Se recorta a [0, 100] y el recorte aparece como término explícito en la explicación.",
        why="La media ponderada de percentiles, con neutro para lo desconocido, concentra el score entre 38 y 68. Una transformación lineal abre el rango y mantiene la suma exacta de contribuciones, porque la constante se reparte según los pesos. Una transformación no lineal (percentil del compuesto) rompería la explicación.",
        evidence="Cuantiles del compuesto → publicado: " + ", ".join(f"P{q}: {np.percentile(comp_[act_], q):.1f} → {np.percentile(a_ + b_ * comp_[act_], q):.1f}" for q in qs),
        chart=chart("bar", "Cuantiles del compuesto y del score publicado", "cuantil", "valor", [f"P{q}" for q in qs],
                    [ds("compuesto (media de percentiles)", [np.percentile(comp_[act_], q) for q in qs]),
                     ds("publicado", [np.clip(np.percentile(a_ + b_ * comp_[act_], q), 0, 100) for q in qs])]))

    last = scored[scored.month == scored.month.max()].score
    hist, edges = np.histogram(last, bins=20, range=(0, 100))
    add(category="producto", title="Bandas sano/vigilar/riesgo (65/35) y reglas del monitor",
        question="¿Cuándo sale una alerta?",
        decision="Bandas: riesgo < 35 ≤ vigilar < 65 ≤ sano, aproximadamente los cuartiles de la escala publicada. Alerta de deterioro si la mediana prevista a 3 meses cae ≥ 10 puntos y el percentil 90 también está por debajo del nivel actual (el intervalo no cruza 0). Severidad alta si todavía parece sana (≥ 55). La mejora es simétrica. Bache frente a caída: tras una caída bruta ≥ 10 en el mes, es bache si la mediana prevista recupera al menos la mitad. Inactividad: alerta inmediata.",
        why="Usar el intervalo y no solo la mediana reduce las falsas alarmas: solo se alerta cuando el modelo está seguro de la dirección. Los umbrales de banda dejan unos tercios aproximados de la cartera y se pueden ajustar al apetito de riesgo del comprador.",
        evidence=f"Distribución del último mes: riesgo {np.mean(last < 35):.0%}, vigilar {np.mean((last >= 35) & (last < 65)):.0%}, sano {np.mean(last >= 65):.0%}.",
        chart=chart("bar", "Distribución del score en el último mes", "score", "empresas", [f"{int(e)}" for e in edges[:-1]], [ds("empresas", hist)],
                    note="Cortes en 35 y 65"))

    cq = ev_cqr(f)
    add(category="modelo", title="Regresión cuantílica (q10/q50/q90) con calibración conformal (CQR)",
        question="¿Cómo dar confianza a la previsión?",
        decision="LightGBM con objective = quantile para q10, q50 y q90 dentro de mlforecast. Después, CQR: se reentrena con train cortado H meses, se miden las puntuaciones de no-conformidad y se ensancha el intervalo por horizonte. q50 es la previsión puntual y los cuantiles se ordenan para que no se crucen.",
        why="Sin calibrar, el intervalo nominal del 80 % solo cubría alrededor del 60 %: LightGBM cuantílico es demasiado confiado. CQR da cobertura garantizada sin cambiar el modelo.",
        evidence="Cobertura del intervalo 80 % por horizonte (sin CQR → con CQR): " + ", ".join(f"h{h}: {cq[False][h]:.0%} → {cq[True][h]:.0%}" for h in cq[True].index),
        chart=chart("bar", "Cobertura del intervalo 80 % (objetivo 80 %)", "horizonte", "% de cobertura", [f"h{h}" for h in cq[True].index],
                    [ds("sin calibrar", cq[False].values * 100), ds("con CQR", cq[True].values * 100)]))

    old = ev_old_event_def(f)
    add(category="validación", title="Eventos definidos contra la base anual, no contra el trimestre actual",
        question="¿Por qué un margen alto 'predecía' deterioro?",
        decision="Declive = MEDIANA de los cobros de los 6 meses siguientes < 50 % de la mediana de los 12 anteriores: robusto a meses pico, no relativo al trimestre actual. Crecimiento = cobros medios > 130 % y caja al alza. Los pesos se calibran con 3 eventos adversos y 1 positivo, así el score también distingue a las empresas sólidas (dos caras).",
        why="Comparar con el trimestre actual convierte cualquier pico en una 'caída' futura: es regresión a la media disfrazada de evento y premiaba a las empresas mediocres.",
        evidence="AUC del margen 6m frente a caída (definición inicial → actual): " + f"{old['net_margin_6m'][0]:.2f} → {old['net_margin_6m'][1]:.2f}; tendencia de cobros: {old['growth_vs_12m'][0]:.2f} → {old['growth_vs_12m'][1]:.2f}",
        chart=chart("bar", "AUC frente a 'caída' según la definición del evento", "feature", "AUC", ["Margen 6m", "Tendencia de cobros"],
                    [ds("relativo al trimestre actual", [old["net_margin_6m"][0], old["growth_vs_12m"][0]]), ds("relativo a la media anual", [old["net_margin_6m"][1], old["growth_vs_12m"][1]])]))

    its = iterations()
    add(category="validación", title="Validación: GroupKFold por grupo × 3 cortes, frente a AR(1)",
        question="¿Cómo sabemos que generaliza y que no es regresión a la media?",
        decision="5 folds por group_id × cortes nov-25, feb-26 y may-26. El scorer se ajusta sin la empresa y el forecaster predice con new_df. La referencia principal es un AR(1) agrupado por horizonte, no el naive.",
        why="El review mostró que la ventaja de la v1 frente al naive era regresión a la media: un AR(1) la igualaba. Por eso toda mejora se mide contra el AR(1).",
        evidence="Skill frente a AR(1) a h3 por versión: " + ", ".join(f"{i['tag']}: {i['metrics'].get('skill_vs_ar1_h3', float('nan')):+.1%}" for i in its if i['metrics'].get('skill_vs_ar1_h3') is not None),
        chart=chart("bar", "Skill a 3 meses frente a AR(1) por iteración", "versión", "skill (1 − MAE/MAE_AR1)",
                    [i["tag"] for i in its if i["metrics"].get("skill_vs_ar1_h3") is not None],
                    [ds("skill vs AR(1)", [100 * i["metrics"]["skill_vs_ar1_h3"] for i in its if i["metrics"].get("skill_vs_ar1_h3") is not None])]))

    add(category="modelo", title=f"Forecaster final: {FINAL_DESC}",
        question="¿Cuántas exógenas y cuánta regularización?",
        decision=FINAL_WHY, why=FINAL_REASON, evidence=FINAL_EVIDENCE,
        chart=chart("bar", "Variantes del forecaster (MAE h1 / h3)", "variante", "MAE",
                    [v for v in VARIANTS if load_metrics(v)],
                    [ds("MAE h1", [load_metrics(v)["mae_h1"] for v in VARIANTS if load_metrics(v)]),
                     ds("MAE h3", [load_metrics(v)["mae_h3"] for v in VARIANTS if load_metrics(v)]),
                     ds("AR(1) h3", [load_metrics(v)["mae_ar1_h3"] for v in VARIANTS if load_metrics(v)])]))

    add(category="modelo", title="¿Por qué una logística para los pesos del score y no un modelo generativo (p.ej. TimeGPT-2)?",
        question="¿Por qué la regresión logística decide el score? ¿Podríamos usar un modelo generativo o fundacional?",
        decision="La logística NO es el score: solo calibra los pesos w_f de una suma lineal de percentiles, con w_f ≥ 0. El score sigue siendo aditivo, monótono y con explicación exacta. La previsión de trayectoria es donde un modelo fundacional de series temporales (TimeGPT-2 de Nixtla) sí encaja: como alternativa (challenger) del TrajectoryForecaster, en particular para empresas con historia corta (zero-shot). Queda pendiente de la API key y del permiso para enviar datos a un servicio externo (o de desplegarlo on-prem).",
        why="El enunciado exige que no sea una caja negra: 'para cualquier empresa hay que poder decir por qué saca ese número'. Un modelo generativo o una red dan mejor ajuste potencial, pero sus pesos no son explicables al jurado ni monótonos. La logística con signo restringido es la forma más simple de anclar los pesos a hechos observables sin perder la interpretabilidad. Si se quiere no linealidad manteniendo la explicación exacta, la alternativa natural es un GAM aditivo (Explainable Boosting Machine) con restricciones monótonas, no un modelo generativo.",
        alternatives="GAM/EBM monótono (no lineal y aditivo): candidato razonable para el siguiente paso. LightGBM + SHAP: explicación aproximada y no monótona. TimeGPT-2 como scorer: es un modelo de previsión, no de clasificación de salud; sirve para la trayectoria, no para los pesos.",
        status="a confirmar con la organización")

    add(category="producto", title="Formato de salida para el leaderboard",
        question="¿Qué formato pide el leaderboard?",
        decision="predict_submission.py genera un CSV por company_id y mes con: score, banda, confianza, q10/q50/q90 a 1-3 meses, tendencia y alerta. Todo sale de la API sklearn (fit sobre train, transform/predict sobre las empresas nuevas).",
        why="No sabemos el formato exacto. Un CSV largo por empresa y mes cubre nivel, trayectoria y anticipación, y es fácil de adaptar.",
        status="a confirmar con la organización")

    add(category="producto", title="Frontend: SPA + FastAPI en vez de Streamlit o Gradio",
        question="¿Streamlit, Gradio o SPA?",
        decision="Backend FastAPI con el modelo cargado en memoria (service.py) y una SPA de un solo HTML (Chart.js) con un contrato JSON explícito (app/API_CONTRACT.md).",
        why="El simulador de escenarios necesita recalcular al mover cada slider (con debounce) y superponer base frente a escenario. Una SPA con API es más fluida, se despliega en cualquier sitio y separa el modelo (reutilizable como producto: la API es lo que compraría Embat) de la demo.",
        alternatives="Streamlit: más rápido de montar, pero se re-ejecuta entero en cada interacción y queda acoplado a Python.")

    add(category="producto", title="Producto y comprador: capa de decisión de Embat para el CFO",
        question="¿Quién paga y por qué?",
        decision="Comprador e integrador: Embat. Usuario: CFO o equipo de tesorería. X-Ray ordena la cartera, explica qué cambió y propone la siguiente acción con un colchón dinámico. Banco, bróker o BaaS quedan como ejecutores opcionales cuando la recomendación requiere capital o licencia.",
        why="Embat ya ofrece previsión, alertas, riesgo y pagos. La aportación incremental de X-Ray es comparabilidad, explicación aditiva y priorización transversal: convertir el rastro que Embat ya tiene en una cola de decisiones, no duplicar el forecast.",
        status="a confirmar con la organización")
    return D, its


VARIANTS = ["v4a", "v4b", "v4c", "v5a", "v5b", "v5c", "v5d", "v5e", "v5f"]
FINAL_DESC = "pendiente"
FINAL_WHY = FINAL_REASON = FINAL_EVIDENCE = ""
DESCS = {
    "v1": "Score a priori (5 pilares) + mlforecast univariante",
    "v2": "v1 + pilares retardados 3m como exógenas",
    "v3a": "Score corregido (facturas, arranque, midrank)",
    "v3b": "v3a + exógenas",
    "v4a": "Panel v4 (FX, internas, pólizas) + pesos a priori, sin exógenas",
    "v4b": "v4 + pesos calibrados por evento, sin exógenas",
    "v4c": "v4b + 21 exógenas por horizonte",
    "v5a": "v4b + arrastre ERP + α=0,5 (sin exógenas)",
    "v5b": "v5a + 6 exógenas",
    "v5c": "v5a + 21 exógenas + regularización fuerte",
    "v5d": "v5a + 6 exógenas + regularización fuerte",
    "v5e": "v5b + sin dato = neutro (sin renormalizar)",
    "v5f": "v5e + escala publicada lineal (P5→15, P95→85) y alertas Δ≥10",
    "v6": "Inactividad causal, intragrupo fuera, FX en facturas, clientes perdidos, calibración 2 caras, EPS relativo",
    "v7": "Eventos v2: tensión, incumplimiento, caída estructural y expansión; probabilidades a 6 meses",
}


def iterations():
    out = []
    for tag in ["v1", "v2", "v3a", "v3b", *VARIANTS, "v6", "v7"]:
        m = load_metrics(tag)
        if not m:
            continue
        keep = {k: v for k, v in m.items() if not isinstance(v, dict)}
        out.append({"tag": tag, "description": DESCS.get(tag, ""), "metrics": keep})
    return out


def clean(o):
    """JSON válido para el navegador (sin NaN/inf) y decimales en formato es-ES en los textos."""
    import math, re
    if isinstance(o, dict):
        return {k: (clean_text(v) if k in TEXT_KEYS and isinstance(v, str) else clean(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(x) for x in o]
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return o


TEXT_KEYS = {"evidence", "why", "decision", "alternatives", "question", "title", "note"}


def clean_text(t: str) -> str:
    import re
    t = re.sub(r"(?<![\w.])(\d+)\.(\d+)(?![\w.])", r"\1,\2", t)  # 0.59 -> 0,59 (no toca v5b, 2026-08, ids)
    t = re.sub(r"(\d)%", r"\1 %", t)  # 3,0% -> 3,0 %
    return t


CURATED = [
    ("auc_deterioro", "AUC caída ≥15 a 3m (modelo)"), ("auc_deterioro_ar1", "AUC caída ≥15 a 3m (AR1)"),
    ("auc_deterioro_top_quintil", "AUC caída · aún sanas (quintil alto)"), ("auc_mejora", "AUC subida ≥15 a 3m (modelo)"),
    ("auc_mejora_ar1", "AUC subida ≥15 a 3m (AR1)"), ("auc_mejora_bottom_quintil", "AUC subida · desde abajo (quintil bajo)"),
    ("prec_top5_down", "Precisión 5 % más en riesgo"), ("prec_top5_up", "Precisión 5 % más en mejora"),
    ("mae_h1", "MAE a 1 mes"), ("mae_h3", "MAE a 3 meses"), ("mae_ar1_h3", "MAE a 3 meses (AR1)"),
    ("skill_vs_ar1_h3", "Skill vs AR1 a 3 meses"), ("coverage80_h3", "Cobertura intervalo 80 % (h3)"),
    ("auc_level_vs_adverse_6m", "AUC nivel vs evento adverso 6m"), ("auc_level_vs_positive_6m", "AUC nivel vs crecimiento 6m"),
    ("alert_down_precision", "Precisión alerta deterioro"), ("alert_up_precision", "Precisión alerta mejora"),
]
ITER_KEYS = ["mae_h1", "mae_h3", "mae_ar1_h3", "skill_vs_ar1_h3", "auc_deterioro", "auc_deterioro_ar1", "auc_mejora",
             "auc_mejora_ar1", "auc_deterioro_top_quintil", "coverage80_h3", "share_big_moves", "auc_level_vs_adverse_6m",
             "auc_level_vs_positive_6m", "prec_top5_down", "prec_top5_up"]
ANT_LABELS = {"lead_time_mediana_meses": "Antelación mediana (meses)", "share_alertadas_antes": "Caídas estructurales alertadas antes",
              "alert_deterioro_precision": "Precisión alerta deterioro (origen móvil)", "alert_mejora_precision": "Precisión alerta mejora (origen móvil)",
              "bache_vs_caida_accuracy": "Acierto bache vs caída", "alert_flicker_rate": "Alertas que parpadean"}


def write(D, its):
    D = clean(D)
    its = clean([{**i, "metrics": {k: i["metrics"].get(k) for k in ITER_KEYS}} for i in its])
    (REP / "decisions.json").write_text(json.dumps({"decisions": D}, ensure_ascii=False, indent=1, allow_nan=False))
    fm = load_metrics(FINAL) or {}
    ant = json.loads((REP / "anticipation_v5.json").read_text()) if (REP / "anticipation_v5.json").exists() else {}
    charts = []
    tags = [i["tag"] for i in its]
    charts.append(chart("bar", "MAE a 3 meses por iteración frente a AR(1)", "versión", "MAE h3", tags,
                        [ds("modelo", [i["metrics"].get("mae_h3") for i in its]), ds("AR(1)", [i["metrics"].get("mae_ar1_h3") for i in its])]))
    charts.append(chart("bar", "Validez externa del nivel: AUC frente a eventos a 6 meses", "versión", "AUC",
                        [i["tag"] for i in its if i["metrics"].get("auc_level_vs_adverse_6m")],
                        [ds(e, [i["metrics"].get(f"auc_level_vs_{e}") for i in its if i["metrics"].get("auc_level_vs_adverse_6m")])
                         for e in ["adverse_6m", "churn_6m", "cash_stress_6m", "decline_6m", "positive_6m"]]))
    if fm:
        charts.append(chart("bar", "Cobertura del intervalo 80 % por horizonte (modelo final)", "horizonte", "%", ["h1", "h2", "h3"],
                            [ds("cobertura", [100 * fm[f"coverage80_h{h}"] for h in (1, 2, 3)]), ds("objetivo", [80, 80, 80])]))
    if ant.get("lead_time_hist"):
        lh = ant["lead_time_hist"]
        charts.append(chart("bar", "Antelación de la primera alerta en caídas estructurales", "meses de antelación", "caídas", list(lh.keys()), [ds("caídas", list(lh.values()))]))
    final = {label: fm.get(k) for k, label in CURATED if fm.get(k) is not None}
    final.update({label: ant[k] for k, label in ANT_LABELS.items() if ant.get(k) is not None})
    payload = clean({"iterations": its, "final": final, "charts": charts})
    (REP / "metrics_app.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1, allow_nan=False))
    md = ["# Registro de decisiones\n", "Generado por `src/decisions.py`. Las gráficas están en la SPA, pestaña «Decisiones».\n"]
    for d in D:
        md.append(f"\n## {d['id']} · {d['title']}\n\n*Categoría:* {d['category']} · *Estado:* {d['status']}\n\n"
                  f"**Pregunta.** {d['question']}\n\n**Decisión.** {d['decision']}\n\n**Por qué.** {d['why']}\n")
        if d.get("alternatives"):
            md.append(f"\n**Alternativas descartadas.** {d['alternatives']}\n")
        if d.get("evidence"):
            md.append(f"\n**Evidencia.** {d['evidence']}\n")
    (ROOT / "DECISIONS.md").write_text("".join(md))


if __name__ == "__main__":
    import sys
    cfg = json.loads((REP / "final_choice.json").read_text()) if (REP / "final_choice.json").exists() else {}
    FINAL_DESC = cfg.get("desc", FINAL_DESC); FINAL_WHY = cfg.get("decision", ""); FINAL_REASON = cfg.get("why", ""); FINAL_EVIDENCE = cfg.get("evidence", "")
    D, its = build()
    write(D, its)
    print(len(D), "decisiones;", len(its), "iteraciones")
