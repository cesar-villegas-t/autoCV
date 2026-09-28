"""The signed-in user's saved profile. Everything here is scoped to the session's user."""
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from apps.api.errors import ApiError
from apps.api.routes.auth import current_user, get_db
from apps.api.schemas.generations import ErrorResponse
from apps.api.schemas.profile import ProfileResponse
from autocv.application.profile import ProfileError, ProfileService, StoredProfile
from autocv.domain.profile import CandidateProfile
from autocv.infrastructure.db.models import User

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])
STATUS = {"profile_too_large": 422, "profile_invalid": 409, "profile_incomplete": 422}
UNAUTHENTICATED = {401: {"model": ErrorResponse}}


def get_profiles(request: Request) -> ProfileService:
    return request.app.state.profiles


def fail(exc: ProfileError) -> ApiError:
    return ApiError(STATUS.get(exc.code, 400), exc.code, str(exc))


def respond(stored: StoredProfile) -> ProfileResponse:
    return ProfileResponse(profile=stored.profile, updated_at=stored.updated_at,
                           missing=stored.missing, complete=not stored.missing)


@router.get("", response_model=ProfileResponse, responses=UNAUTHENTICATED)
def read_profile(user: User = Depends(current_user), db: Session = Depends(get_db),
                 profiles: ProfileService = Depends(get_profiles)):
    try:
        return respond(profiles.get(db, user.id))
    except ProfileError as exc:
        raise fail(exc) from None


@router.put("", response_model=ProfileResponse,
            responses={**UNAUTHENTICATED, 422: {"model": ErrorResponse}})
def save_profile(body: CandidateProfile, user: User = Depends(current_user),
                 db: Session = Depends(get_db), profiles: ProfileService = Depends(get_profiles)):
    try:
        return respond(profiles.save(db, user.id, body))
    except ProfileError as exc:
        raise fail(exc) from None


@router.delete("", status_code=204, responses=UNAUTHENTICATED)
def clear_profile(user: User = Depends(current_user), db: Session = Depends(get_db),
                  profiles: ProfileService = Depends(get_profiles)):
    profiles.clear(db, user.id)
    return Response(status_code=204)


@router.get("/markdown", response_class=PlainTextResponse, responses=UNAUTHENTICATED)
def read_profile_markdown(user: User = Depends(current_user), db: Session = Depends(get_db),
                          profiles: ProfileService = Depends(get_profiles)):
    """Exactly the text that would be sent to the generator, so users can see what is used."""
    try:
        return PlainTextResponse(profiles.markdown(db, user.id), media_type="text/markdown; charset=utf-8",
                                 headers={"Cache-Control": "no-store"})
    except ProfileError as exc:
        raise fail(exc) from None
