import math
import time
from datetime import date

import yfinance as yf

from backend.services.market_data import get_moving_averages

# Module-level regime cache (1 hour TTL — regime changes max once/day)
_regime_cache: dict | None = None
_regime_cache_time: float = 0
_REGIME_CACHE_TTL = 3600

# Breadth cache (1 hour TTL — batch download of all S&P 500)
_breadth_cache: dict | None = None
_breadth_cache_time: float = 0
_BREADTH_CACHE_TTL = 3600
_BREADTH_STALE_TTL = 86400

# NDX 100 breadth cache (1 hour TTL)
_ndx_breadth_cache: dict | None = None
_ndx_breadth_cache_time: float = 0
_NDX_BREADTH_CACHE_TTL = 3600


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


def _breadth_confidence(coverage_pct: float | None) -> str:
    if coverage_pct is None:
        return "LOW"
    if coverage_pct >= 90:
        return "HIGH"
    if coverage_pct >= 75:
        return "MEDIUM"
    return "LOW"


def _breadth_signal(pct_200: float | None) -> str:
    if pct_200 is None:
        return "UNKNOWN"
    if pct_200 >= 70:
        return "STRONG"
    if pct_200 >= 50:
        return "HEALTHY"
    if pct_200 >= 30:
        return "WEAKENING"
    return "POOR"


def _breadth_payload(
    *,
    method: str,
    universe_size: int = 0,
    sample_size: int = 0,
    pct_200: float | None = None,
    pct_50: float | None = None,
    pct_20: float | None = None,
    notes: list[str] | None = None,
) -> dict:
    coverage_pct = round(sample_size / universe_size * 100, 1) if universe_size else 0.0
    confidence = _breadth_confidence(coverage_pct)
    signal = _breadth_signal(pct_200)
    notes = list(notes or [])

    if pct_200 is not None and pct_50 is not None and pct_200 >= 50 and pct_50 < 40:
        notes.append("Internal deterioration: 50d participation is lagging 200d breadth.")
    if pct_20 is not None and pct_50 is not None and pct_200 is not None:
        if 30 <= pct_200 < 50 and pct_20 > pct_50 > pct_200:
            notes.append("Early breadth recovery: short-term participation is improving first.")

    if coverage_pct < 50:
        method = "unavailable"
        confidence = "LOW"
        signal = "UNKNOWN"
        notes.append("Breadth coverage below 50%; excluded from regime scoring.")
        pct_200 = None
        pct_50 = None
        pct_20 = None

    return {
        "as_of": date.today().isoformat(),
        "method": method,
        "universe_size": universe_size,
        "sample_size": sample_size,
        "coverage_pct": coverage_pct,
        "pct_above_200d": pct_200,
        "pct_above_50d": pct_50,
        "pct_above_20d": pct_20,
        "breadth_signal": signal,
        "confidence": confidence,
        "notes": notes,
    }


def _stale_breadth_payload() -> dict | None:
    if _breadth_cache is None:
        return None
    age = time.time() - _breadth_cache_time
    if age >= _BREADTH_STALE_TTL:
        return None

    stale = dict(_breadth_cache)
    stale["method"] = "stale_cache"
    stale["confidence"] = "LOW" if stale.get("confidence") == "HIGH" else stale.get("confidence", "LOW")
    stale["notes"] = list(stale.get("notes", [])) + ["Using last successful breadth cache."]
    return stale


def _breadth_score_adjustment(breadth: dict | None) -> float:
    if not breadth:
        return 0.0

    confidence = breadth.get("confidence")
    signal = breadth.get("breadth_signal")
    if signal == "UNKNOWN" or confidence == "LOW":
        return 0.0

    adjustments = {
        "STRONG": 0.5,
        "HEALTHY": 0.25,
        "WEAKENING": -0.5,
        "POOR": -1.0,
    }
    adjustment = adjustments.get(signal, 0.0)
    if confidence == "MEDIUM":
        adjustment /= 2
    return adjustment


def _score_to_verdict(score: float) -> tuple[str, int]:
    if score >= 3:
        return "DEPLOY", 5
    if score >= 2:
        return "CAUTIOUS", 2
    if score >= 1:
        return "DEFENSIVE", 0
    return "CASH", 0


def calculate_vix_tax(vix: float) -> dict:
    """Calculate how much extra premium you pay vs VIX at 15 (historical calm)."""
    baseline_vix = 15.0
    if vix <= baseline_vix:
        return {"premium_premium_pct": 0, "note": f"VIX at {vix} — premiums at normal levels."}

    premium_pct = round((vix - baseline_vix) / baseline_vix * 100, 0)
    if vix > 30:
        note = (
            f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
            f"4x target likely unachievable on delta 0.25-0.40 contracts. Avoid."
        )
    elif vix > 25:
        note = (
            f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
            f"Need larger underlying move for 4x. Highest-conviction B1 only."
        )
    else:
        note = (
            f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
            f"Acceptable for B1 plays where fear is narrative, not fundamental."
        )
    return {"premium_premium_pct": int(premium_pct), "note": note}


def determine_regime(spy: dict, qqq: dict, vix: float, breadth: dict | None = None) -> dict:
    if vix > 35:
        return {
            "verdict": "CASH",
            "max_new_positions": 0,
            "spy_direction": spy["direction"],
            "qqq_direction": qqq["direction"],
            "vix": vix,
            "score": 0,
            "base_score": 0,
            "breadth_adjustment": 0,
            "vix_tax": calculate_vix_tax(vix),
            "options_note": "NO new options positions. VIX extreme — capital preservation.",
        }

    spy_score = DIRECTION_SCORES.get(spy["direction"], 1.5)
    qqq_score = DIRECTION_SCORES.get(qqq["direction"], 1.5)
    base_score = (spy_score + qqq_score) / 2

    if vix > 25:
        base_score -= 0.5
    elif vix < 20:
        base_score += 0.25

    base_verdict, _ = _score_to_verdict(base_score)
    breadth_adjustment = _breadth_score_adjustment(breadth)
    final_score = base_score + breadth_adjustment
    verdict, max_pos = _score_to_verdict(final_score)

    if base_verdict in ("DEFENSIVE", "CASH") and verdict == "DEPLOY":
        verdict, max_pos = "CAUTIOUS", 2

    vix_tax = calculate_vix_tax(vix)

    return {
        "verdict": verdict,
        "max_new_positions": max_pos,
        "spy_direction": spy["direction"],
        "qqq_direction": qqq["direction"],
        "vix": vix,
        "score": round(final_score, 2),
        "base_score": round(base_score, 2),
        "breadth_adjustment": round(breadth_adjustment, 2),
        "vix_tax": vix_tax,
        "options_note": vix_tax["note"] if verdict in ("DEPLOY", "CAUTIOUS") else "NO new positions.",
    }


def calculate_market_breadth() -> dict:
    """Calculate structured breadth metrics for the S&P 500 using a deterministic batch download."""
    global _breadth_cache, _breadth_cache_time
    now = time.time()
    if _breadth_cache is not None and (now - _breadth_cache_time) < _BREADTH_CACHE_TTL:
        return _breadth_cache

    try:
        from backend.services.sp500 import get_sp500_tickers

        all_tickers = sorted(get_sp500_tickers())
        universe_size = len(all_tickers)
        if universe_size == 0:
            raise ValueError("No S&P 500 tickers available")

        df = yf.download(
            all_tickers,
            period="1y",
            group_by="column",
            progress=False,
            threads=True,
        )
        if df.empty:
            raise ValueError("Breadth download returned no data")

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
            _breadth_cache = result
            _breadth_cache_time = time.time()
            return result
    except Exception:
        stale = _stale_breadth_payload()
        if stale is not None:
            return stale

    return _breadth_payload(
        method="unavailable",
        notes=["Live breadth data unavailable."],
    )


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


def get_full_regime() -> dict:
    """Get full market regime, including breadth. Cached in memory for 1 hour."""
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
    if hasattr(close_col, "columns"):
        close_col = close_col.iloc[:, 0]
    vix = round(float(close_col.iloc[-1]), 2)

    spy_info = {**spy_ma, "direction": spy_dir, "ticker": "SPY"}
    qqq_info = {**qqq_ma, "direction": qqq_dir, "ticker": "QQQ"}
    breadth = calculate_market_breadth()

    regime = determine_regime(spy_info, qqq_info, vix, breadth)
    result = {"spy": spy_info, "qqq": qqq_info, "regime": regime, "breadth": breadth}

    _regime_cache = result
    _regime_cache_time = now
    return result
