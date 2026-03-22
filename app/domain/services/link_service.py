"""Link service — core business logic for creating and resolving short links."""

import secrets
import string
from datetime import datetime, timezone
from uuid import uuid4

from user_agents import parse as parse_user_agent

from app.api.models.responses import ClickEvent
from app.infrastructure.storage.queue_client import QueueClient
from app.infrastructure.storage.table_client import TableStorageClient


class LinkService:
    """Handles link creation, resolution, and click event logging."""

    def __init__(self, table_client: TableStorageClient, queue_client: QueueClient, code_length: int = 7):
        self._table = table_client
        self._queue = queue_client
        self._code_length = code_length

    def _generate_code(self) -> str:
        """Generate a random alphanumeric short code."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(self._code_length))

    async def create_link(self, original_url: str, custom_code: str | None = None) -> str:
        """Create a new short link. Returns the short code."""
        short_code = custom_code or self._generate_code()

        # Check if custom code already exists
        if custom_code:
            existing = await self._table.get_link(short_code)
            if existing:
                raise ValueError(f"Short code '{short_code}' is already taken")

        await self._table.put_link(short_code, original_url)
        return short_code

    async def resolve_link(self, short_code: str) -> str | None:
        """Look up the original URL for a short code."""
        return await self._table.get_link(short_code)

    async def log_click(
        self,
        short_code: str,
        original_url: str,
        user_agent_str: str,
        ip_address: str,
        referer: str,
    ) -> None:
        """Log a click event to the queue (async, non-blocking).

        This is the equivalent of BnaEventMiddleware in shared-proxy —
        every redirect is logged as a ClickEvent for later processing.
        """
        # Parse device type from user-agent
        ua = parse_user_agent(user_agent_str)
        if ua.is_bot:
            device_type = "bot"
        elif ua.is_mobile:
            device_type = "mobile"
        elif ua.is_tablet:
            device_type = "tablet"
        elif ua.is_pc:
            device_type = "desktop"
        else:
            device_type = "unknown"

        event = ClickEvent(
            event_id=uuid4().hex,
            short_code=short_code,
            original_url=original_url,
            timestamp=datetime.now(timezone.utc),
            user_agent=user_agent_str[:500],  # truncate long UAs
            device_type=device_type,
            ip_address=ip_address,
            referer=referer[:500],
        )

        await self._queue.send_event(event.model_dump(mode="json"))

    async def list_links(self, base_url: str, limit: int = 50) -> list[dict]:
        """List all links with their short URLs."""
        raw_links = await self._table.list_links(limit)
        return [
            {
                "short_code": link["short_code"],
                "short_url": f"{base_url}/{link['short_code']}",
                "original_url": link["original_url"],
                "created_at": link["created_at"],
            }
            for link in raw_links
        ]

