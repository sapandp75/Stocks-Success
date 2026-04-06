"""
Research Intelligence — RSS fetcher + aggregator + SQLite cache.
Only fetches for tickers you care about. Caches aggressively.
"""
import re
import feedparser
from datetime import datetime
from backend.database import get_db
from backend.config import (
    RESEARCH_CONFIG, SA_RSS_TEMPLATE, SUBSTACK_FEEDS,
)


def _is_fresh(fetched_at: str, ttl_hours: int) -> bool:
    if not fetched_at:
        return False
    fetched = datetime.fromisoformat(fetched_at)
    return (datetime.now() - fetched).total_seconds() < ttl_hours * 3600


def _save_research(ticker: str, source: str, content_type: str,
                   title: str, summary: str, url: str,
                   published_date: str, raw_json: str = ""):
    db = get_db()
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
        pass

    return _get_cached(ticker, "seeking_alpha")


def fetch_substack_mentions(ticker: str) -> list[dict]:
    """Check curated Substack feeds for mentions of this ticker."""
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
    """Aggregate all research for a ticker."""
    sa_articles = fetch_seeking_alpha(ticker)
    substack = fetch_substack_mentions(ticker)

    return {
        "ticker": ticker,
        "seeking_alpha": sa_articles,
        "substack": substack,
        "total_items": len(sa_articles) + len(substack),
    }


def get_research_for_claude(ticker: str) -> str:
    """Format research as plain text for Claude's deep dive context."""
    research = get_all_research(ticker)
    sections = []

    if research["seeking_alpha"]:
        sections.append("## Recent Seeking Alpha Articles")
        for a in research["seeking_alpha"]:
            sections.append(f"- **{a['title']}** ({a['published_date']})")
            if a['summary']:
                clean = re.sub(r'<[^>]+>', '', a['summary'])
                sections.append(f"  {clean[:300]}...")

    if research["substack"]:
        sections.append("\n## Value Investing Newsletter Mentions")
        for a in research["substack"]:
            sections.append(f"- **{a['title']}** ({a['published_date']})")
            if a['summary']:
                clean = re.sub(r'<[^>]+>', '', a['summary'])
                sections.append(f"  {clean[:300]}...")

    if not sections:
        return f"No recent research articles found for {ticker}."

    return f"# Research Context for {ticker}\n\n" + "\n".join(sections)
