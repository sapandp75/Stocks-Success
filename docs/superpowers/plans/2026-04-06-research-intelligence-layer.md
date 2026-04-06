# Research Intelligence Layer — Integration Plan

> **Principle:** Research surfaces at the point of decision, not as a feed. No new pages. No noise. Only signal that strengthens existing workflows.

**Goal:** Add a research intelligence layer to the Contrarian Investing Platform that deepens screener results, enriches deep dives, monitors watchlist changes, and strengthens regime awareness — without introducing a single new page or standalone news feed.

**Constraint:** Every piece of research must be **scoped** (only tickers you care about), **cached** (no API hammering), **collapsed by default** (you pull it when you want it), and **contrarian-aware** (negative sentiment = bullish signal for you).

---

## Design Principles

1. **No new pages.** Research integrates into the 6 existing pages.
2. **Scoped to your universe.** Only fetch for: watchlist tickers + latest screener B1/B2 hits. Never the whole market.
3. **Cached in SQLite.** Max one fetch per ticker per 6 hours. Respects API rate limits.
4. **Collapsed by default.** Research panels are closed until you expand them. They don't shout.
5. **Contrarian-inverted sentiment.** Negative crowd sentiment on a quality name is shown as a green signal, not a red warning.
6. **Feeds Claude, not just your eyes.** The bridge script pre-fetches research context so Claude's deep dive analysis is informed by latest SA articles, earnings transcripts, and filings.

---

## What Goes Where

| Existing Page | What's Added | Data Sources | Why It Helps |
|---------------|-------------|--------------|--------------|
| **Screener** | 2 new columns: Sentiment Score + Analyst Trend | Alpha Vantage News Sentiment API + Finnhub Analyst Recs | Spot contrarian setups: beaten-down + hated = your sweet spot |
| **Deep Dive** | New collapsed section: "Research Context" | Seeking Alpha RSS + Finnhub Earnings Transcripts + FMP Press Releases + SEC EDGAR | Gives Claude (and you) the latest articles, management commentary, and material events before writing the analysis |
| **Watchlist** | "What Changed" digest at top | Finnhub Insider Txns + FMP Press Releases + SA RSS (watchlist tickers only) | One-line-per-event summary of material changes since last check |
| **Regime** | Macro context badges + Watchlist Earnings Calendar | Alpha Vantage macro sentiment + yfinance earnings dates | Know what's coming this week for stocks you care about |
| **Options** | (No change) | Already has earnings proximity + regime context | Already well-served |
| **Positions** | (No change) | Already has P&L tracking | Already well-served |

---

## Architecture

### New Files

```
backend/
  services/
    research.py              # RSS fetcher + research aggregator + SQLite cache
    sentiment.py             # Alpha Vantage news sentiment + Finnhub analyst consensus
    transcripts.py           # Finnhub earnings call transcripts
    digest.py                # Watchlist "What Changed" — insider txns, press releases, analyst changes
  routers/
    research.py              # GET /api/research/{ticker}, GET /api/research/{ticker}/sentiment
```

### Modified Files

```
backend/
  database.py               # Add research_cache + sentiment_cache tables
  config.py                 # Add research config (cache TTL, RSS URLs, Substack feeds)
  routers/
    deep_dive.py            # Include research context in GET response
    screener.py             # Include sentiment scores in scan results
    watchlist.py            # Add GET /api/watchlist/digest endpoint
    regime.py               # Add earnings calendar for watchlist tickers
bridge/
  deep_dive_worker.py       # Pre-fetch research context for Claude's analysis
frontend/src/
  pages/
    ScreenerPage.jsx        # Add Sentiment + Analyst Trend columns to StockCard
    DeepDivePage.jsx        # Add 9th collapsed section: "Research Context"
    WatchlistPage.jsx       # Add "What Changed" digest panel at top
    RegimePage.jsx          # Add macro badges + earnings calendar
  components/
    SentimentBadge.jsx      # Contrarian-inverted sentiment indicator (NEW)
    ResearchPanel.jsx       # Collapsed research context for deep dive (NEW)
    DigestList.jsx          # Watchlist digest event list (NEW)
    EarningsCalendar.jsx    # Upcoming earnings for watchlist stocks (NEW)
```

### New Dependencies (add to requirements.txt)

```
feedparser>=6.0             # RSS parsing (Seeking Alpha, CNBC, Substack)
```

Note: All Finnhub/FMP/Alpha Vantage calls use `httpx` (already in requirements.txt). No additional API client libraries needed.

### New SQLite Tables (add to database.py init_db)

```sql
CREATE TABLE IF NOT EXISTS research_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    source TEXT NOT NULL,           -- "seeking_alpha", "finnhub_transcript", "fmp_press", "substack"
    content_type TEXT NOT NULL,     -- "article", "transcript", "press_release", "newsletter"
    title TEXT,
    summary TEXT,                   -- First 500 chars or AI-generated summary
    url TEXT,
    published_date TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_json TEXT                   -- Full content for Claude context
);

CREATE INDEX IF NOT EXISTS idx_research_ticker ON research_cache(ticker, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_source ON research_cache(source, ticker);

CREATE TABLE IF NOT EXISTS sentiment_cache (
    ticker TEXT PRIMARY KEY,
    av_sentiment_score REAL,        -- Alpha Vantage: -1.0 to 1.0
    av_sentiment_label TEXT,        -- "Bearish", "Somewhat-Bearish", "Neutral", "Somewhat-Bullish", "Bullish"
    av_article_count INTEGER,       -- Number of articles scored
    finnhub_consensus TEXT,         -- "strongBuy", "buy", "hold", "sell", "strongSell"
    finnhub_target_mean REAL,       -- Mean analyst price target
    finnhub_target_high REAL,
    finnhub_target_low REAL,
    finnhub_recent_change TEXT,     -- "upgrade", "downgrade", "maintain" (last 30 days)
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS digest_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    event_type TEXT NOT NULL,       -- "insider_buy", "insider_sell", "press_release", "new_article", "analyst_change"
    headline TEXT NOT NULL,
    detail TEXT,
    event_date TEXT,
    source TEXT,
    url TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
    seen INTEGER DEFAULT 0          -- 1 = user has seen this
);

CREATE INDEX IF NOT EXISTS idx_digest_ticker ON digest_events(ticker, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_digest_unseen ON digest_events(seen, fetched_at DESC);
```

---

## New Config (add to config.py)

```python
# Research Intelligence Layer
RESEARCH_CONFIG = {
    "cache_ttl_hours": 6,               # Don't re-fetch within this window
    "max_articles_per_ticker": 5,        # Keep latest 5 SA articles per ticker
    "max_transcript_age_days": 90,       # Only fetch transcripts from last quarter
    "digest_lookback_days": 7,           # "What Changed" looks back 7 days
    "sentiment_staleness_hours": 12,     # Re-fetch sentiment after 12 hours
}

# Seeking Alpha RSS (no key needed, no rate limit)
SA_RSS_TEMPLATE = "https://seekingalpha.com/api/sa/combined/{ticker}.xml"

# Substack feeds — curated value investing newsletters
SUBSTACK_FEEDS = [
    {"name": "Yet Another Value Blog", "url": "https://yetanothervalueblog.substack.com/feed"},
    {"name": "Compounding Quality", "url": "https://www.compoundingquality.net/feed"},
    {"name": "TSOH Investment Research", "url": "https://thescienceofhitting.com/feed"},
    {"name": "Net Interest", "url": "https://www.netinterest.co/feed"},
]

# CNBC RSS (no key needed)
CNBC_EARNINGS_RSS = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"
```

---

## Task R1: Research Services (Backend)

**Depends on:** Phase 1 Tasks 1-3 complete (project scaffolding, database, market data)
**When to build:** After Task 9 (all routers exist), before Task 10 (frontend)

### Files to Create

#### backend/services/research.py

```python
"""
Research Intelligence — RSS fetcher + aggregator + SQLite cache.
Only fetches for tickers you care about. Caches aggressively.
"""
import feedparser
import time
from datetime import datetime, timedelta
from backend.database import get_db
from backend.config import (
    RESEARCH_CONFIG, SA_RSS_TEMPLATE, SUBSTACK_FEEDS, CNBC_EARNINGS_RSS,
)


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    """Check if cached data is still within TTL."""
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _save_research(ticker: str, source: str, content_type: str,
                   title: str, summary: str, url: str,
                   published_date: str, raw_json: str = ""):
    db = get_db()
    # Avoid duplicates by URL
    existing = db.execute(
        "SELECT id FROM research_cache WHERE ticker = ? AND url = ?",
        (ticker, url)
    ).fetchone()
    if not existing:
        db.execute("""
            INSERT INTO research_cache (ticker, source, content_type, title, summary, url, published_date, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticker, source, content_type, title, summary[:500] if summary else "", url, published_date, raw_json))
        db.commit()
    db.close()


def fetch_seeking_alpha(ticker: str) -> list[dict]:
    """Fetch latest SA articles for a ticker via RSS. No API key needed."""
    db = get_db()
    latest = db.execute(
        "SELECT fetched_at FROM research_cache WHERE ticker = ? AND source = 'seeking_alpha' ORDER BY fetched_at DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    db.close()

    if latest and _is_fresh(latest["fetched_at"], RESEARCH_CONFIG["cache_ttl_hours"]):
        return _get_cached(ticker, "seeking_alpha")

    url = SA_RSS_TEMPLATE.format(ticker=ticker)
    try:
        feed = feedparser.parse(url)
        max_articles = RESEARCH_CONFIG["max_articles_per_ticker"]
        for entry in feed.entries[:max_articles]:
            _save_research(
                ticker=ticker,
                source="seeking_alpha",
                content_type="article",
                title=entry.get("title", ""),
                summary=entry.get("summary", ""),
                url=entry.get("link", ""),
                published_date=entry.get("published", ""),
            )
    except Exception:
        pass  # Fail silently — research is enrichment, not critical path

    return _get_cached(ticker, "seeking_alpha")


def fetch_substack_mentions(ticker: str) -> list[dict]:
    """
    Check curated Substack feeds for mentions of this ticker.
    Only fetches each feed once per TTL, then scans cached entries.
    """
    db = get_db()
    latest = db.execute(
        "SELECT fetched_at FROM research_cache WHERE ticker = ? AND source = 'substack' ORDER BY fetched_at DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    db.close()

    if latest and _is_fresh(latest["fetched_at"], RESEARCH_CONFIG["cache_ttl_hours"]):
        return _get_cached(ticker, "substack")

    for feed_info in SUBSTACK_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                # Only save if ticker is mentioned in title or first 500 chars of summary
                ticker_upper = ticker.upper()
                if ticker_upper in title.upper() or ticker_upper in summary[:500].upper():
                    _save_research(
                        ticker=ticker,
                        source="substack",
                        content_type="newsletter",
                        title=f"[{feed_info['name']}] {title}",
                        summary=summary[:500],
                        url=entry.get("link", ""),
                        published_date=entry.get("published", ""),
                    )
        except Exception:
            continue

    return _get_cached(ticker, "substack")


def _get_cached(ticker: str, source: str) -> list[dict]:
    db = get_db()
    rows = db.execute("""
        SELECT title, summary, url, published_date, source, content_type
        FROM research_cache
        WHERE ticker = ? AND source = ?
        ORDER BY published_date DESC
        LIMIT ?
    """, (ticker, source, RESEARCH_CONFIG["max_articles_per_ticker"])).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_all_research(ticker: str) -> dict:
    """
    Aggregate all research for a ticker. Called by deep dive endpoint.
    Each source fetches independently — one failure doesn't block others.
    """
    sa_articles = fetch_seeking_alpha(ticker)
    substack = fetch_substack_mentions(ticker)

    return {
        "ticker": ticker,
        "seeking_alpha": sa_articles,
        "substack": substack,
        "total_items": len(sa_articles) + len(substack),
    }


def get_research_for_claude(ticker: str) -> str:
    """
    Format research as plain text for Claude's deep dive context.
    Called by bridge/deep_dive_worker.py.
    """
    research = get_all_research(ticker)
    sections = []

    if research["seeking_alpha"]:
        sections.append("## Recent Seeking Alpha Articles")
        for a in research["seeking_alpha"]:
            sections.append(f"- **{a['title']}** ({a['published_date']})")
            if a['summary']:
                # Strip HTML tags from RSS summary
                import re
                clean = re.sub(r'<[^>]+>', '', a['summary'])
                sections.append(f"  {clean[:300]}...")

    if research["substack"]:
        sections.append("\n## Value Investing Newsletter Mentions")
        for a in research["substack"]:
            sections.append(f"- **{a['title']}** ({a['published_date']})")
            if a['summary']:
                import re
                clean = re.sub(r'<[^>]+>', '', a['summary'])
                sections.append(f"  {clean[:300]}...")

    if not sections:
        return f"No recent research articles found for {ticker}."

    return f"# Research Context for {ticker}\n\n" + "\n".join(sections)
```

#### backend/services/sentiment.py

```python
"""
Sentiment Intelligence — Contrarian-aware sentiment scoring.
Combines Alpha Vantage news sentiment + Finnhub analyst consensus.
Inverts the signal: negative sentiment on quality = opportunity.
"""
import os
import httpx
from datetime import datetime
from backend.database import get_db
from backend.config import RESEARCH_CONFIG


AV_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def fetch_sentiment(ticker: str) -> dict:
    """
    Get combined sentiment for a ticker. Cached in SQLite.
    Returns both raw scores and contrarian interpretation.
    """
    db = get_db()
    cached = db.execute("SELECT * FROM sentiment_cache WHERE ticker = ?", (ticker,)).fetchone()
    db.close()

    if cached and _is_fresh(cached["fetched_at"], RESEARCH_CONFIG["sentiment_staleness_hours"]):
        return _format_sentiment(dict(cached))

    # Fetch fresh data from both sources
    av_data = _fetch_alpha_vantage_sentiment(ticker)
    fh_data = _fetch_finnhub_consensus(ticker)

    # Merge and cache
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

    db = get_db()
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
    db.close()

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
        # AV sentiment: <= -0.35 Bearish, -0.35 to -0.15 Somewhat-Bearish,
        # -0.15 to 0.15 Neutral, 0.15 to 0.35 Somewhat-Bullish, >= 0.35 Bullish
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
        # Recommendations
        rec_url = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker}&token={FINNHUB_API_KEY}"
        rec_resp = httpx.get(rec_url, timeout=10)
        recs = rec_resp.json()

        consensus = None
        recent_change = "maintain"
        if recs and len(recs) >= 1:
            latest = recs[0]
            # Determine consensus from buy/hold/sell counts
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

            # Check for recent change (compare last 2 periods)
            if len(recs) >= 2:
                prev_buy = recs[1].get("buy", 0) + recs[1].get("strongBuy", 0)
                if buy > prev_buy + 1:
                    recent_change = "upgrade"
                elif buy < prev_buy - 1:
                    recent_change = "downgrade"

        # Price targets
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

    # Contrarian signal logic:
    # Negative sentiment + quality fundamentals (caller checks) = opportunity
    # Downgrades on a B1 candidate = classic contrarian entry
    contrarian_signals = []

    if av_score is not None and av_score <= -0.15:
        contrarian_signals.append("NEGATIVE_SENTIMENT")
    if fh_change == "downgrade":
        contrarian_signals.append("RECENT_DOWNGRADE")
    if fh_consensus == "sell":
        contrarian_signals.append("ANALYSTS_BEARISH")

    # Inversion: more bearish signals = more interesting for a contrarian
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


def fetch_sentiment_batch(tickers: list[str]) -> dict[str, dict]:
    """Fetch sentiment for multiple tickers. Used by screener."""
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = fetch_sentiment(ticker)
        except Exception:
            results[ticker] = {"contrarian_rating": "UNKNOWN"}
    return results
```

#### backend/services/transcripts.py

```python
"""
Earnings Call Transcripts — via Finnhub API.
Fetched on-demand for deep dives, cached in research_cache.
"""
import os
import httpx
from datetime import datetime, timedelta
from backend.database import get_db
from backend.config import RESEARCH_CONFIG

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def fetch_latest_transcript(ticker: str) -> dict | None:
    """
    Fetch the most recent earnings call transcript for a ticker.
    Cached in research_cache as content_type='transcript'.
    """
    db = get_db()
    cached = db.execute("""
        SELECT title, summary, raw_json, published_date, fetched_at
        FROM research_cache
        WHERE ticker = ? AND content_type = 'transcript'
        ORDER BY published_date DESC LIMIT 1
    """, (ticker,)).fetchone()
    db.close()

    if cached:
        fetched = datetime.fromisoformat(cached["fetched_at"])
        max_age = timedelta(days=RESEARCH_CONFIG["max_transcript_age_days"])
        if (datetime.now() - fetched) < max_age:
            return dict(cached)

    if not FINNHUB_API_KEY:
        return None

    try:
        # Get earnings calendar to find latest earnings date
        now = datetime.now()
        from_date = (now - timedelta(days=120)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")

        cal_url = (
            f"https://finnhub.io/api/v1/stock/earnings?symbol={ticker}&token={FINNHUB_API_KEY}"
        )
        cal_resp = httpx.get(cal_url, timeout=10)
        earnings = cal_resp.json()

        if not earnings:
            return None

        # Get the most recent quarter
        latest = earnings[0]
        quarter = latest.get("quarter", 0)
        year = latest.get("year", now.year)

        # Fetch transcript
        transcript_url = (
            f"https://finnhub.io/api/v1/stock/transcripts?symbol={ticker}"
            f"&token={FINNHUB_API_KEY}"
        )
        transcript_resp = httpx.get(transcript_url, timeout=15)
        transcript_list = transcript_resp.json()

        if not transcript_list or "transcripts" not in transcript_list:
            return None

        transcripts = transcript_list["transcripts"]
        if not transcripts:
            return None

        # Get the latest transcript ID
        latest_id = transcripts[0].get("id")
        if not latest_id:
            return None

        # Fetch full transcript
        full_url = (
            f"https://finnhub.io/api/v1/stock/transcripts?id={latest_id}"
            f"&token={FINNHUB_API_KEY}"
        )
        full_resp = httpx.get(full_url, timeout=15)
        full = full_resp.json()

        if not full or "transcript" not in full:
            return None

        # Build readable text from transcript segments
        segments = full["transcript"]
        text_parts = []
        for seg in segments:
            speaker = seg.get("name", "Unknown")
            speech = seg.get("speech", [])
            text = " ".join(speech) if isinstance(speech, list) else str(speech)
            text_parts.append(f"**{speaker}:** {text}")

        full_text = "\n\n".join(text_parts)
        title = f"Q{quarter} {year} Earnings Call Transcript"
        summary = full_text[:500]

        # Cache it
        import json
        db = get_db()
        db.execute("""
            INSERT INTO research_cache (ticker, source, content_type, title, summary, url, published_date, raw_json)
            VALUES (?, 'finnhub_transcript', 'transcript', ?, ?, '', ?, ?)
        """, (ticker, title, summary, transcripts[0].get("time", ""), json.dumps({"text": full_text})))
        db.commit()
        db.close()

        return {"title": title, "summary": summary, "full_text": full_text}

    except Exception:
        return None


def get_transcript_for_claude(ticker: str) -> str:
    """Format transcript as plain text for Claude's deep dive context."""
    transcript = fetch_latest_transcript(ticker)
    if not transcript:
        return ""

    full_text = transcript.get("full_text", transcript.get("summary", ""))
    # Truncate to reasonable length for context (keep first 8000 chars)
    if len(full_text) > 8000:
        full_text = full_text[:8000] + "\n\n[... transcript truncated for context length ...]"

    return f"## Latest Earnings Call: {transcript['title']}\n\n{full_text}"
```

#### backend/services/digest.py

```python
"""
Watchlist Digest — "What Changed" for tickers you're watching.
Aggregates: insider transactions, press releases, new SA articles, analyst changes.
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
    """
    Fetch material events for given tickers and store in digest_events.
    Called when user opens watchlist page. Respects cache TTL.
    """
    db = get_db()
    last_refresh = db.execute(
        "SELECT MAX(fetched_at) as latest FROM digest_events"
    ).fetchone()
    db.close()

    if last_refresh and last_refresh["latest"]:
        latest = datetime.fromisoformat(last_refresh["latest"])
        if (datetime.now() - latest).total_seconds() < RESEARCH_CONFIG["cache_ttl_hours"] * 3600:
            return  # Still fresh

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

            shares = txn.get("share", 0)
            change = txn.get("change", 0)
            name = txn.get("name", "Insider")
            txn_type = "insider_buy" if change > 0 else "insider_sell"

            # Only surface significant transactions
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
    # Avoid duplicates
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
    """Get digest events, optionally filtered to specific tickers and unseen items."""
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
```

#### backend/routers/research.py

```python
"""
Research API — serves aggregated research, sentiment, transcripts, and digest.
All endpoints are scoped to specific tickers. No "firehose" endpoints.
"""
from fastapi import APIRouter, Query
from backend.services.research import get_all_research
from backend.services.sentiment import fetch_sentiment
from backend.services.transcripts import fetch_latest_transcript
from backend.services.digest import get_digest, refresh_digest, mark_digest_seen
from backend.database import get_db

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/{ticker}")
def get_research_for_ticker(ticker: str):
    """
    Get all research context for a single ticker.
    Used by Deep Dive page to populate Research Context section.
    """
    ticker = ticker.upper()
    research = get_all_research(ticker)
    sentiment = fetch_sentiment(ticker)
    transcript = fetch_latest_transcript(ticker)

    return {
        "ticker": ticker,
        "articles": research.get("seeking_alpha", []),
        "newsletters": research.get("substack", []),
        "sentiment": sentiment,
        "transcript": {
            "title": transcript["title"] if transcript else None,
            "summary": transcript["summary"] if transcript else None,
            "available": transcript is not None,
        },
        "total_research_items": research.get("total_items", 0),
    }


@router.get("/{ticker}/sentiment")
def get_sentiment(ticker: str):
    """Sentiment only — used by screener for lightweight column data."""
    return fetch_sentiment(ticker.upper())


@router.get("/digest/watchlist")
def get_watchlist_digest(unseen_only: bool = Query(False)):
    """
    Get "What Changed" digest for all watchlist tickers.
    Triggers a refresh if data is stale.
    """
    db = get_db()
    rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
    db.close()

    tickers = [r["ticker"] for r in rows]
    if not tickers:
        return {"events": [], "note": "Add stocks to watchlist first."}

    # Refresh if stale
    refresh_digest(tickers)

    events = get_digest(tickers=tickers, unseen_only=unseen_only)
    return {
        "tickers_checked": len(tickers),
        "events": events,
        "unseen_count": len([e for e in events if not e.get("seen")]),
    }


@router.post("/digest/mark-seen")
def mark_seen(data: dict):
    """Mark digest events as seen."""
    event_ids = data.get("event_ids", [])
    if event_ids:
        mark_digest_seen(event_ids)
    return {"status": "ok", "marked": len(event_ids)}
```

---

## Task R2: Modifications to Existing Backend

### Modify: backend/database.py

Add the three new tables (`research_cache`, `sentiment_cache`, `digest_events`) to the `init_db()` function. SQL is defined above in the Architecture section. Add after the existing `CREATE TABLE` statements.

### Modify: backend/config.py

Add `RESEARCH_CONFIG`, `SA_RSS_TEMPLATE`, `SUBSTACK_FEEDS`, and `CNBC_EARNINGS_RSS` constants. Code is defined above in the New Config section.

### Modify: backend/main.py

Add the research router:

```python
from backend.routers import regime, screener, options, deep_dive, watchlist, positions, research

# ... existing routers ...
app.include_router(research.router)
```

### Modify: backend/routers/deep_dive.py — GET endpoint

Add research context to the deep dive response. After the existing `ai_analysis` block, add:

```python
# Research context (collapsed by default in UI)
from backend.services.research import get_all_research
from backend.services.sentiment import fetch_sentiment
from backend.services.transcripts import fetch_latest_transcript

research_context = None
try:
    research = get_all_research(ticker)
    sentiment = fetch_sentiment(ticker)
    transcript = fetch_latest_transcript(ticker)
    research_context = {
        "articles": research.get("seeking_alpha", []),
        "newsletters": research.get("substack", []),
        "sentiment": sentiment,
        "transcript_available": transcript is not None,
        "transcript_title": transcript["title"] if transcript else None,
    }
except Exception:
    pass  # Research is enrichment, never blocks the critical path
```

Add `"research_context": research_context` to the return dict.

### Modify: backend/routers/screener.py — scan results

After scan_sp500() returns results, enrich B1/B2 candidates with sentiment. This is done **lazily** — sentiment is only fetched for stocks that passed the gates, not all 500.

```python
# Enrich candidates with sentiment (only for stocks that passed gates)
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
```

### Modify: backend/routers/watchlist.py — add digest endpoint

Add to the existing watchlist router:

```python
@router.get("/digest")
def get_watchlist_digest():
    """Redirect to research digest for watchlist tickers."""
    from backend.services.digest import get_digest, refresh_digest
    db = get_db()
    rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
    db.close()
    tickers = [r["ticker"] for r in rows]
    if tickers:
        refresh_digest(tickers)
    return get_digest(tickers=tickers)
```

### Modify: backend/routers/regime.py — add earnings calendar

Add to the regime response:

```python
@router.get("/earnings-calendar")
def get_watchlist_earnings():
    """Upcoming earnings dates for watchlist tickers. Shown on regime page."""
    from backend.services.market_data import get_stock_fundamentals
    db = get_db()
    rows = db.execute("SELECT ticker FROM watchlist WHERE status = 'WATCHING'").fetchall()
    db.close()

    upcoming = []
    for r in rows:
        try:
            data = get_stock_fundamentals(r["ticker"]).value
            ed = data.get("earnings_date")
            if ed:
                upcoming.append({"ticker": r["ticker"], "earnings_date": ed})
        except Exception:
            continue

    # Sort by date, soonest first
    upcoming.sort(key=lambda x: x.get("earnings_date", "9999"))
    return {"upcoming_earnings": upcoming}
```

### Modify: bridge/deep_dive_worker.py

Enhance the bridge script to pre-fetch research context for Claude. Add a `--context` flag:

```python
# Add to the argparse section:
parser.add_argument("--context", action="store_true",
                    help="Print research context for Claude to use in analysis")

# Add to the main() function, before the elif args.post block:
if args.context:
    from backend.services.research import get_research_for_claude
    from backend.services.transcripts import get_transcript_for_claude
    context = get_research_for_claude(ticker)
    transcript = get_transcript_for_claude(ticker)
    print(context)
    if transcript:
        print("\n" + transcript)
    return
```

**Usage from Claude Code:**
```bash
# First, get research context
python bridge/deep_dive_worker.py ADBE --context

# Then use it to inform the deep dive analysis
# Claude reads the output and incorporates it into the 8-section analysis
```

---

## Task R3: Frontend Modifications

### Modify: ScreenerPage.jsx — Add sentiment columns

Add two columns to StockCard:

1. **Sentiment** — A `SentimentBadge` component showing:
   - Score from -1 to +1 (from Alpha Vantage)
   - **Contrarian-inverted color**: red/bearish sentiment shows as green (opportunity), green/bullish shows as grey (consensus)
   - Tooltip: "Wall Street sentiment: Bearish — Contrarian interest: HIGH"

2. **Analyst Trend** — An arrow icon:
   - Down arrow (green for contrarian) = recent downgrade
   - Up arrow (grey) = recent upgrade
   - Dash = maintain/no change

### New component: frontend/src/components/SentimentBadge.jsx

```jsx
/**
 * Contrarian-inverted sentiment badge.
 * Negative sentiment = green (opportunity for contrarian).
 * Positive sentiment = grey (consensus, less edge).
 */
export default function SentimentBadge({ score, label, contrarianRating }) {
  if (score === null || score === undefined) {
    return <span className="text-xs text-gray-400">—</span>;
  }

  // Contrarian inversion: bearish = good, bullish = meh
  const colorMap = {
    HIGH_INTEREST: "bg-green-100 text-green-800 border-green-300",
    MODERATE_INTEREST: "bg-amber-50 text-amber-700 border-amber-200",
    CONSENSUS: "bg-gray-100 text-gray-500 border-gray-200",
    UNKNOWN: "bg-gray-50 text-gray-400 border-gray-100",
  };

  const style = colorMap[contrarianRating] || colorMap.UNKNOWN;

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${style}`}
      title={`Crowd sentiment: ${label} (${score.toFixed(2)}) — Contrarian interest: ${contrarianRating}`}
    >
      {score.toFixed(2)}
    </span>
  );
}
```

### Modify: DeepDivePage.jsx — Add 9th collapsed section

Add after section 8 (Verdict), a collapsed "Research Context" section:

```jsx
<CollapsibleSection title="Research Context" defaultOpen={false} accent="blue">
  <ResearchPanel ticker={ticker} />
</CollapsibleSection>
```

### New component: frontend/src/components/ResearchPanel.jsx

```jsx
/**
 * Research Context panel for Deep Dive page.
 * Fetches from /api/research/{ticker} on mount.
 * Shows: SA articles, Substack mentions, sentiment, transcript availability.
 * Collapsed by default — user pulls when ready.
 */
import { useState, useEffect } from "react";
import { fetchResearch } from "../api";
import SentimentBadge from "./SentimentBadge";

export default function ResearchPanel({ ticker }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [fetched, setFetched] = useState(false);

  // Lazy load: only fetch when user expands the section
  useEffect(() => {
    if (!fetched) return;
    setLoading(true);
    fetchResearch(ticker)
      .then(setData)
      .finally(() => setLoading(false));
  }, [ticker, fetched]);

  // Trigger fetch on first render (section was expanded)
  useEffect(() => { setFetched(true); }, []);

  if (loading) return <p className="text-sm text-gray-500">Loading research...</p>;
  if (!data) return <p className="text-sm text-gray-400">No research data available.</p>;

  return (
    <div className="space-y-4">
      {/* Sentiment Summary */}
      {data.sentiment && (
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-600">Crowd Sentiment:</span>
          <SentimentBadge
            score={data.sentiment.av_sentiment_score}
            label={data.sentiment.av_sentiment_label}
            contrarianRating={data.sentiment.contrarian_rating}
          />
          {data.sentiment.contrarian_note && (
            <span className="text-xs text-gray-500 italic">{data.sentiment.contrarian_note}</span>
          )}
        </div>
      )}

      {/* Analyst Targets */}
      {data.sentiment?.finnhub_target_mean && (
        <div className="text-sm text-gray-600">
          Analyst target: ${data.sentiment.finnhub_target_low?.toFixed(0)} —
          <strong> ${data.sentiment.finnhub_target_mean?.toFixed(0)} </strong>
          — ${data.sentiment.finnhub_target_high?.toFixed(0)}
          {data.sentiment.finnhub_recent_change !== "maintain" && (
            <span className={`ml-2 text-xs ${
              data.sentiment.finnhub_recent_change === "downgrade"
                ? "text-green-600"  /* contrarian: downgrade = opportunity */
                : "text-gray-400"
            }`}>
              ({data.sentiment.finnhub_recent_change})
            </span>
          )}
        </div>
      )}

      {/* Seeking Alpha Articles */}
      {data.articles?.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-1">Recent Analysis (Seeking Alpha)</h4>
          <ul className="space-y-1">
            {data.articles.map((a, i) => (
              <li key={i} className="text-sm">
                <a href={a.url} target="_blank" rel="noopener noreferrer"
                   className="text-blue-600 hover:underline">
                  {a.title}
                </a>
                <span className="text-gray-400 text-xs ml-2">{a.published_date}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Substack Mentions */}
      {data.newsletters?.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-1">Newsletter Mentions</h4>
          <ul className="space-y-1">
            {data.newsletters.map((a, i) => (
              <li key={i} className="text-sm">
                <a href={a.url} target="_blank" rel="noopener noreferrer"
                   className="text-blue-600 hover:underline">
                  {a.title}
                </a>
                <span className="text-gray-400 text-xs ml-2">{a.published_date}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Transcript */}
      {data.transcript?.available && (
        <div className="text-sm text-gray-600">
          Latest transcript: <strong>{data.transcript.title}</strong>
          <span className="text-xs text-gray-400 ml-2">(full text available in Claude deep dive)</span>
        </div>
      )}

      {data.total_research_items === 0 && (
        <p className="text-sm text-gray-400 italic">No recent research found for {ticker}.</p>
      )}
    </div>
  );
}
```

### Modify: WatchlistPage.jsx — Add digest panel

Add at the top of the watchlist page, above the ticker list:

```jsx
{/* What Changed — digest of material events for watchlist tickers */}
<DigestList />
```

### New component: frontend/src/components/DigestList.jsx

```jsx
/**
 * "What Changed" digest for watchlist page.
 * Shows one-line-per-event summary of material changes.
 * Fetches from /api/watchlist/digest on mount.
 */
import { useState, useEffect } from "react";
import { fetchWatchlistDigest, markDigestSeen } from "../api";

const EVENT_ICONS = {
  insider_buy: { icon: "arrow-up", color: "text-green-600", label: "Insider Buy" },
  insider_sell: { icon: "arrow-down", color: "text-red-500", label: "Insider Sell" },
  press_release: { icon: "newspaper", color: "text-blue-600", label: "Press Release" },
  analyst_change: { icon: "chart", color: "text-amber-600", label: "Analyst Change" },
  new_article: { icon: "document", color: "text-gray-600", label: "Article" },
};

export default function DigestList() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWatchlistDigest()
      .then((data) => setEvents(data.events || []))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-sm text-gray-400 py-2">Checking for updates...</div>;
  if (events.length === 0) return null; // Don't show anything if no events — no noise

  const unseenCount = events.filter((e) => !e.seen).length;

  return (
    <div className="mb-6 bg-white rounded-lg border border-[#e2e4e8] p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">
          What Changed
          {unseenCount > 0 && (
            <span className="ml-2 bg-amber-100 text-amber-700 text-xs px-1.5 py-0.5 rounded">
              {unseenCount} new
            </span>
          )}
        </h3>
        {unseenCount > 0 && (
          <button
            onClick={() => {
              const ids = events.filter((e) => !e.seen).map((e) => e.id);
              markDigestSeen(ids).then(() => {
                setEvents(events.map((e) => ({ ...e, seen: 1 })));
              });
            }}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Mark all seen
          </button>
        )}
      </div>
      <ul className="space-y-1.5">
        {events.slice(0, 15).map((event) => {
          const meta = EVENT_ICONS[event.event_type] || EVENT_ICONS.new_article;
          return (
            <li key={event.id} className={`flex items-start gap-2 text-sm ${!event.seen ? "font-medium" : "text-gray-500"}`}>
              <span className={`${meta.color} text-xs mt-0.5`}>[{meta.label}]</span>
              <span className="font-mono text-xs text-gray-400 w-12">{event.ticker}</span>
              <span className="flex-1">{event.headline}</span>
              <span className="text-xs text-gray-300">{event.event_date?.split("T")[0]}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

### Modify: RegimePage.jsx — Add earnings calendar

Add below the existing regime cards:

```jsx
<EarningsCalendar />
```

### New component: frontend/src/components/EarningsCalendar.jsx

```jsx
/**
 * Upcoming earnings dates for watchlist tickers.
 * Shown on Regime page so you know what's coming.
 * Ties into the 14-day options proximity rule.
 */
import { useState, useEffect } from "react";
import { fetchEarningsCalendar } from "../api";

export default function EarningsCalendar() {
  const [earnings, setEarnings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEarningsCalendar()
      .then((data) => setEarnings(data.upcoming_earnings || []))
      .finally(() => setLoading(false));
  }, []);

  if (loading || earnings.length === 0) return null;

  // Only show next 14 days
  const now = new Date();
  const twoWeeks = new Date(now.getTime() + 14 * 86400000);
  const upcoming = earnings.filter((e) => {
    const d = new Date(e.earnings_date);
    return d >= now && d <= twoWeeks;
  });

  if (upcoming.length === 0) return null;

  return (
    <div className="mt-4 bg-white rounded-lg border border-[#e2e4e8] p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-2">
        Watchlist Earnings — Next 14 Days
      </h3>
      <div className="flex flex-wrap gap-3">
        {upcoming.map((e) => (
          <div key={e.ticker} className="flex items-center gap-1.5 bg-amber-50 border border-amber-200 rounded px-2 py-1">
            <span className="font-mono text-sm font-medium">{e.ticker}</span>
            <span className="text-xs text-amber-600">
              {new Date(e.earnings_date).toLocaleDateString("en-GB", { month: "short", day: "numeric" })}
            </span>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400 mt-2">
        Options rule: No new positions within 14 days of earnings.
      </p>
    </div>
  );
}
```

### Modify: frontend/src/api.js — Add new fetch helpers

```javascript
// Research endpoints
export const fetchResearch = (ticker) =>
  fetch(`/api/research/${ticker}`).then((r) => r.json());

export const fetchSentiment = (ticker) =>
  fetch(`/api/research/${ticker}/sentiment`).then((r) => r.json());

export const fetchWatchlistDigest = () =>
  fetch("/api/watchlist/digest").then((r) => r.json());

export const markDigestSeen = (eventIds) =>
  fetch("/api/research/digest/mark-seen", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_ids: eventIds }),
  }).then((r) => r.json());

export const fetchEarningsCalendar = () =>
  fetch("/api/regime/earnings-calendar").then((r) => r.json());
```

---

## Task R4: Tests

### tests/test_research.py

```python
from unittest.mock import patch, MagicMock
from backend.services.research import fetch_seeking_alpha, get_research_for_claude
from backend.services.sentiment import _format_sentiment
from backend.services.digest import _save_digest_event, get_digest


def test_format_sentiment_bearish_is_high_interest():
    """Contrarian rule: bearish crowd = high interest."""
    result = _format_sentiment({
        "av_sentiment_score": -0.4,
        "av_sentiment_label": "Bearish",
        "finnhub_consensus": "sell",
        "finnhub_recent_change": "downgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "HIGH_INTEREST"
    assert "NEGATIVE_SENTIMENT" in result["contrarian_signals"]
    assert "ANALYSTS_BEARISH" in result["contrarian_signals"]


def test_format_sentiment_bullish_is_consensus():
    """Contrarian rule: bullish crowd = less edge."""
    result = _format_sentiment({
        "av_sentiment_score": 0.5,
        "av_sentiment_label": "Bullish",
        "finnhub_consensus": "buy",
        "finnhub_recent_change": "upgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "CONSENSUS"
    assert len(result["contrarian_signals"]) == 0


def test_format_sentiment_downgrade_is_moderate():
    """Downgrade alone = moderate interest."""
    result = _format_sentiment({
        "av_sentiment_score": 0.1,
        "av_sentiment_label": "Neutral",
        "finnhub_consensus": "hold",
        "finnhub_recent_change": "downgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "MODERATE_INTEREST"
    assert "RECENT_DOWNGRADE" in result["contrarian_signals"]


def test_research_for_claude_returns_string():
    """Bridge context should be a formatted string."""
    with patch("backend.services.research.get_all_research") as mock:
        mock.return_value = {
            "seeking_alpha": [{"title": "Test Article", "summary": "Good read", "published_date": "2026-04-01"}],
            "substack": [],
            "total_items": 1,
        }
        result = get_research_for_claude("AAPL")
        assert "Test Article" in result
        assert "Research Context for AAPL" in result
```

### tests/test_digest.py

```python
from backend.services.digest import get_digest
from backend.database import init_db, get_db


def test_digest_returns_list(tmp_path, monkeypatch):
    """Digest should return a list of events."""
    # Use temp DB
    from backend import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    init_db()

    events = get_digest(tickers=["AAPL"])
    assert isinstance(events, list)
```

---

## Task R5: MCP Server Additions (Optional, Post-Phase 2)

These are recommendations for MCP servers to install in Claude Desktop/Code config for enhanced research during deep dives. Not required for the app to function.

### SEC EDGAR MCP

```json
{
  "mcpServers": {
    "sec-edgar": {
      "command": "uvx",
      "args": ["sec-edgar-mcp"]
    }
  }
}
```

**Use case:** During deep dives, ask Claude to pull specific 10-K sections, risk factors, or management discussion. Complements the research layer by giving Claude direct filing access.

### FRED MCP

```json
{
  "mcpServers": {
    "fred": {
      "command": "uvx",
      "args": ["fred-mcp-server"]
    }
  }
}
```

**Use case:** During regime analysis, ask Claude about yield curve inversion, credit spreads, or GDP trends. Adds macro context to the regime verdict.

---

## Integration Sequence

Build these tasks in this order, slotting into the existing plan:

| When | Task | What | Depends On |
|------|------|------|-----------|
| After Task 1 | R1a | Add new tables to `database.py` + config to `config.py` | Task 1 complete |
| After Task 3 | R1b | Create `research.py`, `sentiment.py`, `transcripts.py`, `digest.py` services | Task 3 (market_data exists) |
| After Task 9 | R1c | Create `routers/research.py` + modify existing routers | Task 9 (all routers exist) |
| After Task 9 | R2 | Modify bridge script with `--context` flag | Task 8 (bridge exists) |
| During Task 10 | R3a | Add `SentimentBadge` to `StockCard` in screener | Task 10 in progress |
| During Task 11 | R3b | Add `ResearchPanel` as 9th section in deep dive | Task 11 in progress |
| During Task 12 | R3c | Add `DigestList` to watchlist, `EarningsCalendar` to regime | Task 12 in progress |
| After Task 12 | R4 | Write and run research tests | All code exists |

**Key principle:** Research services are built early (after Task 3) so they're available when the frontend tasks (10-12) need them. But they never block the critical path — every research call is wrapped in try/except and fails silently.

---

## Rate Limit Budget

| API | Free Limit | Our Usage | Headroom |
|-----|-----------|-----------|----------|
| **Alpha Vantage** | 25 calls/day | ~1 per screener hit (max 15-20 B1/B2 candidates) | Tight — cache aggressively |
| **Finnhub** | 60 calls/min | ~3 per ticker (sentiment + transcript + insider) | Comfortable |
| **FMP** | 250 calls/day | ~1 per watchlist ticker (press releases) | Comfortable |
| **Seeking Alpha RSS** | Unlimited | ~1 per deep dive + watchlist ticker | No concern |
| **Substack RSS** | Unlimited | ~4 feeds per deep dive | No concern |

**Mitigation for AV tight budget:** Only fetch sentiment for stocks that pass screener gates. With typical 10-20 B1/B2 hits per scan, this stays within the 25/day limit. Cache for 12 hours.

---

## What This Does NOT Add

- No new pages or standalone news feeds
- No real-time notifications or alerts
- No Reddit sentiment (too noisy for contrarian value)
- No social buzz or trending stocks
- No news for stocks not in watchlist/screener hits
- No auto-refreshing or polling
- No YouTube integration in the app (keep for manual Claude sessions)
- No "AI summary" of articles (that's what the deep dive is for)

---

## Summary: Before vs After

| Feature | Before (Phase 1 only) | After (with Research Layer) |
|---------|----------------------|---------------------------|
| **Screener results** | Numbers only | Numbers + sentiment + analyst trend (contrarian-inverted) |
| **Deep dive** | 8 sections, AI-blind to latest news | 9 sections, AI reads SA articles + earnings transcripts |
| **Watchlist** | Static list | Static list + "What Changed" digest (insider buys, press, downgrades) |
| **Regime** | SPY/QQQ/VIX only | SPY/QQQ/VIX + upcoming watchlist earnings calendar |
| **Claude bridge** | Writes analysis cold | Pre-loads research context, then writes informed analysis |
| **Options** | No change needed | No change needed (already has earnings proximity) |
| **Positions** | No change needed | No change needed (already has P&L) |
