from fastapi import APIRouter
from backend.services.regime_checker import get_full_regime

router = APIRouter(prefix="/api/regime", tags=["regime"])


@router.get("")
def regime_check():
    return get_full_regime()
