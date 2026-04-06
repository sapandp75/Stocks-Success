from datetime import datetime, timedelta
from backend.services.earnings import check_earnings_proximity


def test_earnings_near_expiry():
    # Earnings 7 days before expiry = IV crush risk
    expiry = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    earnings = (datetime.now() + timedelta(days=53)).strftime("%Y-%m-%d")
    result = check_earnings_proximity(earnings, expiry)
    assert result["iv_crush_risk"] is True


def test_earnings_far_from_expiry():
    expiry = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    earnings = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = check_earnings_proximity(earnings, expiry)
    assert result["iv_crush_risk"] is False


def test_earnings_none():
    result = check_earnings_proximity(None, "2026-07-17")
    assert result["iv_crush_risk"] is False
    assert "unknown" in result["note"].lower()
