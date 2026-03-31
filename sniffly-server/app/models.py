"""Pydantic models for request/response validation."""
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class UserLogin(BaseModel):
    """用户登录请求模型"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ShareData(BaseModel):
    """分享数据模型"""
    statistics: dict[str, Any]
    charts: list[dict[str, Any]]
    user_commands: list[dict[str, Any]]
    version: str
    is_public: bool = False
    project_name: str


class ShareCreate(BaseModel):
    """创建分享请求模型"""
    share_id: str
    data: ShareData


class ShareResponse(BaseModel):
    """创建分享响应模型"""
    url: str
    share_id: str


class ShareStats(BaseModel):
    """分享统计数据模型"""
    total_commands: int
    total_tokens: int
    duration_days: int


class ShareItem(BaseModel):
    """画廊列表项模型"""
    id: str
    title: str
    project_name: str
    created_at: datetime
    stats: ShareStats


class GalleryResponse(BaseModel):
    """画廊响应模型"""
    projects: list[ShareItem]
    total: int


# Admin models
class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    is_active: bool = True


class UserUpdate(BaseModel):
    """更新用户请求模型"""
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """用户响应模型"""
    username: str
    created_at: datetime
    is_active: bool
    share_count: int = 0


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    users: list[UserResponse]
    total: int
    page: int
    limit: int


class ShareAdminItem(BaseModel):
    """管理后台分享列表项"""
    id: str
    project_name: str
    created_by: str
    created_at: datetime
    is_public: bool


class ShareListResponse(BaseModel):
    """分享列表响应模型"""
    shares: list[ShareAdminItem]
    total: int
    page: int
    limit: int


class AdminStats(BaseModel):
    """系统统计模型"""
    total_users: int
    active_users: int
    total_shares: int
    public_shares: int
    recent_shares: list[ShareAdminItem]
