# Contrarian Investing Platform — Claude Code Context

## What This Is
Unified stock screening + deep dive + options system for a contrarian quality investor.
Single-process local app at localhost:8000. SQLite storage. React frontend built to static.

## Deep Dive Bridge
To run a deep dive analysis, use the bridge script:
```
python bridge/deep_dive_worker.py ADBE --post
```
This POSTs your AI analysis to the local API at /api/deep-dive/ADBE.
The dashboard will then render your analysis in the 8-section view.

## Available MCP Tools (Value Investing Server)
- analyze_stock_complete, calculate_intrinsic_value, calculate_moat_score
- calculate_margin_of_safety, calculate_owner_earnings, calculate_position_size
- get_financial_statements, get_company_info, get_historical_prices
- get_analyst_estimates, get_analyst_ratings, get_ownership_analysis
- get_dividend_analysis, get_risk_metrics, stock_screener, search_ticker

## Screener Rules (fail-closed: missing data = FAIL)
B1: op margin >20%, FCF+, down >20%, rev growth >0%, D/E <5x, fwd PE <50x
B2: rev growth >25%, gross margin >40%, revenue >$200M

## Deep Dive Sequence (NEVER skip or reorder)
1. Data Snapshot  2. First Impression  3. Bear Case FIRST (stock vs business)
4. Bull Case (rebuttal + upside)  5. Valuation (reverse DCF first, then forward)
6. Whole Picture  7. Self-Review  8. Verdict + Entry Grid + Exit Playbook

## DCF Rules (Non-Negotiable)
- SBC-adjusted FCF if SBC >10% of revenue
- Use 3-year average FCF, not single year
- WACC fixed at 10% across ALL scenarios. Only vary growth assumptions.
- Terminal value MUST be <50% of total
- Reverse DCF before forward DCF — always
- Net debt from balance sheet, never zero

## Options Rules (Non-Negotiable)
- Premium = stop loss. Max GBP500/trade. 60-120 DTE. Delta 0.25-0.40.
- OI >500. Spread <10%. Premium <=USD7. Calls only for B1.
- MUST check earnings proximity (14 days). IV CRUSH RISK warning.
- Exit: half at 3x, rest at 4x. Time stop 21 DTE if <2x.
- Never hold through earnings. Never add to losers. Max 5 positions.
- DEFENSIVE/CASH regime = NO new positions.

## Koyfin Palette
bg: #f0f1f3, cards: #ffffff, hover: #f7f8fa, borders: #e2e4e8
green: #00a562, red: #e5484d, amber: #d97b0e
