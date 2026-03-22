"""Azure Storage Queue client — sends and receives click events asynchronously."""

import json

from azure.storage.queue.aio import QueueServiceClient
from loguru import logger


class QueueClient:
    """Wraps Azure Storage Queue for async click event processing."""

    def __init__(self, connection_string: str, queue_name: str):
        self._conn_str = connection_string
        self._queue_name = queue_name
        self._service: QueueServiceClient | None = None

    async def init(self) -> None:
        """Create queue if it doesn't exist (called once at startup)."""
        self._service = QueueServiceClient.from_connection_string(self._conn_str)
        queue = self._service.get_queue_client(self._queue_name)
        try:
            await queue.create_queue()
            logger.info(f"Queue '{self._queue_name}' ready")
        except Exception:
            # Queue already exists — that's fine
            logger.info(f"Queue '{self._queue_name}' already exists")

    async def close(self) -> None:
        if self._service:
            await self._service.close()

    async def send_event(self, event: dict) -> None:
        """Send a click event to the queue (non-blocking, fire-and-forget)."""
        queue = self._service.get_queue_client(self._queue_name)
        message = json.dumps(event)
        await queue.send_message(message)

    async def receive_events(self, max_messages: int = 10) -> list[dict]:
        """Receive a batch of click events from the queue.

        Returns list of dicts with 'id', 'pop_receipt', and 'content' keys.
        """
        queue = self._service.get_queue_client(self._queue_name)
        messages = []
        received = queue.receive_messages(max_messages=max_messages, visibility_timeout=30)
        async for msg in received:
            try:
                content = json.loads(msg.content)
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed queue message: {msg.content}")
                content = {"raw": msg.content}
            messages.append({
                "id": msg.id,
                "pop_receipt": msg.pop_receipt,
                "content": content,
            })
        return messages

    async def delete_event(self, message_id: str, pop_receipt: str) -> None:
        """Delete a processed message from the queue (acknowledge)."""
        queue = self._service.get_queue_client(self._queue_name)
        await queue.delete_message(message_id, pop_receipt)

