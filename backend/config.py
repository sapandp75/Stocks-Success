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

# Research Intelligence Layer
RESEARCH_CONFIG = {
    "cache_ttl_hours": 6,
    "max_articles_per_ticker": 5,
    "max_transcript_age_days": 90,
    "digest_lookback_days": 7,
    "sentiment_staleness_hours": 12,
}

SA_RSS_TEMPLATE = "https://seekingalpha.com/api/sa/combined/{ticker}.xml"

SUBSTACK_FEEDS = [
    {"name": "Yet Another Value Blog", "url": "https://yetanothervalueblog.substack.com/feed"},
    {"name": "Compounding Quality", "url": "https://www.compoundingquality.net/feed"},
    {"name": "TSOH Investment Research", "url": "https://thescienceofhitting.com/feed"},
    {"name": "Net Interest", "url": "https://www.netinterest.co/feed"},
]

CNBC_EARNINGS_RSS = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"

# Technicals config
TECHNICALS_CONFIG = {
    "cache_ttl_hours": 1,
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bollinger_period": 20,
    "bollinger_std": 2,
    "adx_period": 14,
    "volume_avg_period": 20,
}

# Enrichment cache TTLs
ENRICHMENT_CONFIG = {
    "financial_history_ttl_hours": 6,
    "insider_ttl_hours": 6,
    "institutional_ttl_hours": 6,
    "analyst_ttl_hours": 6,
    "peer_ttl_hours": 6,
}

# Gemini 2.5 Pro config
GEMINI_CONFIG = {
    "model": "gemini-2.5-pro",
    "max_rpm": 5,
    "max_rpd": 100,
    "max_output_tokens": 8192,
    "temperature": 0.7,
}

# DCF defaults — WACC fixed across scenarios per spec
DCF_DEFAULTS = {
    "wacc": 0.10,
    "terminal_growth": 0.025,
    "forecast_years": 10,
    "max_terminal_pct": 0.50,
    "sbc_threshold": 0.10,  # flag if SBC > 10% of revenue
}
