from backend.services.fund_flow import classify_fund_type, compute_13f_delta


def test_classify_fund_type():
    """Known fund names map to types."""
    assert classify_fund_type("VANGUARD GROUP INC") == "index"
    assert classify_fund_type("BLACKROCK INC.") == "index"
    assert classify_fund_type("BERKSHIRE HATHAWAY INC") == "value"
    assert classify_fund_type("ARK INVESTMENT MANAGEMENT LLC") == "growth"
    assert classify_fund_type("RANDOM HEDGE FUND LP") == "other"


def test_compute_delta_new_position():
    """New holder = net buy."""
    current = [
        {"fund_name": "Fund A", "shares": 1000, "value_usd": 100000},
    ]
    prior = []
    delta = compute_13f_delta(current, prior)
    assert len(delta["new_positions"]) == 1
    assert delta["new_positions"][0]["fund_name"] == "Fund A"
    assert delta["net_shares_change"] == 1000


def test_compute_delta_exit():
    """Exited holder = net sell."""
    current = []
    prior = [
        {"fund_name": "Fund A", "shares": 1000, "value_usd": 100000},
    ]
    delta = compute_13f_delta(current, prior)
    assert len(delta["exits"]) == 1
    assert delta["net_shares_change"] == -1000


def test_compute_delta_increase():
    """Increased position detected."""
    current = [
        {"fund_name": "Fund A", "shares": 1500, "value_usd": 150000},
    ]
    prior = [
        {"fund_name": "Fund A", "shares": 1000, "value_usd": 100000},
    ]
    delta = compute_13f_delta(current, prior)
    assert len(delta["increased"]) == 1
    assert delta["increased"][0]["change"] == 500
    assert delta["net_shares_change"] == 500
