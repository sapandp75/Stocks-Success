from datetime import datetime
from backend.config import OPTIONS_PARAMS


def check_earnings_proximity(earnings_date: str | None, expiry_date: str) -> dict:
    """Check if earnings fall within proximity_days of option expiry.

    Only flags risk when earnings are BEFORE or NEAR expiry (option still held).
    Options expiring BEFORE earnings don't face IV crush.
    """
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
        # Positive = earnings before expiry (risk), negative = earnings after expiry
        days_before_expiry = (exp - ed).days

        if days_before_expiry < 0:
            # Earnings AFTER expiry — no IV crush risk
            return {
                "iv_crush_risk": False,
                "days_between": abs(days_before_expiry),
                "note": f"Earnings {abs(days_before_expiry)}d after expiry. No IV crush risk.",
            }

        if days_before_expiry <= proximity:
            return {
                "iv_crush_risk": True,
                "days_between": days_before_expiry,
                "note": f"IV CRUSH RISK: Earnings {days_before_expiry}d before expiry. Avoid.",
            }
        return {
            "iv_crush_risk": False,
            "days_between": days_before_expiry,
            "note": f"Earnings {days_before_expiry}d before expiry. OK.",
        }
    except (ValueError, TypeError):
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }
