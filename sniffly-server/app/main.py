"""FastAPI main application."""
from fastapi import FastAPI, Request, Response, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import json

from app.config import settings
from app.database import connect_mongodb, disconnect_mongodb, connect_redis, disconnect_redis, get_mongodb
from app.routers import auth_router, shares_router, gallery_router, admin_router
from app.auth import create_access_token, verify_password, decode_token, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    # Startup
    await connect_mongodb()
    await connect_redis()
    yield
    # Shutdown
    await disconnect_mongodb()
    await disconnect_redis()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth_router)
app.include_router(shares_router)
app.include_router(gallery_router)
app.include_router(admin_router)


# Security
security = HTTPBearer(auto_error=False)


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str | None:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials).get("sub")
    except Exception:
        return None


# ==================== Public Routes ====================

@app.get("/")
async def index(request: Request, current_user: str | None = Depends(get_optional_user)):
    """Public index page with public shares gallery."""
    db = get_mongodb()

    # Get public shares for gallery
    cursor = db.shares.find({"is_public": True}).sort("created_at", -1).limit(20)
    projects = []
    async for share in cursor:
        stats = share.get("statistics", {})
        overview = stats.get("overview", {})
        total_tokens = overview.get("total_tokens", {})
        token_count = (total_tokens.get("input", 0) + total_tokens.get("output", 0))
        user_interactions = stats.get("user_interactions", {})

        projects.append({
            "id": share["_id"],
            "project_name": share.get("project_name", "Untitled"),
            "created_by": share.get("created_by", "Unknown"),
            "created_at": share.get("created_at"),
            "stats": {
                "total_commands": user_interactions.get("user_commands_analyzed", 0),
                "total_tokens": token_count,
            }
        })

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "projects": projects,
            "current_user": current_user,
        }
    )


@app.get("/login")
async def login_page(request: Request, current_user: str | None = Depends(get_optional_user)):
    """Login page."""
    if current_user:
        return RedirectResponse(url="/admin", status_code=302)

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None}
    )


@app.post("/login")
async def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    """Handle login request."""
    db = get_mongodb()

    # Find user
    user = await db.users.find_one({"username": username})
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401
        )

    # Check if active
    if not user.get("is_active", True):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Account is disabled"},
            status_code=401
        )

    # Verify password
    if not verify_password(password, user["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password"},
            status_code=401
        )

    # Create token
    token = create_access_token(data={"sub": username})

    # Return HTML with token in a script for client storage
    return templates.TemplateResponse(
        "login_success.html",
        {"request": request, "username": username, "token": token}
    )


@app.get("/auth/logout")
async def logout():
    """Logout and redirect to home."""
    return RedirectResponse(url="/", status_code=302)


# ==================== Admin Routes ====================

@app.get("/admin")
async def admin_page(request: Request, current_user: str | None = Depends(get_optional_user)):
    """Admin dashboard overview page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    if current_user != settings.admin_username:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Access denied. Admin privileges required."},
            status_code=403
        )

    # Get stats
    db = get_mongodb()
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    total_shares = await db.shares.count_documents({})
    public_shares = await db.shares.count_documents({"is_public": True})

    # Recent shares
    cursor = db.shares.find().sort("created_at", -1).limit(5)
    recent_shares = []
    async for share in cursor:
        recent_shares.append({
            "id": share["_id"],
            "project_name": share.get("project_name", "Untitled"),
            "created_by": share.get("created_by", "Unknown"),
            "created_at": share.get("created_at"),
            "is_public": share.get("is_public", False),
        })

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "total_shares": total_shares,
        "public_shares": public_shares,
        "recent_shares": recent_shares,
    }

    return templates.TemplateResponse(
        "admin/index.html",
        {"request": request, "stats": stats, "active_page": "overview"}
    )


@app.get("/admin/users")
async def admin_users_page(request: Request, current_user: str | None = Depends(get_optional_user)):
    """User management page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    if current_user != settings.admin_username:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Access denied. Admin privileges required."},
            status_code=403
        )

    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "active_page": "users"}
    )


@app.get("/admin/shares")
async def admin_shares_page(request: Request, current_user: str | None = Depends(get_optional_user)):
    """Share management page."""
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)

    if current_user != settings.admin_username:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error": "Access denied. Admin privileges required."},
            status_code=403
        )

    return templates.TemplateResponse(
        "admin/shares.html",
        {"request": request, "active_page": "shares"}
    )


# ==================== Existing Routes ====================

@app.get("/share/{share_id}")
async def share_page(request: Request, share_id: str):
    """Render share page."""
    db = get_mongodb()

    share = await db.shares.find_one({"_id": share_id})
    if not share:
        return templates.TemplateResponse(
            "share.html",
            {"request": request, "error": "Share not found"}
        )

    # Prepare chart configs for client-side rendering
    charts = share.get("charts", [])
    charts_json = json.dumps(charts)

    return templates.TemplateResponse(
        "share.html",
        {
            "request": request,
            "project_name": share.get("project_name", "Untitled"),
            "created_at": share.get("created_at"),
            "created_by": share.get("created_by", "Unknown"),
            "statistics": share.get("statistics", {}),
            "charts": charts,
            "charts_json": charts_json,
            "user_commands": share.get("user_commands", [])
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
