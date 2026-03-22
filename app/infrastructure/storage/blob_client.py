"""Azure Blob Storage client — event lake for click analytics."""

import json
from datetime import datetime, timezone

from azure.storage.blob.aio import BlobServiceClient
from loguru import logger


class BlobStorageClient:
    """Writes click events as JSON to Azure Blob Storage (event lake)."""

    def __init__(self, connection_string: str, container_name: str):
        self._conn_str = connection_string
        self._container_name = container_name
        self._service: BlobServiceClient | None = None

    async def init(self) -> None:
        """Create blob container if it doesn't exist."""
        self._service = BlobServiceClient.from_connection_string(self._conn_str)
        container = self._service.get_container_client(self._container_name)
        try:
            await container.create_container()
            logger.info(f"Blob container '{self._container_name}' ready")
        except Exception:
            logger.info(f"Blob container '{self._container_name}' already exists")

    async def close(self) -> None:
        if self._service:
            await self._service.close()

    async def write_events(self, events: list[dict]) -> str:
        """Write a batch of events as a single JSON-lines file to Blob Storage.

        Path structure: events/year=YYYY/month=MM/day=DD/hour=HH/{timestamp}.jsonl
        Returns the blob path.
        """
        if not events:
            return ""

        now = datetime.now(timezone.utc)
        blob_path = (
            f"events/year={now.year}/month={now.month:02d}/day={now.day:02d}"
            f"/hour={now.hour:02d}/{now.strftime('%Y%m%d%H%M%S%f')}.jsonl"
        )

        # JSON-lines format: one JSON object per line
        content = "\n".join(json.dumps(e) for e in events)

        container = self._service.get_container_client(self._container_name)
        blob = container.get_blob_client(blob_path)
        await blob.upload_blob(content.encode("utf-8"), overwrite=True)

        logger.info(f"Wrote {len(events)} events to blob: {blob_path}")
        return blob_path

    async def list_event_files(self, prefix: str = "events/") -> list[str]:
        """List all event files under a prefix (for DuckDB querying)."""
        container = self._service.get_container_client(self._container_name)
        blobs = []
        async for blob in container.list_blobs(name_starts_with=prefix):
            blobs.append(blob.name)
        return blobs

