from typing import Any

from pydantic import BaseModel, Field


class StandardResponse(BaseModel):
    status: int = Field(default=200, description="HTTP status code")
    message: str = Field(default="Success", description="Status message")
    data: Any | None = Field(default=None, description="Response payload")
    error: str | None = Field(default=None, description="Error message if failed")
