"""
Forward Estimates — Analyst growth projections for EPS and revenue.
Primary source: yfinance info dict (free, no API key).
Secondary source: MCP get_analyst_estimates (when available via bridge).
"""
import json
import yfinance as yf
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG


def parse_yfinance_estimates(info: dict) -> dict:
    """Pure function: extract forward estimates from yfinance info dict."""
    forward_eps = info.get("forwardEps")
    trailing_eps = info.get("trailingEps")

    eps_fwd_vs_trailing = None
    if forward_eps and trailing_eps and trailing_eps != 0:
        eps_fwd_vs_trailing = round(forward_eps / trailing_eps - 1, 4)

    return {
        "eps_growth_1yr": info.get("earningsGrowth"),
        "eps_growth_quarterly": info.get("earningsQuarterlyGrowth"),
        "revenue_growth_trailing": info.get("revenueGrowth"),
        "forward_eps": forward_eps,
        "trailing_eps": trailing_eps,
        "eps_fwd_vs_trailing": eps_fwd_vs_trailing,
        "peg_ratio": info.get("pegRatio"),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
    }


def get_earnings_history(ticker: str) -> list[dict]:
    """Last 4 quarters: EPS actual vs estimate + surprise %."""
    try:
        stock = yf.Ticker(ticker)
        ed = stock.earnings_dates
        if ed is None or ed.empty:
            return []

        import pandas as pd
        quarters = []
        for date, row in ed.head(8).iterrows():
            eps_est = row.get("EPS Estimate")
            eps_act = row.get("Reported EPS")
            surprise = row.get("Surprise(%)")
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)

            if pd.notna(eps_act):
                quarters.append({
                    "date": date_str,
                    "eps_estimate": round(float(eps_est), 2) if pd.notna(eps_est) else None,
                    "eps_actual": round(float(eps_act), 2),
                    "surprise_pct": round(float(surprise), 2) if pd.notna(surprise) else None,
                    "beat": surprise > 0 if pd.notna(surprise) else None,
                })
            elif pd.notna(eps_est):
                quarters.append({
                    "date": date_str,
                    "eps_estimate": round(float(eps_est), 2),
                    "eps_actual": None,
                    "surprise_pct": None,
                    "beat": None,
                    "upcoming": True,
                })

        return quarters
    except Exception:
        return []


def get_forward_estimates(ticker: str) -> dict:
    """Fetch forward estimates + earnings history. Cached 6hr."""
    ttl = ENRICHMENT_CONFIG.get("forward_estimates_ttl_hours", 6)

    with get_db() as db:
        cached = db.execute(
            "SELECT data_json, fetched_at FROM forward_estimates_cache WHERE ticker = ?",
            (ticker,),
        ).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        return json.loads(cached["data_json"])

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
    except Exception:
        info = {}

    estimates = parse_yfinance_estimates(info)
    estimates["earnings_history"] = get_earnings_history(ticker)

    # Beat rate: consecutive beats
    beats = [q for q in estimates["earnings_history"] if q.get("beat") is not None]
    if beats:
        consecutive = 0
        for q in beats:
            if q["beat"]:
                consecutive += 1
            else:
                break
        estimates["consecutive_beats"] = consecutive
        estimates["beat_rate_4q"] = round(
            sum(1 for q in beats[:4] if q["beat"]) / min(len(beats), 4), 2
        )
    else:
        estimates["consecutive_beats"] = None
        estimates["beat_rate_4q"] = None

    # Cache
    data_json = json.dumps(estimates)
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO forward_estimates_cache (ticker, data_json, fetched_at) VALUES (?, ?, datetime('now'))",
            (ticker, data_json),
        )
        db.commit()

    return estimates
