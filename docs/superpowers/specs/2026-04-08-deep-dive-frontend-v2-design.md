# Deep Dive Frontend V2 — Design Spec

**Date:** 2026-04-08
**Scope:** Task 14 from Deep Dive V2 plan — rebuild `DeepDivePage.jsx` to match the 10-section investment memo format with expanded data visualizations.
**Depends on:** Backend Tasks 1-13 (expanded GET endpoint delivering gates, quarterly, growth_metrics, forward_estimates, external_targets, fund_flow, staleness_days).

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Page structure | Hybrid: data dashboard header + 10 memo sections | Numbers always visible at a glance; AI narrative flows below |
| Chart library | Recharts (~45KB gzip) | V2 needs bar charts, line charts, range bars — hand-rolling is brittle and slow |
| Data strip density | Two-tier: sticky header + collapsible tabbed panels | Ticker/price/gates always visible; data accessible but not overwhelming |
| Pre-AI behavior | Show data panels, lock pure-narrative sections | Data before opinion; matches contrarian methodology |
| Moat visualization | Horizontal segmented bar ratings | More readable than radar charts; consistent with Koyfin aesthetic |
| Scenario visualization | Table + horizontal range bar | Range bar shows price position in outcome distribution at a glance |
| Scroll behavior | Sticky tier 1, auto-collapsible tier 2 | Maximizes reading space for memo; data one click away |
| AI trigger | Manual (click "Analyze" button) | Not auto-generated on page load |
| Component architecture | Section-per-file (Approach 2) | Each component <150 lines, independently testable, easy to expand |

---

## Architecture

### Data Flow

```
GET /api/deep-dive/:ticker
        │
        ▼
  DeepDivePage.jsx (orchestrator)
        │
        ├── StickyHeader ← fundamentals, gates, staleness_days, earnings_date
        ├── DataStrip ← fundamentals, technicals, financial_history, quarterly, growth_metrics
        │
        └── 10 × CollapsibleSection
            ├── GatesBusiness ← gates, fundamentals, ai_analysis.gates_summary
            ├── KeyFundamentals ← fundamentals, growth_metrics, ai_analysis.key_fundamentals
            ├── GrowthSection ← quarterly, growth_metrics, forward_estimates, reverse_dcf, ai_analysis.growth
            ├── BearCase ← ai_analysis.bear_case_stock, ai_analysis.bear_case_business
            ├── BullCase ← ai_analysis.bull_case_rebuttal, ai_analysis.bull_case_upside
            ├── ValuationTargets ← reverse_dcf, forward_dcf, sensitivity_matrix, external_targets, peers, analyst, ai_analysis.valuation
            ├── MoatAssessment ← ai_analysis.moat_structured
            ├── OpportunitiesThreats ← ai_analysis.opportunities, ai_analysis.threats
            ├── SmartMoney ← fund_flow, insider_activity, institutional, ai_analysis.smart_money
            └── VerdictScenarios ← ai_analysis.scenarios, ai_analysis.verdict, ai_analysis.conviction, ai_analysis.entry_grid, ai_analysis.exit_playbook, ai_analysis.next_review_date
```

Single API call. No prop drilling beyond one level — each section receives only its data slice.

### File Structure

```
frontend/src/
├── pages/
│   └── DeepDivePage.jsx              (~100 lines, orchestrator)
├── components/
│   ├── deep-dive/
│   │   ├── StickyHeader.jsx          (~80 lines)
│   │   ├── DataStrip.jsx             (~150 lines)
│   │   └── sections/
│   │       ├── GatesBusiness.jsx           (~60 lines)
│   │       ├── KeyFundamentals.jsx         (~80 lines)
│   │       ├── GrowthSection.jsx           (~120 lines)
│   │       ├── BearCase.jsx                (~60 lines)
│   │       ├── BullCase.jsx                (~60 lines)
│   │       ├── ValuationTargets.jsx        (~140 lines)
│   │       ├── MoatAssessment.jsx          (~80 lines)
│   │       ├── OpportunitiesThreats.jsx    (~70 lines)
│   │       ├── SmartMoney.jsx              (~90 lines)
│   │       └── VerdictScenarios.jsx        (~120 lines)
│   └── charts/
│       ├── QuarterlyBarChart.jsx      (~50 lines)
│       ├── TrendSparkline.jsx         (~40 lines)
│       ├── MoatRatingBars.jsx         (~50 lines)
│       ├── ScenarioRangeBar.jsx       (~45 lines)
│       └── PriceTargetBar.jsx         (~45 lines)
```

**Total: ~1,390 lines across 17 new files** (avg ~82 lines/file).

**Existing components reused:** CollapsibleSection (minor enhancement: add `locked` prop for lock icon + muted styling when AI not yet generated), DcfCalculator, SensitivityMatrix, PeerTable, InsiderPanel, EntryGrid, AiAnalyzeButton, TechnicalPanel, SparklineGrid, AnalystBar, ResearchPanel.

**New dependency:** `recharts` added to `package.json`.

---

## Component Specifications

### DeepDivePage.jsx (Orchestrator)

**State:**
- `ticker` — from URL param (`useParams`) or search input
- `data` — full response from `GET /api/deep-dive/:ticker`
- `loading` / `error` — fetch status
- `dataStripCollapsed` — boolean, controls tier 2 auto-collapse

**Behavior:**
- Single `useEffect` on ticker change triggers `getDeepDive(ticker)`
- `IntersectionObserver` on sentinel div below DataStrip controls `dataStripCollapsed`
- Passes data slices as props to children — no context providers needed
- Search input + "Load" button navigates to `/deep-dive/${ticker}`

---

### StickyHeader.jsx (Tier 1)

Always pinned at top (`position: sticky`, `z-50`). Single row, ~56px height. White background, bottom border `#e2e4e8`.

| Element | Source | Behavior |
|---------|--------|----------|
| Ticker + Company Name | ticker prop, `fundamentals.business_summary` | Bold, large text. Left-aligned. |
| Current Price + Change | `fundamentals.price` | Green/red based on direction. |
| Drop from 52w High | `fundamentals.drop_from_high` | Red badge, e.g. "-32%" |
| Gates Badge | `gates.passes_all` | Green "GATES PASS" or red "GATES FAIL" pill. Hover tooltip: market cap + volume vs thresholds. |
| Staleness Indicator | `staleness_days` | Hidden if no AI. Green "Fresh" if <=3d. Amber if 4-14d. Red if >14d. Click triggers re-analysis. |
| Earnings Proximity | `fundamentals.earnings_date` | Amber banner if within 14 days: "Earnings in X days" |
| AI Analyze Button | existing `AiAnalyzeButton` | Right-aligned. Spinner during analysis. `onComplete` re-fetches data. |

**Responsive:** Ticker + price on first line, badges wrap to second line on <768px.

---

### DataStrip.jsx (Tier 2)

Three tabs: **Fundamentals | Technicals | History**

**Collapsed state:** 36px strip showing tab labels + chevron expand button. Clicking a tab expands + switches.

**Expanded state:** ~280px height.

**Auto-collapse:** `IntersectionObserver` watches sentinel div. When scrolled past, `dataStripCollapsed = true`. CSS transition via `max-height` + `opacity`.

**Fundamentals tab — 4-row metric grid:**

| Row | Metrics |
|-----|---------|
| Valuation | Forward P/E, Trailing P/E, PEG, EV/EBIT, FCF Yield |
| Profitability | Gross Margin, Operating Margin, Profit Margin, ROE, ROIC |
| Health | D/E, Free Cash Flow, Piotroski F-Score, Accruals Ratio, Buyback Yield |
| Size | Market Cap, Enterprise Value, Avg Volume, Short Interest, Short Ratio |

Each cell: label above, value below. Color thresholds from screener rules (operating margin green >20%, D/E red >5x, etc.).

**Technicals tab:** Reuses existing `TechnicalPanel` + `SparklineGrid`.

**History tab:** 4-year trends using Recharts `AreaChart` (120x60px each) — revenue, EPS, FCF, operating margin. Trend-colored fill.

---

### Memo Sections (1-10)

All sections use the existing `CollapsibleSection` component (white card, 3px left accent border, numbered badge, title, toggle arrow).

#### Section 1: GatesBusiness.jsx
- **Accent:** blue `#3b82f6`
- **Default:** always open
- **Content:** Gates pass/fail badges with actual vs threshold values. AI paragraph (business description, sector, revenue model). Pre-AI fallback: `fundamentals.business_summary` (500-char yfinance summary).

#### Section 2: KeyFundamentals.jsx
- **Accent:** indigo `#6366f1`
- **Default:** open if data exists
- **Content:** 3-column metric grid (PE, forward PE, PEG, FCF yield, ROE, ROIC, EV/EBIT, gross margin, operating margin, D/E, Piotroski F-Score). Red flag callouts (accruals >10%, ROIC declining, negative FCF yield). AI first impression paragraph at bottom. Pre-AI: metrics always show, no narrative.

#### Section 3: GrowthSection.jsx
- **Accent:** cyan `#06b6d4`
- **Default:** open if quarterly data exists
- **Content:**
  - Quarterly revenue bar chart (`QuarterlyBarChart`) — last 8 quarters, Y/Y growth labels, green/red bars
  - EPS quarterly trend line chart
  - Forward estimates panel — 1yr/3yr/5yr EPS and revenue growth, beat rate streak badge
  - Implied vs Actual gap callout — "Market implies X% growth. Historical CAGR is Y%. Gap: Z%." Green if undervalued, red if optimistic.
  - AI narrative when available.

#### Section 4: BearCase.jsx
- **Accent:** red `#e5484d`
- **Default:** open if AI exists; collapsed with lock icon if not
- **Content:** Two columns — "Stock Risk" (left) and "Business Risk" (right). AI bullet points. Pre-AI: locked placeholder "Run AI analysis to generate bear case."

#### Section 5: BullCase.jsx
- **Accent:** green `#00a562`
- **Default:** open if AI exists; collapsed with lock icon if not
- **Content:** Two columns — "Rebuttal" (left, countering bear points) and "Upside Catalysts" (right). Pre-AI: locked placeholder.

#### Section 6: ValuationTargets.jsx
- **Accent:** amber `#d97b0e`
- **Default:** always open
- **Content:**
  - Reverse DCF block — implied growth rate + interpretation
  - Forward DCF — 3-scenario grid (bear/base/bull): intrinsic value/share, terminal value %, margin of safety %
  - `DcfCalculator` — existing interactive component (WACC locked at 10%)
  - `SensitivityMatrix` — existing component
  - Price target comparison — `PriceTargetBar` showing Yahoo, Finviz, DCF base, current price on same axis
  - `PeerTable` — existing component
  - AI narrative when available.

#### Section 7: MoatAssessment.jsx
- **Accent:** purple `#8b5cf6`
- **Default:** open if AI exists; collapsed with lock icon if not
- **Content:**
  - `MoatRatingBars` — 5 factors (Pricing Power, Switching Costs, Network Effects, Intangible Assets, Cost Advantage). Each as 4-step segmented bar (NONE→STRONG) with evidence text.
  - Overall moat badge (NONE/NARROW/WIDE)
  - Trend badge (STRENGTHENING/STABLE/ERODING) with arrow icon

#### Section 8: OpportunitiesThreats.jsx
- **Accent:** teal `#14b8a6`
- **Default:** open if AI exists; collapsed with lock icon if not
- **Content:** Two columns — "Opportunities" (revenue expansion, margin expansion, value unlock) and "Threats" (competition, regulation, disruption). AI bullets with quantified TAM/impact.

#### Section 9: SmartMoney.jsx
- **Accent:** violet `#7c3aed`
- **Default:** open if fund_flow or insider data exists
- **Content:**
  - Fund flow summary — net buy/sell badge, new positions count, exits count
  - Top holders table — fund name, shares, % change Q/Q, type (index/value/growth/activist)
  - `InsiderPanel` — existing component
  - AI signal interpretation when available.

#### Section 10: VerdictScenarios.jsx
- **Accent:** green `#00a562`
- **Default:** open if AI exists; collapsed with lock icon if not
- **Content:**
  - `ScenarioRangeBar` — worst→best horizontal bar, current price line, probability-weighted target diamond
  - Scenario table — 3 rows (worst/base/best), columns: revenue, margin, EPS, target price, probability, upside/downside %. Color-coded rows (red/amber/green).
  - Verdict badge — large BUY/HOLD/AVOID pill with conviction (HIGH/MODERATE/LOW)
  - `EntryGrid` — existing component (4 tranches)
  - Exit playbook — bullet list (profit target, stop loss, time stop, thesis-breaker)
  - Next review date badge

---

## Shared Chart Components

### QuarterlyBarChart.jsx
- Recharts `BarChart` with `ResponsiveContainer`
- Props: `data` (array of `{quarter, value, yoy}`), `label`, `valueFormatter`
- Bars green/red based on Y/Y growth sign
- Y/Y % label rendered above each bar
- Used in: GrowthSection

### TrendSparkline.jsx
- Recharts `AreaChart`, 120x60px
- Props: `data` (array of numeric values), `color`, `label`
- Filled area, stroke colored by trend direction (green=up, red=down)
- Used in: DataStrip History tab

### MoatRatingBars.jsx
- Pure HTML/CSS, no Recharts
- Props: `ratings` (array of `{factor, rating, evidence}`)
- 4-step segmented bar per factor. Segments: light gray default, filled to rating level. Colors: NONE=gray, WEAK=red, MODERATE=amber, STRONG=green.
- Evidence text in muted font beside each bar.
- Used in: MoatAssessment

### ScenarioRangeBar.jsx
- Pure HTML/CSS with positioned markers
- Props: `worst`, `base`, `best`, `currentPrice`, `weightedTarget`
- Horizontal gradient bar (red→amber→green). Current price as labeled vertical line. Weighted target as diamond marker.
- Used in: VerdictScenarios

### PriceTargetBar.jsx
- Recharts horizontal `BarChart` or pure HTML
- Props: `sources` (array of `{name, low, mean, high}`), `currentPrice`
- Each source as horizontal range bar (low→high), mean marked. Current price as vertical reference line.
- Used in: ValuationTargets

---

## Error Handling & Edge Cases

**Missing data:**
- Each section checks its data slice for `null`/`undefined`. If missing: muted "Data unavailable" text. Never crashes, never shows broken charts.
- Recharts receives empty arrays gracefully (blank axes, no errors).
- Page is fully functional with fundamentals alone — StickyHeader + DataStrip Fundamentals tab + Valuation section all render.

**Loading states:**
- Initial load: full-page skeleton with pulsing placeholder cards matching section layout.
- AI in progress: `AiAnalyzeButton` spinner, locked narrative sections show pulsing border on lock icon.
- Individual enrichment failures: section shows "Data unavailable" — no error toast, no blocking.

**Staleness:**
- Only shown after AI has been run at least once.
- Click on staleness badge triggers re-analysis.
- Thresholds: <=3 days green "Fresh", 4-14 days amber, >14 days red.

**Responsiveness:**
- DataStrip tabs stack vertically on <768px.
- Metric grids: 4-column → 2-column on mobile.
- Memo sections: single column throughout, no breakpoint needed.
- StickyHeader: wraps badges to second line on narrow screens.

**Performance:**
- Single API call (`GET /api/deep-dive/:ticker`). No additional fetches.
- Recharts `ResponsiveContainer` with `debounce={200}` to prevent resize thrashing.
- `CollapsibleSection`: collapsed sections use conditional rendering (not `display:none`) — children not mounted when collapsed.

---

## Styling

Koyfin palette throughout (from `theme.js`):
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

No black backgrounds. No pure white backgrounds. Tailwind utility classes for layout, inline `style` for Koyfin colors (existing pattern). No CSS modules, no styled-components, no UI library.

---

## What Does NOT Change

- `App.jsx` routing — `/deep-dive/:ticker` route stays the same
- `api.js` — `getDeepDive(ticker)` and `triggerAiAnalysis(ticker)` calls unchanged
- `theme.js` — no changes
- `RegimeContext.jsx` — no changes
- Existing shared components: `CollapsibleSection`, `DcfCalculator`, `SensitivityMatrix`, `PeerTable`, `InsiderPanel`, `EntryGrid`, `AiAnalyzeButton`, `TechnicalPanel`, `SparklineGrid`, `AnalystBar`, `ResearchPanel` — all reused as-is

## What Gets Replaced

- `DeepDivePage.jsx` — current 320-line monolith replaced by ~100-line orchestrator + 10 section components + 2 header components

## New Dependency

- `recharts` — added to `frontend/package.json`
