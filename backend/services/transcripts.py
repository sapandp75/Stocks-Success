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
    with get_db() as db:
        cached = db.execute("""
            SELECT title, summary, raw_json, published_date, fetched_at
            FROM research_cache
            WHERE ticker = ? AND content_type = 'transcript'
            ORDER BY published_date DESC LIMIT 1
        """, (ticker,)).fetchone()

    if cached:
        fetched = datetime.fromisoformat(cached["fetched_at"])
        max_age = timedelta(days=RESEARCH_CONFIG["max_transcript_age_days"])
        if (datetime.now() - fetched) < max_age:
            return dict(cached)

    if not FINNHUB_API_KEY:
        return None

    # Try Finnhub transcript API (requires premium plan)
    try:
        transcript_url = f"https://finnhub.io/api/v1/stock/transcripts?symbol={ticker}&token={FINNHUB_API_KEY}"
        transcript_resp = httpx.get(transcript_url, timeout=15)

        if transcript_resp.status_code == 403:
            # Premium-only endpoint — fall back to earnings summary
            return _earnings_summary_fallback(ticker)

        transcript_list = transcript_resp.json()

        if not transcript_list or "transcripts" not in transcript_list:
            return _earnings_summary_fallback(ticker)

        transcripts = transcript_list["transcripts"]
        if not transcripts:
            return _earnings_summary_fallback(ticker)

        latest_id = transcripts[0].get("id")
        if not latest_id:
            return _earnings_summary_fallback(ticker)

        full_url = f"https://finnhub.io/api/v1/stock/transcripts?id={latest_id}&token={FINNHUB_API_KEY}"
        full_resp = httpx.get(full_url, timeout=15)
        full = full_resp.json()

        if not full or "transcript" not in full:
            return _earnings_summary_fallback(ticker)

        segments = full["transcript"]
        text_parts = []
        for seg in segments:
            speaker = seg.get("name", "Unknown")
            speech = seg.get("speech", [])
            text = " ".join(speech) if isinstance(speech, list) else str(speech)
            text_parts.append(f"**{speaker}:** {text}")

        full_text = "\n\n".join(text_parts)
        title = f"Earnings Call Transcript"
        summary = full_text[:500]

        with get_db() as db:
            db.execute("""
                INSERT INTO research_cache (ticker, source, content_type, title, summary, url, published_date, raw_json)
                VALUES (?, 'finnhub_transcript', 'transcript', ?, ?, '', ?, ?)
            """, (ticker, title, summary, transcripts[0].get("time", ""), json.dumps({"text": full_text})))
            db.commit()

        return {"title": title, "summary": summary, "full_text": full_text}

    except Exception:
        return _earnings_summary_fallback(ticker)


def _earnings_summary_fallback(ticker: str) -> dict | None:
    """Fallback: build earnings summary from yfinance when Finnhub transcripts unavailable."""
    try:
        import yfinance as yf
        import pandas as pd

        stock = yf.Ticker(ticker)
        ed = stock.earnings_dates
        if ed is None or ed.empty:
            return None

        lines = []
        for date, row in ed.head(4).iterrows():
            eps_est = row.get("EPS Estimate")
            eps_act = row.get("Reported EPS")
            surprise = row.get("Surprise(%)")
            date_str = date.strftime("%Y-%m-%d")

            if pd.notna(eps_act):
                beat = "BEAT" if surprise and surprise > 0 else "MISS" if surprise and surprise < 0 else "MET"
                lines.append(
                    f"**{date_str}:** EPS ${eps_act:.2f} vs est ${eps_est:.2f} "
                    f"({beat}, {surprise:+.1f}%)" if pd.notna(eps_est) and pd.notna(surprise)
                    else f"**{date_str}:** EPS ${eps_act:.2f}"
                )
            elif pd.notna(eps_est):
                lines.append(f"**{date_str}:** Upcoming — EPS estimate ${eps_est:.2f}")

        if not lines:
            return None

        title = f"{ticker} Earnings History (last 4 quarters)"
        full_text = "\n".join(lines)
        return {"title": title, "summary": full_text, "full_text": full_text}

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
