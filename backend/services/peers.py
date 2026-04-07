"""
Peer Comparison — Sector-based ranking among S&P 500 peers.
Ranks ticker on PE, margin, growth vs same-sector companies.
"""
import json
import yfinance as yf
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG
from backend.services.sp500 import get_sp500_tickers
from backend.services.market_data import get_stock_fundamentals, get_moving_averages
from backend.services.regime_checker import classify_direction


def _rank_among_peers(ticker: str, peers: list[dict]) -> dict:
    """Rank ticker's PE/margin/growth among peers.

    Lower PE = rank 1 (better). Higher margin/growth = rank 1 (better).
    Returns dict with pe_rank, margin_rank, growth_rank, total_peers.
    """
    target = None
    for p in peers:
        if p.get("ticker") == ticker:
            target = p
            break

    if not target:
        return {"pe_rank": None, "margin_rank": None, "growth_rank": None, "total_peers": len(peers)}

    total = len(peers)

    # PE rank: lower is better, None values go to end
    pe_vals = [(p["ticker"], p.get("forward_pe")) for p in peers]
    pe_valid = sorted([(t, v) for t, v in pe_vals if v is not None], key=lambda x: x[1])
    pe_rank = None
    for i, (t, _) in enumerate(pe_valid):
        if t == ticker:
            pe_rank = i + 1
            break

    # Margin rank: higher is better
    margin_vals = [(p["ticker"], p.get("operating_margin")) for p in peers]
    margin_valid = sorted([(t, v) for t, v in margin_vals if v is not None], key=lambda x: x[1], reverse=True)
    margin_rank = None
    for i, (t, _) in enumerate(margin_valid):
        if t == ticker:
            margin_rank = i + 1
            break

    # Growth rank: higher is better
    growth_vals = [(p["ticker"], p.get("revenue_growth")) for p in peers]
    growth_valid = sorted([(t, v) for t, v in growth_vals if v is not None], key=lambda x: x[1], reverse=True)
    growth_rank = None
    for i, (t, _) in enumerate(growth_valid):
        if t == ticker:
            growth_rank = i + 1
            break

    return {
        "pe_rank": pe_rank,
        "margin_rank": margin_rank,
        "growth_rank": growth_rank,
        "total_peers": total,
    }


def get_peer_comparison(ticker: str) -> dict:
    """Find same-sector peers from S&P 500, rank ticker among them. Cached."""
    ttl = ENRICHMENT_CONFIG["peer_ttl_hours"]

    with get_db() as db:
        cached = db.execute("SELECT * FROM peer_cache WHERE ticker = ?", (ticker,)).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        data = json.loads(cached["peers_json"]) if cached["peers_json"] else {}
        return data

    # Get target sector
    try:
        target_info = yf.Ticker(ticker).info
        target_sector = target_info.get("sector", "")
    except Exception:
        return {"peers": [], "ticker_rank": {}, "sector": "Unknown"}

    if not target_sector:
        return {"peers": [], "ticker_rank": {}, "sector": "Unknown"}

    # Find same-sector peers from S&P 500 — use yfinance sector data
    try:
        sp500 = get_sp500_tickers()
    except Exception:
        sp500 = []

    # Filter by sector — sort by market cap proximity for relevant peers
    candidates = [t for t in sp500 if t != ticker]

    # Get target market cap for proximity sorting
    target_mcap = target_info.get("marketCap", 0) or 0

    peer_tickers = []
    sector_matches = []

    # First pass: find all sector matches (check up to 100 tickers, deterministic sample)
    import random
    if len(candidates) > 100:
        sample = random.Random(hash(ticker)).sample(candidates, 100)
    else:
        sample = candidates

    for t in sample:
        try:
            info = yf.Ticker(t).info
            if info.get("sector") == target_sector:
                sector_matches.append({
                    "ticker": t,
                    "mcap": info.get("marketCap", 0) or 0,
                })
        except Exception:
            pass

    # Sort by market cap proximity to target, take top 8
    sector_matches.sort(key=lambda x: abs(x["mcap"] - target_mcap))
    peer_tickers = [m["ticker"] for m in sector_matches[:8]]

    # Fetch fundamentals for target + peers
    all_tickers = [ticker] + peer_tickers
    peers_data = []
    for t in all_tickers:
        try:
            fund = get_stock_fundamentals(t)
            data = fund.value if hasattr(fund, "value") else fund
            ma = get_moving_averages(t)
            direction = ""
            if ma:
                direction = classify_direction(
                    ma.get("price", 0), ma.get("ema20", 0),
                    ma.get("sma50", 0), ma.get("sma200", 0),
                )
            peers_data.append({
                "ticker": t,
                "forward_pe": data.get("forward_pe"),
                "operating_margin": data.get("operating_margin"),
                "revenue_growth": data.get("revenue_growth"),
                "price": data.get("price"),
                "direction": direction,
            })
        except Exception:
            continue

    ticker_rank = _rank_among_peers(ticker, peers_data)

    result = {
        "peers": peers_data,
        "ticker_rank": ticker_rank,
        "sector": target_sector,
    }

    # Cache
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO peer_cache (ticker, peers_json, fetched_at)
               VALUES (?, ?, datetime('now'))""",
            (ticker, json.dumps(result)),
        )
        db.commit()

    return result
