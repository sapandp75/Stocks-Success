from datetime import datetime
from backend.config import OPTIONS_PARAMS


def check_earnings_proximity(earnings_date: str | None, expiry_date: str) -> dict:
    """Check if earnings fall within proximity_days of option expiry."""
    proximity = OPTIONS_PARAMS["earnings_proximity_days"]

    if not earnings_date:
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }

    try:
        ed = datetime.strptime(str(earnings_date).split(" ")[0], "%Y-%m-%d")
        exp = datetime.strptime(expiry_date, "%Y-%m-%d")
        days_between = abs((exp - ed).days)

        if days_between <= proximity:
            return {
                "iv_crush_risk": True,
                "days_between": days_between,
                "note": f"IV CRUSH RISK: Earnings {days_between}d from expiry. Avoid.",
            }
        return {
            "iv_crush_risk": False,
            "days_between": days_between,
            "note": f"Earnings {days_between}d from expiry. OK.",
        }
    except (ValueError, TypeError):
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }
