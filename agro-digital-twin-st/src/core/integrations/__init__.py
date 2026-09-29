"""Read-only integrations with external scientific services."""

from .fastapi_client import (
    FastAPIClient,
    FastAPIConnectionError,
    choose_preferred_simulation,
)

__all__ = ["FastAPIClient", "FastAPIConnectionError", "choose_preferred_simulation"]
