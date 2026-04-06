"""Unit tests for Gemini analyzer — no API calls."""

import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.gemini_analyzer import (
    _build_context_string,
    _parse_sections,
    GeminiRateLimiter,
)


# --- _build_context_string tests ---

def test_build_context_string():
    """Verify output contains provided data."""
    context = {
        "fundamentals": {"revenue": 1_000_000, "margin": 0.25},
        "technicals": {"rsi": 45},
        "peers": ["MSFT", "GOOG"],
    }
    result = _build_context_string(context)
    assert "revenue" in result
    assert "1000000" in result
    assert "margin" in result
    assert "rsi" in result
    assert "MSFT" in result
    assert "GOOG" in result


def test_build_context_string_empty():
    """Empty dict returns empty string, no crash."""
    assert _build_context_string({}) == ""
    assert _build_context_string(None) == ""


# --- _parse_sections tests ---

def test_parse_sections_basic():
    """Parse markdown with ### Section N headers."""
    text = """
### Section 1: Data Snapshot & First Impression
Revenue is $10B, margins are healthy.

### Section 2: First Impression (Deep)
The market is pricing in 15% growth.

### Section 3: Bear Case
Competition is intensifying.

### Section 4: Bull Case
Strong moat and pricing power.

### Section 5: Valuation
Reverse DCF implies 8% growth.

### Section 6: Whole Picture
Sector tailwinds are strong.

### Section 7: Self-Review
Possible anchoring bias on historical growth.

### Section 8: Verdict + Entry Grid + Exit Playbook
BUY with medium conviction.
"""
    sections = _parse_sections(text)
    assert "data_snapshot" in sections
    assert "first_impression" in sections
    assert "bear_case" in sections
    assert "bull_case" in sections
    assert "valuation" in sections
    assert "whole_picture" in sections
    assert "self_review" in sections
    assert "verdict" in sections
    assert "Revenue" in sections["data_snapshot"]
    assert "Competition" in sections["bear_case"]
    assert "BUY" in sections["verdict"]


def test_parse_sections_empty():
    """Empty text returns empty dict."""
    assert _parse_sections("") == {}
    assert _parse_sections(None) == {}
    assert _parse_sections("   ") == {}


# --- GeminiRateLimiter tests ---

def test_rate_limiter_allows():
    """Fresh limiter should allow requests."""
    limiter = GeminiRateLimiter(max_rpm=5, max_rpd=100)
    assert limiter.acquire() is True
    assert limiter.seconds_until_available() == 0


def test_rate_limiter_blocks_rpm():
    """After max_rpm requests, should block."""
    limiter = GeminiRateLimiter(max_rpm=3, max_rpd=100)
    for _ in range(3):
        assert limiter.acquire() is True
    assert limiter.acquire() is False
    assert limiter.seconds_until_available() > 0
