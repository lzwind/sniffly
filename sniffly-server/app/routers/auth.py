"""Authentication router for login/logout."""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.auth import verify_password, get_password_hash, create_access_token
from app.models import UserLogin, TokenResponse

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Authenticate user and return JWT token."""
    # Verify credentials against admin settings
    if credentials.username != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check password (compare with hashed version)
    # For simplicity, we store/compare plaintext in settings for now
    # In production, settings.admin_password should be bcrypt hashed
    if credentials.password != settings.admin_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Create JWT token
    access_token = create_access_token(
        data={"sub": credentials.username}
    )

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_hours * 3600
    )
