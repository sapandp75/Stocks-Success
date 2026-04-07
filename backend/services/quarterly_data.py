"""
Quarterly Data — Q/Q and Y/Y growth for revenue, EPS, FCF.
Fetches yfinance quarterly statements, calculates growth rates, caches in SQLite.
"""
import json
import yfinance as yf
import pandas as pd
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG


def _safe_get_q(df: pd.DataFrame, labels: list[str], col) -> float | None:
    for label in labels:
        if label in df.index:
            val = df.loc[label, col]
            if pd.notna(val):
                return float(val)
    return None


def _growth(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round(current / prior - 1, 4)


def extract_quarterly_growth(
    income_q: pd.DataFrame,
    cashflow_q: pd.DataFrame,
    shares: float | None = None,
) -> dict:
    """Pure function: extract Q/Q and Y/Y growth from quarterly DataFrames.

    Returns dict with keys: revenue, eps, fcf, operating_income.
    Each value is a list of dicts: {quarter, value, qoq, yoy} sorted most recent first.
    """
    result = {"revenue": [], "eps": [], "fcf": [], "operating_income": []}

    if income_q is None or income_q.empty:
        return result

    quarters = sorted(income_q.columns, reverse=True)

    for i, col in enumerate(quarters):
        q_label = f"{col.year}-Q{(col.month - 1) // 3 + 1}" if hasattr(col, "year") else str(col)
        prev_q = quarters[i + 1] if i + 1 < len(quarters) else None
        prev_yr = None
        # Find same quarter last year
        if hasattr(col, "year"):
            for c in quarters:
                if hasattr(c, "year") and c.year == col.year - 1 and c.month == col.month:
                    prev_yr = c
                    break

        rev = _safe_get_q(income_q, ["Total Revenue", "Revenue"], col)
        rev_prev_q = _safe_get_q(income_q, ["Total Revenue", "Revenue"], prev_q) if prev_q is not None else None
        rev_prev_yr = _safe_get_q(income_q, ["Total Revenue", "Revenue"], prev_yr) if prev_yr is not None else None

        result["revenue"].append({
            "quarter": q_label, "value": rev,
            "qoq": _growth(rev, rev_prev_q), "yoy": _growth(rev, rev_prev_yr),
        })

        op_inc = _safe_get_q(income_q, ["Operating Income", "EBIT"], col)
        op_prev_q = _safe_get_q(income_q, ["Operating Income", "EBIT"], prev_q) if prev_q is not None else None
        op_prev_yr = _safe_get_q(income_q, ["Operating Income", "EBIT"], prev_yr) if prev_yr is not None else None
        result["operating_income"].append({
            "quarter": q_label, "value": op_inc,
            "qoq": _growth(op_inc, op_prev_q), "yoy": _growth(op_inc, op_prev_yr),
        })

        ni = _safe_get_q(income_q, ["Net Income", "Net Income Common Stockholders"], col)
        ni_prev_q = _safe_get_q(income_q, ["Net Income", "Net Income Common Stockholders"], prev_q) if prev_q is not None else None
        ni_prev_yr = _safe_get_q(income_q, ["Net Income", "Net Income Common Stockholders"], prev_yr) if prev_yr is not None else None
        eps_val = round(ni / shares, 2) if ni is not None and shares and shares > 0 else None
        eps_prev_q = round(ni_prev_q / shares, 2) if ni_prev_q is not None and shares and shares > 0 else None
        eps_prev_yr = round(ni_prev_yr / shares, 2) if ni_prev_yr is not None and shares and shares > 0 else None
        result["eps"].append({
            "quarter": q_label, "value": eps_val,
            "qoq": _growth(eps_val, eps_prev_q), "yoy": _growth(eps_val, eps_prev_yr),
        })

        if cashflow_q is not None and not cashflow_q.empty:
            fcf = _safe_get_q(cashflow_q, ["Free Cash Flow"], col)
            fcf_prev_q = _safe_get_q(cashflow_q, ["Free Cash Flow"], prev_q) if prev_q is not None else None
            fcf_prev_yr = _safe_get_q(cashflow_q, ["Free Cash Flow"], prev_yr) if prev_yr is not None else None
            result["fcf"].append({
                "quarter": q_label, "value": fcf,
                "qoq": _growth(fcf, fcf_prev_q), "yoy": _growth(fcf, fcf_prev_yr),
            })

    return result


def get_quarterly_data(ticker: str) -> dict:
    """Fetch quarterly financials with Q/Q and Y/Y growth. Cached 6hr."""
    ttl = ENRICHMENT_CONFIG.get("quarterly_ttl_hours", 6)

    with get_db() as db:
        cached = db.execute(
            "SELECT data_json, fetched_at FROM quarterly_cache WHERE ticker = ?", (ticker,)
        ).fetchone()

    if cached and is_fresh(cached["fetched_at"], ttl):
        return json.loads(cached["data_json"])

    try:
        stock = yf.Ticker(ticker)
        income_q = stock.quarterly_financials
        cashflow_q = stock.quarterly_cashflow
        shares = (stock.info or {}).get("sharesOutstanding")
    except Exception:
        return {"revenue": [], "eps": [], "fcf": [], "operating_income": []}

    result = extract_quarterly_growth(
        income_q=income_q if income_q is not None else pd.DataFrame(),
        cashflow_q=cashflow_q if cashflow_q is not None else pd.DataFrame(),
        shares=shares,
    )

    # Cache
    data_json = json.dumps(result)
    with get_db() as db:
        db.execute(
            "INSERT OR REPLACE INTO quarterly_cache (ticker, data_json, fetched_at) VALUES (?, ?, datetime('now'))",
            (ticker, data_json),
        )
        db.commit()

    return result
