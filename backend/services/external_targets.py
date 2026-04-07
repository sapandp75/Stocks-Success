"""
External Price Targets & Fair Values — Multi-source aggregation.
Sources: Yahoo (via yfinance), Finviz (via finvizfinance).
"""
import json
import logging
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG

logger = logging.getLogger(__name__)


def parse_finviz_data(fundament: dict) -> dict:
    """Extract target and recommendation from finviz fundament dict."""
    target = fundament.get("Target Price")
    try:
        target = float(target) if target else None
    except (ValueError, TypeError):
        target = None
    return {
        "target": target,
        "recommendation": fundament.get("Analyst") or fundament.get("Recom"),
    }


def _fetch_finviz_target(ticker: str) -> dict:
    """Fetch target price from Finviz."""
    try:
        from finvizfinance.quote import finvizfinance
        stock = finvizfinance(ticker)
        fundament = stock.ticker_fundament()
        return parse_finviz_data(fundament)
    except Exception as e:
        logger.warning("Finviz fetch failed for %s: %s", ticker, e)
        return {"target": None, "recommendation": None}


def _fetch_yahoo_targets(ticker: str) -> dict:
    """Get analyst targets from yfinance."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return {
            "mean": info.get("targetMeanPrice"),
            "low": info.get("targetLowPrice"),
            "high": info.get("targetHighPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
        }
    except Exception:
        return {"mean": None, "low": None, "high": None, "num_analysts": None}


def build_target_comparison(
    targets: dict, your_dcf: dict, current_price: float,
) -> dict:
    """Build unified comparison table from all sources."""
    yahoo = targets.get("yahoo", {})
    finviz = targets.get("finviz", {})

    yahoo_mean = yahoo.get("mean")
    finviz_target = finviz.get("target")
    dcf_base = your_dcf.get("base")

    def _upside(target):
        if target and current_price and current_price > 0:
            return round(target / current_price - 1, 4)
        return None

    return {
        "current_price": current_price,
        "yahoo_mean": yahoo_mean,
        "yahoo_low": yahoo.get("low"),
        "yahoo_high": yahoo.get("high"),
        "yahoo_num_analysts": yahoo.get("num_analysts"),
        "finviz_target": finviz_target,
        "finviz_recommendation": finviz.get("recommendation"),
        "your_dcf_bear": your_dcf.get("bear"),
        "your_dcf_base": dcf_base,
        "your_dcf_bull": your_dcf.get("bull"),
        "upside_to_street_mean": _upside(yahoo_mean),
        "upside_to_finviz": _upside(finviz_target),
        "upside_to_your_base": _upside(dcf_base),
    }


def get_external_targets(ticker: str) -> dict:
    """Fetch all external targets. Cached 6hr."""
    ttl = ENRICHMENT_CONFIG.get("external_targets_ttl_hours", 6)

    with get_db() as db:
        cached = db.execute(
            "SELECT data_json, fetched_at FROM external_targets_cache WHERE ticker = ?",
            (ticker,),
        ).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        return json.loads(cached["data_json"])

    targets = {
        "yahoo": _fetch_yahoo_targets(ticker),
        "finviz": _fetch_finviz_target(ticker),
    }

    result = {
        "sources": targets,
        "fetched_sources": [k for k, v in targets.items() if v.get("target") or v.get("mean")],
    }

    data_json = json.dumps(result)
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO external_targets_cache (ticker, data_json, fetched_at) VALUES (?, ?, datetime('now'))",
            (ticker, data_json),
        )
        db.commit()

    return result
