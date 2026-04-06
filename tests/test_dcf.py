from backend.services.dcf_calculator import (
    calculate_dcf, reverse_dcf, build_sensitivity_matrix, adjust_fcf_for_sbc,
)


def test_dcf_basic():
    result = calculate_dcf(
        starting_fcf=1e9, growth_rate_1_5=0.15, growth_rate_6_10=0.08,
        terminal_growth=0.025, wacc=0.10,
        shares_outstanding=450_000_000, net_debt=2e9,
    )
    assert result["intrinsic_value_per_share"] > 0
    assert result["terminal_value_pct"] <= 1.0


def test_dcf_terminal_warning():
    """Low near-term growth with higher terminal growth triggers >50% warning."""
    result = calculate_dcf(
        starting_fcf=100e6, growth_rate_1_5=0.01, growth_rate_6_10=0.01,
        terminal_growth=0.04, wacc=0.10,
        shares_outstanding=100e6, net_debt=0,
    )
    assert result.get("terminal_value_warning") is not None


def test_sensitivity_matrix_wacc_is_fixed():
    """Spec rule: WACC cannot change between scenarios. Matrix varies growth only."""
    matrix = build_sensitivity_matrix(
        starting_fcf=1e9, base_growth_1_5=0.15, base_growth_6_10=0.08,
        terminal_growth=0.025, wacc=0.10,
        shares_outstanding=450e6, net_debt=2e9,
    )
    # All rows should use the same WACC
    for row in matrix:
        assert row["wacc"] == 0.10


def test_reverse_dcf():
    result = reverse_dcf(
        current_price=250.0, starting_fcf=1e9,
        shares_outstanding=450e6, net_debt=2e9,
    )
    assert "implied_growth_rate" in result
    assert isinstance(result["implied_growth_rate"], float)


def test_sbc_adjustment():
    adjusted = adjust_fcf_for_sbc(fcf=1e9, sbc=150e6, revenue=1e9)
    assert adjusted == 1e9 - 150e6  # SBC > 10% of revenue, so subtract


def test_sbc_no_adjustment_below_threshold():
    adjusted = adjust_fcf_for_sbc(fcf=1e9, sbc=50e6, revenue=1e9)
    assert adjusted == 1e9  # SBC = 5% < 10%, no adjustment
