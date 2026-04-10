from fastapi import APIRouter

from backend.services.breadth import get_combined_breadth

router = APIRouter(prefix="/api/breadth", tags=["breadth"])


@router.get("")
def breadth():
    return get_combined_breadth()
