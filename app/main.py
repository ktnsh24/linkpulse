"""LinkPulse — FastAPI application entry point.

This module wires together all infrastructure clients, services, middleware,
routes, and the background worker using FastAPI's lifespan context manager.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.routes import analytics, health, links
from app.config import Settings, get_settings
from app.domain.services.link_service import LinkService
from app.infrastructure.storage.blob_client import BlobStorageClient
from app.infrastructure.storage.queue_client import QueueClient
from app.infrastructure.storage.table_client import TableStorageClient
from app.worker.event_worker import ClickEventWorker


@asynccontextmanager
async def app_lifespan(application: FastAPI):
    """Startup and shutdown lifecycle.

    Startup:
      1. Load settings
      2. Initialize Azure Storage clients (Table, Queue, Blob)
      3. Create domain services
      4. Start background worker
    Shutdown:
      1. Stop background worker
      2. Close all Azure clients
    """
    settings: Settings = get_settings()
    logger.info(f"Starting LinkPulse ({settings.app_env})")

    # ── Initialize infrastructure clients ──
    table_client = TableStorageClient(
        connection_string=settings.azure_storage_connection_string,
        links_table=settings.table_links,
        clicks_table=settings.table_clicks,
    )
    queue_client = QueueClient(
        connection_string=settings.azure_storage_connection_string,
        queue_name=settings.queue_click_events,
    )
    blob_client = BlobStorageClient(
        connection_string=settings.azure_storage_connection_string,
        container_name=settings.blob_container_events,
    )

    await table_client.init()
    await queue_client.init()
    await blob_client.init()

    # ── Create domain services ──
    link_service = LinkService(
        table_client=table_client,
        queue_client=queue_client,
        code_length=settings.short_code_length,
    )

    # ── Start background worker ──
    worker = ClickEventWorker(
        queue_client=queue_client,
        table_client=table_client,
        blob_client=blob_client,
    )
    await worker.start()

    # ── Attach to app.state for route access ──
    application.state.settings = settings
    application.state.table_client = table_client
    application.state.queue_client = queue_client
    application.state.blob_client = blob_client
    application.state.link_service = link_service
    application.state.worker = worker

    logger.info("LinkPulse ready")
    yield

    # ── Shutdown ──
    logger.info("Shutting down LinkPulse")
    await worker.stop()
    await table_client.close()
    await queue_client.close()
    await blob_client.close()
    logger.info("LinkPulse stopped")


app = FastAPI(
    title="LinkPulse",
    description="URL Shortener with Click Analytics — event-driven microservice on Azure",
    version="0.1.0",
    lifespan=app_lifespan,
)

# ── Middleware (order matters: request flows top→bottom in, bottom→top out) ──
app.add_middleware(RequestLoggingMiddleware)

# ── Routes ──
app.include_router(health.router, tags=["Health"])
app.include_router(analytics.router, tags=["Analytics"])
app.include_router(links.router, tags=["Links"])  # Must be last (has /{short_code} catch-all)

