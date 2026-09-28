"""HTTP adapter. Replace the service boundary to add queued generation later."""
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from autocv.application.generation import GenerationError, Generator
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
             responses={422: {"model": ErrorResponse}, 502: {"model": GenerationResponse},
                        503: {"model": GenerationResponse}, 500: {"model": GenerationResponse}})
def generate(body: GenerateRequest, generator: Generator = Depends(get_generator)):
    try:
        result = generator.generate_cv(**body.model_dump())
    except GenerationError as exc:
        code = 502 if exc.code.startswith("provider_") else {"not_configured": 503, "invalid_cv": 502}.get(exc.code, 500)
        response = GenerationResponse(id=str(uuid4()), status=GenerationStatus.failed,
                                      error=ErrorDetail(code=exc.code, message=str(exc)))
        return JSONResponse(status_code=code, content=response.model_dump(mode="json"))
    return GenerationResponse(
        id=result.id, status=GenerationStatus.completed,
        download_url=f"/api/v1/cv/generations/{result.id}/pdf",
    )


@router.get("/cv/generations/{generation_id}/pdf", response_class=FileResponse,
            responses={200: {"content": {"application/pdf": {}}},
                       404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def download(generation_id: UUID, request: Request):
    # Only UUIDs address isolated artifact directories; never accept a client path.
    root = request.app.state.settings.output_dir.resolve()
    directory = root / str(generation_id)
    files = [p for p in directory.iterdir() if p.suffix.lower() == ".pdf"] if directory.is_dir() else []
    if (directory.is_symlink() or len(files) != 1 or files[0].is_symlink()
            or not files[0].is_file() or not files[0].resolve().is_relative_to(root)):
        error = ErrorResponse(error=ErrorDetail(code="not_found", message="PDF not found."))
        return JSONResponse(status_code=404, content=error.model_dump(mode="json"))
    return FileResponse(files[0], media_type="application/pdf", filename=files[0].name,
                        headers={"Cache-Control": "no-store"})
