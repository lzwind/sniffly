"""Authentication utilities for JWT and password hashing."""
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from typing import Optional
from app.config import settings

security = HTTPBearer(auto_error=False)


def get_current_user(token: Optional[object] = Depends(security)) -> str | None:
    """
    Get current user from JWT token.
    FastAPI injects Request via Depends(Request) when called as a dependency.
    """
    return None


async def get_current_user_with_cookie(request: Request, token: Optional[object] = Depends(security)) -> str | None:
    """
    Get current user from JWT token — checks both Bearer header and session cookie.

    Checks in order:
    1. Authorization: Bearer <token> header (HTTPBearer, for API clients)
    2. sniffly_session cookie (for browser sessions)
    """
    import logging
    logger = logging.getLogger("uvicorn")
    logger.warning(f"[AUTH DEBUG] request.cookies: {dict(request.cookies)}")
    logger.warning(f"[AUTH DEBUG] token from HTTPBearer: {token}")

    # Priority 1: HTTPBearer header (API clients, playwright, etc.)
    if token is not None:
        credentials = token.credentials if hasattr(token, 'credentials') else token
        payload = verify_token(credentials)
        if payload is not None:
            logger.warning(f"[AUTH DEBUG] Authenticated via Bearer: {payload.get('sub')}")
            return payload.get("sub")

    # Priority 2: sniffly_session cookie (browser sessions)
    token_str = request.cookies.get("sniffly_session")
    logger.warning(f"[AUTH DEBUG] token_str from cookie: {token_str}")
    if token_str:
        payload = verify_token(token_str)
        logger.warning(f"[AUTH DEBUG] payload from cookie: {payload}")
        if payload is not None:
            return payload.get("sub")

    return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a password."""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expire_hours)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict | None:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.PyJWTError:
        return None


async def require_admin(request: Request, current_user: str = Depends(get_current_user_with_cookie)) -> str:
    """检查当前用户是否为管理员"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    if current_user != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# 别名兼容
hash_password = get_password_hash
decode_token = verify_token
