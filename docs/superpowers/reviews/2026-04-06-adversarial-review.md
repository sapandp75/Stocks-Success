# Adversarial Review — Contrarian Investing Platform

**Date:** 2026-04-06
**Scope:** 96 files, ~18k lines. Backend (FastAPI/SQLite) + Frontend (React/Vite) + Bridge CLI.
**Reviewers:** Two parallel code-reviewer agents (backend + frontend)

## Scoreboard

| Severity | Backend | Frontend | Total |
|----------|---------|----------|-------|
| CRITICAL | 6 | 4 | **10** |
| HIGH | 9 | 9 | **18** |
| MEDIUM | 8 | 10 | **18** |
| LOW | 5 | 7 | **12** |

---

## CRITICAL

### Backend

#### CRIT-B1: No ticker input validation anywhere — stored XSS, unbounded strings

**Files:** `backend/routers/deep_dive.py:15,170,201` | `backend/routers/watchlist.py:16,51` | `backend/routers/positions.py:61`

Every route accepts a raw `ticker: str` path parameter, calls `.upper()`, then passes it into SQL queries (parameterized — so SQL injection is blocked) and stores it in SQLite. Zero validation that the ticker is a plausible stock symbol. A value like `<img src=x onerror=alert(1)>` gets stored in `deep_dives.ticker`, `watchlist.ticker`, `positions.ticker`, and rendered back to the browser.

**Fix:** Add a FastAPI validator:
```python
import re
from fastapi import Path, HTTPException

def validate_ticker(ticker: str) -> str:
    if not re.match(r'^[A-Z]{1,5}(-[A-Z]{1,2})?$', ticker.upper()):
        raise HTTPException(status_code=422, detail="Invalid ticker format")
    return ticker.upper()
```

---

#### CRIT-B2: Database connections never closed on exception — connection leak

**Files:** `backend/services/technicals.py:305-309,367-406` | `backend/services/financial_history.py:98-103,133-144` | `backend/services/institutional.py:52-54,107-113` | and every other service file

Pattern everywhere is `db = get_db()` then later `db.close()`. No `try/finally`, no context manager. If any exception is raised between `get_db()` and `db.close()`, the connection is never closed. Under a scan touching ~500 tickers, any error path leaks a connection. Accumulated leaks exhaust OS file descriptors.

**Fix:** Use context managers:
```python
with get_db() as db:
    db.execute(...)
    db.commit()
```

---

#### CRIT-B3: GeminiRateLimiter is not thread-safe — TOCTOU race on daily quota

**File:** `backend/services/gemini_analyzer.py:56,233-244`

`_rate_limiter = GeminiRateLimiter()` is a module-level singleton. `_prune()` mutates `self._minute_timestamps` and `self._day_timestamps` (both `deque` objects). FastAPI runs sync routes in a threadpool. Two concurrent requests can both pass `can_request()`, both call `record_request()`, and both hit the Gemini API, burning two RPM slots instead of one.

**Fix:** Add `threading.Lock` to the rate limiter.

---

#### CRIT-B4: `scan_sp500` blocks entire FastAPI process for 3-8 minutes

**Files:** `backend/routers/screener.py:33-85` | `backend/services/stock_screener.py:89-141`

`run_scan()` calls `scan_sp500()` synchronously. Iterates ~500 tickers, each requiring `yf.Ticker(t).info` (HTTP round-trip). At 1.5s throttle per 5 tickers, takes 3-8 minutes. No progress, no cancel, no timeout. Freezes all other requests.

**Fix:** Move to background task with job ID + polling endpoint.

---

#### CRIT-B5: `get_peer_comparison` makes up to 30 sequential yfinance calls + random peers

**File:** `backend/services/peers.py:97-142`

Checks up to 30 random S&P 500 tickers to find 8 same-sector peers. `random.shuffle(candidates)` means peers differ on every call. Two calls to `get_peer_comparison("ADBE")` return different peers. Non-reproducible peer comparisons mean AI context fed to Gemini changes silently.

**Fix:** Deterministic peer selection (sort by ticker, take every nth). Maintain stable sector-to-tickers mapping.

---

#### CRIT-B6: No `PRAGMA busy_timeout` — write contention raises immediate exception

**File:** `backend/database.py:13-198`

WAL mode allows concurrent readers but only one writer. No `busy_timeout` is set, so any concurrent write attempt immediately raises `OperationalError: database is locked` instead of waiting.

**Fix:** Add `conn.execute("PRAGMA busy_timeout=5000")` to `get_db()`.

---

### Frontend

#### CRIT-F1: Silent `catch(() => {})` on every page — errors indistinguishable from empty state

**Files:** `RegimePage.jsx:47` | `WatchlistPage.jsx:10` | `PositionsPage.jsx:10-11` | `ResearchPanel.jsx:17` | `DigestList.jsx:18` | `EarningsCalendar.jsx:8` | `DeepDivePage.jsx:55`

Every `catch(() => {})` swallows errors. Network failure renders empty list indistinguishable from genuinely empty data. For a trading decision tool, this is material UX failure.

**Fix:** Add `error` state to each page. On catch, set it. Render visible error banner. Distinguish "loading", "error", and "empty" states.

---

#### CRIT-F2: Screener scan is a blocking GET with no progress polling

**Files:** `frontend/src/api.js:38` | `ScreenerPage.jsx:99`

`runScan` is a plain GET that holds connection open for 3-5 minutes. No timeout, no `AbortController`, no progress polling. `ScanProgress` renders static `scanned={0}`. If request times out, `loading` stays `true` forever.

**Fix:** POST to trigger scan, return job ID, poll status endpoint.

---

#### CRIT-F3: `window.prompt()` for financial data entry — structurally broken

**File:** `PositionsPage.jsx:20-25`

```js
const price = prompt('Exit price:')
```

No validation before `parseFloat(price)` — `"abc"` produces NaN sent to API. No error handling on `closePosition`. This is the only entry point for closing a position.

**Fix:** Inline form/modal with numeric validation and error handling.

---

#### CRIT-F4: Options tickers not URL-encoded

**File:** `frontend/src/api.js:41`

```js
export const scanOptions = (tickers) => fetchJSON(`/options/scan?tickers=${tickers}`)
```

Raw user input inserted into URL without `encodeURIComponent`. Special characters corrupt query string.

**Fix:** Use `URLSearchParams`.

---

## HIGH

### Backend

#### HIGH-B1: No Pydantic models on POST endpoints — no field validation

**File:** `backend/routers/deep_dive.py:170-198`

`data: dict = Body(...)` accepts any dictionary. Malformed payloads silently store `None` values. Same pattern in `watchlist.py`, `positions.py`.

---

#### HIGH-B2: Bear case stock/business stored as same value

**File:** `backend/routers/deep_dive.py:273-289`

Both `ai_bear_case_stock` and `ai_bear_case_business` set to `result.get("bear_case")`. The Gemini prompt produces sub-sections "Stock Risk" and "Business Risk" but they get merged into one key. Frontend shows identical text in both cards.

---

#### HIGH-B3: Hardcoded GBP/USD 0.80 — stale FX rate

**File:** `backend/config.py:14`

Used for `premium_gbp`, `theta_daily_gbp`, and P&L. Never updated. Systematically over/under-sizes every position by ~2.5%.

**Fix:** Fetch rate on startup with 24h TTL, fall back to hardcoded.

---

#### HIGH-B4: No regime caching — live yfinance calls every page load

**File:** `backend/services/regime_checker.py:147-165`

`get_full_regime()` calls `yf.download` for SPY, QQQ, VIX on every request. Regime changes once/day max. Wastes rate limit quota, adds 300-800ms latency per call.

**Fix:** Cache in SQLite with 1-hour TTL.

---

#### HIGH-B5: `abs()` on earnings proximity — wrong IV crush classification

**File:** `backend/services/earnings.py:18-32`

Options expiring BEFORE earnings get false IV crush warnings. Options expiring before the event don't face crush at all.

**Fix:** Use signed difference `(ed - exp).days` instead of `abs()`.

---

#### HIGH-B6: S&P 500 in-memory cache never expires

**File:** `backend/services/sp500.py:7,20-36`

Module-level `_cache` set once, never invalidated. S&P 500 changes monthly. After one call, stale for entire process lifetime (could be weeks).

**Fix:** Add timestamp-based staleness check (24h TTL).

---

#### HIGH-B7: Reverse DCF hardcodes g2 = g1 * 0.6

**File:** `backend/services/dcf_calculator.py:144-153`

Undocumented assumption. For implied growth of 25%, gives g2=15% — unreasonably high for Phase 2. Skews the "what is the market pricing in" narrative fed to Gemini.

---

#### HIGH-B8: `mark_digest_seen` crashes on empty list

**File:** `backend/services/digest.py:183-188`

Empty `event_ids` generates `WHERE id IN ()` — invalid SQL, raises `OperationalError`. Router checks `if event_ids:` but function has no guard.

---

#### HIGH-B9: Zero logging + all exceptions swallowed

**Files:** `backend/services/research.py:64-65,99` | `backend/services/transcripts.py:93-94`

Every `except Exception: pass` means network errors, API key failures, rate limits, and parsing bugs are invisible. Not a single `logger.warning()` in any service file.

---

### Frontend

#### HIGH-F1: DeepDivePage has no error state

**File:** `DeepDivePage.jsx:52-56`

If API returns 404/500, `data` stays `null`, `loading` drops to `false`, page renders nothing. No "ticker not found" message.

---

#### HIGH-F2: InsiderPanel: SELLING and BUYING same green color

**File:** `InsiderPanel.jsx:6-11`

```js
BUYING: '#00a562',
SELLING: '#00a562',  // same green
```

Green "SELLING (contrarian)" badge contradicts the rest of the color system where green = positive.

---

#### HIGH-F3: Placeholder shows literal `{ticker}` not actual symbol

**File:** `DeepDivePage.jsx:147`

JSX string attribute, not template literal. User sees `python bridge/deep_dive_worker.py {ticker} --post` instead of the actual ticker.

---

#### HIGH-F4: Navbar regime fetch duplicates RegimePage fetch

**File:** `Navbar.jsx:18-20`

Independent `getRegime()` on every mount. No shared state. Badge and page can show conflicting signals if data changes between two sequential requests.

---

#### HIGH-F5: OptionsPage uses `alert()` for errors

**File:** `OptionsPage.jsx:20`

Blocking modal, no persistence, page left in indeterminate state after dismissal.

---

#### HIGH-F6: WatchlistPage flashes empty state before data loads

**File:** `WatchlistPage.jsx:6-11`

Initial state `[]`, no loading flag. Users briefly see "No stocks on watchlist" before data arrives.

---

#### HIGH-F7: DcfCalculator dead URLSearchParams + NaN propagation

**File:** `DcfCalculator.jsx:18-26`

`URLSearchParams` constructed and never used. Empty inputs produce `parseFloat("") === NaN` that propagates through DCF math, displaying `$NaN`.

---

#### HIGH-F8: NYSE fallback in bridge hides exchange mismatch

**File:** `bridge/deep_dive_worker.py:77-93`

NASDAQ fails silently, retries NYSE. Wrong exchange → wrong indicators. Original exception swallowed entirely.

---

#### HIGH-F9: ScreenerPage tab count rebuilds Set on every render

**File:** `ScreenerPage.jsx:221-225`

IIFE inside JSX builds 500-element Set on every render. Same computation in `getCandidates()` runs twice. Causes jank on filter keystroke.

---

## MEDIUM

### Backend

1. **Financial history cache: stale rows accumulate on refresh** — old years persist alongside new data (`financial_history.py:99-111`)
2. **Random breadth sample makes regime non-deterministic** — two calls return different signals (`regime_checker.py:97-144`)
3. **Forward DCF scenarios hardcoded** — same growth rates for utilities and hypergrowth SaaS (`deep_dive.py:45-49`)
4. **`sbc_adjusted` flag uses float `!=`** — can show True when no adjustment applied (`deep_dive.py:154`)
5. **Options chain DTE range inconsistent with filter config** — fetches 30-150 DTE, filters to 60-120 (`market_data.py:107`)
6. **`_is_fresh` duplicated in 8 files** — divergence and naive/aware timezone risk (`services/*`)
7. **Deep dive GET makes 40+ sequential HTTP calls** — cold load takes 45-90 seconds (`deep_dive.py:15-167`)
8. **Seeking Alpha RSS silently broken** — returns 403 since 2022, feature never works (`research.py:50`)

### Frontend

1. **DcfCalculator: no validation on terminal_growth >= WACC** — produces silently wrong results (`DcfCalculator.jsx:9,77`)
2. **Pass rate calculation double-counts Both stocks** (`ScreenerPage.jsx:198`)
3. **`$${price?.toFixed(2)}` renders `$undefined`** when price is null (`DeepDivePage.jsx:71,121`)
4. **`data.direction.includes()` without null guard** — TypeError on null direction (`RegimePage.jsx:14-15`)
5. **CollapsibleSection: no aria-expanded** — inaccessible to screen readers (`CollapsibleSection.jsx:8-19`)
6. **PositionsPage tab count recomputes filter twice per render** (`PositionsPage.jsx:56-59`)
7. **ResearchPanel uses raw `fetch()` instead of `api.js`** — skips error checking (`ResearchPanel.jsx:15`)
8. **BreadthGauge SVG arc calculation incorrect for edge cases** (`BreadthGauge.jsx:29-30`)
9. **AnalystBar: price outside range silently clamped** — no indicator shown (`AnalystBar.jsx:15`)
10. **SensitivityMatrix: `matrix[0].wacc` not null-guarded** (`SensitivityMatrix.jsx:7`)

## LOW

### Backend

1. `is_stale` always False — hardcoded TODO (`screener.py:98`)
2. Fragile direction classification elif ordering (`regime_checker.py:5-18`)
3. Theta divides by 365 not 252 — underestimates daily decay by ~45% (`options_scanner.py:21`)
4. TradingView exchange fallback incomplete — misses ARCA, CBOE (`deep_dive_worker.py:62-92`)
5. Test suite has no mocking — fails without network access (`tests/*`)

### Frontend

1. `fmt()` defined independently in 4 files with inconsistent behavior
2. `deep_dive_worker.py --get` has no error handling (`deep_dive_worker.py:155-157`)
3. Hardcoded `~503 stocks processed` — S&P count changes (`ScreenerPage.jsx:70`)
4. No `<meta description>`, no favicon, no CSP header (`index.html`)
5. `StockCard` uses `alert()` for watchlist confirmation (`StockCard.jsx:26-29`)
6. `AiAnalyzeButton` detects rate limiting by string matching `"429"` (`AiAnalyzeButton.jsx:15`)
7. `SparklineGrid` label says "4yr" but backend provides 5 years (`SparklineGrid.jsx:74`)

---

## Systemic Observations

1. **"Fail silently on everything"** is the most dangerous systemic issue. ~30 `try/except: pass` blocks mean the analyst has no way to know if Gemini received full context or zero enrichment data. There is no data completeness check before calling Gemini.

2. **Single-process architecture is correctly chosen** for a personal tool, but its implications aren't respected. The scan must be backgrounded. The deep-dive cold load must be split.

3. **Financial calculation layer is solid.** DCF math, fail-closed gates, SBC adjustment, Black-Scholes delta are all correct. These are the most important parts and they work.

4. **Seeking Alpha RSS is silently broken** — returns 403 for non-subscribers since 2022. Feature never works.

5. **No logging anywhere.** Not a single `logger.warning()` or `logger.error()` call exists in any service file. Infrastructure failures are completely invisible.
