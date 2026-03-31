"""Share router for creating and retrieving shares."""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings
from app.auth import verify_token
from app.database import get_mongodb
from app.models import ShareCreate, ShareResponse
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/shares", tags=["shares"])
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token and return user info."""
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload.get("sub")

@router.post("", response_model=ShareResponse)
async def create_share(
    share: ShareCreate,
    request: Request,
    username: str = Depends(get_current_user)
):
    """Create a new share."""
    db = get_mongodb()

    # Prepare share document
    share_doc = {
        "_id": share.share_id,
        "created_at": datetime.utcnow(),
        "statistics": share.data.statistics,
        "charts": share.data.charts,
        "user_commands": share.data.user_commands,
        "version": share.data.version,
        "is_public": share.data.is_public,
        "project_name": share.data.project_name,
        "created_by": username,
        "expires_at": None
    }

    # Insert into MongoDB
    await db.shares.insert_one(share_doc)

    # Generate share URL
    base_url = str(request.base_url).rstrip("/")
    share_url = f"{base_url}/share/{share.share_id}"

    return ShareResponse(url=share_url, share_id=share.share_id)

@router.get("/{share_id}")
async def get_share(share_id: str):
    """Get share data by ID (for internal use)."""
    db = get_mongodb()
    share = await db.shares.find_one({"_id": share_id})
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found"
        )
    return share
