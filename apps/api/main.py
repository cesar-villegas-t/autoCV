from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from autocv.application.generation import Generator
from autocv.config import Settings
from apps.api.routes.generations import router
from apps.api.schemas.generations import ErrorDetail, ErrorResponse


def create_app(settings: Settings | None = None, generator: Generator | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="autoCV", version="0.1.0")
    app.state.settings = settings
    app.state.generator = generator or Generator(settings)
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=False, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    def error(status: int, code: str, message: str):
        body = ErrorResponse(error=ErrorDetail(code=code, message=message))
        return JSONResponse(status_code=status, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # FastAPI's default validation response echoes input values, possibly CVs.
        return error(422, "invalid_request", "Invalid request. Check the text fields and PDF filename.")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(exc.status_code, "http_error", "The requested operation is unavailable.")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return error(500, "internal_error", "The request could not be completed.")

    app.include_router(router)
    return app


app = create_app()
