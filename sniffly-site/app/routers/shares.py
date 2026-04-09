"""Shares API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_db, require_admin
from app.models import Share, User


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


@router.get("/stats")
async def get_shares_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get shares statistics (admin only)."""
    total = db.query(Share).count()
    public = db.query(Share).filter(Share.is_public == True).count()
    private = total - public
    with_commands = db.query(Share).filter(Share.user_commands != []).count()

    return {
        "total": total,
        "total_active": total,
        "total_deleted": 0,
        "public": public,
        "public_active": public,
        "public_deleted": 0,
        "private": private,
        "private_active": private,
        "private_deleted": 0,
        "with_commands": with_commands,
        "with_commands_active": with_commands,
    }


@router.get("/gallery")
async def get_gallery(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all shares as gallery projects (admin only)."""
    from sqlalchemy import func

    # Load without ordering to avoid sort_buffer_size issues with large JSON columns
    shares = db.query(
        Share.id,
        Share.uuid,
        Share.project_name,
        Share.is_featured,
        Share.stats,
        Share.created_at,
        Share.updated_at,
    ).all()

    # Sort in Python instead of MySQL
    shares = sorted(shares, key=lambda x: x.updated_at or x.created_at, reverse=True)

    result = []
    for share in shares:
        stats = share.stats or {}
        overview = stats.get("overview", {})
        total_tokens = overview.get("total_tokens", {})

        result.append({
            "id": share.id,
            "uuid": share.uuid,
            "project_name": share.project_name,
            "is_featured": share.is_featured,
            "total_commands": 0,  # Simplified to avoid loading large JSON
            "total_tokens": total_tokens.get("input", 0) + total_tokens.get("output", 0),
            "created_at": share.created_at.isoformat() if share.created_at else None,
            "updated_at": share.updated_at.isoformat() if share.updated_at else None,
        })

    return result


@router.get("/gallery/{share_id}")
async def get_gallery_project(
    share_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get a single gallery project details (admin only)."""
    share = db.query(Share).filter(Share.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    return {
        "id": share.id,
        "uuid": share.uuid,
        "project_name": share.project_name,
        "is_featured": share.is_featured,
        "stats": share.stats,
        "user_commands": share.user_commands,
        "created_at": share.created_at.isoformat() if share.created_at else None,
        "updated_at": share.updated_at.isoformat() if share.updated_at else None,
    }


@router.post("/gallery/{share_id}/feature")
async def toggle_feature_project(
    share_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Toggle featured status for a project (admin only)."""
    share = db.query(Share).filter(Share.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    share.is_featured = not share.is_featured
    db.commit()

    return {
        "id": share.id,
        "is_featured": share.is_featured,
        "message": "Featured status updated",
    }


@router.get("/public/{share_uuid}")
async def get_public_share(share_uuid: str, db: Session = Depends(get_db)):
    """Get a single share by UUID (public access, no authentication required)."""
    share = db.query(Share).filter(Share.uuid == share_uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    # Return only necessary fields, excluding sensitive info like user_id
    return {
        "uuid": share.uuid,
        "project_name": share.project_name,
        "stats": share.stats,
        "user_commands": share.user_commands,
        "created_at": share.created_at,
        "updated_at": share.updated_at,
    }


@router.get("/{share_uuid}", response_model=ShareDetailResponse)
async def get_share(
    share_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single share by UUID (requires authentication)."""
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
