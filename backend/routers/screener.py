import json
from fastapi import APIRouter, Query
from backend.services.stock_screener import scan_sp500
from backend.database import get_db

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("/scan")
def run_scan(scan_type: str = Query("weekly", enum=["daily", "weekly"])):
    """Run S&P 500 scan. Weekly = full rescan. Daily = watchlist only."""
    if scan_type == "daily":
        # Daily: only scan watchlist tickers
        db = get_db()
        rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
        db.close()
        tickers = [r["ticker"] for r in rows]
        if not tickers:
            return {"error": "No watchlist entries. Add stocks first or run weekly scan."}
        # Scan only those tickers
        from backend.services.market_data import get_stock_fundamentals
        from backend.services.stock_screener import check_b1_gates, check_b1_warnings
        results = []
        for t in tickers:
            try:
                data = get_stock_fundamentals(t).value
                data["warnings"] = check_b1_warnings(data)
                results.append(data)
            except Exception as e:
                results.append({"ticker": t, "error": str(e)})
        return {"scan_type": "daily", "results": results}

    results = scan_sp500(scan_type=scan_type)
    # Save to database
    db = get_db()
    db.execute(
        "INSERT INTO scan_results (scan_type, total_scanned, b1_count, b2_count, results_json, errors_json) VALUES (?, ?, ?, ?, ?, ?)",
        (scan_type, results["total_scanned"], results["b1_count"], results["b2_count"],
         json.dumps(results, default=str), json.dumps(results["errors"], default=str)),
    )
    db.commit()
    db.close()
    return results


@router.get("/latest")
def get_latest_scan():
    """Get most recent scan results with freshness indicator."""
    db = get_db()
    row = db.execute("SELECT * FROM scan_results ORDER BY scan_date DESC LIMIT 1").fetchone()
    db.close()
    if not row:
        return {"error": "No scan results. Run /api/screener/scan?scan_type=weekly first."}
    result = json.loads(row["results_json"])
    result["scan_id"] = row["id"]
    result["is_stale"] = False  # TODO: check age > 7 days
    return result
