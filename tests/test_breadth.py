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
