"""
Peer Comparison — Sector-based ranking among S&P 500 peers.
Ranks ticker on PE, margin, growth vs same-sector companies.
"""
import json
import random
import yfinance as yf
from datetime import datetime
from backend.database import get_db
from backend.config import ENRICHMENT_CONFIG
from backend.services.sp500 import get_sp500_tickers
from backend.services.market_data import get_stock_fundamentals, get_moving_averages
from backend.services.regime_checker import classify_direction


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


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

    db = get_db()
    cached = db.execute("SELECT * FROM peer_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ttl):
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

    # Find same-sector peers from S&P 500
    try:
        sp500 = get_sp500_tickers()
    except Exception:
        sp500 = []

    candidates = [t for t in sp500 if t != ticker]
    random.shuffle(candidates)

    peer_tickers = []
    checked = 0
    for t in candidates:
        if checked >= 30 or len(peer_tickers) >= 8:
            break
        try:
            info = yf.Ticker(t).info
            if info.get("sector") == target_sector:
                peer_tickers.append(t)
        except Exception:
            pass
        checked += 1

    # Fetch fundamentals for target + peers
    all_tickers = [ticker] + peer_tickers
    peers_data = []
    for t in all_tickers:
        try:
            fund = get_stock_fundamentals(t)
            data = fund.data if hasattr(fund, "data") else fund
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
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO peer_cache (ticker, peers_json, fetched_at)
           VALUES (?, ?, datetime('now'))""",
        (ticker, json.dumps(result)),
    )
    db.commit()
    db.close()

    return result
