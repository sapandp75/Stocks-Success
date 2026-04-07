# Breadth Page — Comprehensive Design Spec
**Date:** 2026-04-07
**Status:** Approved

---

## Overview

A dedicated **Breadth** tab replacing the minimal single-gauge on the Regime page. Full breadth terminal pulling live data from two sources: StockCharts (McClellan indicators, A/D, bullish %) and our existing yfinance batch download (% above MAs, own calculation). 1-hour cache on all data.

---

## Data Sources

### Source 1: StockCharts `j-sum` endpoint
Single call: `GET https://stockcharts.com/j-sum/sum?q=$NYMO`
Headers required: `Referer: https://stockcharts.com/`
Returns JSON with these sections (no API key, public endpoint):

**Market Breadth section — symbols we use:**
| Symbol | Name | What it measures |
|--------|------|-----------------|
| `$NYMO` | NYSE McClellan Oscillator | Short-term breadth momentum (EMA19 − EMA39 of NYSE A/D). Range ±150. |
| `$NYSI` | NYSE McClellan Summation | Cumulative NYMO. Negative = downtrend in breadth. |
| `$NAMO` | Nasdaq McClellan Oscillator | Same as NYMO but for Nasdaq. |
| `$NASI` | Nasdaq McClellan Summation | Cumulative NAMO. |
| `$NYAD` | NYSE Advance-Decline | Net advancing stocks today on NYSE. |
| `$NAAD` | Nasdaq Advance-Decline | Net advancing stocks today on Nasdaq. |
| `$NYHL` | NYSE New Highs−Lows | Daily 52wk new highs minus new lows, NYSE. |
| `$NAHL` | Nasdaq New Highs−Lows | Daily 52wk new highs minus new lows, Nasdaq. |
| `$CPC` | CBOE Put/Call Ratio | Above 1.0 = fear. Below 0.7 = complacency. |
| `$TRIN` | NYSE Arms Index | Volume-weighted A/D. Above 2 = panic selling. |
| `$VIX` | Volatility Index | Already in regime; shown here as context only. |

**Bullish Percent Indexes section — symbols we use:**
| Symbol | Name |
|--------|------|
| `$BPSPX` | S&P 500 Bullish % |
| `$BPNDX` | Nasdaq 100 Bullish % |
| `$BPNYA` | NYSE Bullish % |
| `$BPINFO` | Info Tech sector BP |
| `$BPFINA` | Financials sector BP |
| `$BPHEAL` | Healthcare sector BP |
| `$BPINDY` | Industrials sector BP |
| `$BPDISC` | Consumer Discretionary sector BP |
| `$BPSTAP` | Consumer Staples sector BP |
| `$BPENER` | Energy sector BP |
| `$BPMATE` | Materials sector BP |
| `$BPREAL` | Real Estate sector BP |
| `$BPCOMM` | Communication Services sector BP |
| `$BPUTIL` | Utilities sector BP |

### Source 2: yfinance batch download (existing)
Already calculated in `regime_checker.py` for S&P 500. Extend to Nasdaq 100.
- S&P 500 % above 200d/50d/20d SMA (existing)
- Nasdaq 100 % above 200d/50d/20d SMA (new — Wikipedia: `List_of_Nasdaq-100_companies`, same scrape pattern as sp500.py)

---

## Backend

### New file: `backend/services/stockcharts.py`
Single responsibility: fetch and parse the StockCharts j-sum endpoint.

```
get_stockcharts_breadth() -> dict
```
- HTTP GET with Referer header
- Parse `Market Breadth` and `Bullish Percent Indexes` sections
- Extract: close value, change, pct_change, name, date
- Cache result for 1 hour (module-level cache, same pattern as regime_checker)
- Stale TTL: 24 hours (`_STALE_TTL = 86400`). Show stale data with badge if within TTL, else return None.
- Fail-closed: on any error, return `{"error": "...", "stale": <last_good_result_or_None>}`
- Never raise — always return dict

### Extend `regime_checker.py`
Add `calculate_ndx100_breadth()` mirroring `calculate_market_breadth()`:
- Fetch Nasdaq 100 tickers from new `backend/services/ndx100.py` (Wikipedia scrape, same pattern as sp500.py)
- Same yfinance batch download, same 200d/50d/20d calculation
- 1-hour cache

### New route: `GET /api/breadth`
Returns combined breadth payload:
```json
{
  "as_of": "2026-04-07",
  "score": 4.1,
  "verdict": "CAUTION",
  "verdict_note": "...",
  "spx_breadth": { "pct_above_200d": 47, "pct_above_50d": 52, "pct_above_20d": 38, "signal": "WEAKENING", ... },
  "ndx_breadth": { "pct_above_200d": 41, ... },
  "mcclellan": {
    "nymo": { "value": 31.62, "change": 11.77, "signal": "RECOVERING" },
    "nysi": { "value": -259.87, "change": 31.63, "signal": "BEARISH" },
    "namo": { "value": 37.58, "change": 11.08, "signal": "RECOVERING" },
    "nasi": { "value": -548.59, "change": 37.57, "signal": "BEARISH" }
  },
  "advance_decline": {
    "nyad": { "value": 723, "signal": "ADVANCING" },
    "naad": { "value": 1148, "signal": "ADVANCING" },
    "nyhl": { "value": 21, "signal": "MARGINAL" },
    "nahl": { "value": 16, "signal": "MARGINAL" }
  },
  "sentiment": {
    "cpc": { "value": 0.97, "signal": "NEUTRAL_FEAR" },
    "trin": { "value": 1.03, "signal": "NEUTRAL" },
    "vix": { "value": 24.17, "signal": "ELEVATED" }
  },
  "bullish_pct": {
    "spx": 43.2, "ndx": 42.0, "nya": 46.42,
    "sectors": [
      { "symbol": "$BPINFO", "name": "Info Tech", "value": 50.7, "signal": "NEUTRAL" },
      ...
    ]
  }
}
```

### Breadth score formula
Aggregate 0–10 score from weighted components (each component scores 0/0.5/1.0 = bearish/neutral/bullish):

| Component | Weight | Bearish (0) | Neutral (0.5) | Bullish (1.0) |
|-----------|--------|-------------|---------------|----------------|
| $NYSI | 3 | < −500 | −500 to 0 | > 0 |
| S&P % above 200d | 2 | < 40% | 40–60% | > 60% |
| $BPSPX | 2 | < 30% | 30–50% | > 50% |
| $NYMO | 1 | < −20 | −20 to +20 | > +20 |
| $NYHL | 1 | < −50 | −50 to +50 | > +50 |
| $CPC | 1 | > 1.2 (extreme fear) | 0.7–1.2 | < 0.7 (complacent) |

**$CPC scores actual sentiment, not contrarian.** High CPC = fear = bearish score. The user decides what to do with the signal.

**$TRIN and $VIX** are displayed as context indicators only — they do NOT contribute to the breadth score.

Max raw score = 10. Verdict: raw < 3.0 = RISK-OFF, 3.0–6.0 = CAUTION, > 6.0 = RISK-ON.

If all components are unavailable, score defaults to 0 (RISK-OFF) — fail-closed.

---

## Frontend

### Navbar: add "Breadth" tab
Between "Options" and "Watchlist". Route: `/breadth`.

### New page: `frontend/src/pages/BreadthPage.jsx`
Fetches `/api/breadth` on mount. 1-hour auto-refresh (same as regime).

**Layout (5 sections, top to bottom):**

1. **Summary strip** — verdict pill + score + 3 key headline numbers ($NYSI, $BPSPX, % above 200d). Contrarian interpretation note.

2. **McClellan section** — 4 cards: $NYMO, $NYSI, $NAMO, $NASI. Each card shows: value, change arrow, signal badge, oscillator gauge bar (gradient track + needle at current position).

3. **Advance/Decline + Highs/Lows** — 4 cards: $NYAD, $NAAD, $NYHL, $NAHL. Value + daily change + signal badge.

4. **Participation** — 4 cards: S&P % above 200d (with 50d/20d inline), NDX % above 200d, $BPSPX, $BPNDX. Values calculated from our batch download.

5. **Sentiment & Sector Bullish %** — Left: 3 cards ($CPC, $TRIN, $VIX). Right: sector BP bar chart (all 12 sectors, sorted by value, color-coded green/amber/red at 60/40 thresholds).

### Delete `BreadthGauge.jsx`
The old single-gauge component is replaced by the full BreadthPage. Remove its import from RegimePage.jsx.

### Compact breadth row on RegimePage
Replace the old BreadthGauge section with a single compact row card:
```
[ CAUTION  4.1/10 ]   S&P 47% above 200d · $NYSI −260 · $BPSPX 43%   [ View full breadth → ]
```
Styled as a flat white card with Koyfin borders. Verdict pill on the left, 3 key numbers in the middle (muted text), link to `/breadth` on the right. No gauge, no detail — that lives on the Breadth page.

---

## Styling
Koyfin palette throughout:
- bg `#f0f1f3`, cards `#ffffff`, borders `#e2e4e8`
- green `#00a562`, amber `#d97b0e`, red `#e5484d`, text `#1a1a2e`, muted `#6b7280`
- Oscillator gauge: CSS gradient track (red → amber → green → amber → red), 2px needle

---

## Error Handling
- If StockCharts call fails: show stale data with "stale" badge if <24h old, else show "Unavailable" with grey placeholder values — never crash the page
- If NDX 100 breadth calculation fails: show S&P only, note NDX unavailable
- All sections independent — one failure doesn't block others

---

## What's Not Included (no free source)
- **NAAIM Exposure Index** — weekly survey, no API
- **Real-time intraday TRIN** — yfinance doesn't have it; StockCharts provides end-of-day only
- **McClellan historical chart** — StockCharts blocks the data download endpoint (403); we show current value only, no sparkline

---

## Files to Create/Modify
| Action | File |
|--------|------|
| CREATE | `backend/services/stockcharts.py` |
| CREATE | `backend/services/ndx100.py` |
| CREATE | `backend/routers/breadth.py` |
| CREATE | `frontend/src/pages/BreadthPage.jsx` |
| MODIFY | `backend/services/regime_checker.py` — add NDX breadth |
| MODIFY | `backend/main.py` — register breadth router |
| MODIFY | `frontend/src/App.jsx` — add /breadth route |
| MODIFY | `frontend/src/components/Navbar.jsx` — add Breadth tab |
| MODIFY | `frontend/src/api.js` — add getBreadth() |
| MODIFY | `frontend/src/pages/RegimePage.jsx` — replace BreadthGauge with compact summary row |
| DELETE | `frontend/src/components/BreadthGauge.jsx` |
