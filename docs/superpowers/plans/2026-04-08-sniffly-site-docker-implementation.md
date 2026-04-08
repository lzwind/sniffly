# Sniffly Site Docker 私有化部署实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 sniffly-site 改为 Docker Compose 私有化部署，FastAPI + MySQL，账号密码认证，支持 API 上传

**Architecture:** FastAPI 作为 API 服务和静态文件服务器，MySQL 存储用户和分享数据（JSON 字段），Docker Compose 编排所有服务

**Tech Stack:** FastAPI, SQLAlchemy, MySQL 8, Docker Compose, OAuth2 Password Grant

---

## 文件结构

```
sniffly-site/
├── requirements.txt          # NEW - Python 依赖
├── Dockerfile               # NEW - Docker 镜像
├── docker-compose.yml       # NEW - 容器编排
├── init.sql                 # NEW - MySQL 初始化
├── fastapi_main.py          # NEW - FastAPI 入口
├── models.py                # NEW - SQLAlchemy 模型
├── auth.py                  # REPLACE - 新认证模块
├── api/                     # NEW - API 路由目录
│   ├── __init__.py
│   ├── auth.py              # OAuth2 token 端点
│   ├── shares.py            # 分享 CRUD
│   └── users.py             # 用户管理（admin）
├── dashboard.html           # NEW - "我的分享"列表
├── index.html               # MODIFY - 改为登录页
├── admin.html               # MODIFY - API 驱动
├── share.html               # MODIFY - 认证逻辑变更
└── share-template.html      # KEEP
```

---

## Task 1: 项目依赖

**Files:**
- Create: `sniffly-site/requirements.txt`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi==0.109.2
uvicorn[standard]==0.27.1
sqlalchemy==2.0.25
pymysql==1.1.0
cryptography==42.0.2
python-multipart==0.0.9
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/requirements.txt
git commit -m "feat: add Python dependencies for FastAPI backend"
```

---

## Task 2: 数据模型

**Files:**
- Create: `sniffly-site/models.py`

- [ ] **Step 1: 创建 models.py**

```python
"""SQLAlchemy models for Sniffly Site."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    username: str = Column(String(50), unique=True, nullable=False)
    password_hash: str = Column(String(255), nullable=False)
    is_admin: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)

    shares: list["Share"] = relationship("Share", back_populates="user", cascade="all, delete-orphan")


class Share(Base):
    __tablename__ = "shares"
    __table_args__ = (UniqueConstraint("user_id", "project_name", name="uix_user_project"),)

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    uuid: str = Column(String(36), unique=True, nullable=False)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_name: str = Column(String(255), nullable=False)
    stats: dict = Column(JSON, nullable=False, default=dict)
    user_commands: list = Column(JSON, nullable=False, default=list)
    is_public: bool = Column(Boolean, default=False, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: "User" = relationship("User", back_populates="shares")
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/models.py
git commit -m "feat: add SQLAlchemy models for User and Share"
```

---

## Task 3: 认证模块

**Files:**
- Create: `sniffly-site/auth.py` (替换现有 Google OAuth 版本)

- [ ] **Step 1: 创建 auth.py**

```python
"""Authentication module using OAuth2 Password Grant and Cookie Session."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from models import User

# Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Load from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


class TokenData(BaseModel):
    username: str
    user_id: int
    is_admin: bool


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(lambda: get_db()),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, user_id=payload.get("user_id"), is_admin=payload.get("is_admin"))
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(db, token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_optional(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(lambda: get_db()),
) -> Optional[User]:
    try:
        return await get_current_user(request, token, db)
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


# Database dependency
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+pymysql://sniffly:sniffly@localhost:3306/sniffly"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/auth.py
git commit -m "feat: replace Google OAuth with Password Grant auth module"
```

---

## Task 4: API 路由 - 认证

**Files:**
- Create: `sniffly-site/api/__init__.py`
- Create: `sniffly-site/api/auth.py`

- [ ] **Step 1: 创建 api/__init__.py**

```python
"""API routes package."""
```

- [ ] **Step 2: 创建 api/auth.py**

```python
"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
)
from models import User


router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 Password Grant - get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/login", response_model=TokenResponse)
async def login_json(login_data: LoginRequest, db: Session = Depends(get_db)):
    """JSON login endpoint for web frontend."""
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint (client should discard token)."""
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return UserResponse(id=current_user.id, username=current_user.username, is_admin=current_user.is_admin)
```

- [ ] **Step 3: 提交**

```bash
git add sniffly-site/api/__init__.py sniffly-site/api/auth.py
git commit -m "feat: add OAuth2 token endpoint and auth API routes"
```

---

## Task 5: API 路由 - 分享

**Files:**
- Create: `sniffly-site/api/shares.py`

- [ ] **Step 1: 创建 api/shares.py**

```python
"""Shares API endpoints."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_current_user, get_db, require_admin
from models import Share, User


router = APIRouter(prefix="/api/shares", tags=["shares"])


class ShareCreateRequest(BaseModel):
    project_name: str
    stats: dict
    user_commands: list


class ShareResponse(BaseModel):
    uuid: str
    project_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShareDetailResponse(BaseModel):
    uuid: str
    project_name: str
    stats: dict
    user_commands: list
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


def merge_user_commands(existing: list, new: list) -> list:
    """Merge user_commands by timestamp + content hash deduplication."""
    seen = set()
    merged = list(existing)

    for cmd in new:
        key = (cmd.get("timestamp"), cmd.get("hash"))
        if key and key not in seen:
            seen.add(key)
            # Check if this command already exists
            exists = any(
                c.get("timestamp") == cmd.get("timestamp") and c.get("hash") == cmd.get("hash")
                for c in existing
            )
            if not exists:
                merged.append(cmd)

    # Sort by timestamp
    merged.sort(key=lambda x: x.get("timestamp", ""))
    return merged


@router.get("", response_model=list[ShareResponse])
async def list_shares(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List current user's shares."""
    shares = db.query(Share).filter(Share.user_id == current_user.id).order_by(Share.updated_at.desc()).all()
    return shares


@router.post("", response_model=ShareResponse)
async def create_or_update_share(
    share_data: ShareCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a share (merge logic)."""
    # Check if share with same user_id + project_name exists
    existing = (
        db.query(Share)
        .filter(Share.user_id == current_user.id, Share.project_name == share_data.project_name)
        .first()
    )

    if existing:
        # Update: merge stats (cover) and user_commands (dedup)
        existing.stats = share_data.stats
        existing.user_commands = merge_user_commands(existing.user_commands, share_data.user_commands)
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        new_uuid = str(uuid.uuid4())
        new_share = Share(
            uuid=new_uuid,
            user_id=current_user.id,
            project_name=share_data.project_name,
            stats=share_data.stats,
            user_commands=share_data.user_commands,
        )
        db.add(new_share)
        db.commit()
        db.refresh(new_share)
        return new_share


@router.get("/{share_uuid}", response_model=ShareDetailResponse)
async def get_share(
    share_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single share by UUID."""
    share = db.query(Share).filter(Share.uuid == share_uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    # Check permission: owner or admin
    if share.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return share


@router.delete("/{share_uuid}")
async def delete_share(
    share_uuid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a share."""
    share = db.query(Share).filter(Share.uuid == share_uuid).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share not found")

    # Check permission: owner or admin
    if share.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db.delete(share)
    db.commit()
    return {"message": "Share deleted"}
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/api/shares.py
git commit -m "feat: add shares API with merge logic"
```

---

## Task 6: API 路由 - 用户管理

**Files:**
- Create: `sniffly-site/api/users.py`

- [ ] **Step 1: 创建 api/users.py**

```python
"""Admin user management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth import get_db, require_admin
from models import Share, User
from auth import get_password_hash


router = APIRouter(prefix="/api/users", tags=["users"])


class UserCreate(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)."""
    users = db.query(User).all()
    return users


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)."""
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        is_admin=user_data.is_admin,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/{user_id}/shares")
async def get_user_shares(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Get all shares for a specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    shares = db.query(Share).filter(Share.user_id == user_id).order_by(Share.updated_at.desc()).all()
    return [
        {
            "uuid": s.uuid,
            "project_name": s.project_name,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }
        for s in shares
    ]


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-delete
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/api/users.py
git commit -m "feat: add admin user management API"
```

---

## Task 7: FastAPI 主入口

**Files:**
- Create: `sniffly-site/fastapi_main.py`

- [ ] **Step 1: 创建 fastapi_main.py**

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/fastapi_main.py
git commit -m "feat: add FastAPI main entry point with static file serving"
```

---

## Task 8: MySQL 初始化脚本

**Files:**
- Create: `sniffly-site/init.sql`

- [ ] **Step 1: 创建 init.sql**

```sql
-- Create database if not exists
CREATE DATABASE IF NOT EXISTS sniffly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE sniffly;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shares table
CREATE TABLE IF NOT EXISTS shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uuid VARCHAR(36) UNIQUE NOT NULL,
    user_id INT NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    stats JSON NOT NULL,
    user_commands JSON NOT NULL,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_share_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uix_user_project UNIQUE (user_id, project_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create default admin user (password: admin)
-- Password hash for 'admin' using bcrypt
INSERT INTO users (username, password_hash, is_admin)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.QWdKHJgLsKJLi', TRUE);
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/init.sql
git commit -m "feat: add MySQL init script with admin user"
```

---

## Task 9: Docker 配置

**Files:**
- Create: `sniffly-site/Dockerfile`
- Create: `sniffly-site/docker-compose.yml`

- [ ] **Step 1: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "fastapi_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 创建 docker-compose.yml**

```yaml
version: "3.8"

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://sniffly:sniffly@mysql:3306/sniffly
      - SECRET_KEY=change-this-secret-key-in-production
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=sniffly
      - MYSQL_USER=sniffly
      - MYSQL_PASSWORD=sniffly
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    ports:
      - "3306:3306"
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  mysql_data:
```

- [ ] **Step 3: 提交**

```bash
git add sniffly-site/Dockerfile sniffly-site/docker-compose.yml
git commit -m "feat: add Docker configuration for local deployment"
```

---

## Task 10: 前端 - 登录页 (index.html)

**Files:**
- Modify: `sniffly-site/index.html`

- [ ] **Step 1: 替换 index.html 为登录页**

保留现有 `<head>` 和样式，替换 `<body>` 内容为简单登录表单：

```html
<!-- 保留现有 head 内容，替换 body -->
<body>
    <div class="login-container">
        <h1>Sniffly</h1>
        <form id="login-form">
            <input type="text" id="username" placeholder="Username" required>
            <input type="password" id="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p id="error-message" style="color: red; display: none;"></p>
    </div>
    <script>
        const API_BASE = '/api';

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('error-message');

            try {
                const response = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                if (!response.ok) {
                    throw new Error('Invalid credentials');
                }

                const data = await response.json();
                localStorage.setItem('access_token', data.access_token);
                window.location.href = '/dashboard';
            } catch (err) {
                errorMsg.textContent = err.message;
                errorMsg.style.display = 'block';
            }
        });
    </script>
</body>
```

- [ ] **Step 2: 添加登录样式到现有 CSS 或内联**

- [ ] **Step 3: 提交**

```bash
git add sniffly-site/index.html
git commit -m "feat: convert index.html to login page"
```

---

## Task 11: 前端 - Dashboard 页面

**Files:**
- Create: `sniffly-site/dashboard.html`

- [ ] **Step 1: 创建 dashboard.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Shares - Sniffly</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header class="header">
        <div class="header-content">
            <h1>My Shares</h1>
            <button id="logout-btn">Logout</button>
        </div>
    </header>

    <main class="container">
        <div id="shares-list">
            <p>Loading...</p>
        </div>
    </main>

    <script>
        const API_BASE = '/api';
        const token = localStorage.getItem('access_token');

        if (!token) {
            window.location.href = '/';
        }

        async function loadShares() {
            try {
                const response = await fetch(`${API_BASE}/shares`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
                    throw new Error('Failed to load shares');
                }

                const shares = await response.json();
                const container = document.getElementById('shares-list');

                if (shares.length === 0) {
                    container.innerHTML = '<p>No shares yet.</p>';
                    return;
                }

                container.innerHTML = shares.map(share => `
                    <div class="share-item">
                        <h3>${share.project_name}</h3>
                        <p>UUID: ${share.uuid}</p>
                        <a href="/share/${share.uuid}">View</a>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('shares-list').innerHTML = `<p style="color:red">${err.message}</p>`;
            }
        }

        document.getElementById('logout-btn').addEventListener('click', () => {
            localStorage.removeItem('access_token');
            window.location.href = '/';
        });

        loadShares();
    </script>
</body>
</html>
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/dashboard.html
git commit -m "feat: add dashboard page for listing user's shares"
```

---

## Task 12: 前端 - Share 查看页认证

**Files:**
- Modify: `sniffly-site/share.html` (由 share-template.html 构建)

- [ ] **Step 1: 修改 share.html 认证逻辑**

在 `<head>` 中添加认证检查脚本，替换现有的 Google OAuth 相关代码：

```javascript
// 在 head 中添加，移除 Google OAuth 相关脚本
<script>
    const API_BASE = '/api';
    const SHARE_DATA_URL = '/api/shares/'; // Will be appended with UUID

    // Check auth on load
    async function init() {
        const pathParts = window.location.pathname.split('/');
        const shareUuid = pathParts[pathParts.length - 1];

        if (!shareUuid) {
            document.body.innerHTML = '<p>Invalid share URL</p>';
            return;
        }

        // For public shares, we need auth to view
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/?redirect=' + encodeURIComponent(window.location.pathname);
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/shares/${shareUuid}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('Share not found or access denied');
            }

            const data = await response.json();
            window.SHARE_DATA = data;
            // Continue with normal page load...
            if (typeof onShareDataLoaded === 'function') {
                onShareDataLoaded(data);
            }
        } catch (err) {
            document.body.innerHTML = `<p style="color:red">${err.message}</p>`;
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
</script>
```

移除 Google OAuth 相关的 `<script>` 标签和登录按钮逻辑。

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/share.html
git commit -m "feat: replace Google OAuth with token auth in share viewer"
```

---

## Task 13: 前端 - Admin 页面

**Files:**
- Modify: `sniffly-site/admin.html`

- [ ] **Step 1: 修改 admin.html**

保留原有 UI 结构，替换认证和 API 调用逻辑：

```javascript
// 替换整个 <script> 部分
<script>
    const API_BASE = '/api';
    let token = localStorage.getItem('access_token');

    async function checkAuth() {
        if (!token) {
            window.location.href = '/';
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('Unauthorized');
            }

            const user = await response.json();
            if (!user.is_admin) {
                document.body.innerHTML = '<p>Admin access required</p>';
                return;
            }

            loadUsers();
        } catch (err) {
            localStorage.removeItem('access_token');
            window.location.href = '/';
        }
    }

    async function loadUsers() {
        const response = await fetch(`${API_BASE}/users`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const users = await response.json();
        // Render users list...
    }

    checkAuth();
</script>
```

- [ ] **Step 2: 提交**

```bash
git add sniffly-site/admin.html
git commit -m "feat: convert admin.html to API-driven with token auth"
```

---

## Task 14: 清理和测试

**Files:**
- Remove: Google Analytics 相关代码（从 index.html, share.html, admin.html）
- Verify: `python build.py` 能正确构建 share.html

- [ ] **Step 1: 移除 Google Analytics**

从 index.html, admin.html 中移除 GA 脚本和 gtag 调用。

- [ ] **Step 2: 运行 build.py**

```bash
cd sniffly-site && python build.py
```

确保 share.html 正确生成。

- [ ] **Step 3: 本地测试**

```bash
# 启动 MySQL (或使用 docker)
docker run -d -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=sniffly \
  -e MYSQL_USER=sniffly \
  -e MYSQL_PASSWORD=sniffly \
  -v $(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql \
  mysql:8

# 启动 API
pip install -r requirements.txt
uvicorn fastapi_main:app --reload

# 测试登录
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=admin&grant_type=password"
```

- [ ] **Step 4: Docker Compose 测试**

```bash
docker-compose up --build
```

- [ ] **Step 5: 提交所有更改**

```bash
git add -A
git commit -m "feat: complete Docker deployment setup for sniffly-site"
```

---

## 任务依赖关系

```
Task 1 (requirements)
    ↓
Task 2 (models)
    ↓
Task 3 (auth.py)
    ↓
Task 4 (API auth) → Task 5 (API shares) → Task 6 (API users)
    ↓
Task 7 (fastapi_main)
    ↓
Task 8 (init.sql) ← Task 9 (Docker)
    ↓
Task 10 (index.html)
    ↓
Task 11 (dashboard.html)
    ↓
Task 12 (share.html)
    ↓
Task 13 (admin.html)
    ↓
Task 14 (cleanup & test)
```

---

## 验证清单

- [ ] admin/admin 默认账号可登录
- [ ] 创建普通用户
- [ ] 普通用户登录后可创建/查看自己的分享
- [ ] admin 可查看所有用户的分享
- [ ] share 页面需要登录才能访问
- [ ] `docker-compose up` 能正常启动所有服务
- [ ] API Password Grant 流程正常工作
