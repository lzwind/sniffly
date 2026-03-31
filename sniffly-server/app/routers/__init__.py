"""Routers package for Sniffly Server."""

from app.routers.auth import router as auth_router
from app.routers.shares import router as shares_router
from app.routers.gallery import router as gallery_router
from app.routers.admin import router as admin_router

__all__ = ["auth_router", "shares_router", "gallery_router", "admin_router"]
