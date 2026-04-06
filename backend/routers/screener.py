import json
import logging
import threading
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from backend.services.stock_screener import scan_sp500
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["screener"])

# In-memory scan state (single-user app)
_scan_state = {
    "status": "idle",  # idle | running | complete | error
    "progress": 0,
    "total": 0,
    "result": None,
    "error": None,
}
_scan_lock = threading.Lock()


def _enrich_candidates(results: dict):
    """Enrich B1/B2 candidates with sentiment + technicals. Mutates in place."""
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
        logger.warning("Failed to enrich candidates with sentiment", exc_info=True)

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
        logger.warning("Failed to enrich candidates with technicals", exc_info=True)


def _run_scan_background(scan_type: str):
    """Run scan in background thread. Updates _scan_state."""
    global _scan_state
    try:
        with _scan_lock:
            _scan_state = {"status": "running", "progress": 0, "total": 503, "result": None, "error": None}

        results = scan_sp500(scan_type=scan_type)
        _enrich_candidates(results)

        # Save to database
        with get_db() as db:
            db.execute(
                "INSERT INTO scan_results (scan_type, total_scanned, b1_count, b2_count, results_json, errors_json) VALUES (?, ?, ?, ?, ?, ?)",
                (scan_type, results["total_scanned"], results["b1_count"], results["b2_count"],
                 json.dumps(results, default=str), json.dumps(results["errors"], default=str)),
            )
            db.commit()

        with _scan_lock:
            _scan_state = {"status": "complete", "progress": results["total_scanned"],
                           "total": results["total_scanned"], "result": results, "error": None}
        logger.info("Scan complete: %d B1, %d B2 from %d", results["b1_count"], results["b2_count"], results["total_scanned"])

    except Exception as e:
        logger.error("Scan failed: %s", e, exc_info=True)
        with _scan_lock:
            _scan_state = {"status": "error", "progress": 0, "total": 0, "result": None, "error": str(e)}


@router.post("/scan")
def start_scan(scan_type: str = Query("weekly", enum=["daily", "weekly"])):
    """Start an S&P 500 scan. Returns immediately with job status."""
    if scan_type == "daily":
        # Daily scans are small enough to run inline
        with get_db() as db:
            rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
        tickers = [r["ticker"] for r in rows]
        if not tickers:
            return {"error": "No watchlist entries. Add stocks first or run weekly scan."}
        from backend.services.market_data import get_stock_fundamentals
        from backend.services.stock_screener import check_b1_warnings
        results = []
        for t in tickers:
            try:
                data = get_stock_fundamentals(t).value
                data["warnings"] = check_b1_warnings(data)
                results.append(data)
            except Exception as e:
                results.append({"ticker": t, "error": str(e)})
        return {"scan_type": "daily", "results": results}

    # Weekly: check if already running
    with _scan_lock:
        if _scan_state["status"] == "running":
            return {"status": "already_running", "progress": _scan_state["progress"], "total": _scan_state["total"]}

    thread = threading.Thread(target=_run_scan_background, args=(scan_type,), daemon=True)
    thread.start()
    return {"status": "started", "message": "Scan started. Poll /api/screener/scan/status for progress."}


@router.get("/scan")
def run_scan_legacy(scan_type: str = Query("weekly", enum=["daily", "weekly"])):
    """Legacy GET endpoint — redirects to POST behavior."""
    return start_scan(scan_type=scan_type)


@router.get("/scan/status")
def scan_status():
    """Poll scan progress."""
    with _scan_lock:
        state = {**_scan_state}
    # Don't send full results in status — use /latest for that
    if state["status"] == "complete":
        return {"status": "complete", "progress": state["progress"], "total": state["total"]}
    return state


@router.get("/latest")
def get_latest_scan():
    """Get most recent scan results with freshness indicator."""
    # Check if just-completed scan is available in memory
    with _scan_lock:
        if _scan_state["status"] == "complete" and _scan_state["result"]:
            result = _scan_state["result"]
            result["is_stale"] = False
            return result

    with get_db() as db:
        row = db.execute("SELECT * FROM scan_results ORDER BY scan_date DESC LIMIT 1").fetchone()
    if not row:
        return {"error": "No scan results. Run POST /api/screener/scan?scan_type=weekly first."}
    result = json.loads(row["results_json"])
    result["scan_id"] = row["id"]
    scan_date = datetime.fromisoformat(row["scan_date"])
    result["is_stale"] = (datetime.now() - scan_date) > timedelta(days=7)
    return result
