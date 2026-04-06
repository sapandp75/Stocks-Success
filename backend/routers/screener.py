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
    # Enrich candidates with sentiment + technicals (only stocks that passed gates)
    try:
        from backend.services.sentiment import fetch_sentiment
        for candidate in results["b1_candidates"] + results["b2_candidates"]:
            try:
                sent = fetch_sentiment(candidate["ticker"])
                candidate["sentiment_score"] = sent.get("av_sentiment_score")
                candidate["sentiment_label"] = sent.get("av_sentiment_label")
                candidate["contrarian_rating"] = sent.get("contrarian_rating")
                candidate["analyst_trend"] = sent.get("finnhub_recent_change")
            except Exception:
                candidate["sentiment_score"] = None
                candidate["contrarian_rating"] = "UNKNOWN"
                candidate["analyst_trend"] = None
    except Exception:
        pass
    # Enrich with technicals: direction + RSI + analyst target
    try:
        from backend.services.technicals import get_full_technicals
        from backend.services.sentiment import get_analyst_data
        for candidate in results["b1_candidates"] + results["b2_candidates"]:
            try:
                tech = get_full_technicals(candidate["ticker"])
                candidate["direction"] = tech.get("direction")
                candidate["rsi"] = tech.get("rsi")
                candidate["macd_crossover"] = tech.get("macd_crossover")
            except Exception:
                candidate["direction"] = None
                candidate["rsi"] = None
            try:
                analyst = get_analyst_data(candidate["ticker"])
                candidate["analyst_target_mean"] = analyst.get("target_mean")
                candidate["analyst_target_upside"] = None
                price = candidate.get("price")
                target = analyst.get("target_mean")
                if price and target and price > 0:
                    candidate["analyst_target_upside"] = round((target - price) / price * 100, 1)
            except Exception:
                candidate["analyst_target_mean"] = None
                candidate["analyst_target_upside"] = None
    except Exception:
        pass
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
