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
