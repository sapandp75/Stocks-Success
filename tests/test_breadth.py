import json
import pandas as pd
from backend.services import ndx100


def _reset_ndx100_cache():
    ndx100._cache = None
    ndx100._cache_time = 0


def test_get_ndx100_tickers_returns_sorted_list(monkeypatch, tmp_path):
    _reset_ndx100_cache()

    html = """
    <table class="wikitable">
    <tr><th>Ticker</th><th>Company</th></tr>
    <tr><td>AAPL</td><td>Apple</td></tr>
    <tr><td>MSFT</td><td>Microsoft</td></tr>
    <tr><td>AMZN</td><td>Amazon</td></tr>
    </table>
    """

    def fake_urlopen(req):
        from io import BytesIO

        class FakeResp:
            def read(self):
                return html.encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("backend.services.ndx100.NDX100_FALLBACK", tmp_path / "ndx100.json")

    tickers = ndx100.get_ndx100_tickers()
    assert tickers == ["AAPL", "AMZN", "MSFT"]
    assert (tmp_path / "ndx100.json").exists()


def test_get_ndx100_tickers_uses_fallback_on_failure(monkeypatch, tmp_path):
    _reset_ndx100_cache()

    fallback_path = tmp_path / "ndx100.json"
    fallback_path.write_text(json.dumps(["GOOG", "META"]))

    monkeypatch.setattr("urllib.request.urlopen", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("backend.services.ndx100.NDX100_FALLBACK", fallback_path)

    tickers = ndx100.get_ndx100_tickers()
    assert tickers == ["GOOG", "META"]


from backend.services import regime_checker


def _reset_regime_caches():
    regime_checker._ndx_breadth_cache = None
    regime_checker._ndx_breadth_cache_time = 0


def test_calculate_ndx100_breadth_returns_structured_payload(monkeypatch):
    _reset_regime_caches()

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

    monkeypatch.setattr("backend.services.ndx100.get_ndx100_tickers", lambda: tickers)
    monkeypatch.setattr(regime_checker.yf, "download", lambda *args, **kwargs: frame)

    breadth = regime_checker.calculate_ndx100_breadth()
    assert breadth["method"] == "full_universe"
    assert breadth["confidence"] == "HIGH"
    assert breadth["sample_size"] == 3
    assert breadth["pct_above_200d"] == 33.3


def test_calculate_ndx100_breadth_returns_unavailable_on_failure(monkeypatch):
    _reset_regime_caches()

    monkeypatch.setattr("backend.services.ndx100.get_ndx100_tickers", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    breadth = regime_checker.calculate_ndx100_breadth()
    assert breadth["method"] == "unavailable"


from backend.services import stockcharts


def _reset_stockcharts_cache():
    stockcharts._cache = None
    stockcharts._cache_time = 0


FAKE_STOCKCHARTS_RESPONSE = {
    "sym": [
        {"s": "$NYMO", "n": "NYSE McClellan Oscillator", "c": 31.62, "ch": 11.77, "pch": 59.32, "d": "2026-04-04"},
        {"s": "$NYSI", "n": "NYSE McClellan Summation", "c": -259.87, "ch": 31.63, "pch": -10.85, "d": "2026-04-04"},
        {"s": "$NAMO", "n": "Nasdaq McClellan Oscillator", "c": 37.58, "ch": 11.08, "pch": 41.79, "d": "2026-04-04"},
        {"s": "$NASI", "n": "Nasdaq McClellan Summation", "c": -548.59, "ch": 37.57, "pch": -6.41, "d": "2026-04-04"},
        {"s": "$NYAD", "n": "NYSE Advance-Decline", "c": 723, "ch": 200, "pch": 38.24, "d": "2026-04-04"},
        {"s": "$NAAD", "n": "Nasdaq Advance-Decline", "c": 1148, "ch": 400, "pch": 53.48, "d": "2026-04-04"},
        {"s": "$NYHL", "n": "NYSE New Highs-Lows", "c": 21, "ch": 5, "pch": 31.25, "d": "2026-04-04"},
        {"s": "$NAHL", "n": "Nasdaq New Highs-Lows", "c": 16, "ch": 3, "pch": 23.08, "d": "2026-04-04"},
        {"s": "$CPC", "n": "CBOE Put/Call Ratio", "c": 0.97, "ch": -0.03, "pch": -3.0, "d": "2026-04-04"},
        {"s": "$TRIN", "n": "NYSE Arms Index", "c": 1.03, "ch": 0.1, "pch": 10.75, "d": "2026-04-04"},
        {"s": "$VIX", "n": "Volatility Index", "c": 24.17, "ch": -1.2, "pch": -4.73, "d": "2026-04-04"},
        {"s": "$BPSPX", "n": "S&P 500 Bullish %", "c": 43.2, "ch": 1.0, "pch": 2.37, "d": "2026-04-04"},
        {"s": "$BPNDX", "n": "Nasdaq 100 Bullish %", "c": 42.0, "ch": 0.5, "pch": 1.2, "d": "2026-04-04"},
        {"s": "$BPNYA", "n": "NYSE Bullish %", "c": 46.42, "ch": 0.8, "pch": 1.75, "d": "2026-04-04"},
        {"s": "$BPINFO", "n": "Info Tech", "c": 50.7, "ch": 1.2, "pch": 2.42, "d": "2026-04-04"},
        {"s": "$BPFINA", "n": "Financials", "c": 62.0, "ch": 0.5, "pch": 0.81, "d": "2026-04-04"},
        {"s": "$BPHEAL", "n": "Healthcare", "c": 38.0, "ch": -1.0, "pch": -2.56, "d": "2026-04-04"},
        {"s": "$BPINDY", "n": "Industrials", "c": 45.0, "ch": 0.3, "pch": 0.67, "d": "2026-04-04"},
        {"s": "$BPDISC", "n": "Consumer Discretionary", "c": 35.0, "ch": -0.5, "pch": -1.41, "d": "2026-04-04"},
        {"s": "$BPSTAP", "n": "Consumer Staples", "c": 72.0, "ch": 1.0, "pch": 1.41, "d": "2026-04-04"},
        {"s": "$BPENER", "n": "Energy", "c": 55.0, "ch": 2.0, "pch": 3.77, "d": "2026-04-04"},
        {"s": "$BPMATE", "n": "Materials", "c": 40.0, "ch": 0.0, "pch": 0.0, "d": "2026-04-04"},
        {"s": "$BPREAL", "n": "Real Estate", "c": 48.0, "ch": 0.5, "pch": 1.05, "d": "2026-04-04"},
        {"s": "$BPCOMM", "n": "Communication Services", "c": 58.0, "ch": 1.5, "pch": 2.65, "d": "2026-04-04"},
        {"s": "$BPUTIL", "n": "Utilities", "c": 68.0, "ch": 0.8, "pch": 1.19, "d": "2026-04-04"},
    ]
}


def test_parse_stockcharts_response():
    _reset_stockcharts_cache()

    result = stockcharts._parse_response(FAKE_STOCKCHARTS_RESPONSE)
    assert result["mcclellan"]["nymo"]["value"] == 31.62
    assert result["mcclellan"]["nysi"]["change"] == 31.63
    assert result["advance_decline"]["nyad"]["value"] == 723
    assert result["sentiment"]["cpc"]["value"] == 0.97
    assert result["bullish_pct"]["spx"] == 43.2
    assert len(result["bullish_pct"]["sectors"]) == 11
    assert result["bullish_pct"]["sectors"][0]["symbol"].startswith("$BP")


def test_stockcharts_returns_error_on_failure(monkeypatch):
    _reset_stockcharts_cache()

    monkeypatch.setattr("urllib.request.urlopen", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))

    result = stockcharts.get_stockcharts_breadth()
    assert "error" in result
    assert result["stale"] is None


def test_stockcharts_returns_stale_on_failure(monkeypatch):
    _reset_stockcharts_cache()

    stockcharts._cache = {"mcclellan": {"nymo": {"value": 10}}}
    stockcharts._cache_time = stockcharts.time.time() - 7200  # 2h old, within 24h stale TTL

    monkeypatch.setattr("urllib.request.urlopen", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))

    result = stockcharts.get_stockcharts_breadth()
    assert "error" in result
    assert result["stale"] is not None
    assert result["stale"]["mcclellan"]["nymo"]["value"] == 10


from backend.services.breadth import calculate_breadth_score, get_combined_breadth


def test_breadth_score_all_bullish():
    sc = {
        "mcclellan": {
            "nymo": {"value": 30, "change": 5, "signal": "BULLISH"},
            "nysi": {"value": 100, "change": 10, "signal": "BULLISH"},
        },
        "advance_decline": {
            "nyhl": {"value": 80, "change": 5, "signal": "HEALTHY"},
        },
        "sentiment": {
            "cpc": {"value": 0.5, "change": -0.1, "signal": "COMPLACENT"},
        },
        "bullish_pct": {
            "spx": 60.0,
        },
    }
    spx = {"pct_above_200d": 70.0}

    score, verdict = calculate_breadth_score(sc, spx)
    assert score == 10.0
    assert verdict == "RISK-ON"


def test_breadth_score_all_bearish():
    sc = {
        "mcclellan": {
            "nymo": {"value": -30, "change": -5, "signal": "BEARISH"},
            "nysi": {"value": -600, "change": -10, "signal": "DEEPLY_BEARISH"},
        },
        "advance_decline": {
            "nyhl": {"value": -80, "change": -5, "signal": "POOR"},
        },
        "sentiment": {
            "cpc": {"value": 1.3, "change": 0.1, "signal": "EXTREME_FEAR"},
        },
        "bullish_pct": {
            "spx": 20.0,
        },
    }
    spx = {"pct_above_200d": 30.0}

    score, verdict = calculate_breadth_score(sc, spx)
    assert score == 0.0
    assert verdict == "RISK-OFF"


def test_breadth_score_mixed():
    sc = {
        "mcclellan": {
            "nymo": {"value": 0, "change": 0, "signal": "NEUTRAL"},
            "nysi": {"value": -200, "change": 5, "signal": "RECOVERING"},
        },
        "advance_decline": {
            "nyhl": {"value": 0, "change": 0, "signal": "MARGINAL"},
        },
        "sentiment": {
            "cpc": {"value": 0.9, "change": 0, "signal": "NEUTRAL"},
        },
        "bullish_pct": {
            "spx": 45.0,
        },
    }
    spx = {"pct_above_200d": 50.0}

    score, verdict = calculate_breadth_score(sc, spx)
    assert score == 5.0
    assert verdict == "CAUTION"


def test_breadth_score_all_unavailable():
    score, verdict = calculate_breadth_score({}, {})
    assert score == 0.0
    assert verdict == "RISK-OFF"


from fastapi.testclient import TestClient
from backend.main import app


def test_breadth_api_returns_200(monkeypatch):
    _reset_stockcharts_cache()

    # Mock stockcharts to avoid real HTTP calls
    monkeypatch.setattr(
        "backend.services.stockcharts.get_stockcharts_breadth",
        lambda: stockcharts._parse_response(FAKE_STOCKCHARTS_RESPONSE),
    )
    # Mock yfinance breadth calculations
    monkeypatch.setattr(
        "backend.services.breadth.calculate_market_breadth",
        lambda: {
            "pct_above_200d": 50.0, "pct_above_50d": 55.0, "pct_above_20d": 40.0,
            "method": "full_universe", "confidence": "HIGH", "breadth_signal": "HEALTHY",
            "universe_size": 500, "sample_size": 480, "coverage_pct": 96.0,
            "as_of": "2026-04-07", "notes": [],
        },
    )
    monkeypatch.setattr(
        "backend.services.breadth.calculate_ndx100_breadth",
        lambda: {
            "pct_above_200d": 45.0, "pct_above_50d": 50.0, "pct_above_20d": 35.0,
            "method": "full_universe", "confidence": "HIGH", "breadth_signal": "WEAKENING",
            "universe_size": 100, "sample_size": 95, "coverage_pct": 95.0,
            "as_of": "2026-04-07", "notes": [],
        },
    )

    client = TestClient(app)
    resp = client.get("/api/breadth")
    assert resp.status_code == 200

    data = resp.json()
    assert "score" in data
    assert "verdict" in data
    assert data["verdict"] in ("RISK-OFF", "CAUTION", "RISK-ON")
    assert "mcclellan" in data
    assert "advance_decline" in data
    assert "sentiment" in data
    assert "bullish_pct" in data
    assert "spx_breadth" in data
    assert "ndx_breadth" in data
