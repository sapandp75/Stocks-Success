import json
import logging
import re
from fastapi import APIRouter
from backend.services.market_data import (
    get_stock_fundamentals, get_fcf_3yr_average, get_sbc, get_net_debt,
)
from backend.services.dcf_calculator import (
    calculate_dcf, reverse_dcf, build_sensitivity_matrix, adjust_fcf_for_sbc,
)
from backend.database import get_db
from backend.validators import validate_ticker, DeepDivePayload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deep-dive", tags=["deep-dive"])


@router.get("/{ticker}")
def get_deep_dive_data(ticker: str):
    """Get all quantitative data for a deep dive + any saved AI analysis."""
    ticker = validate_ticker(ticker)
    fundamentals_result = get_stock_fundamentals(ticker)
    fundamentals = fundamentals_result.value

    # --- GATES CHECK ---
    from backend.config import DEEP_DIVE_GATES
    gates = {
        "market_cap": fundamentals.get("market_cap"),
        "avg_volume": fundamentals.get("avg_volume"),
        "min_market_cap": DEEP_DIVE_GATES["min_market_cap"],
        "min_avg_volume": DEEP_DIVE_GATES["min_avg_volume"],
        "passes_market_cap": (fundamentals.get("market_cap") or 0) >= DEEP_DIVE_GATES["min_market_cap"],
        "passes_volume": (fundamentals.get("avg_volume") or 0) >= DEEP_DIVE_GATES["min_avg_volume"],
    }
    gates["passes_all"] = gates["passes_market_cap"] and gates["passes_volume"]

    # --- FCF + DCF (existing) ---
    fcf_3yr = get_fcf_3yr_average(ticker)
    sbc = get_sbc(ticker)
    revenue = fundamentals.get("total_revenue")
    net_debt = get_net_debt(ticker)
    shares = fundamentals.get("shares_outstanding")
    price = fundamentals.get("price")

    starting_fcf = fcf_3yr or fundamentals.get("free_cash_flow")
    if starting_fcf and sbc:
        starting_fcf = adjust_fcf_for_sbc(starting_fcf, sbc, revenue)

    reverse_dcf_result = None
    if starting_fcf and shares and price and starting_fcf > 0:
        reverse_dcf_result = reverse_dcf(
            current_price=price, starting_fcf=starting_fcf,
            shares_outstanding=shares, net_debt=net_debt or 0,
        )

    forward_dcf = None
    sensitivity = None
    if starting_fcf and shares and starting_fcf > 0:
        forward_dcf = {
            "bear": calculate_dcf(starting_fcf, 0.05, 0.03, shares_outstanding=shares, net_debt=net_debt or 0),
            "base": calculate_dcf(starting_fcf, 0.12, 0.07, shares_outstanding=shares, net_debt=net_debt or 0),
            "bull": calculate_dcf(starting_fcf, 0.20, 0.12, shares_outstanding=shares, net_debt=net_debt or 0),
        }
        sensitivity = build_sensitivity_matrix(
            starting_fcf, 0.12, 0.07,
            shares_outstanding=shares, net_debt=net_debt or 0,
        )

    # --- SAVED AI ANALYSIS ---
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM deep_dives WHERE ticker = ? ORDER BY dive_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()

    ai_analysis = None
    if row:
        # Always build legacy keys from DB columns (frontend depends on these)
        ai_analysis = {
            "dive_date": row["dive_date"],
            "first_impression": row["ai_first_impression"],
            "bear_case_stock": row["ai_bear_case_stock"],
            "bear_case_business": row["ai_bear_case_business"],
            "bull_case_rebuttal": row["ai_bull_case_rebuttal"],
            "bull_case_upside": row["ai_bull_case_upside"],
            "whole_picture": row["ai_whole_picture"],
            "self_review": row["ai_self_review"],
            "verdict": row["ai_verdict"],
            "conviction": row["ai_conviction"],
            "entry_grid": json.loads(row["ai_entry_grid_json"]) if row["ai_entry_grid_json"] else None,
            "exit_playbook": row["ai_exit_playbook"],
            "next_review_date": row["ai_next_review_date"] if "ai_next_review_date" in row.keys() else None,
        }
        # Merge V2 sections on top (adds new keys, legacy keys preserved from columns)
        sections_json = row["ai_sections_json"] if "ai_sections_json" in row.keys() else None
        if sections_json:
            v2 = json.loads(sections_json)
            for k, v in v2.items():
                if k not in ai_analysis or ai_analysis[k] is None:
                    ai_analysis[k] = v

    # --- ENRICHMENTS (each in try/except — never blocks) ---
    technicals = None
    try:
        from backend.services.technicals import get_full_technicals
        technicals = get_full_technicals(ticker)
    except Exception:
        logger.warning("Failed to fetch technicals for %s", ticker, exc_info=True)

    financial_history = None
    try:
        from backend.services.financial_history import get_financial_history
        financial_history = get_financial_history(ticker)
    except Exception:
        logger.warning("Failed to fetch financial history for %s", ticker, exc_info=True)

    insider_activity = None
    try:
        from backend.services.institutional import get_insider_activity
        insider_activity = get_insider_activity(ticker)
    except Exception:
        logger.warning("Failed to fetch insider activity for %s", ticker, exc_info=True)

    institutional = None
    try:
        from backend.services.institutional import get_institutional_summary
        institutional = get_institutional_summary(ticker)
    except Exception:
        logger.warning("Failed to fetch institutional data for %s", ticker, exc_info=True)

    analyst = None
    try:
        from backend.services.sentiment import get_analyst_data
        analyst = get_analyst_data(ticker)
    except Exception:
        logger.warning("Failed to fetch analyst data for %s", ticker, exc_info=True)

    peers = None
    try:
        from backend.services.peers import get_peer_comparison
        peers = get_peer_comparison(ticker)
    except Exception:
        logger.warning("Failed to fetch peer comparison for %s", ticker, exc_info=True)

    edgar_data = None
    try:
        from backend.services.edgar import get_edgar_context
        edgar_data = get_edgar_context(ticker)
    except Exception:
        logger.warning("Failed to fetch SEC EDGAR data for %s", ticker, exc_info=True)

    research_context = None
    try:
        from backend.services.research import get_all_research
        from backend.services.sentiment import fetch_sentiment
        from backend.services.transcripts import fetch_latest_transcript
        r = get_all_research(ticker)
        s = fetch_sentiment(ticker)
        t = fetch_latest_transcript(ticker)
        research_context = {
            "articles": r.get("seeking_alpha", []),
            "newsletters": r.get("substack", []),
            "sentiment": s,
            "transcript_available": t is not None,
            "transcript_title": t["title"] if t else None,
        }
    except Exception:
        logger.warning("Failed to fetch research context for %s", ticker, exc_info=True)

    # --- NEW: Quarterly Data ---
    quarterly = None
    try:
        from backend.services.quarterly_data import get_quarterly_data
        quarterly = get_quarterly_data(ticker)
    except Exception:
        logger.warning("Failed to fetch quarterly data for %s", ticker, exc_info=True)

    # --- NEW: Growth Metrics ---
    growth_metrics = None
    try:
        from backend.services.growth_metrics import get_growth_metrics
        growth_metrics = get_growth_metrics(ticker)
        # Compute implied vs historical gap
        if growth_metrics and reverse_dcf_result and growth_metrics.get("revenue_cagr_3yr"):
            implied = reverse_dcf_result["implied_growth_rate"]
            historical = growth_metrics["revenue_cagr_3yr"]
            growth_metrics["implied_vs_historical_gap"] = round(implied - historical, 4)
    except Exception:
        logger.warning("Failed to fetch growth metrics for %s", ticker, exc_info=True)

    # --- NEW: Forward Estimates ---
    forward_estimates = None
    try:
        from backend.services.forward_estimates import get_forward_estimates
        forward_estimates = get_forward_estimates(ticker)
    except Exception:
        logger.warning("Failed to fetch forward estimates for %s", ticker, exc_info=True)

    # --- NEW: External Targets ---
    external_targets = None
    try:
        from backend.services.external_targets import get_external_targets, build_target_comparison
        raw_targets = get_external_targets(ticker)
        dcf_prices = {}
        if forward_dcf:
            dcf_prices = {
                "bear": forward_dcf["bear"]["intrinsic_value_per_share"],
                "base": forward_dcf["base"]["intrinsic_value_per_share"],
                "bull": forward_dcf["bull"]["intrinsic_value_per_share"],
            }
        external_targets = build_target_comparison(
            raw_targets.get("sources", {}), dcf_prices, price or 0,
        )
    except Exception:
        logger.warning("Failed to fetch external targets for %s", ticker, exc_info=True)

    # --- NEW: 13F Fund Flow ---
    fund_flow = None
    try:
        from backend.services.fund_flow import get_fund_flow
        fund_flow = get_fund_flow(ticker)
    except Exception:
        logger.warning("Failed to fetch fund flow for %s", ticker, exc_info=True)

    # --- Staleness ---
    staleness_days = None
    if ai_analysis and ai_analysis.get("dive_date"):
        from datetime import datetime
        try:
            dive_dt = datetime.fromisoformat(ai_analysis["dive_date"])
            staleness_days = (datetime.now() - dive_dt).days
        except Exception:
            pass

    return {
        "ticker": ticker,
        "gates": gates,
        "fundamentals": fundamentals,
        "data_quality": {
            "source": fundamentals_result.source,
            "completeness": fundamentals_result.completeness,
            "missing_fields": fundamentals_result.missing_fields,
        },
        "fcf_3yr_avg": fcf_3yr,
        "sbc": sbc,
        "sbc_adjusted": bool(starting_fcf != (fcf_3yr or fundamentals.get("free_cash_flow"))),
        "net_debt": net_debt,
        "reverse_dcf": reverse_dcf_result,
        "forward_dcf": forward_dcf,
        "sensitivity_matrix": sensitivity,
        "technicals": technicals,
        "financial_history": financial_history,
        "insider_activity": insider_activity,
        "institutional": institutional,
        "analyst": analyst,
        "peers": peers,
        "ai_analysis": ai_analysis,
        "edgar": edgar_data,
        "research_context": research_context,
        # NEW sections
        "quarterly": quarterly,
        "growth_metrics": growth_metrics,
        "forward_estimates": forward_estimates,
        "external_targets": external_targets,
        "fund_flow": fund_flow,
        "staleness_days": staleness_days,
    }


@router.post("/{ticker}")
def save_deep_dive(ticker: str, data: DeepDivePayload):
    """Save AI-generated deep dive analysis. Called by bridge/deep_dive_worker.py."""
    ticker = validate_ticker(ticker)
    with get_db() as db:
        db.execute("""
            INSERT INTO deep_dives (
                ticker, ai_first_impression, ai_bear_case_stock, ai_bear_case_business,
                ai_bull_case_rebuttal, ai_bull_case_upside, ai_whole_picture,
                ai_self_review, ai_verdict, ai_conviction,
                ai_entry_grid_json, ai_exit_playbook, ai_next_review_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            data.first_impression,
            data.bear_case_stock,
            data.bear_case_business,
            data.bull_case_rebuttal,
            data.bull_case_upside,
            data.whole_picture,
            data.self_review,
            data.verdict,
            data.conviction,
            json.dumps(data.entry_grid) if data.entry_grid else None,
            data.exit_playbook,
            data.next_review_date,
        ))
        db.commit()
    return {"status": "saved", "ticker": ticker}


@router.post("/{ticker}/analyze")
def analyze_deep_dive(ticker: str):
    """Trigger Gemini 2.5 Pro to generate all 8 deep dive sections."""
    ticker = validate_ticker(ticker)
    context = {}

    # Gather all Tier 1 data (each in try/except so failures don't block)
    try:
        fund = get_stock_fundamentals(ticker)
        context["fundamentals"] = fund.value if hasattr(fund, 'value') else fund
    except Exception:
        logger.warning("Analyze %s: failed to get fundamentals", ticker, exc_info=True)

    try:
        from backend.services.technicals import get_full_technicals
        context["technicals"] = get_full_technicals(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get technicals", ticker, exc_info=True)

    try:
        from backend.services.financial_history import get_financial_history
        context["financial_history"] = get_financial_history(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get financial history", ticker, exc_info=True)

    try:
        from backend.services.institutional import get_insider_activity
        context["insider_activity"] = get_insider_activity(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get insider activity", ticker, exc_info=True)

    try:
        from backend.services.institutional import get_institutional_summary
        context["institutional"] = get_institutional_summary(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get institutional data", ticker, exc_info=True)

    try:
        from backend.services.sentiment import get_analyst_data
        context["analyst"] = get_analyst_data(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get analyst data", ticker, exc_info=True)

    try:
        from backend.services.sentiment import fetch_sentiment
        context["sentiment"] = fetch_sentiment(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get sentiment", ticker, exc_info=True)

    try:
        from backend.services.peers import get_peer_comparison
        context["peers"] = get_peer_comparison(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get peer comparison", ticker, exc_info=True)

    try:
        from backend.services.regime_checker import get_full_regime
        regime_data = get_full_regime()
        context["regime"] = regime_data.get("regime", {})
    except Exception:
        logger.warning("Analyze %s: failed to get regime", ticker, exc_info=True)

    try:
        from backend.services.edgar import get_edgar_context
        context["edgar"] = get_edgar_context(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get SEC EDGAR data", ticker, exc_info=True)

    try:
        from backend.services.quarterly_data import get_quarterly_data
        context["quarterly"] = get_quarterly_data(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get quarterly data", ticker, exc_info=True)

    try:
        from backend.services.growth_metrics import get_growth_metrics
        context["growth_metrics"] = get_growth_metrics(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get growth metrics", ticker, exc_info=True)

    try:
        from backend.services.forward_estimates import get_forward_estimates
        context["forward_estimates"] = get_forward_estimates(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get forward estimates", ticker, exc_info=True)

    try:
        from backend.services.external_targets import get_external_targets
        context["external_targets"] = get_external_targets(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get external targets", ticker, exc_info=True)

    try:
        from backend.services.fund_flow import get_fund_flow
        context["fund_flow"] = get_fund_flow(ticker)
    except Exception:
        logger.warning("Analyze %s: failed to get fund flow", ticker, exc_info=True)

    from backend.services.gemini_analyzer import generate_deep_dive
    result = generate_deep_dive(ticker, context)

    if "error" in result:
        from fastapi import HTTPException
        status_code = 429 if "Rate limit" in result["error"] else 500
        raise HTTPException(status_code=status_code, detail=result["error"])

    # Split bear case into stock/business if Gemini returned a combined section
    bear_raw = result.get("bear_case", "")
    bear_stock = result.get("bear_case_stock", "")
    bear_business = result.get("bear_case_business", "")
    if bear_raw and not bear_stock and not bear_business:
        # Try to split on sub-headings
        stock_match = re.split(r"\*\*(?:Stock Risk|Price Risk)\*\*", bear_raw, maxsplit=1)
        biz_match = re.split(r"\*\*(?:Business Risk|Fundamental Risk)\*\*", bear_raw, maxsplit=1)
        if len(stock_match) > 1 and len(biz_match) > 1:
            bear_stock = biz_match[0].strip() if len(stock_match) > 1 else bear_raw
            bear_business = biz_match[1].strip() if len(biz_match) > 1 else ""
        else:
            # Can't split — use full text for stock, leave business empty
            bear_stock = bear_raw
            bear_business = ""

    # Split bull case similarly
    bull_raw = result.get("bull_case", "")
    bull_rebuttal = result.get("bull_case_rebuttal", "")
    bull_upside = result.get("bull_case_upside", "")
    if bull_raw and not bull_rebuttal and not bull_upside:
        rebuttal_match = re.split(r"\*\*(?:Rebuttal)\*\*", bull_raw, maxsplit=1)
        upside_match = re.split(r"\*\*(?:Upside)\*\*", bull_raw, maxsplit=1)
        if len(upside_match) > 1:
            bull_rebuttal = upside_match[0].strip()
            bull_upside = upside_match[1].strip()
        else:
            bull_rebuttal = bull_raw
            bull_upside = ""

    # Extract next review date from verdict section
    next_review = None
    verdict_text = result.get("verdict", "")
    if verdict_text:
        review_match = re.search(r"\*\*Next Review Date\*\*[:\s]*(.+?)(?:\n|$)", verdict_text)
        if review_match:
            next_review = review_match.group(1).strip()

    # Extract conviction from verdict section
    conviction = None
    if verdict_text:
        conviction_match = re.search(
            r"(?:conviction|confidence)[:\s]*\*?\*?(HIGH|MODERATE|MEDIUM|LOW)\*?\*?",
            verdict_text, re.IGNORECASE,
        )
        if conviction_match:
            raw = conviction_match.group(1).upper()
            conviction = "MODERATE" if raw == "MEDIUM" else raw

    # Extract entry grid from verdict section
    entry_grid = None
    if verdict_text:
        grid_rows = re.findall(
            r"\|\s*T(\d)\s*(?:\([^)]*\))?\s*\|\s*\$?([\d,.]+)\s*\|\s*([\d]+%?)\s*\|\s*(.+?)\s*\|",
            verdict_text,
        )
        if grid_rows:
            entry_grid = []
            for tranche, price, pct, trigger in grid_rows:
                entry_grid.append({
                    "tranche": int(tranche),
                    "price": float(price.replace(",", "")),
                    "pct_of_position": pct.strip(),
                    "trigger": trigger.strip(),
                })

    # Extract exit playbook
    exit_playbook = None
    if verdict_text:
        exit_match = re.search(
            r"\*\*Exit Playbook\*\*[:\s]*([\s\S]+?)(?:\*\*Next Review|$)",
            verdict_text,
        )
        if exit_match:
            exit_playbook = exit_match.group(1).strip()

    # Build full V2 sections dict for durable storage
    v2_sections = {
        k: v for k, v in result.items()
        if k not in ("raw_text", "ticker", "generated_at", "model", "error")
    }
    # Override with parsed/split values
    v2_sections["bear_case_stock"] = bear_stock
    v2_sections["bear_case_business"] = bear_business
    v2_sections["bull_case_rebuttal"] = bull_rebuttal
    v2_sections["bull_case_upside"] = bull_upside
    if conviction:
        v2_sections["conviction"] = conviction
    if entry_grid:
        v2_sections["entry_grid"] = entry_grid
    if exit_playbook:
        v2_sections["exit_playbook"] = exit_playbook
    if next_review:
        v2_sections["next_review_date"] = next_review

    # Save to deep_dives table (legacy columns + full V2 JSON)
    with get_db() as db:
        db.execute("""INSERT INTO deep_dives (
            ticker, ai_first_impression, ai_bear_case_stock, ai_bear_case_business,
            ai_bull_case_rebuttal, ai_bull_case_upside, ai_whole_picture,
            ai_self_review, ai_verdict, ai_conviction, ai_entry_grid_json,
            ai_exit_playbook, ai_next_review_date, ai_sections_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
            ticker,
            result.get("first_impression") or result.get("data_snapshot"),
            bear_stock,
            bear_business,
            bull_rebuttal,
            bull_upside,
            result.get("whole_picture") or result.get("moat"),
            result.get("self_review") or result.get("opportunities_threats"),
            verdict_text,
            conviction,
            json.dumps(entry_grid) if entry_grid else None,
            exit_playbook,
            next_review,
            json.dumps(v2_sections, default=str),
        ))
        db.commit()

    return {
        "ticker": ticker,
        "status": "generated",
        "model": result.get("model", ""),
        "sections": {
            k: v for k, v in result.items()
            if k not in ("raw_text", "ticker", "generated_at", "model")
        },
    }
