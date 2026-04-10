"""Shared validators for the contrarian investing platform."""

import re
from fastapi import HTTPException
from pydantic import BaseModel, field_validator


# --- Ticker validation ---

_TICKER_RE = re.compile(r'^[A-Z]{1,5}(-[A-Z]{1,2})?$')


def validate_ticker(ticker: str) -> str:
    """Validate and normalize a ticker symbol. Raises 422 on invalid input."""
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(status_code=422, detail=f"Invalid ticker format: {ticker!r}")
    return t


# --- Pydantic request models ---

class DeepDivePayload(BaseModel):
    # Section 1-2: Gates & Fundamentals (generated text)
    gates_summary: str | None = None
    key_fundamentals: str | None = None
    # Section 3: Growth
    growth: str | None = None
    # Section 4-5: Bear/Bull (split)
    bear_case_stock: str | None = None
    bear_case_business: str | None = None
    bull_case_rebuttal: str | None = None
    bull_case_upside: str | None = None
    # Section 6: Valuation
    valuation: str | None = None
    # Section 7: Moat (structured)
    moat: str | None = None
    # Section 8: Opportunities & Threats
    opportunities_threats: str | None = None
    # Section 9: Smart Money
    smart_money: str | None = None
    # Section 10: Verdict
    verdict: str | None = None
    conviction: str | None = None
    entry_grid: list[dict] | None = None
    exit_playbook: str | None = None
    next_review_date: str | None = None
    # Legacy fields (backwards compat with existing data)
    first_impression: str | None = None
    whole_picture: str | None = None
    self_review: str | None = None
    # Appendix fields (stored in ai_sections_json)
    moat_structured: dict | None = None
    opportunities: str | list | None = None
    threats: str | list | None = None
    scenarios: list[dict] | dict | None = None


class WatchlistEntry(BaseModel):
    ticker: str
    bucket: str = "B1"
    thesis_note: str = ""
    entry_zone_low: float | None = None
    entry_zone_high: float | None = None
    conviction: str = "MODERATE"
    status: str = "WATCHING"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        t = v.strip().upper()
        if not _TICKER_RE.match(t):
            raise ValueError(f"Invalid ticker: {v!r}")
        return t


class PositionEntry(BaseModel):
    ticker: str
    position_type: str
    bucket: str = "B1"
    shares: float | None = None
    avg_price: float | None = None
    strike: float | None = None
    expiry: str | None = None
    premium_paid: float | None = None
    contracts: int | None = None
    thesis: str = ""
    invalidation: list[str] = []
    target_fair_value: float | None = None
    status: str = "OPEN"

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        t = v.strip().upper()
        if not _TICKER_RE.match(t):
            raise ValueError(f"Invalid ticker: {v!r}")
        return t

    @field_validator("position_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("stock", "option"):
            raise ValueError("position_type must be 'stock' or 'option'")
        return v


class ClosePositionPayload(BaseModel):
    exit_price: float
    exit_reason: str = ""
