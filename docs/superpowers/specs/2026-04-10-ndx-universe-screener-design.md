# NDX Universe Screener — Design Spec

**Date:** 2026-04-10
**Status:** Approved
**Approach:** Universe Toggle on Existing Screener Page (Approach A)

## Summary

Add Nasdaq-100 screening to the existing screener using the same B1/B2 gates. SPX and NDX run as independent scans with a universe toggle in the UI.

## Backend Changes

### `stock_screener.py`

- Rename `scan_sp500()` → `scan_universe(universe: str)`
- Dispatch ticker source based on universe:
  - `"spx"` → `get_sp500_tickers()`
  - `"ndx"` → `get_ndx100_tickers()` (existing `services/ndx100.py`)
- B1/B2 gate logic, enrichment, warnings — unchanged. Pure metric filters, universe-agnostic.

### `screener.py` router

- `_scan_state` becomes a dict keyed by universe: `{"spx": {...}, "ndx": {...}}`
- All endpoints gain `?universe=spx|ndx` query param, defaulting to `"spx"`
  - `POST /api/screener/scan?universe=ndx&scan_type=weekly`
  - `GET /api/screener/scan/status?universe=ndx`
  - `GET /api/screener/latest?universe=ndx`
- Per-universe threading lock — SPX and NDX scans can run concurrently
- Daily scan (watchlist) stays universe-independent, no change

### Database

- Add `universe TEXT DEFAULT 'spx'` column to `scan_results` table
- Existing rows become SPX results automatically
- `latest` query filters on `WHERE universe = ?`
- 7-day staleness check applies per-universe independently

## Frontend Changes

### `ScreenerPage.jsx`

- Add `universe` state: `"spx"` | `"ndx"`
- Pill toggle at top of page, above B1/B2/Both/Watchlist tabs
- Koyfin-style segmented control: two pills, active pill gets card bg + border
- Switching universe swaps displayed scan results (independent scan state per universe)
- "Scan Now" triggers scan for active universe only
- Summary cards reflect active universe
- Sort/filter state resets on universe switch
- Poll loop is per-universe

### `api.js`

- All screener functions gain optional `universe` param (default `"spx"`):
  - `startScan(scanType, universe)`
  - `getScanStatus(universe)`
  - `getLatestScan(universe)`

## Edge Cases

- **NDX/SPX overlap (~40 stocks):** No deduplication. Same stock can appear in both universes. Correct behavior.
- **Concurrent scans:** Independent state keys allow SPX + NDX to scan simultaneously.
- **Fallback data:** `ndx100_fallback.json` already exists at config path.
- **Backward compatibility:** All API defaults to `"spx"`, existing calls unchanged.
