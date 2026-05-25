from pydantic import BaseModel, Field
from typing import Any, Optional

class StandardResponse(BaseModel):
    status: int = Field(default=200, description="HTTP status code")
    message: str = Field(default="Success", description="Status message")
    data: Optional[Any] = Field(default=None, description="Response payload")
    error: Optional[str] = Field(default=None, description="Error message if failed")
