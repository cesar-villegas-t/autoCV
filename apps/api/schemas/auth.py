from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Format and strength are checked by the service so messages stay specific but never echo input.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128, repr=False)


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
