# Agent Handover — Contrarian Investing Platform

## Status: BUILT — Deep Dive V2 Frontend Complete (2026-04-10)

The platform is fully built and running at localhost:8000. All phases are implemented. The most recent work was the Deep Dive Frontend V2 rebuild (22 new components replacing the V1 monolith).

---

## What's Built

| Component | Status | Key Files |
|-----------|--------|-----------|
| **Backend — Core** | Done | `backend/main.py`, `backend/routers/`, `backend/services/` |
| **Backend — Screener** | Done | B1/B2 gates, fail-closed, S&P 500 scan |
| **Backend — Deep Dive** | Done | 8-section analysis, DCF, sensitivity matrix |
| **Backend — Deep Dive V2** | Done | 5 new services: quarterly, growth metrics, forward estimates, external targets, fund flow |
| **Backend — Options** | Done | Scanner with earnings proximity, delta/OI/spread filters |
| **Backend — Regime** | Done | SPY/QQQ/VIX regime check, 4 verdicts |
| **Backend — Watchlist/Positions** | Done | SQLite persistence, P&L tracking |
| **Backend — Research Intelligence** | Done | R1-R5: sentiment, SA RSS, transcripts, digest |
| **Backend — Enrichments** | Done | FMP, Finnhub, EdgarTools, insider, institutional, peers, technicals |
| **Frontend — All Pages** | Done | Screener, Deep Dive, Options, Regime, Watchlist, Positions |
| **Frontend — Deep Dive V2** | Done | 22 new components, contrarian flow enforced, adversarial review incorporated |
| **MCP Servers** | Done | TradingView indicators + screener configured in `.mcp.json` |
| **Bridge CLI** | Done | `bridge/deep_dive_worker.py` — AI analysis via Gemini |

---

## Architecture Decisions (Non-Negotiable)

These were validated through adversarial review. Do not change them.

| Decision | Reason |
|----------|--------|
| **Single process** — FastAPI serves built React static files | One `./start.sh` command |
| **SQLite with WAL mode** | Atomic writes, no corruption, concurrent-safe |
| **Fail-closed gates** — missing data = FAIL | A screener that passes stocks with missing data is dangerous |
| **WACC fixed at 10%** — varies growth only | Spec rule: WACC cannot change between scenarios |
| **3-year average FCF** — not single year | Spec rule |
| **SBC-adjusted FCF** — if SBC >10% of revenue | Spec rule |
| **Net debt from balance sheet** — never zero | Materially affects per-share valuation |
| **Reverse DCF before forward DCF** — always | Understand what market implies before projecting |
| **Bear case FIRST** — before bull case | Contrarian discipline: challenge the thesis before defending it |

---

## Deep Dive V2 Frontend — What Changed (2026-04-10)

The 320-line `DeepDivePage.jsx` monolith was replaced with a component architecture:

**Structure:**
- `DeepDivePage.jsx` — ~130 line orchestrator with `computeMemoTrust()`
- `StickyHeader` — ticker, price, conviction state, AI action (stripped per adversarial review)
- `AnalysisStatus` — top-level trust block: AI status, freshness, gates, completeness, critical gaps, earnings
- `DataStrip` — 3-tab data dashboard (Fundamentals/Technicals/History), user-controlled collapse only

**Core Flow (§1-8, contrarian order enforced):**
1. DataSnapshot — metrics grid, gates, data quality
2. FirstImpression — AI narrative
3. BearCase — stock risk + business risk (FIRST per spec)
4. BullCase — rebuttal + upside catalysts
5. Valuation — reverse DCF first, forward DCF, calculator, sensitivity, peers, targets
6. WholePicture — fund flow, insiders, institutional, AI narrative
7. SelfReview — bias check, pre-mortem
8. VerdictAction — verdict, conviction, entry grid, exit playbook, next review

**Appendices (A-D, supporting analysis, default collapsed):**
- A. GrowthEstimates — quarterly charts, forward estimates, implied vs actual gap
- B. MoatAssessment — 5-factor rating bars, overall/trend badges
- C. OpportunitiesThreats — two-column layout
- D. Scenarios — range bar, scenario table with probability labels

**Adversarial review findings addressed:**
- CRITICAL-1: Section order restored to CLAUDE.md canonical flow
- CRITICAL-2: VerdictScenarios split into VerdictAction + Scenarios appendix
- HIGH-1: StickyHeader stripped to essentials
- HIGH-2: DataStrip auto-collapse removed
- HIGH-3: AiProvenance component on all AI-structured sections
- HIGH-4: MissingSeverity component with critical/important/optional levels
- HIGH-5: AnalysisStatus trust block added
- MEDIUM-3: Company name from `fundamentals.name`, not `business_summary`

---

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/pages/DeepDivePage.jsx` | V2 orchestrator |
| `frontend/src/components/deep-dive/` | Header, status, data strip, shared utilities |
| `frontend/src/components/deep-dive/sections/` | 12 section components (8 core + 4 appendix) |
| `frontend/src/components/charts/` | 5 Recharts-based chart components |
| `backend/services/` | All backend services including V2 additions |
| `bridge/deep_dive_worker.py` | CLI for AI analysis |
| `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md` | Revised V2 design spec |
| `docs/superpowers/reviews/2026-04-08-deep-dive-frontend-v2-adversarial-review.md` | Adversarial review findings |
| `CLAUDE.md` | Project rules, screener gates, DCF rules, options rules |

---

## How to Run

```bash
cd stock-analysis-system
./start.sh          # Starts FastAPI at localhost:8000
```

For deep dive AI analysis:
```bash
python bridge/deep_dive_worker.py AAPL --post          # AI analysis
python bridge/deep_dive_worker.py AAPL --tv --post     # with TradingView data
python bridge/deep_dive_worker.py AAPL --context --tv  # full context + TV
```

---

## Tech Stack

- **Backend:** Python 3.12+ / FastAPI / uvicorn / SQLite (WAL mode)
- **Frontend:** React 18 / Vite / Tailwind CSS / Recharts
- **Data:** yfinance + FMP + Finnhub + EdgarTools
- **AI:** Gemini via bridge CLI, Claude Code for development
- **MCP:** TradingView indicators + screener (no API key needed)
- **Storage:** SQLite — watchlist, positions, scans, deep dives, research

---

## Screener Rules

**B1 Hard Gates (ALL must pass, missing = FAIL):**
- Operating margin >20%, FCF positive, down >20% from 52w high
- Revenue growth >0%, D/E <5x, Forward P/E <50x

**B2 Hard Gates (ALL must pass, missing = FAIL):**
- Revenue growth >25%, Gross margin >40%, Revenue >$200M

---

## Deep Dive Sequence (NEVER skip or reorder)

1. Data Snapshot  2. First Impression  3. Bear Case FIRST (stock vs business)
4. Bull Case (rebuttal + upside)  5. Valuation (reverse DCF first, then forward)
6. Whole Picture  7. Self-Review  8. Verdict + Entry Grid + Exit Playbook

---

## DCF Rules (Non-Negotiable)

- SBC-adjusted FCF if SBC >10% of revenue
- Use 3-year average FCF, not single year
- WACC fixed at 10% across ALL scenarios. Only vary growth assumptions.
- Terminal value MUST be <50% of total
- Reverse DCF before forward DCF — always
- Net debt from balance sheet, never zero

---

## Options Rules (Non-Negotiable)

- Premium = stop loss. Max GBP500/trade. 60-120 DTE. Delta 0.25-0.40.
- OI >500. Spread <10%. Premium <=USD7. Calls only for B1.
- MUST check earnings proximity (14 days). IV CRUSH RISK warning.
- Exit: half at 3x, rest at 4x. Time stop 21 DTE if <2x.
- Never hold through earnings. Never add to losers. Max 5 positions.
- DEFENSIVE/CASH regime = NO new positions.

---

## Duplicate Directory Note

`stock-analysis-system/` contains a copy of the full app. It is tracked as a gitlink (orphaned submodule reference with no `.gitmodules`). The canonical frontend source is `frontend/` at the repo root. The `stock-analysis-system/` copy is synced periodically but may lag behind.
