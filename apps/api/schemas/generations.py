from enum import Enum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator
from autocv.domain.files import normalized_pdf_name


class GenerationStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    profile_text: Annotated[str, Field(min_length=1, max_length=100_000)]
    offer_text: Annotated[str, Field(min_length=1, max_length=100_000)]
    output_name: str = "cv.pdf"

    @field_validator("profile_text", "offer_text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must not be blank.")
        return value

    @field_validator("output_name")
    @classmethod
    def filename(cls, value: str) -> str:
        return normalized_pdf_name(value)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    status: GenerationStatus = GenerationStatus.failed
    error: ErrorDetail


class GenerationResponse(BaseModel):
    id: str
    status: GenerationStatus
    download_url: str | None = None
    error: ErrorDetail | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
