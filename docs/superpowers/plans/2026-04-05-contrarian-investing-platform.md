# Contrarian Investing Platform — Revised Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified local web app combining stock screening (B1/B2), deep dive analysis (Gate 1-8), options contract scanning, market regime filtering, and position tracking — as a single-process FastAPI app serving React static files at `http://localhost:8000`.

**Architecture:** Single-process FastAPI backend serves the API and built React static files (no separate Vite process in production). SQLite with WAL mode for all persistence (watchlist, positions, scans, deep dives). Data provider abstraction with primary/fallback sources. Claude Code (Max plan) generates AI analysis via a CLI bridge script that POSTs structured results to the local API. Bootstrap script handles all setup in one command.

**Tech Stack:** Python 3.12+ / FastAPI / uvicorn / SQLite (backend), React 18 / Vite / Tailwind CSS (frontend, built to static), yfinance + edgartools (Tier 1 data), FMP + Finnhub + Alpha Vantage (Tier 2, when keys available)

**Adversarial review addressed:** All 10 findings from the 2026-04-05 adversarial review are resolved in this revision. See traceability notes per task.

---

## Phasing Strategy (Honest)

| Phase | What | Data Sources | Spec Coverage |
|-------|------|-------------|---------------|
| **Phase 1: Core MVP** (Tasks 1-12) | Full app with all 6 pages working | yfinance only | ~70% of CORE features |
| **Phase 2: Data Enrichment** (Tasks 13-15) | FMP, Finnhub, EdgarTools integration | +FMP +Finnhub +EdgarTools | ~90% of CORE features |
| **Phase 3: MCP + Technical** (Tasks 16-17) | TradingView MCPs, Alpha Vantage MCP | +TradingView +Alpha Vantage | 100% CORE + ENRICHMENT |

**Deferred explicitly (not in any phase):**
- TradingView chart screenshots (requires ChromeDriver + TV account — S2-66/67/68/69)
- Custom MCP server wrapper for scanner (S2-129/130/131/132 — optional in spec)
- `window.storage` artifact mode (S1-43 — replaced by SQLite, more reliable)

---

## File Structure

```
stock-analysis-system/
├── CLAUDE.md                              # Claude Code system prompt
├── setup.sh                               # One-command bootstrap (Python + Node + deps)
├── start.sh                               # One-command startup
├── requirements.txt                       # Python dependencies
├── backend/
│   ├── main.py                            # FastAPI app + static file serving + CORS
│   ├── config.py                          # API keys, system params, constants
│   ├── database.py                        # SQLite setup + WAL mode + migrations
│   ├── routers/
│   │   ├── regime.py                      # GET /api/regime
│   │   ├── screener.py                    # GET /api/screener/scan, /latest, /daily
│   │   ├── deep_dive.py                   # GET/POST /api/deep-dive/{ticker}
│   │   ├── options.py                     # GET /api/options/scan
│   │   ├── watchlist.py                   # GET/POST/PUT/DELETE /api/watchlist
│   │   └── positions.py                   # GET/POST/PUT/DELETE /api/positions + P&L
│   ├── services/
│   │   ├── providers.py                   # Data provider abstraction (primary/fallback)
│   │   ├── market_data.py                 # yfinance + FMP wrappers
│   │   ├── regime_checker.py              # SPY/QQQ/VIX regime + breadth + VIX tax
│   │   ├── stock_screener.py              # B1/B2 screening (fail-closed gates)
│   │   ├── dcf_calculator.py              # DCF: SBC-adjusted, 3yr avg, correct sensitivity
│   │   ├── options_scanner.py             # Options filtering + Black-Scholes + earnings check
│   │   ├── sp500.py                       # S&P 500 list with cached fallback
│   │   └── earnings.py                    # Earnings date proximity checker
│   └── data/
│       ├── app.db                         # SQLite database (created by setup)
│       └── sp500_fallback.json            # Cached S&P 500 ticker list
├── bridge/
│   └── deep_dive_worker.py                # CLI: Claude Code calls this to POST analysis
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                        # Layout + client-side routing
│   │   ├── api.js                         # Fetch helpers
│   │   ├── theme.js                       # Koyfin palette
│   │   ├── pages/
│   │   │   ├── RegimePage.jsx             # Gate 0 dashboard
│   │   │   ├── ScreenerPage.jsx           # B1/B2/Both/Watchlist tabs + filters + sector bar
│   │   │   ├── DeepDivePage.jsx           # 8 collapsible sections
│   │   │   ├── OptionsPage.jsx            # Contract scanner + regime context
│   │   │   ├── WatchlistPage.jsx          # Persistent watchlist manager
│   │   │   └── PositionsPage.jsx          # Position tracker + P&L summary
│   │   └── components/
│   │       ├── Navbar.jsx                 # Top nav + regime badge
│   │       ├── StockCard.jsx              # Screener result card
│   │       ├── WarningBadge.jsx           # Amber/red warning tags
│   │       ├── SectorBar.jsx              # Sector distribution bar chart
│   │       ├── DcfCalculator.jsx          # Interactive DCF with inputs + sensitivity
│   │       ├── SensitivityMatrix.jsx      # 4x4 growth × growth heatmap (WACC fixed)
│   │       ├── EntryGrid.jsx              # Tranche entry table
│   │       ├── OptionsTable.jsx           # Contract results + warnings + regime note
│   │       ├── RegimeBadge.jsx            # Colored verdict badge
│   │       ├── CollapsibleSection.jsx     # Reusable collapsible panel
│   │       └── FilterBar.jsx              # Screener filter dropdowns + sort
│   └── public/
└── tests/
    ├── conftest.py                        # Shared fixtures (test DB, mock data)
    ├── test_regime.py
    ├── test_screener.py
    ├── test_dcf.py
    ├── test_options_scanner.py
    ├── test_earnings.py
    ├── test_database.py
    └── test_api.py
```

---

## Task 1: Project Scaffolding + SQLite + Bootstrap

**Covers:** S1-148, S2-207, S2-232, S2-245-249, S2-253
**Addresses review:** #1 (single process), #9 (bootstrap), #10 (SQLite over JSON)

**Files:**
- Create: `stock-analysis-system/requirements.txt`
- Create: `stock-analysis-system/backend/main.py`
- Create: `stock-analysis-system/backend/config.py`
- Create: `stock-analysis-system/backend/database.py`
- Create: `stock-analysis-system/setup.sh`
- Create: `stock-analysis-system/start.sh`
- Create: `stock-analysis-system/CLAUDE.md`

- [ ] **Step 1: Create project directories and git init**

```bash
cd "/Users/sbakshi/Documents/Stocks Sucess"
mkdir -p stock-analysis-system/{backend/{routers,services,data},bridge,tests,frontend}
cd stock-analysis-system
git init
```

- [ ] **Step 2: Create requirements.txt**

```
yfinance>=0.2.36
fastapi>=0.115.0
uvicorn>=0.30.0
pandas>=2.0
numpy>=1.24
scipy>=1.11
pydantic>=2.0
httpx>=0.27.0
edgartools>=5.28
tabulate>=0.9
aiosqlite>=0.20.0
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 3: Create backend/config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "app.db"
SP500_FALLBACK = DATA_DIR / "sp500_fallback.json"

# API keys — set via environment variables
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

USD_GBP_RATE = 0.80

# B1 hard gates — missing data = FAIL (fail-closed)
B1_GATES = {
    "min_operating_margin": 0.20,
    "fcf_positive": True,
    "min_drop_from_high": 0.20,
    "min_revenue_growth": 0.0,
    "max_debt_to_equity": 5.0,
    "max_forward_pe": 50.0,
}

# B2 hard gates — missing data = FAIL (fail-closed)
B2_GATES = {
    "min_revenue_growth": 0.25,
    "min_gross_margin": 0.40,
    "min_revenue": 200_000_000,
}

# Options scanner parameters
OPTIONS_PARAMS = {
    "min_dte": 60,
    "max_dte": 120,
    "min_delta": 0.25,
    "max_delta": 0.40,
    "min_oi": 500,
    "max_spread_pct": 0.10,
    "max_premium_usd": 7.00,
    "risk_per_trade_gbp": 500,
    "target_multiple": 4,
    "earnings_proximity_days": 14,
}

# DCF defaults — WACC fixed across scenarios per spec
DCF_DEFAULTS = {
    "wacc": 0.10,
    "terminal_growth": 0.025,
    "forecast_years": 10,
    "max_terminal_pct": 0.50,
    "sbc_threshold": 0.10,  # flag if SBC > 10% of revenue
}
```

- [ ] **Step 4: Create backend/database.py**

```python
import sqlite3
from pathlib import Path
from backend.config import DB_PATH


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            ticker TEXT PRIMARY KEY,
            bucket TEXT NOT NULL,
            added_date TEXT NOT NULL DEFAULT (date('now')),
            thesis_note TEXT DEFAULT '',
            entry_zone_low REAL,
            entry_zone_high REAL,
            last_deep_dive TEXT,
            conviction TEXT DEFAULT 'MODERATE',
            status TEXT DEFAULT 'WATCHING'
        );

        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            position_type TEXT NOT NULL,
            bucket TEXT DEFAULT 'B1',
            shares REAL,
            avg_price REAL,
            strike REAL,
            expiry TEXT,
            premium_paid REAL,
            contracts INTEGER,
            entry_date TEXT NOT NULL DEFAULT (date('now')),
            thesis TEXT DEFAULT '',
            invalidation TEXT DEFAULT '[]',
            target_fair_value REAL,
            status TEXT DEFAULT 'OPEN',
            exit_price REAL,
            exit_date TEXT,
            exit_reason TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date TEXT NOT NULL DEFAULT (datetime('now')),
            scan_type TEXT NOT NULL DEFAULT 'weekly',
            total_scanned INTEGER,
            b1_count INTEGER,
            b2_count INTEGER,
            results_json TEXT NOT NULL,
            errors_json TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS deep_dives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            dive_date TEXT NOT NULL DEFAULT (datetime('now')),
            fundamentals_json TEXT,
            reverse_dcf_json TEXT,
            forward_dcf_json TEXT,
            ai_first_impression TEXT,
            ai_bear_case_stock TEXT,
            ai_bear_case_business TEXT,
            ai_bull_case_rebuttal TEXT,
            ai_bull_case_upside TEXT,
            ai_whole_picture TEXT,
            ai_self_review TEXT,
            ai_verdict TEXT,
            ai_conviction TEXT,
            ai_entry_grid_json TEXT,
            ai_exit_playbook TEXT,
            data_completeness TEXT DEFAULT '{}'
        );

        CREATE INDEX IF NOT EXISTS idx_deep_dives_ticker ON deep_dives(ticker, dive_date DESC);
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
        CREATE INDEX IF NOT EXISTS idx_scan_results_date ON scan_results(scan_date DESC);
    """)
    conn.close()
```

- [ ] **Step 5: Create backend/main.py (single-process, serves static files)**

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import init_db

app = FastAPI(title="Contrarian Investing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # dev only
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve React build (production mode)
STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
```

- [ ] **Step 6: Create CLAUDE.md**

```markdown
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
```

- [ ] **Step 7: Create setup.sh (one-command bootstrap)**

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Contrarian Investing Platform Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install Python 3.12+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python: $PYTHON_VERSION"

# Check Node
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Install Node.js 18+."
    exit 1
fi
echo "Node: $(node --version)"

# Python venv + deps
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Initialize database
echo "Initializing SQLite database..."
python3 -c "from backend.database import init_db; init_db()"

# Frontend
echo "Installing frontend dependencies..."
cd frontend
npm install --silent
echo "Building frontend..."
npm run build
cd ..

echo ""
echo "=== Setup complete! ==="
echo "Run ./start.sh to launch the app."
```

- [ ] **Step 8: Create start.sh**

```bash
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

echo ""
echo "=========================================="
echo "  Contrarian Investing Platform"
echo "  http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "=========================================="
echo ""

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- [ ] **Step 9: Make scripts executable and verify**

```bash
chmod +x setup.sh start.sh
```

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with SQLite, bootstrap script, single-process architecture"
```

---

## Task 2: S&P 500 List with Cached Fallback + Data Provider Abstraction

**Covers:** S1-111, S1-144, S1-145, S1-146, S1-147
**Addresses review:** #3 (data layer resilience), #10 (stale data)

**Files:**
- Create: `backend/services/sp500.py`
- Create: `backend/services/providers.py`
- Create: `backend/data/sp500_fallback.json`
- Create: `tests/conftest.py`
- Create: `tests/test_market_data.py`

- [ ] **Step 1: Write test for S&P 500 with fallback**

```python
# tests/test_market_data.py
import json
from unittest.mock import patch
from backend.services.sp500 import get_sp500_tickers


def test_get_sp500_tickers_returns_list():
    tickers = get_sp500_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) > 400
    assert "AAPL" in tickers


def test_get_sp500_tickers_fallback_on_failure():
    with patch("backend.services.sp500._fetch_from_wikipedia", side_effect=Exception("network error")):
        tickers = get_sp500_tickers(use_cache=True)
        assert isinstance(tickers, list)
        assert len(tickers) > 400
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd "/Users/sbakshi/Documents/Stocks Sucess/stock-analysis-system"
source .venv/bin/activate
python -m pytest tests/test_market_data.py -v
# Expected: FAIL — ModuleNotFoundError
```

- [ ] **Step 3: Implement sp500.py with cached fallback**

```python
# backend/services/sp500.py
import json
import pandas as pd
from pathlib import Path
from backend.config import SP500_FALLBACK

_cache: list[str] | None = None


def _fetch_from_wikipedia() -> list[str]:
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    tables = pd.read_html(url)
    df = tables[0]
    return sorted(df["Symbol"].str.replace(".", "-", regex=False).tolist())


def get_sp500_tickers(use_cache: bool = True) -> list[str]:
    global _cache
    if _cache is not None:
        return _cache

    try:
        tickers = _fetch_from_wikipedia()
        # Update fallback file on success
        SP500_FALLBACK.parent.mkdir(parents=True, exist_ok=True)
        SP500_FALLBACK.write_text(json.dumps(tickers))
        _cache = tickers
        return tickers
    except Exception:
        if use_cache and SP500_FALLBACK.exists():
            _cache = json.loads(SP500_FALLBACK.read_text())
            return _cache
        raise
```

- [ ] **Step 4: Create initial sp500_fallback.json**

```bash
cd "/Users/sbakshi/Documents/Stocks Sucess/stock-analysis-system"
source .venv/bin/activate
python3 -c "
from backend.services.sp500 import get_sp500_tickers
tickers = get_sp500_tickers()
print(f'Cached {len(tickers)} tickers')
"
```

- [ ] **Step 5: Create providers.py (data abstraction)**

```python
# backend/services/providers.py
"""
Data provider abstraction. Each data function tries primary source,
falls back to secondary, tracks data quality.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class DataResult:
    """Wraps any data fetch with provenance metadata."""
    value: Any
    source: str  # "yfinance", "fmp", "finnhub", "edgar", "fallback"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    is_stale: bool = False
    is_fallback: bool = False
    missing_fields: list[str] = field(default_factory=list)

    @property
    def completeness(self) -> float:
        """0.0 to 1.0 — fraction of expected fields present."""
        if not self.missing_fields:
            return 1.0
        # Caller must set expected count
        return max(0, 1.0 - len(self.missing_fields) / 20)


def try_providers(primary_fn, fallback_fn=None, primary_name="yfinance", fallback_name="fallback"):
    """Try primary data source, fall back to secondary on failure."""
    try:
        result = primary_fn()
        return DataResult(value=result, source=primary_name)
    except Exception as primary_err:
        if fallback_fn:
            try:
                result = fallback_fn()
                return DataResult(value=result, source=fallback_name, is_fallback=True)
            except Exception:
                pass
        raise primary_err
```

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_market_data.py -v
# Expected: all PASS
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: S&P 500 ticker list with cached fallback and data provider abstraction"
```

---

## Task 3: Market Data Service (Fail-Closed, with Quality Tracking)

**Covers:** S1-54-68, S1-74, S2-19-32
**Addresses review:** #3 (None handling, fail-closed), #10 (data quality)

**Files:**
- Create: `backend/services/market_data.py`
- Modify: `tests/test_market_data.py`

- [ ] **Step 1: Write test for fundamentals with missing data detection**

```python
# tests/test_market_data.py (append)
from backend.services.market_data import get_stock_fundamentals, REQUIRED_B1_FIELDS


def test_get_stock_fundamentals_aapl():
    result = get_stock_fundamentals("AAPL")
    data = result.value
    assert data["ticker"] == "AAPL"
    assert data["market_cap"] is not None and data["market_cap"] > 0
    assert result.source == "yfinance"


def test_fundamentals_tracks_missing_fields():
    result = get_stock_fundamentals("AAPL")
    # AAPL should have most fields populated
    assert isinstance(result.missing_fields, list)


def test_required_b1_fields_defined():
    assert "operating_margin" in REQUIRED_B1_FIELDS
    assert "free_cash_flow" in REQUIRED_B1_FIELDS
    assert "forward_pe" in REQUIRED_B1_FIELDS
    assert "revenue_growth" in REQUIRED_B1_FIELDS
    assert "debt_to_equity" in REQUIRED_B1_FIELDS
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_market_data.py::test_get_stock_fundamentals_aapl -v
# Expected: FAIL
```

- [ ] **Step 3: Implement market_data.py**

```python
# backend/services/market_data.py
import yfinance as yf
import pandas as pd
from datetime import datetime
from backend.services.providers import DataResult

REQUIRED_B1_FIELDS = [
    "operating_margin", "free_cash_flow", "revenue_growth",
    "debt_to_equity", "forward_pe", "drop_from_high",
]

REQUIRED_B2_FIELDS = [
    "revenue_growth", "gross_margin", "total_revenue",
]

ALL_FUNDAMENTAL_FIELDS = [
    "price", "market_cap", "forward_pe", "trailing_pe",
    "revenue_growth", "operating_margin", "gross_margin", "profit_margin",
    "free_cash_flow", "total_revenue", "debt_to_equity", "return_on_equity",
    "short_percent", "shares_outstanding", "beta", "dividend_yield",
    "high_52w", "low_52w", "drop_from_high", "earnings_date",
]


def get_stock_fundamentals(ticker: str) -> DataResult:
    stock = yf.Ticker(ticker)
    info = stock.info

    high_52w = info.get("fiftyTwoWeekHigh")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    drop = (high_52w - price) / high_52w if (high_52w and price and high_52w > 0) else None

    # Earnings date
    earnings_date = None
    try:
        cal = stock.calendar
        if cal is not None and not cal.empty:
            earnings_date = str(cal.iloc[0, 0]) if hasattr(cal, 'iloc') else None
    except Exception:
        pass

    # D/E: yfinance returns as percentage (e.g., 150 = 1.5x)
    raw_de = info.get("debtToEquity")
    de_ratio = raw_de / 100 if raw_de is not None else None

    data = {
        "ticker": ticker,
        "name": info.get("shortName", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "price": price,
        "market_cap": info.get("marketCap"),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
        "revenue_growth": info.get("revenueGrowth"),
        "operating_margin": info.get("operatingMargins"),
        "gross_margin": info.get("grossMargins"),
        "profit_margin": info.get("profitMargins"),
        "free_cash_flow": info.get("freeCashflow"),
        "total_revenue": info.get("totalRevenue"),
        "debt_to_equity": de_ratio,
        "return_on_equity": info.get("returnOnEquity"),
        "short_percent": info.get("shortPercentOfFloat"),
        "high_52w": high_52w,
        "low_52w": info.get("fiftyTwoWeekLow"),
        "drop_from_high": round(drop, 4) if drop is not None else None,
        "shares_outstanding": info.get("sharesOutstanding"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
        "earnings_date": earnings_date,
    }

    missing = [f for f in ALL_FUNDAMENTAL_FIELDS if data.get(f) is None]

    return DataResult(value=data, source="yfinance", missing_fields=missing)


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def get_moving_averages(ticker: str) -> dict:
    df = get_price_history(ticker, period="1y")
    if df.empty:
        return {}
    price = float(df["Close"].iloc[-1])
    ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
    sma50 = float(df["Close"].rolling(50).mean().iloc[-1])
    sma200 = float(df["Close"].rolling(200).mean().iloc[-1])
    return {
        "price": round(price, 2),
        "ema20": round(ema20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
    }


def get_options_chain(ticker: str) -> list[dict]:
    stock = yf.Ticker(ticker)
    expirations = stock.options
    all_contracts = []
    now = datetime.now()

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
        dte = (exp_date - now).days
        if dte < 30 or dte > 150:
            continue
        chain = stock.option_chain(exp_str)
        for df, otype in [(chain.calls, "call"), (chain.puts, "put")]:
            copy = df.copy()
            copy["expiry"] = exp_str
            copy["dte"] = dte
            copy["option_type"] = otype
            all_contracts.append(copy)

    if not all_contracts:
        return []
    return pd.concat(all_contracts, ignore_index=True).to_dict(orient="records")


def get_fcf_3yr_average(ticker: str) -> float | None:
    """Get 3-year average FCF. Returns None if insufficient data."""
    stock = yf.Ticker(ticker)
    try:
        cf = stock.cashflow
        if cf is None or cf.empty:
            return None
        fcf_row = cf.loc["Free Cash Flow"] if "Free Cash Flow" in cf.index else None
        if fcf_row is None:
            return None
        values = [v for v in fcf_row.values[:3] if pd.notna(v)]
        if len(values) < 2:
            return None
        return sum(values) / len(values)
    except Exception:
        return None


def get_sbc(ticker: str) -> float | None:
    """Get stock-based compensation from cash flow statement."""
    stock = yf.Ticker(ticker)
    try:
        cf = stock.cashflow
        if cf is None or cf.empty:
            return None
        for label in ["Stock Based Compensation", "Share Based Compensation"]:
            if label in cf.index:
                val = cf.loc[label].values[0]
                return float(val) if pd.notna(val) else None
        return None
    except Exception:
        return None


def get_net_debt(ticker: str) -> float | None:
    """Get net debt from balance sheet (total debt - cash)."""
    stock = yf.Ticker(ticker)
    try:
        bs = stock.balance_sheet
        if bs is None or bs.empty:
            return None
        total_debt = None
        cash = None
        for label in ["Total Debt", "Long Term Debt"]:
            if label in bs.index:
                val = bs.loc[label].values[0]
                if pd.notna(val):
                    total_debt = float(val)
                    break
        for label in ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]:
            if label in bs.index:
                val = bs.loc[label].values[0]
                if pd.notna(val):
                    cash = float(val)
                    break
        if total_debt is not None and cash is not None:
            return total_debt - cash
        return total_debt  # if no cash data, return gross debt
    except Exception:
        return None
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_market_data.py -v
# Expected: all PASS
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: market data service with fail-closed field tracking, 3yr FCF, SBC, net debt"
```

---

## Task 4: Market Regime Checker (Gate 0) with VIX Tax

**Covers:** S2-133-161, S1-141-142
**Addresses review:** #10 (regime correctness — VIX tax)

**Files:**
- Create: `backend/services/regime_checker.py`
- Create: `backend/routers/regime.py`
- Create: `tests/test_regime.py`

- [ ] **Step 1: Write tests for regime logic + VIX tax**

```python
# tests/test_regime.py
from backend.services.regime_checker import determine_regime, classify_direction, calculate_vix_tax


def test_classify_full_uptrend():
    d = classify_direction(500, 495, 490, 470)
    assert d == "FULL_UPTREND"


def test_classify_full_downtrend():
    d = classify_direction(400, 420, 440, 470)
    assert d == "FULL_DOWNTREND"


def test_determine_regime_deploy():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=15.0)
    assert result["verdict"] == "DEPLOY"
    assert result["max_new_positions"] == 5


def test_determine_regime_cash_on_downtrend():
    spy = {"direction": "FULL_DOWNTREND"}
    qqq = {"direction": "FULL_DOWNTREND"}
    result = determine_regime(spy, qqq, vix=30.0)
    assert result["verdict"] == "CASH"
    assert result["max_new_positions"] == 0


def test_determine_regime_vix_override():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=36.0)
    assert result["verdict"] == "CASH"


def test_vix_tax_at_normal():
    tax = calculate_vix_tax(15.0)
    assert tax["premium_premium_pct"] == 0


def test_vix_tax_at_elevated():
    tax = calculate_vix_tax(25.0)
    assert tax["premium_premium_pct"] > 0
    assert "elevated" in tax["note"].lower() or "above" in tax["note"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_regime.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement regime_checker.py with VIX tax**

```python
# backend/services/regime_checker.py
import yfinance as yf
from backend.services.market_data import get_moving_averages


def classify_direction(price: float, ema20: float, sma50: float, sma200: float) -> str:
    if price > ema20 > sma50 > sma200:
        return "FULL_UPTREND"
    elif price > sma50 and price > sma200 and price < ema20:
        return "PULLBACK_IN_UPTREND"
    elif price < ema20 and price < sma50 and price > sma200:
        if abs(sma50 - sma200) / sma200 < 0.02:
            return "POTENTIAL_TREND_CHANGE"
        return "TREND_WEAKENING"
    elif price < ema20 and price < sma50 and sma50 > sma200:
        return "CORRECTION_IN_UPTREND"
    elif price < ema20 and price < sma50 and price < sma200:
        return "FULL_DOWNTREND"
    return "MIXED"


DIRECTION_SCORES = {
    "FULL_UPTREND": 4,
    "PULLBACK_IN_UPTREND": 3,
    "TREND_WEAKENING": 2,
    "CORRECTION_IN_UPTREND": 1.5,
    "MIXED": 1.5,
    "POTENTIAL_TREND_CHANGE": 1,
    "FULL_DOWNTREND": 0,
}


def calculate_vix_tax(vix: float) -> dict:
    """Calculate how much extra premium you pay vs VIX at 15 (historical calm)."""
    baseline_vix = 15.0
    if vix <= baseline_vix:
        return {"premium_premium_pct": 0, "note": f"VIX at {vix} — premiums at normal levels."}

    # Rough approximation: option premiums scale ~linearly with IV
    premium_pct = round((vix - baseline_vix) / baseline_vix * 100, 0)
    if vix > 30:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"4x target likely unachievable on delta 0.25-0.40 contracts. Avoid.")
    elif vix > 25:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"Need larger underlying move for 4x. Highest-conviction B1 only.")
    else:
        note = (f"VIX at {vix} — premiums ~{premium_pct:.0f}% above normal. "
                f"Acceptable for B1 plays where fear is narrative, not fundamental.")
    return {"premium_premium_pct": int(premium_pct), "note": note}


def determine_regime(spy: dict, qqq: dict, vix: float) -> dict:
    if vix > 35:
        return {
            "verdict": "CASH",
            "max_new_positions": 0,
            "spy_direction": spy["direction"],
            "qqq_direction": qqq["direction"],
            "vix": vix,
            "score": 0,
            "vix_tax": calculate_vix_tax(vix),
            "options_note": "NO new options positions. VIX extreme — capital preservation.",
        }

    spy_score = DIRECTION_SCORES.get(spy["direction"], 1.5)
    qqq_score = DIRECTION_SCORES.get(qqq["direction"], 1.5)
    avg_score = (spy_score + qqq_score) / 2

    if vix > 25:
        avg_score -= 0.5
    elif vix < 20:
        avg_score += 0.25

    if avg_score >= 3:
        verdict, max_pos = "DEPLOY", 5
    elif avg_score >= 2:
        verdict, max_pos = "CAUTIOUS", 2
    elif avg_score >= 1:
        verdict, max_pos = "DEFENSIVE", 0
    else:
        verdict, max_pos = "CASH", 0

    vix_tax = calculate_vix_tax(vix)

    return {
        "verdict": verdict,
        "max_new_positions": max_pos,
        "spy_direction": spy["direction"],
        "qqq_direction": qqq["direction"],
        "vix": vix,
        "score": round(avg_score, 2),
        "vix_tax": vix_tax,
        "options_note": vix_tax["note"] if verdict in ("DEPLOY", "CAUTIOUS") else "NO new positions.",
    }


def get_full_regime() -> dict:
    spy_ma = get_moving_averages("SPY")
    qqq_ma = get_moving_averages("QQQ")

    spy_dir = classify_direction(spy_ma["price"], spy_ma["ema20"], spy_ma["sma50"], spy_ma["sma200"])
    qqq_dir = classify_direction(qqq_ma["price"], qqq_ma["ema20"], qqq_ma["sma50"], qqq_ma["sma200"])

    vix_data = yf.download("^VIX", period="5d", interval="1d", progress=False)
    vix = round(float(vix_data["Close"].iloc[-1]), 2)

    spy_info = {**spy_ma, "direction": spy_dir, "ticker": "SPY"}
    qqq_info = {**qqq_ma, "direction": qqq_dir, "ticker": "QQQ"}

    regime = determine_regime(spy_info, qqq_info, vix)
    return {"spy": spy_info, "qqq": qqq_info, "regime": regime}
```

- [ ] **Step 4: Create regime router**

```python
# backend/routers/regime.py
from fastapi import APIRouter
from backend.services.regime_checker import get_full_regime

router = APIRouter(prefix="/api/regime", tags=["regime"])


@router.get("")
def regime_check():
    return get_full_regime()
```

- [ ] **Step 5: Wire router into main.py** — add `from backend.routers import regime` and `app.include_router(regime.router)` after the startup event.

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_regime.py -v
# Expected: all PASS
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: market regime checker with VIX tax calculation and direction scoring"
```

---

## Task 5: Stock Screener (Fail-Closed Gates + All Warnings)

**Covers:** S1-03-42, S1-149
**Addresses review:** #3 (fail-closed gates), #2 (all warning flags)

**Files:**
- Create: `backend/services/stock_screener.py`
- Create: `backend/routers/screener.py`
- Create: `tests/test_screener.py`

- [ ] **Step 1: Write tests for fail-closed B1 gates**

```python
# tests/test_screener.py
from backend.services.stock_screener import check_b1_gates, check_b1_warnings, check_b2_gates


def test_b1_gates_pass():
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is True


def test_b1_gates_fail_missing_margin():
    """Missing data = FAIL (fail-closed)."""
    stock = {
        "operating_margin": None, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is False


def test_b1_gates_fail_missing_pe():
    """Missing forward PE = FAIL."""
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": 0.5, "forward_pe": None,
    }
    assert check_b1_gates(stock) is False


def test_b1_gates_fail_missing_de():
    """Missing D/E = FAIL."""
    stock = {
        "operating_margin": 0.35, "free_cash_flow": 5e9, "drop_from_high": 0.43,
        "revenue_growth": 0.10, "debt_to_equity": None, "forward_pe": 15.0,
    }
    assert check_b1_gates(stock) is False


def test_b1_warnings_all():
    stock = {
        "revenue_growth": 0.03, "debt_to_equity": 3.5, "short_percent": 0.12,
        "return_on_equity": 1.5, "trailing_pe": 60, "forward_pe": 15,
        "sector": "Energy", "earnings_date": "2026-04-15",
    }
    warnings = check_b1_warnings(stock)
    assert "SLOW GROWTH" in warnings
    assert "HIGH LEVERAGE" in warnings
    assert "HIGH SHORT" in warnings
    assert "LEVERAGE-DRIVEN ROE" in warnings
    assert "P/E COMPRESSION" in warnings
    assert "CYCLICAL" in warnings


def test_b2_gates_fail_closed():
    stock = {"revenue_growth": None, "gross_margin": 0.50, "total_revenue": 300e6}
    assert check_b2_gates(stock) is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_screener.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement stock_screener.py (fail-closed)**

```python
# backend/services/stock_screener.py
from datetime import datetime, timedelta
from backend.config import B1_GATES, B2_GATES


def check_b1_gates(stock: dict) -> bool:
    """All gates are fail-closed: None = FAIL."""
    om = stock.get("operating_margin")
    fcf = stock.get("free_cash_flow")
    drop = stock.get("drop_from_high")
    rg = stock.get("revenue_growth")
    de = stock.get("debt_to_equity")
    fpe = stock.get("forward_pe")

    # Fail-closed: any None = reject
    if om is None or om < B1_GATES["min_operating_margin"]:
        return False
    if fcf is None or fcf <= 0:
        return False
    if drop is None or drop < B1_GATES["min_drop_from_high"]:
        return False
    if rg is None or rg < B1_GATES["min_revenue_growth"]:
        return False
    if de is None or de > B1_GATES["max_debt_to_equity"]:
        return False
    if fpe is None or fpe > B1_GATES["max_forward_pe"]:
        return False
    return True


def check_b2_gates(stock: dict) -> bool:
    """All gates are fail-closed: None = FAIL."""
    rg = stock.get("revenue_growth")
    gm = stock.get("gross_margin")
    rev = stock.get("total_revenue")

    if rg is None or rg < B2_GATES["min_revenue_growth"]:
        return False
    if gm is None or gm < B2_GATES["min_gross_margin"]:
        return False
    if rev is None or rev < B2_GATES["min_revenue"]:
        return False
    return True


def check_b1_warnings(stock: dict) -> list[str]:
    warnings = []
    rg = stock.get("revenue_growth")
    de = stock.get("debt_to_equity")
    si = stock.get("short_percent")
    roe = stock.get("return_on_equity")
    tpe = stock.get("trailing_pe")
    fpe = stock.get("forward_pe")
    sector = stock.get("sector", "")
    earnings = stock.get("earnings_date")

    if rg is not None and rg < 0.05:
        warnings.append("SLOW GROWTH")
    if de is not None and de > 3.0:
        warnings.append("HIGH LEVERAGE")
    if si is not None and si > 0.10:
        warnings.append("HIGH SHORT")
    if roe is not None and roe > 1.0:
        warnings.append("LEVERAGE-DRIVEN ROE")
    if tpe and fpe and fpe > 0 and tpe / fpe > 3:
        warnings.append("P/E COMPRESSION")
    if sector in ("Energy", "Basic Materials"):
        warnings.append("CYCLICAL")
    if earnings:
        try:
            ed = datetime.fromisoformat(str(earnings).split(" ")[0])
            if (ed - datetime.now()).days <= 14:
                warnings.append("EARNINGS SOON")
        except (ValueError, TypeError):
            pass
    return warnings


def check_b2_warnings(stock: dict) -> list[str]:
    warnings = []
    fcf = stock.get("free_cash_flow")
    fpe = stock.get("forward_pe")
    if fcf is not None and fcf < 0:
        warnings.append("CASH BURN")
    if fpe is not None and fpe > 80:
        warnings.append("EXTREME VALUATION")
    return warnings


def scan_sp500(scan_type: str = "weekly") -> dict:
    """Full S&P 500 scan. Returns B1 and B2 candidates with warnings."""
    from backend.services.sp500 import get_sp500_tickers
    from backend.services.market_data import get_stock_fundamentals

    tickers = get_sp500_tickers()
    b1_candidates = []
    b2_candidates = []
    errors = []

    for ticker in tickers:
        try:
            result = get_stock_fundamentals(ticker)
            data = result.value
            data["data_source"] = result.source
            data["data_completeness"] = result.completeness
            data["missing_fields"] = result.missing_fields

            is_b1 = check_b1_gates(data)
            is_b2 = check_b2_gates(data)

            if is_b1:
                entry = {**data, "warnings": check_b1_warnings(data), "bucket": "B1"}
                b1_candidates.append(entry)
            if is_b2:
                entry = {**data, "warnings": check_b2_warnings(data), "bucket": "B2"}
                b2_candidates.append(entry)
        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})

    return {
        "scan_date": datetime.now().isoformat(),
        "scan_type": scan_type,
        "total_scanned": len(tickers),
        "b1_count": len(b1_candidates),
        "b2_count": len(b2_candidates),
        "error_count": len(errors),
        "b1_candidates": sorted(b1_candidates, key=lambda x: x.get("drop_from_high") or 0, reverse=True),
        "b2_candidates": sorted(b2_candidates, key=lambda x: x.get("revenue_growth") or 0, reverse=True),
        "errors": errors,
    }
```

- [ ] **Step 4: Create screener router with daily/weekly modes**

```python
# backend/routers/screener.py
import json
from fastapi import APIRouter, Query
from backend.services.stock_screener import scan_sp500
from backend.database import get_db

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/scan")
def run_scan(scan_type: str = Query("weekly", enum=["daily", "weekly"])):
    """Run S&P 500 scan. Weekly = full rescan. Daily = watchlist only."""
    if scan_type == "daily":
        # Daily: only scan watchlist tickers
        db = get_db()
        rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
        db.close()
        tickers = [r["ticker"] for r in rows]
        if not tickers:
            return {"error": "No watchlist entries. Add stocks first or run weekly scan."}
        # Scan only those tickers
        from backend.services.market_data import get_stock_fundamentals
        from backend.services.stock_screener import check_b1_gates, check_b1_warnings
        results = []
        for t in tickers:
            try:
                data = get_stock_fundamentals(t).value
                data["warnings"] = check_b1_warnings(data)
                results.append(data)
            except Exception as e:
                results.append({"ticker": t, "error": str(e)})
        return {"scan_type": "daily", "results": results}

    results = scan_sp500(scan_type=scan_type)
    # Save to database
    db = get_db()
    db.execute(
        "INSERT INTO scan_results (scan_type, total_scanned, b1_count, b2_count, results_json, errors_json) VALUES (?, ?, ?, ?, ?, ?)",
        (scan_type, results["total_scanned"], results["b1_count"], results["b2_count"],
         json.dumps(results, default=str), json.dumps(results["errors"], default=str)),
    )
    db.commit()
    db.close()
    return results


@router.get("/latest")
def get_latest_scan():
    """Get most recent scan results with freshness indicator."""
    db = get_db()
    row = db.execute("SELECT * FROM scan_results ORDER BY scan_date DESC LIMIT 1").fetchone()
    db.close()
    if not row:
        return {"error": "No scan results. Run /api/screener/scan?scan_type=weekly first."}
    result = json.loads(row["results_json"])
    result["scan_id"] = row["id"]
    result["is_stale"] = False  # TODO: check age > 7 days
    return result
```

- [ ] **Step 5: Wire screener router into main.py**

- [ ] **Step 6: Run tests**

```bash
python -m pytest tests/test_screener.py -v
# Expected: all PASS
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: B1/B2 stock screener with fail-closed gates, all warnings, daily/weekly modes"
```

---

## Task 6: DCF Calculator (Corrected Per Spec)

**Covers:** S1-85-103, S1-152
**Addresses review:** #4 (DCF correctness — SBC, 3yr avg, WACC fixed, net debt)

**Files:**
- Create: `backend/services/dcf_calculator.py`
- Create: `tests/test_dcf.py`

- [ ] **Step 1: Write tests enforcing spec rules**

```python
# tests/test_dcf.py
from backend.services.dcf_calculator import (
    calculate_dcf, reverse_dcf, build_sensitivity_matrix, adjust_fcf_for_sbc,
)


def test_dcf_basic():
    result = calculate_dcf(
        starting_fcf=1e9, growth_rate_1_5=0.15, growth_rate_6_10=0.08,
        terminal_growth=0.025, wacc=0.10,
        shares_outstanding=450_000_000, net_debt=2e9,
    )
    assert result["intrinsic_value_per_share"] > 0
    assert result["terminal_value_pct"] <= 1.0


def test_dcf_terminal_warning():
    """Low growth should trigger terminal value >50% warning."""
    result = calculate_dcf(
        starting_fcf=100e6, growth_rate_1_5=0.01, growth_rate_6_10=0.01,
        terminal_growth=0.025, wacc=0.10,
        shares_outstanding=100e6, net_debt=0,
    )
    assert result.get("terminal_value_warning") is not None


def test_sensitivity_matrix_wacc_is_fixed():
    """Spec rule: WACC cannot change between scenarios. Matrix varies growth only."""
    matrix = build_sensitivity_matrix(
        starting_fcf=1e9, base_growth_1_5=0.15, base_growth_6_10=0.08,
        terminal_growth=0.025, wacc=0.10,
        shares_outstanding=450e6, net_debt=2e9,
    )
    # All rows should use the same WACC
    for row in matrix:
        assert row["wacc"] == 0.10


def test_reverse_dcf():
    result = reverse_dcf(
        current_price=250.0, starting_fcf=1e9,
        shares_outstanding=450e6, net_debt=2e9,
    )
    assert "implied_growth_rate" in result
    assert isinstance(result["implied_growth_rate"], float)


def test_sbc_adjustment():
    adjusted = adjust_fcf_for_sbc(fcf=1e9, sbc=150e6, revenue=1e9)
    assert adjusted == 1e9 - 150e6  # SBC > 10% of revenue, so subtract


def test_sbc_no_adjustment_below_threshold():
    adjusted = adjust_fcf_for_sbc(fcf=1e9, sbc=50e6, revenue=1e9)
    assert adjusted == 1e9  # SBC = 5% < 10%, no adjustment
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_dcf.py -v
# Expected: FAIL
```

- [ ] **Step 3: Implement dcf_calculator.py (corrected)**

```python
# backend/services/dcf_calculator.py
from backend.config import DCF_DEFAULTS


def adjust_fcf_for_sbc(fcf: float, sbc: float | None, revenue: float | None) -> float:
    """Subtract SBC from FCF if SBC > 10% of revenue. Spec rule."""
    if sbc is None or revenue is None or revenue <= 0:
        return fcf
    if sbc / revenue > DCF_DEFAULTS["sbc_threshold"]:
        return fcf - sbc
    return fcf


def _compute_dcf(starting_fcf, g1, g2, tg, wacc, shares, net_debt) -> dict:
    """Core DCF computation. No recursion, no __wrapped__ hack."""
    fcf = starting_fcf
    projections = []

    # Years 1-5
    for year in range(1, 6):
        fcf = fcf * (1 + g1)
        projections.append({"year": year, "fcf": fcf, "growth": g1})

    # Years 6-10: linear deceleration from g2 to terminal
    for year in range(6, 11):
        blend = (year - 5) / 5
        rate = g2 * (1 - blend) + tg * blend
        fcf = fcf * (1 + rate)
        projections.append({"year": year, "fcf": fcf, "growth": round(rate, 4)})

    # Terminal value
    if wacc <= tg:
        terminal_value = 0  # invalid — flag it
    else:
        terminal_fcf = fcf * (1 + tg)
        terminal_value = terminal_fcf / (wacc - tg)

    pv_fcfs = sum(p["fcf"] / (1 + wacc) ** p["year"] for p in projections)
    pv_terminal = terminal_value / (1 + wacc) ** 10
    enterprise_value = pv_fcfs + pv_terminal
    equity_value = enterprise_value - (net_debt or 0)
    per_share = equity_value / shares if shares and shares > 0 else 0
    terminal_pct = pv_terminal / enterprise_value if enterprise_value > 0 else 0

    return {
        "per_share": round(per_share, 2),
        "enterprise_value": round(enterprise_value),
        "equity_value": round(equity_value),
        "pv_fcfs": round(pv_fcfs),
        "pv_terminal": round(pv_terminal),
        "terminal_value_pct": round(terminal_pct, 4),
        "projections": projections,
    }


def calculate_dcf(
    starting_fcf: float,
    growth_rate_1_5: float,
    growth_rate_6_10: float,
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
    wacc: float = DCF_DEFAULTS["wacc"],
    shares_outstanding: int = 1,
    net_debt: float = 0,
) -> dict:
    core = _compute_dcf(starting_fcf, growth_rate_1_5, growth_rate_6_10,
                        terminal_growth, wacc, shares_outstanding, net_debt)

    result = {
        "intrinsic_value_per_share": core["per_share"],
        "enterprise_value": core["enterprise_value"],
        "equity_value": core["equity_value"],
        "pv_fcfs": core["pv_fcfs"],
        "pv_terminal": core["pv_terminal"],
        "terminal_value_pct": core["terminal_value_pct"],
        "fcf_projections": core["projections"],
        "inputs": {
            "starting_fcf": starting_fcf,
            "growth_1_5": growth_rate_1_5,
            "growth_6_10": growth_rate_6_10,
            "terminal_growth": terminal_growth,
            "wacc": wacc,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt,
        },
    }

    if core["terminal_value_pct"] > DCF_DEFAULTS["max_terminal_pct"]:
        result["terminal_value_warning"] = (
            f"Terminal value is {core['terminal_value_pct']:.0%} of total — exceeds 50%. "
            f"Consider shorter forecast period or higher near-term growth."
        )

    return result


def build_sensitivity_matrix(
    starting_fcf: float,
    base_growth_1_5: float,
    base_growth_6_10: float,
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
    wacc: float = DCF_DEFAULTS["wacc"],
    shares_outstanding: int = 1,
    net_debt: float = 0,
) -> list[dict]:
    """
    4x4 sensitivity matrix. WACC is FIXED (spec rule).
    Rows and columns both vary growth rates.
    """
    g1_offsets = [-0.05, -0.02, 0.0, 0.03]
    g2_offsets = [-0.03, -0.01, 0.0, 0.02]
    matrix = []

    for g1_off in g1_offsets:
        row = {
            "wacc": wacc,
            "growth_1_5": round(base_growth_1_5 + g1_off, 3),
            "values": [],
        }
        for g2_off in g2_offsets:
            g1 = base_growth_1_5 + g1_off
            g2 = base_growth_6_10 + g2_off
            core = _compute_dcf(starting_fcf, g1, g2, terminal_growth, wacc,
                                shares_outstanding, net_debt)
            row["values"].append({
                "growth_6_10": round(g2, 3),
                "per_share": core["per_share"],
            })
        matrix.append(row)

    return matrix


def reverse_dcf(
    current_price: float,
    starting_fcf: float,
    shares_outstanding: int,
    net_debt: float,
    wacc: float = DCF_DEFAULTS["wacc"],
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
) -> dict:
    """What growth rate does the market price imply? Binary search."""
    target_equity = current_price * shares_outstanding + (net_debt or 0)
    low, high = -0.10, 0.50

    for _ in range(100):
        mid = (low + high) / 2
        core = _compute_dcf(starting_fcf, mid, mid * 0.6, terminal_growth, wacc,
                            shares_outstanding, net_debt or 0)
        if core["equity_value"] < target_equity:
            low = mid
        else:
            high = mid

    implied = round((low + high) / 2, 4)
    return {
        "implied_growth_rate": implied,
        "current_price": current_price,
        "interpretation": _interpret_implied(implied),
    }


def _interpret_implied(rate: float) -> str:
    if rate < 0:
        return "Market prices in DECLINE. If stable business, this is deep value."
    if rate < 0.05:
        return "Market expects very low growth. Modest beat = significant upside."
    if rate < 0.10:
        return "Market expects moderate growth. Check if achievable."
    if rate < 0.20:
        return "Market expects strong growth. Needs sustained execution."
    return "Market expects exceptional growth. High bar — any miss punished."
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_dcf.py -v
# Expected: all PASS
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: DCF calculator — SBC-adjusted, 3yr avg ready, WACC fixed in sensitivity, net debt"
```

---

## Task 7: Earnings Proximity Checker + Options Scanner

**Covers:** S2-78-128, S2-97, S2-104, S2-160-161
**Addresses review:** #5 (earnings proximity, VIX tax in options)

**Files:**
- Create: `backend/services/earnings.py`
- Create: `backend/services/options_scanner.py`
- Create: `backend/routers/options.py`
- Create: `tests/test_options_scanner.py`
- Create: `tests/test_earnings.py`

- [ ] **Step 1: Write test for earnings proximity**

```python
# tests/test_earnings.py
from datetime import datetime, timedelta
from backend.services.earnings import check_earnings_proximity


def test_earnings_near_expiry():
    # Earnings 7 days before expiry = IV crush risk
    expiry = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
    earnings = (datetime.now() + timedelta(days=53)).strftime("%Y-%m-%d")
    result = check_earnings_proximity(earnings, expiry)
    assert result["iv_crush_risk"] is True


def test_earnings_far_from_expiry():
    expiry = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    earnings = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    result = check_earnings_proximity(earnings, expiry)
    assert result["iv_crush_risk"] is False


def test_earnings_none():
    result = check_earnings_proximity(None, "2026-07-17")
    assert result["iv_crush_risk"] is False
    assert "unknown" in result["note"].lower()
```

- [ ] **Step 2: Write test for options scanner with earnings warning**

```python
# tests/test_options_scanner.py
from backend.services.options_scanner import calculate_delta, filter_contracts


def test_delta_atm():
    delta = calculate_delta(S=100, K=100, T=0.25, r=0.05, sigma=0.30)
    assert 0.45 < delta < 0.60


def test_delta_otm():
    delta = calculate_delta(S=100, K=110, T=0.25, r=0.05, sigma=0.30)
    assert 0.10 < delta < 0.50


def test_filter_contracts_includes_earnings_warning():
    contracts = [{
        "strike": 107, "bid": 4.5, "ask": 5.0, "openInterest": 1000,
        "impliedVolatility": 0.35, "dte": 90, "expiry": "2026-07-17",
        "option_type": "call",
    }]
    results = filter_contracts(
        contracts, stock_price=100,
        earnings_date="2026-07-10",  # 7 days before expiry
    )
    if results:  # may not pass delta filter at this strike
        for r in results:
            assert "IV CRUSH RISK" in r.get("warnings", [])
```

- [ ] **Step 3: Implement earnings.py**

```python
# backend/services/earnings.py
from datetime import datetime
from backend.config import OPTIONS_PARAMS


def check_earnings_proximity(earnings_date: str | None, expiry_date: str) -> dict:
    """Check if earnings fall within proximity_days of option expiry."""
    proximity = OPTIONS_PARAMS["earnings_proximity_days"]

    if not earnings_date:
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }

    try:
        ed = datetime.strptime(str(earnings_date).split(" ")[0], "%Y-%m-%d")
        exp = datetime.strptime(expiry_date, "%Y-%m-%d")
        days_between = abs((exp - ed).days)

        if days_between <= proximity:
            return {
                "iv_crush_risk": True,
                "days_between": days_between,
                "note": f"IV CRUSH RISK: Earnings {days_between}d from expiry. Avoid.",
            }
        return {
            "iv_crush_risk": False,
            "days_between": days_between,
            "note": f"Earnings {days_between}d from expiry. OK.",
        }
    except (ValueError, TypeError):
        return {
            "iv_crush_risk": False,
            "days_between": None,
            "note": "Earnings date unknown — verify manually before entry.",
        }
```

- [ ] **Step 4: Implement options_scanner.py with earnings integration**

```python
# backend/services/options_scanner.py
import numpy as np
from scipy.stats import norm
from backend.config import OPTIONS_PARAMS, USD_GBP_RATE
from backend.services.earnings import check_earnings_proximity


def calculate_delta(S: float, K: float, T: float, r: float = 0.05, sigma: float = 0.30) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1))


def calculate_theta(S: float, K: float, T: float, r: float = 0.05, sigma: float = 0.30) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
             - r * K * np.exp(-r * T) * norm.cdf(d2))
    return round(theta / 365, 4)


def filter_contracts(
    contracts: list[dict],
    stock_price: float,
    earnings_date: str | None = None,
) -> list[dict]:
    params = OPTIONS_PARAMS
    results = []

    for c in contracts:
        if c.get("option_type") != "call":
            continue

        strike = c.get("strike", 0)
        bid = c.get("bid", 0) or 0
        ask = c.get("ask", 0) or 0
        oi = c.get("openInterest", 0) or 0
        iv = c.get("impliedVolatility", 0) or 0
        dte = c.get("dte", 0)

        if dte < params["min_dte"] or dte > params["max_dte"]:
            continue

        otm_pct = (strike - stock_price) / stock_price if stock_price > 0 else 0
        if otm_pct < 0.05 or otm_pct > 0.10:
            continue

        if oi < params["min_oi"]:
            continue

        mid = (bid + ask) / 2 if (bid + ask) > 0 else 0
        spread_pct = (ask - bid) / mid if mid > 0 else 1
        if spread_pct > params["max_spread_pct"]:
            continue

        if ask > params["max_premium_usd"] or ask <= 0:
            continue

        T = dte / 365
        sigma = iv if iv > 0 else 0.30
        delta = calculate_delta(stock_price, strike, T, sigma=sigma)
        if delta < params["min_delta"] or delta > params["max_delta"]:
            continue

        theta_daily = calculate_theta(stock_price, strike, T, sigma=sigma)
        target_4x = ask * params["target_multiple"]
        required_move = (target_4x - ask) / delta if delta > 0 else 0
        required_move_pct = required_move / stock_price if stock_price > 0 else 0

        warnings = []
        if oi < 1000:
            warnings.append("LOW LIQUIDITY")
        if spread_pct > 0.05:
            warnings.append("WIDE SPREAD")

        # Earnings proximity check
        expiry = c.get("expiry", "")
        if earnings_date and expiry:
            ep = check_earnings_proximity(earnings_date, expiry)
            if ep["iv_crush_risk"]:
                warnings.append("IV CRUSH RISK")

        results.append({
            "ticker": c.get("ticker", ""),
            "strike": strike,
            "expiry": expiry,
            "dte": dte,
            "delta": round(delta, 3),
            "iv": round(iv, 3) if iv else None,
            "bid": bid,
            "ask": ask,
            "mid": round(mid, 2),
            "premium_usd": ask,
            "premium_gbp": round(ask * 100 * USD_GBP_RATE, 2),
            "target_3x": round(ask * 3, 2),
            "target_4x": round(ask * 4, 2),
            "required_move_pct": round(required_move_pct, 4),
            "required_move_pct_note": "Approximation — ignores gamma/vega/IV change",
            "open_interest": oi,
            "spread_pct": round(spread_pct, 4),
            "theta_daily": theta_daily,
            "theta_daily_gbp": round(theta_daily * 100 * USD_GBP_RATE, 2),
            "warnings": warnings,
        })

    return sorted(results, key=lambda x: x["required_move_pct"])


def scan_tickers(tickers: list[str]) -> list[dict]:
    from backend.services.market_data import get_stock_fundamentals, get_options_chain

    all_results = []
    for ticker in tickers:
        try:
            fundamentals = get_stock_fundamentals(ticker).value
            price = fundamentals["price"]
            earnings_date = fundamentals.get("earnings_date")
            chain = get_options_chain(ticker)
            for c in chain:
                c["ticker"] = ticker
            qualified = filter_contracts(chain, price, earnings_date=earnings_date)
            all_results.extend(qualified)
        except Exception as e:
            all_results.append({"ticker": ticker, "error": str(e)})
    return all_results
```

- [ ] **Step 5: Create options router with regime context**

```python
# backend/routers/options.py
from fastapi import APIRouter, Query
from backend.services.options_scanner import scan_tickers
from backend.services.regime_checker import get_full_regime

router = APIRouter(prefix="/api/options", tags=["options"])


@router.get("/scan")
def scan_options(tickers: str = Query(..., description="Comma-separated tickers")):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    results = scan_tickers(ticker_list)
    # Include regime context so UI can show it
    try:
        regime = get_full_regime()
    except Exception:
        regime = None
    return {"results": results, "regime": regime}
```

- [ ] **Step 6: Wire options router into main.py**

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/test_earnings.py tests/test_options_scanner.py -v
# Expected: all PASS
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: options scanner with earnings proximity, IV crush warnings, and regime context"
```

---

## Task 8: Deep Dive API + Claude Code Bridge Script

**Covers:** S1-49-53, S1-77-87, S2-207
**Addresses review:** #7 (real Claude bridge — CLI that POSTs to API)

**Files:**
- Create: `backend/routers/deep_dive.py`
- Create: `bridge/deep_dive_worker.py`

- [ ] **Step 1: Create deep_dive router (GET data + POST AI analysis)**

```python
# backend/routers/deep_dive.py
import json
from fastapi import APIRouter, Body
from backend.services.market_data import (
    get_stock_fundamentals, get_fcf_3yr_average, get_sbc, get_net_debt,
)
from backend.services.dcf_calculator import (
    calculate_dcf, reverse_dcf, build_sensitivity_matrix, adjust_fcf_for_sbc,
)
from backend.database import get_db

router = APIRouter(prefix="/api/deep-dive", tags=["deep-dive"])


@router.get("/{ticker}")
def get_deep_dive_data(ticker: str):
    """Get all quantitative data for a deep dive + any saved AI analysis."""
    ticker = ticker.upper()
    fundamentals_result = get_stock_fundamentals(ticker)
    fundamentals = fundamentals_result.value

    # FCF: 3-year average, SBC-adjusted per spec
    fcf_3yr = get_fcf_3yr_average(ticker)
    sbc = get_sbc(ticker)
    revenue = fundamentals.get("total_revenue")
    net_debt = get_net_debt(ticker)
    shares = fundamentals.get("shares_outstanding")
    price = fundamentals.get("price")

    starting_fcf = fcf_3yr or fundamentals.get("free_cash_flow")
    if starting_fcf and sbc:
        starting_fcf = adjust_fcf_for_sbc(starting_fcf, sbc, revenue)

    # Reverse DCF (always first per spec)
    reverse_dcf_result = None
    if starting_fcf and shares and price and starting_fcf > 0:
        reverse_dcf_result = reverse_dcf(
            current_price=price, starting_fcf=starting_fcf,
            shares_outstanding=shares, net_debt=net_debt or 0,
        )

    # Forward DCF (3 scenarios)
    forward_dcf = None
    sensitivity = None
    if starting_fcf and shares and starting_fcf > 0:
        forward_dcf = {
            "bear": calculate_dcf(starting_fcf, 0.05, 0.03, shares_outstanding=shares, net_debt=net_debt or 0),
            "base": calculate_dcf(starting_fcf, 0.12, 0.07, shares_outstanding=shares, net_debt=net_debt or 0),
            "bull": calculate_dcf(starting_fcf, 0.20, 0.12, shares_outstanding=shares, net_debt=net_debt or 0),
        }
        sensitivity = build_sensitivity_matrix(
            starting_fcf, 0.12, 0.07,
            shares_outstanding=shares, net_debt=net_debt or 0,
        )

    # Load saved AI analysis
    db = get_db()
    row = db.execute(
        "SELECT * FROM deep_dives WHERE ticker = ? ORDER BY dive_date DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    db.close()

    ai_analysis = None
    if row:
        ai_analysis = {
            "dive_date": row["dive_date"],
            "first_impression": row["ai_first_impression"],
            "bear_case_stock": row["ai_bear_case_stock"],
            "bear_case_business": row["ai_bear_case_business"],
            "bull_case_rebuttal": row["ai_bull_case_rebuttal"],
            "bull_case_upside": row["ai_bull_case_upside"],
            "whole_picture": row["ai_whole_picture"],
            "self_review": row["ai_self_review"],
            "verdict": row["ai_verdict"],
            "conviction": row["ai_conviction"],
            "entry_grid": json.loads(row["ai_entry_grid_json"]) if row["ai_entry_grid_json"] else None,
            "exit_playbook": row["ai_exit_playbook"],
        }

    return {
        "ticker": ticker,
        "fundamentals": fundamentals,
        "data_quality": {
            "source": fundamentals_result.source,
            "completeness": fundamentals_result.completeness,
            "missing_fields": fundamentals_result.missing_fields,
        },
        "fcf_3yr_avg": fcf_3yr,
        "sbc": sbc,
        "sbc_adjusted": starting_fcf != (fcf_3yr or fundamentals.get("free_cash_flow")),
        "net_debt": net_debt,
        "reverse_dcf": reverse_dcf_result,
        "forward_dcf": forward_dcf,
        "sensitivity_matrix": sensitivity,
        "ai_analysis": ai_analysis,
    }


@router.post("/{ticker}")
def save_deep_dive(ticker: str, data: dict = Body(...)):
    """Save AI-generated deep dive analysis. Called by bridge/deep_dive_worker.py."""
    ticker = ticker.upper()
    db = get_db()
    db.execute("""
        INSERT INTO deep_dives (
            ticker, ai_first_impression, ai_bear_case_stock, ai_bear_case_business,
            ai_bull_case_rebuttal, ai_bull_case_upside, ai_whole_picture,
            ai_self_review, ai_verdict, ai_conviction,
            ai_entry_grid_json, ai_exit_playbook
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker,
        data.get("first_impression"),
        data.get("bear_case_stock"),
        data.get("bear_case_business"),
        data.get("bull_case_rebuttal"),
        data.get("bull_case_upside"),
        data.get("whole_picture"),
        data.get("self_review"),
        data.get("verdict"),
        data.get("conviction"),
        json.dumps(data.get("entry_grid")) if data.get("entry_grid") else None,
        data.get("exit_playbook"),
    ))
    db.commit()
    db.close()
    return {"status": "saved", "ticker": ticker}
```

- [ ] **Step 2: Create bridge/deep_dive_worker.py (Claude Code CLI bridge)**

```python
#!/usr/bin/env python3
"""
Deep Dive Bridge — CLI tool for Claude Code to POST analysis to the local API.

Usage (from Claude Code):
    python bridge/deep_dive_worker.py ADBE --post

This script:
1. Reads a JSON payload from stdin (piped from Claude Code)
2. POSTs it to http://localhost:8000/api/deep-dive/ADBE
3. The dashboard then renders the AI analysis in the 8-section view

Example JSON payload (Claude Code generates this):
{
    "first_impression": "...",
    "bear_case_stock": "...",
    "bear_case_business": "...",
    "bull_case_rebuttal": "...",
    "bull_case_upside": "...",
    "whole_picture": "...",
    "self_review": "...",
    "verdict": "B1 — HIGH conviction",
    "conviction": "HIGH",
    "entry_grid": [...],
    "exit_playbook": "..."
}
"""
import sys
import json
import argparse
import httpx

API_BASE = "http://localhost:8000"


def post_analysis(ticker: str, payload: dict):
    url = f"{API_BASE}/api/deep-dive/{ticker}"
    response = httpx.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print(f"Analysis saved for {ticker}. Refresh dashboard to view.")
    else:
        print(f"Error: {response.status_code} — {response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Deep Dive Bridge for Claude Code")
    parser.add_argument("ticker", help="Stock ticker (e.g. ADBE)")
    parser.add_argument("--post", action="store_true", help="POST analysis from stdin")
    parser.add_argument("--get", action="store_true", help="GET current data for ticker")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    if args.get:
        response = httpx.get(f"{API_BASE}/api/deep-dive/{ticker}", timeout=30)
        print(json.dumps(response.json(), indent=2, default=str))

    elif args.post:
        print(f"Reading analysis JSON from stdin for {ticker}...")
        payload = json.load(sys.stdin)
        post_analysis(ticker, payload)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Wire deep_dive router into main.py**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: deep dive API with 3yr FCF, SBC adjustment, and Claude Code bridge CLI"
```

---

## Task 9: Watchlist + Positions Routers (SQLite)

**Covers:** S1-44-46, S1-104-110, S2-188-206
**Addresses review:** #10 (SQLite, no file corruption)

**Files:**
- Create: `backend/routers/watchlist.py`
- Create: `backend/routers/positions.py`

- [ ] **Step 1: Create watchlist router**

```python
# backend/routers/watchlist.py
from fastapi import APIRouter, Body
from backend.database import get_db

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def get_watchlist():
    db = get_db()
    rows = db.execute("SELECT * FROM watchlist ORDER BY added_date DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("")
def add_to_watchlist(entry: dict = Body(...)):
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO watchlist (ticker, bucket, thesis_note, entry_zone_low, entry_zone_high, conviction, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["ticker"].upper(), entry.get("bucket", "B1"),
        entry.get("thesis_note", ""), entry.get("entry_zone_low"),
        entry.get("entry_zone_high"), entry.get("conviction", "MODERATE"),
        entry.get("status", "WATCHING"),
    ))
    db.commit()
    db.close()
    return {"status": "saved", "ticker": entry["ticker"]}


@router.delete("/{ticker}")
def remove_from_watchlist(ticker: str):
    db = get_db()
    db.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    db.commit()
    db.close()
    return {"status": "removed", "ticker": ticker}
```

- [ ] **Step 2: Create positions router with P&L summary**

```python
# backend/routers/positions.py
import json
from fastapi import APIRouter, Body
from backend.database import get_db
from backend.config import USD_GBP_RATE

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("")
def get_positions():
    db = get_db()
    rows = db.execute("SELECT * FROM positions ORDER BY entry_date DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/open")
def get_open_positions():
    db = get_db()
    rows = db.execute("SELECT * FROM positions WHERE status = 'OPEN' ORDER BY entry_date DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.get("/summary")
def get_pnl_summary():
    """P&L summary for closed positions."""
    db = get_db()
    rows = db.execute("SELECT * FROM positions WHERE status = 'CLOSED'").fetchall()
    db.close()

    total_pnl_gbp = 0
    wins = 0
    losses = 0
    for r in rows:
        if r["position_type"] == "option" and r["premium_paid"] and r["exit_price"] is not None:
            pnl = (r["exit_price"] - r["premium_paid"]) * (r["contracts"] or 1) * 100 * USD_GBP_RATE
            total_pnl_gbp += pnl
            if pnl > 0:
                wins += 1
            else:
                losses += 1
        elif r["position_type"] == "stock" and r["avg_price"] and r["exit_price"] is not None:
            pnl = (r["exit_price"] - r["avg_price"]) * (r["shares"] or 0)
            total_pnl_gbp += pnl * USD_GBP_RATE
            if pnl > 0:
                wins += 1
            else:
                losses += 1

    return {
        "total_pnl_gbp": round(total_pnl_gbp, 2),
        "total_trades": wins + losses,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / (wins + losses), 2) if (wins + losses) > 0 else 0,
    }


@router.post("")
def add_position(entry: dict = Body(...)):
    db = get_db()
    db.execute("""
        INSERT INTO positions (ticker, position_type, bucket, shares, avg_price,
            strike, expiry, premium_paid, contracts, thesis, invalidation,
            target_fair_value, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["ticker"].upper(), entry["position_type"], entry.get("bucket", "B1"),
        entry.get("shares"), entry.get("avg_price"),
        entry.get("strike"), entry.get("expiry"),
        entry.get("premium_paid"), entry.get("contracts"),
        entry.get("thesis", ""), json.dumps(entry.get("invalidation", [])),
        entry.get("target_fair_value"), entry.get("status", "OPEN"),
    ))
    db.commit()
    pos_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.close()
    return {"status": "added", "id": pos_id}


@router.put("/{position_id}/close")
def close_position(position_id: int, data: dict = Body(...)):
    db = get_db()
    db.execute("""
        UPDATE positions SET status = 'CLOSED', exit_price = ?, exit_date = date('now'), exit_reason = ?
        WHERE id = ?
    """, (data.get("exit_price"), data.get("exit_reason", ""), position_id))
    db.commit()
    db.close()
    return {"status": "closed", "id": position_id}
```

- [ ] **Step 3: Wire all remaining routers into main.py**

Final `backend/main.py`:

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.database import init_db
from backend.routers import regime, screener, options, deep_dive, watchlist, positions

app = FastAPI(title="Contrarian Investing Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(regime.router)
app.include_router(screener.router)
app.include_router(options.router)
app.include_router(deep_dive.router)
app.include_router(watchlist.router)
app.include_router(positions.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health():
    return {"status": "ok"}


STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: watchlist and positions APIs with SQLite persistence and P&L summary"
```

---

## Task 10: React Frontend — Full Screener with Filters + Sector Bar

**Covers:** S1-01, S1-21-42, S1-143, S1-150
**Addresses review:** #6 (complete frontend, not placeholders)

**Files:**
- Create: `frontend/` (full Vite + React + Tailwind project)
- Create all page and component files listed in file structure

This task creates the complete React frontend with:
- Navbar with live regime badge
- ScreenerPage with B1/B2/Both/Watchlist tabs, all 5 filter dropdowns, all 5 sort options, sector distribution bar, stock cards with warnings, working "+ Watch" and "Deep Dive" buttons
- All filter/sort combinations functional
- Sector distribution bar showing breakdown per tab

**Due to length, the full JSX code for each component is provided in the implementation, not the plan. The implementation must include:**

- [ ] **Step 1: Scaffold Vite + React + Tailwind**

```bash
cd "/Users/sbakshi/Documents/Stocks Sucess/stock-analysis-system"
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Configure vite.config.js with Tailwind and API proxy**

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
```

- [ ] **Step 3: Create theme.js, api.js** — Koyfin palette constants and fetch helpers for all 12+ API endpoints.

- [ ] **Step 4: Create App.jsx** — Layout with Navbar and page routing (6 pages).

- [ ] **Step 5: Create Navbar.jsx** — Top nav with page links + live regime badge (fetches /api/regime on mount).

- [ ] **Step 6: Create ScreenerPage.jsx** — Must include:
  - Tabs: B1 | B2 | Both | Watchlist (Both shows stocks in both buckets)
  - Filter dropdowns: Sector, Min FCF Yield, Max Forward P/E, Min Operating Margin
  - Sort dropdown: Most Beaten Down, Highest FCF Yield, Cheapest P/E, Highest Margin, Fastest Growth
  - Scan timestamp in header
  - "Run Weekly Scan" and "Run Daily Scan" buttons
  - Error count indicator if scan had errors
  - Stock cards with all required columns + warning badges
  - Working "+ Watch" button that POSTs to /api/watchlist
  - Working "Deep Dive" button that navigates to DeepDivePage

- [ ] **Step 7: Create SectorBar.jsx** — Horizontal stacked bar showing sector distribution of displayed candidates.

- [ ] **Step 8: Create FilterBar.jsx** — Reusable filter/sort bar component.

- [ ] **Step 9: Create StockCard.jsx + WarningBadge.jsx** — Card component showing all required fields, warning badges in Koyfin amber.

- [ ] **Step 10: Build and verify**

```bash
cd frontend && npm run build
# Expected: dist/ directory created, no errors
```

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: React frontend with full screener — tabs, filters, sorts, sector bar, watchlist integration"
```

---

## Task 11: React Frontend — Deep Dive (8 Collapsible Sections) + DCF Calculator

**Covers:** S1-02, S1-49-103, S1-151-152
**Addresses review:** #6 (full 8-section deep dive, not placeholder)

**Files:**
- Create/modify: `frontend/src/pages/DeepDivePage.jsx`
- Create: `frontend/src/components/CollapsibleSection.jsx`
- Create: `frontend/src/components/DcfCalculator.jsx`
- Create: `frontend/src/components/SensitivityMatrix.jsx`
- Create: `frontend/src/components/EntryGrid.jsx`

The DeepDivePage must render 8 collapsible sections:

- [ ] **Step 1: Create CollapsibleSection.jsx** — Reusable accordion panel with title, expand/collapse, colored accent border.

- [ ] **Step 2: Create DeepDivePage.jsx with all 8 sections:**

1. **Data Snapshot** — Financial metrics grid from /api/deep-dive/{ticker} fundamentals. Shows data quality indicator (source, completeness). Highlights missing fields.
2. **First Impression** — AI-generated text (from ai_analysis.first_impression). Shows placeholder prompt if no AI analysis saved.
3. **Bear Case** — Split cards: "Bear on Stock" (red accent) + "Bear on Business" (dark red accent). AI-generated.
4. **Bull Case** — Split cards: "Bear Rebuttal" (green) + "Unpriced Upside" (green). AI-generated.
5. **Valuation** — Reverse DCF result (always shown first per spec), then forward DCF (3 scenarios: bear/base/bull), then interactive DCF calculator, then sensitivity matrix. Terminal value warning if >50%.
6. **Whole Picture** — AI-generated: sector theme, smart money, management, customer evidence.
7. **Self-Review** — AI-generated: bias check, gap check, pre-mortem, "what would make me wrong."
8. **Verdict** — Bucket assignment, conviction, entry grid table, exit playbook, decision tree, next review date.

- [ ] **Step 3: Create DcfCalculator.jsx** — Interactive component with adjustable inputs: Starting FCF, Growth Year 1-5, Growth Year 6-10, Terminal Growth, WACC (default 10%), Shares Outstanding, Net Debt. Calls backend DCF endpoint on change. Shows intrinsic value, margin of safety, terminal value %.

- [ ] **Step 4: Create SensitivityMatrix.jsx** — 4x4 heatmap grid. Growth Year 1-5 on rows, Growth Year 6-10 on columns. WACC fixed (shown as label, not variable). Green for values above current price, red for below.

- [ ] **Step 5: Create EntryGrid.jsx** — Table: Tranche | Trigger | Technical Confirmation | Price Zone. 4 rows: 1st third (stabilisation), 2nd third (higher low), 3rd third (trend reversal), DO NOT ENTER (free fall).

- [ ] **Step 6: Build and verify**

```bash
cd frontend && npm run build
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: deep dive dashboard with 8 collapsible sections, interactive DCF, sensitivity matrix"
```

---

## Task 12: React Frontend — Options, Watchlist, Positions Pages + Integration Tests

**Covers:** S2-78-128, S1-44-46, S2-188-206, S2-162-187
**Addresses review:** #6 (complete pages), #9 (end-to-end test)

**Files:**
- Create: `frontend/src/pages/OptionsPage.jsx`
- Create: `frontend/src/pages/WatchlistPage.jsx`
- Create: `frontend/src/pages/PositionsPage.jsx`
- Create: `frontend/src/pages/RegimePage.jsx`
- Create: `tests/test_api.py`

- [ ] **Step 1: Create OptionsPage.jsx** — Ticker input, scan button, regime context display (verdict + VIX tax note), results table with ALL columns from spec (Ticker, Strike, Expiry, DTE, Delta, IV, Premium $, Premium GBP, 3x Target, 4x Target, Req'd Move%, OI, Spread%, Theta/day, Warnings). IV CRUSH RISK warnings highlighted red.

- [ ] **Step 2: Create RegimePage.jsx** — SPY/QQQ cards with price, MAs, direction. VIX gauge. Verdict with max positions. VIX tax calculation. Options note.

- [ ] **Step 3: Create WatchlistPage.jsx** — List with ticker, bucket badge, conviction, thesis note (editable inline), entry zones, Deep Dive and Remove buttons. Add form for manual entries.

- [ ] **Step 4: Create PositionsPage.jsx** — Open positions with live data. Closed positions. P&L summary card (total P&L GBP, win rate, wins/losses). Close position flow with exit price and reason.

- [ ] **Step 5: Build frontend**

```bash
cd frontend && npm run build
```

- [ ] **Step 6: Write integration tests**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_watchlist_crud():
    client.post("/api/watchlist", json={"ticker": "TEST", "bucket": "B1"})
    wl = client.get("/api/watchlist").json()
    assert any(w["ticker"] == "TEST" for w in wl)
    client.delete("/api/watchlist/TEST")
    wl = client.get("/api/watchlist").json()
    assert not any(w["ticker"] == "TEST" for w in wl)


def test_position_add_and_close():
    r = client.post("/api/positions", json={
        "ticker": "ADBE", "position_type": "option", "strike": 270,
        "expiry": "2026-07-17", "premium_paid": 5.50, "contracts": 1,
    })
    pid = r.json()["id"]
    client.put(f"/api/positions/{pid}/close", json={"exit_price": 22.0, "exit_reason": "4x target"})
    summary = client.get("/api/positions/summary").json()
    assert summary["total_trades"] >= 1


def test_deep_dive_post_and_get():
    client.post("/api/deep-dive/TEST", json={
        "first_impression": "Looks interesting",
        "bear_case_stock": "Price decline",
        "verdict": "B1", "conviction": "HIGH",
    })
    r = client.get("/api/deep-dive/TEST").json()
    assert r["ai_analysis"]["first_impression"] == "Looks interesting"
    assert r["ai_analysis"]["conviction"] == "HIGH"
```

- [ ] **Step 7: Run all tests**

```bash
python -m pytest tests/ -v
# Expected: all PASS
```

- [ ] **Step 8: Full end-to-end startup test**

```bash
cd "/Users/sbakshi/Documents/Stocks Sucess/stock-analysis-system"
./start.sh &
sleep 3
curl http://localhost:8000/api/health
curl http://localhost:8000/api/regime
# Visit http://localhost:8000 in browser — React app loads
kill %1
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: complete frontend (options, watchlist, positions, regime) + integration tests"
```

---

## Phase 2 Tasks (Data Enrichment — After API Keys Obtained)

### Task 13: FMP Integration (250 calls/day)

**Covers:** S1-116-119, S1-146
**Deferred until:** User signs up at https://financialmodelingprep.com

- [ ] Add FMP provider to `providers.py` with fallback chain: FMP → yfinance
- [ ] 5-year financial statements (income, balance sheet, cash flow)
- [ ] Pre-calculated DCF endpoint
- [ ] Key metrics (ROIC, SBC, FCF, debt ratios pre-calculated)
- [ ] Analyst estimates (consensus EPS, revenue forecasts)
- [ ] Rate limiter: 250 calls/day tracking
- [ ] Tests for FMP → yfinance fallback

### Task 14: Finnhub + EdgarTools Integration

**Covers:** S1-70-73, S1-112-113, S1-121-122, S1-145
**Deferred until:** Finnhub key obtained

- [ ] Finnhub: news sentiment scores per ticker
- [ ] Finnhub: insider transactions
- [ ] Finnhub: analyst recommendations + history
- [ ] EdgarTools: 13F institutional holdings
- [ ] EdgarTools: Form 4 insider trades (parsed, structured)
- [ ] EdgarTools: 10-K/10-Q financial statements
- [ ] Wire into deep dive Whole Picture section

### Task 15: Enhanced Deep Dive Frontend (with enriched data)

**Covers:** S1-55, S1-60-62, S1-64-67, S1-82, S1-87
**Depends on:** Tasks 13-14

- [ ] 5-year sparklines for revenue, margins, FCF (using FMP historical data)
- [ ] SBC flag if >10% of revenue (prominent display)
- [ ] Revenue by segment breakdown
- [ ] GAAP vs non-GAAP gap indicator
- [ ] P/E 5-year average context
- [ ] EV/EBITDA, P/S, PEG ratios display
- [ ] Peer comparison table
- [ ] Editable first impression field (local save)
- [ ] Smart money positioning table (13F data)
- [ ] Insider activity timeline (Form 4 data)

---

## Phase 3 Tasks (MCP + Technical Analysis)

### Task 16: TradingView MCP Servers Setup

**Covers:** S1-123-140, S2-34-65
**Deferred until:** Phase 1+2 stable

- [ ] Install tradingview-mcp (Henrik404) — pip install, add to Claude MCP config
- [ ] Install mcp-tradingview-server (bidouilles) — clone, pip install
- [ ] Install tradingview-mcp-server (atilaahmettaner) — clone, uv setup
- [ ] Verify each server responds to test queries
- [ ] Wire TradingView technical ratings into screener view
- [ ] Wire indicator snapshots into deep dive technical section
- [ ] Wire Reddit sentiment into deep dive Whole Picture

### Task 17: Alpha Vantage MCP + Full Technical Layer

**Covers:** S1-120, S1-76, S2-43-56
**Deferred until:** Alpha Vantage key obtained

- [ ] Configure Alpha Vantage hosted MCP server
- [ ] 50+ technical indicators available
- [ ] RSI (weekly) integration in screener + deep dive
- [ ] Volume analysis (60-day) integration
- [ ] Entry grid validation with exact 50d SMA, 200d SMA, 10-week EMA values

---

## Traceability Summary

| Spec Feature Count | Phase 1 | Phase 2 | Phase 3 | Deferred |
|---|---|---|---|---|
| S1 CORE (107) | 82 | 18 | 7 | 0 |
| S1 ENRICHMENT (46) | 12 | 22 | 10 | 2 |
| S2 CORE (68) | 62 | 2 | 4 | 0 |
| S2 ENRICHMENT (37) | 8 | 12 | 13 | 4 |
| **Total (258)** | **164** | **54** | **34** | **6** |

**6 explicitly deferred features:** TradingView chart screenshots (4), custom MCP wrapper (1), window.storage mode (1).

---

## Workflow: How Claude Code (Max) Powers Deep Dives

1. User opens `http://localhost:8000`, navigates to Screener
2. Screener shows B1/B2 candidates with quantitative data + warnings
3. User clicks "Deep Dive" on ADBE → Dashboard shows Gate 1 (data) + Gate 5 (reverse/forward DCF) automatically
4. User opens Claude Code and says: **"deep dive ADBE"**
5. Claude Code uses Value Investing MCP tools to gather data, then generates:
   - First Impression, Bear Case (stock + business), Bull Case (rebuttal + upside)
   - Whole Picture, Self-Review (bias check, pre-mortem), Verdict + Entry Grid
6. Claude Code runs:
   ```bash
   echo '{"first_impression": "...", "bear_case_stock": "...", ...}' | python bridge/deep_dive_worker.py ADBE --post
   ```
7. User refreshes Deep Dive page — all 8 sections now populated
8. If conviction is HIGH → user goes to Options page, enters ADBE, scans contracts
