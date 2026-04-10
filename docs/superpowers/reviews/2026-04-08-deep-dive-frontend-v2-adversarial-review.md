# Adversarial Review — Deep Dive Frontend V2 Design

**Date:** 2026-04-08
**Scope:** Review of `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md`
**Purpose:** Stress-test the Deep Dive Frontend V2 design before implementation, focusing on decision quality, workflow discipline, UI risk, and analytical trust.

## Verdict

The V2 design spec is substantially better than a vague frontend todo list. It defines component boundaries, layout behavior, and interaction patterns clearly enough to implement. The problem is not lack of detail anymore. The problem is that the design is optimizing for analytical richness and polished memo presentation faster than it is optimizing for contrarian decision discipline.

The result is a design that is likely to look sophisticated and feel comprehensive, but still risks:
- burying the actual decision outputs
- overstating trust in structured AI sections
- degrading too quietly when important inputs are missing
- introducing too much sticky/intermediate UI behavior on a page meant for long-form reasoning

## Findings

### CRITICAL-1: The design still weakens the original contrarian workflow

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:13-21`
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:156-248`

**Problem**

The page is organized around a hybrid dashboard plus 10 memo sections:
- Gates/Business
- Key Fundamentals
- Growth
- Bear
- Bull
- Valuation
- Moat
- Opportunities/Threats
- Smart Money
- Verdict/Scenarios

That is analytically dense, but it no longer clearly enforces the original contrarian discipline:
- bear case first
- bull case as rebuttal
- self-review before action
- verdict as culmination

The design moves too much explanatory/expansion content ahead of action-quality judgment.

**Why it matters**

This product is not a research memo generator. It is a decision tool for a contrarian investor. If the UI stops enforcing decision order, it loses one of its highest-value behavioral advantages.

**Fix**

Reframe the section order around decision flow:

1. Header
2. Data Strip
3. Bear Case
4. Bull Case
5. Valuation
6. Whole Picture / Smart Money
7. Self-Review
8. Verdict & Action Plan

Supporting quantitative sections like growth, moat, and opportunities can still exist, but should feed into those core stages rather than dominate the reading flow.

---

### CRITICAL-2: Section 10 is overloaded and likely to bury actionability

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:241-248`

**Problem**

The `VerdictScenarios` section combines:
- scenario range bar
- scenario table
- verdict
- conviction
- entry grid
- exit playbook
- next review date

This is too much high-value content in one section. The eye will get pulled toward the more graphical scenario content while the operational items risk becoming secondary.

**Why it matters**

The primary user need at the end of a deep dive is not “view scenario graphics.” It is “know what to do next.”

**Fix**

Split Section 10 into:
- `Verdict & Action Plan`
- `Scenarios`

Pin verdict, conviction, entry grid, exit rules, and next review date together in a compact action card. Keep scenario content adjacent but separate.

---

### HIGH-1: StickyHeader is too dense for the amount of status it carries

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:84-103`

**Problem**

The sticky header includes:
- ticker + company
- price + change
- drop from 52-week high
- gates badge
- staleness
- earnings proximity
- AI Analyze button

That is too much for a 56px sticky band, especially when a second sticky layer exists below it.

**Why it matters**

Deep-dive pages are long reading surfaces. Excess sticky chrome steals space and increases cognitive noise.

**Fix**

Reduce sticky tier 1 to:
- ticker
- price
- conviction/verdict state
- AI action

Move gates, staleness, and earnings into a compact secondary status strip or an expandable status row.

---

### HIGH-2: The DataStrip interaction model is too clever for a reading-first page

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:107-131`

**Problem**

The design combines:
- sticky tier 2
- tabs
- collapsed vs expanded states
- auto-collapse on scroll
- `IntersectionObserver`

That is a lot of behavior for a page that should feel stable and inspectable.

**Why it matters**

Auto-collapsing UI often harms orientation. Users lose track of where key data went and the page feels like it is moving under them.

**Fix**

Make DataStrip collapse user-controlled only.

Keep:
- sticky tabs
- manual expand/collapse

Remove:
- automatic collapse on scroll

The page should be predictable, not smart.

---

### HIGH-3: Structured AI sections are presented with too much implied authority

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:224-248`

**Problem**

The moat panel, opportunities/threats panel, and scenario panel all convert AI output into clean, structured visual objects:
- factor ratings
- quantified threats/opportunities
- probability-weighted scenarios

The design does not require visible trust cues such as:
- AI-generated label
- source-backed label
- editable status
- confidence level

**Why it matters**

Polished structure creates false authority. A segmented moat bar looks much more reliable than the underlying model probably is.

**Fix**

Every AI-shaped section should carry visible metadata:
- `AI synthesis`
- `Source-backed` or `Not source-backed`
- `Editable`
- `Confidence: low/medium/high` when available

Also, avoid overly exact visuals for low-confidence outputs. For example, scenario probabilities should look like judgments, not like calibrated forecasts.

---

### HIGH-4: Missing-data handling is too passive for a financial decision tool

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:266-276`

**Problem**

The spec says missing sections should show muted “Data unavailable” text and individual enrichment failures should not block or show error toasts.

That is fine for low-value auxiliary widgets. It is not fine for high-value sections like:
- valuation targets
- peers
- smart money
- AI verdict

**Why it matters**

Quiet degradation encourages action on partial analysis.

**Fix**

Add severity-based missing-data handling:
- `critical`: warning banner
- `important`: inline warning card
- `optional`: muted unavailable state

Critical sections should degrade the memo’s trust state, not just their own card.

---

### HIGH-5: The spec lacks a unified trust/completeness state

**Where**
- entire design spec

**Problem**

The design handles staleness, loading, and missing-data locally, but it does not define a top-level memo trust model.

There is no visible summary of:
- AI generated or not
- stale or fresh
- complete or partial
- critical missing sections
- source conflicts

**Why it matters**

Users need one glance to know whether this memo is decision-grade or just partially rendered.

**Fix**

Add an `Analysis Trust` block in the sticky area or directly under it:

```text
Analysis Status: PARTIAL
Freshness: 9 days old
Critical gaps: scenarios missing, peers unavailable
AI memo: generated
```

This should be a first-class design element, not inferred from section fragments.

---

### MEDIUM-1: The “fully functional with fundamentals alone” claim is too broad

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:268-269`

**Problem**

The spec says the page is fully functional with fundamentals alone.

That is true only in the narrow sense that the page renders. It is not true in the sense that V2’s decision-support value is intact.

**Fix**

Replace that claim with:

`The page remains renderable with fundamentals alone, but analytical trust is reduced and critical sections must be flagged as partial.`

---

### MEDIUM-2: Existing components are unlikely to fit “as-is”

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:58-63`
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:300`

**Problem**

The spec assumes multiple components can be reused unchanged:
- `DcfCalculator`
- `SensitivityMatrix`
- `PeerTable`
- `InsiderPanel`
- `EntryGrid`
- `TechnicalPanel`
- others

That is optimistic. A new information architecture usually requires density, labeling, and state changes even if the core logic is reused.

**Fix**

Treat those components as:
- logic reusable
- presentation likely needs adaptation

The spec should explicitly allow light wrapper or presentation updates.

---

### MEDIUM-3: Header data contract contains a likely field mismatch

**Where**
- `docs/superpowers/specs/2026-04-08-deep-dive-frontend-v2-design.md:91`

**Problem**

The StickyHeader table says “Ticker + Company Name” comes from `fundamentals.business_summary`.

That is not a company name field.

**Fix**

Use a real company name field from fundamentals, for example:
- `fundamentals.name`

Use `business_summary` only as fallback descriptive text in Section 1.

## What the spec gets right

- It clearly defines component ownership and data flow.
- It chooses a sensible hybrid dashboard + memo direction rather than a pure memo wall.
- It avoids auto-generating AI on page load.
- It makes pre-AI behavior explicit and preserves data-first access.
- It identifies staleness and earnings proximity as top-level concerns.

## Recommended Spec Corrections

1. Reorder sections around contrarian decision flow, not memo completeness.
2. Split `VerdictScenarios` into separate action and scenario sections.
3. Simplify the sticky layers; remove auto-collapse from DataStrip.
4. Add a first-class `Analysis Trust` state.
5. Add severity-based missing-data treatment.
6. Add provenance and confidence labels to AI-shaped sections.
7. Correct the StickyHeader company-name data contract.
8. Allow shared components to be adapted rather than reused blindly.

## Recommended Target State

The page should ultimately feel like this:

- `Tier 1`: compact sticky identity + action controls
- `Tier 2`: manually collapsible data strip
- `Core flow`: Bear -> Bull -> Valuation -> Whole Picture -> Self-Review -> Verdict
- `Appendices`: Growth, Moat, Opportunities/Threats, Scenarios, raw supporting panels
- `Trust layer`: explicit freshness, completeness, AI/source status

That would preserve the strongest parts of the V2 design while keeping the product aligned with its real purpose: better investing decisions, not prettier research artifacts.
