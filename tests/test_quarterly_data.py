import pandas as pd
import numpy as np
from datetime import datetime
from backend.services.quarterly_data import extract_quarterly_growth


def _make_quarterly(data: dict[str, list]) -> pd.DataFrame:
    """Build a mock quarterly DataFrame like yfinance returns."""
    quarters = [
        datetime(2025, 12, 31), datetime(2025, 9, 30),
        datetime(2025, 6, 30), datetime(2025, 3, 31),
        datetime(2024, 12, 31), datetime(2024, 9, 30),
        datetime(2024, 6, 30), datetime(2024, 3, 31),
        datetime(2023, 12, 31), datetime(2023, 9, 30),
        datetime(2023, 6, 30), datetime(2023, 3, 31),
    ]
    n = len(list(data.values())[0])
    return pd.DataFrame(data, index=quarters[:n]).T


def test_quarterly_revenue_yoy():
    """Q/Q and Y/Y revenue growth calculated correctly."""
    income = _make_quarterly({
        "Total Revenue": [110e9, 105e9, 100e9, 95e9, 100e9, 95e9, 90e9, 85e9, 90e9, 85e9, 80e9, 75e9],
    })
    result = extract_quarterly_growth(income_q=income, cashflow_q=pd.DataFrame())
    rev = result["revenue"]
    # Most recent quarter Y/Y: 110/100 - 1 = 10%
    assert abs(rev[0]["yoy"] - 0.10) < 0.001
    # Q/Q: 110/105 - 1 = ~4.76%
    assert abs(rev[0]["qoq"] - (110 / 105 - 1)) < 0.001


def test_quarterly_eps():
    """EPS calculated as net_income / shares."""
    income = _make_quarterly({
        "Total Revenue": [100e9, 90e9, 80e9, 70e9, 90e9, 80e9, 70e9, 60e9],
        "Net Income": [20e9, 18e9, 16e9, 14e9, 18e9, 16e9, 14e9, 12e9],
    })
    result = extract_quarterly_growth(
        income_q=income, cashflow_q=pd.DataFrame(), shares=1e9,
    )
    eps = result["eps"]
    assert eps[0]["value"] == 20.0  # 20e9 / 1e9
    assert abs(eps[0]["yoy"] - (20 / 18 - 1)) < 0.001


def test_quarterly_fcf():
    """FCF Q/Q and Y/Y from cashflow statement."""
    income = _make_quarterly({
        "Total Revenue": [100e9, 90e9, 80e9, 70e9, 90e9, 80e9, 70e9, 60e9],
    })
    cashflow = _make_quarterly({
        "Free Cash Flow": [25e9, 22e9, 20e9, 18e9, 22e9, 20e9, 18e9, 16e9],
    })
    result = extract_quarterly_growth(income_q=income, cashflow_q=cashflow)
    fcf = result["fcf"]
    assert fcf[0]["value"] == 25e9
    assert abs(fcf[0]["yoy"] - (25 / 22 - 1)) < 0.001


def test_quarterly_handles_missing_data():
    """Returns empty lists when data insufficient."""
    result = extract_quarterly_growth(income_q=pd.DataFrame(), cashflow_q=pd.DataFrame())
    assert result["revenue"] == []
    assert result["eps"] == []
    assert result["fcf"] == []
