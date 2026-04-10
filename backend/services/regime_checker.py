import time
import yfinance as yf
from backend.services.market_data import get_moving_averages

# Module-level regime cache (1 hour TTL — regime changes max once/day)
_regime_cache: dict | None = None
_regime_cache_time: float = 0
_REGIME_CACHE_TTL = 3600


def classify_direction(price: float, ema20: float, sma50: float, sma200: float) -> str:
    if price > ema20 > sma50 > sma200:
        return "FULL_UPTREND"
    elif price > sma50 and price > sma200 and price < ema20:
        return "PULLBACK_IN_UPTREND"
    elif price < ema20 and price < sma50 and price > sma200:
        if abs(sma50 - sma200) / sma200 < 0.02:
            return "POTENTIAL_TREND_CHANGE"
        return "TREND_WEAKENING"
    elif price < ema20 and price < sma50 and sma50 > sma200:
        return "CORRECTION_IN_UPTREND"
    elif price < ema20 and price < sma50 and price < sma200:
        return "FULL_DOWNTREND"
    return "MIXED"


DIRECTION_SCORES = {
    "FULL_UPTREND": 4,
    "PULLBACK_IN_UPTREND": 3,
    "TREND_WEAKENING": 2,
    "CORRECTION_IN_UPTREND": 1.5,
    "MIXED": 1.5,
    "POTENTIAL_TREND_CHANGE": 1,
    "FULL_DOWNTREND": 0,
}


def calculate_vix_tax(vix: float) -> dict:
    """Calculate how much extra premium you pay vs VIX at 15 (historical calm)."""
    baseline_vix = 15.0
    if vix <= baseline_vix:
        return {"premium_premium_pct": 0, "note": f"VIX at {vix} — premiums at normal levels."}

    # Rough approximation: option premiums scale ~linearly with IV
    premium_pct = round((vix - baseline_vix) / baseline_vix * 100, 0)
    if vix > 30:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"4x target likely unachievable on delta 0.25-0.40 contracts. Avoid.")
    elif vix > 25:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"Need larger underlying move for 4x. Highest-conviction B1 only.")
    else:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"Acceptable for B1 plays where fear is narrative, not fundamental.")
    return {"premium_premium_pct": int(premium_pct), "note": note}


def determine_regime(spy: dict, qqq: dict, vix: float) -> dict:
    if vix > 35:
        return {
            "verdict": "CASH",
            "max_new_positions": 0,
            "spy_direction": spy["direction"],
            "qqq_direction": qqq["direction"],
            "vix": vix,
            "score": 0,
            "vix_tax": calculate_vix_tax(vix),
            "options_note": "NO new options positions. VIX extreme — capital preservation.",
        }

    spy_score = DIRECTION_SCORES.get(spy["direction"], 1.5)
    qqq_score = DIRECTION_SCORES.get(qqq["direction"], 1.5)
    avg_score = (spy_score + qqq_score) / 2

    if vix > 25:
        avg_score -= 0.5
    elif vix < 20:
        avg_score += 0.25

    if avg_score >= 3:
        verdict, max_pos = "DEPLOY", 5
    elif avg_score >= 2:
        verdict, max_pos = "CAUTIOUS", 2
    elif avg_score >= 1:
        verdict, max_pos = "DEFENSIVE", 0
    else:
        verdict, max_pos = "CASH", 0

    vix_tax = calculate_vix_tax(vix)

    return {
        "verdict": verdict,
        "max_new_positions": max_pos,
        "spy_direction": spy["direction"],
        "qqq_direction": qqq["direction"],
        "vix": vix,
        "score": round(avg_score, 2),
        "vix_tax": vix_tax,
        "options_note": vix_tax["note"] if verdict in ("DEPLOY", "CAUTIOUS") else "NO new positions.",
    }


def calculate_market_breadth() -> dict:
    """Sample ~50 S&P stocks to estimate % above 200d, 50d, and 20d SMA."""
    try:
        from backend.services.sp500 import get_sp500_tickers
        import random
        all_tickers = get_sp500_tickers()
        sample = random.sample(all_tickers, min(50, len(all_tickers)))

        above_200 = 0
        above_50 = 0
        above_20 = 0
        counted = 0

        for t in sample:
            try:
                ma = get_moving_averages(t)
                if not ma or not ma.get("price"):
                    continue
                counted += 1
                if ma["price"] > ma.get("sma200", 0):
                    above_200 += 1
                if ma["price"] > ma.get("sma50", 0):
                    above_50 += 1
                if ma["price"] > ma.get("ema20", 0):
                    above_20 += 1
            except Exception:
                continue

        if counted == 0:
            return {"pct_above_200d": None, "pct_above_50d": None, "pct_above_20d": None, "breadth_signal": "UNKNOWN", "sample_size": 0}

        pct_200 = round(above_200 / counted * 100, 1)
        pct_50 = round(above_50 / counted * 100, 1)
        pct_20 = round(above_20 / counted * 100, 1)

        if pct_200 >= 70:
            signal = "STRONG"
        elif pct_200 >= 50:
            signal = "HEALTHY"
        elif pct_200 >= 30:
            signal = "WEAKENING"
        else:
            signal = "POOR"

        return {
            "pct_above_200d": pct_200,
            "pct_above_50d": pct_50,
            "pct_above_20d": pct_20,
            "breadth_signal": signal,
            "sample_size": counted,
        }
    except Exception:
        return {"pct_above_200d": None, "pct_above_50d": None, "pct_above_20d": None, "breadth_signal": "UNKNOWN", "sample_size": 0}


# NDX 100 breadth cache (1 hour TTL)
_ndx_breadth_cache: dict | None = None
_ndx_breadth_cache_time: float = 0
_NDX_BREADTH_CACHE_TTL = 3600


def calculate_ndx100_breadth() -> dict:
    """Batch-download NDX 100 to compute % above 200d, 50d, 20d SMA."""
    global _ndx_breadth_cache, _ndx_breadth_cache_time
    import math

    now = time.time()
    if _ndx_breadth_cache is not None and (now - _ndx_breadth_cache_time) < _NDX_BREADTH_CACHE_TTL:
        return _ndx_breadth_cache

    try:
        from backend.services.ndx100 import get_ndx100_tickers

        all_tickers = sorted(get_ndx100_tickers())
        if not all_tickers:
            raise ValueError("No NDX 100 tickers available")

        df = yf.download(all_tickers, period="1y", group_by="column", progress=False, threads=True)
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
                if any(math.isnan(v) for v in (price, sma20, sma50, sma200)):
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

        if counted == 0:
            raise ValueError("No valid NDX tickers after filtering")

        result = {
            "pct_above_200d": round(above_200 / counted * 100, 1),
            "pct_above_50d": round(above_50 / counted * 100, 1),
            "pct_above_20d": round(above_20 / counted * 100, 1),
            "breadth_signal": "STRONG" if above_200 / counted >= 0.7 else "HEALTHY" if above_200 / counted >= 0.5 else "WEAKENING" if above_200 / counted >= 0.3 else "POOR",
            "sample_size": counted,
        }

        _ndx_breadth_cache = result
        _ndx_breadth_cache_time = time.time()
        return result
    except Exception:
        return {"pct_above_200d": None, "pct_above_50d": None, "pct_above_20d": None, "breadth_signal": "UNKNOWN", "sample_size": 0}


def get_full_regime() -> dict:
    """Get full market regime. Cached in memory for 1 hour."""
    global _regime_cache, _regime_cache_time
    now = time.time()
    if _regime_cache is not None and (now - _regime_cache_time) < _REGIME_CACHE_TTL:
        return _regime_cache

    spy_ma = get_moving_averages("SPY")
    qqq_ma = get_moving_averages("QQQ")

    spy_dir = classify_direction(spy_ma["price"], spy_ma["ema20"], spy_ma["sma50"], spy_ma["sma200"])
    qqq_dir = classify_direction(qqq_ma["price"], qqq_ma["ema20"], qqq_ma["sma50"], qqq_ma["sma200"])

    vix_data = yf.download("^VIX", period="5d", interval="1d", progress=False)
    close_col = vix_data["Close"]
    # yf.download may return MultiIndex columns; flatten if needed
    if hasattr(close_col, "columns"):
        close_col = close_col.iloc[:, 0]
    vix = round(float(close_col.iloc[-1]), 2)

    spy_info = {**spy_ma, "direction": spy_dir, "ticker": "SPY"}
    qqq_info = {**qqq_ma, "direction": qqq_dir, "ticker": "QQQ"}

    regime = determine_regime(spy_info, qqq_info, vix)
    result = {"spy": spy_info, "qqq": qqq_info, "regime": regime}

    _regime_cache = result
    _regime_cache_time = now
    return result
