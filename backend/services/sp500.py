import json
import time
import urllib.request
import pandas as pd
from io import StringIO
from backend.config import SP500_FALLBACK

_cache: list[str] | None = None
_cache_time: float = 0
_CACHE_TTL = 86400  # 24 hours


def _fetch_from_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    return sorted(df["Symbol"].str.replace(".", "-", regex=False).tolist())


def get_sp500_tickers(use_cache: bool = True) -> list[str]:
    global _cache, _cache_time

    if _cache is not None and (time.time() - _cache_time) < _CACHE_TTL:
        return _cache

    try:
        tickers = _fetch_from_wikipedia()
        SP500_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
        SP500_FALLBACK.write_text(json.dumps(tickers))
        _cache = tickers
        _cache_time = time.time()
        return tickers
    except Exception:
        if use_cache and SP500_FALLBACK.exists():
            _cache = json.loads(SP500_FALLBACK.read_text())
            _cache_time = time.time()
            return _cache
        raise
