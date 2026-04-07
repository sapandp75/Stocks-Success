# Breadth Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated Breadth tab with full market breadth terminal — McClellan indicators, advance/decline, bullish %, participation, sentiment — replacing the old single-gauge BreadthGauge component.

**Architecture:** Two data sources feed one `/api/breadth` endpoint: (1) StockCharts j-sum public endpoint for McClellan/A-D/sentiment/bullish-% data, (2) existing yfinance batch download extended to Nasdaq 100 for % above MA calculations. A weighted 0–10 breadth score aggregates 6 components into RISK-OFF/CAUTION/RISK-ON verdict. Frontend renders 5 sections on a new BreadthPage, and RegimePage gets a compact 1-line summary row replacing the old gauge.

**Tech Stack:** Python/FastAPI backend, React frontend, StockCharts j-sum API (no key), yfinance, Wikipedia scrape for NDX 100 tickers.

**Spec:** `docs/superpowers/specs/2026-04-07-breadth-page-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| CREATE | `backend/services/stockcharts.py` | Fetch + parse StockCharts j-sum endpoint, 1h cache, stale fallback |
| CREATE | `backend/services/ndx100.py` | NDX 100 ticker list from Wikipedia, 24h cache, fallback file |
| CREATE | `backend/services/breadth.py` | Combine all breadth sources, score formula, verdict logic |
| CREATE | `backend/routers/breadth.py` | `GET /api/breadth` route |
| CREATE | `frontend/src/pages/BreadthPage.jsx` | Full breadth terminal page |
| CREATE | `tests/test_breadth.py` | Tests for breadth scoring, stockcharts parsing, ndx100 |
| MODIFY | `backend/services/regime_checker.py` | Add `calculate_ndx100_breadth()` |
| MODIFY | `backend/config.py` | Add `NDX100_FALLBACK` path |
| MODIFY | `backend/main.py` | Register breadth router |
| MODIFY | `frontend/src/App.jsx` | Add `/breadth` route |
| MODIFY | `frontend/src/components/Navbar.jsx` | Add Breadth tab between Options and Watchlist |
| MODIFY | `frontend/src/api.js` | Add `getBreadth()` |
| MODIFY | `frontend/src/pages/RegimePage.jsx` | Replace BreadthGauge with compact summary row |
| DELETE | `frontend/src/components/BreadthGauge.jsx` | Old single-gauge component |

---

### Task 1: NDX 100 Ticker Service

**Files:**
- Create: `backend/services/ndx100.py`
- Modify: `backend/config.py`
- Test: `tests/test_breadth.py`

- [ ] **Step 1: Add NDX100_FALLBACK to config**

In `backend/config.py`, add after the `SP500_FALLBACK` line:

```python
NDX100_FALLBACK = DATA_DIR / "ndx100_fallback.json"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_breadth.py`:

```python
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
    monkeypatch.setattr("backend.config.NDX100_FALLBACK", tmp_path / "ndx100.json")

    tickers = ndx100.get_ndx100_tickers()
    assert tickers == ["AAPL", "AMZN", "MSFT"]
    assert (tmp_path / "ndx100.json").exists()


def test_get_ndx100_tickers_uses_fallback_on_failure(monkeypatch, tmp_path):
    _reset_ndx100_cache()

    fallback_path = tmp_path / "ndx100.json"
    fallback_path.write_text(json.dumps(["GOOG", "META"]))

    monkeypatch.setattr("urllib.request.urlopen", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("backend.config.NDX100_FALLBACK", fallback_path)

    tickers = ndx100.get_ndx100_tickers()
    assert tickers == ["GOOG", "META"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py -v`
Expected: FAIL — `ndx100` module does not exist yet.

- [ ] **Step 4: Implement ndx100.py**

Create `backend/services/ndx100.py`:

```python
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
    url = "https://en.wikipedia.org/wiki/List_of_Nasdaq-100_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    return sorted(df["Ticker"].str.replace(".", "-", regex=False).tolist())


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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/config.py backend/services/ndx100.py tests/test_breadth.py
git commit -m "feat: add NDX 100 ticker service with Wikipedia scrape and fallback"
```

---

### Task 2: NDX 100 Breadth Calculation in regime_checker.py

**Files:**
- Modify: `backend/services/regime_checker.py`
- Test: `tests/test_breadth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_breadth.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py::test_calculate_ndx100_breadth_returns_structured_payload -v`
Expected: FAIL — `calculate_ndx100_breadth` not defined.

- [ ] **Step 3: Add NDX breadth calculation to regime_checker.py**

Add after `_BREADTH_STALE_TTL = 86400` (line 18):

```python
# NDX 100 breadth cache (1 hour TTL)
_ndx_breadth_cache: dict | None = None
_ndx_breadth_cache_time: float = 0
_NDX_BREADTH_CACHE_TTL = 3600
```

Add after `calculate_market_breadth()` function (after line 307):

```python
def calculate_ndx100_breadth() -> dict:
    """Calculate structured breadth metrics for the Nasdaq 100 using a deterministic batch download."""
    global _ndx_breadth_cache, _ndx_breadth_cache_time
    now = time.time()
    if _ndx_breadth_cache is not None and (now - _ndx_breadth_cache_time) < _NDX_BREADTH_CACHE_TTL:
        return _ndx_breadth_cache

    try:
        from backend.services.ndx100 import get_ndx100_tickers

        all_tickers = sorted(get_ndx100_tickers())
        universe_size = len(all_tickers)
        if universe_size == 0:
            raise ValueError("No NDX 100 tickers available")

        df = yf.download(
            all_tickers,
            period="1y",
            group_by="column",
            progress=False,
            threads=True,
        )
        if df.empty:
            raise ValueError("NDX breadth download returned no data")

        close = df["Close"]

        above_200 = 0
        above_50 = 0
        above_20 = 0
        counted = 0

        for ticker in all_tickers:
            try:
                series = close[ticker].dropna()
                if len(series) < 200:
                    continue
                price = float(series.iloc[-1])
                sma20 = float(series.rolling(20).mean().iloc[-1])
                sma50 = float(series.rolling(50).mean().iloc[-1])
                sma200 = float(series.rolling(200).mean().iloc[-1])
                if any(math.isnan(value) for value in (price, sma20, sma50, sma200)):
                    continue
                counted += 1
                if price > sma20:
                    above_20 += 1
                if price > sma50:
                    above_50 += 1
                if price > sma200:
                    above_200 += 1
            except Exception:
                continue

        result = _breadth_payload(
            method="full_universe",
            universe_size=universe_size,
            sample_size=counted,
            pct_200=round(above_200 / counted * 100, 1) if counted else None,
            pct_50=round(above_50 / counted * 100, 1) if counted else None,
            pct_20=round(above_20 / counted * 100, 1) if counted else None,
        )

        if result["method"] != "unavailable":
            _ndx_breadth_cache = result
            _ndx_breadth_cache_time = time.time()
            return result
    except Exception:
        pass

    return _breadth_payload(
        method="unavailable",
        notes=["NDX 100 breadth data unavailable."],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/regime_checker.py tests/test_breadth.py
git commit -m "feat: add NDX 100 breadth calculation to regime_checker"
```

---

### Task 3: StockCharts Service

**Files:**
- Create: `backend/services/stockcharts.py`
- Test: `tests/test_breadth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_breadth.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py::test_parse_stockcharts_response -v`
Expected: FAIL — `stockcharts` module does not exist.

- [ ] **Step 3: Implement stockcharts.py**

Create `backend/services/stockcharts.py`:

```python
import json
import time
import urllib.request

_cache: dict | None = None
_cache_time: float = 0
_CACHE_TTL = 3600  # 1 hour
_STALE_TTL = 86400  # 24 hours

# Symbols we extract from the j-sum response
_MCCLELLAN_SYMBOLS = {"$NYMO", "$NYSI", "$NAMO", "$NASI"}
_AD_SYMBOLS = {"$NYAD", "$NAAD", "$NYHL", "$NAHL"}
_SENTIMENT_SYMBOLS = {"$CPC", "$TRIN", "$VIX"}
_BP_INDEX_SYMBOLS = {"$BPSPX", "$BPNDX", "$BPNYA"}
_BP_SECTOR_SYMBOLS = {
    "$BPINFO", "$BPFINA", "$BPHEAL", "$BPINDY", "$BPDISC",
    "$BPSTAP", "$BPENER", "$BPMATE", "$BPREAL", "$BPCOMM", "$BPUTIL",
}

_MCCLELLAN_KEYS = {"$NYMO": "nymo", "$NYSI": "nysi", "$NAMO": "namo", "$NASI": "nasi"}
_AD_KEYS = {"$NYAD": "nyad", "$NAAD": "naad", "$NYHL": "nyhl", "$NAHL": "nahl"}
_SENTIMENT_KEYS = {"$CPC": "cpc", "$TRIN": "trin", "$VIX": "vix"}
_BP_INDEX_KEYS = {"$BPSPX": "spx", "$BPNDX": "ndx", "$BPNYA": "nya"}


def _signal_mcclellan(symbol: str, value: float) -> str:
    if symbol in ("$NYSI", "$NASI"):
        if value > 0:
            return "BULLISH"
        if value > -500:
            return "RECOVERING" if value > -250 else "BEARISH"
        return "DEEPLY_BEARISH"
    # Oscillators ($NYMO, $NAMO)
    if value > 50:
        return "OVERBOUGHT"
    if value > 20:
        return "BULLISH"
    if value > -20:
        return "RECOVERING" if value > 0 else "NEUTRAL"
    if value > -50:
        return "BEARISH"
    return "OVERSOLD"


def _signal_ad(symbol: str, value: float) -> str:
    if symbol in ("$NYHL", "$NAHL"):
        if value > 100:
            return "STRONG"
        if value > 50:
            return "HEALTHY"
        if value > -50:
            return "MARGINAL"
        return "POOR"
    # $NYAD, $NAAD
    if value > 500:
        return "ADVANCING"
    if value > 0:
        return "SLIGHTLY_ADVANCING"
    if value > -500:
        return "SLIGHTLY_DECLINING"
    return "DECLINING"


def _signal_sentiment(symbol: str, value: float) -> str:
    if symbol == "$CPC":
        if value > 1.2:
            return "EXTREME_FEAR"
        if value > 1.0:
            return "FEAR"
        if value > 0.7:
            return "NEUTRAL"
        return "COMPLACENT"
    if symbol == "$TRIN":
        if value > 2.0:
            return "PANIC_SELLING"
        if value > 1.2:
            return "BEARISH"
        if value > 0.8:
            return "NEUTRAL"
        return "BULLISH"
    # $VIX
    if value > 30:
        return "EXTREME"
    if value > 25:
        return "HIGH"
    if value > 20:
        return "ELEVATED"
    if value > 15:
        return "NORMAL"
    return "LOW"


def _signal_bp(value: float) -> str:
    if value >= 60:
        return "BULLISH"
    if value >= 40:
        return "NEUTRAL"
    return "BEARISH"


def _parse_response(data: dict) -> dict:
    symbols = {item["s"]: item for item in data.get("sym", [])}

    mcclellan = {}
    for sym, key in _MCCLELLAN_KEYS.items():
        item = symbols.get(sym)
        if item:
            mcclellan[key] = {
                "value": item["c"],
                "change": item["ch"],
                "signal": _signal_mcclellan(sym, item["c"]),
            }

    advance_decline = {}
    for sym, key in _AD_KEYS.items():
        item = symbols.get(sym)
        if item:
            advance_decline[key] = {
                "value": item["c"],
                "change": item["ch"],
                "signal": _signal_ad(sym, item["c"]),
            }

    sentiment = {}
    for sym, key in _SENTIMENT_KEYS.items():
        item = symbols.get(sym)
        if item:
            sentiment[key] = {
                "value": item["c"],
                "change": item["ch"],
                "signal": _signal_sentiment(sym, item["c"]),
            }

    bullish_pct = {}
    for sym, key in _BP_INDEX_KEYS.items():
        item = symbols.get(sym)
        if item:
            bullish_pct[key] = item["c"]

    sectors = []
    for sym in sorted(_BP_SECTOR_SYMBOLS):
        item = symbols.get(sym)
        if item:
            sectors.append({
                "symbol": sym,
                "name": item["n"],
                "value": item["c"],
                "signal": _signal_bp(item["c"]),
            })
    bullish_pct["sectors"] = sectors

    return {
        "mcclellan": mcclellan,
        "advance_decline": advance_decline,
        "sentiment": sentiment,
        "bullish_pct": bullish_pct,
    }


def _stale_result() -> dict | None:
    if _cache is None:
        return None
    age = time.time() - _cache_time
    if age >= _STALE_TTL:
        return None
    return _cache


def get_stockcharts_breadth() -> dict:
    global _cache, _cache_time

    now = time.time()
    if _cache is not None and (now - _cache_time) < _CACHE_TTL:
        return _cache

    try:
        url = "https://stockcharts.com/j-sum/sum?q=$NYMO"
        req = urllib.request.Request(url, headers={
            "Referer": "https://stockcharts.com/",
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        result = _parse_response(data)
        _cache = result
        _cache_time = time.time()
        return result
    except Exception as e:
        return {"error": str(e), "stale": _stale_result()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/stockcharts.py tests/test_breadth.py
git commit -m "feat: add StockCharts j-sum breadth service with caching and stale fallback"
```

---

### Task 4: Breadth Score & Aggregation Service

**Files:**
- Create: `backend/services/breadth.py`
- Test: `tests/test_breadth.py`

- [ ] **Step 1: Write the failing test for score calculation**

Append to `tests/test_breadth.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py::test_breadth_score_all_bullish -v`
Expected: FAIL — module `backend.services.breadth` not found.

- [ ] **Step 3: Implement breadth.py**

Create `backend/services/breadth.py`:

```python
from datetime import date

from backend.services.stockcharts import get_stockcharts_breadth
from backend.services.regime_checker import calculate_market_breadth, calculate_ndx100_breadth


def _component_score(value: float | None, bearish_thresh: float, bullish_thresh: float, *, invert: bool = False) -> float | None:
    """Score a component 0/0.5/1.0. If invert=True, high values are bearish."""
    if value is None:
        return None
    if invert:
        if value > bearish_thresh:
            return 0.0
        if value < bullish_thresh:
            return 1.0
        return 0.5
    else:
        if value < bearish_thresh:
            return 0.0
        if value > bullish_thresh:
            return 1.0
        return 0.5


def calculate_breadth_score(stockcharts_data: dict, spx_breadth: dict) -> tuple[float, str]:
    """
    Weighted 0-10 breadth score from 6 components.
    Returns (score, verdict).
    """
    components = [
        # (weight, score_or_none)
        (3, _component_score(
            stockcharts_data.get("mcclellan", {}).get("nysi", {}).get("value"),
            bearish_thresh=-500, bullish_thresh=0,
        )),
        (2, _component_score(
            spx_breadth.get("pct_above_200d"),
            bearish_thresh=40, bullish_thresh=60,
        )),
        (2, _component_score(
            stockcharts_data.get("bullish_pct", {}).get("spx"),
            bearish_thresh=30, bullish_thresh=50,
        )),
        (1, _component_score(
            stockcharts_data.get("mcclellan", {}).get("nymo", {}).get("value"),
            bearish_thresh=-20, bullish_thresh=20,
        )),
        (1, _component_score(
            stockcharts_data.get("advance_decline", {}).get("nyhl", {}).get("value"),
            bearish_thresh=-50, bullish_thresh=50,
        )),
        (1, _component_score(
            stockcharts_data.get("sentiment", {}).get("cpc", {}).get("value"),
            bearish_thresh=1.2, bullish_thresh=0.7, invert=True,
        )),
    ]

    total_weight = 0
    weighted_sum = 0.0

    for weight, score in components:
        if score is not None:
            total_weight += weight
            weighted_sum += weight * score

    if total_weight == 0:
        return 0.0, "RISK-OFF"

    raw = round(weighted_sum / total_weight * 10, 1)

    if raw < 3.0:
        verdict = "RISK-OFF"
    elif raw <= 6.0:
        verdict = "CAUTION"
    else:
        verdict = "RISK-ON"

    return raw, verdict


def _verdict_note(verdict: str, score: float) -> str:
    if verdict == "RISK-OFF":
        return f"Breadth score {score}/10 — majority of indicators bearish. Market internals weak."
    if verdict == "CAUTION":
        return f"Breadth score {score}/10 — mixed signals. Some internals healthy, others deteriorating."
    return f"Breadth score {score}/10 — broad participation. Market internals support risk-taking."


def get_combined_breadth() -> dict:
    """Assemble the full breadth payload from all sources."""
    sc_data = get_stockcharts_breadth()
    spx_breadth = calculate_market_breadth()
    ndx_breadth = calculate_ndx100_breadth()

    # If stockcharts returned an error, use stale data or empty
    if "error" in sc_data:
        sc_effective = sc_data.get("stale") or {}
        is_stale = sc_data.get("stale") is not None
    else:
        sc_effective = sc_data
        is_stale = False

    score, verdict = calculate_breadth_score(sc_effective, spx_breadth)

    result = {
        "as_of": date.today().isoformat(),
        "score": score,
        "verdict": verdict,
        "verdict_note": _verdict_note(verdict, score),
        "spx_breadth": spx_breadth,
        "ndx_breadth": ndx_breadth,
        "mcclellan": sc_effective.get("mcclellan", {}),
        "advance_decline": sc_effective.get("advance_decline", {}),
        "sentiment": sc_effective.get("sentiment", {}),
        "bullish_pct": sc_effective.get("bullish_pct", {}),
    }

    if is_stale:
        result["stale"] = True

    if "error" in sc_data and sc_data.get("stale") is None:
        result["stockcharts_error"] = sc_data["error"]

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/breadth.py tests/test_breadth.py
git commit -m "feat: add breadth score aggregation with weighted 0-10 formula"
```

---

### Task 5: Breadth API Route

**Files:**
- Create: `backend/routers/breadth.py`
- Modify: `backend/main.py`
- Test: `tests/test_breadth.py`

- [ ] **Step 1: Create the router**

Create `backend/routers/breadth.py`:

```python
from fastapi import APIRouter

from backend.services.breadth import get_combined_breadth

router = APIRouter(prefix="/api/breadth", tags=["breadth"])


@router.get("")
def breadth():
    return get_combined_breadth()
```

- [ ] **Step 2: Register the router in main.py**

In `backend/main.py`, add to the import line (line 8):

```python
from backend.routers import regime, screener, options, deep_dive, watchlist, positions, research, breadth
```

Add after `app.include_router(research.router)` (line 34):

```python
app.include_router(breadth.router)
```

- [ ] **Step 3: Write an integration test**

Append to `tests/test_breadth.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd stock-analysis-system && python -m pytest tests/test_breadth.py::test_breadth_api_returns_200 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/breadth.py backend/main.py tests/test_breadth.py
git commit -m "feat: add GET /api/breadth route"
```

---

### Task 6: Frontend API Helper & Routing

**Files:**
- Modify: `frontend/src/api.js`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Navbar.jsx`

- [ ] **Step 1: Add getBreadth to api.js**

In `frontend/src/api.js`, add after the `getRegime` line (line 36):

```javascript
export const getBreadth = () => fetchJSON('/breadth')
```

- [ ] **Step 2: Add Breadth tab to Navbar**

In `frontend/src/components/Navbar.jsx`, update the links array (lines 5-12):

```javascript
const links = [
  ['/', 'Regime'],
  ['/screener', 'Screener'],
  ['/deep-dive', 'Deep Dive'],
  ['/options', 'Options'],
  ['/breadth', 'Breadth'],
  ['/watchlist', 'Watchlist'],
  ['/positions', 'Positions'],
]
```

- [ ] **Step 3: Add /breadth route to App.jsx**

In `frontend/src/App.jsx`, add the import (after line 8):

```javascript
import BreadthPage from './pages/BreadthPage'
```

Add the route (after the Options route, line 22):

```jsx
<Route path="/breadth" element={<BreadthPage />} />
```

- [ ] **Step 4: Create placeholder BreadthPage**

Create `frontend/src/pages/BreadthPage.jsx` with a minimal placeholder so the route doesn't crash:

```jsx
export default function BreadthPage() {
  return <div className="p-6">Breadth page loading...</div>
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api.js frontend/src/components/Navbar.jsx frontend/src/App.jsx frontend/src/pages/BreadthPage.jsx
git commit -m "feat: add breadth route, navbar tab, and API helper"
```

---

### Task 7: BreadthPage — Full Implementation

**Files:**
- Modify: `frontend/src/pages/BreadthPage.jsx`

- [ ] **Step 1: Implement the full BreadthPage**

Replace `frontend/src/pages/BreadthPage.jsx` with:

```jsx
import { useState, useEffect } from 'react'
import { getBreadth } from '../api'

const COLORS = {
  green: '#00a562', red: '#e5484d', amber: '#d97b0e',
  text: '#1a1a2e', muted: '#6b7280', border: '#e2e4e8', bg: '#f0f1f3',
}

function verdictColor(verdict) {
  if (verdict === 'RISK-ON') return COLORS.green
  if (verdict === 'RISK-OFF') return COLORS.red
  return COLORS.amber
}

function signalBadge(signal) {
  if (!signal) return null
  const bullish = ['BULLISH', 'STRONG', 'HEALTHY', 'ADVANCING', 'OVERBOUGHT', 'LOW', 'COMPLACENT']
  const bearish = ['BEARISH', 'DEEPLY_BEARISH', 'POOR', 'DECLINING', 'OVERSOLD', 'EXTREME', 'HIGH', 'EXTREME_FEAR', 'PANIC_SELLING', 'FEAR']
  let bg, color
  if (bullish.includes(signal)) { bg = '#dcfce7'; color = COLORS.green }
  else if (bearish.includes(signal)) { bg = '#fef2f2'; color = COLORS.red }
  else { bg = '#fef9c3'; color = COLORS.amber }
  return (
    <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ backgroundColor: bg, color }}>
      {signal.replace(/_/g, ' ')}
    </span>
  )
}

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-lg border p-4" style={{ borderColor: COLORS.border }}>
      {title && <div className="text-xs font-medium mb-2" style={{ color: COLORS.muted }}>{title}</div>}
      {children}
    </div>
  )
}

function ValueCard({ label, data }) {
  if (!data) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const changeArrow = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '—'
  const changeColor = data.change > 0 ? COLORS.green : data.change < 0 ? COLORS.red : COLORS.muted
  return (
    <Card title={label}>
      <div className="flex items-center justify-between">
        <span className="text-xl font-bold" style={{ color: COLORS.text }}>
          {typeof data.value === 'number' ? data.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}
        </span>
        {signalBadge(data.signal)}
      </div>
      <div className="text-xs mt-1" style={{ color: changeColor }}>
        {changeArrow} {Math.abs(data.change || 0).toFixed(2)}
      </div>
    </Card>
  )
}

function OscillatorCard({ label, data, min, max }) {
  if (!data) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const range = max - min
  const pct = Math.max(0, Math.min(100, ((data.value - min) / range) * 100))
  const changeArrow = data.change > 0 ? '▲' : data.change < 0 ? '▼' : '—'
  const changeColor = data.change > 0 ? COLORS.green : data.change < 0 ? COLORS.red : COLORS.muted
  return (
    <Card title={label}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xl font-bold" style={{ color: COLORS.text }}>
          {data.value.toFixed(2)}
        </span>
        {signalBadge(data.signal)}
      </div>
      <div className="text-xs mb-1" style={{ color: changeColor }}>
        {changeArrow} {Math.abs(data.change || 0).toFixed(2)}
      </div>
      <div className="relative h-2 rounded-full" style={{
        background: `linear-gradient(to right, ${COLORS.red}, ${COLORS.amber} 30%, ${COLORS.green} 50%, ${COLORS.amber} 70%, ${COLORS.red})`,
      }}>
        <div className="absolute top-0 w-0.5 h-full bg-black rounded" style={{ left: `${pct}%`, transform: 'translateX(-50%)' }} />
      </div>
      <div className="flex justify-between text-xs mt-0.5" style={{ color: COLORS.muted }}>
        <span>{min}</span><span>0</span><span>{max}</span>
      </div>
    </Card>
  )
}

function ParticipationCard({ label, data }) {
  if (!data || data.pct_above_200d == null) return <Card title={label}><span style={{ color: COLORS.muted }}>Unavailable</span></Card>
  const pct200 = data.pct_above_200d
  const pct50 = data.pct_above_50d
  const pct20 = data.pct_above_20d
  const barColor = pct200 >= 60 ? COLORS.green : pct200 >= 40 ? COLORS.amber : COLORS.red
  return (
    <Card title={label}>
      <div className="text-xl font-bold" style={{ color: COLORS.text }}>{pct200.toFixed(1)}%</div>
      <div className="text-xs" style={{ color: COLORS.muted }}>above 200d SMA</div>
      <div className="h-2 rounded-full mt-2" style={{ backgroundColor: '#e2e4e8' }}>
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, pct200)}%`, backgroundColor: barColor }} />
      </div>
      <div className="flex gap-3 text-xs mt-2" style={{ color: COLORS.muted }}>
        <span>50d: {pct50 != null ? `${pct50.toFixed(1)}%` : 'N/A'}</span>
        <span>20d: {pct20 != null ? `${pct20.toFixed(1)}%` : 'N/A'}</span>
      </div>
    </Card>
  )
}

function SectorChart({ sectors }) {
  if (!sectors || sectors.length === 0) return null
  const sorted = [...sectors].sort((a, b) => b.value - a.value)
  const maxVal = 100
  return (
    <Card title="Sector Bullish %">
      <div className="space-y-1.5">
        {sorted.map(s => {
          const barColor = s.value >= 60 ? COLORS.green : s.value >= 40 ? COLORS.amber : COLORS.red
          return (
            <div key={s.symbol} className="flex items-center gap-2">
              <div className="text-xs w-28 truncate" style={{ color: COLORS.text }}>{s.name}</div>
              <div className="flex-1 h-3 rounded-full" style={{ backgroundColor: '#e2e4e8' }}>
                <div className="h-full rounded-full" style={{ width: `${s.value / maxVal * 100}%`, backgroundColor: barColor }} />
              </div>
              <div className="text-xs w-10 text-right font-medium" style={{ color: COLORS.text }}>{s.value.toFixed(0)}%</div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export default function BreadthPage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = () => {
      getBreadth()
        .then(d => { if (!cancelled) { setData(d); setLoading(false); setError(null) } })
        .catch(e => { if (!cancelled) { setError(e.message); setLoading(false) } })
    }
    load()
    const interval = setInterval(load, 3600000) // 1h refresh
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (loading) return <div className="p-8" style={{ color: COLORS.muted }}>Loading breadth data...</div>
  if (!data) return (
    <div className="p-8" style={{ color: COLORS.red }}>
      Failed to load breadth data.{error && ` (${error})`}
    </div>
  )

  const mc = data.mcclellan || {}
  const ad = data.advance_decline || {}
  const sent = data.sentiment || {}
  const bp = data.bullish_pct || {}

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-6" style={{ color: COLORS.text }}>Market Breadth</h1>

      {/* Section 1: Summary strip */}
      <div className="bg-white rounded-lg border p-4 mb-6 flex items-center gap-4 flex-wrap" style={{ borderColor: COLORS.border }}>
        <span className="text-sm font-bold px-3 py-1 rounded" style={{
          backgroundColor: verdictColor(data.verdict) + '20',
          color: verdictColor(data.verdict),
        }}>
          {data.verdict}
        </span>
        <span className="text-2xl font-bold" style={{ color: COLORS.text }}>{data.score}/10</span>
        <div className="flex gap-4 text-sm" style={{ color: COLORS.muted }}>
          <span>$NYSI {mc.nysi?.value?.toLocaleString() ?? 'N/A'}</span>
          <span>$BPSPX {bp.spx != null ? `${bp.spx}%` : 'N/A'}</span>
          <span>S&P above 200d {data.spx_breadth?.pct_above_200d != null ? `${data.spx_breadth.pct_above_200d}%` : 'N/A'}</span>
        </div>
        {data.stale && (
          <span className="text-xs px-2 py-0.5 rounded" style={{ backgroundColor: '#fef9c3', color: COLORS.amber }}>
            STALE DATA
          </span>
        )}
      </div>

      {data.verdict_note && (
        <div className="text-sm mb-6 p-3 rounded" style={{ backgroundColor: '#f7f8fa', color: COLORS.muted }}>
          {data.verdict_note}
        </div>
      )}

      {/* Section 2: McClellan */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>McClellan Indicators</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <OscillatorCard label="$NYMO — NYSE Oscillator" data={mc.nymo} min={-150} max={150} />
        <OscillatorCard label="$NYSI — NYSE Summation" data={mc.nysi} min={-1500} max={1500} />
        <OscillatorCard label="$NAMO — Nasdaq Oscillator" data={mc.namo} min={-150} max={150} />
        <OscillatorCard label="$NASI — Nasdaq Summation" data={mc.nasi} min={-1500} max={1500} />
      </div>

      {/* Section 3: Advance/Decline + Highs/Lows */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Advance/Decline & Highs/Lows</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <ValueCard label="$NYAD — NYSE A/D" data={ad.nyad} />
        <ValueCard label="$NAAD — Nasdaq A/D" data={ad.naad} />
        <ValueCard label="$NYHL — NYSE Highs−Lows" data={ad.nyhl} />
        <ValueCard label="$NAHL — Nasdaq Highs−Lows" data={ad.nahl} />
      </div>

      {/* Section 4: Participation */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Participation</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <ParticipationCard label="S&P 500 — % Above MAs" data={data.spx_breadth} />
        <ParticipationCard label="Nasdaq 100 — % Above MAs" data={data.ndx_breadth} />
        <ValueCard label="$BPSPX — S&P 500 BP" data={bp.spx != null ? { value: bp.spx, change: 0, signal: bp.spx >= 60 ? 'BULLISH' : bp.spx >= 40 ? 'NEUTRAL' : 'BEARISH' } : null} />
        <ValueCard label="$BPNDX — Nasdaq 100 BP" data={bp.ndx != null ? { value: bp.ndx, change: 0, signal: bp.ndx >= 60 ? 'BULLISH' : bp.ndx >= 40 ? 'NEUTRAL' : 'BEARISH' } : null} />
      </div>

      {/* Section 5: Sentiment & Sector BP */}
      <h2 className="text-lg font-bold mb-3" style={{ color: COLORS.text }}>Sentiment & Sector Bullish %</h2>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="space-y-4">
          <ValueCard label="$CPC — Put/Call Ratio" data={sent.cpc} />
          <ValueCard label="$TRIN — Arms Index" data={sent.trin} />
          <ValueCard label="$VIX — Volatility Index" data={sent.vix} />
        </div>
        <div className="lg:col-span-2">
          <SectorChart sectors={bp.sectors} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/BreadthPage.jsx
git commit -m "feat: implement full BreadthPage with 5 sections"
```

---

### Task 8: RegimePage Compact Breadth Row & Cleanup

**Files:**
- Modify: `frontend/src/pages/RegimePage.jsx`
- Delete: `frontend/src/components/BreadthGauge.jsx`

- [ ] **Step 1: Replace BreadthGauge with compact summary row**

Replace the entire content of `frontend/src/pages/RegimePage.jsx` with:

```jsx
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useRegime } from '../RegimeContext'
import { getBreadth } from '../api'
import RegimeBadge from '../components/RegimeBadge'
import EarningsCalendar from '../components/EarningsCalendar'

function DirectionCard({ data }) {
  if (!data) return null
  return (
    <div className="bg-white rounded-lg border p-5" style={{ borderColor: '#e2e4e8' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-lg" style={{ color: '#1a1a2e' }}>{data.ticker}</span>
        <span className="text-sm font-medium px-2 py-0.5 rounded" style={{
          backgroundColor: data.direction?.includes('UPTREND') ? '#dcfce7' : data.direction?.includes('DOWNTREND') ? '#fef2f2' : '#fef9c3',
          color: data.direction?.includes('UPTREND') ? '#00a562' : data.direction?.includes('DOWNTREND') ? '#e5484d' : '#d97b0e',
        }}>
          {(data.direction || 'UNKNOWN').replace(/_/g, ' ')}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span style={{ color: '#6b7280' }}>Price</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.price?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>EMA 20</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.ema20?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>SMA 50</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.sma50?.toFixed(2)}</div>
        </div>
        <div>
          <span style={{ color: '#6b7280' }}>SMA 200</span>
          <div className="font-semibold" style={{ color: '#1a1a2e' }}>${data.sma200?.toFixed(2)}</div>
        </div>
      </div>
    </div>
  )
}

function BreadthSummaryRow() {
  const [breadth, setBreadth] = useState(null)

  useEffect(() => {
    getBreadth().then(setBreadth).catch(() => {})
  }, [])

  if (!breadth) return null

  const verdictColor = breadth.verdict === 'RISK-ON' ? '#00a562' : breadth.verdict === 'RISK-OFF' ? '#e5484d' : '#d97b0e'
  const nysi = breadth.mcclellan?.nysi?.value
  const bpspx = breadth.bullish_pct?.spx
  const pct200 = breadth.spx_breadth?.pct_above_200d

  return (
    <div className="mt-6 mb-6">
      <div className="bg-white rounded-lg border p-4 flex items-center gap-4 flex-wrap" style={{ borderColor: '#e2e4e8' }}>
        <span className="text-sm font-bold px-3 py-1 rounded" style={{
          backgroundColor: verdictColor + '20',
          color: verdictColor,
        }}>
          {breadth.verdict} {breadth.score}/10
        </span>
        <div className="flex gap-3 text-sm flex-1" style={{ color: '#6b7280' }}>
          <span>S&P {pct200 != null ? `${pct200}%` : '—'} above 200d</span>
          <span>·</span>
          <span>$NYSI {nysi != null ? nysi.toLocaleString() : '—'}</span>
          <span>·</span>
          <span>$BPSPX {bpspx != null ? `${bpspx}%` : '—'}</span>
        </div>
        <Link to="/breadth" className="text-sm font-medium" style={{ color: '#00a562' }}>
          View full breadth →
        </Link>
      </div>
    </div>
  )
}

export default function RegimePage() {
  const { data, loading, error } = useRegime()

  if (loading) return <div className="p-8" style={{ color: '#6b7280' }}>Loading regime data...</div>
  if (!data) return (
    <div className="p-8" style={{ color: '#e5484d' }}>
      Failed to load regime data.{error && ` (${error})`}
    </div>
  )

  const { spy, qqq, regime } = data

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6" style={{ color: '#1a1a2e' }}>Market Regime — Gate 0</h1>

      <div className="bg-white rounded-lg border p-6 mb-6" style={{ borderColor: '#e2e4e8' }}>
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-medium mb-1" style={{ color: '#6b7280' }}>Current Verdict</div>
            <RegimeBadge verdict={regime.verdict} vix={regime.vix} />
          </div>
          <div className="text-right">
            <div className="text-sm" style={{ color: '#6b7280' }}>Max New Positions</div>
            <div className="text-2xl font-bold" style={{ color: '#1a1a2e' }}>{regime.max_new_positions}</div>
          </div>
        </div>
        <div className="text-sm p-3 rounded" style={{ backgroundColor: '#f7f8fa', color: '#1a1a2e' }}>
          {regime.options_note}
        </div>
        {regime.vix_tax && regime.vix_tax.premium_premium_pct > 0 && (
          <div className="text-sm mt-3 p-3 rounded" style={{ backgroundColor: '#fef9c3', color: '#d97b0e' }}>
            VIX Tax: Premiums ~{regime.vix_tax.premium_premium_pct}% above normal. {regime.vix_tax.note}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DirectionCard data={spy} />
        <DirectionCard data={qqq} />
      </div>

      <BreadthSummaryRow />

      <EarningsCalendar />
    </div>
  )
}
```

- [ ] **Step 2: Delete BreadthGauge.jsx**

```bash
rm frontend/src/components/BreadthGauge.jsx
```

- [ ] **Step 3: Verify no remaining BreadthGauge imports**

Search for any remaining references:
```bash
grep -r "BreadthGauge" frontend/src/
```
Expected: no results.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/RegimePage.jsx
git rm frontend/src/components/BreadthGauge.jsx
git commit -m "feat: replace BreadthGauge with compact summary row on RegimePage"
```

---

### Task 9: Build & Smoke Test

- [ ] **Step 1: Run all backend tests**

```bash
cd stock-analysis-system && python -m pytest tests/test_breadth.py -v
```
Expected: all 12 tests pass.

- [ ] **Step 2: Run full test suite to check no regressions**

```bash
cd stock-analysis-system && python -m pytest tests/ -v
```
Expected: all tests pass (existing test_regime.py tests still pass).

- [ ] **Step 3: Build frontend**

```bash
cd stock-analysis-system/frontend && npm run build
```
Expected: build succeeds with no errors.

- [ ] **Step 4: Start the server and verify manually**

```bash
cd stock-analysis-system && uvicorn backend.main:app --reload
```

Verify:
- `http://localhost:8000/api/breadth` returns JSON with score, verdict, all sections
- `http://localhost:8000/` shows RegimePage with compact breadth row (not the old gauge)
- `http://localhost:8000/breadth` shows full BreadthPage with all 5 sections
- Navbar shows Breadth tab between Options and Watchlist

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: breadth page build verification"
```
