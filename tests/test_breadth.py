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
