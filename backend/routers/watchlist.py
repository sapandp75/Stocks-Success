from fastapi import APIRouter, Body
from backend.database import get_db

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("")
def get_watchlist():
    db = get_db()
    rows = db.execute("SELECT * FROM watchlist ORDER BY added_date DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


@router.post("")
def add_to_watchlist(entry: dict = Body(...)):
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO watchlist (ticker, bucket, thesis_note, entry_zone_low, entry_zone_high, conviction, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        entry["ticker"].upper(), entry.get("bucket", "B1"),
        entry.get("thesis_note", ""), entry.get("entry_zone_low"),
        entry.get("entry_zone_high"), entry.get("conviction", "MODERATE"),
        entry.get("status", "WATCHING"),
    ))
    db.commit()
    db.close()
    return {"status": "saved", "ticker": entry["ticker"]}


@router.get("/digest")
def get_watchlist_digest():
    """What Changed digest for watchlist tickers."""
    from backend.services.digest import get_digest, refresh_digest
    db = get_db()
    rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
    db.close()
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
    db = get_db()
    db.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker.upper(),))
    db.commit()
    db.close()
    return {"status": "removed", "ticker": ticker}
