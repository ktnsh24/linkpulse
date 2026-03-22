"""Link routes — POST /api/v1/links and GET /{short_code}."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from app.api.models.requests import CreateLinkRequest
from app.api.models.responses import LinkListResponse, LinkResponse

router = APIRouter()


@router.post("/api/v1/links", response_model=LinkResponse, status_code=201)
async def create_link(body: CreateLinkRequest, request: Request):
    """Create a new short link.

    - Generates a random 7-character code (or uses custom_code if provided)
    - Stores the mapping in Azure Table Storage
    - Returns the short URL
    """
    link_service = request.app.state.link_service
    settings = request.app.state.settings

    try:
        short_code = await link_service.create_link(body.original_url, body.custom_code)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    logger.info(f"Created link: {short_code} → {body.original_url}")

    return LinkResponse(
        short_code=short_code,
        short_url=f"{settings.base_url}/{short_code}",
        original_url=body.original_url,
        created_at="just now",
    )


@router.get("/api/v1/links", response_model=LinkListResponse)
async def list_links(request: Request):
    """List all short links."""
    link_service = request.app.state.link_service
    settings = request.app.state.settings
    links_data = await link_service.list_links(settings.base_url)
    links = [LinkResponse(**ld) for ld in links_data]
    return LinkListResponse(links=links, total=len(links))


@router.get("/{short_code}")
async def redirect_short_link(short_code: str, request: Request):
    """Redirect a short code to the original URL.

    Flow:
    1. Lookup short_code in Table Storage
    2. If found → 307 redirect + log click event to queue (async)
    3. If not found → 404
    """
    # Skip if the short_code looks like an API or static path
    if short_code in ("docs", "openapi.json", "redoc", "health", "favicon.ico"):
        raise HTTPException(status_code=404, detail="Not found")

    link_service = request.app.state.link_service
    original_url = await link_service.resolve_link(short_code)

    if not original_url:
        raise HTTPException(status_code=404, detail=f"Short link '{short_code}' not found")

    # Log click event asynchronously (non-blocking)
    try:
        await link_service.log_click(
            short_code=short_code,
            original_url=original_url,
            user_agent_str=request.headers.get("user-agent", ""),
            ip_address=request.client.host if request.client else "unknown",
            referer=request.headers.get("referer", ""),
        )
    except Exception as exc:
        # Don't block the redirect if event logging fails
        logger.error(f"Failed to log click event: {exc}")

    return RedirectResponse(url=original_url, status_code=307)

