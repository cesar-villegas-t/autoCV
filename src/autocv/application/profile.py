"""Profile use cases: read, save, clear and prepare the Markdown sent to the generator."""
import uuid
from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from autocv.domain.profile import CandidateProfile, missing_for_generation
from autocv.domain.profile_markdown import render_profile_markdown
from autocv.infrastructure.db.models import Profile

# Same ceiling as the generation endpoint accepts for profile text.
MAX_MARKDOWN_LENGTH = 100_000


class ProfileError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StoredProfile:
    profile: CandidateProfile
    updated_at: datetime | None

    @property
    def missing(self) -> list[str]:
        return missing_for_generation(self.profile)


class ProfileService:
    def get(self, db: Session, user_id: uuid.UUID) -> StoredProfile:
        row = db.get(Profile, user_id)
        if row is None:
            return StoredProfile(CandidateProfile(), None)
        try:
            return StoredProfile(CandidateProfile.model_validate(row.data), row.updated_at)
        except ValidationError:
            raise ProfileError("profile_invalid", "The saved profile is no longer valid. Review and save it again.") from None

    def save(self, db: Session, user_id: uuid.UUID, profile: CandidateProfile) -> StoredProfile:
        if len(render_profile_markdown(profile)) > MAX_MARKDOWN_LENGTH:
            raise ProfileError("profile_too_large", "The profile is too long. Shorten some descriptions.")
        data = profile.model_dump(mode="json")
        # Atomic upsert: two first saves racing each other cannot fail on the primary key.
        statement = insert(Profile).values(user_id=user_id, data=data)
        statement = statement.on_conflict_do_update(
            index_elements=[Profile.user_id], set_={"data": data, "updated_at": func.now()},
        ).returning(Profile.updated_at)
        updated_at = db.execute(statement).scalar_one()
        db.commit()
        return StoredProfile(profile, updated_at)

    def clear(self, db: Session, user_id: uuid.UUID) -> None:
        db.execute(delete(Profile).where(Profile.user_id == user_id))
        db.commit()

    def markdown(self, db: Session, user_id: uuid.UUID) -> str:
        return render_profile_markdown(self.get(db, user_id).profile)

    def markdown_for_generation(self, db: Session, user_id: uuid.UUID) -> str:
        stored = self.get(db, user_id)
        if stored.missing:
            raise ProfileError("profile_incomplete", "Complete your profile before generating: " + ", ".join(
                {"name": "first name", "email": "email",
                 "experience_or_education": "at least one work experience or education entry"}[key]
                for key in stored.missing) + ".")
        return render_profile_markdown(stored.profile)
