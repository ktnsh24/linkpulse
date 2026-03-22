"""Unit tests for the LinkService."""

import pytest

from app.api.models.responses import ClickEvent
from app.domain.services.link_service import LinkService


class FakeTableClient:
    """In-memory fake for TableStorageClient."""

    def __init__(self):
        self.links: dict[str, str] = {}
        self.clicks: dict[str, int] = {}

    async def init(self):
        pass

    async def close(self):
        pass

    async def put_link(self, short_code: str, original_url: str):
        self.links[short_code] = original_url

    async def get_link(self, short_code: str) -> str | None:
        return self.links.get(short_code)

    async def list_links(self, limit=50):
        return [
            {"short_code": k, "original_url": v, "created_at": ""}
            for k, v in list(self.links.items())[:limit]
        ]

    async def increment_click(self, short_code: str) -> int:
        self.clicks[short_code] = self.clicks.get(short_code, 0) + 1
        return self.clicks[short_code]

    async def get_click_count(self, short_code: str) -> int:
        return self.clicks.get(short_code, 0)


class FakeQueueClient:
    """In-memory fake for QueueClient."""

    def __init__(self):
        self.messages: list[dict] = []

    async def init(self):
        pass

    async def close(self):
        pass

    async def send_event(self, event: dict):
        self.messages.append(event)


@pytest.fixture
def link_service():
    table = FakeTableClient()
    queue = FakeQueueClient()
    return LinkService(table_client=table, queue_client=queue, code_length=7)


@pytest.fixture
def fake_queue():
    return FakeQueueClient()


@pytest.fixture
def link_service_with_queue(fake_queue):
    table = FakeTableClient()
    return LinkService(table_client=table, queue_client=fake_queue, code_length=7), fake_queue


class TestCreateLink:
    async def test_create_link_generates_code(self, link_service):
        code = await link_service.create_link("https://example.com")
        assert len(code) == 7
        assert code.isalnum()

    async def test_create_link_with_custom_code(self, link_service):
        code = await link_service.create_link("https://example.com", custom_code="mycode")
        assert code == "mycode"

    async def test_custom_code_conflict_raises(self, link_service):
        await link_service.create_link("https://example.com", custom_code="taken")
        with pytest.raises(ValueError, match="already taken"):
            await link_service.create_link("https://other.com", custom_code="taken")


class TestResolveLink:
    async def test_resolve_existing_link(self, link_service):
        await link_service.create_link("https://example.com", custom_code="abc")
        result = await link_service.resolve_link("abc")
        assert result == "https://example.com"

    async def test_resolve_nonexistent_link(self, link_service):
        result = await link_service.resolve_link("nope")
        assert result is None


class TestLogClick:
    async def test_log_click_sends_event_to_queue(self, link_service_with_queue):
        svc, queue = link_service_with_queue
        await svc.log_click(
            short_code="abc",
            original_url="https://example.com",
            user_agent_str="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ip_address="1.2.3.4",
            referer="https://google.com",
        )
        assert len(queue.messages) == 1
        event = queue.messages[0]
        assert event["short_code"] == "abc"
        assert event["device_type"] == "desktop"
        assert event["ip_address"] == "1.2.3.4"

    async def test_mobile_user_agent_detected(self, link_service_with_queue):
        svc, queue = link_service_with_queue
        await svc.log_click(
            short_code="xyz",
            original_url="https://example.com",
            user_agent_str="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)",
            ip_address="5.6.7.8",
            referer="",
        )
        assert queue.messages[0]["device_type"] == "mobile"


class TestClickEventModel:
    def test_click_event_schema(self):
        """Verify the ClickEvent model has all required fields (like bna_events table)."""
        fields = ClickEvent.model_fields
        assert "event_id" in fields
        assert "short_code" in fields
        assert "original_url" in fields
        assert "timestamp" in fields
        assert "user_agent" in fields
        assert "device_type" in fields
        assert "ip_address" in fields
        assert "referer" in fields

