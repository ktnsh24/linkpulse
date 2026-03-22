"""Click event worker — polls Azure Queue, enriches events, writes to Blob Storage.

This is the equivalent of BnaEventWorker in maestro-devops-monitoring.
It runs as a background asyncio task inside the same Container App.
"""

import asyncio

from loguru import logger

from app.infrastructure.storage.blob_client import BlobStorageClient
from app.infrastructure.storage.queue_client import QueueClient
from app.infrastructure.storage.table_client import TableStorageClient


class ClickEventWorker:
    """Background worker that processes click events from the queue.

    Flow:
    1. Poll Azure Storage Queue every `poll_interval` seconds
    2. Receive a batch of messages
    3. For each message: increment click counter in Table Storage
    4. Write the batch of events to Blob Storage as JSON-lines
    5. Delete processed messages from the queue
    """

    def __init__(
        self,
        queue_client: QueueClient,
        table_client: TableStorageClient,
        blob_client: BlobStorageClient,
        poll_interval: float = 5.0,
        batch_size: int = 10,
    ):
        self._queue = queue_client
        self._table = table_client
        self._blob = blob_client
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the worker as a background asyncio task."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"ClickEventWorker started (poll every {self._poll_interval}s, batch size {self._batch_size})")

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ClickEventWorker stopped")

    async def _run_loop(self) -> None:
        """Main polling loop — runs until stopped."""
        while self._running:
            try:
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Worker error: {exc}")
            await asyncio.sleep(self._poll_interval)

    async def _process_batch(self) -> None:
        """Process one batch of messages from the queue."""
        messages = await self._queue.receive_events(max_messages=self._batch_size)

        if not messages:
            return  # No messages — sleep and retry

        logger.info(f"Processing {len(messages)} click events")

        events_to_write = []
        for msg in messages:
            event = msg["content"]

            # Increment click counter in Table Storage
            short_code = event.get("short_code", "unknown")
            try:
                await self._table.increment_click(short_code)
            except Exception as exc:
                logger.error(f"Failed to increment counter for {short_code}: {exc}")

            events_to_write.append(event)

        # Write events batch to Blob Storage (event lake)
        if events_to_write:
            try:
                blob_path = await self._blob.write_events(events_to_write)
                logger.info(f"Wrote {len(events_to_write)} events to {blob_path}")
            except Exception as exc:
                logger.error(f"Failed to write events to blob: {exc}")
                return  # Don't delete messages — they'll become visible again

        # Delete processed messages from queue (acknowledge)
        for msg in messages:
            try:
                await self._queue.delete_event(msg["id"], msg["pop_receipt"])
            except Exception as exc:
                logger.warning(f"Failed to delete message {msg['id']}: {exc}")

