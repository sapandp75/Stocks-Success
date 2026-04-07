# Gap Analysis: Contrarian Investing Platform
**Date:** 2026-04-06

## Spec Documents Audited
1. `CONTRARIAN-OPTIONS-SYSTEM-BUILD.md` (Options system)
2. `STOCK-SCREENER-DEEPDIVE-BUILD.md` (Screener + Deep Dive)
3. `2026-04-06-platform-enrichment-design.md` (Enrichment tier)
4. `2026-04-06-research-intelligence-layer.md` (Research layer)

## Adversarial Review Status
- 10 CRITICAL issues identified, 8 fixed, 1 partial, 1 remaining
- 18 HIGH issues identified, 13 fixed, 2 partial, 3 remaining

---

## MAJOR GAPS (7)

### 1. No Standalone CLI Scripts
**Spec:** Phase 1-3 of Options Build spec calls for `market_regime.py` and `contrarian_options_scanner.py` as standalone Python CLI tools runnable from terminal.
**Built:** Web API endpoints only (`/api/regime`, `/api/options/scan`). No CLI entry points.
**Impact:** Cannot run quick regime check or options scan from terminal without the full web stack running. The spec envisioned these as lightweight CLI tools for daily workflow.

### 2. SEC EDGAR Integration Missing
**Spec:** EdgarTools for SEC material events, 10-Q/10-K filings, insider data from EDGAR. Listed as a data source in both the Screener spec and Research Intelligence Layer.
**Built:** `edgartools` is in requirements.txt but never imported or used anywhere. The `providers.py` enum references `"edgar"` as a source but no service calls it.
**Impact:** Deep dive "Whole Picture" section lacks SEC filing data. Research context missing material events.

### 3. Phase 4 Workflow Automation Not Built
**Spec:** Detailed daily and weekly automated workflows:
- Daily: regime check -> position target check -> scan if DEPLOY/CAUTIOUS
- Weekly: regime -> TradingView RSI<30 scan -> options scan on watchlist -> Reddit sentiment
- Entry workflow: 6-gate verification before any trade
- Exit workflow: 4 exit rules (half at 3x, rest at 4x, 21 DTE time stop, regime-triggered close)
**Built:** Individual endpoints exist but no orchestration, no automated scheduling, no enforced workflow sequence.
**Impact:** The system provides tools but doesn't enforce the disciplined workflow that the spec was designed around.

### 4. Exit Rules Not Enforced in Position Tracker
**Spec:** Positions must track `target_3x` and `target_4x` with specific exit rules: half at 3x, rest at 4x, sell if <21 DTE and below 2x, close on regime change to DEFENSIVE/CASH.
**Built:** Positions store `target_fair_value` but no `target_3x`/`target_4x`. No automatic exit alerts. No DTE-based time stop. No regime-triggered position closure alerts.
**Impact:** The core risk management automation for options is absent. User must manually track all exit triggers.

### 5. Deep Dive "Whole Picture" Section Incomplete
**Spec:** Section 6 requires: smart money positioning (13F data with fund type context), management quality + compensation structure, customer/product evidence, PE/strategic acquirer floor.
**Built:** Gemini prompt asks for these but the context fed to Gemini lacks 13F data (no SEC EDGAR), management compensation data, and acquirer analysis data. The AI must hallucinate or skip these.
**Impact:** The highest-value analytical section relies on data that isn't provided, degrading analysis quality.

### 6. Deep Dive "Next Review Date" Missing
**Spec:** Verdict section must include a next review date.
**Built:** Not in the Gemini prompt template or the deep dive payload schema.
**Impact:** No systematic follow-up scheduling for watched stocks.

### 7. Peer Comparison Non-Deterministic (CRIT-B5 Unfixed)
**Spec:** Peer comparison should be reliable and reproducible.
**Built:** `random.shuffle(candidates)` in `peers.py` means two calls for the same ticker return different peers on cache miss. Up to 60 sequential yfinance calls.
**Impact:** Deep dive peer analysis is inconsistent. Same stock analyzed twice may show different peers and different conclusions.

---

## MODERATE GAPS (10)

### 1. FCF Yield Not Filterable (Only Sortable)
**Spec:** FilterBar should have FCF yield filter with ranges (Any / 5%+ / 8%+).
**Built:** FCF yield is a sort option but not a range filter in the FilterBar dropdown.
**Impact:** Users can sort by FCF yield but can't filter to only see high-FCF-yield stocks.

### 2. Bear Case Separation Fragile (HIGH-B2)
**Spec:** Deep dive must split bear case into "Bear on Stock" vs "Bear on Business" as separate sections.
**Built:** Gemini generates `bear_case_stock` and `bear_case_business`, but the save/display logic falls back to the same value if either is missing: `result.get("bear_case_stock") or result.get("bear_case")`.
**Impact:** If Gemini returns a single `bear_case` field, both stock and business risk show identical text.

### 3. Decision Tree Missing from Verdict
**Spec:** Verdict section should include a decision tree (if catalyst beats -> X, if misses -> Y).
**Built:** Entry grid and exit playbook exist, but no structured decision tree with conditional branches.
**Impact:** Reduces the actionability of the verdict for scenario planning.

### 4. Screener Silent Catch Block (CRIT-F1 Residual)
**Spec/Review:** All errors should surface to user.
**Built:** ScreenerPage line 90 still has `.catch(() => { setInitialLoading(false) })` -- swallows errors silently.
**Impact:** If initial screener data load fails, user sees no error message, just an empty screen.

### 5. Finnhub Earnings Transcripts -- Limited Implementation
**Spec:** Research context should include Finnhub earnings call transcripts.
**Built:** `transcripts.py` exists with a fallback function, but the primary transcript fetch may fail silently. Transcript content is title + summary only, not full transcript text.
**Impact:** Deep dive research context may lack earnings call insights.

### 6. Substack Newsletter Parsing Scope
**Spec:** 4 curated Substack value investing newsletters parsed for ticker mentions.
**Built:** Config references Substack feeds, but RSS parsing of Substack is notoriously unreliable (many newsletters block RSS or use partial feeds).
**Impact:** Research context from newsletters may be consistently empty.

### 7. "What Would Make Me Wrong" -- No Structured Extraction
**Spec:** Self-review section must include explicit "What would make me wrong" list (3-5 conditions).
**Built:** Gemini prompt requests this but there's no structured field or validation. It may appear as prose or be omitted.
**Impact:** The key contrarian discipline check may not render consistently.

### 8. Accounting Red Flags Panel Missing
**Spec:** Data Snapshot (Section 1) should include an accounting red flags panel.
**Built:** SBC > 10% flag exists, but no dedicated accounting red flags panel (e.g., receivables growing faster than revenue, off-balance-sheet items, audit opinions).
**Impact:** Financial due diligence weaker than specified.

### 9. TradingView MCP Integration -- Partial
**Spec:** 4 TradingView MCP servers (screener, indicators, advanced/Reddit, chart). Bridge should fetch TV data.
**Built:** Bridge has `--tv` flag using `tradingview-ta` library (direct, not MCP). MCP servers configured in `.mcp.json` but only usable in Claude Code sessions, not by the web app.
**Impact:** Web app cannot access TradingView data. Only Claude Code sessions can.

### 10. No Automated Staleness Warning for Deep Dives
**Spec:** Watchlist stores `last_deep_dive` date to track freshness.
**Built:** Field exists in DB but no UI indicator showing "deep dive is X weeks old" or prompting refresh.
**Impact:** Stale analysis may be relied upon without awareness.

---

## MINOR GAPS (8)

### 1. Position Tracker Uses SQLite Instead of JSON File
**Spec:** Positions persist in `positions.json`, portable, no database required.
**Built:** SQLite `positions` table. Better for the web app but not portable as a standalone file.
**Impact:** Minor -- SQLite is superior for the web context. Standalone portability lost.

### 2. DCF Phase 2 Growth Hardcoded
**Spec:** DCF parameters should be configurable.
**Built:** Phase 2 growth = `min(g1 * 0.6, 0.12)` -- hardcoded but documented and reasonable.
**Impact:** Power users can't adjust growth decay assumptions.

### 3. Macro Context Badges on Regime Page
**Spec:** Research Intelligence Layer calls for "macro context badges" on regime page.
**Built:** Regime page has SPY/QQQ direction cards, VIX, breadth gauge, and earnings calendar. No explicit "macro context badges" as a separate component.
**Impact:** Cosmetic -- the information is present, just not badged separately.

### 4. Short Interest % Display
**Spec:** StockCard should show short interest %.
**Built:** Warning flag triggers at >10% but the actual short interest % value may not display on the card.
**Impact:** Users see the warning but not the exact number.

### 5. Screener Scan Timestamp Not Prominent
**Spec:** Screener should show scan timestamp in header.
**Built:** Latest scan data includes timestamp but display prominence varies.
**Impact:** Minor UX -- users may not immediately see when data was last refreshed.

### 6. Conviction Level Not Overridable on Deep Dive
**Spec:** Conviction should be settable per watchlist entry AND per deep dive.
**Built:** Watchlist has conviction field. Gemini generates conviction in deep dive. But there's no explicit UI to override AI-generated conviction.
**Impact:** Minor -- user can edit watchlist conviction separately.

### 7. HIGH SBC Warning Flag Scope
**Spec:** `SBC > 10% of revenue -> "HIGH SBC" flag` in screener.
**Built:** SBC check exists in deep dive (FCF adjustment) but not as a screener warning flag. Screener has 9 other flags.
**Impact:** Low -- SBC is caught during deep dive, just not flagged at screener level.

### 8. No --json Flag on Regime Check
**Spec:** Regime script should support `--json` flag for machine-readable output.
**Built:** Web API returns JSON by default. No standalone CLI script exists.
**Impact:** Negligible -- API is inherently JSON.

---

## Summary Scorecard

| Category | Count | Key Themes |
|----------|-------|------------|
| **MAJOR** | 7 | No CLI tools, no SEC EDGAR, no workflow automation, no exit rule enforcement, incomplete Whole Picture data, no next review date, non-deterministic peers |
| **MODERATE** | 10 | FCF filter missing, bear case fragile, no decision tree, silent catch, transcript limits, Substack reliability, no red flags panel, TV only via Claude, no staleness UI |
| **MINOR** | 8 | SQLite vs JSON, hardcoded DCF decay, macro badges, short interest display, SBC flag scope |

## Adversarial Review Residuals

| Issue | Status |
|-------|--------|
| CRIT-B1: Ticker validation | FIXED |
| CRIT-B2: DB connection leaks | FIXED |
| CRIT-B3: Rate limiter thread safety | FIXED |
| CRIT-B4: Blocking scan | FIXED |
| CRIT-B5: Non-deterministic peers | UNFIXED |
| CRIT-B6: SQLite busy_timeout | FIXED |
| CRIT-F1: Silent catch blocks | 1 REMAINING (ScreenerPage) |
| CRIT-F2: Blocking GET scan | FIXED |
| CRIT-F3: window.prompt() | FIXED |
| CRIT-F4: URL encoding | FIXED |

## Overall Assessment

The **core platform architecture is solid** -- 6 pages, 7 routers, 16 services, 27 components, 13 test files. The screener gates, DCF calculator, regime filter, options scanner, and Gemini integration all work. ~90% of adversarial review critical issues were fixed.

The **major gaps cluster around two themes**:
1. **Workflow discipline** -- The system provides tools but doesn't enforce the contrarian workflow (daily/weekly sequences, exit rules, position limits based on regime). The spec's core value proposition was disciplined process, not just data display.
2. **Data completeness** -- SEC EDGAR, 13F filings, and management compensation data are specified but not connected, leaving the "Whole Picture" section under-informed.
