"""Shares API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, get_db, require_admin
from models import Share, User


router = APIRouter(prefix="/api/shares", tags=["shares"])


class ShareCreateRequest(BaseModel):
    project_name: str
    stats: dict
    user_commands: list


class ShareResponse(BaseModel):
    uuid: str
    project_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShareDetailResponse(BaseModel):
    uuid: str
    project_name: str
    stats: dict
    user_commands: list
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def merge_user_commands(existing: list, new: list) -> list:
    """Merge user_commands by timestamp + content hash deduplication."""
    seen = set()
    merged = list(existing)

    for cmd in new:
        key = (cmd.get("timestamp"), cmd.get("hash"))
        if key and key not in seen:
            seen.add(key)
            exists = any(
                c.get("timestamp") == cmd.get("timestamp") and c.get("hash") == cmd.get("hash")
                for c in existing
            )
            if not exists:
                merged.append(cmd)

    merged.sort(key=lambda x: x.get("timestamp", ""))
    return merged


@router.get("", response_model=list[ShareResponse])
async def list_shares(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's shares."""
    shares = db.query(Share).filter(Share.user_id == current_user.id).order_by(Share.updated_at.desc()).all()
    return shares


@router.post("", response_model=ShareResponse)
async def create_or_update_share(
    share_data: ShareCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a share (merge logic)."""
    existing = (
        db.query(Share)
        .filter(Share.user_id == current_user.id, Share.project_name == share_data.project_name)
        .first()
    )

    if existing:
        existing.stats = share_data.stats
        existing.user_commands = merge_user_commands(existing.user_commands, share_data.user_commands)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_uuid = str(uuid.uuid4())
        new_share = Share(
            uuid=new_uuid,
            user_id=current_user.id,
            project_name=share_data.project_name,
            stats=share_data.stats,
            user_commands=share_data.user_commands,
        )
        db.add(new_share)
        db.commit()
        db.refresh(new_share)
        return new_share


@router.get("/{share_uuid}", response_model=ShareDetailResponse)
async def get_share(
    share_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single share by UUID."""
    share = db.query(Share).filter(Share.uuid == share_uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    if share.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return share


@router.delete("/{share_uuid}")
async def delete_share(
    share_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a share."""
    share = db.query(Share).filter(Share.uuid == share_uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    if share.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db.delete(share)
    db.commit()
    return {"message": "Share deleted"}
