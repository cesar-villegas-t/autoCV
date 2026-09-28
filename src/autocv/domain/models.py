"""Strict CV contract, independent of HTTP and provider transport."""
import json
from typing import Annotated, Any
from pydantic import AfterValidator, BaseModel, ConfigDict, ValidationError, model_validator
from autocv.domain.text import plain

Text = Annotated[str, AfterValidator(plain)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)


class Contact(StrictModel):
    email: Text
    phone: Text
    location: Text
    linkedin: Text
    github: Text


class Experience(StrictModel):
    title: Text
    company: Text
    dates: Text
    location: Text
    bullets: list[Text]


class Education(StrictModel):
    degree: Text
    institution: Text
    dates: Text
    details: Text


class Project(StrictModel):
    name: Text
    tech: Text
    bullets: list[Text]


class Skill(StrictModel):
    category: Text
    items: list[Text]


class Resume(StrictModel):
    name: Text
    headline: Text
    contact: Contact
    summary: Text
    experience: list[Experience]
    education: list[Education]
    projects: list[Project]
    skills: list[Skill]
    languages: list[Text]

    @model_validator(mode="after")
    def usable_content(self) -> "Resume":
        if not self.name or not self.headline:
            raise ValueError("Missing candidate name or headline.")
        if not any((self.experience, self.education, self.projects, self.skills)):
            raise ValueError("Missing usable CV content.")
        return self


def parse_resume(model_output: str) -> dict[str, Any]:
    try:
        return Resume.model_validate(json.loads(model_output)).model_dump()
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("Gemini returned an invalid CV object.") from exc
