"""Pydantic response models for the LinkPulse API."""

from datetime import datetime

from pydantic import BaseModel


class LinkResponse(BaseModel):
    """Response after creating or retrieving a short link."""

    short_code: str
    short_url: str
    original_url: str
    created_at: str


class LinkListResponse(BaseModel):
    """Response for listing all links."""

    links: list[LinkResponse]
    total: int


class ClickAnalyticsResponse(BaseModel):
    """Response for GET /api/v1/analytics/{short_code}."""

    short_code: str
    original_url: str | None
    total_clicks: int


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str  # "healthy" | "degraded"
    environment: str
    version: str = "0.1.0"
    checks: dict[str, str] = {}  # component → "ok" | "error"


class ClickEvent(BaseModel):
    """Schema for click events written to queue and blob storage.

    This is the equivalent of the bna_events table in shared-proxy.
    """

    event_id: str
    short_code: str
    original_url: str
    timestamp: datetime
    user_agent: str
    device_type: str  # "desktop" | "mobile" | "tablet" | "bot" | "unknown"
    ip_address: str
    referer: str

