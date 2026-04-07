import yfinance as yf
import pandas as pd
from datetime import datetime
from backend.services.providers import DataResult

REQUIRED_B1_FIELDS = [
    "operating_margin", "free_cash_flow", "revenue_growth",
    "debt_to_equity", "forward_pe", "drop_from_high",
]

REQUIRED_B2_FIELDS = [
    "revenue_growth", "gross_margin", "total_revenue",
]

ALL_FUNDAMENTAL_FIELDS = [
    "price", "market_cap", "forward_pe", "trailing_pe", "peg_ratio",
    "revenue_growth", "operating_margin", "gross_margin", "profit_margin",
    "free_cash_flow", "total_revenue", "debt_to_equity", "return_on_equity",
    "short_percent", "short_ratio", "shares_outstanding", "beta", "dividend_yield",
    "high_52w", "low_52w", "drop_from_high", "earnings_date",
    "forward_eps", "trailing_eps", "avg_volume", "enterprise_value", "ebitda",
    "ex_dividend_date", "business_summary",
]


def get_stock_fundamentals(ticker: str) -> DataResult:
    stock = yf.Ticker(ticker)
    info = stock.info

    high_52w = info.get("fiftyTwoWeekHigh")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    drop = (high_52w - price) / high_52w if (high_52w and price and high_52w > 0) else None

    # Earnings date
    earnings_date = None
    try:
        cal = stock.calendar
        if cal is not None and not cal.empty:
            earnings_date = str(cal.iloc[0, 0]) if hasattr(cal, 'iloc') else None
    except Exception:
        pass

    # D/E: yfinance returns as percentage (e.g., 150 = 1.5x)
    raw_de = info.get("debtToEquity")
    de_ratio = raw_de / 100 if raw_de is not None else None

    data = {
        "ticker": ticker,
        "name": info.get("shortName", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "price": price,
        "market_cap": info.get("marketCap"),
        "forward_pe": info.get("forwardPE"),
        "trailing_pe": info.get("trailingPE"),
        "revenue_growth": info.get("revenueGrowth"),
        "operating_margin": info.get("operatingMargins"),
        "gross_margin": info.get("grossMargins"),
        "profit_margin": info.get("profitMargins"),
        "free_cash_flow": info.get("freeCashflow"),
        "total_revenue": info.get("totalRevenue"),
        "debt_to_equity": de_ratio,
        "return_on_equity": info.get("returnOnEquity"),
        "short_percent": info.get("shortPercentOfFloat"),
        "short_ratio": info.get("shortRatio"),
        "high_52w": high_52w,
        "low_52w": info.get("fiftyTwoWeekLow"),
        "drop_from_high": round(drop, 4) if drop is not None else None,
        "shares_outstanding": info.get("sharesOutstanding"),
        "beta": info.get("beta"),
        "dividend_yield": info.get("dividendYield"),
        "earnings_date": earnings_date,
        "peg_ratio": info.get("pegRatio"),
        "forward_eps": info.get("forwardEps"),
        "trailing_eps": info.get("trailingEps"),
        "avg_volume": info.get("averageVolume"),
        "enterprise_value": info.get("enterpriseValue"),
        "ebitda": info.get("ebitda"),
        "ex_dividend_date": str(info.get("exDividendDate", "")) if info.get("exDividendDate") else None,
        "business_summary": (info.get("longBusinessSummary") or "")[:500],
    }

    missing = [f for f in ALL_FUNDAMENTAL_FIELDS if data.get(f) is None]

    return DataResult(value=data, source="yfinance", missing_fields=missing)


def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def get_moving_averages(ticker: str) -> dict:
    df = get_price_history(ticker, period="1y")
    if df.empty:
        return {}
    price = float(df["Close"].iloc[-1])
    ema20 = float(df["Close"].ewm(span=20).mean().iloc[-1])
    sma50 = float(df["Close"].rolling(50).mean().iloc[-1])
    sma200 = float(df["Close"].rolling(200).mean().iloc[-1])
    return {
        "price": round(price, 2),
        "ema20": round(ema20, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
    }


def get_options_chain(ticker: str) -> list[dict]:
    stock = yf.Ticker(ticker)
    expirations = stock.options
    all_contracts = []
    now = datetime.now()

    for exp_str in expirations:
        exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
        dte = (exp_date - now).days
        if dte < 30 or dte > 150:
            continue
        chain = stock.option_chain(exp_str)
        for df, otype in [(chain.calls, "call"), (chain.puts, "put")]:
            copy = df.copy()
            copy["expiry"] = exp_str
            copy["dte"] = dte
            copy["option_type"] = otype
            all_contracts.append(copy)

    if not all_contracts:
        return []
    return pd.concat(all_contracts, ignore_index=True).to_dict(orient="records")


def get_fcf_3yr_average(ticker: str) -> float | None:
    """Get 3-year average FCF. Returns None if insufficient data."""
    stock = yf.Ticker(ticker)
    try:
        cf = stock.cashflow
        if cf is None or cf.empty:
            return None
        fcf_row = cf.loc["Free Cash Flow"] if "Free Cash Flow" in cf.index else None
        if fcf_row is None:
            return None
        values = [v for v in fcf_row.values[:3] if pd.notna(v)]
        if len(values) < 2:
            return None
        return sum(values) / len(values)
    except Exception:
        return None


def get_sbc(ticker: str) -> float | None:
    """Get stock-based compensation from cash flow statement."""
    stock = yf.Ticker(ticker)
    try:
        cf = stock.cashflow
        if cf is None or cf.empty:
            return None
        for label in ["Stock Based Compensation", "Share Based Compensation"]:
            if label in cf.index:
                val = cf.loc[label].values[0]
                return float(val) if pd.notna(val) else None
        return None
    except Exception:
        return None


def get_net_debt(ticker: str) -> float | None:
    """Get net debt from balance sheet (total debt - cash)."""
    stock = yf.Ticker(ticker)
    try:
        bs = stock.balance_sheet
        if bs is None or bs.empty:
            return None
        total_debt = None
        cash = None
        for label in ["Total Debt", "Long Term Debt"]:
            if label in bs.index:
                val = bs.loc[label].values[0]
                if pd.notna(val):
                    total_debt = float(val)
                    break
        for label in ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]:
            if label in bs.index:
                val = bs.loc[label].values[0]
                if pd.notna(val):
                    cash = float(val)
                    break
        if total_debt is not None and cash is not None:
            return total_debt - cash
        return total_debt  # if no cash data, return gross debt
    except Exception:
        return None
