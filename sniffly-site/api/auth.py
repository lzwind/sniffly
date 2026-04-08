"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
)
from models import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 Password Grant - get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """JSON login endpoint for web frontend."""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint (client should discard token)."""
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(id=current_user.id, username=current_user.username, is_admin=current_user.is_admin)
