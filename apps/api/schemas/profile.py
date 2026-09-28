from datetime import datetime

from pydantic import BaseModel

from autocv.domain.profile import CandidateProfile


class ProfileResponse(BaseModel):
    profile: CandidateProfile
    updated_at: datetime | None
    # Machine-readable gaps for the generation flow: name, email, experience_or_education.
    missing: list[str]
    complete: bool
