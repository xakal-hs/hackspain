## Learned User Preferences
- For data-analysis deliverables, produce the complete end-to-end result as a self-contained HTML artifact that opens directly without a server.
- Interpret fields according to their domain meaning and include substantive exploratory coverage such as distributions, temporal patterns, correlations, and outliers.

## Learned Workspace Facts
- The repository remote is `https://github.com/xakal-hs/hackspain`, with `main` as the default branch.
- Hackathon datasets and their data dictionary live under `data/`; `data/invoices.csv` and `data/transactions.csv` are tracked with Git LFS.
- The reproducible exploratory report consists of `analysis/generate_report.py` and the generated self-contained artifact `analysis/report.html`.

## Project Context

This repository contains the HackSpain 2026 **X Ray** challenge from Embat. The canonical challenge brief is available in `context/challenge.md` and `context/challenge.html`.

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

Operational frame: [`context/scoring.md`](context/scoring.md) (readable page: [`context/scoring.html`](context/scoring.html)).

- Design the score as a lender with €100,000 to place. Start from consumer credit questions, then map them onto company cash, invoices and debt. The nature of the risk is the same; the data type is not.
- **Criticality is not uniform.** Cash available that evaporates quickly must move the score far more than a mild shift in collection days (DSO) or payment days (DPO). Do not give every feature the same weight.
- Translate jargon into consumer language in every explanation: available cash is “the money left in the account”; DSO is “how long they take to get paid”; DPO is “how long they take to pay”.
- The deliverable is not only a number for ranking A against B. For each company and month, expose level, trajectory, signal criticality, a plain-language why, dip vs structural drop, and a lender action (lend / watch / do not lend).
- Observability gaps (missing ERP, truncated month, uncategorized flows) are coverage, not health.

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
- `balances.csv` is only the final snapshot. Reconstruct historical balances backward from transactions, by product and currency.
- Amounts are multi-currency. Do not aggregate them globally without a justified conversion.
- IDs are categorical keys, never continuous numerical features.
- Consult `data/data_dictionary.md` before assigning meaning to a field.
- Treat ERP, connection age, missingness, and reconciliation coverage as observability signals, not automatically as financial health.

## Open Questions

- Confirm whether leaderboard scoring is at `company_id` or `group_id` level.
- Confirm the required prediction file format and submission mechanism.
- Confirm whether labels exist outside the provided files or whether the score must be unsupervised.
