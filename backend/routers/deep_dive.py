import json
from fastapi import APIRouter, Body
from backend.services.market_data import (
    get_stock_fundamentals, get_fcf_3yr_average, get_sbc, get_net_debt,
)
from backend.services.dcf_calculator import (
    calculate_dcf, reverse_dcf, build_sensitivity_matrix, adjust_fcf_for_sbc,
)
from backend.database import get_db

router = APIRouter(prefix="/api/deep-dive", tags=["deep-dive"])


@router.get("/{ticker}")
def get_deep_dive_data(ticker: str):
    """Get all quantitative data for a deep dive + any saved AI analysis."""
    ticker = ticker.upper()
    fundamentals_result = get_stock_fundamentals(ticker)
    fundamentals = fundamentals_result.value

    # FCF: 3-year average, SBC-adjusted per spec
    fcf_3yr = get_fcf_3yr_average(ticker)
    sbc = get_sbc(ticker)
    revenue = fundamentals.get("total_revenue")
    net_debt = get_net_debt(ticker)
    shares = fundamentals.get("shares_outstanding")
    price = fundamentals.get("price")

    starting_fcf = fcf_3yr or fundamentals.get("free_cash_flow")
    if starting_fcf and sbc:
        starting_fcf = adjust_fcf_for_sbc(starting_fcf, sbc, revenue)

    # Reverse DCF (always first per spec)
    reverse_dcf_result = None
    if starting_fcf and shares and price and starting_fcf > 0:
        reverse_dcf_result = reverse_dcf(
            current_price=price, starting_fcf=starting_fcf,
            shares_outstanding=shares, net_debt=net_debt or 0,
        )

    # Forward DCF (3 scenarios)
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

    # Load saved AI analysis
    db = get_db()
    row = db.execute(
        "SELECT * FROM deep_dives WHERE ticker = ? ORDER BY dive_date DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    db.close()

    ai_analysis = None
    if row:
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
        }

    # Enrichment: technicals, financial history, insider, institutional, analyst, peers
    # Each in try/except — enrichment never blocks the critical path
    technicals = None
    try:
        from backend.services.technicals import get_full_technicals
        technicals = get_full_technicals(ticker)
    except Exception:
        pass

    financial_history = None
    try:
        from backend.services.financial_history import get_financial_history
        financial_history = get_financial_history(ticker)
    except Exception:
        pass

    insider_activity = None
    try:
        from backend.services.institutional import get_insider_activity
        insider_activity = get_insider_activity(ticker)
    except Exception:
        pass

    institutional = None
    try:
        from backend.services.institutional import get_institutional_summary
        institutional = get_institutional_summary(ticker)
    except Exception:
        pass

    analyst = None
    try:
        from backend.services.sentiment import get_analyst_data
        analyst = get_analyst_data(ticker)
    except Exception:
        pass

    peers = None
    try:
        from backend.services.peers import get_peer_comparison
        peers = get_peer_comparison(ticker)
    except Exception:
        pass

    # Research context (collapsed by default in UI)
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
        pass

    return {
        "ticker": ticker,
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
        "research_context": research_context,
    }


@router.post("/{ticker}")
def save_deep_dive(ticker: str, data: dict = Body(...)):
    """Save AI-generated deep dive analysis. Called by bridge/deep_dive_worker.py."""
    ticker = ticker.upper()
    db = get_db()
    db.execute("""
        INSERT INTO deep_dives (
            ticker, ai_first_impression, ai_bear_case_stock, ai_bear_case_business,
            ai_bull_case_rebuttal, ai_bull_case_upside, ai_whole_picture,
            ai_self_review, ai_verdict, ai_conviction,
            ai_entry_grid_json, ai_exit_playbook
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker,
        data.get("first_impression"),
        data.get("bear_case_stock"),
        data.get("bear_case_business"),
        data.get("bull_case_rebuttal"),
        data.get("bull_case_upside"),
        data.get("whole_picture"),
        data.get("self_review"),
        data.get("verdict"),
        data.get("conviction"),
        json.dumps(data.get("entry_grid")) if data.get("entry_grid") else None,
        data.get("exit_playbook"),
    ))
    db.commit()
    db.close()
    return {"status": "saved", "ticker": ticker}


@router.post("/{ticker}/analyze")
def analyze_deep_dive(ticker: str):
    """Trigger Gemini 2.5 Pro to generate all 8 deep dive sections."""
    ticker = ticker.upper()
    context = {}

    # Gather all Tier 1 data (each in try/except so failures don't block)
    try:
        fund = get_stock_fundamentals(ticker)
        context["fundamentals"] = fund.value if hasattr(fund, 'value') else fund
    except Exception:
        pass

    try:
        from backend.services.technicals import get_full_technicals
        context["technicals"] = get_full_technicals(ticker)
    except Exception:
        pass

    try:
        from backend.services.financial_history import get_financial_history
        context["financial_history"] = get_financial_history(ticker)
    except Exception:
        pass

    try:
        from backend.services.institutional import get_insider_activity
        context["insider_activity"] = get_insider_activity(ticker)
    except Exception:
        pass

    try:
        from backend.services.institutional import get_institutional_summary
        context["institutional"] = get_institutional_summary(ticker)
    except Exception:
        pass

    try:
        from backend.services.sentiment import get_analyst_data
        context["analyst"] = get_analyst_data(ticker)
    except Exception:
        pass

    try:
        from backend.services.sentiment import fetch_sentiment
        context["sentiment"] = fetch_sentiment(ticker)
    except Exception:
        pass

    try:
        from backend.services.peers import get_peer_comparison
        context["peers"] = get_peer_comparison(ticker)
    except Exception:
        pass

    try:
        from backend.services.regime_checker import get_full_regime
        regime_data = get_full_regime()
        context["regime"] = regime_data.get("regime", {})
    except Exception:
        pass

    from backend.services.gemini_analyzer import generate_deep_dive
    result = generate_deep_dive(ticker, context)

    if "error" in result:
        from fastapi import HTTPException
        status_code = 429 if "Rate limit" in result["error"] else 500
        raise HTTPException(status_code=status_code, detail=result["error"])

    # Save to deep_dives table
    db = get_db()
    db.execute("""INSERT INTO deep_dives (
        ticker, ai_first_impression, ai_bear_case_stock, ai_bear_case_business,
        ai_bull_case_rebuttal, ai_bull_case_upside, ai_whole_picture,
        ai_self_review, ai_verdict, ai_conviction
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        ticker,
        result.get("first_impression") or result.get("data_snapshot"),
        result.get("bear_case"),
        result.get("bear_case"),  # combined
        result.get("bull_case"),
        result.get("bull_case"),
        result.get("whole_picture"),
        result.get("self_review"),
        result.get("verdict"),
        None,
    ))
    db.commit()
    db.close()

    return {
        "ticker": ticker,
        "status": "generated",
        "model": result.get("model", ""),
        "sections": {
            k: v for k, v in result.items()
            if k not in ("raw_text", "ticker", "generated_at", "model")
        },
    }
