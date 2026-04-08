"""FastAPI main entry point - serves API and static files."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api import auth, shares, users

app = FastAPI(title="Sniffly Site API")

# Include API routers
app.include_router(auth.router)
app.include_router(shares.router)
app.include_router(users.router)

# Get the directory containing this file
BASE_DIR = Path(__file__).parent.absolute()


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve login page (index.html)."""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>Sniffly Site</h1><p>Please ensure index.html exists.</p>")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve dashboard page."""
    dashboard_path = BASE_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    return HTMLResponse(content="<h1>Dashboard</h1><p>Please ensure dashboard.html exists.</p>", status_code=404)


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def share_page(share_id: str):
    """Serve share viewer page."""
    share_path = BASE_DIR / "share.html"
    if share_path.exists():
        return FileResponse(str(share_path))
    return HTMLResponse(content="<h1>Share</h1><p>Please ensure share.html exists.</p>", status_code=404)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    """Serve admin page."""
    admin_path = BASE_DIR / "admin.html"
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
