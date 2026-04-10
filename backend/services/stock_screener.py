from datetime import datetime, timedelta
from backend.config import B1_GATES, B2_GATES


def check_b1_gates(stock: dict) -> bool:
    """All gates are fail-closed: None = FAIL."""
    om = stock.get("operating_margin")
    fcf = stock.get("free_cash_flow")
    drop = stock.get("drop_from_high")
    rg = stock.get("revenue_growth")
    de = stock.get("debt_to_equity")
    fpe = stock.get("forward_pe")

    # Fail-closed: any None = reject
    if om is None or om < B1_GATES["min_operating_margin"]:
        return False
    if fcf is None or fcf <= 0:
        return False
    if drop is None or drop < B1_GATES["min_drop_from_high"]:
        return False
    if rg is None or rg < B1_GATES["min_revenue_growth"]:
        return False
    if de is None or de > B1_GATES["max_debt_to_equity"]:
        return False
    if fpe is None or fpe > B1_GATES["max_forward_pe"]:
        return False
    return True


def check_b2_gates(stock: dict) -> bool:
    """All gates are fail-closed: None = FAIL."""
    rg = stock.get("revenue_growth")
    gm = stock.get("gross_margin")
    rev = stock.get("total_revenue")

    if rg is None or rg < B2_GATES["min_revenue_growth"]:
        return False
    if gm is None or gm < B2_GATES["min_gross_margin"]:
        return False
    if rev is None or rev < B2_GATES["min_revenue"]:
        return False
    return True


def check_b1_warnings(stock: dict) -> list[str]:
    warnings = []
    rg = stock.get("revenue_growth")
    de = stock.get("debt_to_equity")
    si = stock.get("short_percent")
    roe = stock.get("return_on_equity")
    tpe = stock.get("trailing_pe")
    fpe = stock.get("forward_pe")
    sector = stock.get("sector", "")
    earnings = stock.get("earnings_date")

    if rg is not None and rg < 0.05:
        warnings.append("SLOW GROWTH")
    if de is not None and de > 3.0:
        warnings.append("HIGH LEVERAGE")
    if si is not None and si > 0.10:
        warnings.append("HIGH SHORT")
    if roe is not None and roe > 1.0:
        warnings.append("LEVERAGE-DRIVEN ROE")
    if tpe and fpe and fpe > 0 and tpe / fpe > 3:
        warnings.append("P/E COMPRESSION")
    if sector in ("Energy", "Basic Materials"):
        warnings.append("CYCLICAL")
    if earnings:
        try:
            ed = datetime.fromisoformat(str(earnings).split(" ")[0])
            if (ed - datetime.now()).days <= 14:
                warnings.append("EARNINGS SOON")
        except (ValueError, TypeError):
            pass
    return warnings


def check_b2_warnings(stock: dict) -> list[str]:
    warnings = []
    fcf = stock.get("free_cash_flow")
    fpe = stock.get("forward_pe")
    if fcf is not None and fcf < 0:
        warnings.append("CASH BURN")
    if fpe is not None and fpe > 80:
        warnings.append("EXTREME VALUATION")
    return warnings


def scan_sp500(scan_type: str = "weekly", progress_callback=None) -> dict:
    """Backward-compat wrapper for SPX scans."""
    return scan_universe(universe="spx", scan_type=scan_type, progress_callback=progress_callback)


def scan_universe(universe: str = "spx", scan_type: str = "weekly", progress_callback=None) -> dict:
    """Scan a stock universe through B1/B2 gates. Returns candidates with warnings.
    universe: 'spx' or 'ndx'. progress_callback(current, total) called per ticker."""
    import time
    from backend.services.market_data import get_stock_fundamentals

    if universe == "ndx":
        from backend.services.ndx100 import get_ndx100_tickers
        tickers = get_ndx100_tickers()
    else:
        from backend.services.sp500 import get_sp500_tickers
        tickers = get_sp500_tickers()
    b1_candidates = []
    b2_candidates = []
    errors = []
    consecutive_errors = 0

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i, len(tickers))
        try:
            result = get_stock_fundamentals(ticker)
            data = result.value
            consecutive_errors = 0
            data["data_source"] = result.source
            data["data_completeness"] = result.completeness
            data["missing_fields"] = result.missing_fields

            is_b1 = check_b1_gates(data)
            is_b2 = check_b2_gates(data)

            if is_b1:
                entry = {**data, "warnings": check_b1_warnings(data), "bucket": "B1"}
                b1_candidates.append(entry)
            if is_b2:
                entry = {**data, "warnings": check_b2_warnings(data), "bucket": "B2"}
                b2_candidates.append(entry)
        except Exception as e:
            errors.append({"ticker": ticker, "error": str(e)})
            consecutive_errors += 1
            # Back off when rate-limited
            if "Rate" in str(e) or "Too Many" in str(e):
                backoff = min(consecutive_errors * 2, 30)
                time.sleep(backoff)

        # Throttle requests to avoid Yahoo rate limits
        if i % 5 == 4:
            time.sleep(1.5)

    return {
        "scan_date": datetime.now().isoformat(),
        "scan_type": scan_type,
        "universe": universe,
        "total_scanned": len(tickers),
        "b1_count": len(b1_candidates),
        "b2_count": len(b2_candidates),
        "error_count": len(errors),
        "b1_candidates": sorted(b1_candidates, key=lambda x: x.get("drop_from_high") or 0, reverse=True),
        "b2_candidates": sorted(b2_candidates, key=lambda x: x.get("revenue_growth") or 0, reverse=True),
        "errors": errors,
    }
