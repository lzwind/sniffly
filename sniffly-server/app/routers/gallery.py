"""Gallery router for listing shared projects."""
from fastapi import APIRouter, Query
from app.database import get_mongodb
from app.models import GalleryResponse, ShareItem, ShareStats
from datetime import datetime

router = APIRouter(prefix="/api/gallery", tags=["gallery"])

@router.get("", response_model=GalleryResponse)
async def get_gallery(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get list of shared projects with pagination."""
    db = get_mongodb()

    # Calculate skip
    skip = (page - 1) * limit

    # Query shares sorted by created_at desc
    cursor = db.shares.find().sort("created_at", -1).skip(skip).limit(limit)
    shares = await cursor.to_list(length=limit)

    # Get total count
    total = await db.shares.count_documents({})

    # Format response
    projects = []
    for share in shares:
        stats = share.get("statistics", {})
        overview = stats.get("overview", {})

        # Calculate duration days
        start_date = overview.get("start_date", "")
        end_date = overview.get("end_date", "")
        duration_days = 0
        if start_date and end_date:
            try:
                start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                duration_days = (end - start).days + 1
            except:
                pass

        projects.append(ShareItem(
            id=share["_id"],
            title=share.get("project_name", "Untitled"),
            project_name=share.get("project_name", "Untitled"),
            created_at=share.get("created_at", datetime.utcnow()),
            stats=ShareStats(
                total_commands=overview.get("total_messages", 0),
                total_tokens=overview.get("total_tokens", {}).get("input", 0) +
                           overview.get("total_tokens", {}).get("output", 0),
                duration_days=duration_days
            )
        ))

    return GalleryResponse(projects=projects, total=total)
