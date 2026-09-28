"""Account endpoints. The session lives in an HttpOnly cookie; only its digest is stored."""
from typing import Iterator

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from apps.api.errors import ApiError
from apps.api.schemas.auth import Credentials, UserResponse
from apps.api.schemas.generations import ErrorResponse
from autocv.application.auth import AuthError, AuthService
from autocv.infrastructure.db.models import User

SESSION_COOKIE = "autocv_session"
STATUS = {"invalid_email": 422, "weak_password": 422, "email_taken": 409, "invalid_credentials": 401}

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_db(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    if factory is None:
        raise ApiError(503, "not_configured", "The database is not configured.")
    with factory() as session:
        yield session


def get_auth(request: Request) -> AuthService:
    return request.app.state.auth


def current_user(request: Request, db: Session = Depends(get_db), auth: AuthService = Depends(get_auth)) -> User:
    user = auth.user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise ApiError(401, "unauthenticated", "Sign in to continue.")
    return user


def _cookie_options(request: Request) -> dict:
    return {"httponly": True, "samesite": "lax", "path": "/",
            "secure": request.app.state.settings.cookie_secure}


def _start_session(request: Request, response: Response, auth: AuthService, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, max_age=int(auth.ttl.total_seconds()), **_cookie_options(request))


def _fail(exc: AuthError) -> ApiError:
    return ApiError(STATUS.get(exc.code, 400), exc.code, str(exc))


@router.post("/register", response_model=UserResponse, status_code=201,
             responses={409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
def register(body: Credentials, request: Request, response: Response,
             db: Session = Depends(get_db), auth: AuthService = Depends(get_auth)):
    try:
        user, token = auth.register(db, body.email, body.password)
    except AuthError as exc:
        raise _fail(exc) from None
    _start_session(request, response, auth, token)
    return user


@router.post("/login", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
def login(body: Credentials, request: Request, response: Response,
          db: Session = Depends(get_db), auth: AuthService = Depends(get_auth)):
    try:
        user, token = auth.login(db, body.email, body.password)
    except AuthError as exc:
        raise _fail(exc) from None
    _start_session(request, response, auth, token)
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db), auth: AuthService = Depends(get_auth)):
    auth.logout(db, request.cookies.get(SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, **_cookie_options(request))
    return response


@router.get("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
def me(user: User = Depends(current_user)):
    return user
