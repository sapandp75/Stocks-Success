"""
Institutional Intelligence — Insider activity (Finnhub) + institutional holdings (yfinance).
Surfaces C-suite buying/selling for contrarian signals.
"""
import os
import json
import httpx
import yfinance as yf
from datetime import datetime
from backend.database import get_db
from backend.config import ENRICHMENT_CONFIG


FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _classify_insider_sentiment(transactions: list[dict]) -> str:
    """Classify insider sentiment from transaction list.

    Returns BUYING/SELLING/MIXED/QUIET based on net change ratio.
    """
    if not transactions:
        return "QUIET"

    net_change = sum(t.get("change", 0) for t in transactions)
    total_abs = sum(abs(t.get("change", 0)) for t in transactions)

    if total_abs == 0:
        return "QUIET"

    ratio = net_change / total_abs
    if ratio > 0.3:
        return "BUYING"
    elif ratio < -0.3:
        return "SELLING"
    else:
        return "MIXED"


def get_insider_activity(ticker: str) -> dict:
    """Finnhub insider transactions. Cached in insider_cache table."""
    ttl = ENRICHMENT_CONFIG["insider_ttl_hours"]

    db = get_db()
    cached = db.execute("SELECT * FROM insider_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ttl):
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        return {
            "net_sentiment": cached["net_sentiment"],
            "recent_buys": data.get("recent_buys", 0),
            "recent_sells": data.get("recent_sells", 0),
            "notable": data.get("notable", []),
        }

    # Fetch from Finnhub
    transactions = []
    if FINNHUB_API_KEY:
        try:
            url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&token={FINNHUB_API_KEY}"
            resp = httpx.get(url, timeout=10)
            raw = resp.json()
            transactions = raw.get("data", [])
        except Exception:
            transactions = []

    net_sentiment = _classify_insider_sentiment(transactions)

    recent_buys = sum(1 for t in transactions if t.get("change", 0) > 0)
    recent_sells = sum(1 for t in transactions if t.get("change", 0) < 0)

    # Notable: C-suite, value > $100K
    csuite_keywords = {"CEO", "CFO", "COO", "PRESIDENT", "CHIEF"}
    notable = []
    for t in transactions:
        name = (t.get("name", "") or "").upper()
        change = t.get("change", 0)
        price = t.get("transactionPrice", 0) or 0
        value = abs(change * price)
        is_csuite = any(kw in name for kw in csuite_keywords)
        if is_csuite and value > 100_000:
            notable.append({
                "name": t.get("name", ""),
                "change": change,
                "value": round(value, 2),
                "date": t.get("transactionDate", ""),
            })

    result = {
        "net_sentiment": net_sentiment,
        "recent_buys": recent_buys,
        "recent_sells": recent_sells,
        "notable": notable,
    }

    # Cache
    data_json = json.dumps({"recent_buys": recent_buys, "recent_sells": recent_sells, "notable": notable})
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO insider_cache (ticker, net_sentiment, data_json, fetched_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (ticker, net_sentiment, data_json),
    )
    db.commit()
    db.close()

    return result


def get_institutional_summary(ticker: str) -> dict:
    """yfinance institutional holders summary. Cached in institutional_cache table."""
    ttl = ENRICHMENT_CONFIG["institutional_ttl_hours"]

    db = get_db()
    cached = db.execute("SELECT * FROM institutional_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], ttl):
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        return {
            "top_holders": data.get("top_holders", []),
            "institutional_pct": data.get("institutional_pct"),
            "trend": cached["trend"],
        }

    # Fetch from yfinance
    try:
        stock = yf.Ticker(ticker)
        holders_df = stock.institutional_holders
        info = stock.info

        top_holders = []
        if holders_df is not None and not holders_df.empty:
            for _, row in holders_df.head(10).iterrows():
                holder = {
                    "name": str(row.get("Holder", "")),
                    "shares": int(row["Shares"]) if "Shares" in row and row["Shares"] else 0,
                    "pct_out": float(row["% Out"]) if "% Out" in row and row["% Out"] else None,
                }
                top_holders.append(holder)

        institutional_pct = info.get("heldPercentInstitutions")
        if institutional_pct is not None:
            institutional_pct = round(institutional_pct * 100, 2)

        # Simple trend: compare to typical level
        if institutional_pct is not None:
            if institutional_pct > 80:
                trend = "HIGH"
            elif institutional_pct > 50:
                trend = "MODERATE"
            else:
                trend = "LOW"
        else:
            trend = "UNKNOWN"

    except Exception:
        top_holders = []
        institutional_pct = None
        trend = "UNKNOWN"

    result = {
        "top_holders": top_holders,
        "institutional_pct": institutional_pct,
        "trend": trend,
    }

    # Cache
    data_json = json.dumps({"top_holders": top_holders, "institutional_pct": institutional_pct})
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO institutional_cache (ticker, trend, data_json, fetched_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (ticker, trend, data_json),
    )
    db.commit()
    db.close()

    return result
