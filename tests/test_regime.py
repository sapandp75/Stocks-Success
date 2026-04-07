import pandas as pd

from backend.services import regime_checker
from backend.services.regime_checker import calculate_market_breadth, calculate_vix_tax, classify_direction, determine_regime


def _reset_breadth_cache():
    regime_checker._breadth_cache = None
    regime_checker._breadth_cache_time = 0


def test_classify_full_uptrend():
    d = classify_direction(500, 495, 490, 470)
    assert d == "FULL_UPTREND"


def test_classify_full_downtrend():
    d = classify_direction(400, 420, 440, 470)
    assert d == "FULL_DOWNTREND"


def test_determine_regime_deploy():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=15.0)
    assert result["verdict"] == "DEPLOY"
    assert result["max_new_positions"] == 5


def test_determine_regime_cash_on_downtrend():
    spy = {"direction": "FULL_DOWNTREND"}
    qqq = {"direction": "FULL_DOWNTREND"}
    result = determine_regime(spy, qqq, vix=30.0)
    assert result["verdict"] == "CASH"
    assert result["max_new_positions"] == 0


def test_determine_regime_vix_override():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=36.0)
    assert result["verdict"] == "CASH"


def test_determine_regime_breadth_can_downgrade():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "TREND_WEAKENING"}
    breadth = {"breadth_signal": "POOR", "confidence": "HIGH"}
    result = determine_regime(spy, qqq, vix=15.0, breadth=breadth)
    assert result["verdict"] == "CAUTIOUS"
    assert result["breadth_adjustment"] == -1.0


def test_determine_regime_low_confidence_breadth_does_not_change_score():
    spy = {"direction": "PULLBACK_IN_UPTREND"}
    qqq = {"direction": "PULLBACK_IN_UPTREND"}
    breadth = {"breadth_signal": "POOR", "confidence": "LOW"}
    result = determine_regime(spy, qqq, vix=20.0, breadth=breadth)
    assert result["verdict"] == "DEPLOY"
    assert result["breadth_adjustment"] == 0


def test_calculate_market_breadth_returns_structured_payload(monkeypatch):
    _reset_breadth_cache()

    tickers = ["AAA", "BBB", "CCC"]
    index = pd.date_range("2025-01-01", periods=220, freq="D")
    close = pd.DataFrame(
        {
            "AAA": list(range(1, 221)),
            "BBB": list(range(220, 0, -1)),
            "CCC": [100] * 220,
        },
        index=index,
    )
    frame = pd.concat({"Close": close}, axis=1)

    monkeypatch.setattr("backend.services.sp500.get_sp500_tickers", lambda: tickers)
    monkeypatch.setattr(regime_checker.yf, "download", lambda *args, **kwargs: frame)

    breadth = calculate_market_breadth()
    assert breadth["method"] == "full_universe"
    assert breadth["confidence"] == "HIGH"
    assert breadth["sample_size"] == 3
    assert breadth["coverage_pct"] == 100.0
    assert breadth["pct_above_200d"] == 33.3
    assert breadth["pct_above_50d"] == 33.3
    assert breadth["pct_above_20d"] == 33.3
    assert breadth["breadth_signal"] == "WEAKENING"


def test_calculate_market_breadth_uses_stale_cache_on_failure(monkeypatch):
    regime_checker._breadth_cache = {
        "as_of": "2026-04-06",
        "method": "full_universe",
        "universe_size": 2,
        "sample_size": 2,
        "coverage_pct": 100.0,
        "pct_above_200d": 50.0,
        "pct_above_50d": 50.0,
        "pct_above_20d": 50.0,
        "breadth_signal": "HEALTHY",
        "confidence": "HIGH",
        "notes": [],
    }
    regime_checker._breadth_cache_time = regime_checker.time.time() - 4000

    monkeypatch.setattr("backend.services.sp500.get_sp500_tickers", lambda: ["AAA", "BBB"])
    monkeypatch.setattr(regime_checker.yf, "download", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    breadth = calculate_market_breadth()
    assert breadth["method"] == "stale_cache"
    assert breadth["confidence"] == "LOW"
    assert "last successful breadth cache" in breadth["notes"][-1].lower()


def test_vix_tax_at_normal():
    tax = calculate_vix_tax(15.0)
    assert tax["premium_premium_pct"] == 0


def test_vix_tax_at_elevated():
    tax = calculate_vix_tax(25.0)
    assert tax["premium_premium_pct"] > 0
    assert "elevated" in tax["note"].lower() or "above" in tax["note"].lower()
