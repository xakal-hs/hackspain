"""Tests de la API sklearn y de robustez OOD (empresas nunca vistas, escalas extremas, datos ausentes).

    cd research && uv run pytest -q
"""
import sys, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import polars as pl
import pytest
from sklearn.base import clone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from features import add_features  # noqa: E402
from targets import add_events  # noqa: E402
from xray import HealthScorer, TrajectoryForecaster, SPEC, explain, alerts_for  # noqa: E402
from service import apply_scenario  # noqa: E402
import evaluate as E  # noqa: E402

MONEY = ["inflow", "outflow", "oper_in", "transfer_in", "payroll", "tax", "debt_service", "fees", "refunds",
         "foreign_flow", "gross_flow", "internal_flow", "cash_end", "lc_drawn", "lc_limit", "overdue_ar", "overdue_ap",
         "overdue_90_ar", "overdue_90_ap", "ar_issued", "ap_issued"]


@pytest.fixture(scope="module")
def raw():
    return pl.read_parquet(ROOT / "data/panel.parquet")


@pytest.fixture(scope="module")
def panel(raw):
    return add_events(add_features(raw)).to_pandas()


@pytest.fixture(scope="module")
def scorer(panel):
    obs = panel.month <= panel.month.max() - pd.DateOffset(months=6)
    return HealthScorer().fit(panel, panel[E.EVENTS].where(obs, axis=0))


def _company(raw, cid):
    return raw.filter(pl.col("company_id") == cid)


def test_sklearn_api(scorer):
    c = clone(scorer)
    assert c.get_params() == scorer.get_params()
    with pytest.raises(Exception):
        c.transform(pd.DataFrame({"runway": [1.0]}))  # NotFittedError
    assert abs(sum(scorer.weights_.values()) - 1) < 1e-9
    assert all(w >= 0 for w in scorer.weights_.values())


def test_scale_invariance(raw, scorer):
    """Una empresa ×1e6 (otra moneda o tamaño nunca visto) tiene el mismo score: todo son ratios."""
    cid = raw["company_id"].unique().sort()[10]
    base = _company(raw, cid)
    s1 = scorer.score_panel(add_features(base).to_pandas()).score.to_numpy()
    for k in (1e-6, 1e-3, 1e3, 1e6):  # suelo EPS relativo a la escala de la empresa (D16)
        big = base.with_columns([pl.col(c) * k for c in MONEY if c in base.columns])
        s2 = scorer.score_panel(add_features(big).to_pandas()).score.to_numpy()
        assert np.allclose(s1, s2, atol=1.0), k


def test_all_missing_and_missing_columns(scorer):
    X = pd.DataFrame({"company_id": ["X"] * 3, "group_id": ["G"] * 3,
                      "month": pd.date_range("2026-01-01", periods=3, freq="MS")})
    out = scorer.score_panel(X)  # sin ninguna feature: no falla, punto neutro de la escala y confianza 0
    a, b = scorer.scale_
    assert np.allclose(out.score, a + b * 50) and (out.confidence == 0).all()


def test_extreme_values_saturate(scorer):
    X = pd.DataFrame({f: [1e12, -1e12, np.inf, np.nan] for f in SPEC})
    t = scorer.transform(X)
    assert t.score_raw.between(0, 100).all()
    assert (t.ood_share.iloc[:2] > 0.5).all()  # detecta valores fuera de rango


def test_explanation_is_exact(raw, scorer):
    cid = raw["company_id"].unique().sort()[20]
    f = add_features(_company(raw, cid)).to_pandas()
    s = scorer.score_panel(f)
    ec = s[[c for c in s.columns if c.startswith("ec_")]].sum(1)
    assert np.allclose(ec, s.score, atol=1e-9)
    e = explain(s, f, cid)
    if e["prev_month"]:
        assert abs(sum(c["delta_points"] for c in e["contributions"]) - e["delta"]) < 0.2  # redondeo a 2 decimales


def test_two_notes_calibrate_on_their_own_events(panel, scorer, raw):
    """D32: la nota adversa calibra con E1-E3 y la de expansión con E4; ambas con explicación aditiva exacta."""
    assert set(scorer.calibration_) == {"tension_6m", "incumplimiento_6m", "caida_6m"}
    obs = panel.month <= panel.month.max() - pd.DateOffset(months=6)
    exp = HealthScorer(target="expansion").fit(panel, panel[E.EVENTS].where(obs, axis=0))
    assert set(exp.calibration_) == {"expansion_6m"}
    assert exp.weights_["runway"] < scorer.weights_["runway"]  # la caja manda en la adversa, no en la expansión
    f = add_features(_company(raw, raw["company_id"].unique().sort()[20])).to_pandas()
    s = exp.score_panel(f)
    assert np.allclose(s[[c for c in s.columns if c.startswith("ec_")]].sum(1), s.score, atol=1e-9)


def test_liquidity_band_rule(panel, scorer):
    """D35: con menos de medio mes de caja propia la nota publicada no es «sano», y la regla es una contribución aditiva."""
    from xray import LIQ_RULE_CAP, LIQ_RULE_MONTHS
    s = scorer.score_panel(panel)
    short = panel.sort_values(["company_id", "month"]).reset_index(drop=True)["runway"] < np.log1p(LIQ_RULE_MONTHS)
    assert (s.score[short.to_numpy()] <= LIQ_RULE_CAP + 1e-9).all()
    assert (s.ec_regla_liquidez[~short.fillna(False).to_numpy()] == 0).all()
    assert np.allclose(s[[c for c in s.columns if c.startswith("ec_")]].sum(1), s.score, atol=1e-9)


def test_monotonicity(scorer):
    """Mejorar una señal nunca baja el score (pesos ≥ 0 y dirección económica)."""
    base = pd.DataFrame({f: [np.nanmedian(scorer.ref_[f])] for f in scorer.features_})
    s0 = scorer.transform(base).score_raw.iloc[0]
    for f, (_, d, *_r) in SPEC.items():
        if f not in scorer.features_:
            continue
        up = base.copy(); up[f] = up[f] * 3 + 1 if d > 0 else up[f] / 3
        assert scorer.transform(up).score_raw.iloc[0] >= s0 - 1e-9, f


def test_short_history_fallback(panel, scorer):
    s = E.build_series(scorer.score_panel(panel), panel)
    fc = TrajectoryForecaster(exog=tuple(E.EXOG), conformal=False).fit(s[s.ds <= "2026-02-01"][["unique_id", "ds", "y", *E.EXOG]])
    ids = s.unique_id.unique()[:3]
    short = s[s.unique_id.isin(ids)].groupby("unique_id").head(2)  # 2 meses de historia
    p = fc.predict(short[["unique_id", "ds", "y", *E.EXOG]])
    assert p.fallback.all() and len(p) == 3 * 3
    assert (p.q10 <= p.q50).all() and (p.q50 <= p.q90).all()
    assert p[["q10", "q50", "q90"]].stack().between(0, 100).all()


def test_scenario_directions(raw, scorer):
    cid = raw["company_id"].unique().sort()[30]
    base = _company(raw, cid).to_pandas()
    s0 = scorer.score_panel(add_features(pl.from_pandas(base)).to_pandas()).score.iloc[-1]
    worse = apply_scenario(base, 3, {"inflow": 0.5, "late_share_ap": 0.4})
    better = apply_scenario(base, 3, {"cash_end": 2.0})
    s_w = scorer.score_panel(add_features(pl.from_pandas(worse)).to_pandas()).score.iloc[-1]
    s_b = scorer.score_panel(add_features(pl.from_pandas(better)).to_pandas()).score.iloc[-1]
    assert s_w <= s0 + 1e-6 and s_b >= s0 - 1e-6


def test_alert_rules():
    a = alerts_for(70, {"q10": 50, "q50": 58, "q90": 66}, None, False)
    assert [x["type"] for x in a] == ["deterioro"] and a[0]["severity"] == "alta"
    assert alerts_for(50, {"q10": 45, "q50": 51, "q90": 58}, None, False) == []
    b = alerts_for(55, {"q10": 50, "q50": 62, "q90": 70}, -12, False)
    assert any(x["type"] == "bache" for x in b)
