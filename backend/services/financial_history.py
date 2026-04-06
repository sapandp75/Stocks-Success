"""
Financial History — 4-year annual financials from yfinance for trend/sparkline display.
Extracts revenue, margins, FCF, SBC, D/E, shares outstanding.
"""
import json
import yfinance as yf
import pandas as pd
from datetime import datetime
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG


METRICS = [
    "revenue", "operating_income", "net_income", "free_cash_flow",
    "sbc", "gross_margin", "operating_margin", "net_margin",
    "debt_to_equity", "shares_outstanding",
]


def _safe_get(df: pd.DataFrame, labels: list[str], col) -> float | None:
    """Try multiple row labels, return first match for a given column."""
    for label in labels:
        if label in df.index:
            val = df.loc[label, col]
            if pd.notna(val):
                return float(val)
    return None


def _extract_financial_history(
    income_stmt: pd.DataFrame,
    cashflow_stmt: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> dict:
    """Pure function: extracts metrics from yfinance DataFrames.

    Returns dict with keys matching METRICS, each a list of {year, value}
    sorted most recent first.
    """
    result = {m: [] for m in METRICS}

    # Columns are datetime objects representing fiscal year ends
    years = sorted(income_stmt.columns, reverse=True) if not income_stmt.empty else []

    for col in years:
        year = col.year if hasattr(col, "year") else int(str(col)[:4])

        revenue = _safe_get(income_stmt, ["Total Revenue", "Revenue"], col)
        gross_profit = _safe_get(income_stmt, ["Gross Profit"], col)
        operating_income = _safe_get(income_stmt, ["Operating Income", "EBIT"], col)
        net_income = _safe_get(income_stmt, ["Net Income", "Net Income Common Stockholders"], col)

        fcf = _safe_get(cashflow_stmt, ["Free Cash Flow"], col) if not cashflow_stmt.empty else None
        sbc = _safe_get(cashflow_stmt, ["Stock Based Compensation", "Share Based Compensation"], col) if not cashflow_stmt.empty else None

        debt = _safe_get(balance_sheet, ["Total Debt", "Long Term Debt"], col) if not balance_sheet.empty else None
        equity = _safe_get(balance_sheet, ["Stockholders Equity", "Total Equity Gross Minority Interest"], col) if not balance_sheet.empty else None
        shares = _safe_get(balance_sheet, ["Ordinary Shares Number", "Share Issued"], col) if not balance_sheet.empty else None

        result["revenue"].append({"year": year, "value": revenue})
        result["operating_income"].append({"year": year, "value": operating_income})
        result["net_income"].append({"year": year, "value": net_income})
        result["free_cash_flow"].append({"year": year, "value": fcf})
        result["sbc"].append({"year": year, "value": sbc})
        result["shares_outstanding"].append({"year": year, "value": shares})

        # Margins
        if revenue and revenue > 0:
            result["gross_margin"].append({"year": year, "value": round(gross_profit / revenue, 4) if gross_profit is not None else None})
            result["operating_margin"].append({"year": year, "value": round(operating_income / revenue, 4) if operating_income is not None else None})
            result["net_margin"].append({"year": year, "value": round(net_income / revenue, 4) if net_income is not None else None})
        else:
            result["gross_margin"].append({"year": year, "value": None})
            result["operating_margin"].append({"year": year, "value": None})
            result["net_margin"].append({"year": year, "value": None})

        # D/E ratio
        if equity and equity != 0 and debt is not None:
            result["debt_to_equity"].append({"year": year, "value": round(debt / equity, 4)})
        else:
            result["debt_to_equity"].append({"year": year, "value": None})

    return result


def get_financial_history(ticker: str) -> dict:
    """Fetch 4-year annual financials. Cached in financial_history_cache table."""
    ttl = ENRICHMENT_CONFIG["financial_history_ttl_hours"]

    # Check cache
    with get_db() as db:
        cached = db.execute(
            "SELECT * FROM financial_history_cache WHERE ticker = ? ORDER BY year DESC",
            (ticker,),
        ).fetchall()

    if cached and is_fresh(cached[0]["fetched_at"], ttl):
        # Rebuild dict from cached rows
        result = {m: [] for m in METRICS}
        for row in cached:
            metric = row["metric"]
            if metric in result:
                result[metric].append({"year": row["year"], "value": row["value"]})
        return result

    # Fetch from yfinance
    try:
        stock = yf.Ticker(ticker)
        income = stock.financials
        cashflow = stock.cashflow
        balance = stock.balance_sheet
    except Exception:
        return {m: [] for m in METRICS}

    if income is None or income.empty:
        return {m: [] for m in METRICS}

    result = _extract_financial_history(
        income,
        cashflow if cashflow is not None else pd.DataFrame(),
        balance if balance is not None else pd.DataFrame(),
    )

    # Store in cache
    with get_db() as db:
        now = datetime.now().isoformat()
        for metric in METRICS:
            for entry in result[metric]:
                db.execute(
                    """INSERT OR REPLACE INTO financial_history_cache
                       (ticker, metric, year, value, fetched_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (ticker, metric, entry["year"], entry["value"], now),
                )
        db.commit()

    return result
