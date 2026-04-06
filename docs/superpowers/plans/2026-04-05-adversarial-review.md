# Executive Summary

Overall severity: **High**.

The plan is trying to collapse two separate spec documents into one local app, but it does so by silently deleting major capabilities from both specs and replacing them with a thinner FastAPI + Vite shell that is not feature-complete enough to satisfy either document as written. The biggest failures are not code-level; they are architectural and workflow-level: the data layer assumes unreliable sources without a fallback strategy, the AI deep-dive workflow has no real invocation mechanism, and the frontend only implements a fraction of the spec surface while presenting placeholder pages as if they complete the product. This should **not ship as-is**; it needs a design rewrite or at minimum a major plan revision before implementation starts.

## 1. Architecture Choices

**Severity: High**

**Findings**

- The plan changes the screener/deep-dive spec from a mostly local script + JSX artifact model into a split FastAPI backend plus React/Vite frontend without justifying why the extra process boundary is worth it. The plan explicitly mandates “a FastAPI backend with a React (Vite) frontend” and “accessible at `http://localhost:5173`” in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L5) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L7). By contrast, Spec 1 describes a separate app that outputs JSON and interactive JSX artifacts, not a mandatory two-process web stack, in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L5), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L315), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L593).
- The plan adds operational complexity for a purely local single-user product. It requires FastAPI, uvicorn, Node/Vite, CORS, proxy config, and two long-running processes in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L179), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1750), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2435), and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2468). Nothing in either spec demonstrates that a single-process local app would be insufficient.
- The Vite proxy is a dev convenience, not an architecture. The plan hardcodes `"/api": "http://localhost:8000"` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1762). That works only in dev and only if the backend is already running on that port. The plan does not define production serving, packaging, or what happens outside the proxy path.
- The plan says “No external database — JSON file storage” in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L7), but the same choice becomes much more fragile once you introduce a separate backend process with multiple write paths and periodic scans. This is a design contradiction, not a code bug.
- The stack choice is also inconsistent with Spec 1’s `window.storage` fallback model for artifact environments in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L344) and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L490). The plan chooses backend JSON persistence everywhere, which is simpler for local code but abandons part of the stated deployment model.

**Recommendations**

- Pick one of two architectures deliberately:
  - A simpler **single-process Python app** with server-rendered UI or lightweight local UI if the goal is a local-only tool.
  - A real **client/server app** with a proper datastore, background jobs, and a defined packaging/deployment story.
- If keeping FastAPI + React, replace raw JSON files with SQLite immediately; otherwise the split architecture is unjustified.
- Treat the Vite proxy as dev-only and add an explicit production/packaging design. Right now there is none.

## 2. Spec Coverage Gaps

**Severity: Critical**

**Findings**

- Spec 1 requires **daily and weekly scan modes** in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L346), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L348), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L354). The plan implements only a single “Run Full Scan” flow and a `/latest` endpoint in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L908) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2036).
- Spec 1 requires screener **filters** and **Both/crossover tab** in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L321) and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L333). The plan frontend only has B1/B2 tab buttons in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2040).
- Spec 1 requires **sector distribution bar** in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L340). The plan lists a `SectorBar.jsx` in the file tree at [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L64) but never tasks or implements it.
- Spec 1 requires deep dive sections 1 through 8, including Whole Picture, Self-Review, Verdict, exit playbook, decision tree, and next review date in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L398), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L432), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L445). The plan deep dive page renders only fundamentals, reverse DCF, and a raw JSON dump of AI analysis in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2125) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2143).
- Spec 1 requires a **forward DCF with 3 scenarios**, **peer comparison**, and an interactive calculator in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L427), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L429), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L459). The plan computes DCF backend functions, but the frontend does not render those features.
- Spec 1 requires **5-year sparklines**, **SBC flag**, **accounting red flags**, **editable first impression**, and sourced bear/bull structure in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L406), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L412), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L415). None are tasked in the plan.
- Spec 2 requires the scanner to calculate **theta**, **earnings proximity warning**, and optionally wrap as an MCP server in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L202), [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L211), and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L371). The plan calculates theta but does not surface it in the UI, does not implement earnings proximity at all, and drops the MCP wrapper entirely in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1341) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2194).

**Recommendations**

- Build a traceability matrix before implementation: every explicit feature in both specs must map to a task.
- Separate “Phase 1 minimum viable screener” from “full spec-complete product.” Right now the plan pretends phase-1 placeholders satisfy phase-2/3 requirements.
- Do not start coding until the missing requirements are either added to the plan or explicitly descoped.

## 3. Data Layer Assumptions

**Severity: Critical**

**Findings**

- Spec 1 explicitly warns that `yfinance` is “Unofficial API, occasionally breaks” in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L70). The plan nevertheless makes `yfinance` the primary implementation path for fundamentals, history, options chains, regime, and screening in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L7), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L367), and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L430). There is no resilience layer beyond “catch exception and keep going.”
- Spec 1 positions FMP, Finnhub, stockanalysis.com, Alpha Vantage, and EdgarTools as primary/backup sources across the deep dive pipeline in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L370). The plan mentions those providers in the architecture line at [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L7) but implements none of them in the data service or deep dive endpoint.
- The fundamentals service simply forwards `.info.get(...)` values and leaves `earnings_date` as `None` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L373) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L404). That directly conflicts with both specs, which rely on earnings timing for warnings and options exclusion in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L299) and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L301).
- The plan’s screening logic treats missing data as “not filtered out” in some cases. Example: it only rejects debt-to-equity if `de is not None and de / 100 > ...` and only rejects forward P/E if `fpe is not None and fpe > ...` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L776). That means missing leverage and valuation data can pass hard gates. That is a design flaw for a screening system.
- The S&P 500 universe is sourced from a live Wikipedia scrape using `pd.read_html(url)` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L332). That is fragile by construction. The plan has no cached fallback, no checksum, and no test strategy beyond “AAPL/MSFT exist” in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L302).

**Recommendations**

- Introduce a **provider abstraction** with primary/backup sources exactly as Spec 1 defines.
- Treat `None` on hard-gate fields as **fail closed**, not pass-through.
- Cache the S&P 500 universe locally with a refresh task and fallback snapshot.
- Add data quality metadata to each response: source, timestamp, completeness flags, stale/fallback flags.

## 4. DCF Calculator Correctness

**Severity: High**

**Findings**

- The plan contains a suspicious recursion-avoidance branch: `_build_sensitivity` tries `calculate_dcf.__wrapped__` if present, otherwise `_simple_dcf` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1105). `calculate_dcf` is not decorated anywhere in the plan, so `__wrapped__` will not exist. This is not a live circular reference bug today; it is dead, misleading logic. It strongly suggests copied code that the author did not reason through.
- More importantly, the DCF implementation does **not enforce** Spec 1’s hard rules. Spec 1 says “WACC cannot be changed between scenarios” and “SBC adjustment is applied by default” in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L479). The plan’s sensitivity matrix explicitly varies WACC across rows in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1096), and the deep-dive endpoint feeds raw `free_cash_flow` from yfinance with no SBC adjustment in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1527).
- Spec 1 requires “Starting FCF (default: SBC-adjusted 3yr average from FMP)” in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L463). The plan uses a single point-in-time yfinance `freeCashflow` field and does not fetch 3-year averages or FMP cash-flow statements.
- The plan’s reverse DCF simplifies year 6-10 growth to `mid * 0.5` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1157). That assumption is not specified anywhere in either document; it is an invented valuation model parameter.
- The plan reduces `net_debt` to zero in the deep-dive route in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1536), despite Spec 1 requiring net debt from FMP balance sheet data in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L470). That materially distorts per-share valuation.

**Recommendations**

- Remove the fake `__wrapped__` branch. Either call `_simple_dcf` deliberately for sensitivity or split the pure calculation core into a non-recursive function.
- Decide whether the matrix is:
  - A true scenario matrix varying business assumptions only, per the hard rule, or
  - A classic WACC/growth sensitivity grid.
  Right now the spec and plan conflict.
- Do not implement DCF until you have SBC-adjusted 3-year FCF and net debt from a real financial statement source.

## 5. Options Scanner Math

**Severity: High**

**Findings**

- The Black-Scholes delta function itself is standard enough for a theoretical call delta in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1275), and Spec 2 explicitly permits calculating delta with Black-Scholes if Yahoo does not provide it in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L198). The problem is the **use case**: this filter is for contract selection in real trading decisions, and the plan treats a static theoretical delta as sufficient without validating chain-provided Greeks or market microstructure.
- Spec 2 says required move may use a “Simple approximation” but notes “More accurate: use Black-Scholes repricing at target stock price” in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L308). The plan chooses the crude approximation `required_move = (target_premium_4x - ask) / delta` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1343). That ignores gamma, vega, IV collapse/expansion, and time decay. It is acceptable as a rough ranking heuristic only; it is not reliable enough for “best risk/reward” sorting if presented as tradable truth.
- Spec 2 explicitly requires **earnings date proximity warning** in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L211) and a `check_earnings_proximity` function in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L301). The plan does not implement that warning at all.
- Spec 2 requires warnings for low liquidity and wide spread at tighter warning thresholds in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L213). The plan does add those warnings in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1347), but it silently omits the more important IV-crush warning.
- Spec 2 also requires regime-layer “VIX tax” logic in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L459). The plan only returns a narrative note string in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L601). No actual calculation exists.

**Recommendations**

- Label `required_move_pct` explicitly as an approximation if kept.
- For ranking, prefer repricing the option at target stock prices with remaining time and assumed IV bands.
- Add an earnings-date exclusion/warning before surfacing any contract.
- Add a regime-aware premium sanity check instead of a purely static $7 cap.

## 6. Frontend Completeness

**Severity: Critical**

**Findings**

- The plan itself calls the pages “minimal placeholder[s] that we'll flesh out in subsequent tasks” in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1957), but there are **no subsequent tasks**. Task 8 is the last UI task before integration and startup.
- The screener page is missing Spec 1’s required filters, Both tab, sector distribution bar, scan timestamp header, and actual watchlist save action from [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L321), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L333), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L342). In the plan UI, the `+ Watch` button has no handler in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2077).
- The deep-dive page is not a usable dashboard; it is a ticker form plus quantitative dump plus raw JSON blob. That does not satisfy the required 8-section structure in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L398).
- The options page omits theta, 3x target, P&L scenarios, earnings risk, and regime context, despite Spec 2 requiring those decision aids in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L202), [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L398), and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L423).
- The positions page is display-only. Spec 2’s optional tracker still defines add/list/check/close/summary flows with P&L summary in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L711) and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L716). The plan UI exposes none of that.

**Recommendations**

- Stop calling the UI complete. It is not.
- Add a second frontend phase with explicit tasks for each missing workflow.
- Define the minimum usable experience per page before writing code; otherwise the team will discover half the product after the backend is already shaped wrong.

## 7. Claude Code Integration

**Severity: Critical**

**Findings**

- The plan claims the user will say “deep dive ADBE” and Claude Code will “use the Value Investing MCP tools + the backend API” and “POST the analysis” to localhost in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2520) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2524). There is no mechanism in the plan that teaches Claude Code to do that.
- `CLAUDE.md` lists Value Investing MCP tools and app context in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L209), but it does not define a callable command, script, MCP tool, or HTTP client wrapper that actually posts results.
- The backend route exists at `/api/deep-dive/{ticker}` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1548), but the plan relies on Claude inferring localhost availability and payload shape from prose. That is not a workflow; that is wishful thinking.
- Spec 1 talks about interactive JSX artifacts and MCP-backed deep dives in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L593), not “Claude will somehow POST into your local FastAPI.” The plan invents an integration contract without implementing any bridge.

**Recommendations**

- Add a real bridge:
  - A local CLI command like `python deep_dive_worker.py ADBE` that posts structured results.
  - Or a custom MCP tool/server that writes directly to the backend storage.
- Encode the POST contract in code, not in `CLAUDE.md` prose.
- If Claude Code is not guaranteed to have network access to localhost in the target environment, do not architect around that assumption.

## 8. Missing From Specs

**Severity: Critical**

**Findings**

- Spec 1 explicitly says “For your system, you want all three” TradingView MCP servers and later provides an updated config with 8 MCP servers in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L692) and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L857). The plan does not include TradingView MCP installation or configuration tasks anywhere.
- Spec 1 requires EdgarTools/13F/insider data for Whole Picture and smart money analysis in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L386) and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L434). The plan mentions EDGAR in architecture prose at [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L7) but never tasks that integration.
- Spec 1 requires **sector distribution bar** in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L340). The plan does not implement it.
- Spec 1 requires **daily vs weekly scan modes** in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L346). The plan omits them.
- Spec 2 requires **earnings proximity warnings on options** in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L211) and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L301). The plan omits them.
- Spec 2 requires **position P&L tracking** via `positions.py summary` in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L716). The plan stores positions and shows open/closed rows, but there is no P&L model or summary computation in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1466) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2293).

**Recommendations**

- Add explicit tasks for TradingView MCP integration, EdgarTools/13F/Form 4 ingestion, daily/weekly workflows, options earnings warnings, and P&L summaries.
- If those features are intentionally deferred, mark them as deferred. Right now the plan claims spec alignment it does not have.

## 9. Deployment / DX Concerns

**Severity: High**

**Findings**

- The plan assumes a non-developer user will create a Python venv, install Python deps, initialize Node/Vite, run npm installs, and keep two processes alive in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L259), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1714), and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2435).
- The startup script helps, but it still presumes `.venv` exists and frontend dependencies are installed in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2474) and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2480). There is no bootstrap, dependency check, or friendly failure mode.
- Spec 1 already has a long MCP/API setup burden for FMP, Alpha Vantage, Finnhub, EdgarTools, and TradingView servers in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L183) and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L626). The plan adds another layer of local webapp complexity instead of reducing it.
- The claimed stack includes “Python 3.14” in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L9), while Spec 2 explicitly mentions “requires Python 3.12+” for `mcp-optionsflow` in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L30). That may be compatible, but the plan does not validate dependency support. It is a hypothetical compatibility risk.

**Recommendations**

- If this is for one local user, package it as one command or one app bundle.
- Add a bootstrap script that verifies Python, Node, env vars, ports, and dependency installation.
- Prefer reducing moving parts over documenting them.

## 10. What Could Go Wrong in Production

**Severity: Critical**

**Findings**

- **Rate limiting / source breakage:** Spec 1 documents rate limits and source fragility for FMP, Alpha Vantage, Finnhub, and yfinance in [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L70), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L116), [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L140), and [STOCK-SCREENER-DEEPDIVE-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/STOCK-SCREENER-DEEPDIVE-BUILD.md#L156). The plan has no rate-limiter, retry policy, cache invalidation policy, or provider failover.
- **Stale data:** The screener saves timestamped JSON snapshots in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L913), but the frontend simply loads `/latest` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L2020). There is no freshness policy, stale banner, TTL, or scheduled refresh model.
- **Missing API keys:** The plan defines env vars for FMP/Finnhub/Alpha Vantage in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L132) but never uses them in implementation tasks. The product will appear to support richer data than it actually can.
- **JSON corruption / concurrent writes:** Watchlist, positions, deep dives, and scans are written with direct `write_text(json.dumps(...))` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L915), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1553), [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1583), and [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1632). There is no atomic write, no lock, no backup, no schema migration, no recovery path.
- **ID collisions / race conditions:** Position IDs are assigned as `len(data) + 1` in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L1649). Two concurrent writes can create duplicate IDs. Even a single corrupted file breaks the counter.
- **Silent degradation:** `scan_sp500()` catches exceptions per ticker and appends them to an `errors` list in [2026-04-05-contrarian-investing-platform.md](/Users/sbakshi/Documents/Stocks%20Sucess/docs/superpowers/plans/2026-04-05-contrarian-investing-platform.md#L874). The frontend does not surface those errors anywhere in the screener page. You can get a partial scan and not know it.
- **Regime correctness drift:** Spec 2 requires market breadth and VIX tax logic in [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L433) and [CONTRARIAN-OPTIONS-SYSTEM-BUILD.md](/Users/sbakshi/Documents/Stocks%20Sucess/CONTRARIAN-OPTIONS-SYSTEM-BUILD.md#L461). The plan omits both, so production decisions are based on an intentionally incomplete Gate 0.

**Recommendations**

- Replace JSON stores with SQLite plus WAL mode before writing any app code.
- Add atomic writes, backup snapshots, and explicit stale/error states if JSON is kept temporarily.
- Add provider health status and freshness indicators to the UI.
- Fail visibly when required datasets are missing or degraded; do not quietly continue with partial truth.

# Final Verdict

**Redesign**, not ship-as-is.

If you want the fastest path to something usable, revise the scope down to a **single-user local app with one process and SQLite**, then add explicit provider fallbacks and a real Claude bridge. If you want the full cross-spec product, the current plan is too incomplete and too architecturally soft to implement safely; it needs a rewritten plan with requirement traceability first.
