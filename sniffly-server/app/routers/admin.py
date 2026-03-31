"""Admin API routes for user and share management."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import get_current_user, require_admin, hash_password, verify_password
from app.database import get_mongodb
from app.models import (
    AdminStats,
    ShareAdminItem,
    ShareListResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(username: str = Depends(require_admin)):
    """获取系统统计信息"""
    db = get_mongodb()

    # 用户统计
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})

    # 分享统计
    total_shares = await db.shares.count_documents({})
    public_shares = await db.shares.count_documents({"is_public": True})

    # 最近分享
    cursor = db.shares.find().sort("created_at", -1).limit(5)
    recent_shares = []
    async for share in cursor:
        recent_shares.append(ShareAdminItem(
            id=share["_id"],
            project_name=share.get("project_name", "Untitled"),
            created_by=share.get("created_by", "Unknown"),
            created_at=share.get("created_at", datetime.utcnow()),
            is_public=share.get("is_public", False),
        ))

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_shares=total_shares,
        public_shares=public_shares,
        recent_shares=recent_shares,
    )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    username: str = Depends(require_admin),
):
    """获取用户列表"""
    db = get_mongodb()
    skip = (page - 1) * limit

    total = await db.users.count_documents({})
    cursor = db.users.find().sort("created_at", -1).skip(skip).limit(limit)

    users = []
    async for user in cursor:
        # 计算用户创建的分享数量
        share_count = await db.shares.count_documents({"created_by": user["username"]})
        users.append(UserResponse(
            username=user["username"],
            created_at=user.get("created_at", datetime.utcnow()),
            is_active=user.get("is_active", True),
            share_count=share_count,
        ))

    return UserListResponse(users=users, total=total, page=page, limit=limit)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    username: str = Depends(require_admin),
):
    """创建新用户"""
    db = get_mongodb()

    # 检查用户名是否已存在
    existing = await db.users.find_one({"username": user_data.username})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # 创建用户
    now = datetime.utcnow()
    await db.users.insert_one({
        "username": user_data.username,
        "password_hash": hash_password(user_data.password),
        "created_at": now,
        "is_active": user_data.is_active,
    })

    return UserResponse(
        username=user_data.username,
        created_at=now,
        is_active=user_data.is_active,
        share_count=0,
    )


@router.get("/users/{target_username}", response_model=UserResponse)
async def get_user(
    target_username: str,
    username: str = Depends(require_admin),
):
    """获取用户详情"""
    db = get_mongodb()

    user = await db.users.find_one({"username": target_username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    share_count = await db.shares.count_documents({"created_by": target_username})

    return UserResponse(
        username=user["username"],
        created_at=user.get("created_at", datetime.utcnow()),
        is_active=user.get("is_active", True),
        share_count=share_count,
    )


@router.put("/users/{target_username}", response_model=UserResponse)
async def update_user(
    target_username: str,
    user_data: UserUpdate,
    username: str = Depends(require_admin),
):
    """更新用户信息"""
    db = get_mongodb()

    # 获取现有用户
    user = await db.users.find_one({"username": target_username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 准备更新数据
    update_data = {}
    if user_data.password is not None:
        update_data["password_hash"] = hash_password(user_data.password)
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active

    if update_data:
        await db.users.update_one(
            {"username": target_username},
            {"$set": update_data}
        )

    share_count = await db.shares.count_documents({"created_by": target_username})

    return UserResponse(
        username=target_username,
        created_at=user.get("created_at", datetime.utcnow()),
        is_active=user_data.is_active if user_data.is_active is not None else user.get("is_active", True),
        share_count=share_count,
    )


@router.delete("/users/{target_username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    target_username: str,
    username: str = Depends(require_admin),
):
    """删除用户"""
    db = get_mongodb()

    # 检查是否是最后一个管理员
    if target_username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    # 检查用户是否存在
    user = await db.users.find_one({"username": target_username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 删除用户
    await db.users.delete_one({"username": target_username})


@router.get("/shares", response_model=ShareListResponse)
async def list_shares(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    username: str = Depends(require_admin),
):
    """获取分享列表"""
    db = get_mongodb()
    skip = (page - 1) * limit

    total = await db.shares.count_documents({})
    cursor = db.shares.find().sort("created_at", -1).skip(skip).limit(limit)

    shares = []
    async for share in cursor:
        shares.append(ShareAdminItem(
            id=share["_id"],
            project_name=share.get("project_name", "Untitled"),
            created_by=share.get("created_by", "Unknown"),
            created_at=share.get("created_at", datetime.utcnow()),
            is_public=share.get("is_public", False),
        ))

    return ShareListResponse(shares=shares, total=total, page=page, limit=limit)


@router.delete("/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share(
    share_id: str,
    username: str = Depends(require_admin),
):
    """删除分享"""
    db = get_mongodb()

    result = await db.shares.delete_one({"_id": share_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )
