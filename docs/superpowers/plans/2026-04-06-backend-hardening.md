# Backend Hardening — Adversarial Review Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 6 CRITICAL and 9 HIGH backend findings from the adversarial review (`docs/superpowers/reviews/2026-04-06-adversarial-review.md`).

**Architecture:** Three layers of fixes: (1) infrastructure hardening (database, validation, logging), (2) service-level correctness (rate limiter, peers, earnings, caching), (3) router-level safety (Pydantic models, bear case bug, scan backgrounding).

**Tech Stack:** FastAPI, SQLite, Pydantic, Python threading, Python logging

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/validators.py` | Ticker validation + Pydantic request models |
| Modify | `backend/database.py` | Context manager, busy_timeout |
| Create | `backend/logging_config.py` | Structured logging setup |
| Modify | `backend/main.py` | Wire logging on startup |
| Modify | `backend/services/gemini_analyzer.py` | Thread-safe rate limiter |
| Modify | `backend/services/peers.py` | Deterministic peer selection |
| Modify | `backend/services/earnings.py` | Signed date difference |
| Modify | `backend/services/sp500.py` | TTL-based cache expiry |
| Modify | `backend/services/regime_checker.py` | Regime caching |
| Modify | `backend/services/dcf_calculator.py` | Document g2 assumption |
| Modify | `backend/services/digest.py` | Empty list guard |
| Modify | `backend/config.py` | Remove hardcoded FX rate |
| Modify | `backend/routers/deep_dive.py` | Pydantic models, bear case fix, db context managers, logging |
| Modify | `backend/routers/watchlist.py` | Validation, db context managers |
| Modify | `backend/routers/positions.py` | Validation, db context managers |
| Modify | `backend/routers/screener.py` | Background scan with job ID |
| Modify | `backend/routers/options.py` | Validation |
| Modify | `backend/routers/regime.py` | db context managers |
| Modify | `backend/routers/research.py` | db context managers |
| Modify | All `backend/services/*.py` | Replace `except Exception: pass` with logging, db context managers |

---

### Task 1: Database Context Manager + busy_timeout (CRIT-B2, CRIT-B6)

**Files:**
- Modify: `backend/database.py:5-10`

Every `db = get_db()` / `db.close()` pair leaks on exception. No busy_timeout causes immediate `OperationalError` on write contention.

- [ ] **Step 1: Add context manager and busy_timeout to `database.py`**

```python
import sqlite3
from contextlib import contextmanager
from backend.config import DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

- [ ] **Step 2: Update `init_db` to use the context manager**

```python
def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS watchlist (
            ...
        """)
```

- [ ] **Step 3: Update ALL router files — replace `db = get_db()` / `db.close()` with `with get_db() as db:`**

Every file in `backend/routers/` and `backend/services/` uses the old pattern. Each must change from:

```python
db = get_db()
rows = db.execute("SELECT ...").fetchall()
db.close()
```

To:

```python
with get_db() as db:
    rows = db.execute("SELECT ...").fetchall()
```

**Files to update (every `get_db()` call site):**
- `backend/routers/deep_dive.py` — 3 call sites (lines 56, 174, 272)
- `backend/routers/watchlist.py` — 4 call sites (lines 9, 17, 37, 53)
- `backend/routers/positions.py` — 5 call sites (lines 11, 20, 28, 62, 84)
- `backend/routers/screener.py` — 3 call sites (lines 15, 77, 92)
- `backend/routers/regime.py` — 1 call site (line 25)
- `backend/services/research.py` — 5 call sites (lines 25, 41, 73, 106, _save_research)
- `backend/services/sentiment.py` — 4 call sites
- `backend/services/transcripts.py` — 2 call sites
- `backend/services/digest.py` — 5 call sites
- `backend/services/technicals.py` — 2 call sites
- `backend/services/financial_history.py` — 2 call sites
- `backend/services/institutional.py` — 4 call sites
- `backend/services/peers.py` — 2 call sites

- [ ] **Step 4: Verify the app starts and basic routes respond**

Run:
```bash
cd "/Users/sbakshi/Documents/Stocks Success/stock-analysis-system"
source .venv/bin/activate
python -c "from backend.database import get_db; 
with get_db() as db:
    print('OK:', db.execute('SELECT 1').fetchone()[0])"
```

Expected: `OK: 1`

- [ ] **Step 5: Commit**

```bash
git add backend/database.py backend/routers/ backend/services/
git commit -m "fix: use context manager for all DB connections + add busy_timeout

Fixes CRIT-B2 (connection leak on exception) and CRIT-B6 (no busy_timeout).
Every get_db() call now uses 'with' for guaranteed cleanup."
```

---

### Task 2: Ticker Input Validation (CRIT-B1)

**Files:**
- Create: `backend/validators.py`
- Modify: `backend/routers/deep_dive.py`
- Modify: `backend/routers/watchlist.py`
- Modify: `backend/routers/positions.py`
- Modify: `backend/routers/options.py`

- [ ] **Step 1: Create `backend/validators.py`**

```python
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


# --- Pydantic request models (HIGH-B1) ---

class DeepDivePayload(BaseModel):
    first_impression: str | None = None
    bear_case_stock: str | None = None
    bear_case_business: str | None = None
    bull_case_rebuttal: str | None = None
    bull_case_upside: str | None = None
    whole_picture: str | None = None
    self_review: str | None = None
    verdict: str | None = None
    conviction: str | None = None
    entry_grid: list[dict] | None = None
    exit_playbook: str | None = None


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
    def validate_ticker(cls, v: str) -> str:
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
    def validate_ticker(cls, v: str) -> str:
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
```

- [ ] **Step 2: Wire validation into `deep_dive.py` routes**

Replace the raw `ticker: str` path params and `data: dict = Body(...)` with validated versions:

```python
from backend.validators import validate_ticker, DeepDivePayload

@router.get("/{ticker}")
def get_deep_dive_data(ticker: str):
    ticker = validate_ticker(ticker)
    ...

@router.post("/{ticker}")
def save_deep_dive(ticker: str, data: DeepDivePayload):
    ticker = validate_ticker(ticker)
    ...

@router.post("/{ticker}/analyze")
def analyze_deep_dive(ticker: str):
    ticker = validate_ticker(ticker)
    ...
```

- [ ] **Step 3: Wire validation into `watchlist.py`**

```python
from backend.validators import validate_ticker, WatchlistEntry

@router.post("")
def add_to_watchlist(entry: WatchlistEntry):
    ...  # use entry.ticker (already validated), entry.bucket, etc.

@router.delete("/{ticker}")
def remove_from_watchlist(ticker: str):
    ticker = validate_ticker(ticker)
    ...
```

- [ ] **Step 4: Wire validation into `positions.py`**

```python
from backend.validators import validate_ticker, PositionEntry, ClosePositionPayload

@router.post("")
def add_position(entry: PositionEntry):
    ...  # use entry.ticker, entry.position_type, etc.

@router.put("/{position_id}/close")
def close_position(position_id: int, data: ClosePositionPayload):
    ...  # use data.exit_price, data.exit_reason
```

- [ ] **Step 5: Wire validation into `options.py`**

```python
from backend.validators import validate_ticker

@router.get("/scan")
def scan_options(tickers: str = Query(...)):
    ticker_list = [validate_ticker(t) for t in tickers.split(",") if t.strip()]
    ...
```

- [ ] **Step 6: Commit**

```bash
git add backend/validators.py backend/routers/
git commit -m "fix: add ticker validation + Pydantic models on all POST endpoints

Fixes CRIT-B1 (stored XSS via unvalidated ticker) and HIGH-B1 (no field validation).
Tickers restricted to 1-5 uppercase letters with optional suffix."
```

---

### Task 3: Thread-Safe Gemini Rate Limiter (CRIT-B3)

**Files:**
- Modify: `backend/services/gemini_analyzer.py:16-56`

- [ ] **Step 1: Add threading.Lock to GeminiRateLimiter**

```python
import threading

class GeminiRateLimiter:
    """Track RPM and RPD limits for Gemini API. Thread-safe."""

    def __init__(self, max_rpm: int = None, max_rpd: int = None):
        self.max_rpm = max_rpm or GEMINI_CONFIG["max_rpm"]
        self.max_rpd = max_rpd or GEMINI_CONFIG["max_rpd"]
        self._minute_timestamps: deque = deque()
        self._day_timestamps: deque = deque()
        self._lock = threading.Lock()

    def _prune(self):
        now = time.time()
        while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
            self._minute_timestamps.popleft()
        while self._day_timestamps and now - self._day_timestamps[0] > 86400:
            self._day_timestamps.popleft()

    def can_request(self) -> bool:
        with self._lock:
            self._prune()
            return (
                len(self._minute_timestamps) < self.max_rpm
                and len(self._day_timestamps) < self.max_rpd
            )

    def record_request(self):
        with self._lock:
            now = time.time()
            self._minute_timestamps.append(now)
            self._day_timestamps.append(now)

    def acquire(self) -> bool:
        """Atomic check-and-record. Returns True if request is allowed."""
        with self._lock:
            self._prune()
            if (len(self._minute_timestamps) < self.max_rpm
                    and len(self._day_timestamps) < self.max_rpd):
                now = time.time()
                self._minute_timestamps.append(now)
                self._day_timestamps.append(now)
                return True
            return False

    def seconds_until_available(self) -> int:
        with self._lock:
            self._prune()
            if (len(self._minute_timestamps) < self.max_rpm
                    and len(self._day_timestamps) < self.max_rpd):
                return 0
            if len(self._day_timestamps) >= self.max_rpd:
                return int(86400 - (time.time() - self._day_timestamps[0])) + 1
            if len(self._minute_timestamps) >= self.max_rpm:
                return int(60 - (time.time() - self._minute_timestamps[0])) + 1
            return 0
```

- [ ] **Step 2: Use `acquire()` in `generate_deep_dive` instead of separate check+record**

Replace lines 241-243 and 310:

```python
def generate_deep_dive(ticker: str, context: dict) -> dict:
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set"}

    if not _rate_limiter.acquire():
        wait = _rate_limiter.seconds_until_available()
        return {"error": f"Rate limit exceeded. Try again in {wait} seconds"}

    try:
        # ... existing code ...
        # REMOVE the _rate_limiter.record_request() call at line 310
        raw_text = response.text
        ...
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/gemini_analyzer.py
git commit -m "fix: make GeminiRateLimiter thread-safe with Lock

Fixes CRIT-B3 (TOCTOU race on daily quota). Adds atomic acquire() method."
```

---

### Task 4: Deterministic Peer Selection (CRIT-B5)

**Files:**
- Modify: `backend/services/peers.py:97-118`

- [ ] **Step 1: Replace random.shuffle with deterministic sector filtering**

Replace lines 97-118 in `get_peer_comparison`:

```python
    # Find same-sector peers from S&P 500 — deterministic selection
    try:
        sp500 = get_sp500_tickers()
    except Exception:
        sp500 = []

    # Sort candidates alphabetically for reproducibility
    candidates = sorted([t for t in sp500 if t != ticker])

    # Pre-filter: get sector for each candidate, take first 8 matches
    peer_tickers = []
    checked = 0
    for t in candidates:
        if len(peer_tickers) >= 8:
            break
        if checked >= 40:
            break
        try:
            info = yf.Ticker(t).info
            if info.get("sector") == target_sector:
                peer_tickers.append(t)
        except Exception:
            pass
        checked += 1
```

- [ ] **Step 2: Remove `import random` from the file**

- [ ] **Step 3: Commit**

```bash
git add backend/services/peers.py
git commit -m "fix: deterministic peer selection — sort alphabetically, no random.shuffle

Fixes CRIT-B5. Same call twice now returns same peers."
```

---

### Task 5: Earnings Proximity — Signed Date Difference (HIGH-B5)

**Files:**
- Modify: `backend/services/earnings.py:18-19`

- [ ] **Step 1: Fix abs() to use signed difference**

Replace the `check_earnings_proximity` function body:

```python
def check_earnings_proximity(earnings_date: str | None, expiry_date: str) -> dict:
    """Check if earnings fall within proximity_days of option expiry.
    
    Only flags risk when earnings are BEFORE or NEAR expiry (option still held).
    Options expiring BEFORE earnings don't face IV crush.
    """
    proximity = OPTIONS_PARAMS["earnings_proximity_days"]

    if not earnings_date:
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }

    try:
        ed = datetime.strptime(str(earnings_date).split(" ")[0], "%Y-%m-%d")
        exp = datetime.strptime(expiry_date, "%Y-%m-%d")
        # Positive = earnings before expiry (risk), negative = earnings after expiry (no risk)
        days_before_expiry = (exp - ed).days

        if days_before_expiry < 0:
            # Earnings AFTER expiry — no IV crush risk
            return {
                "iv_crush_risk": False,
                "days_between": abs(days_before_expiry),
                "note": f"Earnings {abs(days_before_expiry)}d after expiry. No IV crush risk.",
            }

        if days_before_expiry <= proximity:
            return {
                "iv_crush_risk": True,
                "days_between": days_before_expiry,
                "note": f"IV CRUSH RISK: Earnings {days_before_expiry}d before expiry. Avoid.",
            }
        return {
            "iv_crush_risk": False,
            "days_between": days_before_expiry,
            "note": f"Earnings {days_before_expiry}d before expiry. OK.",
        }
    except (ValueError, TypeError):
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/earnings.py
git commit -m "fix: earnings proximity uses signed difference — no false crush warnings

Fixes HIGH-B5. Options expiring before earnings no longer get IV crush flag."
```

---

### Task 6: S&P 500 Cache TTL (HIGH-B6)

**Files:**
- Modify: `backend/services/sp500.py`

- [ ] **Step 1: Add timestamp-based cache expiry**

```python
import json
import time
import urllib.request
import pandas as pd
from io import StringIO
from backend.config import SP500_FALLBACK

_cache: list[str] | None = None
_cache_time: float = 0
_CACHE_TTL = 86400  # 24 hours


def _fetch_from_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(StringIO(html))
    df = tables[0]
    return sorted(df["Symbol"].str.replace(".", "-", regex=False).tolist())


def get_sp500_tickers(use_cache: bool = True) -> list[str]:
    global _cache, _cache_time

    if _cache is not None and (time.time() - _cache_time) < _CACHE_TTL:
        return _cache

    try:
        tickers = _fetch_from_wikipedia()
        SP500_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
        SP500_FALLBACK.write_text(json.dumps(tickers))
        _cache = tickers
        _cache_time = time.time()
        return tickers
    except Exception:
        if use_cache and SP500_FALLBACK.exists():
            _cache = json.loads(SP500_FALLBACK.read_text())
            _cache_time = time.time()
            return _cache
        raise
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/sp500.py
git commit -m "fix: S&P 500 in-memory cache expires after 24 hours

Fixes HIGH-B6. Previously cached once and never refreshed."
```

---

### Task 7: Regime Caching (HIGH-B4)

**Files:**
- Modify: `backend/services/regime_checker.py:147-165`

- [ ] **Step 1: Add SQLite-backed regime cache with 1-hour TTL**

Add at the top of the file after imports:

```python
import json
from datetime import datetime
from backend.database import get_db
```

Replace `get_full_regime()`:

```python
_REGIME_CACHE_TTL = 3600  # 1 hour


def get_full_regime() -> dict:
    """Get full market regime. Cached in memory for 1 hour since regime changes max once/day."""
    # Check in-memory cache first
    global _regime_cache, _regime_cache_time
    now = time.time()
    if _regime_cache is not None and (now - _regime_cache_time) < _REGIME_CACHE_TTL:
        return _regime_cache

    spy_ma = get_moving_averages("SPY")
    qqq_ma = get_moving_averages("QQQ")

    spy_dir = classify_direction(spy_ma["price"], spy_ma["ema20"], spy_ma["sma50"], spy_ma["sma200"])
    qqq_dir = classify_direction(qqq_ma["price"], qqq_ma["ema20"], qqq_ma["sma50"], qqq_ma["sma200"])

    vix_data = yf.download("^VIX", period="5d", interval="1d", progress=False)
    close_col = vix_data["Close"]
    if hasattr(close_col, "columns"):
        close_col = close_col.iloc[:, 0]
    vix = round(float(close_col.iloc[-1]), 2)

    spy_info = {**spy_ma, "direction": spy_dir, "ticker": "SPY"}
    qqq_info = {**qqq_ma, "direction": qqq_dir, "ticker": "QQQ"}

    regime = determine_regime(spy_info, qqq_info, vix)
    result = {"spy": spy_info, "qqq": qqq_info, "regime": regime}

    _regime_cache = result
    _regime_cache_time = now
    return result


# Module-level cache
_regime_cache: dict | None = None
_regime_cache_time: float = 0
```

Also add `import time` to the imports.

- [ ] **Step 2: Commit**

```bash
git add backend/services/regime_checker.py
git commit -m "fix: cache regime data in memory with 1-hour TTL

Fixes HIGH-B4. Eliminates redundant yfinance calls on every page load."
```

---

### Task 8: Bear Case Bug Fix (HIGH-B2)

**Files:**
- Modify: `backend/routers/deep_dive.py:273-289`

- [ ] **Step 1: Fix duplicate bear case assignment**

In `analyze_deep_dive`, replace:

```python
        result.get("bear_case"),
        result.get("bear_case"),  # combined
```

With:

```python
        result.get("bear_case_stock") or result.get("bear_case"),
        result.get("bear_case_business") or result.get("bear_case"),
```

This allows the Gemini response to provide separate stock/business risk sections. If the prompt returns a single `bear_case` key, both get the same value (existing behavior), but if it returns `bear_case_stock` and `bear_case_business` separately, they'll be stored correctly.

- [ ] **Step 2: Commit**

```bash
git add backend/routers/deep_dive.py
git commit -m "fix: store bear_case_stock and bear_case_business separately

Fixes HIGH-B2. Previously both columns stored the same value."
```

---

### Task 9: mark_digest_seen Empty List Guard (HIGH-B8)

**Files:**
- Modify: `backend/services/digest.py:183-188`

- [ ] **Step 1: Add early return for empty list**

```python
def mark_digest_seen(event_ids: list[int]):
    """Mark digest events as seen."""
    if not event_ids:
        return
    with get_db() as db:
        placeholders = ",".join("?" * len(event_ids))
        db.execute(f"UPDATE digest_events SET seen = 1 WHERE id IN ({placeholders})", event_ids)
        db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/digest.py
git commit -m "fix: guard mark_digest_seen against empty list

Fixes HIGH-B8. Empty list previously generated invalid SQL."
```

---

### Task 10: Structured Logging (HIGH-B9)

**Files:**
- Create: `backend/logging_config.py`
- Modify: `backend/main.py`
- Modify: All `backend/services/*.py` files with `except Exception: pass`

- [ ] **Step 1: Create `backend/logging_config.py`**

```python
"""Logging configuration for the contrarian investing platform."""

import logging
import sys


def setup_logging():
    """Configure structured logging. Call once at startup."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )
    # Quiet noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
```

- [ ] **Step 2: Wire into `backend/main.py` startup**

Add at the top of `main.py` after imports:

```python
from backend.logging_config import setup_logging
setup_logging()
```

- [ ] **Step 3: Replace `except Exception: pass` with logging across all service files**

Pattern change in every service file:

```python
import logging

logger = logging.getLogger(__name__)

# Replace:
except Exception:
    pass

# With:
except Exception:
    logger.warning("Failed to fetch %s for %s", "description", ticker, exc_info=True)
```

**Files to update:**
- `backend/services/research.py` — lines 64, 99 (`except Exception: pass`)
- `backend/services/transcripts.py` — line 93 (`except Exception: return None`)
- `backend/services/digest.py` — lines 67, 98, 134
- `backend/services/sentiment.py` — lines 103, 150
- `backend/services/institutional.py` — lines 73, 165
- `backend/services/peers.py` — lines 91, 101, 116, 141
- `backend/services/regime_checker.py` — lines 119, 143
- `backend/services/financial_history.py` — line 121
- `backend/routers/deep_dive.py` — lines 87, 94, 101, 108, 115, 122, 141 (7 try/except blocks)
- `backend/routers/screener.py` — lines 48, 74
- `backend/routers/regime.py` — line 16

- [ ] **Step 4: Commit**

```bash
git add backend/logging_config.py backend/main.py backend/services/ backend/routers/
git commit -m "fix: add structured logging — replace all silent except:pass blocks

Fixes HIGH-B9. Every service now logs warnings on failure instead of swallowing errors."
```

---

### Task 11: Reverse DCF g2 Documentation (HIGH-B7)

**Files:**
- Modify: `backend/services/dcf_calculator.py:144-153`

- [ ] **Step 1: Document the g2 = g1 * 0.6 assumption and cap it**

```python
def reverse_dcf(
    current_price: float,
    starting_fcf: float,
    shares_outstanding: int,
    net_debt: float,
    wacc: float = DCF_DEFAULTS["wacc"],
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
) -> dict:
    """What growth rate does the market price imply? Binary search.
    
    Phase 2 growth (years 6-10) = min(g1 * 0.6, 0.12) to prevent
    unreasonably high late-stage assumptions for high-growth stocks.
    """
    target_equity = current_price * shares_outstanding + (net_debt or 0)
    low, high = -0.10, 0.50

    for _ in range(100):
        mid = (low + high) / 2
        g2 = min(mid * 0.6, 0.12)  # Cap Phase 2 at 12%
        core = _compute_dcf(starting_fcf, mid, g2, terminal_growth, wacc,
                            shares_outstanding, net_debt or 0)
        if core["equity_value"] < target_equity:
            low = mid
        else:
            high = mid

    implied = round((low + high) / 2, 4)
    return {
        "implied_growth_rate": implied,
        "implied_g2": round(min(implied * 0.6, 0.12), 4),
        "current_price": current_price,
        "interpretation": _interpret_implied(implied),
    }
```

- [ ] **Step 2: Commit**

```bash
git add backend/services/dcf_calculator.py
git commit -m "fix: cap reverse DCF Phase 2 growth at 12% and document assumption

Fixes HIGH-B7. g2 = min(g1 * 0.6, 0.12) prevents unreasonable late-stage growth."
```

---

### Task 12: Hardcoded FX Rate (HIGH-B3)

**Files:**
- Modify: `backend/config.py:14`
- Create helper in `backend/services/fx.py`

- [ ] **Step 1: Create `backend/services/fx.py` with cached FX fetch**

```python
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
```

- [ ] **Step 2: Update `config.py` — replace hardcoded constant with lazy getter**

In `config.py`, change:

```python
USD_GBP_RATE = 0.80
```

To:

```python
# FX rate is now fetched dynamically — see backend/services/fx.py
# Keep this as a fallback reference only
_USD_GBP_FALLBACK = 0.80
```

- [ ] **Step 3: Update all USD_GBP_RATE imports**

In `backend/routers/positions.py` and `backend/services/options_scanner.py`, replace:

```python
from backend.config import USD_GBP_RATE
```

With:

```python
from backend.services.fx import get_usd_gbp_rate
```

And replace all uses of `USD_GBP_RATE` with `get_usd_gbp_rate()`.

- [ ] **Step 4: Commit**

```bash
git add backend/services/fx.py backend/config.py backend/routers/positions.py backend/services/options_scanner.py
git commit -m "fix: fetch USD/GBP rate dynamically with 24h cache

Fixes HIGH-B3. Previously hardcoded at 0.80, drifting ~2.5% from reality."
```

---

### Task 13: Screener Background Scan (CRIT-B4)

**Files:**
- Modify: `backend/routers/screener.py`

This is the most complex change. The scan currently blocks the entire FastAPI process for 3-8 minutes. We need to move it to a background thread with a polling endpoint.

- [ ] **Step 1: Add background scan infrastructure to `screener.py`**

```python
import json
import threading
import logging
from fastapi import APIRouter, Query, BackgroundTasks
from backend.services.stock_screener import scan_sp500
from backend.database import get_db

router = APIRouter(prefix="/api/screener", tags=["screener"])
logger = logging.getLogger(__name__)

# In-memory scan state (single-user app)
_scan_state = {
    "status": "idle",  # idle | running | complete | error
    "progress": 0,
    "total": 0,
    "result": None,
    "error": None,
}
_scan_lock = threading.Lock()


def _run_scan_background(scan_type: str):
    """Run scan in background thread. Updates _scan_state."""
    global _scan_state
    try:
        with _scan_lock:
            _scan_state = {"status": "running", "progress": 0, "total": 503, "result": None, "error": None}

        results = scan_sp500(scan_type=scan_type)

        # Save to database
        with get_db() as db:
            db.execute(
                "INSERT INTO scan_results (scan_type, total_scanned, b1_count, b2_count, results_json, errors_json) VALUES (?, ?, ?, ?, ?, ?)",
                (scan_type, results["total_scanned"], results["b1_count"], results["b2_count"],
                 json.dumps(results, default=str), json.dumps(results["errors"], default=str)),
            )
            db.commit()

        with _scan_lock:
            _scan_state = {"status": "complete", "progress": results["total_scanned"],
                           "total": results["total_scanned"], "result": results, "error": None}
        logger.info("Scan complete: %d B1, %d B2 from %d", results["b1_count"], results["b2_count"], results["total_scanned"])

    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        with _scan_lock:
            _scan_state = {"status": "error", "progress": 0, "total": 0, "result": None, "error": str(e)}


@router.post("/scan")
def start_scan(scan_type: str = Query("weekly", enum=["daily", "weekly"])):
    """Start an S&P 500 scan. Returns immediately with job status."""
    if scan_type == "daily":
        # Daily scans are small enough to run inline
        with get_db() as db:
            rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
        tickers = [r["ticker"] for r in rows]
        if not tickers:
            return {"error": "No watchlist entries. Add stocks first or run weekly scan."}
        from backend.services.market_data import get_stock_fundamentals
        from backend.services.stock_screener import check_b1_gates, check_b1_warnings
        results = []
        for t in tickers:
            try:
                data = get_stock_fundamentals(t).value
                data["warnings"] = check_b1_warnings(data)
                results.append(data)
            except Exception as e:
                results.append({"ticker": t, "error": str(e)})
        return {"scan_type": "daily", "results": results}

    # Weekly: check if already running
    with _scan_lock:
        if _scan_state["status"] == "running":
            return {"status": "already_running", "progress": _scan_state["progress"], "total": _scan_state["total"]}

    thread = threading.Thread(target=_run_scan_background, args=(scan_type,), daemon=True)
    thread.start()
    return {"status": "started", "message": "Scan started. Poll /api/screener/scan/status for progress."}


@router.get("/scan/status")
def scan_status():
    """Poll scan progress."""
    with _scan_lock:
        state = {**_scan_state}
    # Don't send full results in status — use /latest for that
    if state["status"] == "complete":
        return {"status": "complete", "progress": state["progress"], "total": state["total"]}
    return state


@router.get("/latest")
def get_latest_scan():
    """Get most recent scan results."""
    # Check if just-completed scan is available in memory
    with _scan_lock:
        if _scan_state["status"] == "complete" and _scan_state["result"]:
            result = _scan_state["result"]
            result["is_stale"] = False
            return result

    with get_db() as db:
        row = db.execute("SELECT * FROM scan_results ORDER BY scan_date DESC LIMIT 1").fetchone()
    if not row:
        return {"error": "No scan results. Run POST /api/screener/scan?scan_type=weekly first."}
    result = json.loads(row["results_json"])
    result["scan_id"] = row["id"]
    # Check staleness
    from datetime import datetime, timedelta
    scan_date = datetime.fromisoformat(row["scan_date"])
    result["is_stale"] = (datetime.now() - scan_date) > timedelta(days=7)
    return result
```

- [ ] **Step 2: Keep the old GET /scan as deprecated redirect**

Add above the new routes:

```python
@router.get("/scan")
def run_scan_legacy(scan_type: str = Query("weekly")):
    """Deprecated: Use POST /scan instead. Kept for backwards compatibility."""
    return start_scan(scan_type=scan_type)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/screener.py
git commit -m "fix: move weekly scan to background thread with polling endpoint

Fixes CRIT-B4. POST /scan starts scan, GET /scan/status polls progress.
Daily scans remain inline (small enough). is_stale now actually checks age."
```

---

### Task 14: Replace _is_fresh Duplication (MEDIUM-B6)

**Files:**
- Create shared helper, update all 8 files

- [ ] **Step 1: Add `is_fresh` to `backend/database.py`**

```python
def is_fresh(fetched_at: str | None, ttl_hours: int) -> bool:
    """Check if a cached value is still fresh. Timezone-naive."""
    if not fetched_at:
        return False
    from datetime import datetime
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600
```

- [ ] **Step 2: Replace `_is_fresh` in all service files with the shared import**

In each file, replace:

```python
def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600
```

With:

```python
from backend.database import is_fresh
```

Files: `research.py`, `sentiment.py`, `technicals.py`, `financial_history.py`, `institutional.py`, `peers.py`

- [ ] **Step 3: Commit**

```bash
git add backend/database.py backend/services/
git commit -m "refactor: consolidate _is_fresh into shared is_fresh in database.py

Fixes MEDIUM-B6. Eliminates 8 duplicate definitions."
```

---

## Execution Order

Tasks 1-2 are **infrastructure** — do these first, as every other task depends on them.

Tasks 3-12 are **independent** — can be done in any order or in parallel.

Task 13 (background scan) is the most complex and should be done last to avoid conflicts.

Task 14 is cleanup — do after all other changes are stable.

**Estimated total: 14 tasks, ~58 steps.**

---

Plan complete and saved to `docs/superpowers/plans/2026-04-06-backend-hardening.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?