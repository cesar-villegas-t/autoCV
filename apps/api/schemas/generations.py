from enum import Enum
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from autocv.domain.files import normalized_pdf_name


class GenerationStatus(str, Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    # Either the profile text is sent (uploaded file) or the saved profile is used, never both.
    profile_text: Annotated[str, Field(min_length=1, max_length=100_000)] | None = None
    use_saved_profile: bool = False
    offer_text: Annotated[str, Field(min_length=1, max_length=100_000)]
    output_name: str = "cv.pdf"

    @field_validator("profile_text", "offer_text")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Text must not be blank.")
        return value

    @model_validator(mode="after")
    def one_profile_source(self):
        if (self.profile_text is None) == (not self.use_saved_profile):
            raise ValueError("Send either profile_text or use_saved_profile, not both or neither.")
        return self

    @field_validator("output_name")
    @classmethod
    def filename(cls, value: str) -> str:
        return normalized_pdf_name(value)


class FieldIssue(BaseModel):
    """Location and reason only; the offending value is never echoed back."""
    field: str
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[FieldIssue] | None = None


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
