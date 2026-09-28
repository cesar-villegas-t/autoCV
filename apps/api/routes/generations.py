"""HTTP adapter. Replace the service boundary to add queued generation later."""
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from autocv.application.generation import GenerationError, Generator
from autocv.application.profile import ProfileError, ProfileService
from autocv.infrastructure.db.models import Generation, User
from apps.api.errors import ApiError
from apps.api.routes.auth import current_user, get_db
from apps.api.routes.profile import get_profiles
from apps.api.schemas.generations import (
    ErrorDetail, ErrorResponse, GenerateRequest, GenerationResponse,
    GenerationStatus, HealthResponse,
)

router = APIRouter(prefix="/api/v1")


def get_generator(request: Request) -> Generator:
    return request.app.state.generator


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post("/cv/generations", response_model=GenerationResponse, status_code=201,
             responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse},
                        502: {"model": GenerationResponse}, 503: {"model": GenerationResponse},
                        500: {"model": GenerationResponse}})
def generate(body: GenerateRequest, user: User = Depends(current_user), db: Session = Depends(get_db),
             generator: Generator = Depends(get_generator), profiles: ProfileService = Depends(get_profiles)):
    if body.use_saved_profile:
        try:
            profile_text = profiles.markdown_for_generation(db, user.id)
        except ProfileError as exc:
            raise ApiError(422 if exc.code == "profile_incomplete" else 409, exc.code, str(exc)) from None
    else:
        profile_text = body.profile_text
    # Generation can take minutes: end the read transaction so no pooled connection is held meanwhile.
    db.commit()
    try:
        result = generator.generate_cv(profile_text=profile_text, offer_text=body.offer_text,
                                       output_name=body.output_name)
    except GenerationError as exc:
        code = 502 if exc.code.startswith("provider_") else {"not_configured": 503, "invalid_cv": 502}.get(exc.code, 500)
        response = GenerationResponse(id=str(uuid4()), status=GenerationStatus.failed,
                                      error=ErrorDetail(code=exc.code, message=str(exc)))
        return JSONResponse(status_code=code, content=response.model_dump(mode="json"))
    db.add(Generation(id=UUID(result.id), user_id=user.id))
    db.commit()
    return GenerationResponse(
        id=result.id, status=GenerationStatus.completed,
        download_url=f"/api/v1/cv/generations/{result.id}/pdf",
    )


@router.get("/cv/generations/{generation_id}/pdf", response_class=FileResponse,
            responses={200: {"content": {"application/pdf": {}}}, 401: {"model": ErrorResponse},
                       404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def download(generation_id: UUID, request: Request, user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    # Only UUIDs address isolated artifact directories; never accept a client path.
    root = request.app.state.settings.output_dir.resolve()
    directory = root / str(generation_id)
    record = db.get(Generation, generation_id)
    # Someone else's PDF is reported as missing so its existence is not revealed.
    owned = record is not None and record.user_id == user.id
    files = [p for p in directory.iterdir() if p.suffix.lower() == ".pdf"] if owned and directory.is_dir() else []
    if (directory.is_symlink() or len(files) != 1 or files[0].is_symlink()
            or not files[0].is_file() or not files[0].resolve().is_relative_to(root)):
        error = ErrorResponse(error=ErrorDetail(code="not_found", message="PDF not found."))
        return JSONResponse(status_code=404, content=error.model_dump(mode="json"))
    return FileResponse(files[0], media_type="application/pdf", filename=files[0].name,
                        headers={"Cache-Control": "no-store"})
