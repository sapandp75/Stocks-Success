# Platform Enrichment — Full Build-Out Design Spec

> Transform the minimal Phase 1 dashboard into a comprehensive contrarian investing platform with technical analysis, AI-powered deep dives, MCP enrichment, and institutional data.

**Date:** 2026-04-06
**Status:** Design approved, awaiting implementation plan

---

## Architecture: Three-Tier Data Model

Every piece of data flows through one of three tiers, each progressively richer.

### Tier 1: Always-On Computed Data (Backend Python)

Available 24/7 in the dashboard. No external AI or MCP session required.

| Feature | Source | Cache TTL |
|---------|--------|-----------|
| Technical indicators (RSI, MACD, MAs, ADX, Bollinger) | yfinance OHLCV, computed in Python | 1 hour |
| Per-stock direction (UPTREND/PULLBACK/BASING/DOWNTREND) | Price vs EMA20/SMA50/SMA200 | 1 hour |
| Volume analysis (trend, dry-up detection, relative volume) | yfinance OHLCV | 1 hour |
| Support/resistance levels | Swing high/low detection from OHLCV | 1 hour |
| Relative strength vs SPY | yfinance price comparison | 1 hour |
| 5-year financial history (revenue, margins, FCF, debt) | yfinance `financials`, `cashflow`, `balance_sheet` | 6 hours |
| Insider transactions | Finnhub API | 6 hours |
| Institutional holdings summary | Finnhub API | 6 hours |
| Analyst consensus + price targets | yfinance `recommendations` + Finnhub | 6 hours |
| Market breadth (% S&P above 200d SMA) | yfinance batch (sampled, not all 500) | 1 hour |
| Peer comparison (same sector, key metrics) | yfinance sector peers | 6 hours |

### Tier 2: AI Analysis via Gemini 2.5 Pro (Backend API Call)

Available 24/7 in the dashboard. User clicks "AI Analyze" on deep dive page. Backend calls Gemini API, stores result in `deep_dives` table.

| Feature | Model | Rate Limit |
|---------|-------|------------|
| Auto-generate all 8 deep dive sections | Gemini 2.5 Pro | 5 RPM, 100 RPD |
| First impression from fundamentals + technicals | Gemini 2.5 Pro | (included in above) |
| Bear case (stock vs business) | Gemini 2.5 Pro | |
| Bull case (rebuttal + upside) | Gemini 2.5 Pro | |
| Valuation commentary | Gemini 2.5 Pro | |
| Whole picture (sector, management, moat) | Gemini 2.5 Pro | |
| Self-review (bias check, pre-mortem) | Gemini 2.5 Pro | |
| Verdict + entry grid + exit playbook | Gemini 2.5 Pro | |

**Prompt design:** The backend constructs a detailed prompt containing all Tier 1 data (fundamentals, technicals, 5yr history, insider activity, analyst targets, research articles) and asks Gemini to produce each section following the contrarian framework. The prompt enforces: bear case FIRST, fail-closed mentality, contrarian inversion (negative sentiment = opportunity).

**Cost:** Free tier. 100 deep dives/day is more than sufficient — user does 2-5 per day max.

### Tier 3: Premium Enrichment via Claude Code + MCP (Session-Based)

Available when user runs a session with Claude Code. Deeper analysis using MCP tools not available to the Python backend.

| Feature | MCP Server | Tool |
|---------|------------|------|
| Economic moat score (10 factors, 0-100) | Value Investing | `calculate_moat_score` |
| Intrinsic value (10-year DCF, Buffett params) | Value Investing | `calculate_intrinsic_value` |
| Owner earnings | Value Investing | `calculate_owner_earnings` |
| Margin of safety (moat-adjusted) | Value Investing | `calculate_margin_of_safety` |
| Position sizing (Kelly criterion) | Value Investing | `calculate_position_size` |
| Buffett Indicator (market context) | Value Investing | `calculate_buffett_indicator` |
| Risk metrics (Altman Z-Score, governance) | Value Investing | `get_risk_metrics` |
| Ownership analysis (insider + institutional signals) | Value Investing | `get_ownership_analysis` |
| Dividend safety (5-factor scoring) | Value Investing | `get_dividend_analysis` |
| TradingView indicator snapshots | mcp-tradingview-server | Full indicator data |
| Reddit sentiment on tickers | tradingview-mcp (atilaahmettaner) | Sentiment tools |
| TradingView stock screening (75+ metrics) | tradingview-mcp (atilaahmettaner) | Screening tools |

**Bridge flow:** Claude Code calls MCP tools → formats results → POSTs to `/api/deep-dive/{ticker}` via bridge script. Dashboard renders enriched analysis.

---

## Workstream Breakdown

### WS1: Technical Analysis Service

**New file:** `backend/services/technicals.py`

Computes all technical indicators from yfinance 1-year OHLCV history.

```
Functions:
  calculate_rsi(prices, period=14) -> float
  calculate_macd(prices) -> {macd, signal, histogram, crossover}
  calculate_bollinger(prices, period=20) -> {upper, middle, lower, pct_b}
  calculate_adx(high, low, close, period=14) -> float
  calculate_volume_analysis(volume, close) -> {avg_20d, relative_volume, trend, dry_up}
  calculate_support_resistance(high, low, close) -> {support: [], resistance: []}
  calculate_relative_strength(ticker_prices, spy_prices) -> {rs_20d, rs_60d}
  classify_stock_direction(price, ema20, sma50, sma200) -> str
  get_full_technicals(ticker) -> dict  # aggregates all above
```

**Cache:** Results stored in new `technicals_cache` SQLite table. TTL 1 hour.

**Integration points:**
- `StockCard` — shows direction badge + RSI chip
- `Deep Dive Section 1` — full technical panel with all indicators
- `Options Page` — technical context for timing
- `Screener` — sortable/filterable by RSI, direction

### WS2: 5-Year Financial History

**New file:** `backend/services/financial_history.py`

Fetches 4 years of annual financials from yfinance for trend analysis.

```
Functions:
  get_financial_history(ticker) -> {
    revenue: [{year, value}],
    operating_income: [{year, value}],
    net_income: [{year, value}],
    free_cash_flow: [{year, value}],
    gross_margin: [{year, value}],
    operating_margin: [{year, value}],
    net_margin: [{year, value}],
    debt_to_equity: [{year, value}],
    roic: [{year, value}],
    sbc: [{year, value}],
    shares_outstanding: [{year, value}],  # dilution check
  }
```

**Cache:** `financial_history_cache` table. TTL 6 hours.

**Integration points:**
- `Deep Dive Section 1` — sparkline charts for each metric
- Frontend component: `SparklineGrid.jsx` — renders 4-year mini-charts

### WS3: Insider + Institutional Data

**Enhance:** `backend/services/digest.py` + new functions in `backend/services/institutional.py`

```
Functions:
  get_insider_activity(ticker) -> {
    recent_buys: [{name, shares, date, value}],
    recent_sells: [{name, shares, date, value}],
    net_insider_sentiment: "BUYING" | "SELLING" | "MIXED" | "QUIET",
    notable_transactions: [],  # CEO/CFO only, >$100K
  }
  get_institutional_summary(ticker) -> {
    top_holders: [{name, shares, pct, change}],
    institutional_pct: float,
    recent_changes: "ACCUMULATING" | "DISTRIBUTING" | "STABLE",
  }
```

**Source:** Finnhub API (key already set). yfinance `institutional_holders` as fallback.

**Integration points:**
- `Deep Dive Section 6` (Whole Picture) — insider/institutional panel
- `Watchlist` digest — insider buys/sells already partially built
- `StockCard` — insider sentiment chip (optional, if space)

### WS4: Analyst Targets + Consensus

**Enhance:** `backend/services/sentiment.py` (already exists, extend)

```
Functions:
  get_analyst_data(ticker) -> {
    consensus: "Strong Buy" | "Buy" | "Hold" | "Sell" | "Strong Sell",
    target_low: float,
    target_mean: float,
    target_high: float,
    num_analysts: int,
    recent_changes: [{firm, from_rating, to_rating, date}],
    price_vs_target: float,  # current price / mean target
    contrarian_signal: str,  # inverted interpretation
  }
```

**Source:** yfinance `info` (already has targets) + Finnhub recommendations.

**Integration points:**
- `Deep Dive Section 5` (Valuation) — analyst target range bar
- `StockCard` — target upside/downside %
- `ResearchPanel` — already partially shows this

### WS5: Market Breadth

**Enhance:** `backend/services/regime_checker.py`

```
Functions:
  calculate_market_breadth() -> {
    pct_above_200d: float,  # % of sampled S&P stocks above 200d SMA
    pct_above_50d: float,
    breadth_signal: "STRONG" | "HEALTHY" | "WEAKENING" | "POOR",
    sample_size: int,
  }
```

**Implementation:** Sample 50 stocks across sectors (not all 500 — too slow). Check price vs 200d SMA for each. Extrapolate.

**Integration points:**
- `Regime Page` — breadth gauge below SPY/QQQ cards
- Regime verdict scoring — breadth factor added to scoring

### WS6: Peer Comparison

**New file:** `backend/services/peers.py`

```
Functions:
  get_peer_comparison(ticker) -> {
    peers: [{
      ticker, name, market_cap, forward_pe, operating_margin,
      revenue_growth, fcf_yield, drop_from_high, direction
    }],
    ticker_rank: {pe_rank, margin_rank, growth_rank, value_rank},
    sector: str,
  }
```

**Implementation:** Use yfinance sector/industry info to find 5-8 peers. Fetch key metrics for each.

**Integration points:**
- `Deep Dive Section 5` (Valuation) — peer comparison table
- New component: `PeerTable.jsx`

### WS7: Gemini 2.5 Pro Integration

**New file:** `backend/services/gemini_analyzer.py`

```
Functions:
  generate_deep_dive(ticker, context: dict) -> {
    first_impression: str,
    bear_case_stock: str,
    bear_case_business: str,
    bull_case_rebuttal: str,
    bull_case_upside: str,
    whole_picture: str,
    self_review: str,
    verdict: str,
    conviction: str,
    entry_grid: list,
    exit_playbook: str,
  }
```

**Context construction:** The function assembles ALL available Tier 1 data into a structured prompt:
- Current fundamentals (price, PE, margins, FCF, D/E, etc.)
- 5-year financial history trends
- Technical indicators (RSI, MACD, direction, support/resistance)
- Insider activity summary
- Analyst consensus + targets
- Research articles (SA, Substack)
- Sentiment scores
- Peer comparison data
- Market regime context

**Prompt template:** Stored in `backend/prompts/deep_dive.txt`. Follows the exact 8-section sequence. Enforces contrarian framework rules:
- Bear case FIRST, always
- Fail-closed mentality
- Negative sentiment = opportunity signal
- SBC-adjusted FCF
- WACC fixed at 10%
- Terminal value <50% warning
- Entry grid with 4 tranches
- "What would make me wrong" in self-review

**API:** `google-generativeai` Python package. Model: `gemini-2.5-pro`.

**Rate limit handling:** Backend tracks calls/minute and calls/day in memory. Returns 429 if exceeded with "Try again in X seconds" message.

**New config:**
```python
GEMINI_CONFIG = {
    "model": "gemini-2.5-pro",
    "max_rpm": 5,
    "max_rpd": 100,
    "max_output_tokens": 8192,
    "temperature": 0.7,
}
```

**New env var:** `GEMINI_API_KEY`

### WS8: TradingView MCP Setup

Install two TradingView MCP servers for Claude Code sessions:

**Server 1: bidouilles/mcp-tradingview-server**
- Full indicator snapshots (all MAs, RSI, MACD, Stochastic, ADX, Bollinger, pivots)
- OHLCV historical data
- No API key needed

**Server 2: atilaahmettaner/tradingview-mcp**
- Stock screening by 30+ technical indicators
- Reddit sentiment analysis
- Strategy backtesting
- No API key needed

**Installation:** Add to Claude Code MCP config. These are available during Claude Code sessions for premium analysis.

**Bridge integration:** The deep dive worker script (`bridge/deep_dive_worker.py`) gets a `--tv` flag to fetch TradingView data and include it in the analysis context.

### WS9: Frontend Enhancements

**New components:**
| Component | Purpose | Used In |
|-----------|---------|---------|
| `TechnicalPanel.jsx` | RSI gauge, MACD chart, MA levels, volume bar | Deep Dive Section 1 |
| `SparklineGrid.jsx` | 4-year mini sparklines for financials | Deep Dive Section 1 |
| `DirectionBadge.jsx` | Per-stock direction indicator | StockCard, Deep Dive |
| `InsiderPanel.jsx` | Insider buys/sells timeline | Deep Dive Section 6 |
| `InstitutionalPanel.jsx` | Top holders + accumulation signal | Deep Dive Section 6 |
| `PeerTable.jsx` | Side-by-side peer metrics | Deep Dive Section 5 |
| `AnalystBar.jsx` | Price target range visualization | Deep Dive Section 5 |
| `BreadthGauge.jsx` | Market breadth indicator | Regime Page |
| `AiAnalyzeButton.jsx` | Triggers Gemini deep dive | Deep Dive Page |
| `RsiChip.jsx` | Compact RSI indicator | StockCard |

**Modified pages:**
| Page | Changes |
|------|---------|
| `ScreenerPage` | Add direction badge, RSI column, analyst target %, sort by RSI/direction |
| `DeepDivePage` | Section 1 gets TechnicalPanel + SparklineGrid. Section 5 gets PeerTable + AnalystBar. Section 6 gets InsiderPanel + InstitutionalPanel. Add "AI Analyze" button. |
| `RegimePage` | Add BreadthGauge below SPY/QQQ cards |
| `StockCard` | Add DirectionBadge, RsiChip, analyst target upside % |
| `FilterBar` | Add direction filter, RSI filter (oversold/neutral/overbought) |

### WS10: Enhanced Deep Dive Router

**Modify:** `backend/routers/deep_dive.py`

The GET endpoint now returns enriched data:
```json
{
  "ticker": "ADBE",
  "fundamentals": { ... },
  "technicals": {
    "rsi": 28.5,
    "macd": { "value": -2.3, "signal": -1.8, "histogram": -0.5, "crossover": "bearish" },
    "direction": "CORRECTION_IN_UPTREND",
    "volume": { "relative": 0.7, "trend": "DRY_UP" },
    "support": [240, 225],
    "resistance": [265, 280],
    "bollinger": { "upper": 275, "middle": 258, "lower": 241, "pct_b": 0.15 },
    "relative_strength_vs_spy": { "20d": -0.08, "60d": -0.15 }
  },
  "financial_history": {
    "revenue": [{"year": 2022, "value": 17610000000}, ...],
    "operating_margin": [{"year": 2022, "value": 0.34}, ...],
    ...
  },
  "insider_activity": {
    "net_sentiment": "BUYING",
    "recent_buys": [...],
    "notable": [...]
  },
  "institutional": {
    "top_holders": [...],
    "trend": "ACCUMULATING"
  },
  "analyst": {
    "consensus": "Buy",
    "target_mean": 320,
    "target_low": 280,
    "target_high": 380,
    "contrarian_signal": "CONSENSUS"
  },
  "peers": [...],
  "research_context": { ... },
  "ai_analysis": { ... },
  "data_quality": { ... }
}
```

**New endpoint:** `POST /api/deep-dive/{ticker}/analyze`
- Triggers Gemini 2.5 Pro analysis
- Assembles all Tier 1 data as context
- Calls Gemini API
- Saves result to `deep_dives` table
- Returns the generated analysis

---

## New Database Tables

```sql
CREATE TABLE IF NOT EXISTS technicals_cache (
    ticker TEXT PRIMARY KEY,
    rsi REAL,
    macd_value REAL,
    macd_signal REAL,
    macd_histogram REAL,
    macd_crossover TEXT,
    direction TEXT,
    ema20 REAL,
    sma50 REAL,
    sma200 REAL,
    adx REAL,
    bollinger_upper REAL,
    bollinger_lower REAL,
    bollinger_pct_b REAL,
    volume_relative REAL,
    volume_trend TEXT,
    support_1 REAL,
    support_2 REAL,
    resistance_1 REAL,
    resistance_2 REAL,
    rs_vs_spy_20d REAL,
    rs_vs_spy_60d REAL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS financial_history_cache (
    ticker TEXT NOT NULL,
    metric TEXT NOT NULL,
    year INTEGER NOT NULL,
    value REAL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (ticker, metric, year)
);

CREATE TABLE IF NOT EXISTS insider_cache (
    ticker TEXT PRIMARY KEY,
    net_sentiment TEXT,
    data_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS institutional_cache (
    ticker TEXT PRIMARY KEY,
    trend TEXT,
    data_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS analyst_cache (
    ticker TEXT PRIMARY KEY,
    consensus TEXT,
    target_mean REAL,
    target_low REAL,
    target_high REAL,
    num_analysts INTEGER,
    data_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS peer_cache (
    ticker TEXT PRIMARY KEY,
    peers_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## New Dependencies

```
# requirements.txt additions
google-generativeai>=0.8    # Gemini API
numpy                        # Already installed (scipy dep)
```

No new frontend dependencies needed — all visualizations use inline SVG/CSS.

---

## New Environment Variables

```bash
export GEMINI_API_KEY="your_key"    # Google AI Studio (free)
# Existing keys already set:
# ALPHA_VANTAGE_API_KEY
# FINNHUB_API_KEY
# FMP_API_KEY
```

---

## Parallel Agent Execution Strategy

This build is large enough to parallelize across specialized agents working on isolated worktrees.

### Phase A: Backend Services (3 parallel agents)

**Agent 1: Technicals + Direction**
- Create `backend/services/technicals.py`
- Add `technicals_cache` table to `database.py`
- Write `tests/test_technicals.py`
- Modify `stock_screener.py` to include direction in scan results

**Agent 2: Financial History + Insider + Institutional + Analyst + Peers**
- Create `backend/services/financial_history.py`
- Create `backend/services/institutional.py`
- Create `backend/services/peers.py`
- Enhance `backend/services/sentiment.py` with analyst data
- Add all cache tables to `database.py`
- Write tests for each service

**Agent 3: Gemini Integration**
- Create `backend/services/gemini_analyzer.py`
- Create `backend/prompts/deep_dive.txt`
- Add `GEMINI_CONFIG` to `config.py`
- Create `POST /api/deep-dive/{ticker}/analyze` endpoint
- Write `tests/test_gemini.py`
- Add rate limiting logic

### Phase B: Backend Integration (sequential, after Phase A merges)
- Modify `routers/deep_dive.py` to include all enriched data
- Modify `routers/screener.py` to include technicals + direction
- Modify `routers/regime.py` to include market breadth
- Update `bridge/deep_dive_worker.py` with new context

### Phase C: Frontend (2 parallel agents, after Phase B)

**Agent 4: Deep Dive + Screener enhancements**
- Create TechnicalPanel, SparklineGrid, InsiderPanel, InstitutionalPanel, PeerTable, AnalystBar, AiAnalyzeButton
- Modify DeepDivePage with all new sections
- Modify StockCard with DirectionBadge + RsiChip
- Modify ScreenerPage with new filters/sorts

**Agent 5: Regime + minor pages**
- Create BreadthGauge
- Modify RegimePage
- Modify FilterBar with direction/RSI filters
- Update api.js with new endpoints

### Phase D: TradingView MCP Setup (separate)
- Install bidouilles/mcp-tradingview-server
- Install atilaahmettaner/tradingview-mcp
- Add to Claude Code MCP config
- Update bridge script with `--tv` flag
- Test MCP tools work in Claude Code session

---

## What This Does NOT Change

- No new pages (still 6 pages)
- No changes to options scanner logic (already complete)
- No changes to position tracker (already complete)
- No changes to watchlist CRUD (already complete)
- No changes to DCF calculator component (already complete)
- SQLite + single process architecture unchanged
- Fail-closed gates unchanged
- All existing tests must continue to pass

---

## Success Criteria

After implementation:

1. **Screener** shows direction badge + RSI + analyst target for every candidate
2. **Deep Dive** loads with full technical panel, 5yr sparklines, insider/institutional data, peer comparison — automatically, before any AI analysis
3. **"AI Analyze" button** on deep dive triggers Gemini 2.5 Pro to generate all 8 sections in ~30 seconds
4. **Regime page** shows market breadth gauge and watchlist earnings calendar
5. **StockCards** show direction (UPTREND/PULLBACK/etc) + RSI chip
6. **Bridge script** can fetch research context + TV data for Claude Code deep dives
7. **All existing tests pass** + new tests for technicals, financial history, Gemini integration
8. **No API key required for Tier 1** (yfinance only) — Tier 2 needs Gemini key, Tier 3 needs Claude Code session
