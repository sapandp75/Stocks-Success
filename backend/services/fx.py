"""USD/GBP exchange rate — fetched on first use, cached 24h, hardcoded fallback."""

import time
import logging

logger = logging.getLogger(__name__)

_FALLBACK_RATE = 0.80
_cached_rate: float | None = None
_cached_time: float = 0
_TTL = 86400  # 24 hours


def get_usd_gbp_rate() -> float:
    """Get current USD/GBP rate. Falls back to 0.80 on failure."""
    global _cached_rate, _cached_time

    if _cached_rate is not None and (time.time() - _cached_time) < _TTL:
        return _cached_rate

    try:
        import yfinance as yf
        data = yf.download("GBPUSD=X", period="1d", interval="1d", progress=False)
        close = data["Close"]
        if hasattr(close, "columns"):
            close = close.iloc[:, 0]
        rate = round(1.0 / float(close.iloc[-1]), 4)  # USD->GBP = 1/GBPUSD
        _cached_rate = rate
        _cached_time = time.time()
        logger.info("USD/GBP rate updated: %.4f", rate)
        return rate
    except Exception:
        logger.warning("Failed to fetch USD/GBP rate, using fallback %.2f", _FALLBACK_RATE)
        _cached_rate = _FALLBACK_RATE
        _cached_time = time.time()
        return _FALLBACK_RATE
