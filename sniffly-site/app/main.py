"""FastAPI main entry point - serves API and static files."""

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.auth import SessionLocal
from app.models import Share
from app.routers import auth, shares, users
from app.routers.shares import get_gallery, get_gallery_project, toggle_feature_project

app = FastAPI(title="Sniffly Site API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(shares.router)
app.include_router(users.router)

# Add gallery routes directly (not under /api/shares prefix)
app.add_api_route("/api/gallery", get_gallery, methods=["GET"], tags=["gallery"])
app.add_api_route("/api/gallery/{share_id}", get_gallery_project, methods=["GET"], tags=["gallery"])
app.add_api_route("/api/gallery/{share_id}/feature", toggle_feature_project, methods=["POST"], tags=["gallery"])

# Get the project root directory (parent of app/)
BASE_DIR = Path(__file__).parent.parent.absolute()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve login page (index.html)."""
    index_path = BASE_DIR / "templates" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>Sniffly Site</h1><p>Please ensure index.html exists.</p>")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard page."""
    dashboard_path = BASE_DIR / "templates" / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return HTMLResponse(content="<h1>Dashboard</h1><p>Please ensure dashboard.html exists.</p>", status_code=404)


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def share_page(share_id: str):
    """Serve share viewer page with injected data."""
    share_path = BASE_DIR / "templates" / "share.html"
    if not share_path.exists():
        return HTMLResponse(content="<h1>Share</h1><p>Please ensure share.html exists.</p>", status_code=404)

    # Get share data from database
    db = SessionLocal()
    try:
        share = db.query(Share).filter(Share.uuid == share_id).first()
        if not share:
            return HTMLResponse(content="<h1>Share Not Found</h1><p>The requested share does not exist.</p>", status_code=404)

        # Prepare share data for injection
        share_data = {
            "project_name": share.project_name,
            "stats": share.stats,
            "user_commands": share.user_commands,
        }

        # Read template and inject data
        template_content = share_path.read_text(encoding='utf-8')
        share_data_json = json.dumps(share_data, ensure_ascii=False)
        injected_script = f"window.SHARE_DATA = {share_data_json};"

        # Replace placeholder with actual data
        html_content = template_content.replace(
            "// SHARE_DATA_INJECTION",
            injected_script
        )

        return HTMLResponse(content=html_content)
    finally:
        db.close()


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Serve admin page."""
    admin_path = BASE_DIR / "templates" / "admin.html"
    if admin_path.exists():
        return FileResponse(str(admin_path))
    return HTMLResponse(content="<h1>Admin</h1><p>Please ensure admin.html exists.</p>", status_code=404)


# Mount static files
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
