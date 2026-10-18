from fastapi import APIRouter

router = APIRouter(
    prefix="/system",
    tags=["System"],
    )


@router.get("/health")
def health_check() -> dict[str, str]:
    """Report whether the API is responding."""
    return {"status": "ok"}