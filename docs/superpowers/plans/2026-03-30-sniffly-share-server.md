# 内网 Sniffly 分享系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建内网 Sniffly 分享服务端和改造客户端，支持认证、服务器地址管理和分享功能

**Architecture:** FastAPI + MongoDB + Redis 服务端，改造现有 sniffly 客户端支持服务器选择、JWT 认证和分享

**Tech Stack:** Python 3.11+, FastAPI, Motor, Redis, PyJWT, bcrypt, Docker Compose

---

## 文件结构

### 新建文件（sniffly-server）

| 文件 | 职责 |
|------|------|
| `sniffly-server/app/__init__.py` | 包初始化 |
| `sniffly-server/app/main.py` | FastAPI 应用入口 |
| `sniffly-server/app/config.py` | 配置管理（环境变量、默认值） |
| `sniffly-server/app/database.py` | MongoDB 和 Redis 连接 |
| `sniffly-server/app/auth.py` | JWT 认证、密码哈希 |
| `sniffly-server/app/models.py` | Pydantic 数据模型 |
| `sniffly-server/app/routers/auth.py` | 认证路由（登录） |
| `sniffly-server/app/routers/shares.py` | 分享 CRUD 路由 |
| `sniffly-server/app/routers/gallery.py` | 画廊列表路由 |
| `sniffly-server/templates/share.html` | 分享页面 HTML 模板 |
| `sniffly-server/static/css/share.css` | 分享页面样式 |
| `sniffly-server/Dockerfile` | 服务端 Docker 镜像 |
| `sniffly-server/docker-compose.yml` | 完整部署配置 |
| `sniffly-server/requirements.txt` | Python 依赖 |
| `sniffly-server/.env.example` | 环境变量示例 |

### 修改文件（sniffly 客户端）

| 文件 | 修改内容 |
|------|----------|
| `sniffly/templates/dashboard.html` | 新增服务器选择、认证表单的 HTML |
| `sniffly/static/js/share-modal.js` | 服务器地址管理、JWT 认证、API 调用 |
| `sniffly/static/css/share-modal.css` | 服务器选择器、登录表单样式 |
| `sniffly/share.py` | 修改 `_upload_via_api()` 支持自定义服务器和 JWT |

---

## Phase 1: 服务端开发

### Task 1: 项目脚手架和依赖

**Files:**
- Create: `sniffly-server/requirements.txt`
- Create: `sniffly-server/.env.example`
- Create: `sniffly-server/app/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
motor==3.3.2
redis==5.0.1
pyjwt==2.8.0
bcrypt==4.1.2
jinja2==3.1.3
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
```

- [ ] **Step 2: 创建 .env.example**

```bash
# MongoDB
MONGODB_URL=mongodb://mongo:27017/sniffly

# Redis
REDIS_URL=redis://redis:6379

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Admin credentials (initial user)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme

# CORS (allow all for internal network)
CORS_ORIGINS=["*"]
```

- [ ] **Step 3: 创建 app/__init__.py**

```python
"""Sniffly Server - Internal share server for sniffly analytics."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Commit**

```bash
git add sniffly-server/
git commit -m "feat: add sniffly-server project scaffold"
```

---

### Task 2: 配置管理

**Files:**
- Create: `sniffly-server/app/config.py`

- [ ] **Step 1: 创建 config.py**

```python
"""Configuration management using pydantic-settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Server configuration."""

    # App
    app_name: str = "Sniffly Server"
    debug: bool = False

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017/sniffly"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret: str = Field(default="dev-secret-key")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin"

    # CORS
    cors_origins: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/config.py
git commit -m "feat: add configuration management"
```

---

### Task 3: 数据库连接

**Files:**
- Create: `sniffly-server/app/database.py`

- [ ] **Step 1: 创建 database.py**

```python
"""Database connections for MongoDB and Redis."""

import motor.motor_asyncio
import redis.asyncio as redis

from app.config import settings

# MongoDB client
mongo_client: motor.motor_asyncio.AsyncIOMotorClient | None = None

# Redis client
redis_client: redis.Redis | None = None


async def connect_mongodb():
    """Connect to MongoDB."""
    global mongo_client
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
    return mongo_client


async def disconnect_mongodb():
    """Disconnect from MongoDB."""
    global mongo_client
    if mongo_client:
        mongo_client.close()


async def connect_redis():
    """Connect to Redis."""
    global redis_client
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client


async def disconnect_redis():
    """Disconnect from Redis."""
    global redis_client
    if redis_client:
        await redis_client.close()


def get_mongodb():
    """Get MongoDB database."""
    if mongo_client is None:
        raise RuntimeError("MongoDB not connected")
    return mongo_client.get_default_database()


def get_redis():
    """Get Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis not connected")
    return redis_client
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/database.py
git commit -m "feat: add MongoDB and Redis connection handlers"
```

---

### Task 4: 认证模块

**Files:**
- Create: `sniffly-server/app/auth.py`

- [ ] **Step 1: 创建 auth.py**

```python
"""Authentication utilities - JWT and password hashing."""

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.jwt_expire_hours))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = decode_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/auth.py
git commit -m "feat: add JWT authentication and password hashing"
```

---

### Task 5: 数据模型

**Files:**
- Create: `sniffly-server/app/models.py`

- [ ] **Step 1: 创建 models.py**

```python
"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Auth models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Share models
class ShareData(BaseModel):
    statistics: Dict[str, Any]
    charts: List[Dict[str, Any]]
    user_commands: List[Dict[str, Any]] = []
    version: str
    is_public: bool = False
    project_name: Optional[str] = None


class CreateShareRequest(BaseModel):
    share_id: str
    data: ShareData


class CreateShareResponse(BaseModel):
    url: str
    share_id: str


class ShareInfo(BaseModel):
    id: str
    title: Optional[str] = None
    project_name: str
    created_at: datetime
    created_by: str
    includes_commands: bool
    stats: Dict[str, Any]


class GalleryResponse(BaseModel):
    projects: List[ShareInfo]
    total: int


# User model (for internal use)
class User(BaseModel):
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/models.py
git commit -m "feat: add Pydantic data models"
```

---

### Task 6: 认证路由

**Files:**
- Create: `sniffly-server/app/routers/__init__.py`
- Create: `sniffly-server/app/routers/auth.py`

- [ ] **Step 1: 创建 routers/__init__.py**

```python
"""API routers."""
```

- [ ] **Step 2: 创建 auth.py**

```python
"""Authentication routes."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, status

from app.auth import create_access_token, hash_password, verify_password
from app.config import settings
from app.database import get_mongodb
from app.models import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def get_or_create_admin_user():
    """Get or create the admin user on startup."""
    db = get_mongodb()
    users = db.users

    admin = await users.find_one({"username": settings.admin_username})
    if not admin:
        # Create admin user
        await users.insert_one({
            "username": settings.admin_username,
            "password_hash": hash_password(settings.admin_password),
        })
        print(f"Created admin user: {settings.admin_username}")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    db = get_mongodb()
    users = db.users

    # Find user
    user = await users.find_one({"username": request.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Create JWT token
    access_token = create_access_token(data={"sub": request.username})

    return LoginResponse(
        access_token=access_token,
        expires_in=settings.jwt_expire_hours * 3600,
    )
```

- [ ] **Step 3: Commit**

```bash
git add sniffly-server/app/routers/__init__.py sniffly-server/app/routers/auth.py
git commit -m "feat: add authentication router with login endpoint"
```

---

### Task 7: 分享路由

**Files:**
- Create: `sniffly-server/app/routers/shares.py`

- [ ] **Step 1: 创建 shares.py**

```python
"""Share CRUD routes."""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import get_current_user
from app.database import get_mongodb
from app.models import CreateShareRequest, CreateShareResponse

router = APIRouter(prefix="/api/shares", tags=["shares"])


def get_base_url(request: Request) -> str:
    """Get base URL from request."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.hostname)
    port = request.headers.get("x-forwarded-port", request.url.port)

    if port and port not in (80, 443, None):
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


@router.post("", response_model=CreateShareResponse, status_code=status.HTTP_201_CREATED)
async def create_share(
    request: CreateShareRequest,
    http_request: Request,
    username: str = Depends(get_current_user),
):
    """Create a new share."""
    db = get_mongodb()
    shares = db.shares

    # Check if share_id already exists
    existing = await shares.find_one({"_id": request.share_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Share ID already exists",
        )

    # Prepare share document
    share_doc = {
        "_id": request.share_id,
        "created_at": datetime.utcnow(),
        "created_by": username,
        "statistics": request.data.statistics,
        "charts": request.data.charts,
        "user_commands": request.data.user_commands,
        "version": request.data.version,
        "is_public": request.data.is_public,
        "project_name": request.data.project_name or "Unknown Project",
    }

    # Insert into database
    await shares.insert_one(share_doc)

    # Generate URL
    base_url = get_base_url(http_request)
    url = f"{base_url}/share/{request.share_id}"

    return CreateShareResponse(url=url, share_id=request.share_id)


@router.get("/{share_id}")
async def get_share(share_id: str) -> Dict[str, Any]:
    """Get a share by ID (for internal API use)."""
    db = get_mongodb()
    shares = db.shares

    share = await shares.find_one({"_id": share_id})
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share not found",
        )

    # Convert _id to id for response
    share["id"] = share.pop("_id")
    return share
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/routers/shares.py
git commit -m "feat: add share CRUD router"
```

---

### Task 8: 画廊路由

**Files:**
- Create: `sniffly-server/app/routers/gallery.py`

- [ ] **Step 1: 创建 gallery.py**

```python
"""Gallery listing routes."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Query

from app.database import get_mongodb
from app.models import GalleryResponse, ShareInfo

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


@router.get("", response_model=GalleryResponse)
async def list_gallery(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List all shares for gallery view."""
    db = get_mongodb()
    shares = db.shares

    # Calculate skip
    skip = (page - 1) * limit

    # Get total count
    total = await shares.count_documents({})

    # Get shares sorted by created_at desc
    cursor = shares.find().sort("created_at", -1).skip(skip).limit(limit)

    projects: List[ShareInfo] = []
    async for share in cursor:
        stats = share.get("statistics", {})
        overview = stats.get("overview", {})
        total_tokens = overview.get("total_tokens", {})
        token_count = total_tokens.get("input", 0) + total_tokens.get("output", 0)

        # Calculate duration
        date_range = overview.get("date_range", {})
        duration_days = 0
        if date_range.get("start") and date_range.get("end"):
            try:
                start = datetime.fromisoformat(date_range["start"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(date_range["end"].replace("Z", "+00:00"))
                duration_days = (end - start).days + 1
            except (ValueError, TypeError):
                pass

        user_interactions = stats.get("user_interactions", {})

        projects.append(ShareInfo(
            id=share["_id"],
            title=share.get("project_name"),
            project_name=share.get("project_name", "Unknown Project"),
            created_at=share["created_at"],
            created_by=share.get("created_by", "unknown"),
            includes_commands=len(share.get("user_commands", [])) > 0,
            stats={
                "total_commands": user_interactions.get("user_commands_analyzed", 0),
                "total_tokens": token_count,
                "duration_days": duration_days,
                "total_cost": overview.get("total_cost", 0),
                "interruption_rate": user_interactions.get("interruption_rate", 0),
                "avg_steps_per_command": user_interactions.get("avg_steps_per_command", 0),
            },
        ))

    return GalleryResponse(projects=projects, total=total)
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/routers/gallery.py
git commit -m "feat: add gallery listing router"
```

---

### Task 9: 分享页面模板

**Files:**
- Create: `sniffly-server/templates/share.html`
- Create: `sniffly-server/static/css/share.css`

- [ ] **Step 1: 创建 templates 目录和 share.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ project_name }} - Sniffly Share</title>
    <link rel="stylesheet" href="/static/css/share.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>{{ project_name }}</h1>
            <p class="meta">Shared on {{ created_at.strftime('%Y-%m-%d %H:%M') }} by {{ created_by }}</p>
        </header>

        <section class="stats-overview">
            <h2>Overview</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Total Commands</h3>
                    <p class="value">{{ stats.get('user_interactions', {}).get('user_commands_analyzed', 0) }}</p>
                </div>
                <div class="stat-card">
                    <h3>Total Tokens</h3>
                    <p class="value">{{ '{:,}'.format(stats.get('overview', {}).get('total_tokens', {}).get('input', 0) + stats.get('overview', {}).get('total_tokens', {}).get('output', 0)) }}</p>
                </div>
                <div class="stat-card">
                    <h3>Duration</h3>
                    <p class="value">{{ duration_days }} days</p>
                </div>
                <div class="stat-card">
                    <h3>Interruption Rate</h3>
                    <p class="value">{{ stats.get('user_interactions', {}).get('interruption_rate', 0) }}%</p>
                </div>
            </div>
        </section>

        <section class="charts">
            <h2>Charts</h2>
            <div class="charts-grid">
                {% for chart in charts %}
                <div class="chart-container">
                    <h3>{{ chart.name }}</h3>
                    <canvas id="chart-{{ loop.index }}"></canvas>
                </div>
                {% endfor %}
            </div>
        </section>
    </div>

    <script>
        // Chart configurations from server
        const chartConfigs = {{ charts | tojson }};

        // Initialize charts
        chartConfigs.forEach((config, index) => {
            const ctx = document.getElementById(`chart-${index + 1}`).getContext('2d');
            new Chart(ctx, {
                type: config.type,
                data: config.data,
                options: config.options
            });
        });
    </script>
</body>
</html>
```

- [ ] **Step 2: 创建 static/css/share.css**

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

header {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

.meta {
    color: #666;
    font-size: 0.9rem;
}

section {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

section h2 {
    margin-bottom: 1.5rem;
    color: #667eea;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
}

.stat-card {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 6px;
    border: 1px solid #e0e0e0;
}

.stat-card h3 {
    font-size: 0.9rem;
    color: #666;
    margin-bottom: 0.5rem;
}

.stat-card .value {
    font-size: 2rem;
    font-weight: bold;
    color: #667eea;
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 2rem;
}

.chart-container {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 6px;
}

.chart-container h3 {
    margin-bottom: 1rem;
    font-size: 1rem;
}
```

- [ ] **Step 3: Commit**

```bash
git add sniffly-server/templates/ sniffly-server/static/
git commit -m "feat: add share page template and styles"
```

---

### Task 10: FastAPI 主应用

**Files:**
- Create: `sniffly-server/app/main.py`

- [ ] **Step 1: 创建 main.py**

```python
"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import connect_mongodb, connect_redis, disconnect_mongodb, disconnect_redis, get_mongodb
from app.routers import auth, gallery, shares


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    await connect_mongodb()
    await connect_redis()

    # Create admin user
    from app.routers.auth import get_or_create_admin_user
    await get_or_create_admin_user()

    yield

    # Shutdown
    await disconnect_mongodb()
    await disconnect_redis()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router)
app.include_router(shares.router)
app.include_router(gallery.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/share/{share_id}", response_class=HTMLResponse)
async def share_page(request: Request, share_id: str):
    """Render share page."""
    from datetime import datetime

    db = get_mongodb()
    shares = db.shares

    share = await shares.find_one({"_id": share_id})
    if not share:
        return HTMLResponse(content="Share not found", status_code=404)

    # Calculate duration
    stats = share.get("statistics", {})
    overview = stats.get("overview", {})
    date_range = overview.get("date_range", {})
    duration_days = 0
    if date_range.get("start") and date_range.get("end"):
        try:
            start = datetime.fromisoformat(date_range["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(date_range["end"].replace("Z", "+00:00"))
            duration_days = (end - start).days + 1
        except (ValueError, TypeError):
            pass

    return templates.TemplateResponse(
        "share.html",
        {
            "request": request,
            "project_name": share.get("project_name", "Unknown Project"),
            "created_at": share["created_at"],
            "created_by": share.get("created_by", "unknown"),
            "stats": stats,
            "duration_days": duration_days,
            "charts": share.get("charts", []),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/main.py
git commit -m "feat: add FastAPI main application with CORS and share page route"
```

---

### Task 11: Dockerfile

**Files:**
- Create: `sniffly-server/Dockerfile`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

# Expose port
EXPOSE 8080

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/Dockerfile
git commit -m "feat: add Dockerfile for sniffly-server"
```

---

### Task 12: Docker Compose 配置

**Files:**
- Create: `sniffly-server/docker-compose.yml`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - MONGODB_URL=mongodb://mongo:27017/sniffly
      - REDIS_URL=redis://redis:6379
      - JWT_SECRET=${JWT_SECRET:-dev-secret-key}
      - JWT_EXPIRE_HOURS=24
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin}
      - CORS_ORIGINS=["*"]
    depends_on:
      - mongo
      - redis
    restart: unless-stopped

  mongo:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  mongo_data:
  redis_data:
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/docker-compose.yml
git commit -m "feat: add docker-compose.yml for full stack deployment"
```

---

## Phase 2: 客户端修改

### Task 13: 分享弹窗 HTML 增强

**Files:**
- Modify: `sniffly/templates/dashboard.html`

- [ ] **Step 1: 在 dashboard.html 中找到分享弹窗位置**

查找现有分享弹窗的 HTML 结构，通常在 `message-modal.js` 动态创建或内嵌在 dashboard.html 中。

- [ ] **Step 2: 添加服务器选择和认证表单**

在分享弹窗的 modal-body 中添加：

```html
<!-- Server Selection Section -->
<div class="share-section">
    <h4>Server Address</h4>
    <div class="server-selector">
        <select id="server-select" class="server-select">
            <option value="">-- Select a server --</option>
        </select>
        <button type="button" id="add-server-btn" class="btn-secondary">+ Add New</button>
    </div>
    <div id="new-server-input" class="new-server-input" style="display: none;">
        <input type="text" id="new-server-url" placeholder="http://10.0.1.100:8080">
        <button type="button" id="save-server-btn" class="btn-primary">Save</button>
        <button type="button" id="cancel-server-btn" class="btn-secondary">Cancel</button>
    </div>
</div>

<!-- Authentication Section -->
<div class="share-section" id="auth-section">
    <h4>Authentication</h4>
    <div class="auth-form">
        <input type="text" id="auth-username" placeholder="Username">
        <input type="password" id="auth-password" placeholder="Password">
    </div>
</div>

<!-- Share Options -->
<div class="share-section">
    <label class="checkbox-label">
        <input type="checkbox" id="include-commands" checked>
        Include commands in share
    </label>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add sniffly/templates/dashboard.html
git commit -m "feat: add server selector and auth form to share modal"
```

---

### Task 14: 分享弹窗 CSS 增强

**Files:**
- Modify: `sniffly/static/css/share-modal.css`

- [ ] **Step 1: 添加服务器选择器和认证表单样式**

```css
/* Server Selection */
.share-section {
    margin-bottom: 1.5rem;
}

.share-section h4 {
    margin-bottom: 0.75rem;
    color: #333;
    font-size: 0.95rem;
}

.server-selector {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.server-select {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
}

.new-server-input {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.new-server-input input {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
}

/* Authentication Form */
.auth-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.auth-form input {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
}

/* Buttons */
.btn-primary {
    padding: 0.5rem 1rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.btn-primary:hover {
    background: #5a67d8;
}

.btn-secondary {
    padding: 0.5rem 1rem;
    background: #f0f0f0;
    color: #333;
    border: 1px solid #ddd;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.btn-secondary:hover {
    background: #e0e0e0;
}

/* Checkbox */
.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
}
```

- [ ] **Step 2: Commit**

```bash
git add sniffly/static/css/share-modal.css
git commit -m "feat: add server selector and auth form styles"
```

---

### Task 15: 分享弹窗 JavaScript 增强

**Files:**
- Modify: `sniffly/static/js/share-modal.js`

- [ ] **Step 1: 添加 LocalStorage 管理函数**

```javascript
// Server and token management in LocalStorage
const StorageKeys = {
    SERVERS: 'sniffly_servers',
    TOKENS: 'sniffly_tokens'
};

// Get saved servers
function getSavedServers() {
    try {
        const data = localStorage.getItem(StorageKeys.SERVERS);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('Failed to load servers:', e);
        return [];
    }
}

// Save servers
function saveServers(servers) {
    localStorage.setItem(StorageKeys.SERVERS, JSON.stringify(servers));
}

// Add new server
function addServer(url, name) {
    const servers = getSavedServers();
    // Check if already exists
    if (!servers.find(s => s.url === url)) {
        servers.push({
            url: url,
            name: name || url,
            last_used: new Date().toISOString()
        });
        saveServers(servers);
    }
}

// Update server last used
function updateServerLastUsed(url) {
    const servers = getSavedServers();
    const server = servers.find(s => s.url === url);
    if (server) {
        server.last_used = new Date().toISOString();
        saveServers(servers);
    }
}

// Get saved token for server
function getServerToken(serverUrl) {
    try {
        const tokens = JSON.parse(localStorage.getItem(StorageKeys.TOKENS) || '{}');
        const tokenData = tokens[serverUrl];
        if (tokenData && new Date(tokenData.expires_at) > new Date()) {
            return tokenData.token;
        }
        return null;
    } catch (e) {
        return null;
    }
}

// Save token for server
function saveServerToken(serverUrl, token, expiresIn) {
    const tokens = JSON.parse(localStorage.getItem(StorageKeys.TOKENS) || '{}');
    tokens[serverUrl] = {
        token: token,
        expires_at: new Date(Date.now() + expiresIn * 1000).toISOString()
    };
    localStorage.setItem(StorageKeys.TOKENS, JSON.stringify(tokens));
}
```

- [ ] **Step 2: 添加服务器选择器初始化**

```javascript
// Initialize server selector
function initServerSelector() {
    const select = document.getElementById('server-select');
    const servers = getSavedServers();

    // Clear existing options except first
    while (select.options.length > 1) {
        select.remove(1);
    }

    // Add server options
    servers.forEach(server => {
        const option = document.createElement('option');
        option.value = server.url;
        option.textContent = server.name;
        select.appendChild(option);
    });

    // Select most recently used
    if (servers.length > 0) {
        const mostRecent = servers.sort((a, b) =>
            new Date(b.last_used) - new Date(a.last_used)
        )[0];
        select.value = mostRecent.url;
    }
}

// Show/hide new server input
function toggleNewServerInput(show) {
    document.getElementById('new-server-input').style.display = show ? 'flex' : 'none';
    if (show) {
        document.getElementById('new-server-url').focus();
    }
}
```

- [ ] **Step 3: 添加认证函数**

```javascript
// Authenticate with server
async function authenticateWithServer(serverUrl, username, password) {
    const response = await fetch(`${serverUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Authentication failed');
    }

    const data = await response.json();
    saveServerToken(serverUrl, data.access_token, data.expires_in);
    return data.access_token;
}

// Get or refresh token
async function getAuthToken(serverUrl, username, password) {
    // Try cached token first
    let token = getServerToken(serverUrl);
    if (token) {
        return token;
    }

    // Authenticate
    token = await authenticateWithServer(serverUrl, username, password);
    return token;
}
```

- [ ] **Step 4: 修改 shareDashboard 函数**

```javascript
// Modified share function
async function shareDashboardWithServer() {
    const serverSelect = document.getElementById('server-select');
    const serverUrl = serverSelect.value;

    if (!serverUrl) {
        alert('Please select a server');
        return;
    }

    const username = document.getElementById('auth-username').value;
    const password = document.getElementById('auth-password').value;

    if (!username || !password) {
        alert('Please enter username and password');
        return;
    }

    try {
        // Update server last used
        updateServerLastUsed(serverUrl);

        // Get auth token
        const token = await getAuthToken(serverUrl, username, password);

        // Prepare share data
        const shareData = {
            share_id: generateShareId(),
            data: {
                statistics: statistics,
                charts: ExportModule.getChartConfigurations(),
                user_commands: getUserCommands(), // Get from dashboard
                version: '0.1.5',
                is_public: false,
                project_name: statistics.overview?.project_name || 'Unknown'
            }
        };

        // Upload to server
        const response = await fetch(`${serverUrl}/api/shares`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(shareData)
        });

        if (!response.ok) {
            throw new Error(`Share failed: ${response.statusText}`);
        }

        const result = await response.json();

        // Show success with link
        showShareResult(result.url);

    } catch (error) {
        console.error('Share failed:', error);
        alert('Share failed: ' + error.message);
    }
}

// Generate share ID
function generateShareId() {
    return Array.from(crypto.getRandomValues(new Uint8Array(12)))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');
}
```

- [ ] **Step 5: 添加事件监听器**

```javascript
// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize server selector when share modal opens
    const shareBtn = document.getElementById('share-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            initServerSelector();
        });
    }

    // Add server button
    const addServerBtn = document.getElementById('add-server-btn');
    if (addServerBtn) {
        addServerBtn.addEventListener('click', () => toggleNewServerInput(true));
    }

    // Save server button
    const saveServerBtn = document.getElementById('save-server-btn');
    if (saveServerBtn) {
        saveServerBtn.addEventListener('click', function() {
            const url = document.getElementById('new-server-url').value.trim();
            if (url) {
                addServer(url, url);
                initServerSelector();
                document.getElementById('server-select').value = url;
                toggleNewServerInput(false);
                document.getElementById('new-server-url').value = '';
            }
        });
    }

    // Cancel server button
    const cancelServerBtn = document.getElementById('cancel-server-btn');
    if (cancelServerBtn) {
        cancelServerBtn.addEventListener('click', () => toggleNewServerInput(false));
    }
});
```

- [ ] **Step 6: Commit**

```bash
git add sniffly/static/js/share-modal.js
git commit -m "feat: add server management, auth, and share upload to modal"
```

---

### Task 16: 修改 sniffly/share.py

**Files:**
- Modify: `sniffly/share.py`

- [ ] **Step 1: 修改 ShareManager 支持自定义服务器**

```python
# In sniffly/share.py, modify ShareManager class

class ShareManager:
    def __init__(self, base_url: str = None, api_token: str = None):
        """Initialize ShareManager with optional custom server URL and token."""
        from sniffly.config import Config
        config = Config()

        # Use provided base_url or fall back to config
        self.base_url = base_url or config.get("share_base_url", "https://sniffly.dev")
        self.api_token = api_token
        self.is_custom_server = base_url is not None

    async def _upload_via_api(self, share_id: str, data: dict[str, Any]):
        """Upload share data via API endpoint (for custom servers)."""
        import httpx

        # API endpoint for share uploads
        api_url = f"{self.base_url}/api/shares"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Prepare headers
                headers = {"Content-Type": "application/json"}
                if self.api_token:
                    headers["Authorization"] = f"Bearer {self.api_token}"

                # Prepare the share data with metadata
                payload = {
                    "share_id": share_id,
                    "data": data,
                    "is_public": data.get("is_public", False),
                }

                # POST to the API endpoint
                response = await client.post(api_url, json=payload, headers=headers)
                response.raise_for_status()

                logger.info(f"Uploaded share via API: {share_id}")

        except httpx.HTTPError as e:
            logger.error(f"Failed to upload share via API: {e}")
            raise Exception(f"Failed to upload share: {str(e)}")
```

- [ ] **Step 2: Commit**

```bash
git add sniffly/share.py
git commit -m "feat: modify ShareManager to support custom server and JWT token"
```

---

## Phase 3: 测试和部署

### Task 17: 本地测试服务端

**Files:**
- Run: `sniffly-server/`

- [ ] **Step 1: 创建虚拟环境并安装依赖**

```bash
cd sniffly-server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 2: 启动 MongoDB 和 Redis（使用 Docker）**

```bash
docker run -d -p 27017:27017 --name sniffly-mongo mongo:7
docker run -d -p 6379:6379 --name sniffly-redis redis:7-alpine
```

- [ ] **Step 3: 启动服务端**

```bash
cp .env.example .env
# Edit .env if needed
uvicorn app.main:app --reload --port 8080
```

- [ ] **Step 4: 测试 API**

```bash
# Health check
curl http://localhost:8080/health

# Login
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Create share (use token from login)
curl -X POST http://localhost:8080/api/shares \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"share_id":"test123","data":{"statistics":{},"charts":[],"version":"0.1.5"}}'
```

- [ ] **Step 5: Commit 测试文档（可选）**

```bash
git add sniffly-server/README.md  # If created
git commit -m "docs: add testing instructions"
```

---

### Task 18: Docker Compose 部署

**Files:**
- Run: `sniffly-server/docker-compose.yml`

- [ ] **Step 1: 构建并启动**

```bash
cd sniffly-server
# Set environment variables
export JWT_SECRET=$(openssl rand -hex 32)
export ADMIN_USERNAME=admin
export ADMIN_PASSWORD=your-secure-password

# Build and run
docker-compose up --build -d
```

- [ ] **Step 2: 验证部署**

```bash
# Check containers
docker-compose ps

# Check logs
docker-compose logs -f app

# Test health endpoint
curl http://localhost:8080/health
```

- [ ] **Step 3: 停止服务**

```bash
docker-compose down
```

---

### Task 19: 客户端测试

**Files:**
- Run: `sniffly/` dashboard

- [ ] **Step 1: 启动本地 dashboard**

```bash
cd sniffly
python -m sniffly.server /path/to/logs
```

- [ ] **Step 2: 测试分享功能**

1. 打开浏览器访问 `http://localhost:8081`
2. 点击 Share 按钮
3. 添加服务器地址 `http://localhost:8080`
4. 输入用户名密码（admin / 设置的密码）
5. 点击 Share
6. 验证分享链接可以访问

---

## 总结

### 完成的组件

1. **sniffly-server** - FastAPI 服务端
   - JWT 认证
   - 分享 CRUD API
   - 画廊列表
   - 分享页面渲染
   - Docker Compose 部署

2. **sniffly 客户端改造**
   - 服务器地址管理（LocalStorage）
   - JWT 认证流程
   - 分享弹窗增强

### 部署清单

- [ ] 在内网服务器部署 sniffly-server
- [ ] 配置防火墙允许访问
- [ ] 设置安全的 admin 密码
- [ ] 分发 sniffly-iceleaf916 包给研发人员
- [ ] 提供服务器地址给研发团队
