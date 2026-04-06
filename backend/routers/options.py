from fastapi import APIRouter, Query
from backend.services.options_scanner import scan_tickers
from backend.services.regime_checker import get_full_regime
from backend.validators import validate_ticker

router = APIRouter(prefix="/api/options", tags=["options"])


@router.get("/scan")
def scan_options(tickers: str = Query(..., description="Comma-separated tickers")):
    ticker_list = [validate_ticker(t) for t in tickers.split(",") if t.strip()]
    results = scan_tickers(ticker_list)
    # Include regime context so UI can show it
    try:
        regime = get_full_regime()
    except Exception:
        regime = None
    return {"results": results, "regime": regime}
