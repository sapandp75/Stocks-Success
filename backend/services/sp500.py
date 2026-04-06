import json
import urllib.request
import pandas as pd
from io import StringIO
from backend.config import SP500_FALLBACK

_cache: list[str] | None = None


def _fetch_from_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    return sorted(df["Symbol"].str.replace(".", "-", regex=False).tolist())


def get_sp500_tickers(use_cache: bool = True) -> list[str]:
    global _cache
    if _cache is not None:
        return _cache

    try:
        tickers = _fetch_from_wikipedia()
        # Update fallback file on success
        SP500_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
        SP500_FALLBACK.write_text(json.dumps(tickers))
        _cache = tickers
        return tickers
    except Exception:
        if use_cache and SP500_FALLBACK.exists():
            _cache = json.loads(SP500_FALLBACK.read_text())
            return _cache
        raise
