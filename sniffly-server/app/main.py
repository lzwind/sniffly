"""FastAPI main application."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json

from app.config import settings
from app.database import connect_mongodb, disconnect_mongodb, connect_redis, disconnect_redis
from app.routers import auth, shares, gallery


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
app.include_router(auth.router)
app.include_router(shares.router)
app.include_router(gallery.router)


@app.get("/share/{share_id}")
async def share_page(request: Request, share_id: str):
    """Render share page."""
    from app.database import get_mongodb
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
