from backend.services.forward_estimates import parse_yfinance_estimates


def test_parse_estimates_basic():
    """Extracts forward growth from yfinance info dict."""
    info = {
        "earningsGrowth": 0.15,
        "earningsQuarterlyGrowth": 0.12,
        "revenueGrowth": 0.18,
        "forwardEps": 8.50,
        "trailingEps": 7.20,
        "pegRatio": 1.2,
    }
    result = parse_yfinance_estimates(info)
    assert result["eps_growth_1yr"] == 0.15
    assert result["revenue_growth_trailing"] == 0.18
    assert result["forward_eps"] == 8.50
    assert result["trailing_eps"] == 7.20
    assert result["peg_ratio"] == 1.2
    assert abs(result["eps_fwd_vs_trailing"] - (8.50 / 7.20 - 1)) < 0.001


def test_parse_estimates_missing():
    """Handles missing fields gracefully."""
    result = parse_yfinance_estimates({})
    assert result["eps_growth_1yr"] is None
    assert result["forward_eps"] is None
    assert result["eps_fwd_vs_trailing"] is None
