"""
13F Fund Flow Analysis — Quarter-over-quarter institutional ownership delta.
Uses yfinance institutional_holders (keyed by issuer) for current snapshot.
"""
import json
import logging
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG

logger = logging.getLogger(__name__)

# Known fund classifications
_INDEX_FUNDS = {"VANGUARD", "BLACKROCK", "STATE STREET", "FIDELITY", "SCHWAB", "ISHARES", "SPDR"}
_VALUE_FUNDS = {"BERKSHIRE", "BAUPOST", "FAIRHOLME", "TWEEDY", "DODGE & COX", "BRANDES"}
_GROWTH_FUNDS = {"ARK INVESTMENT", "BAILLIE GIFFORD", "T. ROWE PRICE", "CATHIE WOOD"}
_ACTIVIST_FUNDS = {"ELLIOTT", "ICAHN", "ACKMAN", "PERSHING", "STARBOARD", "THIRD POINT", "TRIAN"}


def classify_fund_type(fund_name: str) -> str:
    """Classify a fund by name into: index, value, growth, activist, other."""
    upper = fund_name.upper()
    for kw in _ACTIVIST_FUNDS:
        if kw in upper:
            return "activist"
    for kw in _VALUE_FUNDS:
        if kw in upper:
            return "value"
    for kw in _GROWTH_FUNDS:
        if kw in upper:
            return "growth"
    for kw in _INDEX_FUNDS:
        if kw in upper:
            return "index"
    return "other"


def compute_13f_delta(
    current_holders: list[dict], prior_holders: list[dict],
) -> dict:
    """Compute quarter-over-quarter changes in institutional holdings.

    Each holder dict has: fund_name, shares, value_usd.
    Returns: new_positions, exits, increased, decreased, net_shares_change.
    """
    current_map = {h["fund_name"]: h for h in current_holders}
    prior_map = {h["fund_name"]: h for h in prior_holders}

    new_positions = []
    exits = []
    increased = []
    decreased = []
    net_change = 0

    # New positions: in current but not prior
    for name, h in current_map.items():
        if name not in prior_map:
            new_positions.append({
                "fund_name": name,
                "shares": h["shares"],
                "value_usd": h.get("value_usd", 0),
                "fund_type": classify_fund_type(name),
            })
            net_change += h["shares"]

    # Exits: in prior but not current
    for name, h in prior_map.items():
        if name not in current_map:
            exits.append({
                "fund_name": name,
                "shares": h["shares"],
                "value_usd": h.get("value_usd", 0),
                "fund_type": classify_fund_type(name),
            })
            net_change -= h["shares"]

    # Changed positions
    for name in current_map:
        if name in prior_map:
            curr_shares = current_map[name]["shares"]
            prev_shares = prior_map[name]["shares"]
            change = curr_shares - prev_shares
            if change > 0:
                increased.append({
                    "fund_name": name,
                    "shares": curr_shares,
                    "change": change,
                    "pct_change": round(change / prev_shares, 4) if prev_shares > 0 else None,
                    "fund_type": classify_fund_type(name),
                })
            elif change < 0:
                decreased.append({
                    "fund_name": name,
                    "shares": curr_shares,
                    "change": change,
                    "pct_change": round(change / prev_shares, 4) if prev_shares > 0 else None,
                    "fund_type": classify_fund_type(name),
                })
            net_change += change

    return {
        "new_positions": sorted(new_positions, key=lambda x: x.get("value_usd", 0), reverse=True),
        "exits": sorted(exits, key=lambda x: x.get("value_usd", 0), reverse=True),
        "increased": sorted(increased, key=lambda x: abs(x.get("change", 0)), reverse=True),
        "decreased": sorted(decreased, key=lambda x: abs(x.get("change", 0)), reverse=True),
        "net_shares_change": net_change,
        "summary": {
            "new_count": len(new_positions),
            "exit_count": len(exits),
            "increased_count": len(increased),
            "decreased_count": len(decreased),
            "net_direction": "NET_BUY" if net_change > 0 else "NET_SELL" if net_change < 0 else "FLAT",
        },
    }


def _fetch_institutional_holders(ticker: str) -> list[dict]:
    """Fetch institutional holders via yfinance (keyed by issuer, not by fund)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.institutional_holders
        if df is None or df.empty:
            return []
        holders = []
        for _, row in df.iterrows():
            holders.append({
                "fund_name": str(row.get("Holder", "Unknown")),
                "shares": int(row.get("Shares", 0) or 0),
                "value_usd": int(row.get("Value", 0) or 0),
            })
        return holders[:30]
    except Exception as e:
        logger.warning("Failed to fetch institutional holders for %s: %s", ticker, e)
        return []


def _type_breakdown(holders: list[dict]) -> dict:
    """Count holders by type."""
    counts = {}
    for h in holders:
        t = h.get("fund_type", "other")
        counts[t] = counts.get(t, 0) + 1
    return counts


def get_fund_flow(ticker: str) -> dict:
    """Get 13F quarter-over-quarter delta. Cached 24hr (13F updates quarterly)."""
    ttl = ENRICHMENT_CONFIG.get("fund_flow_ttl_hours", 24)

    with get_db() as db:
        cached = db.execute(
            "SELECT data_json, fetched_at FROM fund_flow_cache WHERE ticker = ?",
            (ticker,),
        ).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        return json.loads(cached["data_json"])

    # Load prior snapshot from cache before fetching fresh data
    prior = []
    if cached:
        try:
            prior_data = json.loads(cached["data_json"])
            prior = prior_data.get("current_holders", [])
        except (json.JSONDecodeError, KeyError):
            pass

    current = _fetch_institutional_holders(ticker)

    if not current:
        return {"delta": None, "current_holders": [], "error": "No institutional holder data available"}

    # Classify current holders
    for h in current:
        h["fund_type"] = classify_fund_type(h["fund_name"])

    delta = compute_13f_delta(current, prior) if prior else None

    result = {
        "current_holders": current[:15],
        "delta": delta,
        "holder_type_breakdown": _type_breakdown(current),
    }

    data_json = json.dumps(result)
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO fund_flow_cache (ticker, data_json, fetched_at) VALUES (?, ?, datetime('now'))",
            (ticker, data_json),
        )
        db.commit()

    return result
