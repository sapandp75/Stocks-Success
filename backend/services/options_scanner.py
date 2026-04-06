import numpy as np
from scipy.stats import norm
from backend.config import OPTIONS_PARAMS
from backend.services.fx import get_usd_gbp_rate
from backend.services.earnings import check_earnings_proximity


def calculate_delta(S: float, K: float, T: float, r: float = 0.05, sigma: float = 0.30) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.cdf(d1))


def calculate_theta(S: float, K: float, T: float, r: float = 0.05, sigma: float = 0.30) -> float:
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    theta = (-(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
             - r * K * np.exp(-r * T) * norm.cdf(d2))
    return round(theta / 365, 4)


def filter_contracts(
    contracts: list[dict],
    stock_price: float,
    earnings_date: str | None = None,
) -> list[dict]:
    params = OPTIONS_PARAMS
    results = []

    for c in contracts:
        if c.get("option_type") != "call":
            continue

        strike = c.get("strike", 0)
        bid = c.get("bid", 0) or 0
        ask = c.get("ask", 0) or 0
        oi = c.get("openInterest", 0) or 0
        iv = c.get("impliedVolatility", 0) or 0
        dte = c.get("dte", 0)

        if dte < params["min_dte"] or dte > params["max_dte"]:
            continue

        otm_pct = (strike - stock_price) / stock_price if stock_price > 0 else 0
        if otm_pct < 0.02 or otm_pct > 0.15:
            continue

        if oi < params["min_oi"]:
            continue

        mid = (bid + ask) / 2 if (bid + ask) > 0 else 0
        spread_pct = (ask - bid) / mid if mid > 0 else 1
        if spread_pct > params["max_spread_pct"]:
            continue

        if ask > params["max_premium_usd"] or ask <= 0:
            continue

        T = dte / 365
        sigma = iv if iv > 0 else 0.30
        delta = calculate_delta(stock_price, strike, T, sigma=sigma)
        if delta < params["min_delta"] or delta > params["max_delta"]:
            continue

        theta_daily = calculate_theta(stock_price, strike, T, sigma=sigma)
        target_4x = ask * params["target_multiple"]
        required_move = (target_4x - ask) / delta if delta > 0 else 0
        required_move_pct = required_move / stock_price if stock_price > 0 else 0

        warnings = []
        if oi < 1000:
            warnings.append("LOW LIQUIDITY")
        if spread_pct > 0.05:
            warnings.append("WIDE SPREAD")

        # Earnings proximity check
        expiry = c.get("expiry", "")
        if earnings_date and expiry:
            ep = check_earnings_proximity(earnings_date, expiry)
            if ep["iv_crush_risk"]:
                warnings.append("IV CRUSH RISK")

        results.append({
            "ticker": c.get("ticker", ""),
            "strike": strike,
            "expiry": expiry,
            "dte": dte,
            "delta": round(delta, 3),
            "iv": round(iv, 3) if iv else None,
            "bid": bid,
            "ask": ask,
            "mid": round(mid, 2),
            "premium_usd": ask,
            "premium_gbp": round(ask * 100 * get_usd_gbp_rate(), 2),
            "target_3x": round(ask * 3, 2),
            "target_4x": round(ask * 4, 2),
            "required_move_pct": round(required_move_pct, 4),
            "required_move_pct_note": "Approximation — ignores gamma/vega/IV change",
            "open_interest": oi,
            "spread_pct": round(spread_pct, 4),
            "theta_daily": theta_daily,
            "theta_daily_gbp": round(theta_daily * 100 * get_usd_gbp_rate(), 2),
            "warnings": warnings,
        })

    return sorted(results, key=lambda x: x["required_move_pct"])


def scan_tickers(tickers: list[str]) -> list[dict]:
    from backend.services.market_data import get_stock_fundamentals, get_options_chain

    all_results = []
    for ticker in tickers:
        try:
            fundamentals = get_stock_fundamentals(ticker).value
            price = fundamentals["price"]
            earnings_date = fundamentals.get("earnings_date")
            chain = get_options_chain(ticker)
            for c in chain:
                c["ticker"] = ticker
            qualified = filter_contracts(chain, price, earnings_date=earnings_date)
            all_results.extend(qualified)
        except Exception as e:
            all_results.append({"ticker": ticker, "error": str(e)})
    return all_results
