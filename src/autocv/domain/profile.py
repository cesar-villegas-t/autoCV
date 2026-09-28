"""Structured candidate profile edited by the user and rendered to Markdown for generation."""
import re
from typing import Annotated

from pydantic import (AfterValidator, BaseModel, ConfigDict, Field, StringConstraints,
                      model_validator)

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^[0-9+().\-\s]{5,30}$")


def _clean(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if _CONTROL.search(value):
        raise ValueError("Control characters are not allowed.")
    return value


def text(max_length: int, min_length: int = 0):
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=min_length,
                                            max_length=max_length), AfterValidator(_clean)]


def _web_address(value: str) -> str:
    scheme = _SCHEME.match(value)
    if scheme and scheme.group(1).lower() not in {"http", "https"}:
        raise ValueError("Only http(s) addresses are allowed.")
    if re.search(r"\s", value):
        raise ValueError("Addresses must not contain spaces.")
    return value


def _email(value: str) -> str:
    if value and not _EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _phone(value: str) -> str:
    if value and not _PHONE.match(value):
        raise ValueError("Enter a valid phone number.")
    return value


Month = Annotated[str, Field(pattern=MONTH_PATTERN)]
WebAddress = Annotated[text(200), AfterValidator(_web_address)]


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


def _check_dates(block, *, needs_end: bool = False) -> None:
    if block.current and block.end_date:
        raise ValueError("A current entry cannot have an end date.")
    if needs_end and not block.current and not block.end_date:
        raise ValueError("Set an end date or mark it as current.")
    if block.start_date and block.end_date and block.end_date < block.start_date:
        raise ValueError("The end date must not be before the start date.")


class Link(_Block):
    label: text(60, 1)
    url: WebAddress


class Experience(_Block):
    company: text(120, 1)
    title: text(120, 1)
    start_date: Month
    end_date: Month | None = None
    # Explicit so that leaving the end date empty can never claim a job is ongoing.
    current: bool = False
    description: text(4000) = ""

    @model_validator(mode="after")
    def dates(self):
        _check_dates(self, needs_end=True)
        return self


class Education(_Block):
    institution: text(160, 1)
    degree: text(160, 1)
    location: text(120) = ""
    start_date: Month | None = None
    end_date: Month | None = None
    current: bool = False
    grade: text(60) = ""
    description: text(4000) = ""

    @model_validator(mode="after")
    def dates(self):
        _check_dates(self)
        return self


class DatedItem(_Block):
    """Achievement or project."""
    name: text(160, 1)
    start_date: Month | None = None
    end_date: Month | None = None
    current: bool = False
    description: text(4000) = ""

    @model_validator(mode="after")
    def dates(self):
        _check_dates(self)
        return self


class Language(_Block):
    language: text(60, 1)
    level: text(60) = ""
    certification: text(120) = ""


class CandidateProfile(_Block):
    first_name: text(80) = ""
    last_name: text(120) = ""
    location: text(120) = ""
    relocations: Annotated[list[text(80, 1)], Field(max_length=10)] = []
    phone: Annotated[text(30), AfterValidator(_phone)] = ""
    email: Annotated[text(320), AfterValidator(_email)] = ""
    linkedin: WebAddress = ""
    links: Annotated[list[Link], Field(max_length=10)] = []
    summary: text(2000) = ""
    experience: Annotated[list[Experience], Field(max_length=30)] = []
    education: Annotated[list[Education], Field(max_length=20)] = []
    achievements: Annotated[list[DatedItem], Field(max_length=30)] = []
    projects: Annotated[list[DatedItem], Field(max_length=30)] = []
    skills: text(6000) = ""
    languages: Annotated[list[Language], Field(max_length=15)] = []


def missing_for_generation(profile: CandidateProfile) -> list[str]:
    """Machine-readable gaps that stop a CV from being generated from this profile."""
    missing = []
    if not profile.first_name:
        missing.append("name")
    if not profile.email:
        missing.append("email")
    if not profile.experience and not profile.education:
        missing.append("experience_or_education")
    return missing
