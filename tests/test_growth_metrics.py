from backend.services.growth_metrics import (
    calc_roic, calc_fcf_yield, calc_ev_ebit, calc_buyback_yield,
    calc_accruals_ratio, calc_piotroski, calc_revenue_cagr,
)


def test_roic():
    """ROIC = NOPAT / Invested Capital."""
    roic = calc_roic(
        operating_income=30e9, tax_rate=0.21,
        total_assets=200e9, current_liabilities=50e9, cash=20e9,
    )
    # NOPAT = 30e9 * 0.79 = 23.7e9
    # Invested Capital = 200e9 - 50e9 - 20e9 = 130e9
    # ROIC = 23.7 / 130 = 0.1823
    assert abs(roic - 0.1823) < 0.001


def test_roic_zero_invested_capital():
    roic = calc_roic(
        operating_income=10e9, tax_rate=0.21,
        total_assets=50e9, current_liabilities=50e9, cash=0,
    )
    assert roic is None


def test_fcf_yield():
    """FCF yield = FCF / market cap."""
    assert abs(calc_fcf_yield(fcf=10e9, market_cap=200e9) - 0.05) < 0.001


def test_fcf_yield_negative_fcf():
    result = calc_fcf_yield(fcf=-5e9, market_cap=200e9)
    assert result < 0


def test_ev_ebit():
    """EV/EBIT = enterprise value / EBIT."""
    assert abs(calc_ev_ebit(ev=300e9, ebit=30e9) - 10.0) < 0.1


def test_ev_ebit_zero():
    assert calc_ev_ebit(ev=300e9, ebit=0) is None


def test_buyback_yield():
    """Positive yield when shares decrease."""
    yld = calc_buyback_yield(shares_history=[1000e6, 1050e6, 1100e6])
    assert yld > 0  # shares decreasing = positive buyback yield


def test_buyback_yield_dilution():
    """Negative yield when shares increase."""
    yld = calc_buyback_yield(shares_history=[1100e6, 1050e6, 1000e6])
    assert yld < 0


def test_accruals_ratio():
    """Accruals = (NI - OCF) / Total Assets."""
    ratio = calc_accruals_ratio(
        net_income=20e9, operating_cashflow=25e9, total_assets=200e9,
    )
    # (20 - 25) / 200 = -0.025 (negative = good, cash > earnings)
    assert abs(ratio - (-0.025)) < 0.001


def test_piotroski_perfect():
    """A company with all 9 signals should score 9."""
    score = calc_piotroski(
        net_income=10e9,            # positive = 1
        ocf=12e9,                   # positive = 1
        roa_current=0.08,           # > roa_prior = 1
        roa_prior=0.06,
        ocf_gt_ni=True,             # OCF > NI = 1
        leverage_current=0.4,       # < leverage_prior = 1
        leverage_prior=0.5,
        current_ratio_current=1.8,  # > prior = 1
        current_ratio_prior=1.5,
        shares_current=1000e6,      # <= prior = 1 (no dilution)
        shares_prior=1000e6,
        gross_margin_current=0.45,  # > prior = 1
        gross_margin_prior=0.40,
        asset_turnover_current=0.7, # > prior = 1
        asset_turnover_prior=0.6,
    )
    assert score == 9


def test_revenue_cagr():
    """3-year CAGR from revenue history."""
    # [100, 90, 80, 70] most recent first
    # 3yr CAGR: (100/70)^(1/3) - 1 = 12.62%
    cagr = calc_revenue_cagr([100e9, 90e9, 80e9, 70e9], years=3)
    assert abs(cagr - 0.1262) < 0.005


def test_revenue_cagr_insufficient():
    cagr = calc_revenue_cagr([100e9], years=3)
    assert cagr is None
