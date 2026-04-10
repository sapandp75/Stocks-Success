# Deep Dive Frontend V2 — Design Spec (Revised)

**Date:** 2026-04-08 | **Revised:** 2026-04-10
**Scope:** Task 14 from Deep Dive V2 plan — rebuild `DeepDivePage.jsx` into a contrarian decision tool with expanded data visualizations.
**Depends on:** Backend Tasks 1-13 (expanded GET endpoint delivering gates, quarterly, growth_metrics, forward_estimates, external_targets, fund_flow, staleness_days).
**Incorporates:** All findings from adversarial review (2026-04-08).

---

## Revision Summary

| Finding | Resolution |
|---------|------------|
| CRITICAL-1: Section order weakens contrarian discipline | Restored CLAUDE.md 8-section core flow. Growth/Moat/O&T/Scenarios moved to appendices. |
| CRITICAL-2: VerdictScenarios overloaded | Split into Verdict & Action Plan (core §8) + Scenarios (appendix). |
| HIGH-1: StickyHeader too dense | Reduced to ticker + price + conviction + AI action. Gates/staleness/earnings moved to Analysis Status block. |
| HIGH-2: DataStrip auto-collapse is bad UX | Removed. Collapse is user-controlled only. |
| HIGH-3: AI sections lack provenance | Added `AiProvenance` component — all AI-shaped sections carry visible metadata. |
| HIGH-4: Missing-data handling too passive | Severity-based: critical/important/optional. Critical gaps degrade memo trust state. |
| HIGH-5: No unified trust state | Added `AnalysisStatus` block below StickyHeader — freshness, completeness, critical gaps at a glance. |
| MEDIUM-1: "Fully functional with fundamentals" too broad | Corrected: renderable but trust-reduced, critical gaps flagged. |
| MEDIUM-2: Components assumed reusable as-is | Explicitly: logic reusable, presentation may need adaptation. |
| MEDIUM-3: Company name from wrong field | Fixed to `fundamentals.name`. |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Page structure | Hybrid: data dashboard header + 8 core sections + 4 appendices | Contrarian decision flow preserved; supporting analysis accessible but subordinate |
| Section order | CLAUDE.md canonical: Data Snapshot → First Impression → Bear → Bull → Valuation → Whole Picture → Self-Review → Verdict | Bear case FIRST enforces contrarian discipline — this is a decision tool, not a research memo |
| Chart library | Recharts (~45KB gzip) | V2 needs bar charts, line charts, range bars — hand-rolling is brittle and slow |
| Data strip density | Two-tier: sticky header + manually collapsible tabbed panels | Ticker/price always visible; data accessible but not overwhelming |
| Scroll behavior | Sticky tier 1, user-controlled tier 2 | No auto-collapse — page must feel stable and predictable |
| Pre-AI behavior | Show data panels, lock pure-narrative sections | Data before opinion; matches contrarian methodology |
| AI provenance | Visible metadata on all AI-structured sections | Prevents false authority from polished structure |
| Missing data | Severity-based (critical/important/optional) | Critical gaps degrade memo trust — quiet degradation is dangerous for financial decisions |
| AI trigger | Manual (click "Analyze" button) | Not auto-generated on page load |
| Component architecture | Section-per-file | Each component <150 lines, independently testable, easy to expand |
| Component reuse | Logic reusable, presentation may need adaptation | New information architecture may require density/labeling changes |

---

## Architecture

### Page Structure

The page has three tiers followed by two zones:

```
┌─────────────────────────────────────────────┐
│  TIER 1: StickyHeader (always pinned)       │  ticker, price, conviction, AI action
├─────────────────────────────────────────────┤
│  TIER 2: AnalysisStatus                     │  freshness, completeness, critical gaps
├─────────────────────────────────────────────┤
│  TIER 3: DataStrip (manually collapsible)   │  Fundamentals | Technicals | History tabs
├─────────────────────────────────────────────┤
│                                             │
│  CORE FLOW (8 sections — contrarian order)  │
│  §1 Data Snapshot                           │
│  §2 First Impression                        │
│  §3 Bear Case (FIRST)                       │
│  §4 Bull Case (rebuttal + upside)           │
│  §5 Valuation (reverse DCF first)           │
│  §6 Whole Picture + Smart Money             │
│  §7 Self-Review                             │
│  §8 Verdict & Action Plan                   │
│                                             │
├─────────────────────────────────────────────┤
│  APPENDICES (supporting analysis)           │
│  A. Growth & Forward Estimates              │
│  B. Moat Assessment                         │
│  C. Opportunities & Threats                 │
│  D. Scenarios                               │
│                                             │
└─────────────────────────────────────────────┘
```

### Data Flow

```
GET /api/deep-dive/:ticker
        │
        ▼
  DeepDivePage.jsx (orchestrator)
        │
        ├── StickyHeader ← fundamentals, ai_analysis.conviction, ai_analysis.verdict
        ├── AnalysisStatus ← staleness_days, gates, data_quality, ai_analysis (existence check)
        ├── DataStrip ← fundamentals, technicals, financial_history, quarterly, growth_metrics
        │
        ├── CORE FLOW (8 × CollapsibleSection)
        │   ├── DataSnapshot ← fundamentals, gates, data_quality
        │   ├── FirstImpression ← ai_analysis.first_impression
        │   ├── BearCase ← ai_analysis.bear_case_stock, ai_analysis.bear_case_business
        │   ├── BullCase ← ai_analysis.bull_case_rebuttal, ai_analysis.bull_case_upside
        │   ├── Valuation ← reverse_dcf, forward_dcf, sensitivity_matrix, external_targets, peers, analyst, ai_analysis.valuation
        │   ├── WholePicture ← fund_flow, insider_activity, institutional, ai_analysis.whole_picture, ai_analysis.smart_money
        │   ├── SelfReview ← ai_analysis.self_review
        │   └── VerdictAction ← ai_analysis.verdict, ai_analysis.conviction, ai_analysis.entry_grid, ai_analysis.exit_playbook, ai_analysis.next_review_date
        │
        └── APPENDICES (4 × CollapsibleSection)
            ├── GrowthEstimates ← quarterly, growth_metrics, forward_estimates, reverse_dcf, ai_analysis.growth
            ├── MoatAssessment ← ai_analysis.moat_structured
            ├── OpportunitiesThreats ← ai_analysis.opportunities, ai_analysis.threats
            └── Scenarios ← ai_analysis.scenarios
```

Single API call. No prop drilling beyond one level — each section receives only its data slice.

### File Structure

```
frontend/src/
├── pages/
│   └── DeepDivePage.jsx              (~110 lines, orchestrator)
├── components/
│   ├── deep-dive/
│   │   ├── StickyHeader.jsx          (~50 lines)
│   │   ├── AnalysisStatus.jsx        (~70 lines)
│   │   ├── DataStrip.jsx             (~140 lines)
│   │   ├── AiProvenance.jsx          (~30 lines)
│   │   ├── MissingSeverity.jsx       (~40 lines)
│   │   └── sections/
│   │       ├── DataSnapshot.jsx           (~80 lines)
│   │       ├── FirstImpression.jsx        (~40 lines)
│   │       ├── BearCase.jsx               (~60 lines)
│   │       ├── BullCase.jsx               (~60 lines)
│   │       ├── Valuation.jsx              (~140 lines)
│   │       ├── WholePicture.jsx           (~100 lines)
│   │       ├── SelfReview.jsx             (~40 lines)
│   │       ├── VerdictAction.jsx          (~100 lines)
│   │       ├── GrowthEstimates.jsx        (~120 lines)
│   │       ├── MoatAssessment.jsx         (~80 lines)
│   │       ├── OpportunitiesThreats.jsx   (~70 lines)
│   │       └── Scenarios.jsx              (~80 lines)
│   └── charts/
│       ├── QuarterlyBarChart.jsx      (~50 lines)
│       ├── TrendSparkline.jsx         (~40 lines)
│       ├── MoatRatingBars.jsx         (~50 lines)
│       ├── ScenarioRangeBar.jsx       (~45 lines)
│       └── PriceTargetBar.jsx         (~45 lines)
```

**Total: ~1,490 lines across 20 new files** (avg ~75 lines/file).

**Existing components reused (logic reusable, presentation may need adaptation):** CollapsibleSection (add `locked` prop for lock icon + muted styling when AI not yet generated), DcfCalculator, SensitivityMatrix, PeerTable, InsiderPanel, InstitutionalPanel, EntryGrid, AiAnalyzeButton, TechnicalPanel, SparklineGrid, AnalystBar, ResearchPanel.

**New dependency:** `recharts` added to `frontend/package.json`.

---

## Component Specifications

### DeepDivePage.jsx (Orchestrator)

**State:**
- `ticker` — from URL param (`useParams`) or search input
- `data` — full response from `GET /api/deep-dive/:ticker`
- `loading` / `error` — fetch status
- `dataStripOpen` — boolean, user-controlled collapse state (default: true)

**Behavior:**
- Single `useEffect` on ticker change triggers `getDeepDive(ticker)`
- No `IntersectionObserver` — DataStrip collapse is manual only
- Passes data slices as props to children — no context providers needed
- Search input + "Load" button navigates to `/deep-dive/${ticker}`
- Computes `memoTrust` object from data completeness (see Analysis Status section)

---

### StickyHeader.jsx (Tier 1)

Always pinned at top (`position: sticky`, `z-50`). Single row, ~48px height. White background, bottom border `#e2e4e8`.

Stripped to essentials only — this is a reading page, not a dashboard.

| Element | Source | Behavior |
|---------|--------|----------|
| Ticker + Company Name | ticker prop, `fundamentals.name` | Bold text. Left-aligned. |
| Current Price + Change | `fundamentals.price`, `fundamentals.price_change_pct` | Green/red based on direction. |
| Conviction State | `ai_analysis.conviction`, `ai_analysis.verdict` | Only shown if AI exists. Pill: BUY/HOLD/AVOID + HIGH/MODERATE/LOW. Color-coded. |
| AI Analyze Button | existing `AiAnalyzeButton` | Right-aligned. Spinner during analysis. `onComplete` re-fetches data. |

**What moved OUT of StickyHeader:** Gates badge → AnalysisStatus. Staleness → AnalysisStatus. Earnings proximity → AnalysisStatus. Drop from 52w high → DataSnapshot section.

**Responsive:** Ticker + price on first line, conviction pill wraps to second line on <768px.

---

### AnalysisStatus.jsx (Tier 2 — Trust Block)

Immediately below StickyHeader. Not sticky — scrolls with content. Compact horizontal strip, ~40px.

This is the top-level memo trust model. One glance tells the user whether this analysis is decision-grade.

**Layout:** Single row with spaced status pills.

| Element | Source | Display |
|---------|--------|---------|
| AI Status | `ai_analysis` existence | "AI Generated" green pill or "No AI Analysis" gray pill |
| Freshness | `staleness_days` | Hidden if no AI. "Fresh" green (<=3d), "X days old" amber (4-14d), "Stale: X days" red (>14d). Click triggers re-analysis. |
| Gates | `gates.passes_all` | "GATES PASS" green or "GATES FAIL" red pill. Hover tooltip: which gates pass/fail with values. |
| Completeness | computed from data slices | "Complete" green, "Partial — N gaps" amber, "Incomplete" red |
| Critical Gaps | computed | Only shown if critical sections missing. Red text: "Missing: valuation, peers" |
| Earnings | `fundamentals.earnings_date` | Only shown if within 14 days. Amber pill: "Earnings in X days" |

**Completeness computation:** Orchestrator checks each section's data availability and classifies gaps by severity (see Missing Data section below).

---

### DataStrip.jsx (Tier 3)

Three tabs: **Fundamentals | Technicals | History**

**Collapsed state:** 36px strip showing tab labels + chevron expand button. Clicking a tab expands + switches.

**Expanded state:** ~280px height.

**Collapse is user-controlled only.** Toggle via chevron button. No `IntersectionObserver`, no auto-collapse on scroll. The page must feel stable and predictable.

**Fundamentals tab — 4-row metric grid:**

| Row | Metrics |
|-----|---------|
| Valuation | Forward P/E, Trailing P/E, PEG, EV/EBIT, FCF Yield |
| Profitability | Gross Margin, Operating Margin, Profit Margin, ROE, ROIC |
| Health | D/E, Free Cash Flow, Piotroski F-Score, Accruals Ratio, Buyback Yield |
| Size | Market Cap, Enterprise Value, Avg Volume, Short Interest, Short Ratio |

Each cell: label above, value below. Color thresholds from screener rules (operating margin green >20%, D/E red >5x, etc.).

**Technicals tab:** Reuses existing `TechnicalPanel` + `SparklineGrid` (may need density adaptation for strip context).

**History tab:** 4-year trends using Recharts `AreaChart` (120x60px each) — revenue, EPS, FCF, operating margin. Trend-colored fill.

---

### AiProvenance.jsx (Shared Component)

Small metadata strip rendered at the top of every AI-structured section. Prevents polished visuals from creating false authority.

**Props:** `type` (string), `sourceBacked` (boolean), `confidence` (string: "low"/"medium"/"high", optional)

**Display:**
```
┌──────────────────────────────────────────────────────────────┐
│  🤖 AI synthesis  ·  Source-backed  ·  Confidence: medium    │
└──────────────────────────────────────────────────────────────┘
```

- `type`: "AI synthesis" (default) or "AI + data-derived"
- `sourceBacked`: "Source-backed" green or "Not source-backed" amber
- `confidence`: shown when available. Low=red, medium=amber, high=green.
- Muted text, small font (11px), left-aligned. Background `#f7f8fa`.

**Used in:** MoatAssessment, OpportunitiesThreats, Scenarios, BearCase, BullCase, SelfReview, WholePicture (AI narrative portions).

---

### MissingSeverity.jsx (Shared Component)

Renders missing-data warnings at appropriate severity levels. Replaces the universal muted "Data unavailable" pattern.

**Props:** `severity` (string: "critical"/"important"/"optional"), `label` (string)

**Display by severity:**
- `critical`: amber warning banner, full-width, icon + text. Example: "⚠ Valuation data unavailable — decision quality reduced"
- `important`: inline warning card with amber left border. Example: "Peer comparison unavailable"
- `optional`: muted gray text. Example: "Smart money data unavailable"

---

## Core Flow Sections (1-8)

All sections use the existing `CollapsibleSection` component (white card, 3px left accent border, numbered badge, title, toggle arrow). The `locked` prop (new) shows a lock icon + muted styling when AI has not yet been generated.

### Section 1: DataSnapshot.jsx
- **Accent:** blue `#3b82f6`
- **Number:** 1
- **Default:** always open
- **Missing severity:** critical (fundamentals are the minimum viable page)
- **Content:**
  - Company identity: name, ticker, sector, industry (from `fundamentals.name`, `fundamentals.sector`, `fundamentals.industry`)
  - Data quality strip (source, completeness %, missing fields — from `data_quality`)
  - Gates pass/fail badges with actual vs threshold values (from `gates`)
  - Drop from 52-week high badge (from `fundamentals.drop_from_high`)
  - 18-metric grid (same as V1): price, mkt cap, fwd P/E, trail P/E, rev growth, op margin, gross margin, FCF, FCF 3yr avg, D/E, net debt, SBC, SBC adjusted flag, short %, drop from high, beta, ROE, div yield
  - Color thresholds from screener rules

### Section 2: FirstImpression.jsx
- **Accent:** indigo `#6366f1`
- **Number:** 2
- **Default:** open if AI exists; collapsed with lock icon if not
- **Missing severity:** optional (AI-only section)
- **Content:** AI first impression narrative. Pre-AI: locked placeholder with bridge command hint.
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={false}`

### Section 3: BearCase.jsx
- **Accent:** red `#e5484d`
- **Number:** 3
- **Default:** open if AI exists; collapsed with lock icon if not
- **Missing severity:** critical (bear case FIRST is non-negotiable for contrarian discipline)
- **Content:** Two columns — "Stock Risk" (left) and "Business Risk" (right). AI bullet points. Pre-AI: locked placeholder "Run AI analysis to generate bear case."
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium"`

### Section 4: BullCase.jsx
- **Accent:** green `#00a562`
- **Number:** 4
- **Default:** open if AI exists; collapsed with lock icon if not
- **Missing severity:** critical (bull case as rebuttal is core to the framework)
- **Content:** Two columns — "Rebuttal" (left, countering bear points) and "Upside Catalysts" (right). Pre-AI: locked placeholder.
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium"`

### Section 5: Valuation.jsx
- **Accent:** amber `#d97b0e`
- **Number:** 5
- **Default:** always open
- **Missing severity:** critical (valuation is decision-critical)
- **Content:**
  - Reverse DCF block — implied growth rate + interpretation (ALWAYS first per CLAUDE.md)
  - Forward DCF — 3-scenario grid (bear/base/bull): intrinsic value/share, terminal value %, margin of safety %
  - `DcfCalculator` — existing interactive component (WACC locked at 10%)
  - `SensitivityMatrix` — existing component
  - Price target comparison — `PriceTargetBar` showing Yahoo, Finviz, DCF base, current price on same axis
  - `PeerTable` — existing component
  - `AnalystBar` — existing component
  - AI valuation narrative when available
- **Provenance:** on AI narrative only: `AiProvenance type="AI + data-derived" sourceBacked={true}`

### Section 6: WholePicture.jsx
- **Accent:** purple `#8b5cf6`
- **Number:** 6
- **Default:** open if AI or smart money data exists
- **Missing severity:** important
- **Content:**
  - AI whole picture narrative (sector theme, management quality, customer evidence)
  - Fund flow summary — net buy/sell badge, new positions count, exits count (from `fund_flow`)
  - Top holders table — fund name, shares, % change Q/Q, type (index/value/growth/activist)
  - `InsiderPanel` — existing component
  - `InstitutionalPanel` — existing component
  - AI smart money interpretation when available
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={true}` on AI narrative portions

### Section 7: SelfReview.jsx
- **Accent:** yellow `#f59e0b`
- **Number:** 7
- **Default:** open if AI exists; collapsed with lock icon if not
- **Missing severity:** important (bias check is a core contrarian safeguard)
- **Content:** AI self-review — bias check vs first impression, gap check, pre-mortem, "what would make me wrong." Pre-AI: locked placeholder.
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={false} confidence="low"`

### Section 8: VerdictAction.jsx
- **Accent:** green `#00a562`
- **Number:** 8
- **Default:** open if AI exists; collapsed with lock icon if not
- **Missing severity:** critical (this is the decision output)
- **Content:**
  - Verdict badge — large BUY/HOLD/AVOID pill with conviction (HIGH/MODERATE/LOW)
  - `EntryGrid` — existing component (4 tranches)
  - Exit playbook — bullet list (profit target, stop loss, time stop, thesis-breaker)
  - Next review date badge
  - Memo trust summary — compact repeat of AnalysisStatus: "This verdict is based on [FRESH/STALE] [COMPLETE/PARTIAL] analysis"
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={true} confidence` from `ai_analysis.conviction`

**Why Verdict is separated from Scenarios:** The user's primary need at the end of a deep dive is "know what to do next" — not "view scenario graphics." Scenarios are supporting quantitative analysis, not the decision itself.

---

## Appendix Sections (A-D)

Appendices provide deeper supporting analysis. They are visually distinct from the core flow: labeled with letters (A-D) instead of numbers, and default collapsed. They feed into the core sections but do not interrupt the decision flow.

### Appendix A: GrowthEstimates.jsx
- **Accent:** cyan `#06b6d4`
- **Label:** A
- **Default:** collapsed
- **Missing severity:** important
- **Content:**
  - Quarterly revenue bar chart (`QuarterlyBarChart`) — last 8 quarters, Y/Y growth labels, green/red bars
  - EPS quarterly trend line chart
  - Forward estimates panel — 1yr/3yr/5yr EPS and revenue growth, beat rate streak badge
  - Implied vs Actual gap callout — "Market implies X% growth. Historical CAGR is Y%. Gap: Z%." Green if undervalued, red if optimistic.
  - AI growth narrative when available.
- **Provenance:** `AiProvenance type="AI + data-derived" sourceBacked={true}` on AI narrative

### Appendix B: MoatAssessment.jsx
- **Accent:** purple `#8b5cf6`
- **Label:** B
- **Default:** collapsed; expanded if AI moat data exists
- **Missing severity:** optional
- **Content:**
  - `MoatRatingBars` — 5 factors (Pricing Power, Switching Costs, Network Effects, Intangible Assets, Cost Advantage). Each as 4-step segmented bar (NONE→STRONG) with evidence text.
  - Overall moat badge (NONE/NARROW/WIDE)
  - Trend badge (STRENGTHENING/STABLE/ERODING) with arrow icon
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={false} confidence="low"`
- **Note:** Moat ratings look authoritative but are AI judgments with limited calibration. The provenance label and low confidence prevent false authority.

### Appendix C: OpportunitiesThreats.jsx
- **Accent:** teal `#14b8a6`
- **Label:** C
- **Default:** collapsed; expanded if AI O&T data exists
- **Missing severity:** optional
- **Content:** Two columns — "Opportunities" (revenue expansion, margin expansion, value unlock) and "Threats" (competition, regulation, disruption). AI bullets with quantified TAM/impact.
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={false} confidence="low"`

### Appendix D: Scenarios.jsx
- **Accent:** slate `#64748b`
- **Label:** D
- **Default:** collapsed; expanded if AI scenarios exist
- **Missing severity:** optional
- **Content:**
  - `ScenarioRangeBar` — worst→best horizontal bar, current price line, probability-weighted target diamond
  - Scenario table — 3 rows (worst/base/best), columns: revenue, margin, EPS, target price, probability, upside/downside %. Color-coded rows (red/amber/green).
- **Provenance:** `AiProvenance type="AI synthesis" sourceBacked={true} confidence="medium"`
- **Note:** Scenario probabilities should look like judgments, not calibrated forecasts. Use descriptive labels ("plausible"/"unlikely") alongside percentages.

---

## Shared Chart Components

### QuarterlyBarChart.jsx
- Recharts `BarChart` with `ResponsiveContainer`
- Props: `data` (array of `{quarter, value, yoy}`), `label`, `valueFormatter`
- Bars green/red based on Y/Y growth sign
- Y/Y % label rendered above each bar
- Used in: GrowthEstimates

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
- Used in: Scenarios

### PriceTargetBar.jsx
- Recharts horizontal `BarChart` or pure HTML
- Props: `sources` (array of `{name, low, mean, high}`), `currentPrice`
- Each source as horizontal range bar (low→high), mean marked. Current price as vertical reference line.
- Used in: Valuation

---

## Missing Data — Severity Model

Each section declares its missing-data severity. The orchestrator computes a `memoTrust` object that feeds `AnalysisStatus`.

| Severity | Sections | Behavior when missing |
|----------|----------|-----------------------|
| **critical** | DataSnapshot, BearCase, BullCase, Valuation, VerdictAction | Amber warning banner in section. Degrades memo trust to "Incomplete". AnalysisStatus shows red "Critical gaps" with list. |
| **important** | WholePicture, SelfReview, GrowthEstimates | Inline warning card with amber border. Degrades memo trust to "Partial" (if no critical gaps). |
| **optional** | FirstImpression, MoatAssessment, OpportunitiesThreats, Scenarios | Muted "Data unavailable" text. No effect on memo trust. |

**Trust state computation:**
```
if (any critical section has missing data) → "Incomplete" (red)
else if (any important section has missing data) → "Partial" (amber)
else → "Complete" (green)
```

**Page is renderable with fundamentals alone** — StickyHeader, DataStrip Fundamentals tab, and DataSnapshot all render. However, AnalysisStatus will show "Incomplete" with critical gaps flagged. This is correct behavior: the page works, but the user knows not to act on partial analysis.

---

## Loading States

- **Initial load:** Full-page skeleton with pulsing placeholder cards matching section layout.
- **AI in progress:** `AiAnalyzeButton` spinner, locked narrative sections show pulsing border on lock icon.
- **Individual enrichment failures:** Section shows `MissingSeverity` at appropriate level — no error toast, no blocking.

---

## Staleness

- Only shown in AnalysisStatus after AI has been run at least once.
- Click on staleness indicator triggers re-analysis.
- Thresholds: <=3 days green "Fresh", 4-14 days amber, >14 days red.

---

## Responsiveness

- DataStrip tabs stack vertically on <768px.
- Metric grids: 4-column → 2-column on mobile.
- Memo sections: single column throughout, no breakpoint needed.
- StickyHeader: wraps conviction pill to second line on narrow screens.

---

## Performance

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

## Existing Components (Logic Reusable, Presentation May Need Adaptation)

- `CollapsibleSection` — add `locked` prop for lock icon + muted styling. May need letter-label variant for appendices.
- `DcfCalculator` — logic unchanged; may need compact mode for V2 density
- `SensitivityMatrix` — likely reusable as-is
- `PeerTable` — likely reusable as-is
- `InsiderPanel` — likely reusable as-is
- `InstitutionalPanel` — likely reusable as-is
- `EntryGrid` — likely reusable as-is
- `AiAnalyzeButton` — reusable as-is
- `TechnicalPanel` — may need density adaptation for DataStrip context
- `SparklineGrid` — may need density adaptation for DataStrip context
- `AnalystBar` — likely reusable as-is
- `ResearchPanel` — available for future use, not in core V2 flow

## What Gets Replaced

- `DeepDivePage.jsx` — current 320-line monolith replaced by ~110-line orchestrator + 12 section components + 3 header/status components + 2 shared utility components

## New Dependencies

- `recharts` — added to `frontend/package.json`
