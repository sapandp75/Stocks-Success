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
        "ai_analysis": ai_analysis,
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
