"""LinkPulse application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration is loaded from environment variables or .env file."""

    # --- Application ---
    app_name: str = "linkpulse"
    app_env: str = "local"  # local | main
    base_url: str = "http://localhost:8000"  # public URL for short links
    log_level: str = "INFO"

    # --- Azure Storage (Table + Queue + Blob in one account) ---
    azure_storage_connection_string: str = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
        "QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )

    # --- Azure Table Storage ---
    table_links: str = "links"  # stores short_code → original_url mappings
    table_clicks: str = "clicks"  # stores per-code click counters

    # --- Azure Storage Queue ---
    queue_click_events: str = "click-events"

    # --- Azure Blob Storage ---
    blob_container_events: str = "click-events-lake"

    # --- Azure Application Insights (optional, empty = disabled) ---
    appinsights_connection_string: str = ""

    # --- Short code settings ---
    short_code_length: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Factory function for dependency injection."""
    return Settings()

