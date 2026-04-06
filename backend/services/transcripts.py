"""
Earnings Call Transcripts — via Finnhub API.
Fetched on-demand for deep dives, cached in research_cache.
"""
import os
import json
import httpx
from datetime import datetime, timedelta
from backend.database import get_db
from backend.config import RESEARCH_CONFIG

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")


def fetch_latest_transcript(ticker: str) -> dict | None:
    """Fetch the most recent earnings call transcript. Cached in research_cache."""
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
        now = datetime.now()

        cal_url = f"https://finnhub.io/api/v1/stock/earnings?symbol={ticker}&token={FINNHUB_API_KEY}"
        cal_resp = httpx.get(cal_url, timeout=10)
        earnings = cal_resp.json()

        if not earnings:
            return None

        latest = earnings[0]
        quarter = latest.get("quarter", 0)
        year = latest.get("year", now.year)

        transcript_url = f"https://finnhub.io/api/v1/stock/transcripts?symbol={ticker}&token={FINNHUB_API_KEY}"
        transcript_resp = httpx.get(transcript_url, timeout=15)
        transcript_list = transcript_resp.json()

        if not transcript_list or "transcripts" not in transcript_list:
            return None

        transcripts = transcript_list["transcripts"]
        if not transcripts:
            return None

        latest_id = transcripts[0].get("id")
        if not latest_id:
            return None

        full_url = f"https://finnhub.io/api/v1/stock/transcripts?id={latest_id}&token={FINNHUB_API_KEY}"
        full_resp = httpx.get(full_url, timeout=15)
        full = full_resp.json()

        if not full or "transcript" not in full:
            return None

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
    if len(full_text) > 8000:
        full_text = full_text[:8000] + "\n\n[... transcript truncated for context length ...]"

    return f"## Latest Earnings Call: {transcript['title']}\n\n{full_text}"
