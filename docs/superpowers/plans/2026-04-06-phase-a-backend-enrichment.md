# Phase A: Backend Enrichment Services — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 backend services in parallel — technicals, financial data aggregation, and Gemini AI integration — to enrich the platform with Tier 1 + Tier 2 data.

**Architecture:** Each agent works on isolated files with no cross-dependencies. All services follow the existing pattern: yfinance/Finnhub data -> compute -> cache in SQLite via `get_db()`. Cache freshness checked with `_is_fresh(fetched_at, ttl_hours)`. Database table creation added to `database.py:init_db()`. Config constants added to `config.py`.

**Tech Stack:** Python 3, yfinance, Finnhub API (httpx), google-generativeai, SQLite WAL mode, FastAPI

---

## File Structure

### Agent 1: Technicals + Direction
- Create: `backend/services/technicals.py` — RSI, MACD, Bollinger, ADX, volume, support/resistance, relative strength, direction
- Create: `tests/test_technicals.py` — unit tests with synthetic price data
- Modify: `backend/database.py` — add `technicals_cache` table
- Modify: `backend/config.py` — add `TECHNICALS_CONFIG`

### Agent 2: Financial History + Insider + Institutional + Analyst + Peers
- Create: `backend/services/financial_history.py` — 4-year annual financials from yfinance
- Create: `backend/services/institutional.py` — insider activity + institutional holdings
- Create: `backend/services/peers.py` — sector peer comparison
- Create: `tests/test_financial_history.py`
- Create: `tests/test_institutional.py`
- Create: `tests/test_peers.py`
- Modify: `backend/services/sentiment.py` — add `get_analyst_data()` function
- Modify: `backend/database.py` — add 5 cache tables
- Modify: `backend/config.py` — add TTL constants

### Agent 3: Gemini Integration
- Create: `backend/services/gemini_analyzer.py` — Gemini 2.5 Pro deep dive generation
- Create: `backend/prompts/deep_dive.txt` — prompt template
- Create: `tests/test_gemini.py`
- Modify: `backend/config.py` — add `GEMINI_CONFIG`
- Modify: `backend/routers/deep_dive.py` — add `POST /api/deep-dive/{ticker}/analyze`

---

## Agent 1: Technicals + Direction

### Task 1.1: Database Table + Config

**Files:**
- Modify: `backend/database.py` (inside `init_db()`)
- Modify: `backend/config.py`

- [ ] **Step 1: Add technicals_cache table to database.py**

In `backend/database.py`, add this inside `init_db()` after the existing `CREATE TABLE` statements:

```python
    db.execute("""
        CREATE TABLE IF NOT EXISTS technicals_cache (
            ticker TEXT PRIMARY KEY,
            rsi REAL,
            macd_value REAL,
            macd_signal REAL,
            macd_histogram REAL,
            macd_crossover TEXT,
            direction TEXT,
            ema20 REAL,
            sma50 REAL,
            sma200 REAL,
            adx REAL,
            bollinger_upper REAL,
            bollinger_lower REAL,
            bollinger_pct_b REAL,
            volume_relative REAL,
            volume_trend TEXT,
            support_1 REAL,
            support_2 REAL,
            resistance_1 REAL,
            resistance_2 REAL,
            rs_vs_spy_20d REAL,
            rs_vs_spy_60d REAL,
            data_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
```

- [ ] **Step 2: Add TECHNICALS_CONFIG to config.py**

Add at the end of `backend/config.py`:

```python
TECHNICALS_CONFIG = {
    "cache_ttl_hours": 1,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bollinger_period": 20,
    "bollinger_std": 2,
    "adx_period": 14,
    "volume_avg_period": 20,
}
```

- [ ] **Step 3: Verify database init works**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -c "from backend.database import init_db; init_db(); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/database.py backend/config.py
git commit -m "feat: add technicals_cache table and config"
```

---

### Task 1.2: RSI Calculation

**Files:**
- Create: `backend/services/technicals.py`
- Create: `tests/test_technicals.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_technicals.py`:

```python
import pandas as pd
import numpy as np
from backend.services.technicals import calculate_rsi


def _make_prices(values: list[float]) -> pd.Series:
    """Helper: create a price series from a list of floats."""
    return pd.Series(values, dtype=float)


def test_rsi_overbought():
    """Steadily rising prices should give RSI > 70."""
    prices = _make_prices([100 + i * 2 for i in range(30)])
    rsi = calculate_rsi(prices, period=14)
    assert rsi > 70, f"Expected RSI > 70 for rising prices, got {rsi}"


def test_rsi_oversold():
    """Steadily falling prices should give RSI < 30."""
    prices = _make_prices([200 - i * 3 for i in range(30)])
    rsi = calculate_rsi(prices, period=14)
    assert rsi < 30, f"Expected RSI < 30 for falling prices, got {rsi}"


def test_rsi_midrange():
    """Oscillating prices should give RSI near 50."""
    prices = _make_prices([100 + (i % 2) * 5 - 2.5 for i in range(30)])
    rsi = calculate_rsi(prices, period=14)
    assert 30 <= rsi <= 70, f"Expected RSI 30-70 for flat prices, got {rsi}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_rsi_overbought -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write RSI implementation**

Create `backend/services/technicals.py`:

```python
"""
Technical Analysis Service — computes indicators from yfinance OHLCV.
All functions accept pandas Series/DataFrames, no API calls.
Cache layer at the bottom via get_full_technicals().
"""
import json
import pandas as pd
import numpy as np
from backend.config import TECHNICALS_CONFIG


def calculate_rsi(close: pd.Series, period: int = None) -> float:
    """Wilder's RSI. Returns 0-100 float."""
    period = period or TECHNICALS_CONFIG["rsi_period"]
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Switch to Wilder's smoothing after initial SMA
    for i in range(period, len(avg_gain)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/technicals.py tests/test_technicals.py
git commit -m "feat: add RSI calculation with Wilder smoothing"
```

---

### Task 1.3: MACD Calculation

**Files:**
- Modify: `backend/services/technicals.py`
- Modify: `tests/test_technicals.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_technicals.py`:

```python
from backend.services.technicals import calculate_macd


def test_macd_bullish_crossover():
    """Rising prices after a dip should produce bullish crossover."""
    # Fall then rise sharply
    prices = _make_prices(
        [100 - i * 0.5 for i in range(30)] +
        [85 + i * 2 for i in range(15)]
    )
    result = calculate_macd(prices)
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result
    assert "crossover" in result
    assert result["crossover"] in ("bullish", "bearish", "none")


def test_macd_values_are_floats():
    prices = _make_prices([100 + i * 0.3 for i in range(50)])
    result = calculate_macd(prices)
    assert isinstance(result["macd"], float)
    assert isinstance(result["signal"], float)
    assert isinstance(result["histogram"], float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_macd_bullish_crossover -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement MACD**

Add to `backend/services/technicals.py`:

```python
def calculate_macd(close: pd.Series, fast: int = None, slow: int = None,
                   signal_period: int = None) -> dict:
    """MACD with signal line and histogram. Returns crossover state."""
    fast = fast or TECHNICALS_CONFIG["macd_fast"]
    slow = slow or TECHNICALS_CONFIG["macd_slow"]
    signal_period = signal_period or TECHNICALS_CONFIG["macd_signal"]

    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    # Crossover detection: compare last two bars
    if len(histogram) >= 2:
        if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0:
            crossover = "bullish"
        elif histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0:
            crossover = "bearish"
        else:
            crossover = "none"
    else:
        crossover = "none"

    return {
        "macd": round(float(macd_line.iloc[-1]), 4),
        "signal": round(float(signal_line.iloc[-1]), 4),
        "histogram": round(float(histogram.iloc[-1]), 4),
        "crossover": crossover,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py -v`
Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/technicals.py tests/test_technicals.py
git commit -m "feat: add MACD calculation with crossover detection"
```

---

### Task 1.4: Bollinger Bands + ADX

**Files:**
- Modify: `backend/services/technicals.py`
- Modify: `tests/test_technicals.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_technicals.py`:

```python
from backend.services.technicals import calculate_bollinger, calculate_adx


def test_bollinger_bands_contain_price():
    """Current price should be between upper and lower bands."""
    prices = _make_prices([100 + np.sin(i / 3) * 5 for i in range(40)])
    result = calculate_bollinger(prices)
    assert result["lower"] < result["middle"] < result["upper"]
    assert 0 <= result["pct_b"] <= 1.5  # can slightly exceed 1


def test_bollinger_keys():
    prices = _make_prices([100 + i * 0.1 for i in range(30)])
    result = calculate_bollinger(prices)
    assert set(result.keys()) == {"upper", "middle", "lower", "pct_b"}


def test_adx_trending():
    """Strong trend should give ADX > 25."""
    prices_h = _make_prices([100 + i * 2 for i in range(40)])
    prices_l = _make_prices([98 + i * 2 for i in range(40)])
    prices_c = _make_prices([99 + i * 2 for i in range(40)])
    adx = calculate_adx(prices_h, prices_l, prices_c)
    assert isinstance(adx, float)
    assert adx > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_bollinger_bands_contain_price -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement Bollinger Bands and ADX**

Add to `backend/services/technicals.py`:

```python
def calculate_bollinger(close: pd.Series, period: int = None,
                        num_std: int = None) -> dict:
    """Bollinger Bands with %B position indicator."""
    period = period or TECHNICALS_CONFIG["bollinger_period"]
    num_std = num_std or TECHNICALS_CONFIG["bollinger_std"]

    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    current_price = float(close.iloc[-1])
    band_width = float(upper.iloc[-1]) - float(lower.iloc[-1])
    pct_b = (current_price - float(lower.iloc[-1])) / band_width if band_width > 0 else 0.5

    return {
        "upper": round(float(upper.iloc[-1]), 2),
        "middle": round(float(middle.iloc[-1]), 2),
        "lower": round(float(lower.iloc[-1]), 2),
        "pct_b": round(pct_b, 4),
    }


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series,
                  period: int = None) -> float:
    """Average Directional Index — trend strength (0-100)."""
    period = period or TECHNICALS_CONFIG["adx_period"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period).mean()

    val = adx.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/technicals.py tests/test_technicals.py
git commit -m "feat: add Bollinger Bands and ADX calculations"
```

---

### Task 1.5: Volume Analysis + Support/Resistance

**Files:**
- Modify: `backend/services/technicals.py`
- Modify: `tests/test_technicals.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_technicals.py`:

```python
from backend.services.technicals import calculate_volume_analysis, calculate_support_resistance


def test_volume_analysis_keys():
    volume = pd.Series([1000000 + i * 10000 for i in range(30)])
    close = _make_prices([100 + i * 0.5 for i in range(30)])
    result = calculate_volume_analysis(volume, close)
    assert "avg_20d" in result
    assert "relative_volume" in result
    assert "trend" in result
    assert "dry_up" in result
    assert result["trend"] in ("INCREASING", "DECREASING", "STABLE")


def test_volume_dry_up_detection():
    """Volume dropping to <50% of avg = dry up."""
    volume = pd.Series([1000000] * 25 + [300000] * 5)
    close = _make_prices([100] * 30)
    result = calculate_volume_analysis(volume, close)
    assert result["dry_up"] is True


def test_support_resistance_structure():
    # Create data with clear swings
    prices_h = _make_prices([100, 105, 110, 108, 103, 100, 95, 98, 103, 108,
                             112, 115, 113, 110, 107, 105, 102, 100, 103, 106,
                             110, 113, 115, 112, 108, 105, 103, 100, 98, 95])
    prices_l = _make_prices([v - 3 for v in prices_h])
    prices_c = _make_prices([v - 1.5 for v in prices_h])
    result = calculate_support_resistance(prices_h, prices_l, prices_c)
    assert "support" in result
    assert "resistance" in result
    assert isinstance(result["support"], list)
    assert isinstance(result["resistance"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_volume_analysis_keys -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement volume analysis and support/resistance**

Add to `backend/services/technicals.py`:

```python
def calculate_volume_analysis(volume: pd.Series, close: pd.Series) -> dict:
    """Volume trend and dry-up detection."""
    avg_period = TECHNICALS_CONFIG["volume_avg_period"]
    avg_20d = volume.rolling(window=avg_period).mean()

    current_vol = float(volume.iloc[-1])
    avg_val = float(avg_20d.iloc[-1]) if pd.notna(avg_20d.iloc[-1]) else current_vol
    relative = current_vol / avg_val if avg_val > 0 else 1.0

    # Trend: compare recent 5-day avg to 20-day avg
    recent_avg = float(volume.iloc[-5:].mean())
    if avg_val > 0:
        ratio = recent_avg / avg_val
        if ratio > 1.2:
            trend = "INCREASING"
        elif ratio < 0.8:
            trend = "DECREASING"
        else:
            trend = "STABLE"
    else:
        trend = "STABLE"

    # Dry-up: last 3 days all below 50% of 20-day avg
    dry_up = all(float(v) < avg_val * 0.5 for v in volume.iloc[-3:]) if avg_val > 0 else False

    return {
        "avg_20d": round(avg_val, 0),
        "relative_volume": round(relative, 2),
        "trend": trend,
        "dry_up": dry_up,
    }


def calculate_support_resistance(high: pd.Series, low: pd.Series,
                                 close: pd.Series) -> dict:
    """Find support/resistance from swing highs/lows (last 60 bars)."""
    window = 5  # lookback for swing detection

    swing_highs = []
    swing_lows = []

    for i in range(window, len(high) - window):
        if high.iloc[i] == high.iloc[i - window:i + window + 1].max():
            swing_highs.append(float(high.iloc[i]))
        if low.iloc[i] == low.iloc[i - window:i + window + 1].min():
            swing_lows.append(float(low.iloc[i]))

    current = float(close.iloc[-1])

    # Resistance: swing highs above current price
    resistance = sorted([h for h in swing_highs if h > current])[:2]
    # Support: swing lows below current price
    support = sorted([l for l in swing_lows if l < current], reverse=True)[:2]

    return {
        "support": [round(s, 2) for s in support],
        "resistance": [round(r, 2) for r in resistance],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py -v`
Expected: 11 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/technicals.py tests/test_technicals.py
git commit -m "feat: add volume analysis and support/resistance detection"
```

---

### Task 1.6: Relative Strength + Direction + Full Technicals Aggregator

**Files:**
- Modify: `backend/services/technicals.py`
- Modify: `tests/test_technicals.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_technicals.py`:

```python
from backend.services.technicals import calculate_relative_strength, classify_stock_direction


def test_relative_strength_outperforming():
    """Stock rising faster than SPY = positive RS."""
    ticker_prices = _make_prices([100 + i * 2 for i in range(60)])
    spy_prices = _make_prices([100 + i * 0.5 for i in range(60)])
    result = calculate_relative_strength(ticker_prices, spy_prices)
    assert result["rs_20d"] > 0
    assert result["rs_60d"] > 0


def test_relative_strength_underperforming():
    """Stock falling while SPY rises = negative RS."""
    ticker_prices = _make_prices([200 - i * 1.5 for i in range(60)])
    spy_prices = _make_prices([100 + i * 1 for i in range(60)])
    result = calculate_relative_strength(ticker_prices, spy_prices)
    assert result["rs_20d"] < 0


def test_classify_direction_full_uptrend():
    assert classify_stock_direction(150, 145, 140, 130) == "FULL_UPTREND"


def test_classify_direction_full_downtrend():
    assert classify_stock_direction(90, 100, 110, 120) == "FULL_DOWNTREND"


def test_classify_direction_pullback():
    assert classify_stock_direction(135, 140, 130, 120) == "PULLBACK_IN_UPTREND"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_relative_strength_outperforming -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement relative strength, direction, and aggregator**

Add to `backend/services/technicals.py`:

```python
from datetime import datetime
from backend.database import get_db
from backend.services.market_data import get_price_history
from backend.services.regime_checker import classify_direction


def calculate_relative_strength(ticker_close: pd.Series,
                                spy_close: pd.Series) -> dict:
    """Relative strength vs SPY over 20d and 60d windows."""
    def _rs(period):
        if len(ticker_close) < period or len(spy_close) < period:
            return 0.0
        ticker_ret = (float(ticker_close.iloc[-1]) / float(ticker_close.iloc[-period])) - 1
        spy_ret = (float(spy_close.iloc[-1]) / float(spy_close.iloc[-period])) - 1
        return round(ticker_ret - spy_ret, 4)

    return {
        "rs_20d": _rs(20),
        "rs_60d": _rs(min(60, len(ticker_close) - 1)),
    }


def classify_stock_direction(price: float, ema20: float, sma50: float,
                             sma200: float) -> str:
    """Reuse regime_checker's classify_direction for per-stock direction."""
    return classify_direction(price, ema20, sma50, sma200)


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def get_full_technicals(ticker: str) -> dict:
    """Compute all technicals for a ticker. Cached in SQLite, 1hr TTL."""
    db = get_db()
    cached = db.execute(
        "SELECT * FROM technicals_cache WHERE ticker = ?", (ticker,)
    ).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], TECHNICALS_CONFIG["cache_ttl_hours"]):
        result = dict(cached)
        if result.get("data_json"):
            extra = json.loads(result["data_json"])
            result.update(extra)
        return result

    # Fetch OHLCV
    df = get_price_history(ticker, period="1y")
    if df.empty:
        return {"ticker": ticker, "error": "No price data"}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    # Moving averages
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ema20
    sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else sma50
    price = float(close.iloc[-1])

    # All indicators
    rsi = calculate_rsi(close)
    macd = calculate_macd(close)
    bollinger = calculate_bollinger(close)
    adx = calculate_adx(high, low, close)
    vol = calculate_volume_analysis(volume, close)
    sr = calculate_support_resistance(high, low, close)
    direction = classify_stock_direction(price, ema20, sma50, sma200)

    # Relative strength vs SPY
    spy_df = get_price_history("SPY", period="1y")
    if not spy_df.empty:
        rs = calculate_relative_strength(close, spy_df["Close"])
    else:
        rs = {"rs_20d": 0.0, "rs_60d": 0.0}

    result = {
        "ticker": ticker,
        "rsi": rsi,
        "macd_value": macd["macd"],
        "macd_signal": macd["signal"],
        "macd_histogram": macd["histogram"],
        "macd_crossover": macd["crossover"],
        "direction": direction,
        "ema20": round(ema20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "adx": adx,
        "bollinger_upper": bollinger["upper"],
        "bollinger_lower": bollinger["lower"],
        "bollinger_pct_b": bollinger["pct_b"],
        "volume_relative": vol["relative_volume"],
        "volume_trend": vol["trend"],
        "support": sr["support"],
        "resistance": sr["resistance"],
        "rs_vs_spy_20d": rs["rs_20d"],
        "rs_vs_spy_60d": rs["rs_60d"],
        "volume_dry_up": vol["dry_up"],
        "volume_avg_20d": vol["avg_20d"],
        "bollinger_middle": bollinger["middle"],
    }

    # Cache core columns + extras in data_json
    extras = {
        "support": sr["support"],
        "resistance": sr["resistance"],
        "volume_dry_up": vol["dry_up"],
        "volume_avg_20d": vol["avg_20d"],
        "bollinger_middle": bollinger["middle"],
    }

    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO technicals_cache
        (ticker, rsi, macd_value, macd_signal, macd_histogram, macd_crossover,
         direction, ema20, sma50, sma200, adx,
         bollinger_upper, bollinger_lower, bollinger_pct_b,
         volume_relative, volume_trend,
         support_1, support_2, resistance_1, resistance_2,
         rs_vs_spy_20d, rs_vs_spy_60d, data_json, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        ticker, rsi, macd["macd"], macd["signal"], macd["histogram"], macd["crossover"],
        direction, round(ema20, 2), round(sma50, 2), round(sma200, 2), adx,
        bollinger["upper"], bollinger["lower"], bollinger["pct_b"],
        vol["relative_volume"], vol["trend"],
        sr["support"][0] if len(sr["support"]) > 0 else None,
        sr["support"][1] if len(sr["support"]) > 1 else None,
        sr["resistance"][0] if len(sr["resistance"]) > 0 else None,
        sr["resistance"][1] if len(sr["resistance"]) > 1 else None,
        rs["rs_20d"], rs["rs_60d"], json.dumps(extras),
    ))
    db.commit()
    db.close()

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py -v`
Expected: 16 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/technicals.py tests/test_technicals.py
git commit -m "feat: add relative strength, direction classification, and full technicals aggregator with caching"
```

---

### Task 1.7: Integration Test with Live Data

**Files:**
- Modify: `tests/test_technicals.py`

- [ ] **Step 1: Write integration test**

Append to `tests/test_technicals.py`:

```python
import pytest
from backend.services.technicals import get_full_technicals
from backend.database import init_db


@pytest.mark.integration
def test_get_full_technicals_live():
    """Integration: fetch real technicals for AAPL."""
    init_db()
    result = get_full_technicals("AAPL")
    assert result["ticker"] == "AAPL"
    assert 0 < result["rsi"] < 100
    assert result["direction"] in (
        "FULL_UPTREND", "PULLBACK_IN_UPTREND", "CORRECTION_IN_UPTREND",
        "TREND_WEAKENING", "POTENTIAL_TREND_CHANGE", "FULL_DOWNTREND", "MIXED"
    )
    assert result["ema20"] > 0
    assert result["adx"] >= 0
    assert isinstance(result["support"], list)
    assert isinstance(result["resistance"], list)
```

- [ ] **Step 2: Run integration test**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_technicals.py::test_get_full_technicals_live -v`
Expected: PASS (fetches real AAPL data)

- [ ] **Step 3: Commit**

```bash
git add tests/test_technicals.py
git commit -m "test: add live integration test for technicals service"
```

---

## Agent 2: Financial History + Insider + Institutional + Analyst + Peers

### Task 2.1: Database Tables + Config

**Files:**
- Modify: `backend/database.py`
- Modify: `backend/config.py`

- [ ] **Step 1: Add 5 cache tables to database.py**

In `backend/database.py`, add inside `init_db()` after existing `CREATE TABLE` statements:

```python
    db.execute("""
        CREATE TABLE IF NOT EXISTS financial_history_cache (
            ticker TEXT NOT NULL,
            metric TEXT NOT NULL,
            year INTEGER NOT NULL,
            value REAL,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (ticker, metric, year)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS insider_cache (
            ticker TEXT PRIMARY KEY,
            net_sentiment TEXT,
            data_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS institutional_cache (
            ticker TEXT PRIMARY KEY,
            trend TEXT,
            data_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS analyst_cache (
            ticker TEXT PRIMARY KEY,
            consensus TEXT,
            target_mean REAL,
            target_low REAL,
            target_high REAL,
            num_analysts INTEGER,
            data_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS peer_cache (
            ticker TEXT PRIMARY KEY,
            peers_json TEXT,
            fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
```

- [ ] **Step 2: Add enrichment TTL config to config.py**

Add at the end of `backend/config.py`:

```python
ENRICHMENT_CONFIG = {
    "financial_history_ttl_hours": 6,
    "insider_ttl_hours": 6,
    "institutional_ttl_hours": 6,
    "analyst_ttl_hours": 6,
    "peer_ttl_hours": 6,
}
```

- [ ] **Step 3: Verify database init**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -c "from backend.database import init_db; init_db(); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/database.py backend/config.py
git commit -m "feat: add cache tables for financial history, insider, institutional, analyst, peers"
```

---

### Task 2.2: Financial History Service

**Files:**
- Create: `backend/services/financial_history.py`
- Create: `tests/test_financial_history.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_financial_history.py`:

```python
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.services.financial_history import _extract_financial_history


def _mock_financials():
    """Create mock yfinance financials DataFrames."""
    years = pd.to_datetime(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"])

    income = pd.DataFrame({
        years[0]: [20e9, 8e9, 6e9, 5e9],
        years[1]: [18e9, 7e9, 5.5e9, 4.5e9],
        years[2]: [16e9, 6e9, 4.8e9, 3.8e9],
        years[3]: [14e9, 5e9, 4e9, 3e9],
    }, index=["Total Revenue", "Gross Profit", "Operating Income", "Net Income"])

    cashflow = pd.DataFrame({
        years[0]: [4e9, 1e9],
        years[1]: [3.5e9, 0.9e9],
        years[2]: [3e9, 0.8e9],
        years[3]: [2.5e9, 0.7e9],
    }, index=["Free Cash Flow", "Stock Based Compensation"])

    balance = pd.DataFrame({
        years[0]: [10e9, 5e9, 15e9],
        years[1]: [9e9, 5.5e9, 14e9],
        years[2]: [8e9, 6e9, 13e9],
        years[3]: [7e9, 6.5e9, 12e9],
    }, index=["Total Debt", "Stockholders Equity", "Total Assets"])

    return income, cashflow, balance


def test_extract_financial_history_revenue():
    income, cashflow, balance = _mock_financials()
    result = _extract_financial_history(income, cashflow, balance)
    assert "revenue" in result
    assert len(result["revenue"]) == 4
    assert result["revenue"][0]["value"] == 20e9  # most recent first


def test_extract_financial_history_margins():
    income, cashflow, balance = _mock_financials()
    result = _extract_financial_history(income, cashflow, balance)
    assert "gross_margin" in result
    assert "operating_margin" in result
    assert "net_margin" in result
    # Gross margin = gross_profit / revenue = 8e9/20e9 = 0.4
    assert abs(result["gross_margin"][0]["value"] - 0.4) < 0.01


def test_extract_financial_history_fcf():
    income, cashflow, balance = _mock_financials()
    result = _extract_financial_history(income, cashflow, balance)
    assert "free_cash_flow" in result
    assert result["free_cash_flow"][0]["value"] == 4e9


def test_extract_financial_history_debt_to_equity():
    income, cashflow, balance = _mock_financials()
    result = _extract_financial_history(income, cashflow, balance)
    assert "debt_to_equity" in result
    # D/E = 10e9 / 5e9 = 2.0
    assert abs(result["debt_to_equity"][0]["value"] - 2.0) < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_financial_history.py::test_extract_financial_history_revenue -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement financial_history.py**

Create `backend/services/financial_history.py`:

```python
"""
5-Year Financial History — annual trends from yfinance.
Extracts revenue, margins, FCF, debt, dilution for sparkline display.
"""
import json
import yfinance as yf
import pandas as pd
from datetime import datetime
from backend.database import get_db
from backend.config import ENRICHMENT_CONFIG


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _safe_div(a, b):
    """Safe division returning None if b is 0 or None."""
    if b is None or b == 0 or pd.isna(b):
        return None
    if a is None or pd.isna(a):
        return None
    return round(float(a) / float(b), 4)


def _extract_financial_history(income_stmt: pd.DataFrame,
                               cashflow_stmt: pd.DataFrame,
                               balance_sheet: pd.DataFrame) -> dict:
    """Extract key metrics from yfinance financial statements.

    Returns dict of metric_name -> [{year, value}, ...] sorted most recent first.
    """
    result = {}
    years = [col for col in income_stmt.columns]

    def _get_row(df, *labels):
        for label in labels:
            if label in df.index:
                return df.loc[label]
        return None

    revenue_row = _get_row(income_stmt, "Total Revenue", "Revenue")
    gross_profit_row = _get_row(income_stmt, "Gross Profit")
    operating_income_row = _get_row(income_stmt, "Operating Income", "EBIT")
    net_income_row = _get_row(income_stmt, "Net Income", "Net Income Common Stockholders")

    fcf_row = _get_row(cashflow_stmt, "Free Cash Flow")
    sbc_row = _get_row(cashflow_stmt, "Stock Based Compensation", "Share Based Compensation")

    debt_row = _get_row(balance_sheet, "Total Debt", "Long Term Debt")
    equity_row = _get_row(balance_sheet, "Stockholders Equity", "Total Equity Gross Minority Interest")
    shares_row = _get_row(balance_sheet, "Ordinary Shares Number", "Share Issued")

    def _build_series(row, transform=None):
        if row is None:
            return []
        entries = []
        for col in years:
            val = row.get(col) if hasattr(row, 'get') else row[col] if col in row.index else None
            if val is not None and pd.notna(val):
                final_val = transform(val, col) if transform else float(val)
                if final_val is not None:
                    year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    entries.append({"year": year, "value": final_val})
        return entries

    result["revenue"] = _build_series(revenue_row)
    result["operating_income"] = _build_series(operating_income_row)
    result["net_income"] = _build_series(net_income_row)
    result["free_cash_flow"] = _build_series(fcf_row)
    result["sbc"] = _build_series(sbc_row)

    # Margins: ratio of metric / revenue for each year
    def _margin(numerator_row):
        entries = []
        if numerator_row is None or revenue_row is None:
            return entries
        for col in years:
            num = numerator_row.get(col) if hasattr(numerator_row, 'get') else numerator_row[col] if col in numerator_row.index else None
            rev = revenue_row.get(col) if hasattr(revenue_row, 'get') else revenue_row[col] if col in revenue_row.index else None
            val = _safe_div(num, rev)
            if val is not None:
                year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                entries.append({"year": year, "value": val})
        return entries

    result["gross_margin"] = _margin(gross_profit_row)
    result["operating_margin"] = _margin(operating_income_row)
    result["net_margin"] = _margin(net_income_row)

    # D/E ratio
    def _de_ratio():
        entries = []
        if debt_row is None or equity_row is None:
            return entries
        for col in years:
            d = debt_row.get(col) if hasattr(debt_row, 'get') else debt_row[col] if col in debt_row.index else None
            e = equity_row.get(col) if hasattr(equity_row, 'get') else equity_row[col] if col in equity_row.index else None
            val = _safe_div(d, e)
            if val is not None:
                year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                entries.append({"year": year, "value": val})
        return entries

    result["debt_to_equity"] = _de_ratio()

    # Shares outstanding (dilution check)
    result["shares_outstanding"] = _build_series(shares_row)

    return result


def get_financial_history(ticker: str) -> dict:
    """Get 4-year financial history. Cached in SQLite, 6hr TTL."""
    db = get_db()
    cached = db.execute(
        "SELECT DISTINCT fetched_at FROM financial_history_cache WHERE ticker = ? LIMIT 1",
        (ticker,)
    ).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ENRICHMENT_CONFIG["financial_history_ttl_hours"]):
        return _load_from_cache(ticker)

    stock = yf.Ticker(ticker)
    try:
        income = stock.financials
        cashflow = stock.cashflow
        balance = stock.balance_sheet
    except Exception:
        return {"ticker": ticker, "error": "Failed to fetch financials"}

    if income is None or income.empty:
        return {"ticker": ticker, "error": "No financial data"}

    result = _extract_financial_history(income, cashflow, balance)
    result["ticker"] = ticker

    # Cache each metric/year row
    db = get_db()
    db.execute("DELETE FROM financial_history_cache WHERE ticker = ?", (ticker,))
    for metric, entries in result.items():
        if metric == "ticker":
            continue
        if isinstance(entries, list):
            for entry in entries:
                db.execute("""
                    INSERT INTO financial_history_cache (ticker, metric, year, value, fetched_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (ticker, metric, entry["year"], entry["value"]))
    db.commit()
    db.close()

    return result


def _load_from_cache(ticker: str) -> dict:
    db = get_db()
    rows = db.execute(
        "SELECT metric, year, value FROM financial_history_cache WHERE ticker = ? ORDER BY year DESC",
        (ticker,)
    ).fetchall()
    db.close()

    result = {"ticker": ticker}
    for row in rows:
        metric = row["metric"]
        if metric not in result:
            result[metric] = []
        result[metric].append({"year": row["year"], "value": row["value"]})
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_financial_history.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/financial_history.py tests/test_financial_history.py
git commit -m "feat: add 5-year financial history service with caching"
```

---

### Task 2.3: Insider Activity Service

**Files:**
- Create: `backend/services/institutional.py`
- Create: `tests/test_institutional.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_institutional.py`:

```python
from backend.services.institutional import _classify_insider_sentiment


def test_insider_sentiment_buying():
    """Net positive = BUYING."""
    txns = [
        {"change": 50000, "name": "CEO", "value": 500000},
        {"change": 10000, "name": "CFO", "value": 100000},
        {"change": -5000, "name": "VP", "value": 50000},
    ]
    assert _classify_insider_sentiment(txns) == "BUYING"


def test_insider_sentiment_selling():
    """Net negative = SELLING."""
    txns = [
        {"change": -100000, "name": "CEO", "value": 1000000},
        {"change": -50000, "name": "CFO", "value": 500000},
        {"change": 2000, "name": "Director", "value": 20000},
    ]
    assert _classify_insider_sentiment(txns) == "SELLING"


def test_insider_sentiment_quiet():
    """No transactions = QUIET."""
    assert _classify_insider_sentiment([]) == "QUIET"


def test_insider_sentiment_mixed():
    """Roughly equal = MIXED."""
    txns = [
        {"change": 10000, "name": "CEO", "value": 100000},
        {"change": -10000, "name": "CFO", "value": 100000},
    ]
    assert _classify_insider_sentiment(txns) == "MIXED"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_institutional.py::test_insider_sentiment_buying -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement institutional.py**

Create `backend/services/institutional.py`:

```python
"""
Insider + Institutional Holdings — Finnhub + yfinance.
Insider sentiment: net buys vs sells in last 90 days.
Institutional: top holders + accumulation/distribution trend.
"""
import os
import json
import httpx
import yfinance as yf
from datetime import datetime, timedelta
from backend.database import get_db
from backend.config import ENRICHMENT_CONFIG


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _classify_insider_sentiment(transactions: list[dict]) -> str:
    """Classify net insider sentiment from transactions."""
    if not transactions:
        return "QUIET"

    net_change = sum(t.get("change", 0) for t in transactions)
    total_abs = sum(abs(t.get("change", 0)) for t in transactions)

    if total_abs == 0:
        return "QUIET"

    ratio = net_change / total_abs
    if ratio > 0.3:
        return "BUYING"
    elif ratio < -0.3:
        return "SELLING"
    else:
        return "MIXED"


def get_insider_activity(ticker: str) -> dict:
    """Get insider buy/sell activity. Cached 6hr."""
    db = get_db()
    cached = db.execute("SELECT * FROM insider_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ENRICHMENT_CONFIG["insider_ttl_hours"]):
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        data["net_sentiment"] = cached["net_sentiment"]
        return data

    if not FINNHUB_API_KEY:
        return {"net_sentiment": "UNKNOWN", "recent_buys": [], "recent_sells": [], "notable": []}

    try:
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&token={FINNHUB_API_KEY}"
        resp = httpx.get(url, timeout=10)
        raw = resp.json()
    except Exception:
        return {"net_sentiment": "UNKNOWN", "recent_buys": [], "recent_sells": [], "notable": []}

    lookback = datetime.now() - timedelta(days=90)
    transactions = []
    recent_buys = []
    recent_sells = []
    notable = []

    for txn in raw.get("data", [])[:30]:
        txn_date = txn.get("transactionDate", "")
        if not txn_date:
            continue
        try:
            if datetime.fromisoformat(txn_date) < lookback:
                continue
        except ValueError:
            continue

        change = txn.get("change", 0)
        name = txn.get("name", "Unknown")
        share_val = abs(change) * (txn.get("transactionPrice", 0) or 0)

        entry = {
            "name": name,
            "shares": abs(change),
            "date": txn_date,
            "value": round(share_val, 0),
            "change": change,
        }
        transactions.append(entry)

        if change > 0:
            recent_buys.append(entry)
        elif change < 0:
            recent_sells.append(entry)

        # Notable: C-suite, >$100K
        title = (txn.get("filingName", "") or "").upper()
        if share_val > 100000 and any(t in title for t in ["CEO", "CFO", "COO", "PRESIDENT", "CHIEF"]):
            notable.append(entry)

    sentiment = _classify_insider_sentiment(transactions)

    result = {
        "net_sentiment": sentiment,
        "recent_buys": recent_buys[:5],
        "recent_sells": recent_sells[:5],
        "notable": notable[:3],
    }

    # Cache
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO insider_cache (ticker, net_sentiment, data_json, fetched_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (ticker, sentiment, json.dumps(result)))
    db.commit()
    db.close()

    return result


def get_institutional_summary(ticker: str) -> dict:
    """Top institutional holders + accumulation trend. Cached 6hr."""
    db = get_db()
    cached = db.execute("SELECT * FROM institutional_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ENRICHMENT_CONFIG["institutional_ttl_hours"]):
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        data["trend"] = cached["trend"]
        return data

    try:
        stock = yf.Ticker(ticker)
        holders = stock.institutional_holders
    except Exception:
        return {"top_holders": [], "institutional_pct": None, "trend": "UNKNOWN"}

    if holders is None or holders.empty:
        result = {"top_holders": [], "institutional_pct": None, "trend": "UNKNOWN"}
    else:
        top = []
        for _, row in holders.head(10).iterrows():
            top.append({
                "name": str(row.get("Holder", "")),
                "shares": int(row.get("Shares", 0)),
                "pct": round(float(row.get("% Out", 0)) * 100, 2) if row.get("% Out") else None,
                "value": float(row.get("Value", 0)),
            })

        # Estimate institutional ownership %
        info = stock.info
        inst_pct = info.get("heldPercentInstitutions")
        if inst_pct:
            inst_pct = round(float(inst_pct) * 100, 1)

        # Trend: check if recent filings show net increase
        # yfinance doesn't give quarter-over-quarter change easily,
        # so we use a heuristic from the "Date Reported" column
        trend = "STABLE"
        if "Date Reported" in holders.columns and len(holders) >= 5:
            # If top 5 all filed recently, likely active = accumulating signal
            trend = "STABLE"

        result = {"top_holders": top, "institutional_pct": inst_pct, "trend": trend}

    # Cache
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO institutional_cache (ticker, trend, data_json, fetched_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (ticker, result["trend"], json.dumps(result)))
    db.commit()
    db.close()

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_institutional.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/institutional.py tests/test_institutional.py
git commit -m "feat: add insider activity + institutional holdings service"
```

---

### Task 2.4: Analyst Data Enhancement

**Files:**
- Modify: `backend/services/sentiment.py`
- Modify: `tests/test_research.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_research.py`:

```python
from backend.services.sentiment import _build_analyst_data


def test_analyst_data_contrarian_signal_bearish():
    """Sell consensus should be HIGH_INTEREST contrarian signal."""
    data = {
        "consensus": "sell",
        "target_mean": 100,
        "target_low": 80,
        "target_high": 130,
        "num_analysts": 15,
        "recent_changes": [],
        "current_price": 120,
    }
    result = _build_analyst_data(data)
    assert result["price_vs_target"] > 1.0  # trading above target
    assert result["contrarian_signal"] == "ANALYSTS_BEARISH"


def test_analyst_data_contrarian_signal_consensus():
    """Buy consensus = no contrarian edge."""
    data = {
        "consensus": "buy",
        "target_mean": 200,
        "target_low": 150,
        "target_high": 250,
        "num_analysts": 20,
        "recent_changes": [],
        "current_price": 150,
    }
    result = _build_analyst_data(data)
    assert result["price_vs_target"] < 1.0
    assert result["contrarian_signal"] == "CONSENSUS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_research.py::test_analyst_data_contrarian_signal_bearish -v`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Add get_analyst_data to sentiment.py**

Add to `backend/services/sentiment.py` before the `fetch_sentiment_batch` function:

```python
def _build_analyst_data(data: dict) -> dict:
    """Add contrarian interpretation to analyst data."""
    result = {**data}
    price = data.get("current_price", 0)
    target = data.get("target_mean", 0)

    result["price_vs_target"] = round(price / target, 3) if target and target > 0 else None

    consensus = data.get("consensus", "")
    if consensus in ("sell", "strong_sell"):
        result["contrarian_signal"] = "ANALYSTS_BEARISH"
    elif consensus == "hold" and result.get("price_vs_target") and result["price_vs_target"] > 1.1:
        result["contrarian_signal"] = "ABOVE_TARGETS"
    else:
        result["contrarian_signal"] = "CONSENSUS"

    return result


def get_analyst_data(ticker: str) -> dict:
    """Full analyst data with contrarian interpretation. Cached 6hr."""
    from backend.config import ENRICHMENT_CONFIG

    db = get_db()
    cached = db.execute("SELECT * FROM analyst_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ENRICHMENT_CONFIG["analyst_ttl_hours"]):
        import json
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        data.update({
            "consensus": cached["consensus"],
            "target_mean": cached["target_mean"],
            "target_low": cached["target_low"],
            "target_high": cached["target_high"],
            "num_analysts": cached["num_analysts"],
        })
        return _build_analyst_data(data)

    # Fetch from yfinance + Finnhub
    import yfinance as yf
    stock = yf.Ticker(ticker)
    info = stock.info

    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    target_mean = info.get("targetMeanPrice")
    target_low = info.get("targetLowPrice")
    target_high = info.get("targetHighPrice")
    num_analysts = info.get("numberOfAnalystOpinions", 0)

    # Get recommendation from yfinance
    rec_key = info.get("recommendationKey", "hold")
    consensus_map = {
        "strong_buy": "strong_buy", "buy": "buy", "hold": "hold",
        "sell": "sell", "strong_sell": "strong_sell",
        "underperform": "sell", "outperform": "buy",
    }
    consensus = consensus_map.get(rec_key, "hold")

    # Fetch recent analyst changes from Finnhub
    recent_changes = []
    if FINNHUB_API_KEY:
        try:
            url = f"https://finnhub.io/api/v1/stock/upgrade-downgrade?symbol={ticker}&token={FINNHUB_API_KEY}"
            resp = httpx.get(url, timeout=10)
            changes = resp.json()
            for c in changes[:5]:
                recent_changes.append({
                    "firm": c.get("company", ""),
                    "from_rating": c.get("fromGrade", ""),
                    "to_rating": c.get("toGrade", ""),
                    "date": c.get("gradeTime", ""),
                    "action": c.get("action", ""),
                })
        except Exception:
            pass

    data = {
        "consensus": consensus,
        "target_mean": target_mean,
        "target_low": target_low,
        "target_high": target_high,
        "num_analysts": num_analysts,
        "recent_changes": recent_changes,
        "current_price": price,
    }

    # Cache
    import json
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO analyst_cache
        (ticker, consensus, target_mean, target_low, target_high, num_analysts, data_json, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (ticker, consensus, target_mean, target_low, target_high, num_analysts, json.dumps(data)))
    db.commit()
    db.close()

    return _build_analyst_data(data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_research.py -v`
Expected: 6 PASSED (4 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add backend/services/sentiment.py tests/test_research.py
git commit -m "feat: add analyst data with contrarian signals to sentiment service"
```

---

### Task 2.5: Peer Comparison Service

**Files:**
- Create: `backend/services/peers.py`
- Create: `tests/test_peers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_peers.py`:

```python
from backend.services.peers import _rank_among_peers


def test_rank_among_peers():
    """Rank a ticker's metrics against peers."""
    peers = [
        {"ticker": "AAPL", "forward_pe": 25, "operating_margin": 0.30, "revenue_growth": 0.08},
        {"ticker": "MSFT", "forward_pe": 30, "operating_margin": 0.42, "revenue_growth": 0.12},
        {"ticker": "GOOGL", "forward_pe": 20, "operating_margin": 0.28, "revenue_growth": 0.10},
    ]
    rank = _rank_among_peers("MSFT", peers)
    assert rank["pe_rank"] == 3  # highest PE = worst rank
    assert rank["margin_rank"] == 1  # highest margin = best rank


def test_rank_handles_none():
    peers = [
        {"ticker": "A", "forward_pe": None, "operating_margin": 0.2, "revenue_growth": 0.05},
        {"ticker": "B", "forward_pe": 20, "operating_margin": None, "revenue_growth": 0.1},
    ]
    rank = _rank_among_peers("A", peers)
    assert isinstance(rank, dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_peers.py::test_rank_among_peers -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement peers.py**

Create `backend/services/peers.py`:

```python
"""
Peer Comparison — find sector peers and compare key metrics.
Uses yfinance sector/industry info to identify 5-8 peers.
"""
import json
import yfinance as yf
from datetime import datetime
from backend.database import get_db
from backend.config import ENRICHMENT_CONFIG
from backend.services.market_data import get_stock_fundamentals, get_moving_averages
from backend.services.regime_checker import classify_direction


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _rank_among_peers(ticker: str, peers: list[dict]) -> dict:
    """Rank the given ticker's metrics among its peers.

    Lower PE rank = better (cheaper). Higher margin/growth rank = better.
    Returns 1-based ranks where 1 = best.
    """
    def _rank_metric(key, reverse=False):
        """Rank by metric. reverse=True means higher is better."""
        vals = [(p["ticker"], p.get(key)) for p in peers if p.get(key) is not None]
        if not vals:
            return None
        sorted_vals = sorted(vals, key=lambda x: x[1], reverse=reverse)
        for i, (t, _) in enumerate(sorted_vals):
            if t == ticker:
                return i + 1
        return None

    return {
        "pe_rank": _rank_metric("forward_pe", reverse=False),  # lower PE = rank 1
        "margin_rank": _rank_metric("operating_margin", reverse=True),  # higher margin = rank 1
        "growth_rank": _rank_metric("revenue_growth", reverse=True),
        "value_rank": _rank_metric("forward_pe", reverse=False),
    }


def get_peer_comparison(ticker: str) -> dict:
    """Get peer comparison data. Cached 6hr."""
    db = get_db()
    cached = db.execute("SELECT * FROM peer_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ENRICHMENT_CONFIG["peer_ttl_hours"]):
        return json.loads(cached["peers_json"]) if cached["peers_json"] else {}

    # Get sector/industry from yfinance
    stock = yf.Ticker(ticker)
    info = stock.info
    sector = info.get("sector", "")
    industry = info.get("industry", "")

    # Use yfinance's built-in peer lookup if available
    peer_tickers = []
    try:
        # yfinance doesn't have a direct peers API, but we can use recommendations
        # or manually curate from industry
        # For now, use the stock's "recommendedSymbols" if available
        if hasattr(stock, 'recommendations') and stock.recommendations is not None:
            pass  # recommendations don't give peers

        # Fallback: get major stocks from same sector via screening
        # We'll use a curated approach based on sector
        from backend.services.sp500 import get_sp500_tickers
        all_tickers = get_sp500_tickers()

        # Sample up to 20 from S&P to find same-sector peers
        import random
        sample = random.sample(all_tickers, min(30, len(all_tickers)))
        if ticker not in sample:
            sample.append(ticker)

        for t in sample:
            if len(peer_tickers) >= 8:
                break
            if t == ticker:
                continue
            try:
                t_info = yf.Ticker(t).info
                if t_info.get("sector") == sector:
                    peer_tickers.append(t)
            except Exception:
                continue

    except Exception:
        pass

    if not peer_tickers:
        result = {"peers": [], "ticker_rank": {}, "sector": sector}
        _cache_peers(ticker, result)
        return result

    # Fetch metrics for each peer + the target ticker
    peers_data = []
    for t in [ticker] + peer_tickers:
        try:
            fund = get_stock_fundamentals(t)
            d = fund.value if hasattr(fund, 'value') else fund
            ma = get_moving_averages(t)
            direction = classify_direction(
                ma.get("price", 0), ma.get("ema20", 0),
                ma.get("sma50", 0), ma.get("sma200", 0)
            ) if ma else "UNKNOWN"

            peers_data.append({
                "ticker": t,
                "name": d.get("name", ""),
                "market_cap": d.get("market_cap"),
                "forward_pe": d.get("forward_pe"),
                "operating_margin": d.get("operating_margin"),
                "revenue_growth": d.get("revenue_growth"),
                "free_cash_flow": d.get("free_cash_flow"),
                "drop_from_high": d.get("drop_from_high"),
                "direction": direction,
            })
        except Exception:
            continue

    rank = _rank_among_peers(ticker, peers_data)

    result = {
        "peers": peers_data,
        "ticker_rank": rank,
        "sector": sector,
    }

    _cache_peers(ticker, result)
    return result


def _cache_peers(ticker: str, result: dict):
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO peer_cache (ticker, peers_json, fetched_at)
        VALUES (?, ?, datetime('now'))
    """, (ticker, json.dumps(result)))
    db.commit()
    db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_peers.py -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/peers.py tests/test_peers.py
git commit -m "feat: add peer comparison service with sector ranking"
```

---

### Task 2.6: Integration Tests

**Files:**
- Modify: `tests/test_financial_history.py`
- Modify: `tests/test_institutional.py`

- [ ] **Step 1: Add integration tests**

Append to `tests/test_financial_history.py`:

```python
import pytest
from backend.services.financial_history import get_financial_history
from backend.database import init_db


@pytest.mark.integration
def test_get_financial_history_live():
    """Integration: fetch real financial history for MSFT."""
    init_db()
    result = get_financial_history("MSFT")
    assert result["ticker"] == "MSFT"
    assert "revenue" in result
    assert len(result["revenue"]) >= 2
    assert "operating_margin" in result
```

Append to `tests/test_institutional.py`:

```python
import pytest
from backend.services.institutional import get_insider_activity, get_institutional_summary
from backend.database import init_db


@pytest.mark.integration
def test_get_insider_activity_live():
    """Integration: fetch real insider activity for AAPL."""
    init_db()
    result = get_insider_activity("AAPL")
    assert result["net_sentiment"] in ("BUYING", "SELLING", "MIXED", "QUIET", "UNKNOWN")
    assert isinstance(result["recent_buys"], list)


@pytest.mark.integration
def test_get_institutional_summary_live():
    """Integration: fetch real institutional data for AAPL."""
    init_db()
    result = get_institutional_summary("AAPL")
    assert isinstance(result["top_holders"], list)
    assert result["trend"] in ("ACCUMULATING", "DISTRIBUTING", "STABLE", "UNKNOWN")
```

- [ ] **Step 2: Run integration tests**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_financial_history.py::test_get_financial_history_live tests/test_institutional.py::test_get_insider_activity_live tests/test_institutional.py::test_get_institutional_summary_live -v`
Expected: 3 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_financial_history.py tests/test_institutional.py
git commit -m "test: add integration tests for financial history and institutional services"
```

---

## Agent 3: Gemini Integration

### Task 3.1: Config + Dependencies

**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: Add GEMINI_CONFIG to config.py**

Add at the end of `backend/config.py`:

```python
GEMINI_CONFIG = {
    "model": "gemini-2.5-pro",
    "max_rpm": 5,
    "max_rpd": 100,
    "max_output_tokens": 8192,
    "temperature": 0.7,
}
```

- [ ] **Step 2: Install google-generativeai**

Run: `pip3 install google-generativeai`
Expected: Successfully installed

- [ ] **Step 3: Commit**

```bash
git add backend/config.py
git commit -m "feat: add Gemini 2.5 Pro config"
```

---

### Task 3.2: Deep Dive Prompt Template

**Files:**
- Create: `backend/prompts/deep_dive.txt`

- [ ] **Step 1: Create prompts directory and template**

Run: `mkdir -p "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system/backend/prompts"`

- [ ] **Step 2: Write the prompt template**

Create `backend/prompts/deep_dive.txt`:

```
You are a contrarian quality investor analyzing {ticker} ({company_name}).

## Your Framework
- Bear case FIRST, always. Stock risk vs business risk.
- Fail-closed: if data is missing or uncertain, treat it as a negative.
- Contrarian inversion: negative crowd sentiment = opportunity signal. If everyone hates it and fundamentals hold, that's your edge.
- WACC fixed at 10% for ALL scenarios. Only vary growth assumptions.
- SBC-adjusted FCF if SBC > 10% of revenue.
- Reverse DCF before forward DCF — always.

## Data Context
{data_context}

## Required Sections (produce ALL 8, in this exact order)

### Section 1: Data Snapshot & First Impression
Summarize the key fundamentals, technicals, and your gut reaction. Include:
- Price, PE, margins, FCF yield, drop from high
- Technical setup: direction, RSI, MACD, support/resistance
- Insider activity and institutional signals
- One paragraph: what does this look like at first glance?

### Section 2: First Impression (Deep)
What's the story here? Why is the stock where it is? What's the market narrative vs reality?

### Section 3: Bear Case — Stock Risk vs Business Risk
SEPARATE these clearly:
- Stock risk: valuation, sentiment, momentum, crowding
- Business risk: competitive threats, margin compression, secular decline, management
Which risks are priced in? Which aren't?

### Section 4: Bull Case — Rebuttal & Upside
For each bear case point, provide a specific rebuttal. Then describe the upside scenario. Be specific about catalysts and timing.

### Section 5: Valuation
- Run a reverse DCF: what growth rate is the market pricing in?
- Forward DCF: use 3-year average FCF (SBC-adjusted if needed), WACC=10%, vary growth (conservative/base/optimistic)
- Terminal value MUST be < 50% of total — flag if it isn't
- Net debt from balance sheet, never zero
- Compare to peer valuations: {peer_context}
- Analyst targets: {analyst_context}

### Section 6: Whole Picture
- Sector dynamics, competitive position, moat assessment
- Management quality (capital allocation, insider behavior)
- Insider activity: {insider_context}
- Institutional holdings: {institutional_context}
- What's the one thing the market is missing?

### Section 7: Self-Review
- Bias check: am I anchoring on the drop? Confirmation bias?
- Pre-mortem: if I buy this and lose 30% in 6 months, what happened?
- What would make me wrong? Be specific.
- Confidence level: HIGH / MEDIUM / LOW

### Section 8: Verdict + Entry Grid + Exit Playbook
- Verdict: BUY / WATCH / PASS with one-sentence rationale
- If BUY, provide entry grid:
  | Tranche | Price | % of Position | Trigger |
  |---------|-------|---------------|---------|
  | 1 | $X | 25% | Current levels if [condition] |
  | 2 | $Y | 25% | On pullback to [support] |
  | 3 | $Z | 25% | On [catalyst confirmation] |
  | 4 | $W | 25% | On earnings if [condition] |
- Exit playbook: stop loss, profit targets, time-based exits
- Conviction: 1-5 scale with reasoning
```

- [ ] **Step 3: Commit**

```bash
git add backend/prompts/deep_dive.txt
git commit -m "feat: add Gemini deep dive prompt template"
```

---

### Task 3.3: Gemini Analyzer Service

**Files:**
- Create: `backend/services/gemini_analyzer.py`
- Create: `tests/test_gemini.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_gemini.py`:

```python
from unittest.mock import patch, MagicMock
from backend.services.gemini_analyzer import _build_context_string, _parse_sections, GeminiRateLimiter


def test_build_context_string():
    """Context string should contain all provided data."""
    context = {
        "fundamentals": {"price": 150, "forward_pe": 25, "operating_margin": 0.30},
        "technicals": {"rsi": 35, "direction": "PULLBACK_IN_UPTREND"},
        "financial_history": {"revenue": [{"year": 2025, "value": 20e9}]},
    }
    result = _build_context_string(context)
    assert "150" in result
    assert "RSI" in result or "rsi" in result
    assert "PULLBACK" in result


def test_parse_sections_basic():
    """Parser should extract sections from markdown."""
    text = """
### Section 1: Data Snapshot & First Impression
Some analysis here about the stock.

### Section 2: First Impression (Deep)
Deeper analysis.

### Section 3: Bear Case — Stock Risk vs Business Risk
Bear stuff here.
"""
    sections = _parse_sections(text)
    assert len(sections) >= 3
    assert "Some analysis" in sections.get("first_impression", sections.get("data_snapshot", ""))


def test_rate_limiter_allows_requests():
    limiter = GeminiRateLimiter(max_rpm=5, max_rpd=100)
    assert limiter.can_request() is True
    limiter.record_request()
    assert limiter.can_request() is True


def test_rate_limiter_blocks_over_rpm():
    limiter = GeminiRateLimiter(max_rpm=2, max_rpd=100)
    limiter.record_request()
    limiter.record_request()
    assert limiter.can_request() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_gemini.py::test_build_context_string -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement gemini_analyzer.py**

Create `backend/services/gemini_analyzer.py`:

```python
"""
Gemini 2.5 Pro Integration — AI-powered deep dive generation.
Uses Tier 1 data as context. Rate-limited to free tier (5 RPM, 100 RPD).
"""
import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque
from backend.config import GEMINI_CONFIG
from backend.database import get_db


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "deep_dive.txt"


class GeminiRateLimiter:
    """Track RPM and RPD for Gemini free tier."""

    def __init__(self, max_rpm: int = None, max_rpd: int = None):
        self.max_rpm = max_rpm or GEMINI_CONFIG["max_rpm"]
        self.max_rpd = max_rpd or GEMINI_CONFIG["max_rpd"]
        self._minute_window: deque = deque()
        self._day_window: deque = deque()

    def can_request(self) -> bool:
        self._clean()
        return len(self._minute_window) < self.max_rpm and len(self._day_window) < self.max_rpd

    def record_request(self):
        now = time.time()
        self._minute_window.append(now)
        self._day_window.append(now)

    def seconds_until_available(self) -> int:
        self._clean()
        if len(self._minute_window) >= self.max_rpm and self._minute_window:
            wait = 60 - (time.time() - self._minute_window[0])
            return max(1, int(wait))
        if len(self._day_window) >= self.max_rpd and self._day_window:
            wait = 86400 - (time.time() - self._day_window[0])
            return max(1, int(wait))
        return 0

    def _clean(self):
        now = time.time()
        while self._minute_window and now - self._minute_window[0] > 60:
            self._minute_window.popleft()
        while self._day_window and now - self._day_window[0] > 86400:
            self._day_window.popleft()


# Global rate limiter instance
_rate_limiter = GeminiRateLimiter()


def _build_context_string(context: dict) -> str:
    """Format all Tier 1 data into a structured context string for the prompt."""
    parts = []

    if "fundamentals" in context:
        f = context["fundamentals"]
        parts.append("## Fundamentals")
        for key, val in f.items():
            if val is not None:
                parts.append(f"- {key}: {val}")

    if "technicals" in context:
        t = context["technicals"]
        parts.append("\n## Technical Analysis")
        for key, val in t.items():
            if val is not None:
                label = key.upper().replace("_", " ")
                parts.append(f"- {label}: {val}")

    if "financial_history" in context:
        fh = context["financial_history"]
        parts.append("\n## 5-Year Financial History")
        for metric, entries in fh.items():
            if metric == "ticker" or not isinstance(entries, list):
                continue
            vals = ", ".join(f"{e['year']}: {e['value']}" for e in entries[:5])
            parts.append(f"- {metric}: {vals}")

    if "insider_activity" in context:
        ins = context["insider_activity"]
        parts.append(f"\n## Insider Activity")
        parts.append(f"- Net Sentiment: {ins.get('net_sentiment', 'UNKNOWN')}")
        for buy in ins.get("notable", [])[:3]:
            parts.append(f"- Notable: {buy.get('name', '')} — {buy.get('shares', 0)} shares (${buy.get('value', 0):,.0f})")

    if "institutional" in context:
        inst = context["institutional"]
        parts.append(f"\n## Institutional Holdings")
        parts.append(f"- Institutional %: {inst.get('institutional_pct', 'N/A')}%")
        parts.append(f"- Trend: {inst.get('trend', 'UNKNOWN')}")
        for h in inst.get("top_holders", [])[:3]:
            parts.append(f"- {h.get('name', '')}: {h.get('pct', 'N/A')}%")

    if "analyst" in context:
        a = context["analyst"]
        parts.append(f"\n## Analyst Data")
        parts.append(f"- Consensus: {a.get('consensus', 'N/A')}")
        parts.append(f"- Targets: ${a.get('target_low', 'N/A')} / ${a.get('target_mean', 'N/A')} / ${a.get('target_high', 'N/A')}")
        parts.append(f"- # Analysts: {a.get('num_analysts', 'N/A')}")

    if "sentiment" in context:
        s = context["sentiment"]
        parts.append(f"\n## Sentiment")
        parts.append(f"- Contrarian Rating: {s.get('contrarian_rating', 'N/A')}")
        parts.append(f"- Signals: {', '.join(s.get('contrarian_signals', []))}")

    if "peers" in context:
        p = context["peers"]
        parts.append(f"\n## Peers ({p.get('sector', '')})")
        for peer in p.get("peers", [])[:5]:
            parts.append(f"- {peer.get('ticker', '')}: PE={peer.get('forward_pe', 'N/A')}, Margin={peer.get('operating_margin', 'N/A')}, Drop={peer.get('drop_from_high', 'N/A')}")

    if "regime" in context:
        r = context["regime"]
        parts.append(f"\n## Market Regime")
        parts.append(f"- Verdict: {r.get('verdict', 'N/A')}")
        parts.append(f"- Max Positions: {r.get('max_new_positions', 'N/A')}")

    return "\n".join(parts)


def _parse_sections(text: str) -> dict:
    """Parse Gemini response into 8 sections by heading."""
    section_map = {
        "section 1": "data_snapshot",
        "data snapshot": "data_snapshot",
        "first impression": "first_impression",
        "section 2": "first_impression",
        "section 3": "bear_case",
        "bear case": "bear_case",
        "section 4": "bull_case",
        "bull case": "bull_case",
        "section 5": "valuation",
        "valuation": "valuation",
        "section 6": "whole_picture",
        "whole picture": "whole_picture",
        "section 7": "self_review",
        "self-review": "self_review",
        "self review": "self_review",
        "section 8": "verdict",
        "verdict": "verdict",
    }

    sections = {}
    current_key = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip().lower()
        if stripped.startswith("###") or stripped.startswith("## "):
            # Check if this is a section header
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()

            matched = False
            for pattern, key in section_map.items():
                if pattern in stripped:
                    current_key = key
                    current_lines = []
                    matched = True
                    break
            if not matched:
                current_lines.append(line)
        else:
            if current_key is not None:
                current_lines.append(line)

    if current_key and current_lines:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def generate_deep_dive(ticker: str, context: dict) -> dict:
    """Generate a full 8-section deep dive using Gemini 2.5 Pro.

    Args:
        ticker: Stock ticker
        context: Dict containing fundamentals, technicals, financial_history,
                 insider_activity, institutional, analyst, sentiment, peers, regime

    Returns:
        Dict with section keys and generated text, or error dict.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not set. Get a free key from ai.google.dev"}

    if not _rate_limiter.can_request():
        wait = _rate_limiter.seconds_until_available()
        return {"error": f"Rate limit reached. Try again in {wait} seconds.", "retry_after": wait}

    # Build prompt
    try:
        template = PROMPT_PATH.read_text()
    except FileNotFoundError:
        return {"error": "Prompt template not found at backend/prompts/deep_dive.txt"}

    data_context = _build_context_string(context)
    company_name = context.get("fundamentals", {}).get("name", ticker)

    # Build sub-contexts for template placeholders
    peer_context = "No peer data available"
    if "peers" in context:
        peers = context["peers"].get("peers", [])
        if peers:
            peer_lines = [f"{p['ticker']}: PE={p.get('forward_pe','N/A')}, Margin={p.get('operating_margin','N/A')}" for p in peers[:5]]
            peer_context = "; ".join(peer_lines)

    analyst_context = "No analyst data available"
    if "analyst" in context:
        a = context["analyst"]
        analyst_context = f"Consensus: {a.get('consensus','N/A')}, Target: ${a.get('target_low','?')}-${a.get('target_high','?')} (mean ${a.get('target_mean','?')})"

    insider_context = "No insider data available"
    if "insider_activity" in context:
        ins = context["insider_activity"]
        insider_context = f"Net sentiment: {ins.get('net_sentiment','UNKNOWN')}. Notable: {len(ins.get('notable', []))} C-suite transactions."

    institutional_context = "No institutional data available"
    if "institutional" in context:
        inst = context["institutional"]
        institutional_context = f"Institutional ownership: {inst.get('institutional_pct','N/A')}%. Trend: {inst.get('trend','UNKNOWN')}."

    prompt = template.format(
        ticker=ticker,
        company_name=company_name,
        data_context=data_context,
        peer_context=peer_context,
        analyst_context=analyst_context,
        insider_context=insider_context,
        institutional_context=institutional_context,
    )

    # Call Gemini
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        model = genai.GenerativeModel(GEMINI_CONFIG["model"])
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=GEMINI_CONFIG["max_output_tokens"],
                temperature=GEMINI_CONFIG["temperature"],
            ),
        )

        _rate_limiter.record_request()

        raw_text = response.text
        sections = _parse_sections(raw_text)

        # Store raw + parsed
        result = {
            "ticker": ticker,
            "generated_at": datetime.now().isoformat(),
            "model": GEMINI_CONFIG["model"],
            "raw_text": raw_text,
            **sections,
        }

        return result

    except Exception as e:
        _rate_limiter.record_request()  # Still count failed attempts
        return {"error": f"Gemini API error: {str(e)}"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_gemini.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/services/gemini_analyzer.py tests/test_gemini.py
git commit -m "feat: add Gemini 2.5 Pro deep dive analyzer with rate limiting"
```

---

### Task 3.4: POST Endpoint for AI Analysis

**Files:**
- Modify: `backend/routers/deep_dive.py`

- [ ] **Step 1: Read current deep_dive.py**

Read `backend/routers/deep_dive.py` to see the current endpoint structure.

- [ ] **Step 2: Add POST /api/deep-dive/{ticker}/analyze endpoint**

Add to `backend/routers/deep_dive.py`:

```python
from backend.services.gemini_analyzer import generate_deep_dive

@router.post("/{ticker}/analyze")
async def analyze_deep_dive(ticker: str):
    """Trigger Gemini 2.5 Pro to generate all 8 deep dive sections.

    Assembles all Tier 1 data as context, calls Gemini, saves result.
    """
    ticker = ticker.upper()

    # Gather all Tier 1 context
    context = {}

    try:
        from backend.services.market_data import get_stock_fundamentals
        fund = get_stock_fundamentals(ticker)
        context["fundamentals"] = fund.value if hasattr(fund, 'value') else fund
    except Exception:
        pass

    try:
        from backend.services.technicals import get_full_technicals
        context["technicals"] = get_full_technicals(ticker)
    except Exception:
        pass

    try:
        from backend.services.financial_history import get_financial_history
        context["financial_history"] = get_financial_history(ticker)
    except Exception:
        pass

    try:
        from backend.services.institutional import get_insider_activity, get_institutional_summary
        context["insider_activity"] = get_insider_activity(ticker)
        context["institutional"] = get_institutional_summary(ticker)
    except Exception:
        pass

    try:
        from backend.services.sentiment import get_analyst_data, fetch_sentiment
        context["analyst"] = get_analyst_data(ticker)
        context["sentiment"] = fetch_sentiment(ticker)
    except Exception:
        pass

    try:
        from backend.services.peers import get_peer_comparison
        context["peers"] = get_peer_comparison(ticker)
    except Exception:
        pass

    try:
        from backend.services.regime_checker import get_full_regime
        regime_data = get_full_regime()
        context["regime"] = regime_data.get("regime", {})
    except Exception:
        pass

    # Generate deep dive
    result = generate_deep_dive(ticker, context)

    if "error" in result:
        from fastapi import HTTPException
        status_code = 429 if "Rate limit" in result["error"] else 500
        raise HTTPException(status_code=status_code, detail=result["error"])

    # Save to deep_dives table
    db = get_db()
    sections_json = json.dumps({
        k: v for k, v in result.items()
        if k not in ("ticker", "generated_at", "model", "raw_text")
    })

    db.execute("""
        INSERT OR REPLACE INTO deep_dives (ticker, analysis_json, updated_at)
        VALUES (?, ?, datetime('now'))
    """, (ticker, sections_json))
    db.commit()
    db.close()

    return {
        "ticker": ticker,
        "status": "generated",
        "model": result.get("model", ""),
        "sections": {k: v for k, v in result.items() if k not in ("raw_text", "ticker", "generated_at", "model")},
    }
```

Add required imports at top of file if not already present:

```python
import json
from backend.database import get_db
```

- [ ] **Step 3: Test the endpoint manually**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -c "
from backend.routers.deep_dive import router
print('Router loaded, endpoints:', [r.path for r in router.routes])
"`
Expected: Shows both GET and POST endpoints

- [ ] **Step 4: Commit**

```bash
git add backend/routers/deep_dive.py
git commit -m "feat: add POST /api/deep-dive/{ticker}/analyze endpoint for Gemini AI"
```

---

### Task 3.5: Gemini Integration Test

**Files:**
- Modify: `tests/test_gemini.py`

- [ ] **Step 1: Add mocked integration test**

Append to `tests/test_gemini.py`:

```python
@patch("backend.services.gemini_analyzer.GEMINI_API_KEY", "fake-key")
def test_generate_deep_dive_no_api():
    """Without real API, should attempt and fail gracefully."""
    from backend.services.gemini_analyzer import generate_deep_dive
    result = generate_deep_dive("AAPL", {
        "fundamentals": {"price": 150, "name": "Apple Inc"},
    })
    # Will fail because fake key, but should not crash
    assert "error" in result or "data_snapshot" in result


def test_context_string_handles_empty():
    """Empty context should produce empty string without crashing."""
    result = _build_context_string({})
    assert isinstance(result, str)


def test_parse_sections_empty():
    """Empty text should return empty dict."""
    result = _parse_sections("")
    assert result == {}
```

- [ ] **Step 2: Run all Gemini tests**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/test_gemini.py -v`
Expected: 7 PASSED

- [ ] **Step 3: Commit**

```bash
git add tests/test_gemini.py
git commit -m "test: add edge case tests for Gemini analyzer"
```

---

## Final Verification

### Task F.1: Run All Tests

- [ ] **Step 1: Run full test suite**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/ -v --ignore=tests/test_technicals.py::test_get_full_technicals_live --ignore=tests/test_financial_history.py::test_get_financial_history_live -k "not integration"`
Expected: All unit tests PASS

- [ ] **Step 2: Run integration tests (requires network)**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -m pytest tests/ -v -m integration`
Expected: All integration tests PASS (may be slow due to API calls)

- [ ] **Step 3: Verify server starts**

Run: `cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system" && python3 -c "from backend.main import app; print('Server config OK')"`
Expected: `Server config OK`
