import yfinance as yf
from backend.services.market_data import get_moving_averages


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


def get_full_regime() -> dict:
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
    return {"spy": spy_info, "qqq": qqq_info, "regime": regime}
