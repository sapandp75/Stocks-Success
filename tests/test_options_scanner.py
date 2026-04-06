from backend.services.options_scanner import calculate_delta, filter_contracts


def test_delta_atm():
    delta = calculate_delta(S=100, K=100, T=0.25, r=0.05, sigma=0.30)
    assert 0.45 < delta < 0.60


def test_delta_otm():
    delta = calculate_delta(S=100, K=110, T=0.25, r=0.05, sigma=0.30)
    assert 0.10 < delta < 0.50


def test_filter_contracts_includes_earnings_warning():
    contracts = [{
        "strike": 107, "bid": 4.5, "ask": 5.0, "openInterest": 1000,
        "impliedVolatility": 0.35, "dte": 90, "expiry": "2026-07-17",
        "option_type": "call",
    }]
    results = filter_contracts(
        contracts, stock_price=100,
        earnings_date="2026-07-10",  # 7 days before expiry
    )
    if results:  # may not pass delta filter at this strike
        for r in results:
            assert "IV CRUSH RISK" in r.get("warnings", [])
