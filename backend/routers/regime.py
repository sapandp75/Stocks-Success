from fastapi import APIRouter
from backend.services.regime_checker import get_full_regime
from backend.database import get_db

router = APIRouter(prefix="/api/regime", tags=["regime"])


@router.get("")
def regime_check():
    data = get_full_regime()
    # Add market breadth (non-blocking enrichment)
    try:
        from backend.services.regime_checker import calculate_market_breadth
        data["breadth"] = calculate_market_breadth()
    except Exception:
        data["breadth"] = None
    return data


@router.get("/earnings-calendar")
def get_watchlist_earnings():
    """Upcoming earnings dates for watchlist tickers."""
    from backend.services.market_data import get_stock_fundamentals
    with get_db() as db:
        rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()

    upcoming = []
    for r in rows:
        try:
            data = get_stock_fundamentals(r["ticker"]).value
            ed = data.get("earnings_date")
            if ed:
                upcoming.append({"ticker": r["ticker"], "earnings_date": ed})
        except Exception:
            continue

    upcoming.sort(key=lambda x: x.get("earnings_date", "9999"))
    return {"upcoming_earnings": upcoming}
