"""Gemini 2.5 Pro integration for deep dive analysis."""

import os
import re
import time
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from backend.config import GEMINI_CONFIG

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "deep_dive_v2.txt"


class GeminiRateLimiter:
    """Track RPM and RPD limits for Gemini API. Thread-safe."""

    def __init__(self, max_rpm: int = None, max_rpd: int = None):
        self.max_rpm = max_rpm or GEMINI_CONFIG["max_rpm"]
        self.max_rpd = max_rpd or GEMINI_CONFIG["max_rpd"]
        self._minute_timestamps: deque = deque()
        self._day_timestamps: deque = deque()
        self._lock = threading.Lock()

    def _prune(self):
        now = time.time()
        while self._minute_timestamps and now - self._minute_timestamps[0] > 60:
            self._minute_timestamps.popleft()
        while self._day_timestamps and now - self._day_timestamps[0] > 86400:
            self._day_timestamps.popleft()

    def acquire(self) -> bool:
        """Atomic check-and-record. Returns True if request is allowed."""
        with self._lock:
            self._prune()
            if (len(self._minute_timestamps) < self.max_rpm
                    and len(self._day_timestamps) < self.max_rpd):
                now = time.time()
                self._minute_timestamps.append(now)
                self._day_timestamps.append(now)
                return True
            return False

    def seconds_until_available(self) -> int:
        with self._lock:
            self._prune()
            if (len(self._minute_timestamps) < self.max_rpm
                    and len(self._day_timestamps) < self.max_rpd):
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

    if "quarterly" in context and context["quarterly"]:
        lines = ["QUARTERLY DATA:"]
        q = context["quarterly"]
        if isinstance(q, dict):
            for metric in ["revenue", "eps", "fcf"]:
                if metric in q and q[metric]:
                    lines.append(f"  {metric.upper()} (Q/Q, Y/Y):")
                    for entry in q[metric][:8]:
                        qoq = f"Q/Q: {entry.get('qoq', 'N/A')}" if entry.get('qoq') is not None else "Q/Q: N/A"
                        yoy = f"Y/Y: {entry.get('yoy', 'N/A')}" if entry.get('yoy') is not None else "Y/Y: N/A"
                        lines.append(f"    {entry.get('quarter', '?')}: {entry.get('value', 'N/A')} ({qoq}, {yoy})")
        sections.append("\n".join(lines))

    if "growth_metrics" in context and context["growth_metrics"]:
        lines = ["GROWTH METRICS:"]
        gm = context["growth_metrics"]
        if isinstance(gm, dict):
            for k, v in gm.items():
                if k != "roic_trend":
                    lines.append(f"  - {k}: {v}")
            if gm.get("roic_trend"):
                lines.append("  ROIC Trend:")
                for entry in gm["roic_trend"]:
                    lines.append(f"    {entry.get('year', '?')}: {entry.get('roic', 'N/A')}")
        sections.append("\n".join(lines))

    if "forward_estimates" in context and context["forward_estimates"]:
        lines = ["FORWARD ESTIMATES:"]
        fe = context["forward_estimates"]
        if isinstance(fe, dict):
            for k, v in fe.items():
                if k != "earnings_history":
                    lines.append(f"  - {k}: {v}")
            if fe.get("earnings_history"):
                lines.append("  Earnings History (last 4Q):")
                for q in fe["earnings_history"][:4]:
                    lines.append(f"    {q.get('date', '?')}: actual={q.get('eps_actual', 'N/A')} vs est={q.get('eps_estimate', 'N/A')} surprise={q.get('surprise_pct', 'N/A')}%")
        sections.append("\n".join(lines))

    if "fund_flow" in context and context["fund_flow"]:
        lines = ["13F FUND FLOW:"]
        ff = context["fund_flow"]
        if isinstance(ff, dict):
            if ff.get("holder_type_breakdown"):
                lines.append(f"  Holder types: {ff['holder_type_breakdown']}")
            delta = ff.get("delta")
            if delta:
                lines.append(f"  Net direction: {delta['summary']['net_direction']}")
                lines.append(f"  New positions: {delta['summary']['new_count']}, Exits: {delta['summary']['exit_count']}")
                for pos in delta.get("new_positions", [])[:3]:
                    lines.append(f"    NEW: {pos['fund_name']} ({pos['fund_type']}): {pos['shares']} shares")
                for pos in delta.get("exits", [])[:3]:
                    lines.append(f"    EXIT: {pos['fund_name']} ({pos['fund_type']}): {pos['shares']} shares")
        sections.append("\n".join(lines))

    if "external_targets" in context and context["external_targets"]:
        lines = ["PRICE TARGET COMPARISON:"]
        et = context["external_targets"]
        if isinstance(et, dict):
            for k, v in et.items():
                lines.append(f"  - {k}: {v}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


# Mapping from various heading patterns to canonical section keys
_SECTION_MAP = {
    "gates": "gates_summary",
    "business summary": "gates_summary",
    "section 1": "gates_summary",
    "key fundamentals": "key_fundamentals",
    "section 2": "key_fundamentals",
    "growth": "growth",
    "historical & forward": "growth",
    "section 3": "growth",
    "bear case": "bear_case",
    "section 4": "bear_case",
    "bull case": "bull_case",
    "section 5": "bull_case",
    "valuation": "valuation",
    "price targets": "valuation",
    "section 6": "valuation",
    "moat": "moat",
    "section 7": "moat",
    "growth opportunities": "opportunities_threats",
    "threats": "opportunities_threats",
    "section 8": "opportunities_threats",
    "13f": "smart_money",
    "smart money": "smart_money",
    "section 9": "smart_money",
    "verdict": "verdict",
    "scenarios": "verdict",
    "section 10": "verdict",
    # Legacy compatibility
    "data snapshot": "gates_summary",
    "first impression": "key_fundamentals",
    "whole picture": "moat",
    "self-review": "smart_money",
    "self review": "smart_money",
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

        # Map heading to canonical key (try longest patterns first to avoid partial matches)
        heading_lower = heading.lower()
        key = None
        for pattern_str, section_key in sorted(_SECTION_MAP.items(), key=lambda x: len(x[0]), reverse=True):
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


def _format_dict_section(data) -> str:
    """Generic formatter for dict/list context data."""
    if isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 5:
                lines.append(f"- {k}: [{len(v)} items]")
                for item in v[:5]:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    return str(data)


def generate_deep_dive(ticker: str, context: dict) -> dict:
    """Generate a full deep dive analysis using Gemini 2.5 Pro.

    Returns a dict with section keys + metadata, or {"error": "message"} on failure.
    """
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY is not set"}

    if not _rate_limiter.acquire():
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

        edgar_context = ""
        if "edgar" in context:
            ed = context["edgar"]
            lines = []
            if isinstance(ed, dict):
                if "filings" in ed and ed["filings"]:
                    lines.append("Recent SEC Filings:")
                    for f in ed["filings"]:
                        lines.append(f"  - {f.get('form', '')} ({f.get('filing_date', '')}): {f.get('description', '')}")
                if "insider_transactions" in ed:
                    ins_data = ed["insider_transactions"]
                    lines.append(f"SEC Form 4 Insider Activity: {ins_data.get('net_sentiment', 'N/A')} "
                                 f"(Buys: {ins_data.get('buy_count', 0)}, Sells: {ins_data.get('sell_count', 0)})")
                    for txn in ins_data.get("transactions", [])[:5]:
                        lines.append(f"  - {txn.get('insider', '')}: {txn.get('type', '')} "
                                     f"{txn.get('shares', 0)} shares ({txn.get('date', '')})")
                if "institutional_holders" in ed:
                    holders = ed["institutional_holders"]
                    if holders.get("top_holders"):
                        lines.append("Top Institutional Holders:")
                        for h in holders["top_holders"][:5]:
                            val = h.get("value_usd", 0)
                            val_str = f"${val:,.0f}" if val else "N/A"
                            pct = h.get("pct_held", 0)
                            pct_str = f" ({pct:.1%})" if pct else ""
                            lines.append(f"  - {h.get('fund_name', '')}: {val_str}{pct_str}")
            edgar_context = "\n".join(lines) if lines else "No SEC EDGAR data available."

        # Get company name from fundamentals
        company_name = "Unknown"
        if "fundamentals" in context and isinstance(context["fundamentals"], dict):
            company_name = context["fundamentals"].get("company_name", context["fundamentals"].get("name", ticker))

        # Build new context fields
        quarterly_context = ""
        if "quarterly" in context:
            quarterly_context = _format_dict_section(context["quarterly"])

        growth_metrics_context = ""
        if "growth_metrics" in context:
            growth_metrics_context = _format_dict_section(context["growth_metrics"])

        forward_estimates_context = ""
        if "forward_estimates" in context:
            forward_estimates_context = _format_dict_section(context["forward_estimates"])

        targets_context = ""
        if "external_targets" in context:
            targets_context = _format_dict_section(context["external_targets"])

        fund_flow_context = ""
        if "fund_flow" in context:
            fund_flow_context = _format_dict_section(context["fund_flow"])

        prompt = template.format(
            ticker=ticker,
            company_name=company_name,
            data_context=data_context or "No data available. Apply fail-closed: treat all missing data as negative.",
            quarterly_context=quarterly_context or "No quarterly data available.",
            growth_metrics_context=growth_metrics_context or "No growth metrics available.",
            forward_estimates_context=forward_estimates_context or "No forward estimates available.",
            peer_context=peer_context or "No peer data available.",
            analyst_context=analyst_context or "No analyst data available.",
            targets_context=targets_context or "No price target comparison available.",
            insider_context=insider_context or "No insider data available.",
            fund_flow_context=fund_flow_context or "No 13F fund flow data available.",
            edgar_context=edgar_context or "No SEC EDGAR data available.",
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
