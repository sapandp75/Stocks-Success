import json
from unittest.mock import patch
from backend.services.sp500 import get_sp500_tickers


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
