import json
from unittest.mock import patch
from backend.services.sp500 import get_sp500_tickers
from backend.services.market_data import get_stock_fundamentals, REQUIRED_B1_FIELDS


def test_get_sp500_tickers_returns_list():
    tickers = get_sp500_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 400
    assert "AAPL" in tickers


def test_get_sp500_tickers_fallback_on_failure():
    with patch("backend.services.sp500._fetch_from_wikipedia", side_effect=Exception("network error")):
        tickers = get_sp500_tickers(use_cache=True)
        assert isinstance(tickers, list)
        assert len(tickers) > 400


def test_get_stock_fundamentals_aapl():
    result = get_stock_fundamentals("AAPL")
    data = result.value
    assert data["ticker"] == "AAPL"
    assert data["market_cap"] is not None and data["market_cap"] > 0
    assert result.source == "yfinance"


def test_fundamentals_tracks_missing_fields():
    result = get_stock_fundamentals("AAPL")
    # AAPL should have most fields populated
    assert isinstance(result.missing_fields, list)


def test_required_b1_fields_defined():
    assert "operating_margin" in REQUIRED_B1_FIELDS
    assert "free_cash_flow" in REQUIRED_B1_FIELDS
    assert "forward_pe" in REQUIRED_B1_FIELDS
    assert "revenue_growth" in REQUIRED_B1_FIELDS
    assert "debt_to_equity" in REQUIRED_B1_FIELDS
