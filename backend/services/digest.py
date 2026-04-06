"""
Watchlist Digest — "What Changed" for tickers you're watching.
Aggregates: insider transactions, press releases, analyst changes.
All scoped to watchlist tickers only.
"""
import os
import httpx
from datetime import datetime, timedelta
from backend.database import get_db
from backend.config import RESEARCH_CONFIG

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")


def refresh_digest(tickers: list[str]):
    """Fetch material events for given tickers. Respects cache TTL."""
    db = get_db()
    last_refresh = db.execute(
        "SELECT MAX(fetched_at) as latest FROM digest_events"
    ).fetchone()
    db.close()

    if last_refresh and last_refresh["latest"]:
        latest = datetime.fromisoformat(last_refresh["latest"])
        if (datetime.now() - latest).total_seconds() < RESEARCH_CONFIG["cache_ttl_hours"] * 3600:
            return

    for ticker in tickers:
        _fetch_insider_transactions(ticker)
        _fetch_fmp_press_releases(ticker)
        _fetch_analyst_changes(ticker)


def _fetch_insider_transactions(ticker: str):
    """Finnhub insider transactions — significant buys/sells only."""
    if not FINNHUB_API_KEY:
        return
    try:
        url = f"https://finnhub.io/api/v1/stock/insider-transactions?symbol={ticker}&token={FINNHUB_API_KEY}"
        resp = httpx.get(url, timeout=10)
        data = resp.json()

        lookback = datetime.now() - timedelta(days=RESEARCH_CONFIG["digest_lookback_days"])

        for txn in data.get("data", [])[:10]:
            txn_date = txn.get("transactionDate", "")
            if not txn_date:
                continue
            try:
                if datetime.fromisoformat(txn_date) < lookback:
                    continue
            except ValueError:
                continue

            change = txn.get("change", 0)
            name = txn.get("name", "Insider")
            txn_type = "insider_buy" if change > 0 else "insider_sell"

            if abs(change) < 1000:
                continue

            headline = f"{name}: {'Bought' if change > 0 else 'Sold'} {abs(change):,.0f} shares"
            _save_digest_event(ticker, txn_type, headline, f"Filed {txn_date}", txn_date, "finnhub")

    except Exception:
        pass


def _fetch_fmp_press_releases(ticker: str):
    """FMP press releases — guidance, acquisitions, material events."""
    if not FMP_API_KEY:
        return
    try:
        url = f"https://financialmodelingprep.com/api/v3/press-releases/{ticker}?limit=5&apikey={FMP_API_KEY}"
        resp = httpx.get(url, timeout=10)
        releases = resp.json()

        lookback = datetime.now() - timedelta(days=RESEARCH_CONFIG["digest_lookback_days"])

        for pr in releases:
            pr_date = pr.get("date", "")
            if not pr_date:
                continue
            try:
                if datetime.fromisoformat(pr_date.split(" ")[0]) < lookback:
                    continue
            except ValueError:
                continue

            title = pr.get("title", "Press Release")
            _save_digest_event(
                ticker, "press_release", title[:200],
                pr.get("text", "")[:300], pr_date, "fmp",
                url=pr.get("url", "")
            )
    except Exception:
        pass


def _fetch_analyst_changes(ticker: str):
    """Finnhub analyst recommendation changes."""
    if not FINNHUB_API_KEY:
        return
    try:
        url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={FINNHUB_API_KEY}"
        resp = httpx.get(url, timeout=10)
        recs = resp.json()

        if len(recs) >= 2:
            current = recs[0]
            previous = recs[1]

            cur_buy = current.get("buy", 0) + current.get("strongBuy", 0)
            prev_buy = previous.get("buy", 0) + previous.get("strongBuy", 0)
            cur_sell = current.get("sell", 0) + current.get("strongSell", 0)
            prev_sell = previous.get("sell", 0) + previous.get("strongSell", 0)

            if cur_buy > prev_buy + 2:
                _save_digest_event(
                    ticker, "analyst_change",
                    f"Analyst upgrades: Buy ratings {prev_buy} -> {cur_buy}",
                    f"Period: {current.get('period', '')}",
                    current.get("period", ""), "finnhub"
                )
            elif cur_sell > prev_sell + 2:
                _save_digest_event(
                    ticker, "analyst_change",
                    f"Analyst downgrades: Sell ratings {prev_sell} -> {cur_sell}",
                    f"Period: {current.get('period', '')}",
                    current.get("period", ""), "finnhub"
                )
    except Exception:
        pass


def _save_digest_event(ticker: str, event_type: str, headline: str,
                       detail: str, event_date: str, source: str, url: str = ""):
    db = get_db()
    existing = db.execute(
        "SELECT id FROM digest_events WHERE ticker = ? AND headline = ? AND event_date = ?",
        (ticker, headline, event_date)
    ).fetchone()
    if not existing:
        db.execute("""
            INSERT INTO digest_events (ticker, event_type, headline, detail, event_date, source, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, event_type, headline, detail, event_date, source, url))
        db.commit()
    db.close()


def get_digest(tickers: list[str] | None = None, unseen_only: bool = False) -> list[dict]:
    """Get digest events, optionally filtered to specific tickers."""
    db = get_db()

    lookback = (datetime.now() - timedelta(days=RESEARCH_CONFIG["digest_lookback_days"])).isoformat()

    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query = f"""
            SELECT * FROM digest_events
            WHERE ticker IN ({placeholders}) AND fetched_at > ?
            {"AND seen = 0" if unseen_only else ""}
            ORDER BY event_date DESC
            LIMIT 50
        """
        rows = db.execute(query, (*tickers, lookback)).fetchall()
    else:
        query = f"""
            SELECT * FROM digest_events
            WHERE fetched_at > ?
            {"AND seen = 0" if unseen_only else ""}
            ORDER BY event_date DESC
            LIMIT 50
        """
        rows = db.execute(query, (lookback,)).fetchall()

    db.close()
    return [dict(r) for r in rows]


def mark_digest_seen(event_ids: list[int]):
    """Mark digest events as seen."""
    db = get_db()
    placeholders = ",".join("?" * len(event_ids))
    db.execute(f"UPDATE digest_events SET seen = 1 WHERE id IN ({placeholders})", event_ids)
    db.commit()
    db.close()
