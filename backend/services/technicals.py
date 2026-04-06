"""
Technical Analysis Service — Pure computation + cached aggregator.
All indicator functions take pandas Series/DataFrames; no API calls.
get_full_technicals is the aggregator that fetches data and caches.
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime

from backend.config import TECHNICALS_CONFIG
from backend.database import get_db
from backend.services.market_data import get_price_history
from backend.services.regime_checker import classify_direction


# ---------------------------------------------------------------------------
# Cache helper
# ---------------------------------------------------------------------------

def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


# ---------------------------------------------------------------------------
# 1. RSI — Wilder's smoothing
# ---------------------------------------------------------------------------

def calculate_rsi(close: pd.Series, period: int = TECHNICALS_CONFIG["rsi_period"]) -> float:
    """Wilder's RSI (0-100). Returns NaN-safe float."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing: first value is SMA, then exponential
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    val = rsi.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else 50.0


# ---------------------------------------------------------------------------
# 2. MACD
# ---------------------------------------------------------------------------

def calculate_macd(
    close: pd.Series,
    fast: int = TECHNICALS_CONFIG["macd_fast"],
    slow: int = TECHNICALS_CONFIG["macd_slow"],
    signal_period: int = TECHNICALS_CONFIG["macd_signal"],
) -> dict:
    """MACD line, signal, histogram, and crossover direction."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    hist = macd_line - signal_line

    macd_val = macd_line.iloc[-1]
    sig_val = signal_line.iloc[-1]
    hist_val = hist.iloc[-1]

    # Crossover detection: compare last two bars
    if len(macd_line) >= 2 and len(signal_line) >= 2:
        prev_diff = macd_line.iloc[-2] - signal_line.iloc[-2]
        curr_diff = macd_line.iloc[-1] - signal_line.iloc[-1]
        if prev_diff <= 0 < curr_diff:
            crossover = "bullish"
        elif prev_diff >= 0 > curr_diff:
            crossover = "bearish"
        else:
            crossover = "none"
    else:
        crossover = "none"

    return {
        "macd": round(float(macd_val), 4) if pd.notna(macd_val) else 0.0,
        "signal": round(float(sig_val), 4) if pd.notna(sig_val) else 0.0,
        "histogram": round(float(hist_val), 4) if pd.notna(hist_val) else 0.0,
        "crossover": crossover,
    }


# ---------------------------------------------------------------------------
# 3. Bollinger Bands
# ---------------------------------------------------------------------------

def calculate_bollinger(
    close: pd.Series,
    period: int = TECHNICALS_CONFIG["bollinger_period"],
    num_std: int = TECHNICALS_CONFIG["bollinger_std"],
) -> dict:
    """Bollinger Bands with %B."""
    middle = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std

    mid_val = middle.iloc[-1]
    up_val = upper.iloc[-1]
    lo_val = lower.iloc[-1]
    close_val = close.iloc[-1]

    if pd.notna(up_val) and pd.notna(lo_val) and (up_val - lo_val) != 0:
        pct_b = (close_val - lo_val) / (up_val - lo_val)
    else:
        pct_b = 0.5

    return {
        "upper": round(float(up_val), 2) if pd.notna(up_val) else 0.0,
        "middle": round(float(mid_val), 2) if pd.notna(mid_val) else 0.0,
        "lower": round(float(lo_val), 2) if pd.notna(lo_val) else 0.0,
        "pct_b": round(float(pct_b), 4) if pd.notna(pct_b) else 0.5,
    }


# ---------------------------------------------------------------------------
# 4. ADX — Average Directional Index
# ---------------------------------------------------------------------------

def calculate_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = TECHNICALS_CONFIG["adx_period"],
) -> float:
    """ADX trend-strength indicator (0-100)."""
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)

    # True Range
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - prev_high
    down_move = prev_low - low

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # Wilder's smoothing
    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr)

    dx = (plus_di - minus_di).abs() / (plus_di + minus_di) * 100
    adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    val = adx.iloc[-1]
    return round(float(val), 2) if pd.notna(val) else 0.0


# ---------------------------------------------------------------------------
# 5. Volume Analysis
# ---------------------------------------------------------------------------

def calculate_volume_analysis(
    volume: pd.Series,
    close: pd.Series,
    avg_period: int = TECHNICALS_CONFIG["volume_avg_period"],
) -> dict:
    """Volume metrics: average, relative volume, trend, dry-up detection."""
    avg_vol = volume.rolling(avg_period).mean()
    avg_val = avg_vol.iloc[-1]
    last_vol = volume.iloc[-1]

    if pd.notna(avg_val) and avg_val > 0:
        rel_vol = float(last_vol) / float(avg_val)
    else:
        rel_vol = 1.0

    # Trend: compare recent 5-day avg vs 20-day avg
    recent_avg = volume.tail(5).mean()
    if pd.notna(avg_val) and avg_val > 0:
        if recent_avg > float(avg_val) * 1.2:
            trend = "increasing"
        elif recent_avg < float(avg_val) * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    # Dry-up: volume < 50% of 20-day average (contrarian signal)
    dry_up = rel_vol < 0.5

    return {
        "avg_20d": round(float(avg_val), 0) if pd.notna(avg_val) else 0.0,
        "relative_volume": round(rel_vol, 2),
        "trend": trend,
        "dry_up": dry_up,
    }


# ---------------------------------------------------------------------------
# 6. Support & Resistance (pivot-based)
# ---------------------------------------------------------------------------

def calculate_support_resistance(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    lookback: int = 60,
) -> dict:
    """Identify support/resistance levels from recent pivot points."""
    h = high.tail(lookback)
    l = low.tail(lookback)
    c = close.tail(lookback)

    current_price = float(c.iloc[-1])

    # Find local minima (supports) and maxima (resistances)
    supports = []
    resistances = []

    window = 5
    for i in range(window, len(l) - window):
        # Local minimum
        if float(l.iloc[i]) == float(l.iloc[i - window : i + window + 1].min()):
            supports.append(round(float(l.iloc[i]), 2))
        # Local maximum
        if float(h.iloc[i]) == float(h.iloc[i - window : i + window + 1].max()):
            resistances.append(round(float(h.iloc[i]), 2))

    # Deduplicate nearby levels (within 1%)
    supports = _dedupe_levels(sorted(set(supports)))
    resistances = _dedupe_levels(sorted(set(resistances)))

    # Keep only levels near current price
    supports = [s for s in supports if s < current_price]
    resistances = [r for r in resistances if r > current_price]

    # Return top 2 of each (closest to price)
    supports = sorted(supports, reverse=True)[:2]
    resistances = sorted(resistances)[:2]

    return {"support": supports, "resistance": resistances}


def _dedupe_levels(levels: list, threshold: float = 0.01) -> list:
    """Merge levels that are within threshold % of each other."""
    if not levels:
        return []
    result = [levels[0]]
    for lvl in levels[1:]:
        if abs(lvl - result[-1]) / result[-1] > threshold:
            result.append(lvl)
    return result


# ---------------------------------------------------------------------------
# 7. Relative Strength vs SPY
# ---------------------------------------------------------------------------

def calculate_relative_strength(
    ticker_close: pd.Series,
    spy_close: pd.Series,
) -> dict:
    """Relative strength: ratio of ticker returns vs SPY over 20d and 60d."""
    def _rs(periods: int) -> float:
        if len(ticker_close) < periods or len(spy_close) < periods:
            return 0.0
        ticker_ret = float(ticker_close.iloc[-1] / ticker_close.iloc[-periods] - 1)
        spy_ret = float(spy_close.iloc[-1] / spy_close.iloc[-periods] - 1)
        return round(ticker_ret - spy_ret, 4)

    return {
        "rs_20d": _rs(20),
        "rs_60d": _rs(60),
    }


# ---------------------------------------------------------------------------
# 8. Direction classification (delegate)
# ---------------------------------------------------------------------------

def classify_stock_direction(
    price: float,
    ema20: float,
    sma50: float,
    sma200: float,
) -> str:
    """Delegates to regime_checker.classify_direction."""
    return classify_direction(price, ema20, sma50, sma200)


# ---------------------------------------------------------------------------
# 9. Aggregator — get_full_technicals
# ---------------------------------------------------------------------------

def get_full_technicals(ticker: str) -> dict:
    """Fetch OHLCV, compute all indicators, cache in SQLite. Returns full dict."""
    # Check cache
    db = get_db()
    cached = db.execute(
        "SELECT * FROM technicals_cache WHERE ticker = ?", (ticker,)
    ).fetchone()
    db.close()

    if cached and _is_fresh(
        cached["fetched_at"], TECHNICALS_CONFIG["cache_ttl_hours"]
    ):
        result = dict(cached)
        if result.get("data_json"):
            result["extras"] = json.loads(result["data_json"])
        return result

    # Fetch price data
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

    # Compute indicators
    rsi = calculate_rsi(close)
    macd = calculate_macd(close)
    boll = calculate_bollinger(close)
    adx = calculate_adx(high, low, close)
    vol = calculate_volume_analysis(volume, close)
    sr = calculate_support_resistance(high, low, close)
    direction = classify_stock_direction(price, ema20, sma50, sma200)

    # Relative strength vs SPY
    try:
        spy_df = get_price_history("SPY", period="1y")
        rs = calculate_relative_strength(close, spy_df["Close"])
    except Exception:
        rs = {"rs_20d": 0.0, "rs_60d": 0.0}

    # Extras for data_json column
    extras = {
        "support": sr["support"],
        "resistance": sr["resistance"],
        "volume_dry_up": vol["dry_up"],
        "volume_avg_20d": vol["avg_20d"],
        "macd_crossover": macd["crossover"],
        "bollinger_pct_b": boll["pct_b"],
    }

    # Cache in SQLite
    support_1 = sr["support"][0] if len(sr["support"]) > 0 else None
    support_2 = sr["support"][1] if len(sr["support"]) > 1 else None
    resistance_1 = sr["resistance"][0] if len(sr["resistance"]) > 0 else None
    resistance_2 = sr["resistance"][1] if len(sr["resistance"]) > 1 else None

    db = get_db()
    db.execute(
        """
        INSERT OR REPLACE INTO technicals_cache
        (ticker, rsi, macd_value, macd_signal, macd_histogram, macd_crossover,
         direction, ema20, sma50, sma200, adx,
         bollinger_upper, bollinger_lower, bollinger_pct_b,
         volume_relative, volume_trend,
         support_1, support_2, resistance_1, resistance_2,
         rs_vs_spy_20d, rs_vs_spy_60d, data_json, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            ticker,
            rsi,
            macd["macd"],
            macd["signal"],
            macd["histogram"],
            macd["crossover"],
            direction,
            round(ema20, 2),
            round(sma50, 2),
            round(sma200, 2),
            adx,
            boll["upper"],
            boll["lower"],
            boll["pct_b"],
            vol["relative_volume"],
            vol["trend"],
            support_1,
            support_2,
            resistance_1,
            resistance_2,
            rs["rs_20d"],
            rs["rs_60d"],
            json.dumps(extras),
        ),
    )
    db.commit()
    db.close()

    return {
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
        "bollinger_upper": boll["upper"],
        "bollinger_lower": boll["lower"],
        "bollinger_pct_b": boll["pct_b"],
        "volume_relative": vol["relative_volume"],
        "volume_trend": vol["trend"],
        "support_1": support_1,
        "support_2": support_2,
        "resistance_1": resistance_1,
        "resistance_2": resistance_2,
        "rs_vs_spy_20d": rs["rs_20d"],
        "rs_vs_spy_60d": rs["rs_60d"],
        "extras": extras,
    }
