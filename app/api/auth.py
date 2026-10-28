"""Login for the web UI: one account from settings, stored in a signed session cookie.

The cookie is signed with SESSION_SECRET (Starlette's SessionMiddleware), so it cannot
be forged without the secret. Registration and multiple users come later.
"""

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import Settings

router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(max_length=200)
    password: str = Field(max_length=200)


class UserOut(BaseModel):
    username: str


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def require_user(request: Request) -> str:
    """Dependency: the logged-in username, or 401."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    return user


CurrentUser = Annotated[str, Depends(require_user)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]


def _matches(given: str, expected: str) -> bool:
    # Constant-time comparison, so response timing does not leak how much matched.
    return secrets.compare_digest(given.encode(), expected.encode())


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    settings: AppSettings,
) -> UserOut:
    client_ip = request.client.host if request.client else "unknown"
    if not request.app.state.login_limiter.allow(client_ip):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many login attempts")

    username_ok = _matches(body.username, settings.app_username)
    password_ok = _matches(body.password, settings.app_password.get_secret_value())
    if not (username_ok and password_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong username or password")

    request.session.clear()
    request.session["user"] = settings.app_username
    return UserOut(username=settings.app_username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request) -> None:
    request.session.clear()


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut(username=user)
