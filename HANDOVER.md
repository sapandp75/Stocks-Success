# Agent Handover — Contrarian Investing Platform

## Status: READY TO BUILD (Phase 1, Task 1)

No code exists yet. The implementation plan is complete and reviewed. Start from Task 1.

---

## What This Project Is

A **unified local web app** for a contrarian quality investor that combines:

1. **Stock Screener** — Scans S&P 500 for B1 (contrarian value) and B2 (Peter Lynch growth) candidates
2. **Deep Dive Dashboard** — Gate 1-8 fundamental analysis with DCF calculator
3. **Options Scanner** — Finds qualifying call contracts for B1 recovery plays
4. **Market Regime Filter** — Gate 0 check (SPY/QQQ/VIX) before any new positions
5. **Watchlist** — Persistent tracking with thesis notes and entry zones
6. **Position Tracker** — Stock + options positions with P&L summary

All in one app at `http://localhost:8000`.

---

## Architecture Decisions (Non-Negotiable)

These were validated through an adversarial review. Do not change them.

| Decision | Reason |
|----------|--------|
| **Single process** — FastAPI serves built React static files | Simpler than 2-process. One `./start.sh` command. |
| **SQLite with WAL mode** — not JSON files | Atomic writes, no corruption, concurrent-safe, proper IDs |
| **Fail-closed gates** — missing data = FAIL | A screener that passes stocks with missing P/E or D/E is dangerous |
| **WACC fixed in sensitivity matrix** — varies growth only | Spec rule: "WACC cannot be changed between scenarios" |
| **3-year average FCF** — not single-year | Spec rule: "3-year average FCF, not peak or trough" |
| **SBC-adjusted FCF** — subtract SBC if >10% of revenue | Spec rule: "SBC adjustment applied by default" |
| **Net debt from balance sheet** — never zero | Materially affects per-share valuation |
| **Earnings proximity check** — 14 days | Spec rule: flag IV crush risk before surfacing any contract |
| **Claude Code bridge** — CLI script POSTs to API | Real mechanism, not "Claude will somehow POST" |
| **Reverse DCF before forward DCF** — always | Spec rule: understand what market implies before projecting |

---

## Key Files

| File | Purpose |
|------|---------|
| `docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md` | **THE PLAN** — 12 Phase 1 tasks with full code, TDD steps, and commit points |
| `STOCK-SCREENER-DEEPDIVE-BUILD.md` | Spec 1: Stock screener + deep dive requirements (153 features) |
| `CONTRARIAN-OPTIONS-SYSTEM-BUILD.md` | Spec 2: Options system requirements (105 features) |
| This file (`HANDOVER.md`) | Context for the implementing agent |

---

## How to Execute

**Recommended:** Use `superpowers:subagent-driven-development` skill to dispatch one subagent per task.

**Alternative:** Use `superpowers:executing-plans` skill for inline execution.

Read `docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md` and execute tasks 1-12 in order. Each task has:
- Spec feature coverage (e.g., "Covers: S1-03-42")
- Adversarial review finding addressed (e.g., "Addresses review: #3")
- TDD steps: write test → verify fail → implement → verify pass → commit
- Exact file paths and code

---

## Phasing

| Phase | Tasks | Data Sources | When |
|-------|-------|-------------|------|
| **Phase 1: Core MVP** | 1-12 | yfinance only | NOW |
| **Phase 2: Data Enrichment** | 13-15 | +FMP +Finnhub +EdgarTools | After user gets free API keys |
| **Phase 3: MCP + Technical** | 16-17 | +TradingView +Alpha Vantage | After Phase 1+2 stable |

**Start with Phase 1 only.** It produces a fully working app with all 6 dashboard pages.

---

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI / uvicorn / SQLite
- **Frontend:** React 18 / Vite / Tailwind CSS (built to static, served by FastAPI)
- **Data:** yfinance (Phase 1), FMP + Finnhub + EdgarTools (Phase 2), TradingView + Alpha Vantage MCP (Phase 3)
- **AI Layer:** Claude Code (Max plan) generates deep dive analysis via `bridge/deep_dive_worker.py`
- **Storage:** SQLite with WAL mode (watchlist, positions, scans, deep dives)

---

## Working Directory

Build everything inside: `/Users/sbakshi/Documents/Stocks Success/stock-analysis-system/`

The `stock-analysis-system/` subdirectory does not exist yet. Task 1 creates it.

---

## User Profile

- Contrarian quality investor
- Uses B1 (contrarian value) + B2 (Peter Lynch growth) framework
- Trades options: GBP 500/trade, 4x target, 60-120 DTE, delta 0.25-0.40
- Has Claude Max plan (unlimited Claude Code usage)
- Wants the app running locally on laptop at localhost:8000
- Prefers Koyfin-style dashboard aesthetics (light theme, specific color palette)
- No paid API keys yet — Phase 1 uses yfinance only

---

## Koyfin Palette (Use Everywhere)

```
Background:  #f0f1f3
Cards:       #ffffff
Hover:       #f7f8fa
Borders:     #e2e4e8
Green:       #00a562
Red:         #e5484d
Amber:       #d97b0e
Text:        #1a1a2e
Muted:       #6b7280
```

No black backgrounds. No pure white backgrounds.

---

## Screener Rules (Memorize These)

**B1 Hard Gates (ALL must pass, missing = FAIL):**
- Operating margin > 20%
- Free cash flow positive
- Stock down > 20% from 52-week high
- Revenue growth > 0% YoY
- Debt-to-equity < 5x
- Forward P/E < 50x

**B2 Hard Gates (ALL must pass, missing = FAIL):**
- Revenue growth > 25% YoY
- Gross margin > 40%
- Revenue > $200M

**Warning flags (show, don't filter):**
- SLOW GROWTH: revenue growth < 5%
- HIGH LEVERAGE: D/E > 3x
- HIGH SHORT: short interest > 10%
- LEVERAGE-DRIVEN ROE: ROE > 100%
- P/E COMPRESSION: trailing P/E > 3x forward P/E
- EARNINGS SOON: earnings within 14 days
- CYCLICAL: Energy or Basic Materials sector
- CASH BURN: negative FCF (B2)
- EXTREME VALUATION: forward P/E > 80x (B2)

---

## DCF Rules (Non-Negotiable — Enforce in Code)

1. SBC-adjusted FCF as starting point if SBC > 10% of revenue
2. Use 3-year average FCF, not single year, not peak, not trough
3. WACC fixed at 10% across ALL scenarios — only vary business growth assumptions
4. Terminal value MUST be < 50% of total DCF value — trigger warning if exceeded
5. Reverse DCF before forward DCF — always show what price implies first
6. Net debt from balance sheet — never hardcode to zero
7. Forward DCF with 3 scenarios: bear, base, bull

---

## Options Rules (Non-Negotiable — Enforce in Code)

- Calls only for B1 recovery plays
- 60-120 DTE, delta 0.25-0.40, OI > 500, spread < 10%, premium <= $7 USD
- Check earnings proximity: flag IV CRUSH RISK if earnings within 14 days of expiry
- Premium = stop loss. Max GBP 500 per trade.
- Exit: half at 3x, rest at 4x. Time stop at 21 DTE if below 2x.
- Never hold through earnings. Never add to losers. Max 5 concurrent positions.
- DEFENSIVE/CASH regime = NO new positions, period.

---

## Regime Verdicts

| Verdict | Max New Positions | Action |
|---------|-------------------|--------|
| DEPLOY | 5 | All signals green, trade normally |
| CAUTIOUS | 2 | Mixed signals, be selective |
| DEFENSIVE | 0 | No new positions, review existing |
| CASH | 0 | Close weak positions, preserve capital |

VIX > 35 = CASH override regardless of other signals.

---

## Deep Dive Sequence (8 Sections, NEVER Skip or Reorder)

1. **Data Snapshot** — Numbers only, no opinion. Financial metrics grid.
2. **First Impression** — One-paragraph gut check (AI-generated, editable).
3. **Bear Case** — FIRST. Split: "Bear on Stock" vs "Bear on Business." Red accent.
4. **Bull Case** — Each bull point MUST address a specific bear point. Green accent.
5. **Valuation** — Reverse DCF first, then forward DCF (3 scenarios), then sensitivity matrix, then peer comparison.
6. **Whole Picture** — Sector theme, smart money (13F), management, customer evidence.
7. **Self-Review** — Bias check vs first impression, gap check, pre-mortem, "what would make me wrong."
8. **Verdict** — Bucket assignment, conviction (HIGH/MODERATE/LOW), entry grid (4 tranches), exit playbook, decision tree, next review date.

---

## Connected MCP Server (Already Available in Claude)

The user has a **Value Investing MCP server** connected with 17 tools:
- `analyze_stock_complete` — full Buffett-style analysis
- `calculate_intrinsic_value` — 10-year DCF
- `calculate_moat_score` — economic moat 0-100
- `calculate_margin_of_safety` — risk-adjusted buy signals
- `calculate_owner_earnings` — NI + D&A - CapEx - dWC
- `calculate_position_size` — modified Kelly Criterion
- `get_financial_statements` — balance sheet, income, cash flow
- `get_company_info` — profile, sector, fundamentals
- `get_historical_prices` — OHLCV data
- `get_analyst_estimates` — price targets, growth forecasts
- `get_analyst_ratings` — consensus, earnings estimates
- `get_ownership_analysis` — insider & institutional
- `get_dividend_analysis` — 5-factor safety scoring
- `get_risk_metrics` — Altman Z-Score, multi-dimensional risk
- `stock_screener` — filter with 96 equity filters
- `search_ticker` — find tickers by company name
- `calculate_buffett_indicator` — total market cap / GDP

Use these for AI-powered deep dive analysis. The backend app uses yfinance directly for batch operations (screening 500 tickers).

---

## What NOT to Do

- Do not use JSON files for persistence — use SQLite
- Do not run 2 processes (FastAPI + Vite dev server) — single process serves static files
- Do not pass stocks with missing data through hard gates — fail closed
- Do not vary WACC in the sensitivity matrix — it violates the spec
- Do not use single-year FCF for DCF — use 3-year average
- Do not hardcode net debt to zero — fetch from balance sheet
- Do not skip earnings proximity check on options — IV crush risk is critical
- Do not create placeholder frontend pages — every page must be fully functional
- Do not add features beyond the plan — YAGNI
- Do not install Phase 2/3 dependencies in Phase 1
