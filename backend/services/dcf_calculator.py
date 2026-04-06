from backend.config import DCF_DEFAULTS


def adjust_fcf_for_sbc(fcf: float, sbc: float | None, revenue: float | None) -> float:
    """Subtract SBC from FCF if SBC > 10% of revenue. Spec rule."""
    if sbc is None or revenue is None or revenue <= 0:
        return fcf
    if sbc / revenue > DCF_DEFAULTS["sbc_threshold"]:
        return fcf - sbc
    return fcf


def _compute_dcf(starting_fcf, g1, g2, tg, wacc, shares, net_debt) -> dict:
    """Core DCF computation."""
    fcf = starting_fcf
    projections = []

    # Years 1-5
    for year in range(1, 6):
        fcf = fcf * (1 + g1)
        projections.append({"year": year, "fcf": fcf, "growth": g1})

    # Years 6-10: linear deceleration from g2 to terminal
    for year in range(6, 11):
        blend = (year - 5) / 5
        rate = g2 * (1 - blend) + tg * blend
        fcf = fcf * (1 + rate)
        projections.append({"year": year, "fcf": fcf, "growth": round(rate, 4)})

    # Terminal value
    if wacc <= tg:
        terminal_value = 0  # invalid — flag it
    else:
        terminal_fcf = fcf * (1 + tg)
        terminal_value = terminal_fcf / (wacc - tg)

    pv_fcfs = sum(p["fcf"] / (1 + wacc) ** p["year"] for p in projections)
    pv_terminal = terminal_value / (1 + wacc) ** 10
    enterprise_value = pv_fcfs + pv_terminal
    equity_value = enterprise_value - (net_debt or 0)
    per_share = equity_value / shares if shares and shares > 0 else 0
    terminal_pct = pv_terminal / enterprise_value if enterprise_value > 0 else 0

    return {
        "per_share": round(per_share, 2),
        "enterprise_value": round(enterprise_value),
        "equity_value": round(equity_value),
        "pv_fcfs": round(pv_fcfs),
        "pv_terminal": round(pv_terminal),
        "terminal_value_pct": round(terminal_pct, 4),
        "projections": projections,
    }


def calculate_dcf(
    starting_fcf: float,
    growth_rate_1_5: float,
    growth_rate_6_10: float,
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
    wacc: float = DCF_DEFAULTS["wacc"],
    shares_outstanding: int = 1,
    net_debt: float = 0,
) -> dict:
    core = _compute_dcf(starting_fcf, growth_rate_1_5, growth_rate_6_10,
                        terminal_growth, wacc, shares_outstanding, net_debt)

    result = {
        "intrinsic_value_per_share": core["per_share"],
        "enterprise_value": core["enterprise_value"],
        "equity_value": core["equity_value"],
        "pv_fcfs": core["pv_fcfs"],
        "pv_terminal": core["pv_terminal"],
        "terminal_value_pct": core["terminal_value_pct"],
        "fcf_projections": core["projections"],
        "inputs": {
            "starting_fcf": starting_fcf,
            "growth_1_5": growth_rate_1_5,
            "growth_6_10": growth_rate_6_10,
            "terminal_growth": terminal_growth,
            "wacc": wacc,
            "shares_outstanding": shares_outstanding,
            "net_debt": net_debt,
        },
    }

    if core["terminal_value_pct"] > DCF_DEFAULTS["max_terminal_pct"]:
        result["terminal_value_warning"] = (
            f"Terminal value is {core['terminal_value_pct']:.0%} of total — exceeds 50%. "
            f"Consider shorter forecast period or higher near-term growth."
        )

    return result


def build_sensitivity_matrix(
    starting_fcf: float,
    base_growth_1_5: float,
    base_growth_6_10: float,
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
    wacc: float = DCF_DEFAULTS["wacc"],
    shares_outstanding: int = 1,
    net_debt: float = 0,
) -> list[dict]:
    """
    4x4 sensitivity matrix. WACC is FIXED (spec rule).
    Rows and columns both vary growth rates.
    """
    g1_offsets = [-0.05, -0.02, 0.0, 0.03]
    g2_offsets = [-0.03, -0.01, 0.0, 0.02]
    matrix = []

    for g1_off in g1_offsets:
        row = {
            "wacc": wacc,
            "growth_1_5": round(base_growth_1_5 + g1_off, 3),
            "values": [],
        }
        for g2_off in g2_offsets:
            g1 = base_growth_1_5 + g1_off
            g2 = base_growth_6_10 + g2_off
            core = _compute_dcf(starting_fcf, g1, g2, terminal_growth, wacc,
                                shares_outstanding, net_debt)
            row["values"].append({
                "growth_6_10": round(g2, 3),
                "per_share": core["per_share"],
            })
        matrix.append(row)

    return matrix


def reverse_dcf(
    current_price: float,
    starting_fcf: float,
    shares_outstanding: int,
    net_debt: float,
    wacc: float = DCF_DEFAULTS["wacc"],
    terminal_growth: float = DCF_DEFAULTS["terminal_growth"],
) -> dict:
    """What growth rate does the market price imply? Binary search."""
    target_equity = current_price * shares_outstanding + (net_debt or 0)
    low, high = -0.10, 0.50

    for _ in range(100):
        mid = (low + high) / 2
        core = _compute_dcf(starting_fcf, mid, mid * 0.6, terminal_growth, wacc,
                            shares_outstanding, net_debt or 0)
        if core["equity_value"] < target_equity:
            low = mid
        else:
            high = mid

    implied = round((low + high) / 2, 4)
    return {
        "implied_growth_rate": implied,
        "current_price": current_price,
        "interpretation": _interpret_implied(implied),
    }


def _interpret_implied(rate: float) -> str:
    if rate < 0:
        return "Market prices in DECLINE. If stable business, this is deep value."
    if rate < 0.05:
        return "Market expects very low growth. Modest beat = significant upside."
    if rate < 0.10:
        return "Market expects moderate growth. Check if achievable."
    if rate < 0.20:
        return "Market expects strong growth. Needs sustained execution."
    return "Market expects exceptional growth. High bar — any miss punished."
