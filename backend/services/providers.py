"""
Data provider abstraction. Each data function tries primary source,
falls back to secondary, tracks data quality.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DataResult:
    """Wraps any data fetch with provenance metadata."""
    value: Any
    source: str  # "yfinance", "fmp", "finnhub", "edgar", "fallback"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_stale: bool = False
    is_fallback: bool = False
    missing_fields: list[str] = field(default_factory=list)

    @property
    def completeness(self) -> float:
        """0.0 to 1.0 — fraction of expected fields present."""
        if not self.missing_fields:
            return 1.0
        return max(0, 1.0 - len(self.missing_fields) / 20)


def try_providers(primary_fn, fallback_fn=None, primary_name="yfinance", fallback_name="fallback"):
    """Try primary data source, fall back to secondary on failure."""
    try:
        result = primary_fn()
        return DataResult(value=result, source=primary_name)
    except Exception as primary_err:
        if fallback_fn:
            try:
                result = fallback_fn()
                return DataResult(value=result, source=fallback_name, is_fallback=True)
            except Exception:
                pass
        raise primary_err
