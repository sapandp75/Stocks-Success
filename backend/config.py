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
