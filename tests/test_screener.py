from backend.services.stock_screener import check_b1_gates, check_b1_warnings, check_b2_gates


def test_b1_gates_pass():
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is True


def test_b1_gates_fail_missing_margin():
    """Missing data = FAIL (fail-closed)."""
    stock = {
        "operating_margin": None, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is False


def test_b1_gates_fail_missing_pe():
    """Missing forward PE = FAIL."""
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": None,
    }
    assert check_b1_gates(stock) is False


def test_b1_gates_fail_missing_de():
    """Missing D/E = FAIL."""
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": None, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is False


def test_b1_warnings_all():
    stock = {
        "revenue_growth": 0.03, "debt_to_equity": 3.5, "short_percent": 0.12,
        "return_on_equity": 1.5, "trailing_pe": 60, "forward_pe": 15,
        "sector": "Energy", "earnings_date": "2026-04-15",
    }
    warnings = check_b1_warnings(stock)
    assert "SLOW GROWTH" in warnings
    assert "HIGH LEVERAGE" in warnings
    assert "HIGH SHORT" in warnings
    assert "LEVERAGE-DRIVEN ROE" in warnings
    assert "P/E COMPRESSION" in warnings
    assert "CYCLICAL" in warnings


def test_b2_gates_fail_closed():
    stock = {"revenue_growth": None, "gross_margin": 0.50, "total_revenue": 300e6}
    assert check_b2_gates(stock) is False
