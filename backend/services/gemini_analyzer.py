"""Gemini 2.5 Pro integration for deep dive analysis."""

import os
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from backend.config import GEMINI_CONFIG

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "deep_dive.txt"


class GeminiRateLimiter:
    """Track RPM and RPD limits for Gemini API."""

    def __init__(self, max_rpm: int = None, max_rpd: int = None):
        self.max_rpm = max_rpm or GEMINI_CONFIG["max_rpm"]
        self.max_rpd = max_rpd or GEMINI_CONFIG["max_rpd"]
        self._minute_timestamps: deque = deque()
        self._day_timestamps: deque = deque()

    def _prune(self):
        now = time.time()
        while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
            self._minute_timestamps.popleft()
        while self._day_timestamps and now - self._day_timestamps[0] > 86400:
            self._day_timestamps.popleft()

    def can_request(self) -> bool:
        self._prune()
        return (
            len(self._minute_timestamps) < self.max_rpm
            and len(self._day_timestamps) < self.max_rpd
        )

    def record_request(self):
        now = time.time()
        self._minute_timestamps.append(now)
        self._day_timestamps.append(now)

    def seconds_until_available(self) -> int:
        self._prune()
        if self.can_request():
            return 0
        if len(self._day_timestamps) >= self.max_rpd:
            return int(86400 - (time.time() - self._day_timestamps[0])) + 1
        if len(self._minute_timestamps) >= self.max_rpm:
            return int(60 - (time.time() - self._minute_timestamps[0])) + 1
        return 0


# Module-level singleton
_rate_limiter = GeminiRateLimiter()


def _build_context_string(context: dict) -> str:
    """Format a dict of Tier 1 data into readable text for the prompt."""
    if not context:
        return ""

    sections = []

    if "fundamentals" in context and context["fundamentals"]:
        lines = ["FUNDAMENTALS:"]
        fund = context["fundamentals"]
        if isinstance(fund, dict):
            for k, v in fund.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  {fund}")
        sections.append("\n".join(lines))

    if "technicals" in context and context["technicals"]:
        lines = ["TECHNICALS:"]
        tech = context["technicals"]
        if isinstance(tech, dict):
            for k, v in tech.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  {tech}")
        sections.append("\n".join(lines))

    if "financial_history" in context and context["financial_history"]:
        lines = ["FINANCIAL HISTORY:"]
        fh = context["financial_history"]
        if isinstance(fh, dict):
            for k, v in fh.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(fh, list):
            for item in fh:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {fh}")
        sections.append("\n".join(lines))

    if "insider_activity" in context and context["insider_activity"]:
        lines = ["INSIDER ACTIVITY:"]
        ins = context["insider_activity"]
        if isinstance(ins, dict):
            for k, v in ins.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(ins, list):
            for item in ins:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {ins}")
        sections.append("\n".join(lines))

    if "institutional" in context and context["institutional"]:
        lines = ["INSTITUTIONAL HOLDERS:"]
        inst = context["institutional"]
        if isinstance(inst, dict):
            for k, v in inst.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(inst, list):
            for item in inst:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {inst}")
        sections.append("\n".join(lines))

    if "analyst" in context and context["analyst"]:
        lines = ["ANALYST CONSENSUS:"]
        an = context["analyst"]
        if isinstance(an, dict):
            for k, v in an.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  {an}")
        sections.append("\n".join(lines))

    if "sentiment" in context and context["sentiment"]:
        lines = ["SENTIMENT:"]
        sent = context["sentiment"]
        if isinstance(sent, dict):
            for k, v in sent.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  {sent}")
        sections.append("\n".join(lines))

    if "peers" in context and context["peers"]:
        lines = ["PEER COMPARISON:"]
        peers = context["peers"]
        if isinstance(peers, dict):
            for k, v in peers.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(peers, list):
            for item in peers:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {peers}")
        sections.append("\n".join(lines))

    if "regime" in context and context["regime"]:
        lines = ["MARKET REGIME:"]
        reg = context["regime"]
        if isinstance(reg, dict):
            for k, v in reg.items():
                lines.append(f"  - {k}: {v}")
        else:
            lines.append(f"  {reg}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


# Mapping from various heading patterns to canonical section keys
_SECTION_MAP = {
    "data snapshot": "data_snapshot",
    "section 1": "data_snapshot",
    "first impression (deep)": "first_impression",
    "first impression deep": "first_impression",
    "section 2": "first_impression",
    "bear case": "bear_case",
    "section 3": "bear_case",
    "bull case": "bull_case",
    "section 4": "bull_case",
    "valuation": "valuation",
    "section 5": "valuation",
    "whole picture": "whole_picture",
    "section 6": "whole_picture",
    "self-review": "self_review",
    "self review": "self_review",
    "section 7": "self_review",
    "verdict": "verdict",
    "section 8": "verdict",
    "entry grid": "verdict",
    "exit playbook": "verdict",
}


def _parse_sections(text: str) -> dict:
    """Parse Gemini's markdown response into named sections."""
    if not text or not text.strip():
        return {}

    # Find all markdown headings (### or ##)
    pattern = r"^#{2,3}\s+(.+)$"
    matches = list(re.finditer(pattern, text, re.MULTILINE))

    if not matches:
        return {"raw": text.strip()}

    sections = {}
    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        # Map heading to canonical key
        heading_lower = heading.lower()
        key = None
        for pattern_str, section_key in _SECTION_MAP.items():
            if pattern_str in heading_lower:
                key = section_key
                break

        if key:
            # Append if key already exists (e.g., verdict sub-sections)
            if key in sections:
                sections[key] += "\n\n" + content
            else:
                sections[key] = content

    return sections


def generate_deep_dive(ticker: str, context: dict) -> dict:
    """Generate a full deep dive analysis using Gemini 2.5 Pro.

    Returns a dict with section keys + metadata, or {"error": "message"} on failure.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set"}

    if not _rate_limiter.can_request():
        wait = _rate_limiter.seconds_until_available()
        return {"error": f"Rate limit exceeded. Try again in {wait} seconds"}

    try:
        # Read prompt template
        template = PROMPT_PATH.read_text()

        # Build context strings
        data_context = _build_context_string(context)
        peer_context = ""
        analyst_context = ""
        insider_context = ""
        institutional_context = ""

        if "peers" in context:
            peers = context["peers"]
            if isinstance(peers, dict):
                peer_context = "\n".join(f"- {k}: {v}" for k, v in peers.items())
            elif isinstance(peers, list):
                peer_context = "\n".join(f"- {p}" for p in peers)

        if "analyst" in context:
            an = context["analyst"]
            if isinstance(an, dict):
                analyst_context = "\n".join(f"- {k}: {v}" for k, v in an.items())

        if "insider_activity" in context:
            ins = context["insider_activity"]
            if isinstance(ins, dict):
                insider_context = "\n".join(f"- {k}: {v}" for k, v in ins.items())
            elif isinstance(ins, list):
                insider_context = "\n".join(f"- {i}" for i in ins)

        if "institutional" in context:
            inst = context["institutional"]
            if isinstance(inst, dict):
                institutional_context = "\n".join(f"- {k}: {v}" for k, v in inst.items())
            elif isinstance(inst, list):
                institutional_context = "\n".join(f"- {i}" for i in inst)

        # Get company name from fundamentals
        company_name = "Unknown"
        if "fundamentals" in context and isinstance(context["fundamentals"], dict):
            company_name = context["fundamentals"].get("company_name", context["fundamentals"].get("name", ticker))

        prompt = template.format(
            ticker=ticker,
            company_name=company_name,
            data_context=data_context or "No data available. Apply fail-closed: treat all missing data as negative.",
            peer_context=peer_context or "No peer data available.",
            analyst_context=analyst_context or "No analyst data available.",
            insider_context=insider_context or "No insider data available.",
            institutional_context=institutional_context or "No institutional data available.",
        )

        # Call Gemini API
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_CONFIG["model"])
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=GEMINI_CONFIG["max_output_tokens"],
                temperature=GEMINI_CONFIG["temperature"],
            ),
        )

        _rate_limiter.record_request()

        raw_text = response.text
        sections = _parse_sections(raw_text)

        result = {
            "ticker": ticker,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": GEMINI_CONFIG["model"],
            "raw_text": raw_text,
        }
        result.update(sections)
        return result

    except Exception as e:
        return {"error": str(e)}
