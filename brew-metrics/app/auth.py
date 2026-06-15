import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Request

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 8
COOKIE_NAME = "brew_admin_token"
COOKIE_MAX_AGE = JWT_EXPIRY_HOURS * 3600


class NotAuthenticatedError(Exception):
    pass


def set_admin_cookie(response, token: str) -> None:
    """Write the admin session cookie with the standard attributes."""
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        path="/",
    )


def get_admin_credentials() -> dict:
    return {
        "username": os.environ.get("ADMIN_USERNAME", "admin"),
        "password": os.environ.get("ADMIN_PASSWORD", "admin"),
    }


def check_credentials(username: str, password: str) -> bool:
    creds = get_admin_credentials()
    return username == creds["username"] and password == creds["password"]


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def require_admin(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise NotAuthenticatedError
    payload = verify_token(token)
    if not payload:
        raise NotAuthenticatedError
    return payload
