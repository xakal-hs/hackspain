"""EDA: temporalidad, distribuciones, outliers, correlaciones. Salida en reports/."""
from pathlib import Path
import numpy as np, polars as pl, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from features import add_features, FEATURES

R = Path(__file__).resolve().parents[1] / "reports"; (R / "fig").mkdir(parents=True, exist_ok=True)
p = add_features(pl.read_parquet(Path(__file__).resolve().parents[1] / "data/panel.parquet"))
out = []

# 1. Historia disponible por empresa
hist = p.group_by("company_id").agg(pl.len().alias("n_months"))
out.append("## Historia por empresa (meses)\n" + str(hist["n_months"].describe()))
out.append(f"Empresas con <6 meses: {(hist['n_months']<6).sum()} · <12: {(hist['n_months']<12).sum()}")

# 2. Temporalidad: índice estacional de entradas (mediana de inflow/mean_company por mes del año)
s = p.with_columns(rel=pl.col("inflow") / (pl.col("inflow").mean().over("company_id") + 1),
                   moy=pl.col("month").dt.month())
seas = s.group_by("moy").agg(pl.col("rel").median().alias("inflow_rel_med"),
                             (pl.col("tax") / (pl.col("outflow") + 1)).median().alias("tax_share_med")).sort("moy")
out.append("## Estacionalidad (inflow relativo a la media de la empresa, mediana)\n" + str(seas))
fig, ax = plt.subplots(1, 2, figsize=(11, 3.5))
ax[0].bar(seas["moy"], seas["inflow_rel_med"]); ax[0].set_title("Entradas relativas por mes del año")
agg = p.group_by("month").agg(pl.col("company_id").n_unique().alias("n")).sort("month")
ax[1].plot(agg["month"], agg["n"]); ax[1].set_title("Empresas activas por mes (panel desbalanceado)")
fig.tight_layout(); fig.savefig(R / "fig/temporalidad.png", dpi=110)

# 3. Distribuciones y outliers de features
desc = p.select(FEATURES).describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99])
out.append("## Distribución de features\n" + str(desc))
nulls = p.select([pl.col(c).is_null().mean().alias(c) for c in FEATURES])
out.append("## Tasa de nulos\n" + str(nulls.transpose(include_header=True)))
fig, axs = plt.subplots(3, 5, figsize=(16, 8))
for a, c in zip(axs.ravel(), FEATURES):
    v = p[c].drop_nulls().to_numpy(); a.hist(v, bins=50); a.set_title(c, fontsize=9)
fig.tight_layout(); fig.savefig(R / "fig/distribuciones.png", dpi=100)
# outliers crudos (escala): colas del tamaño en unidades locales
raw = p.select(pl.col("inflow").log1p().alias("log_inflow"), pl.col("cash_end").sign().alias("cash_sign"))
out.append("## Escala (log inflow mensual)\n" + str(raw["log_inflow"].describe(percentiles=[0.01, 0.5, 0.99])))
out.append(f"Meses con caja reconstruida negativa: {(p['cash_end']<0).mean():.3f}; null caja: {p['cash_end'].is_null().mean():.3f}")
out.append(f"Meses con inflow=0 (actividad esporádica): {(p['inflow']==0).mean():.3f}")
tax_months = p.filter(pl.col("tax") > 0).group_by("company_id").agg(pl.len().alias("m"))
out.append("## Eventos ocasionales: meses con pago de impuestos por empresa\n" + str(tax_months["m"].describe()))
debt_months = p.filter(pl.col("debt_service") > 0)["company_id"].n_unique()
out.append(f"Empresas con servicio de deuda algún mes: {debt_months}")

# 4. Correlaciones (Spearman) entre features
X = p.select(FEATURES).to_pandas()
corr = X.corr(method="spearman")
fig, a = plt.subplots(figsize=(8, 7)); im = a.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
a.set_xticks(range(len(FEATURES)), FEATURES, rotation=90, fontsize=7); a.set_yticks(range(len(FEATURES)), FEATURES, fontsize=7)
fig.colorbar(im); fig.tight_layout(); fig.savefig(R / "fig/correlaciones.png", dpi=110)
pairs = corr.where(np.triu(np.ones(corr.shape), 1).astype(bool)).stack().sort_values(key=abs, ascending=False)
out.append("## Top correlaciones Spearman\n" + pairs.head(12).to_string())

# 5. Autocorrelación mes a mes (persistencia) de cada feature
ac = {c: p.select(pl.corr(pl.col(c), pl.col(c).shift(1).over("company_id", order_by="month"), method="spearman")).item() for c in FEATURES}
out.append("## Persistencia (Spearman lag-1)\n" + "\n".join(f"{k}: {v:.2f}" for k, v in ac.items()))

(R / "eda.md").write_text("# EDA X-Ray\n\n" + "\n\n".join(f"```\n{o}\n```" if not o.startswith("#") else o.split("\n",1)[0]+"\n```\n"+o.split("\n",1)[1]+"\n```" for o in out))
print("\n\n".join(out))
