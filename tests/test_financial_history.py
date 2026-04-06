import pandas as pd
import numpy as np
from datetime import datetime
from backend.services.financial_history import _extract_financial_history


def _make_income(data: dict[str, list]) -> pd.DataFrame:
    """Build a mock income statement DataFrame like yfinance returns."""
    years = [datetime(2024, 12, 31), datetime(2023, 12, 31), datetime(2022, 12, 31), datetime(2021, 12, 31)]
    return pd.DataFrame(data, index=years[:len(list(data.values())[0])]).T


def _make_cashflow(data: dict[str, list]) -> pd.DataFrame:
    years = [datetime(2024, 12, 31), datetime(2023, 12, 31), datetime(2022, 12, 31), datetime(2021, 12, 31)]
    return pd.DataFrame(data, index=years[:len(list(data.values())[0])]).T


def _make_balance(data: dict[str, list]) -> pd.DataFrame:
    years = [datetime(2024, 12, 31), datetime(2023, 12, 31), datetime(2022, 12, 31), datetime(2021, 12, 31)]
    return pd.DataFrame(data, index=years[:len(list(data.values())[0])]).T


def test_extract_financial_history_revenue():
    """Revenue is correctly extracted from income statement."""
    income = _make_income({
        "Total Revenue": [100e9, 90e9, 80e9, 70e9],
        "Gross Profit": [60e9, 54e9, 48e9, 42e9],
        "Operating Income": [30e9, 27e9, 24e9, 21e9],
        "Net Income": [20e9, 18e9, 16e9, 14e9],
    })
    result = _extract_financial_history(income, pd.DataFrame(), pd.DataFrame())
    revenues = result["revenue"]
    assert len(revenues) == 4
    # Most recent first
    assert revenues[0]["year"] == 2024
    assert revenues[0]["value"] == 100e9
    assert revenues[-1]["year"] == 2021
    assert revenues[-1]["value"] == 70e9


def test_extract_financial_history_margins():
    """Margin calculations: numerator / revenue for each year."""
    income = _make_income({
        "Total Revenue": [100e9, 80e9],
        "Gross Profit": [60e9, 40e9],
        "Operating Income": [30e9, 20e9],
        "Net Income": [20e9, 10e9],
    })
    result = _extract_financial_history(income, pd.DataFrame(), pd.DataFrame())

    assert result["gross_margin"][0]["value"] == 0.6
    assert result["operating_margin"][0]["value"] == 0.3
    assert result["net_margin"][0]["value"] == 0.2

    assert result["gross_margin"][1]["value"] == 0.5
    assert result["operating_margin"][1]["value"] == 0.25
    assert result["net_margin"][1]["value"] == 0.125


def test_extract_financial_history_fcf():
    """FCF is correctly extracted from cashflow statement."""
    income = _make_income({
        "Total Revenue": [100e9, 90e9],
        "Operating Income": [30e9, 27e9],
        "Net Income": [20e9, 18e9],
    })
    cashflow = _make_cashflow({
        "Free Cash Flow": [25e9, 22e9],
        "Stock Based Compensation": [5e9, 4e9],
    })
    result = _extract_financial_history(income, cashflow, pd.DataFrame())

    assert result["free_cash_flow"][0]["value"] == 25e9
    assert result["free_cash_flow"][1]["value"] == 22e9
    assert result["sbc"][0]["value"] == 5e9


def test_extract_financial_history_debt_to_equity():
    """D/E ratio = debt / equity for each year."""
    income = _make_income({
        "Total Revenue": [100e9, 90e9],
        "Operating Income": [30e9, 27e9],
        "Net Income": [20e9, 18e9],
    })
    balance = _make_balance({
        "Total Debt": [50e9, 40e9],
        "Stockholders Equity": [100e9, 80e9],
    })
    result = _extract_financial_history(income, pd.DataFrame(), balance)

    assert result["debt_to_equity"][0]["value"] == 0.5
    assert result["debt_to_equity"][1]["value"] == 0.5
