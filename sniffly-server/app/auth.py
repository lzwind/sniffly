"""Authentication utilities for JWT and password hashing."""
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional
from app.config import settings

security = HTTPBearer(auto_error=False)


def get_current_user(token: Optional[object] = Depends(security)) -> str | None:
    """Get current user from JWT token. Returns None if no valid token."""
    if token is None:
        return None
    # HTTPBearer returns HTTPAuthorizationCredentials object
    credentials = token.credentials if hasattr(token, 'credentials') else token
    payload = verify_token(credentials)
    if payload is None:
        return None
    return payload.get("sub")


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


async def require_admin(current_user: str = Depends(get_current_user)) -> str:
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
