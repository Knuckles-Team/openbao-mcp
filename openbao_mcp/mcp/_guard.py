"""Confirmation guard shared by the destructive typed tools."""

from typing import Any

CONFIRMATION_REQUIRED: dict[str, Any] = {
    "error": "confirmation_required",
    "message": "This call is destructive. Pass confirm=true after the person agrees.",
}
