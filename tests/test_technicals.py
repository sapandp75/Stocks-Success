"""
Tests for backend/services/technicals.py
All unit tests use synthetic price data — no API calls.
"""
import numpy as np
import pandas as pd
import pytest

from backend.services.technicals import (
    calculate_adx,
    calculate_bollinger,
    calculate_macd,
    calculate_relative_strength,
    calculate_rsi,
    calculate_support_resistance,
    calculate_volume_analysis,
    classify_stock_direction,
)


# ---------------------------------------------------------------------------
# Helpers — synthetic price series
# ---------------------------------------------------------------------------

def _rising_series(n=100, start=100.0, step=1.0):
    """Steadily rising prices."""
    return pd.Series([start + i * step for i in range(n)])


def _falling_series(n=100, start=200.0, step=1.0):
    """Steadily falling prices."""
    return pd.Series([start - i * step for i in range(n)])


def _oscillating_series(n=200, center=100.0, amplitude=5.0):
    """Oscillating prices around a center."""
    return pd.Series([center + amplitude * np.sin(i * 0.3) for i in range(n)])


def _random_ohlcv(n=100, seed=42):
    """Generate synthetic OHLCV data."""
    rng = np.random.RandomState(seed)
    close = 100 + rng.randn(n).cumsum()
    high = close + rng.uniform(0.5, 2.0, n)
    low = close - rng.uniform(0.5, 2.0, n)
    volume = rng.randint(100_000, 1_000_000, n).astype(float)
    return pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume)


# ---------------------------------------------------------------------------
# RSI tests
# ---------------------------------------------------------------------------

def test_rsi_overbought():
    close = _rising_series(100)
    rsi = calculate_rsi(close)
    assert rsi > 70, f"Rising prices should give RSI > 70, got {rsi}"


def test_rsi_oversold():
    close = _falling_series(100)
    rsi = calculate_rsi(close)
    assert rsi < 30, f"Falling prices should give RSI < 30, got {rsi}"


def test_rsi_midrange():
    close = _oscillating_series(200)
    rsi = calculate_rsi(close)
    assert 30 <= rsi <= 70, f"Oscillating prices should give RSI 30-70, got {rsi}"


# ---------------------------------------------------------------------------
# MACD tests
# ---------------------------------------------------------------------------

def test_macd_values_are_floats():
    close = _oscillating_series(100)
    result = calculate_macd(close)
    assert isinstance(result["macd"], float)
    assert isinstance(result["signal"], float)
    assert isinstance(result["histogram"], float)


def test_macd_crossover_values():
    close = _oscillating_series(200)
    result = calculate_macd(close)
    assert result["crossover"] in ("bullish", "bearish", "none")


# ---------------------------------------------------------------------------
# Bollinger Bands tests
# ---------------------------------------------------------------------------

def test_bollinger_bands_order():
    close = _oscillating_series(100)
    result = calculate_bollinger(close)
    assert result["lower"] < result["middle"] < result["upper"], (
        f"Expected lower < middle < upper, got {result['lower']}, {result['middle']}, {result['upper']}"
    )


# ---------------------------------------------------------------------------
# ADX tests
# ---------------------------------------------------------------------------

def test_adx_returns_float():
    high, low, close, _ = _random_ohlcv(100)
    adx = calculate_adx(high, low, close)
    assert isinstance(adx, float)
    assert 0 <= adx <= 100, f"ADX should be 0-100, got {adx}"


# ---------------------------------------------------------------------------
# Volume analysis tests
# ---------------------------------------------------------------------------

def test_volume_analysis_keys():
    _, _, close, volume = _random_ohlcv(100)
    result = calculate_volume_analysis(volume, close)
    for key in ("avg_20d", "relative_volume", "trend", "dry_up"):
        assert key in result, f"Missing key: {key}"


def test_volume_dry_up_detection():
    """Volume at 30% of average should trigger dry_up=True."""
    n = 30
    # 20 days of normal volume, then 10 days at 30% of normal
    normal_vol = [1_000_000.0] * 20
    low_vol = [300_000.0] * 10
    volume = pd.Series(normal_vol + low_vol)
    close = pd.Series([100.0] * n)
    result = calculate_volume_analysis(volume, close)
    assert result["dry_up"] is True, f"Expected dry_up=True when volume is 30% of avg"


# ---------------------------------------------------------------------------
# Support & Resistance tests
# ---------------------------------------------------------------------------

def test_support_resistance_structure():
    high, low, close, _ = _random_ohlcv(100)
    result = calculate_support_resistance(high, low, close)
    assert isinstance(result["support"], list)
    assert isinstance(result["resistance"], list)


# ---------------------------------------------------------------------------
# Relative Strength tests
# ---------------------------------------------------------------------------

def test_relative_strength_outperforming():
    """Stock that rises more than SPY should have positive RS."""
    ticker_close = pd.Series([100.0 + i * 2.0 for i in range(60)])
    spy_close = pd.Series([100.0 + i * 0.5 for i in range(60)])
    result = calculate_relative_strength(ticker_close, spy_close)
    assert result["rs_20d"] > 0, f"Outperforming stock should have positive RS_20d, got {result['rs_20d']}"
    assert result["rs_60d"] > 0, f"Outperforming stock should have positive RS_60d, got {result['rs_60d']}"


# ---------------------------------------------------------------------------
# Direction classification tests
# ---------------------------------------------------------------------------

def test_classify_direction_full_uptrend():
    result = classify_stock_direction(
        price=150.0, ema20=145.0, sma50=140.0, sma200=130.0
    )
    assert result == "FULL_UPTREND"


# ---------------------------------------------------------------------------
# Integration test (requires network)
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_get_full_technicals_live():
    from backend.services.technicals import get_full_technicals

    result = get_full_technicals("AAPL")
    assert "error" not in result, f"Got error: {result.get('error')}"
    required_keys = [
        "ticker", "rsi", "direction", "ema20", "sma50", "sma200",
        "adx", "macd_value", "bollinger_upper", "volume_relative",
        "rs_vs_spy_20d",
    ]
    for key in required_keys:
        assert key in result, f"Missing key in full technicals: {key}"
    assert 0 <= result["rsi"] <= 100
    assert isinstance(result["direction"], str)
