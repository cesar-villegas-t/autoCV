from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker
from starlette.exceptions import HTTPException

from autocv.application.auth import AuthService
from autocv.application.generation import Generator
from autocv.application.profile import ProfileService
from autocv.config import Settings
from autocv.infrastructure.db.session import create_db_engine, create_session_factory
from apps.api.errors import ApiError
from apps.api.routes.auth import router as auth_router
from apps.api.routes.generations import router
from apps.api.routes.profile import router as profile_router
from apps.api.schemas.generations import ErrorDetail, ErrorResponse, FieldIssue

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PRIVATE_PREFIXES = ("/api/v1/profile", "/api/v1/auth")
MAX_ISSUES = 20


def create_app(settings: Settings | None = None, generator: Generator | None = None,
               session_factory: sessionmaker[Session] | None = None,
               auth: AuthService | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="autoCV", version="0.1.0")
    app.state.settings = settings
    app.state.generator = generator or Generator(settings)
    if session_factory is None and settings.database_url:
        session_factory = create_session_factory(create_db_engine(settings.database_url))
    app.state.session_factory = session_factory
    app.state.auth = auth or AuthService(ttl=timedelta(days=settings.session_days))
    app.state.profiles = ProfileService()
    # Credentials are needed for the session cookie; origins stay explicit, never wildcards.
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Content-Type"])

    def error(status: int, code: str, message: str, fields: list[FieldIssue] | None = None):
        body = ErrorResponse(error=ErrorDetail(code=code, message=message, fields=fields))
        return JSONResponse(status_code=status, content=body.model_dump(mode="json"))

    @app.middleware("http")
    async def reject_cross_origin_writes(request: Request, call_next):
        # CSRF defense in depth on top of SameSite=Lax. Non-browser clients send no Origin.
        origin = request.headers.get("origin")
        if request.method not in SAFE_METHODS and origin is not None:
            own = f"{request.url.scheme}://{request.url.netloc}"
            if origin != own and origin not in settings.cors_origins:
                return error(403, "forbidden_origin", "Cross-origin request rejected.")
        response = await call_next(request)
        if request.url.path.startswith(PRIVATE_PREFIXES):
            response.headers["Cache-Control"] = "no-store"  # Personal data must not linger in caches.
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, exc: ApiError):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError):
        # FastAPI's default validation response echoes input values, possibly CVs. Report only
        # where and why (never the value) so forms can point at the offending field.
        issues = [FieldIssue(field=".".join(str(part) for part in item["loc"][1:])[:120],
                             message=str(item["msg"]).removeprefix("Value error, ")[:200])
                  for item in exc.errors()[:MAX_ISSUES]]
        return error(422, "invalid_request", "Invalid request. Check the listed fields.", issues or None)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error(exc.status_code, "http_error", "The requested operation is unavailable.")

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return error(500, "internal_error", "The request could not be completed.")

    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(profile_router)
    return app


app = create_app()
