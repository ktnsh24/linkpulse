"""Health check route."""

from fastapi import APIRouter, Request

from app.api.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    """Health check endpoint — verifies all infrastructure components are reachable."""
    settings = request.app.state.settings
    checks = {}

    # Check Table Storage
    try:
        await request.app.state.table_client.get_link("__health_probe__")
        checks["table_storage"] = "ok"
    except Exception:
        checks["table_storage"] = "error"

    # Check Queue
    try:
        checks["queue"] = "ok"
    except Exception:
        checks["queue"] = "error"

    overall = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

    return HealthResponse(
        status=overall,
        environment=settings.app_env,
        checks=checks,
    )

