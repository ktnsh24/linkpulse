"""Azure Table Storage client — stores link mappings and click counters."""

from datetime import datetime, timezone

from azure.data.tables.aio import TableServiceClient
from loguru import logger


class TableStorageClient:
    """Wraps Azure Table Storage for links and click counters."""

    def __init__(self, connection_string: str, links_table: str, clicks_table: str):
        self._conn_str = connection_string
        self._links_table = links_table
        self._clicks_table = clicks_table
        self._service: TableServiceClient | None = None

    async def init(self) -> None:
        """Create tables if they don't exist (called once at startup)."""
        self._service = TableServiceClient.from_connection_string(self._conn_str)
        for name in (self._links_table, self._clicks_table):
            try:
                await self._service.create_table_if_not_exists(name)
                logger.info(f"Table '{name}' ready")
            except Exception as exc:
                logger.error(f"Failed to create table '{name}': {exc}")
                raise

    async def close(self) -> None:
        if self._service:
            await self._service.close()

    # ── Links table ──────────────────────────────────────────────────────

    async def put_link(self, short_code: str, original_url: str) -> None:
        """Store a short_code → original_url mapping."""
        async with self._service.get_table_client(self._links_table) as table:
            entity = {
                "PartitionKey": "link",
                "RowKey": short_code,
                "original_url": original_url,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await table.upsert_entity(entity)

    async def get_link(self, short_code: str) -> str | None:
        """Retrieve the original URL for a short_code. Returns None if not found."""
        async with self._service.get_table_client(self._links_table) as table:
            try:
                entity = await table.get_entity(partition_key="link", row_key=short_code)
                return entity["original_url"]
            except Exception:
                return None

    async def list_links(self, limit: int = 50) -> list[dict]:
        """List recent links."""
        async with self._service.get_table_client(self._links_table) as table:
            results = []
            async for entity in table.query_entities("PartitionKey eq 'link'"):
                results.append({
                    "short_code": entity["RowKey"],
                    "original_url": entity["original_url"],
                    "created_at": entity.get("created_at", ""),
                })
                if len(results) >= limit:
                    break
            return results

    # ── Clicks table ─────────────────────────────────────────────────────

    async def increment_click(self, short_code: str) -> int:
        """Increment click counter and return new total."""
        async with self._service.get_table_client(self._clicks_table) as table:
            try:
                entity = await table.get_entity(partition_key="counter", row_key=short_code)
                new_count = int(entity.get("total_clicks", 0)) + 1
                entity["total_clicks"] = new_count
                await table.upsert_entity(entity)
                return new_count
            except Exception:
                # First click — create the counter
                entity = {
                    "PartitionKey": "counter",
                    "RowKey": short_code,
                    "total_clicks": 1,
                    "first_click_at": datetime.now(timezone.utc).isoformat(),
                }
                await table.upsert_entity(entity)
                return 1

    async def get_click_count(self, short_code: str) -> int:
        """Get total click count for a short_code."""
        async with self._service.get_table_client(self._clicks_table) as table:
            try:
                entity = await table.get_entity(partition_key="counter", row_key=short_code)
                return int(entity.get("total_clicks", 0))
            except Exception:
                return 0

