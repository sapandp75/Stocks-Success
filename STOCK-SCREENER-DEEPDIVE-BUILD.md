# Stock Screener & Deep Dive Dashboard — Claude Code Build Instructions

## What This Is

A complete stock screening and deep analysis system for a **contrarian quality investor**. This is a **separate app** from the Contrarian Options System but designed to work alongside it. The options system tells you WHICH contracts to buy — this system tells you WHICH stocks deserve your capital in the first place.

**Two dashboards in one app:**
1. **Screener Dashboard** — daily/weekly scanning of the S&P 500 for B1 (contrarian value) and B2 (growth) candidates
2. **Deep Dive Dashboard** — full Gate 1-5 analysis of individual stocks with DCF calculator, bear/bull cases, and entry planning

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    STOCK ANALYSIS APP                        │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │   SCREENER DASHBOARD │  │    DEEP DIVE DASHBOARD       │ │
│  │                      │  │                              │ │
│  │  • Daily scan        │  │  • Gate 1: Data Snapshot     │ │
│  │  • Weekly scan       │  │  • Gate 2: First Impression  │ │
│  │  • B1 candidates     │  │  • Gate 3: Bear Case         │ │
│  │  • B2 candidates     │  │  • Gate 4: Bull Case         │ │
│  │  • Watchlist (saved) │  │  • Gate 5: Valuation (DCF)   │ │
│  │  • Warning flags     │  │  • Whole Picture             │ │
│  │  • Sector breakdown  │  │  • Self-Review               │ │
│  │                      │  │  • Verdict + Entry Grid      │ │
│  └──────────┬───────────┘  └──────────────┬───────────────┘ │
│             │                             │                 │
│  ┌──────────┴─────────────────────────────┴───────────────┐ │
│  │              DATA LAYER (MCP + APIs)                    │ │
│  │                                                        │ │
│  │  FREE — No API key:                                    │ │
│  │  • yfinance (price, fundamentals, options chains)      │ │
│  │  • SEC EDGAR / EdgarTools (13F, insider, filings)      │ │
│  │  • stockanalysis.com (web fetch backup)                │ │
│  │                                                        │ │
│  │  FREE — API key required (free tier):                  │ │
│  │  • FMP (250 calls/day — financials, DCF, estimates)    │ │
│  │  • Alpha Vantage (25 calls/day — technicals, RSI)      │ │
│  │  • Finnhub (60 calls/min — news, sentiment, insider)   │ │
│  │                                                        │ │
│  │  MCP SERVERS:                                          │ │
│  │  • mcp-stockflow (stock data + options chains)         │ │
│  │  • mcp-stockscreen (stock screening)                   │ │
│  │  • Alpha Vantage MCP (official, hosted)                │ │
│  │  • EdgarTools MCP (SEC filings, 13F, insider)          │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## FREE DATA SOURCES — Complete Map

### TIER 1: No API Key Required (Unlimited, Free Forever)

#### 1. yfinance (Python library)
- **Install:** `pip install yfinance`
- **What it gives you:**
  - Current & historical prices (OHLCV)
  - Moving averages (calculate from price data)
  - Basic fundamentals (P/E, market cap, revenue, margins, EPS)
  - Options chains (strikes, premiums, OI, volume, IV)
  - Earnings dates
  - Sector/industry classification
  - Shares outstanding, float, short interest
- **Limits:** Unofficial API, occasionally breaks. No rate limit but don't hammer it
- **Use for:** Batch screening (scan 500 tickers), daily price checks, options data
- **Gate coverage:** Gate 1 (partial), Gate 3 (partial), Technical Analysis (full)

#### 2. SEC EDGAR via EdgarTools (Python library + MCP server)
- **Install:** `pip install edgartools`
- **MCP server:** Built-in, configure for Claude Code/Desktop
- **What it gives you:**
  - **13F institutional holdings** — who owns what, position sizes, quarter-over-quarter changes
  - **Form 4 insider transactions** — buy/sell, exact shares, prices, dates, owner names
  - **10-K/10-Q financial statements** — structured, parsed into Python objects
  - **8-K current reports** — material events, management changes
  - **DEF 14A proxy statements** — executive compensation
  - **Schedule 13D/13G** — activist investor positions (5%+ ownership)
- **Limits:** None. SEC EDGAR is a public resource. Completely free, no key needed
- **Use for:** Gate 1 (insider activity), Gate 2 (smart money analysis), Gate 6 (whole picture)
- **THIS IS GOLD FOR YOUR SYSTEM.** 13F data + insider trading is exactly what you need for the "who's buying, who's selling" analysis. And it's free

#### 3. stockanalysis.com (Web fetch)
- **Access:** Web fetch from Claude — no API, just parse the page
- **What it gives you:**
  - Clean financial statements (income, balance sheet, cash flow)
  - Key statistics page
  - Analyst estimates
  - Earnings history
  - Revenue/earnings growth rates
- **Limits:** Web scraping, may block heavy use. Use as backup/verification
- **Use for:** Cross-checking yfinance data, Gate 1 (financials), Gate 3 (valuation)

---

### TIER 2: Free API Key Required (Generous Free Tiers)

#### 4. Financial Modeling Prep (FMP)
- **Signup:** https://financialmodelingprep.com — free, instant
- **Free tier:** 250 API calls/day
- **What it gives you:**
  - 5-year income statements, balance sheets, cash flow statements
  - Key metrics (FCF, ROIC, SBC, debt ratios — all pre-calculated)
  - **DCF endpoint** — pre-calculated intrinsic value per share
  - Analyst estimates (consensus EPS, revenue forecasts)
  - Stock screener endpoint (filter by fundamentals)
  - Earnings calendar with surprise history
  - **Financial ratios** — 5-year trend for every ratio you need
  - Stock grade/rating
  - Enterprise value breakdown
- **Limits:** 250 calls/day. Each ticker = ~3-5 calls for full data. So ~50-80 full analyses per day
- **Use for:** Gate 1 (full financials), Gate 3 (DCF + historical valuation), Gate 5 (valuation)
- **MCP server:** Community-built FMP MCP servers exist on GitHub. Or build a thin wrapper
- **THIS IS YOUR PRIMARY DATA BACKBONE.** Once you have this key, the screener and deep dive become massively more powerful

#### 5. Alpha Vantage
- **Signup:** https://alphavantage.co — free, instant
- **Free tier:** 25 API calls/day (very restrictive) — OR use their **official MCP server**
- **MCP server (OFFICIAL, HOSTED — no local install needed):**
  ```json
  {
    "mcpServers": {
      "alphavantage": {
        "httpUrl": "https://mcp.alphavantage.co/mcp?apikey=YOUR_API_KEY"
      }
    }
  }
  ```
- **What it gives you:**
  - 50+ pre-computed technical indicators (RSI, MACD, SMA, EMA, Bollinger, etc.)
  - Fundamentals (P/E, margins, financial statements)
  - Earnings surprise history
  - 20+ years of historical price data
  - News sentiment API
- **Limits:** 25 calls/day on free tier is painfully low. Use strategically — for deep dives only, not batch screening
- **Use for:** Technical Analysis skill (RSI, volume), Gate 1 (cross-check), earnings surprise data
- **KEY ADVANTAGE:** Official MCP server means it works from Claude Desktop/Code without local install

#### 6. Finnhub
- **Signup:** https://finnhub.io — free, instant
- **Free tier:** 60 API calls/minute (most generous free tier)
- **What it gives you:**
  - Real-time stock quotes
  - **News sentiment scores** — AI-scored sentiment per article per ticker
  - **Insider transactions** — buy/sell activity
  - **Earnings surprises** — actual vs estimate history
  - **Analyst recommendations** — buy/sell/hold consensus + history
  - **SEC filings** — recent filings list
  - Company peers list
  - Basic financials
- **Limits:** No options data. Limited historical depth on free tier
- **Use for:** Gate 2 (sentiment), Gate 6 (news, analyst consensus), daily morning scan (news)
- **MCP server:** Community-built, multiple versions on GitHub

---

### TIER 3: Specialised Free Sources

#### 7. SEC EDGAR Direct (Beat & Raise MCP)
- **MCP:** https://beatandraise.com/mcp — free for Claude Pro/Max subscribers
- **What it gives you:**
  - Full-text search across all SEC filings
  - Parsed 13F holdings (individual positions with values)
  - Form 4 insider transactions (parsed, structured)
  - Financial statements from 10-K/10-Q
- **Use for:** Deep dives — insider activity, institutional flow analysis

#### 8. 13F.info (Web)
- **Access:** Free website, web fetch
- **What it gives you:**
  - Clean 13F data by fund or by stock
  - Quarter-over-quarter comparison
  - All managers holding a specific stock
- **Use for:** Gate 6 (who's buying/selling) — "show me all funds that hold ADBE"

---

## MCP SERVERS — Complete Installation Guide

### Server 1: mcp-stockflow (Stock Data + Options Chains)
```bash
git clone https://github.com/twolven/mcp-stockflow.git
cd mcp-stockflow
pip install -r requirements.txt
# Dependencies: mcp, yfinance
```
**Tools:** `get-stock-data`, `get-historical-data`, `get-options-chain`
**Config:**
```json
"stockflow": {
  "command": "python",
  "args": ["/path/to/mcp-stockflow/stockflow.py"]
}
```

### Server 2: mcp-stockscreen (Stock Screener)
```bash
git clone https://github.com/twolven/mcp-stockscreen.git
cd mcp-stockscreen
pip install -r requirements.txt
```
**Tools:** Stock screening with technical + fundamental filters
**Config:**
```json
"stockscreen": {
  "command": "python",
  "args": ["/path/to/mcp-stockscreen/stockscreen.py"]
}
```

### Server 3: Alpha Vantage MCP (OFFICIAL, HOSTED)
No installation needed. This is a remote MCP server.
```json
"alphavantage": {
  "httpUrl": "https://mcp.alphavantage.co/mcp?apikey=YOUR_ALPHA_VANTAGE_KEY"
}
```
Get free key at: https://alphavantage.co
**Tools:** TIME_SERIES_DAILY, RSI, SMA, EMA, MACD, OVERVIEW, EARNINGS, NEWS_SENTIMENT, and 50+ more

### Server 4: EdgarTools MCP (SEC Filings — FREE, No Key)
```bash
pip install edgartools
```
Follow setup at: https://www.edgartools.io/edgartools-mcp-for-sec-filings/
**Tools:** 13F holdings, Form 4 insider trades, 10-K/10-Q financials, company search, filing search
**Config:** See EdgarTools docs — supports both Claude Desktop and Claude Code

### Server 5: mcp-optionsflow (Options Analysis)
*(From the Options System — shared across both apps)*
```bash
git clone https://github.com/twolven/mcp-optionsflow.git
cd mcp-optionsflow
pip install -r requirements.txt
# Dependencies: mcp, yfinance, pandas, numpy, scipy
```
**Config:**
```json
"optionsflow": {
  "command": "python",
  "args": ["/path/to/mcp-optionsflow/optionsflow.py"]
}
```

### Complete Claude Config (All Servers)
```json
{
  "mcpServers": {
    "stockflow": {
      "command": "python",
      "args": ["/path/to/mcp-stockflow/stockflow.py"]
    },
    "stockscreen": {
      "command": "python",
      "args": ["/path/to/mcp-stockscreen/stockscreen.py"]
    },
    "optionsflow": {
      "command": "python",
      "args": ["/path/to/mcp-optionsflow/optionsflow.py"]
    },
    "alphavantage": {
      "httpUrl": "https://mcp.alphavantage.co/mcp?apikey=YOUR_AV_KEY"
    },
    "edgartools": {
      "command": "python",
      "args": ["-m", "edgar.mcp"]
    }
  }
}
```

---

## PHASE 1: Build the Screener Dashboard

### 1A — Screener Python Script (`stock_screener.py`)

Scans the full S&P 500 and filters into B1 and B2 buckets.

**B1 (Contrarian Value) Hard Gates:**
- Operating margin > 20% (proves pricing power)
- Free cash flow positive (business funds itself)
- Stock down > 20% from 52-week high (market punishment)
- Revenue growth > 0% YoY (not actually broken)
- Debt-to-equity < 5x (not over-leveraged)
- Forward P/E < 50x (not speculative)

**B1 Warning Flags (show, don't filter):**
- Revenue growth < 5% → "SLOW GROWTH"
- D/E > 3x → "HIGH LEVERAGE"
- Short interest > 10% → "HIGH SHORT"
- ROE > 100% → "LEVERAGE-DRIVEN ROE"
- Trailing P/E > 3x forward P/E → "P/E COMPRESSION"
- Earnings within 14 days → "EARNINGS SOON"
- SBC > 10% of revenue → "HIGH SBC" (if data available)
- Energy/Materials sector → "CYCLICAL"

**B2 (Peter Lynch Growth) Hard Gates:**
- Revenue growth > 25% YoY
- Gross margin > 40% (or improving)
- Revenue > $200M (real business, not speculative)

**B2 Warning Flags:**
- Negative FCF → "CASH BURN"
- Forward P/E > 80x → "EXTREME VALUATION"
- Insider selling heavy → "INSIDER SELLING"

**Data source:** yfinance for batch screening (no rate limits). FMP for enrichment (when key available).

**Output:** JSON file with all candidates + flags, consumed by the React dashboard.

### 1B — Screener React Dashboard

Interactive JSX artifact with the Koyfin palette. Features:

**Tabs:** B1 | B2 | Watchlist | Both (crossover names)

**Per-stock card shows:**
- Ticker, name, sector
- Price, % from 52-week high
- Revenue growth, operating margin, FCF yield
- Forward P/E, trailing P/E
- Short interest
- Direction (DOWNTREND / BASING / PULLBACK / UPTREND)
- Warning badges (amber tags under each ticker)
- "+ Watch" button (saves to persistent storage via `window.storage`)

**Filters (dropdowns):**
- Sector
- Min FCF yield (Any / 5%+ / 8%+)
- Max forward P/E (Any / <15 / <20 / <30)
- Min operating margin (Any / 25%+ / 30%+ / 40%+)
- Sort by: Most beaten down / Highest FCF yield / Cheapest P/E / Highest margin / Fastest growth

**Sector distribution bar** at top of each tab — visual breakdown of sector concentration.

**Scan timestamp** in header — shows when data was last refreshed.

**Watchlist persistence** — uses `window.storage` API to save/load watchlist across sessions. Each watchlist entry stores: ticker, bucket (B1/B2), thesis note (editable text field).

### 1C — Daily vs Weekly Scan Modes

**Daily scan (triggered by "run my screen" or "morning glance"):**
- Quick price check on watchlist names only
- Flag any that moved >5% since last scan
- Flag any approaching entry zones
- Update regime status (link to market regime filter)

**Weekly scan (triggered by "weekly review" or "Sunday session"):**
- Full S&P 500 rescan with fresh data
- Rebuild entire dashboard
- Compare to previous week's candidates — who's new, who dropped off
- Surface 2-3 "blood in the streets" names (biggest drops on quality names)

---

## PHASE 2: Build the Deep Dive Dashboard

### 2A — Data Pipeline Per Ticker

When user says "deep dive ADBE" or "analyse TTD", the system runs:

**Step 1: Gather data (parallel where possible)**

| Data Point | Primary Source | Backup Source | Gate |
|---|---|---|---|
| Revenue 5yr trend | FMP `/income-statement` | stockanalysis.com | 1 |
| Operating margin trend | FMP `/income-statement` | yfinance `.info` | 1 |
| Free cash flow + SBC | FMP `/cash-flow-statement` | stockanalysis.com | 1 |
| Debt/equity, interest coverage | FMP `/balance-sheet-statement` | yfinance | 1 |
| ROE, ROIC | FMP `/key-metrics` | calculate from statements | 1 |
| Revenue by segment | stockanalysis.com (web fetch) | 10-K via EdgarTools | 1 |
| GAAP vs non-GAAP gap | FMP (compare EPS) | earnings transcripts | 1 |
| P/E trailing + forward | yfinance `.info` | FMP `/ratios` | 3 |
| P/E 5-year average | FMP `/ratios` (historical) | stockanalysis.com | 3 |
| EV/EBITDA, P/S, PEG | FMP `/ratios` | yfinance | 3 |
| FCF yield | Calculate: FCF / market cap | FMP `/key-metrics` | 3 |
| Pre-calculated DCF | FMP `/discounted-cash-flow` | build own | 5 |
| Analyst consensus | Finnhub `/recommendation` | FMP `/analyst-estimates` | 6 |
| Analyst price targets | FMP `/analyst-estimates` | web search | 6 |
| Insider activity 6mo | EdgarTools (Form 4) | Finnhub `/insider` | 6 |
| 13F institutional flows | EdgarTools (13F) | 13f.info (web fetch) | 6 |
| Short interest | yfinance `.info` | Finnhub | 6 |
| News sentiment | Finnhub `/news-sentiment` | web search | 6 |
| Earnings date | yfinance `.calendar` | FMP `/earning_calendar` | 6 |
| Current price + MAs | yfinance (historical) | Alpha Vantage MCP | TA |
| Volume analysis | yfinance (60-day daily) | Alpha Vantage | TA |
| RSI (weekly) | Alpha Vantage RSI endpoint | calculate from yfinance | TA |
| Peer comparison | FMP `/stock-peers` | manual selection | 5 |

### 2B — Deep Dive React Dashboard

Interactive JSX artifact. 8 collapsible sections following the exact Gate 1-5 sequence.

**Header card:**
- Ticker, price, bucket assignment (B1/B2/PASS)
- Conviction level (HIGH/MODERATE/LOW)
- Risk/reward ratio
- Key verdict sentence

**Section 1: Data Snapshot**
- Financial metrics in a clean grid
- 5-year sparklines for revenue, margins, FCF (if data available)
- SBC flag if >10% of revenue
- Accounting red flags panel

**Section 2: First Impression**
- One paragraph gut check (editable — user can override)

**Section 3: Bear Case**
- Split into "Bear on Stock" vs "Bear on Business"
- Red-accented cards
- Sourced from short reports, analyst downgrades, earnings Q&A

**Section 4: Bull Case**
- Split into "Bear Rebuttal" vs "Unpriced Upside"
- Green-accented cards
- Each bull point MUST address a specific bear point

**Section 5: Valuation**
- Reverse DCF result (what growth does the price imply?)
- Forward DCF with 3 scenarios (bear/base/bull)
- Sensitivity matrix (4x4 grid: WACC vs growth rate)
- Peer comparison table
- Rules: WACC fixed at 10-12%, terminal value <50% of total, SBC-adjusted FCF as starting point

**Section 6: Whole Picture**
- Sector theme assessment
- Smart money positioning (13F data — fund type matters)
- Management quality + compensation structure
- Customer/product evidence
- PE/strategic acquirer floor

**Section 7: Self-Review**
- Bias check vs first impression
- Gap check — what data is missing
- Pre-mortem: "It's one year from now and this lost 30%. What happened?"
- "What would make me wrong" list (3-5 specific conditions)

**Section 8: Verdict**
- Bucket assignment with justification
- Conviction level with primary reason
- Entry grid (from Technical Analysis skill):
  | Tranche | Trigger | Technical Confirmation | Price Zone |
  |---------|---------|----------------------|------------|
  | 1st third | Stabilisation | Volume drying up, ranges narrowing | $X-$Y |
  | 2nd third | Higher low | 10-week EMA reclaim | $X-$Y |
  | 3rd third | Trend reversal | 50d SMA reclaim on 1.5x volume | $X-$Y |
  | DO NOT ENTER | Free fall | Expanding down-volume, new lows | Below $X |
- Exit playbook (thesis invalidation triggers, profit targets, time horizon)
- Decision tree (if catalyst beats → X, if misses → Y)
- Next review date

### 2C — DCF Calculator Component

Built into the Deep Dive dashboard as an interactive sub-component.

**Inputs (adjustable by user):**
- Starting FCF (default: SBC-adjusted 3yr average from FMP)
- Growth rate year 1-5 (default: analyst consensus or historical CAGR)
- Growth rate year 6-10 (default: linear deceleration to terminal)
- Terminal growth rate (default: 2.5%)
- WACC / discount rate (default: 10%, adjustable 7-14%)
- Shares outstanding (from yfinance)
- Net debt (from FMP balance sheet)

**Outputs:**
- Intrinsic value per share (3 scenarios)
- Margin of safety vs current price
- 4x4 sensitivity heatmap (WACC rows × growth columns)
- Terminal value as % of total (red warning if >50%)
- Implied growth rate at current price (reverse DCF)

**Hard rules enforced in code:**
- WACC cannot be changed between scenarios — only business assumptions change
- Terminal value >50% triggers a warning and suggests shortening forecast period
- SBC adjustment is applied by default — toggle to show with/without

---

## PHASE 3: Watchlist Persistence + Position Tracking

### 3A — Persistent Watchlist

Uses `window.storage` API (for React artifacts in Claude.ai) OR a local JSON file (for Claude Code).

**Stored per watchlist entry:**
```json
{
  "ticker": "ADBE",
  "bucket": "B1",
  "added_date": "2026-04-05",
  "thesis_note": "AI fear oversold, record FCF, 10x fwd PE",
  "entry_zone_low": 220,
  "entry_zone_high": 250,
  "last_deep_dive": "2026-04-05",
  "conviction": "HIGH",
  "status": "WATCHING"  // WATCHING | ENTERED | CLOSED
}
```

### 3B — Position Tracker

Simple JSON-based tracker (same as Options System but for stock positions):

```json
{
  "ticker": "ADBE",
  "bucket": "B1",
  "tranches": [
    {"date": "2026-04-10", "shares": 20, "price": 242.50, "pct_portfolio": 3.5}
  ],
  "thesis": "AI fear oversold, record Q1 FCF, 10x fwd PE, CEO transition manageable",
  "invalidation": ["Rev growth <5% for 2 quarters", "Op margin <30%", "Firefly adoption stalls"],
  "target_fair_value": 340,
  "status": "OPEN"
}
```

---

## PHASE 4: Integration — Screener → Deep Dive → Options

The workflow connecting both apps:

```
SCREENER DASHBOARD
  → Identifies ADBE as B1 candidate (-43%, 10x fwd PE, record FCF)
  → User clicks "Deep Dive" button
  
DEEP DIVE DASHBOARD  
  → Pulls all data from MCP servers + APIs
  → Runs Gate 1-5 analysis
  → Verdict: B1, HIGH conviction, entry zone $220-250
  → User approves thesis
  
OPTIONS SYSTEM (separate app)
  → Scanner filters ADBE options: Jul $260C, delta 0.35, premium $5.20
  → Regime check: CAUTIOUS — max 2 new positions
  → User executes trade
```

---

## CLAUDE.md System Prompt (for this app)

```markdown
# Stock Screener & Deep Dive Dashboard — Claude Code Context

## Available MCP Servers
- `stockflow` — real-time stock data, historical prices, options chains (yfinance)
- `stockscreen` — stock screening with filters
- `alphavantage` — 50+ technical indicators, fundamentals, earnings, news sentiment
- `edgartools` — SEC filings, 13F holdings, Form 4 insider trades (FREE, no key)

## Available APIs (Python)
- yfinance — batch screening, prices, basic fundamentals
- FMP (key: [PENDING]) — 5yr financials, DCF, ratios, estimates, analyst data
- Finnhub (key: [PENDING]) — news sentiment, insider trades, recommendations

## Screener Rules
B1 hard gates: op margin >20%, FCF positive, down >20%, rev growth >0%, D/E <5x, fwd PE <50x
B2 hard gates: rev growth >25%, gross margin >40%, revenue >$200M
Everything else = flagged, not filtered

## Deep Dive Sequence (NEVER skip or reorder)
1. Data Snapshot (numbers only, no opinion)
2. First Impression (gut check)
3. Bear Case FIRST (bear on stock vs bear on business)
4. Bull Case (bear rebuttal + unpriced upside)
5. Valuation (reverse DCF first, then forward DCF, sensitivity matrix)
6. Whole Picture (sector, smart money, management, scuttlebutt)
7. Self-Review (bias check, gap check, pre-mortem)
8. Verdict (bucket, conviction, entry grid, exit playbook)

## DCF Rules (Non-Negotiable)
- SBC-adjusted FCF as starting point if SBC >10% of revenue
- WACC fixed across scenarios (10-12%). Only vary business assumptions
- Terminal value MUST be <50% of total DCF value
- 3-year average FCF, not peak or trough
- Reverse DCF before forward DCF — always

## Koyfin Palette
bg: #f0f1f3, cards: #ffffff, hover: #f7f8fa, borders: #e2e4e8
green: #00a562, red: #e5484d, amber: #d97b0e
No black backgrounds. No pure white backgrounds.

## Output Rules
- All results as interactive JSX artifacts (MUST render inline, not just downloadable files)
- Propose plan first, wait for approval before building
- After creating anything, perform critical self-review before presenting
```

---

## File Structure

```
stock-analysis-system/
├── CLAUDE.md                          # Claude Code system prompt
├── README.md                          # This file
├── stock_screener.py                  # B1/B2 batch screener
├── deep_dive.py                       # Data pipeline for individual analysis
├── dcf_calculator.py                  # DCF model with sensitivity analysis
├── watchlist.json                     # Persistent watchlist
├── positions.json                     # Position tracker
├── scan_results/
│   ├── latest_b1.json                # Most recent B1 scan
│   ├── latest_b2.json                # Most recent B2 scan
│   └── history/                      # Historical scans for comparison
├── deep_dives/
│   ├── ADBE_2026-04-05.json          # Saved deep dive results
│   └── TTD_2026-04-05.json
├── mcp-stockflow/                    # Cloned MCP server
├── mcp-stockscreen/                  # Cloned MCP server
└── mcp-optionsflow/                  # Shared with Options System
```

---

## API Keys Checklist

| Service | Free Tier | Key Status | Signup URL |
|---|---|---|---|
| yfinance | Unlimited | No key needed | — |
| SEC EDGAR / EdgarTools | Unlimited | No key needed | — |
| stockanalysis.com | Unlimited (web) | No key needed | — |
| FMP | 250 calls/day | **PENDING** | https://financialmodelingprep.com |
| Alpha Vantage | 25 calls/day + MCP | **PENDING** | https://alphavantage.co |
| Finnhub | 60 calls/min | **PENDING** | https://finnhub.io |

**Priority order for signup:** FMP first (most valuable for your system), then Finnhub (most generous free tier), then Alpha Vantage (official MCP server is the draw).

---

## Dependencies

```
# requirements.txt
yfinance>=0.2.36
pandas>=2.0
numpy>=1.24
scipy>=1.11
tabulate>=0.9
edgartools>=5.28
requests>=2.31
mcp>=1.0
```

---

## Testing Checklist

- [ ] `stock_screener.py` runs full S&P 500 scan and outputs B1 + B2 JSON
- [ ] Screener React dashboard renders with all filters and watchlist
- [ ] Watchlist persists across sessions (via `window.storage` or JSON file)
- [ ] `mcp-stockflow` responds to `get-stock-data` calls
- [ ] EdgarTools MCP returns 13F data and insider trades for a given ticker
- [ ] Alpha Vantage MCP returns RSI and SMA data
- [ ] `deep_dive.py` pulls all data for a single ticker from all sources
- [ ] DCF calculator produces sensitivity matrix with hard rules enforced
- [ ] Deep dive dashboard renders all 8 sections with correct gating
- [ ] Warning flags appear correctly on screener cards
- [ ] Sector distribution bar shows correct breakdown
- [ ] "Deep Dive" button on screener card triggers the deep dive pipeline

---

## Notes

1. **Build Phase 1 first (screener).** Get the scanning and dashboard working with yfinance alone. Then layer in FMP/Finnhub/Alpha Vantage for enrichment.

2. **EdgarTools is the hidden gem.** Free, no key, unlimited 13F + insider data + financial statements from SEC filings. This alone gives you institutional-grade smart money analysis for free.

3. **Alpha Vantage MCP is the easiest win.** It's a hosted remote server — no local install. One line of config and Claude has access to 50+ technical indicators. The 25 calls/day limit is fine for deep dives (you only deep dive 1-2 stocks per session).

4. **FMP is the highest-value key to get.** 250 calls/day unlocks 5-year financial history, pre-calculated DCF, analyst estimates, and the stock screener API. This is the single biggest upgrade to your system.

5. **Don't try to build everything at once.** Start with yfinance + EdgarTools. Add FMP when you have the key. Add Alpha Vantage MCP for technical analysis. Add Finnhub for news sentiment. Each layer makes the system better but each layer also works independently.

---

---

## TRADINGVIEW MCP SERVERS — Technical Analysis Layer

Three free TradingView MCP servers exist, each serving a different purpose. For your system, you want **all three** — they cover different angles of technical analysis.

### TV Server 1: tradingview-mcp (Market Screener + Technical Indicators)
**By:** Henrik404 (PyPI: `tradingview-mcp`)
**Best for:** Batch screening stocks by TradingView technical ratings, RSI, MACD, moving averages across 76+ markets. No TradingView account needed.

```bash
# Install via pip/uvx (easiest)
pip install tradingview-mcp

# Or from source
git clone https://github.com/k73a/tradingview-mcp.git
cd tradingview-mcp
```

**Config:**
```json
"tradingview-screener": {
  "command": "uvx",
  "args": ["tradingview-mcp"]
}
```

**What it gives you:**
- Screen 11,000+ stocks using TradingView's screener API
- Filter by 75+ investment metrics (RSI, MACD, volume, P/E, market cap, sector, etc.)
- Auto-market detection (stocks, forex, crypto, futures, bonds)
- Supports all global exchanges (US, UK, Germany, Japan, etc.)
- Smart filters with human-readable names ("Relative Strength Index (14)" not just "RSI")

**Use for your system:**
- **Daily scan:** Screen S&P 500 for oversold stocks (RSI <30 weekly) — feeds into B1 candidate list
- **Weekly review:** Get TradingView's technical rating (STRONG BUY / BUY / NEUTRAL / SELL) for all watchlist names
- **Volume analysis:** Filter for stocks with declining volume (seller exhaustion signal)
- **No API key, no TradingView account needed. Completely free.**

---

### TV Server 2: mcp-tradingview-server (Technical Indicators + OHLCV Data)
**By:** bidouilles
**Best for:** Pulling full TradingView indicator snapshots for a single stock — all indicators at once, plus historical candle data.

```bash
git clone https://github.com/bidouilles/mcp-tradingview-server.git
cd mcp-tradingview-server
pip install -e .
```

**Config (Claude Code):**
```bash
claude mcp add tradingview -- uvx --from /path/to/mcp-tradingview-server mcp-tradingview
```

**Config (Claude Desktop):**
```json
"tradingview-indicators": {
  "command": "/path/to/mcp-tradingview-server/.venv/bin/python",
  "args": ["/path/to/mcp-tradingview-server/src/tradingview_server.py"],
  "cwd": "/path/to/mcp-tradingview-server"
}
```

**Tools:**
- `get_indicators(symbol, exchange, timeframe)` — full indicator snapshot: RSI, MACD, Stochastic, ADX, CCI, AO, momentum, Bollinger Bands, Ichimoku, pivot points, MAs (all of them), and TradingView's overall RECOMMEND signal
- `get_specific_indicators(symbol, indicators)` — cherry-pick just the ones you need
- `get_historical_data(symbol, timeframe, max_records)` — OHLCV candle data streamed

**Use for your system:**
- **Deep dive technical section:** Pull RSI, volume trend, MA positions, and TradingView's recommendation in one call
- **Entry grid validation:** Get exact 50d SMA, 200d SMA, 10-week EMA values for tranche triggers
- **Weekly chart review:** Historical candle data to check for narrowing ranges and stabilisation
- **Supports multiple timeframes:** 1h, 4h, 1D, 1W — use 1W for your position trading style
- **No API key, no TradingView account needed. Completely free.**

---

### TV Server 3: tradingview-chart-mcp (Visual Chart Screenshots)
**By:** ertugrul59
**Best for:** Getting actual TradingView chart images that Claude can see and interpret. Visual technical analysis.

```bash
git clone https://github.com/ertugrul59/tradingview-chart-mcp.git
cd tradingview-chart-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Config:**
```json
"tradingview-charts": {
  "command": "/path/to/tradingview-chart-mcp/.venv/bin/python",
  "args": ["/path/to/tradingview-chart-mcp/main_optimized.py"]
}
```

**Requirements:**
- TradingView account (free tier works)
- ChromeDriver installed
- Session ID + session sign from TradingView cookies (set in `.env` file)

**What it gives you:**
- Actual chart screenshot images (PNG/base64)
- Any ticker, any interval (1m to 1M)
- Claude can **visually interpret** the chart — support/resistance, patterns, volume bars
- Browser pooling for fast concurrent requests

**Use for your system:**
- **Weekly review:** "Show me the weekly chart for ADBE" → Claude sees the chart and identifies stabilisation visually
- **Entry timing:** Visual confirmation of volume drying up, narrowing ranges, base formation
- **Pattern recognition:** Claude can identify failed breakdowns, higher lows on the weekly chart
- **Requires TradingView account (free works) + browser setup. More complex but most powerful.**

---

### TV Server 4: tradingview-mcp (Advanced — Backtesting + Sentiment)
**By:** atilaahmettaner (PyPI: `tradingview-mcp-server`)
**Best for:** Strategy backtesting, Reddit sentiment analysis, combined technical + sentiment signals. The most feature-rich but also the most complex.

```bash
git clone https://github.com/atilaahmettaner/tradingview-mcp.git
cd tradingview-mcp
uv run tradingview-mcp
```

**Config:**
```json
"tradingview-advanced": {
  "command": "uv",
  "args": ["run", "tradingview-mcp"],
  "cwd": "/path/to/tradingview-mcp"
}
```

**Tools (30+):**
- `market_snapshot` — S&P 500, BTC, VIX, EUR/USD in one call (daily regime check)
- `market_sentiment` — Reddit sentiment for any ticker (bullish/bearish score + post count)
- `backtest_strategy` — backtest RSI, MACD, Supertrend, Bollinger strategies on any ticker
- `compare_strategies` — rank which strategy performed best on a stock
- `combined_analysis` — technical + sentiment + news in one combined signal
- `screener` — stock screener with technical filters
- Walk-forward backtesting with equity curves
- Yahoo Finance integration for fundamental data

**Use for your system:**
- **Sunday session:** "What is Reddit saying about ADBE?" → Sentiment read for contrarian signal (extreme bearishness = your entry zone)
- **Regime check:** `market_snapshot` gives you SPY, VIX, major indices in one call
- **Validation:** Backtest whether mean-reversion works on your B1 candidates historically
- **No API key needed. Free and open source.**

---

### Recommended TradingView Setup (Priority Order)

| Priority | Server | Why | Difficulty |
|---|---|---|---|
| **1st** | `tradingview-mcp` (Henrik404) | Screener + indicators, no account needed, one-line install | Easy |
| **2nd** | `mcp-tradingview-server` (bidouilles) | Full indicator snapshots for deep dives, OHLCV data | Easy |
| **3rd** | `tradingview-mcp` (atilaahmettaner) | Sentiment + backtesting + combined analysis | Medium |
| **4th** | `tradingview-chart-mcp` (ertugrul59) | Visual charts (requires TradingView account + ChromeDriver) | Hard |

**Start with #1 and #2.** They're pip-installable, need no accounts, and cover 90% of your technical analysis needs. Add #3 when you want sentiment analysis. Add #4 only if you want Claude to visually interpret charts.

---

### Updated Complete MCP Config (All Servers)

```json
{
  "mcpServers": {
    "stockflow": {
      "command": "python",
      "args": ["/path/to/mcp-stockflow/stockflow.py"]
    },
    "stockscreen": {
      "command": "python",
      "args": ["/path/to/mcp-stockscreen/stockscreen.py"]
    },
    "optionsflow": {
      "command": "python",
      "args": ["/path/to/mcp-optionsflow/optionsflow.py"]
    },
    "alphavantage": {
      "httpUrl": "https://mcp.alphavantage.co/mcp?apikey=YOUR_AV_KEY"
    },
    "edgartools": {
      "command": "python",
      "args": ["-m", "edgar.mcp"]
    },
    "tradingview-screener": {
      "command": "uvx",
      "args": ["tradingview-mcp"]
    },
    "tradingview-indicators": {
      "command": "/path/to/mcp-tradingview-server/.venv/bin/python",
      "args": ["/path/to/mcp-tradingview-server/src/tradingview_server.py"],
      "cwd": "/path/to/mcp-tradingview-server"
    },
    "tradingview-advanced": {
      "command": "uv",
      "args": ["run", "tradingview-mcp"],
      "cwd": "/path/to/tradingview-mcp"
    }
  }
}
```

**Total MCP servers: 8** (stockflow, stockscreen, optionsflow, Alpha Vantage, EdgarTools, TV screener, TV indicators, TV advanced)
**Total cost: £0**
**API keys needed: 1** (Alpha Vantage — free signup)

---

*Educational purposes only. Not financial advice. All investment decisions are yours alone.*
