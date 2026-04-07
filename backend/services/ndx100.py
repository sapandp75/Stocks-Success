import json
import time
import urllib.request

import pandas as pd
from io import StringIO

from backend.config import NDX100_FALLBACK

_cache: list[str] | None = None
_cache_time: float = 0
_CACHE_TTL = 86400  # 24 hours


def _fetch_from_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    # Find the table with a "Ticker" column
    for df in tables:
        if "Ticker" in df.columns:
            return sorted(df["Ticker"].str.replace(".", "-", regex=False).tolist())
    raise ValueError("No table with 'Ticker' column found on Nasdaq-100 Wikipedia page")


def get_ndx100_tickers(use_cache: bool = True) -> list[str]:
    global _cache, _cache_time

    if _cache is not None and (time.time() - _cache_time) < _CACHE_TTL:
        return _cache

    try:
        tickers = _fetch_from_wikipedia()
        NDX100_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
        NDX100_FALLBACK.write_text(json.dumps(tickers))
        _cache = tickers
        _cache_time = time.time()
        return tickers
    except Exception:
        if use_cache and NDX100_FALLBACK.exists():
            _cache = json.loads(NDX100_FALLBACK.read_text())
            _cache_time = time.time()
            return _cache
        raise
