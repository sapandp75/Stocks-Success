import json
import logging
import threading
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from backend.services.stock_screener import scan_universe
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/screener", tags=["screener"])

VALID_UNIVERSES = ("spx", "ndx")
_DEFAULT_TOTALS = {"spx": 503, "ndx": 103}


def _make_idle_state():
    return {"status": "idle", "progress": 0, "total": 0, "result": None, "error": None}


# Per-universe scan state (single-user app)
_scan_states = {u: _make_idle_state() for u in VALID_UNIVERSES}
_scan_locks = {u: threading.Lock() for u in VALID_UNIVERSES}


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


def _run_scan_background(universe: str, scan_type: str):
    """Run scan in background thread. Updates per-universe _scan_states."""
    lock = _scan_locks[universe]
    try:
        # State already set to "running" by start_scan before thread launch
        def _update_progress(current, total):
            with lock:
                _scan_states[universe]["progress"] = current
                _scan_states[universe]["total"] = total

        results = scan_universe(universe=universe, scan_type=scan_type, progress_callback=_update_progress)
        _enrich_candidates(results)

        # Save to database
        with get_db() as db:
            db.execute(
                "INSERT INTO scan_results (scan_type, universe, total_scanned, b1_count, b2_count, results_json, errors_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (scan_type, universe, results["total_scanned"], results["b1_count"], results["b2_count"],
                 json.dumps(results, default=str), json.dumps(results["errors"], default=str)),
            )
            db.commit()

        with lock:
            _scan_states[universe] = {"status": "complete", "progress": results["total_scanned"],
                           "total": results["total_scanned"], "result": results, "error": None}
        logger.info("[%s] Scan complete: %d B1, %d B2 from %d", universe.upper(), results["b1_count"], results["b2_count"], results["total_scanned"])

    except Exception as e:
        logger.error("[%s] Scan failed: %s", universe.upper(), e, exc_info=True)
        with lock:
            _scan_states[universe] = {"status": "error", "progress": 0, "total": 0, "result": None, "error": str(e)}


@router.post("/scan")
def start_scan(
    scan_type: str = Query("weekly", enum=["daily", "weekly"]),
    universe: str = Query("spx", enum=["spx", "ndx"]),
):
    """Start a scan for the given universe. Returns immediately with job status."""
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

    # Weekly: check if already running for this universe
    lock = _scan_locks[universe]
    default_total = _DEFAULT_TOTALS.get(universe, 500)
    with lock:
        if _scan_states[universe]["status"] == "running":
            state = _scan_states[universe]
            return {"status": "already_running", "progress": state["progress"], "total": state["total"]}
        # Claim "running" inside the lock to prevent double-launch (TOCTOU)
        _scan_states[universe] = {"status": "running", "progress": 0, "total": default_total, "result": None, "error": None}

    thread = threading.Thread(target=_run_scan_background, args=(universe, scan_type), daemon=True)
    thread.start()
    return {"status": "started", "universe": universe, "message": f"Scan started for {universe.upper()}. Poll /api/screener/scan/status?universe={universe} for progress."}


@router.get("/scan")
def run_scan_legacy(
    scan_type: str = Query("weekly", enum=["daily", "weekly"]),
    universe: str = Query("spx", enum=["spx", "ndx"]),
):
    """Legacy GET endpoint — redirects to POST behavior."""
    return start_scan(scan_type=scan_type, universe=universe)


@router.post("/scan/reset")
def reset_scan(universe: str = Query("spx", enum=["spx", "ndx"])):
    """Force-reset a stuck scan state back to idle."""
    lock = _scan_locks[universe]
    with lock:
        prev = _scan_states[universe]["status"]
        _scan_states[universe] = _make_idle_state()
    logger.info("[%s] Scan state reset from '%s' to 'idle'", universe.upper(), prev)
    return {"status": "reset", "universe": universe, "previous": prev}


@router.get("/scan/status")
def scan_status(universe: str = Query("spx", enum=["spx", "ndx"])):
    """Poll scan progress for the given universe."""
    lock = _scan_locks[universe]
    with lock:
        state = {**_scan_states[universe]}
    # Don't send full results in status — use /latest for that
    if state["status"] == "complete":
        return {"status": "complete", "progress": state["progress"], "total": state["total"]}
    return state


@router.get("/latest")
def get_latest_scan(universe: str = Query("spx", enum=["spx", "ndx"])):
    """Get most recent scan results for the given universe with freshness indicator."""
    # Check if just-completed scan is available in memory
    lock = _scan_locks[universe]
    with lock:
        if _scan_states[universe]["status"] == "complete" and _scan_states[universe]["result"]:
            result = {**_scan_states[universe]["result"], "is_stale": False}
            return result

    with get_db() as db:
        row = db.execute(
            "SELECT * FROM scan_results WHERE universe = ? ORDER BY scan_date DESC LIMIT 1",
            (universe,),
        ).fetchone()
    if not row:
        label = "S&P 500" if universe == "spx" else "Nasdaq-100"
        return {"error": f"No {label} scan results. Run POST /api/screener/scan?universe={universe}&scan_type=weekly first."}
    result = json.loads(row["results_json"])
    result["scan_id"] = row["id"]
    scan_date = datetime.fromisoformat(row["scan_date"])
    result["is_stale"] = (datetime.now() - scan_date) > timedelta(days=7)
    return result
