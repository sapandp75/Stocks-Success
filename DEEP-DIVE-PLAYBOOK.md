# Deep Dive Playbook

Step-by-step guide for running a full deep dive on any ticker.

---

## Prerequisites

```bash
cd "/Users/sbakshi/Documents/Stocks Success"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Verify: `curl -s http://localhost:8000/api/health` should return `{"status":"ok"}`

> The backend serves both the API and the built frontend static files on port 8000.

---

## Step 1: Gather Context

Pull all quantitative data and research context for Claude to read:

```bash
python3 bridge/deep_dive_worker.py TICKER --context --tv
```

This prints to stdout:
- Fundamentals, financials, FCF, SBC, net debt
- Technicals (RSI, MACD, ADX, Bollinger, support/resistance, RS vs SPY)
- TradingView indicator snapshot (buy/sell/neutral counts, pivots)
- 5-year financial history (revenue, EPS, margins, FCF trends)
- Insider activity (net buys/sells, sentiment)
- Institutional holdings (trend, top holders)
- Analyst consensus + contrarian signal
- Research articles, transcripts

Claude reads this output and uses it to write the analysis.

---

## Step 2: Write the 8-Section Analysis

Follow this sequence exactly. **Never skip or reorder.**

| # | Section | Key Rules |
|---|---------|-----------|
| 1 | **Data Snapshot** | Summarize gates, data quality, key metrics |
| 2 | **First Impression** | Gut reaction before deep analysis |
| 3 | **Bear Case** | ALWAYS first. Split into **stock risk** (price, valuation, technicals) and **business risk** (competitive, execution, structural) |
| 4 | **Bull Case** | **Rebuttal** of each bear point + **independent upside** catalysts |
| 5 | **Valuation** | Reverse DCF first (what growth is priced in?), then forward DCF (bear/base/bull). See DCF rules below |
| 6 | **Whole Picture** | Synthesize: fund flows, insider/institutional, macro regime, sector positioning |
| 7 | **Self-Review** | Challenge your own analysis. What could you be wrong about? |
| 8 | **Verdict + Entry Grid + Exit Playbook** | Final call: BUY/WATCH/PASS, conviction (HIGH/MODERATE/LOW), tranche prices, exit rules, next review date |

### DCF Rules (Non-Negotiable)

- Use **3-year average FCF**, never a single year
- **SBC-adjust** FCF if SBC > 10% of revenue
- **WACC fixed at 10%** across ALL scenarios. Only vary growth assumptions
- **Terminal value < 50%** of total intrinsic value
- **Reverse DCF before forward DCF** — always
- **Net debt from balance sheet** — never zero

### Appendices (after Section 8)

| Appendix | Content |
|----------|---------|
| A: Growth Estimates | Quarterly trends, forward estimates, implied vs historical growth gap |
| B: Moat Assessment | Structured moat scoring (switching costs, network effects, intangibles, cost advantage, scale) |
| C: Opportunities & Threats | Bulleted lists of each |
| D: Scenarios | Bear/base/bull price targets with probabilities |

### Appendix JSON Shape (Required for Dashboard Rendering)

Two appendix sections are schema-sensitive in the frontend. Do not improvise these keys.

**Moat Assessment** must be posted as:

```json
"moat_structured": {
  "overall": "WIDE|NARROW|NONE",
  "trend": "STRENGTHENING|STABLE|ERODING",
  "factors": [
    {"name": "Switching Costs", "score": 4, "max": 5, "note": "..."},
    {"name": "Network Effects", "score": 1, "max": 5, "note": "..."},
    {"name": "Intangibles", "score": 5, "max": 5, "note": "..."},
    {"name": "Cost Advantage", "score": 4, "max": 5, "note": "..."},
    {"name": "Scale", "score": 5, "max": 5, "note": "..."}
  ]
}
```

Do **not** post a flat object like `"switching_costs": {...}` unless you are also updating the UI.

**Scenarios** must be posted as either:

```json
"scenarios": [
  {"name": "Bear", "target_price": 340, "probability": 0.25, "rationale": "..."},
  {"name": "Base", "target_price": 450, "probability": 0.50, "rationale": "..."},
  {"name": "Bull", "target_price": 580, "probability": 0.25, "rationale": "..."}
]
```

or:

```json
"scenarios": {
  "worst": {"name": "Bear", "target_price": 340, "probability": 0.25, "rationale": "..."},
  "base": {"name": "Base", "target_price": 450, "probability": 0.50, "rationale": "..."},
  "best": {"name": "Bull", "target_price": 580, "probability": 0.25, "rationale": "..."}
}
```

Use numeric probabilities like `0.25`, not strings like `"25%"`.

---

## Step 3: POST Analysis to Dashboard

Format your analysis as JSON and pipe it to the bridge:

```bash
cat <<'EOF' | python3 bridge/deep_dive_worker.py TICKER --post
{
  "first_impression": "...",
  "bear_case_stock": "...",
  "bear_case_business": "...",
  "bull_case_rebuttal": "...",
  "bull_case_upside": "...",
  "whole_picture": "...",
  "self_review": "...",
  "verdict": "...",
  "conviction": "HIGH|MODERATE|LOW",
  "entry_grid": [
    {"tranche": 1, "price": 400.00, "pct_of_position": "40%", "trigger": "Current levels"},
    {"tranche": 2, "price": 370.00, "pct_of_position": "30%", "trigger": "Support break"},
    {"tranche": 3, "price": 340.00, "pct_of_position": "30%", "trigger": "Bear scenario"}
  ],
  "exit_playbook": "...",
  "next_review_date": "2026-07-10",
  "moat_structured": {
    "overall": "WIDE",
    "trend": "STABLE",
    "factors": [
      {"name": "Switching Costs", "score": 4, "max": 5, "note": "..."},
      {"name": "Network Effects", "score": 2, "max": 5, "note": "..."},
      {"name": "Intangibles", "score": 5, "max": 5, "note": "..."},
      {"name": "Cost Advantage", "score": 3, "max": 5, "note": "..."},
      {"name": "Scale", "score": 4, "max": 5, "note": "..."}
    ]
  },
  "opportunities": ["...", "..."],
  "threats": ["...", "..."],
  "scenarios": [
    {"name": "Bear", "target_price": 340, "probability": 0.25, "rationale": "..."},
    {"name": "Base", "target_price": 450, "probability": 0.50, "rationale": "..."},
    {"name": "Bull", "target_price": 580, "probability": 0.25, "rationale": "..."}
  ]
}
EOF
```

Response: `{"status": "saved", "ticker": "TICKER"}`

### Step 3A: Verify Appendix Fields Saved Correctly

Immediately verify the stored payload after every POST:

```bash
curl -s http://localhost:8000/api/deep-dive/TICKER | python3 -m json.tool
```

Confirm all of the following before considering the deep dive complete:
- `ai_analysis.moat_structured.overall` exists
- `ai_analysis.moat_structured.factors` is a non-empty list
- `ai_analysis.scenarios` exists
- each scenario has `name`, `target_price`, and numeric `probability`

If moat or scenarios are missing in the dashboard, assume a schema mismatch first.

---

## Step 4: View in Dashboard

Open: **http://localhost:8000/deep-dive/TICKER**

### What You See

**Sticky Header** — ticker, price, change, sector, conviction badge

**Analysis Status** — data completeness, staleness, memo trust score

**Data Strip (5 tabs):**
| Tab | Content |
|-----|---------|
| Fundamentals | Valuation, profitability, health, size metrics |
| Technicals | RSI, MACD, Bollinger, support/resistance, relative strength |
| Chart | Live TradingView chart |
| LEAPS | Options chain with rules highlighting (green = passes) |
| History | Sparkline grid of 5-year financial trends |

**Core Flow** — Sections 1-8 rendered in order

**Appendices** — Growth estimates, moat radar, opportunities/threats, scenarios

---

## Data Persistence

All data persists automatically in SQLite (`backend/data/app.db`):

- **AI analysis** — saved to `deep_dives` table columns + `ai_sections_json`
- **Market data** — saved to `snapshot_json` (24 fields: fundamentals, technicals, financials, options, growth, analyst, insider, institutional, DCF results, etc.)
- **Fallback logic** — on every page load, live data is fetched. If any fetch fails, the last saved value is restored from snapshot
- **Data survives** server restarts, page reloads, API outages
- **Data refreshes** only when you run a new deep dive or when live fetches succeed

---

## Quick Reference

```bash
# Full deep dive workflow (one-liner)
python3 bridge/deep_dive_worker.py TICKER --context --tv

# Check stored data
python3 bridge/deep_dive_worker.py TICKER --get

# Submit analysis
cat analysis.json | python3 bridge/deep_dive_worker.py TICKER --post

# Direct API check
curl -s http://localhost:8000/api/deep-dive/TICKER | python3 -m json.tool

# Gemini fallback (from dashboard UI)
# Click "Re-analyze" button on the Analysis Status bar
```

---

## Options Rules (for LEAPS tab / Entry Grid)

- Premium = stop loss. Max GBP500/trade
- DTE: 60-120 days. Delta: 0.25-0.40
- OI > 500. Spread < 10%. Premium <= $7. Calls only for B1
- Check earnings proximity (14 days) — IV CRUSH RISK
- Exit: half at 3x, rest at 4x. Time stop 21 DTE if < 2x
- Never hold through earnings. Never add to losers. Max 5 positions
- DEFENSIVE/CASH regime = NO new positions

---

## Gates (Auto-Checked)

A ticker must pass these before deep dive:
- Market cap >= $2B
- Average volume >= 500K shares/day

Screener buckets (for watchlist context):
- **B1**: Op margin >20%, FCF+, down >20%, rev growth >0%, D/E <5x, fwd PE <50x
- **B2**: Rev growth >25%, gross margin >40%, revenue >$200M
