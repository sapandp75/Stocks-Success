"""
Growth Metrics — Calculated financial ratios for deep dive.
All functions are pure calculations. No API calls.
get_growth_metrics() is the aggregator that fetches data and caches.
"""
import json
import yfinance as yf
import pandas as pd
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG


def calc_roic(
    operating_income: float, tax_rate: float,
    total_assets: float, current_liabilities: float, cash: float,
) -> float | None:
    """ROIC = NOPAT / Invested Capital."""
    nopat = operating_income * (1 - tax_rate)
    invested_capital = total_assets - current_liabilities - cash
    if invested_capital <= 0:
        return None
    return round(nopat / invested_capital, 4)


def calc_fcf_yield(fcf: float, market_cap: float) -> float | None:
    """FCF Yield = FCF / Market Cap."""
    if market_cap is None or market_cap <= 0:
        return None
    return round(fcf / market_cap, 4)


def calc_ev_ebit(ev: float, ebit: float) -> float | None:
    """EV/EBIT ratio."""
    if ebit is None or ebit == 0:
        return None
    return round(ev / ebit, 2)


def calc_buyback_yield(shares_history: list[float]) -> float | None:
    """Buyback yield from shares outstanding trend.

    shares_history: most recent first. Positive yield = buyback.
    """
    if not shares_history or len(shares_history) < 2:
        return None
    current = shares_history[0]
    prior = shares_history[1]
    if prior <= 0:
        return None
    return round(-(current / prior - 1), 4)


def calc_accruals_ratio(
    net_income: float, operating_cashflow: float, total_assets: float,
) -> float | None:
    """Accruals ratio = (NI - OCF) / Total Assets. Lower/negative = better."""
    if total_assets is None or total_assets <= 0:
        return None
    return round((net_income - operating_cashflow) / total_assets, 4)


def calc_piotroski(
    net_income: float, ocf: float,
    roa_current: float, roa_prior: float,
    ocf_gt_ni: bool,
    leverage_current: float, leverage_prior: float,
    current_ratio_current: float, current_ratio_prior: float,
    shares_current: float, shares_prior: float,
    gross_margin_current: float, gross_margin_prior: float,
    asset_turnover_current: float, asset_turnover_prior: float,
) -> int:
    """Piotroski F-Score (0-9). Higher = stronger fundamentals."""
    score = 0
    # Profitability (4 points)
    if net_income > 0:
        score += 1
    if ocf > 0:
        score += 1
    if roa_current > roa_prior:
        score += 1
    if ocf_gt_ni:
        score += 1
    # Leverage & Liquidity (3 points)
    if leverage_current < leverage_prior:
        score += 1
    if current_ratio_current > current_ratio_prior:
        score += 1
    if shares_current <= shares_prior:
        score += 1
    # Operating Efficiency (2 points)
    if gross_margin_current > gross_margin_prior:
        score += 1
    if asset_turnover_current > asset_turnover_prior:
        score += 1
    return score


def calc_revenue_cagr(revenue_history: list[float], years: int = 3) -> float | None:
    """CAGR from revenue history (most recent first)."""
    if not revenue_history or len(revenue_history) < years + 1:
        return None
    current = revenue_history[0]
    prior = revenue_history[years]
    if prior is None or prior <= 0 or current is None or current <= 0:
        return None
    return round((current / prior) ** (1 / years) - 1, 4)


def _safe_float(df: pd.DataFrame, labels: list[str], col) -> float | None:
    for label in labels:
        if label in df.index:
            val = df.loc[label, col]
            if pd.notna(val):
                return float(val)
    return None


def get_growth_metrics(ticker: str) -> dict:
    """Calculate all growth metrics for a ticker. Cached 6hr."""
    ttl = ENRICHMENT_CONFIG.get("growth_metrics_ttl_hours", 6)

    with get_db() as db:
        cached = db.execute(
            "SELECT data_json, fetched_at FROM growth_metrics_cache WHERE ticker = ?",
            (ticker,),
        ).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        return json.loads(cached["data_json"])

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        income = stock.financials
        cashflow = stock.cashflow
        balance = stock.balance_sheet
    except Exception:
        return {}

    result = {}

    # --- FCF Yield ---
    fcf = info.get("freeCashflow")
    mcap = info.get("marketCap")
    result["fcf_yield"] = calc_fcf_yield(fcf, mcap) if fcf and mcap else None

    # --- EV/EBIT ---
    ev = info.get("enterpriseValue")
    ebit = None
    if income is not None and not income.empty:
        ebit = _safe_float(income, ["Operating Income", "EBIT"], income.columns[0])
    result["ev_ebit"] = calc_ev_ebit(ev, ebit) if ev and ebit else None

    # --- ROIC (current + 3yr trend) ---
    roic_trend = []
    if income is not None and not income.empty and balance is not None and not balance.empty:
        years = sorted(income.columns, reverse=True)
        for col in years[:4]:
            op_inc = _safe_float(income, ["Operating Income", "EBIT"], col)
            tax = _safe_float(income, ["Tax Provision", "Income Tax Expense"], col)
            pretax = _safe_float(income, ["Pretax Income", "Income Before Tax"], col)
            tax_rate = (tax / pretax) if tax and pretax and pretax != 0 else 0.21

            total_assets = _safe_float(balance, ["Total Assets"], col) if col in balance.columns else None
            curr_liab = _safe_float(balance, ["Current Liabilities"], col) if col in balance.columns else None
            cash = _safe_float(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"], col) if col in balance.columns else None

            if op_inc and total_assets:
                roic = calc_roic(op_inc, tax_rate, total_assets, curr_liab or 0, cash or 0)
                year = col.year if hasattr(col, "year") else None
                roic_trend.append({"year": year, "roic": roic})

    result["roic_current"] = roic_trend[0]["roic"] if roic_trend else None
    result["roic_trend"] = roic_trend

    # --- Buyback Yield ---
    shares_hist = []
    if balance is not None and not balance.empty:
        for col in sorted(balance.columns, reverse=True)[:4]:
            s = _safe_float(balance, ["Ordinary Shares Number", "Share Issued"], col)
            if s:
                shares_hist.append(s)
    result["buyback_yield"] = calc_buyback_yield(shares_hist)

    # --- Total Shareholder Yield ---
    div_yield = info.get("dividendYield") or 0
    bb_yield = result["buyback_yield"] or 0
    result["total_shareholder_yield"] = round(div_yield + bb_yield, 4) if div_yield or bb_yield else None

    # --- Accruals Ratio ---
    if income is not None and not income.empty and cashflow is not None and not cashflow.empty:
        ni = _safe_float(income, ["Net Income", "Net Income Common Stockholders"], income.columns[0])
        ocf = _safe_float(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"], cashflow.columns[0])
        ta = _safe_float(balance, ["Total Assets"], balance.columns[0]) if balance is not None and not balance.empty else None
        result["accruals_ratio"] = calc_accruals_ratio(ni, ocf, ta) if ni is not None and ocf is not None and ta else None
    else:
        result["accruals_ratio"] = None

    # --- Revenue CAGR ---
    rev_hist = []
    if income is not None and not income.empty:
        for col in sorted(income.columns, reverse=True):
            r = _safe_float(income, ["Total Revenue", "Revenue"], col)
            if r:
                rev_hist.append(r)
    result["revenue_cagr_3yr"] = calc_revenue_cagr(rev_hist, 3)
    result["revenue_cagr_5yr"] = calc_revenue_cagr(rev_hist, 5) if len(rev_hist) > 5 else None

    # --- Piotroski F-Score ---
    try:
        if income is not None and not income.empty and len(income.columns) >= 2:
            cols = sorted(income.columns, reverse=True)
            c0, c1 = cols[0], cols[1]

            ni = _safe_float(income, ["Net Income"], c0) or 0
            ocf_val = _safe_float(cashflow, ["Operating Cash Flow", "Total Cash From Operating Activities"], c0) if cashflow is not None and not cashflow.empty else 0
            ocf_val = ocf_val or 0

            ta_c0 = _safe_float(balance, ["Total Assets"], c0) if balance is not None and c0 in balance.columns else None
            ta_c1 = _safe_float(balance, ["Total Assets"], c1) if balance is not None and c1 in balance.columns else None
            roa_c = ni / ta_c0 if ta_c0 and ta_c0 > 0 else 0
            roa_p = (_safe_float(income, ["Net Income"], c1) or 0) / ta_c1 if ta_c1 and ta_c1 > 0 else 0

            debt_c0 = _safe_float(balance, ["Total Debt", "Long Term Debt"], c0) if balance is not None and c0 in balance.columns else 0
            eq_c0 = _safe_float(balance, ["Stockholders Equity"], c0) if balance is not None and c0 in balance.columns else 1
            debt_c1 = _safe_float(balance, ["Total Debt", "Long Term Debt"], c1) if balance is not None and c1 in balance.columns else 0
            eq_c1 = _safe_float(balance, ["Stockholders Equity"], c1) if balance is not None and c1 in balance.columns else 1
            lev_c = (debt_c0 or 0) / eq_c0 if eq_c0 and eq_c0 > 0 else 0
            lev_p = (debt_c1 or 0) / eq_c1 if eq_c1 and eq_c1 > 0 else 0

            ca_c0 = _safe_float(balance, ["Current Assets"], c0) if balance is not None and c0 in balance.columns else 0
            cl_c0 = _safe_float(balance, ["Current Liabilities"], c0) if balance is not None and c0 in balance.columns else 1
            ca_c1 = _safe_float(balance, ["Current Assets"], c1) if balance is not None and c1 in balance.columns else 0
            cl_c1 = _safe_float(balance, ["Current Liabilities"], c1) if balance is not None and c1 in balance.columns else 1
            cr_c = (ca_c0 or 0) / cl_c0 if cl_c0 and cl_c0 > 0 else 0
            cr_p = (ca_c1 or 0) / cl_c1 if cl_c1 and cl_c1 > 0 else 0

            sh_c = _safe_float(balance, ["Ordinary Shares Number", "Share Issued"], c0) if balance is not None and c0 in balance.columns else 0
            sh_p = _safe_float(balance, ["Ordinary Shares Number", "Share Issued"], c1) if balance is not None and c1 in balance.columns else 0

            rev_c0 = _safe_float(income, ["Total Revenue"], c0) or 1
            rev_c1 = _safe_float(income, ["Total Revenue"], c1) or 1
            gp_c0 = _safe_float(income, ["Gross Profit"], c0) or 0
            gp_c1 = _safe_float(income, ["Gross Profit"], c1) or 0
            gm_c = gp_c0 / rev_c0
            gm_p = gp_c1 / rev_c1

            at_c = rev_c0 / ta_c0 if ta_c0 and ta_c0 > 0 else 0
            at_p = rev_c1 / ta_c1 if ta_c1 and ta_c1 > 0 else 0

            result["piotroski"] = calc_piotroski(
                net_income=ni, ocf=ocf_val,
                roa_current=roa_c, roa_prior=roa_p,
                ocf_gt_ni=(ocf_val > ni),
                leverage_current=lev_c, leverage_prior=lev_p,
                current_ratio_current=cr_c, current_ratio_prior=cr_p,
                shares_current=sh_c or 0, shares_prior=sh_p or 0,
                gross_margin_current=gm_c, gross_margin_prior=gm_p,
                asset_turnover_current=at_c, asset_turnover_prior=at_p,
            )
        else:
            result["piotroski"] = None
    except Exception:
        result["piotroski"] = None

    # --- Implied Growth vs Historical CAGR ---
    result["implied_vs_historical_gap"] = None

    # Cache
    data_json = json.dumps(result)
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO growth_metrics_cache (ticker, data_json, fetched_at) VALUES (?, ?, datetime('now'))",
            (ticker, data_json),
        )
        db.commit()

    return result
