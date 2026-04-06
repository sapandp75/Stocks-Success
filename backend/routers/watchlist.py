from fastapi import APIRouter
from backend.database import get_db
from backend.validators import validate_ticker, WatchlistEntry

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def get_watchlist():
    with get_db() as db:
        rows = db.execute("SELECT * FROM watchlist ORDER BY added_date DESC").fetchall()
    return [dict(r) for r in rows]


@router.post("")
def add_to_watchlist(entry: WatchlistEntry):
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO watchlist (ticker, bucket, thesis_note, entry_zone_low, entry_zone_high, conviction, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.ticker, entry.bucket,
            entry.thesis_note, entry.entry_zone_low,
            entry.entry_zone_high, entry.conviction,
            entry.status,
        ))
        db.commit()
    return {"status": "saved", "ticker": entry.ticker}


@router.get("/digest")
def get_watchlist_digest():
    """What Changed digest for watchlist tickers."""
    from backend.services.digest import get_digest, refresh_digest
    with get_db() as db:
        rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
    tickers = [r["ticker"] for r in rows]
    if not tickers:
        return {"events": [], "note": "Add stocks to watchlist first."}
    refresh_digest(tickers)
    events = get_digest(tickers=tickers)
    return {
        "tickers_checked": len(tickers),
        "events": events,
        "unseen_count": len([e for e in events if not e.get("seen")]),
    }


@router.delete("/{ticker}")
def remove_from_watchlist(ticker: str):
    ticker = validate_ticker(ticker)
    with get_db() as db:
        db.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        db.commit()
    return {"status": "removed", "ticker": ticker}
