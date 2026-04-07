from backend.services.external_targets import (
    build_target_comparison, parse_finviz_data,
)


def test_build_target_comparison():
    """Aggregates targets from multiple sources."""
    targets = {
        "yahoo": {"mean": 185, "low": 160, "high": 210},
        "finviz": {"target": 190},
    }
    your_dcf = {"bear": 140, "base": 175, "bull": 220}
    result = build_target_comparison(targets, your_dcf, current_price=165)

    assert result["current_price"] == 165
    assert result["yahoo_mean"] == 185
    assert result["finviz_target"] == 190
    assert result["your_dcf_base"] == 175
    assert result["upside_to_street_mean"] > 0  # 185/165 - 1


def test_build_target_comparison_missing():
    """Handles missing sources gracefully."""
    result = build_target_comparison({}, {}, current_price=100)
    assert result["yahoo_mean"] is None
    assert result["finviz_target"] is None


def test_parse_finviz_data():
    """Extracts target price from finviz fundament dict."""
    mock = {"Target Price": "190.50", "Analyst": "Buy"}
    result = parse_finviz_data(mock)
    assert result["target"] == 190.50
