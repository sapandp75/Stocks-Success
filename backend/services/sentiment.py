"""
Sentiment Intelligence — Contrarian-aware sentiment scoring.
Combines Alpha Vantage news sentiment + Finnhub analyst consensus.
Inverts the signal: negative sentiment on quality = opportunity.
"""
import os
import json
import httpx
from backend.database import get_db, is_fresh
from backend.config import RESEARCH_CONFIG, ENRICHMENT_CONFIG


AV_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def fetch_sentiment(ticker: str) -> dict:
    """Get combined sentiment for a ticker. Cached in SQLite."""
    with get_db() as db:
        cached = db.execute("SELECT * FROM sentiment_cache WHERE ticker = ?", (ticker,)).fetchone()

    if cached and is_fresh(cached["fetched_at"], RESEARCH_CONFIG["sentiment_staleness_hours"]):
        return _format_sentiment(dict(cached))

    av_data = _fetch_alpha_vantage_sentiment(ticker)
    fh_data = _fetch_finnhub_consensus(ticker)

    record = {
        "ticker": ticker,
        "av_sentiment_score": av_data.get("score"),
        "av_sentiment_label": av_data.get("label"),
        "av_article_count": av_data.get("article_count", 0),
        "finnhub_consensus": fh_data.get("consensus"),
        "finnhub_target_mean": fh_data.get("target_mean"),
        "finnhub_target_high": fh_data.get("target_high"),
        "finnhub_target_low": fh_data.get("target_low"),
        "finnhub_recent_change": fh_data.get("recent_change"),
    }

    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO sentiment_cache
            (ticker, av_sentiment_score, av_sentiment_label, av_article_count,
             finnhub_consensus, finnhub_target_mean, finnhub_target_high, finnhub_target_low,
             finnhub_recent_change, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            ticker, record["av_sentiment_score"], record["av_sentiment_label"],
            record["av_article_count"], record["finnhub_consensus"],
            record["finnhub_target_mean"], record["finnhub_target_high"],
            record["finnhub_target_low"], record["finnhub_recent_change"],
        ))
        db.commit()

    return _format_sentiment(record)


def _fetch_alpha_vantage_sentiment(ticker: str) -> dict:
    """Alpha Vantage News Sentiment API — 25 calls/day on free tier."""
    if not AV_API_KEY:
        return {}
    try:
        url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={AV_API_KEY}&limit=10"
        resp = httpx.get(url, timeout=15)
        data = resp.json()
        if "feed" not in data:
            return {}

        scores = []
        for item in data["feed"]:
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    score = float(ts.get("ticker_sentiment_score", 0))
                    scores.append(score)

        if not scores:
            return {}

        avg_score = sum(scores) / len(scores)
        if avg_score <= -0.35:
            label = "Bearish"
        elif avg_score <= -0.15:
            label = "Somewhat-Bearish"
        elif avg_score <= 0.15:
            label = "Neutral"
        elif avg_score <= 0.35:
            label = "Somewhat-Bullish"
        else:
            label = "Bullish"

        return {"score": round(avg_score, 3), "label": label, "article_count": len(scores)}
    except Exception:
        return {}


def _fetch_finnhub_consensus(ticker: str) -> dict:
    """Finnhub analyst recommendations + price targets — 60 calls/min free."""
    if not FINNHUB_API_KEY:
        return {}
    try:
        rec_url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={FINNHUB_API_KEY}"
        rec_resp = httpx.get(rec_url, timeout=10)
        recs = rec_resp.json()

        consensus = None
        recent_change = "maintain"
        if recs and len(recs) >= 1:
            latest = recs[0]
            buy = latest.get("buy", 0) + latest.get("strongBuy", 0)
            hold = latest.get("hold", 0)
            sell = latest.get("sell", 0) + latest.get("strongSell", 0)
            total = buy + hold + sell
            if total > 0:
                if buy / total > 0.6:
                    consensus = "buy"
                elif sell / total > 0.3:
                    consensus = "sell"
                else:
                    consensus = "hold"

            if len(recs) >= 2:
                prev_buy = recs[1].get("buy", 0) + recs[1].get("strongBuy", 0)
                if buy > prev_buy + 1:
                    recent_change = "upgrade"
                elif buy < prev_buy - 1:
                    recent_change = "downgrade"

        target_url = f"https://finnhub.io/api/v1/stock/price-target?symbol={ticker}&token={FINNHUB_API_KEY}"
        target_resp = httpx.get(target_url, timeout=10)
        targets = target_resp.json()

        return {
            "consensus": consensus,
            "recent_change": recent_change,
            "target_mean": targets.get("targetMean"),
            "target_high": targets.get("targetHigh"),
            "target_low": targets.get("targetLow"),
        }
    except Exception:
        return {}


def _format_sentiment(record: dict) -> dict:
    """Add contrarian interpretation to raw sentiment data."""
    result = {**record}

    av_score = record.get("av_sentiment_score")
    fh_consensus = record.get("finnhub_consensus")
    fh_change = record.get("finnhub_recent_change")

    contrarian_signals = []

    if av_score is not None and av_score <= -0.15:
        contrarian_signals.append("NEGATIVE_SENTIMENT")
    if fh_change == "downgrade":
        contrarian_signals.append("RECENT_DOWNGRADE")
    if fh_consensus == "sell":
        contrarian_signals.append("ANALYSTS_BEARISH")

    if len(contrarian_signals) >= 2:
        result["contrarian_rating"] = "HIGH_INTEREST"
        result["contrarian_note"] = "Wall Street hates this. If fundamentals hold, this is your edge."
    elif len(contrarian_signals) == 1:
        result["contrarian_rating"] = "MODERATE_INTEREST"
        result["contrarian_note"] = "Some pessimism priced in. Worth investigating."
    else:
        result["contrarian_rating"] = "CONSENSUS"
        result["contrarian_note"] = "Crowd is neutral/positive. Less contrarian edge here."

    result["contrarian_signals"] = contrarian_signals
    return result


def _build_analyst_data(data: dict) -> dict:
    """Add contrarian interpretation to analyst data."""
    result = {**data}
    price = data.get("current_price", 0)
    target = data.get("target_mean", 0)
    result["price_vs_target"] = round(price / target, 3) if target and target > 0 else None

    consensus = data.get("consensus", "")
    if consensus in ("sell", "strong_sell"):
        result["contrarian_signal"] = "ANALYSTS_BEARISH"
    elif consensus == "hold" and result.get("price_vs_target") and result["price_vs_target"] > 1.1:
        result["contrarian_signal"] = "ABOVE_TARGETS"
    else:
        result["contrarian_signal"] = "CONSENSUS"
    return result


def get_analyst_data(ticker: str) -> dict:
    """Full analyst data with contrarian interpretation. Cached 6hr."""
    ttl = ENRICHMENT_CONFIG["analyst_ttl_hours"]

    with get_db() as db:
        cached = db.execute("SELECT * FROM analyst_cache WHERE ticker = ?", (ticker,)).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        data = json.loads(cached["data_json"]) if cached["data_json"] else {}
        return _build_analyst_data(data)

    # Fetch from yfinance
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        target_mean = info.get("targetMeanPrice")
        target_low = info.get("targetLowPrice")
        target_high = info.get("targetHighPrice")
        num_analysts = info.get("numberOfAnalystOpinions")
        consensus = info.get("recommendationKey", "")
    except Exception:
        current_price = 0
        target_mean = None
        target_low = None
        target_high = None
        num_analysts = None
        consensus = ""

    # Fetch upgrades/downgrades from Finnhub
    recent_changes = []
    if FINNHUB_API_KEY:
        try:
            url = f"https://finnhub.io/api/v1/stock/upgrade-downgrade?symbol={ticker}&token={FINNHUB_API_KEY}"
            resp = httpx.get(url, timeout=10)
            changes = resp.json()
            if isinstance(changes, list):
                recent_changes = changes[:10]
        except Exception:
            recent_changes = []

    data = {
        "ticker": ticker,
        "current_price": current_price,
        "target_mean": target_mean,
        "target_low": target_low,
        "target_high": target_high,
        "num_analysts": num_analysts,
        "consensus": consensus,
        "recent_changes": recent_changes,
    }

    # Cache
    data_json = json.dumps(data)
    with get_db() as db:
        db.execute(
            """INSERT OR REPLACE INTO analyst_cache
               (ticker, consensus, target_mean, target_low, target_high, num_analysts, data_json, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (ticker, consensus, target_mean, target_low, target_high, num_analysts, data_json),
        )
        db.commit()

    return _build_analyst_data(data)


def fetch_sentiment_batch(tickers: list[str]) -> dict[str, dict]:
    """Fetch sentiment for multiple tickers. Used by screener."""
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = fetch_sentiment(ticker)
        except Exception:
            results[ticker] = {"contrarian_rating": "UNKNOWN"}
    return results
