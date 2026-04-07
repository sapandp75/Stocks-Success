# Market Breadth Design

> Resolve the current spec/code mismatch around breadth by defining a deterministic, fast-enough, fail-soft market breadth service for Gate 0 regime decisions.

**Date:** 2026-04-06
**Status:** Design complete, ready for implementation
**Primary files:** `backend/services/regime_checker.py`, `backend/services/sp500.py`, `backend/routers/regime.py`, `frontend/src/components/BreadthGauge.jsx`, `frontend/src/pages/RegimePage.jsx`

---

## Problem

The platform currently has three conflicting breadth ideas:

1. The options spec says Gate 0 should include market breadth.
2. The enrichment spec describes breadth as a sampled estimate.
3. The current code is moving toward full-universe batch download to remove randomness.

This needs a single design because breadth is not cosmetic. It affects whether the app recommends `DEPLOY`, `CAUTIOUS`, `DEFENSIVE`, or `CASH`.

---

## Decision

Use a **deterministic full-universe breadth calculation by default**, with a **deterministic sector-balanced fallback sample** only when the full run fails or returns unusable coverage.

Do not use random sampling.

Rationale:

- Full-universe breadth is materially more trustworthy for a regime gate than a 50-name estimate.
- A single batch `yf.download()` call is usually cheaper and faster than hundreds of sequential ticker calls.
- Random samples create non-reproducible regime outputs, which is unacceptable for a decision gate.
- A deterministic fallback prevents the endpoint from turning brittle when batch download partially fails.

---

## Design Goals

1. Same market state should produce the same breadth result.
2. Breadth enrichment must not break the regime endpoint.
3. Breadth should improve the regime verdict, not dominate it.
4. UI must show confidence and coverage, not just one percentage.
5. Failures must be visible in the payload, not silently converted into fake certainty.

---

## Breadth Model

### Core Metrics

Breadth payload should expose:

```python
{
  "as_of": "2026-04-06",
  "method": "full_universe" | "sector_sample" | "stale_cache" | "unavailable",
  "universe_size": 503,
  "sample_size": 487,
  "coverage_pct": 96.8,
  "pct_above_200d": 58.9,
  "pct_above_50d": 46.2,
  "pct_above_20d": 41.5,
  "breadth_signal": "HEALTHY",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "sector_breakdown": [
    {"sector": "Technology", "count": 68, "pct_above_200d": 64.7, "pct_above_50d": 51.5},
  ],
  "notes": []
}
```

Minimum required for MVP scoring:

- `pct_above_200d`
- `pct_above_50d`
- `breadth_signal`
- `sample_size`
- `coverage_pct`
- `method`

### Why add 20d breadth

`pct_above_200d` captures structural health.
`pct_above_50d` captures intermediate participation.
`pct_above_20d` gives an early read on thrust or loss of thrust.

The regime verdict should still anchor on 200d/50d. The 20d metric is diagnostic and useful in the UI even if not initially scored.

---

## Universe Definition

Primary universe: current S&P 500 constituents from `get_sp500_tickers()`.

Normalization rules:

- Replace `.` with `-` to match Yahoo symbols.
- Sort tickers alphabetically before batch download.
- Keep the raw constituent count in the payload as `universe_size`.
- Only include symbols with enough data for the requested moving average in the effective sample.

Why sorted order matters:

- deterministic batching
- deterministic debug logs
- reproducible fallback slices

---

## Computation Strategy

### Primary Path: Full-Universe Batch Download

1. Fetch sorted S&P 500 tickers.
2. Call `yf.download(tickers, period="1y", group_by="column", progress=False, threads=True)`.
3. Use the `Close` panel only.
4. For each ticker:
   - drop NaNs
   - require at least 200 closes
   - compute last close, SMA20, SMA50, SMA200
5. Count how many names are above each moving average.
6. Compute percentages from the counted universe only.

This is the default because it is deterministic and aligns with the seriousness of Gate 0.

### Secondary Path: Deterministic Sector-Balanced Fallback

If the batch download fails, or coverage is too low, compute breadth from a deterministic sample:

- build per-sector ticker buckets from cached fundamentals or sector metadata already available during peer work
- sort tickers within each sector
- take the first `n` names from each sector proportional to sector size, with a minimum floor per sector
- target 80-120 names total, not 50

Fallback should be deterministic across calls on the same day.

Do not use `random.sample()` and do not shuffle candidates.

### Tertiary Path: Stale Cache

If both live paths fail:

- return the most recent cached breadth result if it is less than 24 hours old
- mark `method="stale_cache"` and lower confidence

If no cached result exists:

- return `method="unavailable"`
- keep all percentages as `None`
- do not inject fake zeros

---

## Coverage Rules

Coverage matters as much as the percentage itself.

Suggested confidence mapping:

| Coverage | Confidence | Allowed for scoring |
|----------|------------|---------------------|
| `>= 90%` | `HIGH` | Yes |
| `75% - 89.9%` | `MEDIUM` | Yes, but half-weight |
| `50% - 74.9%` | `LOW` | UI only, no verdict impact |
| `< 50%` | `LOW` | Treat as unavailable |

This prevents a misleading regime shift because only half the universe came back from Yahoo.

---

## Signal Classification

Classify breadth primarily from `% above 200d`:

| `% Above 200d` | Signal | Interpretation |
|----------------|--------|----------------|
| `>= 70%` | `STRONG` | Broad participation, healthy tape |
| `50% - 69.9%` | `HEALTHY` | Constructive but not euphoric |
| `30% - 49.9%` | `WEAKENING` | Narrow leadership, caution |
| `< 30%` | `POOR` | Weak participation, defensive posture |

Optional refinement:

- If `pct_above_200d` is `HEALTHY` but `pct_above_50d < 40%`, add note: "internal deterioration".
- If `pct_above_200d` is `WEAKENING` but `pct_above_20d > pct_above_50d > pct_above_200d`, add note: "early breadth recovery".

Those notes should guide interpretation before they affect verdict math.

---

## Regime Scoring Integration

Breadth should be a modifier, not the sole driver.

Current regime logic scores only SPY, QQQ, and VIX. Add breadth as a bounded overlay:

| Breadth Signal | Confidence | Score Adjustment |
|----------------|------------|------------------|
| `STRONG` | `HIGH` | `+0.5` |
| `HEALTHY` | `HIGH` | `+0.25` |
| `WEAKENING` | `HIGH` | `-0.5` |
| `POOR` | `HIGH` | `-1.0` |
| any | `MEDIUM` | half the above |
| any | `LOW` | `0` |

Guardrails:

- VIX `> 35` remains a hard `CASH` override.
- Breadth alone cannot upgrade `DEFENSIVE` to `DEPLOY`.
- Breadth can downgrade an otherwise borderline setup.
- If breadth is unavailable, preserve existing SPY/QQQ/VIX scoring and surface the missing enrichment explicitly.

This keeps breadth important but avoids overfitting a single metric.

---

## API Contract

`GET /api/regime` should always return regime data even if breadth fails.

Breadth field rules:

- never omit `breadth`
- return a structured payload with `method` and `confidence`
- attach `breadth_error` only if something truly failed internally

Recommended response shape:

```python
{
  "spy": {...},
  "qqq": {...},
  "regime": {...},
  "breadth": {
    "method": "full_universe",
    "confidence": "HIGH",
    "pct_above_200d": 58.9,
    "pct_above_50d": 46.2,
    "sample_size": 487,
    "coverage_pct": 96.8,
    "breadth_signal": "HEALTHY",
    "notes": []
  }
}
```

Avoid the current `data["breadth"] = None` pattern because it hides whether breadth is absent, stale, degraded, or simply not computed yet.

---

## Caching

Use two cache layers:

### In-Memory TTL

- TTL: 1 hour
- Use for repeated dashboard loads
- Safe because breadth changes slowly relative to intraday UI refreshes

### Persistent SQLite Cache

Add a `regime_breadth_cache` table if the app needs resilience across restarts:

```sql
CREATE TABLE IF NOT EXISTS regime_breadth_cache (
  cache_key TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

Why persist:

- preserves last known breadth across app restarts
- enables stale-cache fallback
- supports debugging by showing last successful calculation

MVP can ship with memory cache only, but the long-term design should include SQLite cache because regime is a daily workflow primitive.

---

## Observability

The service should log:

- chosen method
- universe size
- sample size
- coverage percentage
- calculation duration
- fallback activation
- exception summary when degradation occurs

Example:

```text
breadth_calculated method=full_universe universe=503 sample=487 coverage=96.8 duration_ms=1820 signal=HEALTHY
```

Without this, breadth failures become invisible and the user cannot tell whether the regime is based on real participation or missing data.

---

## Frontend Behavior

`BreadthGauge.jsx` should stop presenting breadth as a single clean percentage without context.

Recommended UI additions:

- show `method`: "Full universe", "Sector-balanced sample", or "Last successful cache"
- show `coverage_pct`
- show confidence badge
- show note if breadth is degraded or stale
- optionally add a tiny 20d / 50d / 200d participation strip

Visual rules:

- `HIGH` confidence: normal styling
- `MEDIUM`: amber sublabel
- `LOW` or `stale_cache`: muted card with warning text
- `unavailable`: render an explicit unavailable state, not a hidden card

This matters because a user may otherwise assume the gauge is precise when it was derived from a reduced sample.

---

## Failure Modes

### Yahoo returns partial data

Response:

- compute from valid names only
- lower confidence if coverage drops below threshold

### Yahoo batch request fails entirely

Response:

- use deterministic sector sample
- if sample also fails, use stale cache

### Universe source fails

Response:

- use cached fallback tickers from `sp500_fallback.json`
- log the source degradation

### Breadth unavailable

Response:

- return structured unavailable payload
- do not change regime score
- show visible UI warning

---

## Test Plan

Add tests for:

1. Full-universe breadth is deterministic given fixed price history.
2. Coverage calculation excludes tickers with fewer than 200 bars.
3. Signal thresholds map correctly at boundary values.
4. Low coverage suppresses score impact.
5. Fallback order is full universe -> sector sample -> stale cache -> unavailable.
6. Regime verdict remains available when breadth fails.
7. API payload always includes `breadth.method` and `breadth.confidence`.

Good test shape:

- mock `get_sp500_tickers`
- mock `yf.download`
- provide synthetic `Close` frames with known above/below MA counts

---

## Rollout Plan

1. Stabilize `calculate_market_breadth()` around the full-universe deterministic path.
2. Add structured payload fields: `method`, `coverage_pct`, `confidence`, `as_of`.
3. Add bounded breadth score integration inside `determine_regime()` or a small wrapper around it.
4. Update `GET /api/regime` to always return structured breadth.
5. Improve `BreadthGauge.jsx` to display confidence and degradation state.
6. Add tests before changing verdict math.

---

## Recommended MVP Cut

If implementation time is limited, the best first version is:

- full-universe batch download
- in-memory 1h cache
- deterministic structured payload
- coverage and confidence fields
- no random fallback
- no verdict scoring changes yet

Then phase 2:

- sector-balanced fallback
- SQLite stale cache
- breadth contribution to regime score
- sector breakdown UI

This sequence fixes the current correctness issue first, then adds sophistication without destabilizing Gate 0.
