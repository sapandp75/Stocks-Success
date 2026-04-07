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
