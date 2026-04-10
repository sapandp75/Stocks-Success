from datetime import date

from backend.services.stockcharts import get_stockcharts_breadth
from backend.services.regime_checker import calculate_market_breadth, calculate_ndx100_breadth


def _component_score(value: float | None, bearish_thresh: float, bullish_thresh: float, *, invert: bool = False) -> float | None:
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
    Weighted 0-10 heuristic breadth composite from 6 components.
    Each component scores 0 (bearish) / 0.5 (neutral) / 1.0 (bullish).

    Component thresholds:
      NYSI (weight 3): Cumulative McClellan — below -500 = deep bearish, above 0 = bullish
      S&P % above 200d (weight 2): Structural participation — below 40% = poor, above 60% = broad
      BPSPX (weight 2): Point & figure bullish % — below 30% = washed out, above 50% = majority bullish
      NYMO (weight 1): McClellan oscillator thrust — below -20 = selling pressure, above +20 = buying
      NYHL (weight 1): Net new highs — below -50 = more lows, above +50 = more highs
      CPC (weight 1, inverted): Put/call ratio — above 1.2 = extreme fear (bearish), below 0.7 = complacent (bullish breadth)
    """
    components = [
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
    categories_present = {"participation": False, "internals": False, "sentiment": False}

    for i, (weight, score) in enumerate(components):
        if score is not None:
            total_weight += weight
            weighted_sum += weight * score
            # Track which categories have data
            if i in (1, 2):  # S&P % above 200d, BPSPX
                categories_present["participation"] = True
            elif i in (0, 3, 4):  # NYSI, NYMO, NYHL
                categories_present["internals"] = True
            elif i == 5:  # CPC
                categories_present["sentiment"] = True

    # Require at least 2 of 3 categories for a meaningful verdict
    categories_met = sum(categories_present.values())
    if total_weight == 0 or categories_met < 2:
        return 0.0, "UNKNOWN"

    raw = round(weighted_sum / total_weight * 10)  # whole number — heuristic, not precise

    if raw < 3:
        verdict = "RISK-OFF"
    elif raw <= 6:
        verdict = "CAUTION"
    else:
        verdict = "RISK-ON"

    return float(raw), verdict


def _verdict_note(verdict: str, score: float) -> str:
    if verdict == "UNKNOWN":
        return "Insufficient data — breadth verdict unavailable."
    if verdict == "RISK-OFF":
        return f"Breadth composite {score:.0f}/10 — majority of indicators bearish. Market internals weak."
    if verdict == "CAUTION":
        return f"Breadth composite {score:.0f}/10 — mixed signals. Some internals healthy, others deteriorating."
    return f"Breadth composite {score:.0f}/10 — broad participation. Market internals support risk-taking."


def get_combined_breadth() -> dict:
    sc_data = get_stockcharts_breadth()
    spx_breadth = calculate_market_breadth()
    ndx_breadth = calculate_ndx100_breadth()

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
