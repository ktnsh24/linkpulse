"""Analytics routes — GET /api/v1/analytics/{short_code}."""

from fastapi import APIRouter, Request

from app.api.models.responses import ClickAnalyticsResponse

router = APIRouter()


@router.get("/api/v1/analytics/{short_code}", response_model=ClickAnalyticsResponse)
async def get_analytics(short_code: str, request: Request):
    """Get click analytics for a short link.

    Returns total clicks from the counter in Table Storage.
    """
    table_client = request.app.state.table_client
    original_url = await table_client.get_link(short_code)
    total_clicks = await table_client.get_click_count(short_code)

    return ClickAnalyticsResponse(
        short_code=short_code,
        original_url=original_url,
        total_clicks=total_clicks,
    )

