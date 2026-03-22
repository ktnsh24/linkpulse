"""Pydantic request models for the LinkPulse API."""

from pydantic import BaseModel, HttpUrl, field_validator


class CreateLinkRequest(BaseModel):
    """POST /api/v1/links — create a new short link."""

    original_url: str  # The long URL to shorten
    custom_code: str | None = None  # Optional: user-chosen short code

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure the URL is valid and starts with http/https."""
        # Use Pydantic's HttpUrl for validation, then return the string
        HttpUrl(v)
        return v

