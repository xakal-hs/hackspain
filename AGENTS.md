## Learned User Preferences
- For data-analysis deliverables, produce the complete end-to-end result as a self-contained HTML artifact that opens directly without a server.
- Interpret fields according to their domain meaning and include substantive exploratory coverage such as distributions, temporal patterns, correlations, and outliers.
- Do not rewrite the raw CSVs in `data/`; correct known dirt through a mapping layer instead.
- After completing a deliverable, open a pull request and merge it into `main`.
- Preferred models for subagent workflows: GPT-5.6 Sol, Claude Opus 5, GLM-5.3, and DeepSeek V4.1 Flash for quick work. Do not route quality-sensitive work to Claude Sonnet 5 — go to Opus 5 instead. Custom subagent profiles live in `.devin/agents/` (`researcher`, `implementer`, `reviewer`, `prototyper`, and the council roles `prestamista`, `cfo`, `auditor-datos`, `riesgo-modelo`, `abogado-diablo`, `cobrador`, `consolidador`).
- The score must be designed bottom-up from the lender's view, with the model explaining why it classified a rating (Y, Z, K), and improved through a measurable test→diagnose→change loop rather than LGBM prediction.
- Size and rank financial products by client impact first, then Embat take within that impact, then the right to create or intermediate the rail. Embat is not a bank today; a partner with an existing banking license is enough to move money. Separate measured bases from assumed bps and adoption; if the repo has no published take, the take is 0, not a fabricated commission.

## Learned Workspace Facts
- `context/`, `notebooks/`, `research/`, `analysis/` and `docs/` are encrypted in `vault/*.enc` and gitignored as working copies. Decrypt them before reading, editing or running anything in those trees: copy `.env.example` to `.env`, set `DECRYPT_KEY`, then `python3 scripts/vault.py decrypt`. After changing those folders, `python3 scripts/vault.py encrypt` refreshes the packs. The key never goes in git.
- The repository remote is `https://github.com/xakal-hs/hackspain`, with `main` as the default branch.
- Hackathon datasets and their data dictionary live under `data/`; `data/invoices.csv` and `data/transactions.csv` are tracked with Git LFS.
- The reproducible exploratory report consists of `analysis/generate_report.py` and the generated self-contained artifact `analysis/report.html`.
- Historical cash is reconstructed in `analysis/cash_history.py` (formula, sentinel handling, cent rounding, drift flags) and explored in `analysis/app.py`. Persist with `scripts/build_cash_db.py`; do not commit `analysis/cash.duckdb`.
- Categorical and referential dirt is inventoried in `src/mapping/ISSUES.md` and corrected at read time by DuckDB views in `src/mapping/` (`attach` / `connect`); raw rows stay in `*_raw` views.
- Score-model experiments, the research API, and the research demo SPA live under `research/`. The jury-facing product UI is the Nuxt app in `frontend/` (`pnpm dev` → http://localhost:3000); it runs on fixtures without `backend/data/panel.parquet`.
- The a-priori weight catalogue of `docs/explicacion_pesos.md` (42 variables, 7 scoring pillars) was measured against the backend's 17 calibrated features in `backend/experiments/` (`catalogo.py`, `medir.py`, `informe_html.py` → `pesos_2x2.html`); arms A-G plus `Aexp`/`Gexp`, all through `metrics.oof`. Verdict: the doc's weights drop the liquidity anchor from 0,848 to 0,719 AUC (−9,7 σ paired) and anticipation −4,8 σ, because allocating 24 % across six liquidity variables caps each at 4,8 % where calibration puts 27 % on `runway` alone; PM misses it entirely (0,6285 → 0,6303). Only `tax_miss` and `payroll_continuity_6m` survive (arm G: anchor unchanged, impago IVA +5,9 σ, alert coverage 18,6 % → 22,6 %, expansion −0,015 on its own score). Nothing was adopted into the backend yet. `salida/oof_*.parquet` is not versioned.
- The autoresearch workflow lives in `.devin/workflows/autoresearch/` and is **data-lead**: every hypothesis cites a data fact. fase0 (datos: auditoría + análisis exploratorio + limpieza discutida en el consejo → `salida/auditoria_datos.md`, `salida/analisis_datos.md`, `salida/hechos_datos.jsonl`, `salida/datos_limpieza.md`), fase1 (política de préstamo, cada criterio apoyado en un hecho), fase2 (consejo → `salida/premisas.jsonl`, cada premisa con `evidencia`), fase3 (bucle sobre `premisas.py`), fase4 (sala de situaciones en la SPA + demo proactiva de factoring/refi con proyección de tesorería aritmética), fase5 (`salida/documento_score.md`, cuestionado por subagentes). Orden canónico 0→1→2→3→4→5, lanzable con `run.sh cadena`. `premisas.py` (`build`/`validate`/`run`/`export`) evalúa premisas contra `research/data/panel.parquet` + `features.py` + `targets.py` + the score (`score`, `score_oof`, `band`, `prob_*`, `ec_*`, `dec_*`), and exports `salida/situaciones.json` for the UI; `premisas.seed.jsonl` es la semilla. `puntuacion.py` reduce un `metrics_<tag>.json` a la métrica única **PM** (media del AUC del nivel frente a E1-E4); `score_datos.py` vuelca los números reales del artefacto (pesos, escala, los 17 coeficientes por evento, probabilidades) y `documento_medidas.py` los hechos del panel puntuado que cita `salida/documento_score.md` (compuesto, cobertura, reglas, bandas, sesgos, ejemplo trabajado → `salida/documento_medidas.json`); la edición anterior del documento queda en `salida/documento_score_r1.md` y los informes del consejo de fase 5 en `salida/consejo/f5_*.md` (ronda 1) y `f5r2_*.md` (ronda 2); `auditoria_datos.py` cuantifica las anomalías de los parquet crudos; `analisis_datos.py` produce la base de evidencia data-lead. `salida/` no se versiona. The repo-restructuring workflow is in `.devin/workflows/reestructura/`.
- The visual language of the demo SPA is defined in `research/app/DESIGN.md`; follow it when touching `research/app/static/index.html`.
- Fase 4 lives in `research/src/proactive.py` (`ProactiveEngine.project/decide/recommend`, `validate`): the cash projection is arithmetic (caja + facturas emitidas/recibidas pendientes **no vencidas** − nóminas − cuotas), never the LGBM forecaster; the decision uses the fase-1 tension threshold (0,25 meses de gasto) because cash < 0 is too rare (≈1 %) to anticipate. Served at `/api/proactive`, `/api/proactive/validation`, `/api/situaciones`; SPA tabs `#/proactivo/{cid}/{month}` and `#/situaciones/{id}`. `salida/demo/` (validation JSON/parquet, `guion.md`) is regenerated with `uv run python src/proactive.py validate` and is not versioned. Held-out validation (fold 0 by `group_id`): among companies healthy today, tension at 2 months is anticipated with precision 0,30 (base 0,09) and 0,59 when invoices cover 40-100 % of bank flows; the "completa" variant with non-invoiced bank flows measured worse and stays as reference only.
- Qualitative product voice from an Embat PM (19 Sep 2026) lives in `context/voz_embat.md` (readable page: `context/voz_embat.html`). Idle cash and FX are hidden costs to show in the app; the agent is unused; subscription is the preferred model and intermediation is a fallback; liquidity criticality is sector-dependent; upsell is a table of fitting options; debt is a short/medium/long mix matched to repayment time.
- Qualitative credit voice from a Capchase co-founder (19 Sep 2026) lives in `context/voz_capchase.md` (readable page: `context/voz_capchase.html`). Moving client money does not require Embat's own banking license — partner with a licensed bank; loan products sit on a sector × tenor grid (days / 6m / 12m / longer); retain the client; cash-rich firms still borrow — park deposits at the partner as collateral to cut the rate.
- Product opportunity sizing lives in `analysis/productos.py` → `analysis/productos.html` (notebook `notebooks/02_productos.ipynb`); the placement frame is `context/oportunidades.md`. Inferred sectors live in `data/processed/empresa_sector.csv` (`tipo`, `tenor`, `product_fit`); regenerate the map with `analysis/cluster_sector.py` → `analysis/cluster_sector.html`, and both CSVs plus `analysis/rentabilidad_sector.html` in one run of `analysis/rentabilidad_sector.py`. Net surplus and holes by `group_id` first — sister companies with both transfer cash internally before any SPA SKU — then yield, FX, factoring, residual insurance, reserve. Stickiness is months of need, not LTV; sector is a conservative TAM filter. Uncapped reserve and insurance takes are generator-tail artifacts, not P&L.

## Project Context

This repository contains the HackSpain 2026 **X Ray** challenge from Embat. The canonical challenge brief is available in `context/challenge.md` and `context/challenge.html`.

**Objectives (source of truth).** The goals, the six questions and the delivery requirements live in [`context/challenge.html`](context/challenge.html) (readable version: [`context/challenge.md`](context/challenge.md)). `context/scoring.md` is the team's operational interpretation of that brief. A feature is only relevant if it serves one of those six questions; the challenge-aligned computation and its AUC evidence are in `analysis/challenge_features.py` → `analysis/features_challenge.html`.

The system must:

1. Produce a financial-health score for every company and month.
2. Capture trajectory, not only the latest snapshot.
3. Detect improvement and deterioration symmetrically.
4. Separate temporary cash-flow shocks from structural changes.
5. Explain which signals changed and when.
6. Measure how many months in advance a meaningful change was detected.
7. Power a sellable product with a clearly identified buyer.

The most obvious buyer is Embat or the company contributing its own treasury data. A simple, interpretable score with a convincing product is preferable to a sophisticated model without a useful product.

## Scoring Philosophy

Operational frame: [`context/scoring.md`](context/scoring.md) (readable page: [`context/scoring.html`](context/scoring.html)). The CFO product row — what is sold and what it is worth on this portfolio — is in [`context/monetizacion.md`](context/monetizacion.md) (readable page: [`context/monetizacion.html`](context/monetizacion.html)). Product placement (cushion / excess / hole, group pooling, yield vs factoring vs FX) is in [`context/oportunidades.md`](context/oportunidades.md). Qualitative voice from Embat product is in [`context/voz_embat.md`](context/voz_embat.md). Qualitative credit voice (partner license, sector × tenor, retention, deposits as collateral) is in [`context/voz_capchase.md`](context/voz_capchase.md).

- Design the score as a lender with €100,000 to place. Start from consumer credit questions, then map them onto company cash, invoices and debt. The nature of the risk is the same; the data type is not.
- **Criticality is not uniform.** Cash available that evaporates quickly must move the score far more than a mild shift in collection days (DSO) or payment days (DPO). Do not give every feature the same weight. Liquidity criticality is also sector-dependent: some firms die without cash; others barely watch it. Do not treat a global runway threshold as universal.
- Translate jargon into consumer language in every explanation: available cash is “the money left in the account”; DSO is “how long they take to get paid”; DPO is “how long they take to pay”.
- The deliverable is not only a number for ranking A against B. For each company and month, expose level, trajectory, signal criticality, a plain-language why, dip vs structural drop, a lender action (lend / watch / do not lend), and the **cost of doing nothing** (idle cash, unconverted FX). Those costs are hidden: show them in the app; do not rely on the agent.
- Observability gaps (missing ERP, truncated month, uncategorized flows) are coverage, not health. Solvency does not wait for perfect reconciliation: it comes from planning and forecasts.
- Embat’s wedge versus banks is treasury data banks do not have (live cash, ERP invoices, reconciliation, connected debt). Pitch banks hard; do not treat the annual rating as the competitor.
- Do not ship one universal metric. The score, weights and decision change with the product being sold (working-capital line, policy, marketplace, agent) and with the viewer (bank, insurer, CFO, Embat), because their objectives differ.
- Upsell is a table of fitting options, not a single SKU ranked by commission. Debt, when offered, is a sector × tenor grid (days / 6 months / 12 months / longer), not one generic line. New debt with ample cash is capital structure, not automatically a hole; the distress case is new debt while cash evaporates. The module sells as a subscription; a partner bank's license is enough to move money — Embat does not need its own. Park surplus at that partner as collateral to cut the rate and keep the client.

## Delivery Requirements

- Score the hidden test set of 60–80 unseen companies.
- Validate with splits that keep complete business groups apart; otherwise related entities can leak across train and validation.
- Include a navigable demo that can be opened in front of the jury.
- Explain each score and its month-over-month movement.
- Identify who pays for the product and why.
- Bonus: quantify anticipation and provide proactive monitoring.

The jury evaluates three equally weighted dimensions:

- **Accuracy:** generalization, trajectory, and detection in both directions.
- **Timing:** anticipation, stability against temporary shocks, and monitoring.
- **Value:** product, buyer, explanation, craftsmanship, and demo quality.

## Dataset Semantics

The synthetic dataset contains 1,286 companies in 250 business groups and covers September 2024 through September 2026.

- `company_id` joins company-level files; `group_id` captures related legal entities.
- `balances.csv` is only the final snapshot. Reconstruct historical balances backward from transactions, by product and currency. Round reconstructed amounts to cents: otherwise accounts that return to zero land at ±1e-13 and flip the sign of `caja negativa` between runs.
- Cash means liquid accounts (`checking`, `saving`, `wallet`). Sentinel balances/transactions above €100M are generator artifacts, not SME cash. **Measure the threshold after converting to EUR**: in raw currency 478 of the 491 transactions above 1e8 are AOA/COP/VND/CLP amounts (COMP_0900: 3.1e9 AOA ≈ €2.9M); only 13 transactions (7 companies) and 4 cash balances (COMP_0420, COMP_0604, COMP_1068) are real sentinels. Loans above €100M (COMP_0630) are plausible debt, not cash.
- `research/data/panel.parquet` carries data-quality flags that no score feature consumes yet (`dq_cash_sentinel`, `has_drift`, `dq_cash_implausible`, `dq_edge_month`, `intragroup_share_3m`, `ar_id_coverage`, `n_sentinel_tx`); the council's verdict per anomaly is in `.devin/workflows/autoresearch/salida/datos_limpieza.md`. `months_since_last_tx` counts a one-month gap as 1 (an off-by-one labelled it 2 before).
- Series whose back-cast requires more than one month of payments in overdraft are incomplete (`has_drift`); exclude them from cohort and group aggregates.
- Country free-text is already canonized to ISO-2 by `src/mapping/`; 82% of companies still have no country.
- Amounts are multi-currency. Do not aggregate them globally without a justified conversion.
- IDs are categorical keys, never continuous numerical features.
- Consult `data/data_dictionary.md` before assigning meaning to a field.
- Treat ERP, connection age, missingness, and reconciliation coverage as observability signals, not automatically as financial health.

## Open Questions

- Confirm whether leaderboard scoring is at `company_id` or `group_id` level.
- Confirm the required prediction file format and submission mechanism.
- Confirm whether labels exist outside the provided files or whether the score must be unsupervised.
