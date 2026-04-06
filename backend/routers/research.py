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
from backend.validators import validate_ticker

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/{ticker}")
def get_research_for_ticker(ticker: str):
    """Get all research context for a single ticker."""
    ticker = validate_ticker(ticker)
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
    return fetch_sentiment(validate_ticker(ticker))


@router.post("/digest/mark-seen")
def mark_seen(data: dict):
    """Mark digest events as seen."""
    event_ids = data.get("event_ids", [])
    if event_ids:
        mark_digest_seen(event_ids)
    return {"status": "ok", "marked": len(event_ids)}
