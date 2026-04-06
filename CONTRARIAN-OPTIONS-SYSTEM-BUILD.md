# Contrarian Options Trading System — Claude Code Build Instructions

## What This Is

A complete options-based trading system for a **contrarian quality investor** who:
- Risks £500 per trade (premium = stop loss, written off at purchase)
- Targets 4x return (£500 → £2,000)
- Holds 2 weeks to 3 months max
- Runs 3-5 concurrent positions, max £5,000 total deployed
- Only trades Bucket 1 (contrarian value) setups: quality companies beaten down by fear, not fundamentals

The system has **three layers**:
1. **MCP servers** — live options chains, stock data, Greeks, and screening via Yahoo Finance
2. **Options scanner CLI tool** — filters contracts matching the system's exact criteria
3. **Market regime filter** — prevents entries during dangerous market conditions

---

## PHASE 1: Install MCP Servers

### 1A — Install mcp-optionsflow (Options Analysis)

This gives Claude access to live options chains, Greeks calculations, and strategy evaluation.

```bash
# Clone the repo
git clone https://github.com/twolven/mcp-optionsflow.git
cd mcp-optionsflow

# Install Python dependencies (requires Python 3.12+)
pip install -r requirements.txt
# Dependencies: mcp, yfinance, pandas, numpy, scipy

# Test it runs
python optionsflow.py
```

**Available tool:** `analyze_basic_strategies`
- Input: symbol, strategy type (ccs/pcs/csp/cc), expiration_date, delta_target, width_pct
- Returns: strikes, credit/premium, max loss, max profit, probability of profit, risk/reward ratio, Greeks

### 1B — Install mcp-stockflow (Stock Data + Options Chains)

This is the **companion server** — gives Claude access to real-time stock prices, fundamentals, historical data, AND raw options chain data.

```bash
git clone https://github.com/twolven/mcp-stockflow.git
cd mcp-stockflow
pip install -r requirements.txt
# Dependencies: mcp, yfinance
```

**Available tools:**
- `get-stock-data` — current price, volume, market cap, P/E, 52-week range
- `get-historical-data` — OHLC, moving averages, technical indicators
- `get-options-chain` — full chain with strikes, premiums, Greeks, IV, volume, OI

### 1C — Install mcp-stockscreen (Stock Screener)

Optional but useful — screens stocks by technical and fundamental criteria.

```bash
git clone https://github.com/twolven/mcp-stockscreen.git
cd mcp-stockscreen
pip install -r requirements.txt
```

### 1D — Install TradingView MCP Servers (Technical Analysis)

Three free TradingView MCP servers for different aspects of technical analysis. All free, no TradingView account needed for the first two.

#### TV Server 1: tradingview-mcp (Screener + Technical Ratings)
Screens 11,000+ stocks by 75+ metrics including RSI, MACD, volume, TradingView's STRONG BUY/SELL ratings. One-line install.

```bash
pip install tradingview-mcp
# Or: uvx tradingview-mcp
```
**No API key, no TradingView account. Completely free.**
**Use for options system:** Screen B1 candidates for oversold conditions (RSI <30 weekly = first-tranche hunting ground). Validate seller exhaustion before deploying £500 on a contract.

#### TV Server 2: mcp-tradingview-server (Full Indicator Snapshots + OHLCV)
Pulls every TradingView indicator for a single stock in one call — all MAs, RSI, MACD, Stochastic, ADX, Bollinger, pivot points, plus OHLCV candle data.

```bash
git clone https://github.com/bidouilles/mcp-tradingview-server.git
cd mcp-tradingview-server
pip install -e .
```
**No API key, no TradingView account. Completely free.**
**Use for options system:** Get exact 50d SMA, 200d SMA, 10-week EMA values for entry grid. Confirm stabilisation signals (narrowing ranges, volume drying up) before buying any options contract.

#### TV Server 3: tradingview-mcp-server (Advanced — Backtesting + Sentiment)
30+ tools including Reddit sentiment analysis, strategy backtesting, market snapshots, combined technical + sentiment signals.

```bash
git clone https://github.com/atilaahmettaner/tradingview-mcp.git
cd tradingview-mcp
uv run tradingview-mcp
```
**No API key. Free and open source.**
**Use for options system:** Reddit sentiment on B1 candidates — extreme bearishness = your contrarian entry signal. Market snapshot for quick regime checks. Backtest mean-reversion on candidates.

#### TV Server 4 (Optional): tradingview-chart-mcp (Visual Chart Screenshots)
Gets actual TradingView chart images that Claude can visually interpret. Requires a TradingView account (free tier works) + ChromeDriver.

```bash
git clone https://github.com/ertugrul59/tradingview-chart-mcp.git
cd tradingview-chart-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Requires: TRADINGVIEW_SESSION_ID and TRADINGVIEW_SESSION_ID_SIGN in .env
```
**Requires TradingView account + ChromeDriver. More complex setup.**
**Use for options system:** Visual confirmation of base formation before committing £500. Claude sees the actual weekly chart.

### 1E — Configure Claude Code / Claude Desktop

Add ALL servers to your Claude configuration file.

**For Claude Desktop** — edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "optionsflow": {
      "command": "python",
      "args": ["/full/path/to/mcp-optionsflow/optionsflow.py"]
    },
    "stockflow": {
      "command": "python",
      "args": ["/full/path/to/mcp-stockflow/stockflow.py"]
    },
    "stockscreen": {
      "command": "python",
      "args": ["/full/path/to/mcp-stockscreen/stockscreen.py"]
    },
    "tradingview-screener": {
      "command": "uvx",
      "args": ["tradingview-mcp"]
    },
    "tradingview-indicators": {
      "command": "/full/path/to/mcp-tradingview-server/.venv/bin/python",
      "args": ["/full/path/to/mcp-tradingview-server/src/tradingview_server.py"],
      "cwd": "/full/path/to/mcp-tradingview-server"
    },
    "tradingview-advanced": {
      "command": "uv",
      "args": ["run", "tradingview-mcp"],
      "cwd": "/full/path/to/tradingview-mcp"
    }
  }
}
```

**For Claude Code (terminal)** — add to `.claude/settings.json` or use `claude mcp add`:

```bash
claude mcp add optionsflow python /full/path/to/mcp-optionsflow/optionsflow.py
claude mcp add stockflow python /full/path/to/mcp-stockflow/stockflow.py
claude mcp add stockscreen python /full/path/to/mcp-stockscreen/stockscreen.py
claude mcp add tradingview-screener -- uvx tradingview-mcp
```

**Replace `/full/path/to/` with actual paths on your machine.**

### 1F — Verify Installation

After configuring, test each server by asking Claude:

```
"Use stockflow to get the current stock data for ADBE"
"Use stockflow to get the options chain for ADBE expiring in July 2026"
"Use optionsflow to analyze a cash-secured put on ADBE expiring 2026-07-17 with delta target 0.3"
"Use tradingview-screener to screen US stocks with RSI below 30"
"Use tradingview-indicators to get all indicators for ADBE on the weekly timeframe"
"Use tradingview-advanced to get Reddit sentiment for ADBE"
```

If all servers return data, your MCP layer is working.

---

## PHASE 2: Build the Options Scanner CLI

The MCP servers give Claude raw data access. Now we need a **purpose-built scanner** that filters contracts against the system's specific criteria.

### 2A — Create the Scanner Script

Create a Python script called `contrarian_options_scanner.py` that:

1. **Takes a list of ticker symbols as input** (the B1 candidates)
2. **For each ticker, pulls the full options chain** via yfinance
3. **Filters contracts matching ALL of these criteria:**
   - Expiry: 60-120 days from today
   - Type: Calls only (for directional B1 recovery plays)
   - Strike: 5-10% OTM (above current price)
   - Delta: 0.25 to 0.40 (calculate using Black-Scholes if yfinance doesn't provide)
   - Open interest: > 500 contracts
   - Bid-ask spread: < 10% of mid-price
   - Premium (ask price): ≤ $7.00 per contract (≈ £500 for 1 contract at $625)
4. **For each qualifying contract, calculates:**
   - Current premium cost in GBP (use a configurable USD/GBP rate, default 0.80)
   - 3x target price (premium × 3)
   - 4x target price (premium × 4)
   - Required underlying move to hit 4x (approximate using delta)
   - Days to expiry
   - Implied volatility
   - Theta decay per day in GBP
5. **Outputs a ranked table** sorted by: best risk/reward ratio first (lowest required underlying move for 4x return)
6. **Flags warnings:**
   - Earnings date within 14 days of expiry → "⚠️ IV CRUSH RISK"
   - Open interest < 1000 → "⚠️ LOW LIQUIDITY"
   - Bid-ask spread > 5% → "⚠️ WIDE SPREAD"

### 2B — Scanner Implementation Details

```python
"""
Contrarian Options Scanner
Filters options contracts for a B1 contrarian recovery system.

Usage:
  python contrarian_options_scanner.py ADBE TTD CRM QCOM
  python contrarian_options_scanner.py --watchlist watchlist.txt
  python contrarian_options_scanner.py ADBE --min-delta 0.25 --max-delta 0.40 --max-premium 7.00

Output:
  Terminal table + optional CSV export
"""

# Required packages:
# pip install yfinance pandas numpy scipy tabulate

import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta
import argparse
import json

# --- SYSTEM PARAMETERS (match your trading rules) ---
SYSTEM_PARAMS = {
    "min_dte": 60,           # Minimum days to expiry
    "max_dte": 120,          # Maximum days to expiry
    "min_delta": 0.25,       # Minimum delta
    "max_delta": 0.40,       # Maximum delta
    "min_oi": 500,           # Minimum open interest
    "max_spread_pct": 0.10,  # Maximum bid-ask spread as % of mid price
    "max_premium_usd": 7.00, # Maximum premium per contract in USD
    "usd_gbp_rate": 0.80,    # USD to GBP conversion rate
    "risk_per_trade_gbp": 500,# Fixed risk per trade in GBP
    "target_multiple": 4,    # Target return multiple
    "option_type": "calls",  # calls for B1 recovery plays
}

# --- CORE FUNCTIONS TO IMPLEMENT ---

def get_options_chain(ticker: str) -> pd.DataFrame:
    """
    Pull full options chain from yfinance.
    Filter to expiries within min_dte to max_dte range.
    Return DataFrame with: strike, bid, ask, lastPrice, volume, 
    openInterest, impliedVolatility, expiry_date, dte
    """
    pass

def calculate_delta(S, K, T, r, sigma, option_type="call"):
    """
    Black-Scholes delta calculation.
    S = current stock price
    K = strike price  
    T = time to expiry in years
    r = risk-free rate (use 0.05 as default)
    sigma = implied volatility
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    if option_type == "call":
        return norm.cdf(d1)
    else:
        return norm.cdf(d1) - 1

def calculate_theta(S, K, T, r, sigma):
    """
    Black-Scholes theta (daily decay in dollars).
    """
    pass

def filter_contracts(chain: pd.DataFrame, stock_price: float) -> pd.DataFrame:
    """
    Apply ALL system filters:
    1. Strike 5-10% OTM
    2. Delta 0.25-0.40
    3. OI > 500
    4. Spread < 10%
    5. Premium <= $7.00
    """
    pass

def check_earnings_proximity(ticker: str, expiry_date: str) -> bool:
    """
    Check if earnings date falls within 14 days of option expiry.
    Returns True if IV crush risk exists.
    """
    pass

def calculate_required_move(delta: float, premium: float, target_multiple: int) -> float:
    """
    Approximate the underlying stock move needed for the option 
    to reach target_multiple × premium.
    
    Simple approximation: required_move ≈ (target_premium - current_premium) / delta
    More accurate: use Black-Scholes repricing at target stock price
    """
    pass

def scan_tickers(tickers: list) -> pd.DataFrame:
    """
    Main scanner function.
    For each ticker:
    1. Get current price
    2. Pull options chain
    3. Filter contracts
    4. Calculate metrics
    5. Rank by risk/reward
    Return combined DataFrame of all qualifying contracts.
    """
    pass

def format_output(results: pd.DataFrame) -> str:
    """
    Format results as a clean terminal table using tabulate.
    Columns:
    | Ticker | Strike | Expiry | DTE | Delta | IV | Premium($) | Premium(£) | 
    | 3x Target | 4x Target | Req'd Move% | OI | Spread% | Warnings |
    """
    pass

# --- CLI ENTRY POINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contrarian Options Scanner")
    parser.add_argument("tickers", nargs="*", help="Stock tickers to scan")
    parser.add_argument("--watchlist", help="Path to watchlist file (one ticker per line)")
    parser.add_argument("--min-delta", type=float, default=0.25)
    parser.add_argument("--max-delta", type=float, default=0.40)
    parser.add_argument("--max-premium", type=float, default=7.00)
    parser.add_argument("--csv", help="Export results to CSV file")
    args = parser.parse_args()
    
    # Build ticker list
    tickers = args.tickers
    if args.watchlist:
        with open(args.watchlist) as f:
            tickers = [line.strip() for line in f if line.strip()]
    
    # Override params if specified
    SYSTEM_PARAMS["min_delta"] = args.min_delta
    SYSTEM_PARAMS["max_delta"] = args.max_delta
    SYSTEM_PARAMS["max_premium_usd"] = args.max_premium
    
    # Run scanner
    results = scan_tickers(tickers)
    print(format_output(results))
    
    if args.csv:
        results.to_csv(args.csv, index=False)
        print(f"\nResults exported to {args.csv}")
```

### 2C — Make It an MCP Server (Optional but Recommended)

Once the scanner works as a CLI tool, wrap it as an MCP server so Claude Code can call it directly:

```python
"""
contrarian_options_mcp.py
MCP server wrapper for the contrarian options scanner.
"""
from mcp import Server
import json

app = Server("contrarian-options")

@app.tool("scan_b1_options")
async def scan_b1_options(tickers: list[str], max_premium: float = 7.0) -> str:
    """
    Scan options chains for B1 contrarian recovery plays.
    Returns qualifying contracts sorted by risk/reward.
    """
    results = scan_tickers(tickers)
    return results.to_json(orient="records")

@app.tool("get_contract_detail")
async def get_contract_detail(ticker: str, strike: float, expiry: str) -> str:
    """
    Get detailed analysis of a specific options contract.
    Returns: Greeks, P&L scenarios, required move for 2x/3x/4x.
    """
    pass

@app.tool("check_regime")
async def check_regime() -> str:
    """
    Quick market regime check: SPY vs 50d/200d, VIX level, breadth.
    Returns: DEPLOY / CAUTIOUS / DEFENSIVE / CASH
    """
    pass
```

Add to Claude config:
```json
"contrarian-options": {
  "command": "python",
  "args": ["/full/path/to/contrarian_options_mcp.py"]
}
```

---

## PHASE 3: Build the Market Regime Filter

The regime filter is **Gate 0** — checked BEFORE any individual stock analysis. No new positions in DEFENSIVE or CASH mode.

### 3A — Regime Check Script

Create `market_regime.py` that:

1. **Pulls current data for:**
   - SPY: price vs 20d EMA, 50d SMA, 200d SMA (use yfinance)
   - QQQ: same
   - VIX: current level
   - Market breadth: % of S&P 500 stocks above 200d SMA (web scrape or estimate)

2. **Applies the direction matrix:**
   ```
   Price > 20d > 50d > 200d              → 🟢 FULL UPTREND (DEPLOY)
   Price > 50d > 200d, price < 20d        → 🟢🟡 PULLBACK IN UPTREND (DEPLOY selectively)
   Price < 20d, price < 50d, price > 200d → 🟡 TREND WEAKENING (CAUTIOUS)
   Price < 20d < 50d, 50d still > 200d    → 🟡🔴 CORRECTION IN UPTREND (CAUTIOUS — max 2 new positions)
   Price < 20d < 50d, 50d approaching 200d → 🔴 POTENTIAL TREND CHANGE (DEFENSIVE — no new positions)
   Price < 20d < 50d < 200d               → 🔴 FULL DOWNTREND (CASH — no new positions)
   ```

3. **VIX overlay:**
   - VIX < 20: Green
   - VIX 20-25: Amber (elevated but manageable — premiums expensive, factor into R/R)
   - VIX > 25: Red (high fear — only deploy if regime is CAUTIOUS or better with strong B1 thesis)
   - VIX > 35: Cash mode override regardless of other signals

4. **Returns a single verdict:**
   ```
   DEPLOY      — All signals green, initiate up to 5 positions
   CAUTIOUS    — Mixed signals, max 2 new positions, be selective
   DEFENSIVE   — No new positions, review existing only
   CASH        — Close weak positions, preserve capital
   ```

5. **Options-specific overlay:**
   - In CAUTIOUS/DEPLOY: note that elevated VIX = expensive premiums → need larger underlying move for 4x
   - Calculate the "VIX tax": how much extra premium you're paying vs VIX at 15 (historical calm)
   - If VIX tax makes 4x mathematically implausible on delta 0.25-0.40 contracts → flag it

### 3B — Implementation

```python
"""
market_regime.py
Gate 0 regime filter for the Contrarian Options System.

Usage:
  python market_regime.py
  python market_regime.py --json  # machine-readable output
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def get_ma_data(ticker: str) -> dict:
    """
    Pull price and calculate 20d EMA, 50d SMA, 200d SMA.
    Return: {price, ema20, sma50, sma200, direction}
    """
    data = yf.download(ticker, period="1y", interval="1d", progress=False)
    price = data["Close"].iloc[-1]
    ema20 = data["Close"].ewm(span=20).mean().iloc[-1]
    sma50 = data["Close"].rolling(50).mean().iloc[-1]
    sma200 = data["Close"].rolling(200).mean().iloc[-1]
    
    # Direction matrix
    if price > ema20 > sma50 > sma200:
        direction = "FULL_UPTREND"
    elif price > sma50 and price > sma200 and price < ema20:
        direction = "PULLBACK_IN_UPTREND"
    elif price < ema20 and price < sma50 and price > sma200:
        direction = "TREND_WEAKENING"
    elif price < ema20 and price < sma50 and sma50 > sma200:
        direction = "CORRECTION_IN_UPTREND"
    elif price < ema20 and price < sma50 and abs(sma50 - sma200) / sma200 < 0.02:
        direction = "POTENTIAL_TREND_CHANGE"
    elif price < ema20 and price < sma50 and price < sma200:
        direction = "FULL_DOWNTREND"
    else:
        direction = "MIXED"
    
    return {
        "ticker": ticker,
        "price": round(float(price), 2),
        "ema20": round(float(ema20), 2),
        "sma50": round(float(sma50), 2),
        "sma200": round(float(sma200), 2),
        "direction": direction,
    }

def get_vix() -> float:
    """Get current VIX level."""
    vix = yf.download("^VIX", period="5d", interval="1d", progress=False)
    return round(float(vix["Close"].iloc[-1]), 2)

def determine_regime(spy: dict, qqq: dict, vix: float) -> dict:
    """
    Combine SPY direction, QQQ direction, and VIX into a single regime verdict.
    """
    # VIX override
    if vix > 35:
        return {"verdict": "CASH", "reason": f"VIX at {vix} — extreme fear, capital preservation mode"}
    
    # Score the directions
    direction_scores = {
        "FULL_UPTREND": 4,
        "PULLBACK_IN_UPTREND": 3,
        "TREND_WEAKENING": 2,
        "CORRECTION_IN_UPTREND": 1.5,
        "MIXED": 1.5,
        "POTENTIAL_TREND_CHANGE": 1,
        "FULL_DOWNTREND": 0,
    }
    
    spy_score = direction_scores.get(spy["direction"], 1.5)
    qqq_score = direction_scores.get(qqq["direction"], 1.5)
    avg_score = (spy_score + qqq_score) / 2
    
    # VIX adjustment
    if vix > 25:
        avg_score -= 0.5
    elif vix < 20:
        avg_score += 0.25
    
    # Verdict
    if avg_score >= 3:
        verdict = "DEPLOY"
        max_positions = 5
    elif avg_score >= 2:
        verdict = "CAUTIOUS"
        max_positions = 2
    elif avg_score >= 1:
        verdict = "DEFENSIVE"
        max_positions = 0
    else:
        verdict = "CASH"
        max_positions = 0
    
    return {
        "verdict": verdict,
        "max_new_positions": max_positions,
        "spy_direction": spy["direction"],
        "qqq_direction": qqq["direction"],
        "vix": vix,
        "score": round(avg_score, 2),
        "options_note": _options_note(vix, verdict),
    }

def _options_note(vix: float, verdict: str) -> str:
    """Generate options-specific guidance based on VIX and regime."""
    if verdict in ("DEFENSIVE", "CASH"):
        return "NO new options positions. Cash is the position."
    if vix > 25:
        return (f"VIX at {vix} — premiums are 30-50% above normal. "
                f"Factor this into R/R: you need a larger move for 4x. "
                f"Only deploy on highest-conviction B1 setups.")
    if vix > 20:
        return (f"VIX at {vix} — premiums moderately elevated. "
                f"Acceptable for B1 plays where fear is narrative, not fundamental.")
    return f"VIX at {vix} — premiums at normal levels. Standard contract selection applies."

if __name__ == "__main__":
    import sys
    import json as json_lib
    
    spy = get_ma_data("SPY")
    qqq = get_ma_data("QQQ")
    vix = get_vix()
    regime = determine_regime(spy, qqq, vix)
    
    if "--json" in sys.argv:
        print(json_lib.dumps({"spy": spy, "qqq": qqq, "regime": regime}, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"  MARKET REGIME CHECK — {datetime.now().strftime('%Y-%m-%d')}")
        print(f"{'='*50}")
        print(f"  SPY: ${spy['price']} | {spy['direction']}")
        print(f"    20d EMA: ${spy['ema20']} | 50d SMA: ${spy['sma50']} | 200d SMA: ${spy['sma200']}")
        print(f"  QQQ: ${qqq['price']} | {qqq['direction']}")
        print(f"    20d EMA: ${qqq['ema20']} | 50d SMA: ${qqq['sma50']} | 200d SMA: ${qqq['sma200']}")
        print(f"  VIX: {vix}")
        print(f"{'='*50}")
        print(f"  VERDICT: {regime['verdict']}")
        print(f"  Max new positions: {regime['max_new_positions']}")
        print(f"  {regime['options_note']}")
        print(f"{'='*50}\n")
```

---

## PHASE 4: The Complete Workflow (How It All Connects)

### Daily Workflow (2 minutes)

```bash
# 1. Check regime (Gate 0)
python market_regime.py

# If DEPLOY or CAUTIOUS → proceed
# If DEFENSIVE or CASH → stop. No new trades.

# 2. Check if any open positions hit 3x or 4x target
# (Manual check on broker — or build a position tracker, see Phase 5)
```

### Weekly Workflow (Sunday, 30 minutes)

```bash
# 1. Regime check
python market_regime.py

# 2. TradingView technical scan — find oversold B1 candidates
# Ask Claude: "Use tradingview-screener to find US stocks with RSI below 30 
#              and operating margin above 20%"

# 3. Scan watchlist for qualifying options contracts
python contrarian_options_scanner.py ADBE TTD CRM QCOM INTU --csv results.csv

# 4. Get TradingView indicator snapshots for top candidates
# Ask Claude: "Use tradingview-indicators to get weekly indicators for ADBE — 
#              I need RSI, 50d SMA, 200d SMA, volume trend"

# 5. Check Reddit sentiment (contrarian signal)
# Ask Claude: "Use tradingview-advanced to get Reddit sentiment for ADBE and TTD"
# Extreme bearishness on a quality name = your entry zone

# 6. Review results with Claude
# "Here are this week's scanner results. Which contracts 
#  have the best R/R given the current regime and each stock's 
#  B1 thesis status?"

# 7. For any contract you're considering, run the deep analysis:
# "Use optionsflow to analyze ADBE calls expiring 2026-07-17 
#  with delta target 0.35"
```

### Entry Workflow (When deploying capital)

```
1. ✅ Regime = DEPLOY or CAUTIOUS
2. ✅ Stock passes Gate 1-5 deep dive (fundamentals)
3. ✅ Technical analysis shows stabilisation (volume drying up, narrowing ranges)
4. ✅ Scanner found qualifying contract (60-120 DTE, delta 0.25-0.40, OI >500, premium ≤$7)
5. ✅ No earnings within 14 days of expiry
6. ✅ Total deployed < £5,000 and < 5 positions
7. → Execute: buy 1 contract at limit order (mid-price or below)
8. → Set calendar reminders: 3x target, 4x target, 21 DTE time stop
```

### Exit Workflow

```
EXIT 1 — PROFIT TARGET:
  Contract hits 3x → sell half
  Contract hits 4x → sell rest
  
EXIT 2 — THESIS BROKEN:
  Fundamental thesis changes (revenue declining, margin collapse) → sell immediately

EXIT 3 — TIME STOP:
  < 21 DTE and below 2x → sell. Theta accelerates, don't hope.
  
EXIT 4 — REGIME CHANGE:
  Market moves to DEFENSIVE/CASH → review all positions, close weak ones

NEVER:
  Hold through earnings (IV crush)
  Add to a losing option position
  Let a position expire worthless hoping for miracle
```

---

## PHASE 5: Position Tracker (Optional Enhancement)

Build a simple JSON-based position tracker that:

```python
"""
positions.py — Simple position tracker

Stores: ticker, strike, expiry, entry_date, premium_paid, premium_gbp,
        target_3x, target_4x, thesis, status (OPEN/CLOSED), exit_price, exit_reason

Commands:
  python positions.py add ADBE 270C 2026-07-17 5.50
  python positions.py list
  python positions.py check  # checks current prices vs targets
  python positions.py close ADBE 270C 2026-07-17 --price 22.00 --reason "4x target hit"
  python positions.py summary  # P&L summary of all closed trades
"""
```

Store positions in `positions.json` — simple, portable, no database needed.

---

## PHASE 6: Integration with Claude Code Sessions

### CLAUDE.md System Prompt

Create a `CLAUDE.md` in your project root that gives Claude Code context for every session:

```markdown
# Contrarian Options System — Claude Code Context

## Who I Am
Contrarian quality investor. I buy options on beaten-down quality companies (B1 = broken stock, not broken business). £500 risk per trade, 4x target, 3-month max hold.

## Available Tools
- `mcp-optionsflow` — options strategy analysis (Greeks, P&L, probabilities)
- `mcp-stockflow` — stock data, historical prices, raw options chains
- `mcp-stockscreen` — stock screening by technical/fundamental criteria
- `tradingview-screener` — screen 11,000+ stocks by 75+ TradingView metrics (RSI, MACD, volume, ratings)
- `tradingview-indicators` — full TradingView indicator snapshots for any stock (all MAs, RSI, MACD, Stochastic, ADX, pivots)
- `tradingview-advanced` — Reddit sentiment, strategy backtesting, market snapshots, combined signals
- `contrarian_options_scanner.py` — custom scanner for B1 options plays
- `market_regime.py` — Gate 0 regime filter
- `positions.py` — position tracker

## Workflow Order
1. Run `market_regime.py` → check regime (DEPLOY/CAUTIOUS/DEFENSIVE/CASH)
2. If DEPLOY or CAUTIOUS → scan watchlist with `contrarian_options_scanner.py`
3. For promising contracts → deep dive the underlying (Gates 1-5)
4. Validate contract with `optionsflow` for Greeks and probabilities
5. Execute entry if all criteria met

## Trading Rules (Non-Negotiable)
- Premium = stop loss. £500 max per trade. Written off at purchase.
- Exit: half at 3x, rest at 4x. Time stop at 21 DTE if below 2x.
- Never hold through earnings. Never add to losers. Max 5 positions.
- DEFENSIVE/CASH regime = NO new positions, period.
- Contract criteria: 60-120 DTE, delta 0.25-0.40, OI >500, spread <10%, premium ≤$7

## My Kryptonite (Stop Me From Doing This)
- Breakout/momentum entries — NEVER works for me
- Tight stop losses — I get shaken out of winners
- Overtrading from boredom — cash IS a position
- Selling winners too early — hold for the thesis, not the drawdown
- Chasing premium on far OTM lottery tickets (delta <0.15)

## Current Watchlist (B1 Candidates)
- ADBE ($242, -43% from high) — AI disruption fear, record revenue, 10x fwd PE
- TTD ($21, -75%) — ad-tech selloff, growth deceleration, OpenAI partnership pending
- CRM ($220, -31%) — SaaS selloff, controls customer data, Agentforce platform
- INTU ($440, -35%) — tax/accounting AI fears, sticky product, needs deep dive
- QCOM ($125, -39%) — mobile cycle + China fears, on-device AI catalyst, earnings Apr 30

## Koyfin Palette (for any visual outputs)
bg: #f0f1f3, cards: #ffffff, hover: #f7f8fa, borders: #e2e4e8
green: #00a562, red: #e5484d, amber: #d97b0e
No black backgrounds. No pure white backgrounds.
```

---

## PHASE 7: Testing Checklist

Before going live, verify each component:

- [ ] `market_regime.py` runs and returns correct verdict
- [ ] `contrarian_options_scanner.py ADBE` returns qualifying contracts (or correctly shows none)
- [ ] `mcp-stockflow` responds to `get-stock-data` and `get-options-chain` calls in Claude
- [ ] `mcp-optionsflow` responds to `analyze_basic_strategies` calls in Claude
- [ ] `tradingview-screener` returns oversold US stocks when filtered by RSI <30
- [ ] `tradingview-indicators` returns full indicator snapshot for ADBE on weekly timeframe
- [ ] `tradingview-advanced` returns Reddit sentiment score for a B1 candidate
- [ ] Scanner correctly flags earnings proximity warnings
- [ ] Scanner correctly filters by delta, OI, spread, and premium limits
- [ ] Position tracker can add, list, check, and close positions
- [ ] `CLAUDE.md` is in project root and Claude Code reads it on session start

---

## File Structure

```
contrarian-options-system/
├── CLAUDE.md                          # Claude Code system prompt
├── README.md                          # This file
├── market_regime.py                   # Gate 0 — regime filter
├── contrarian_options_scanner.py      # Options contract scanner
├── contrarian_options_mcp.py          # MCP wrapper (optional)
├── positions.py                       # Position tracker
├── positions.json                     # Position data store
├── watchlist.txt                      # Ticker watchlist
├── mcp-optionsflow/                   # Cloned MCP server
│   ├── optionsflow.py
│   └── requirements.txt
├── mcp-stockflow/                     # Cloned MCP server
│   ├── stockflow.py
│   └── requirements.txt
├── mcp-stockscreen/                   # Cloned MCP server (optional)
│   ├── stockscreen.py
│   └── requirements.txt
├── mcp-tradingview-server/            # TradingView indicators + OHLCV
│   ├── src/tradingview_server.py
│   └── requirements.txt
└── tradingview-mcp/                   # TradingView advanced (sentiment + backtesting)
    └── (installed via uv)
```

*Note: `tradingview-mcp` screener (Henrik404) is pip-installed globally, no local folder needed.*

---

## Key Dependencies

```
# requirements.txt for the custom tools
yfinance>=0.2.36
pandas>=2.0
numpy>=1.24
scipy>=1.11
tabulate>=0.9
mcp>=1.0  # only if building custom MCP server wrapper
tradingview-mcp  # TradingView screener (Henrik404)
tradingview-scraper  # Used by mcp-tradingview-server (bidouilles)
edgartools>=5.28  # SEC EDGAR — 13F, insider trades, financials (FREE, no key)
```

---

## Important Notes

1. **This is NOT a black box.** The system identifies candidates and contracts — YOU make the final decision. Every trade requires a thesis.

2. **Yahoo Finance data has limitations.** Options data may be delayed 15-20 minutes. Greeks are calculated, not live-streamed. Volume and OI are end-of-day snapshots. For execution, always verify on your broker's platform.

3. **Start paper trading.** Run the system for 4-6 weeks tracking positions without real money. Verify the 4x targets are achievable on the contracts the scanner surfaces.

4. **The regime filter is the most important component.** It's what stops you from deploying into falling markets. Trust it even when you feel FOMO.

5. **Options are leveraged instruments.** The £500 per trade is designed to be money you can afford to lose entirely. Never risk more than your system allows.

---

*Educational purposes only. Not financial advice. All investment decisions are yours alone.*
