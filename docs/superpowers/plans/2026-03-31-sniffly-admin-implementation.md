# Sniffly Server 管理后台和首页实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 sniffly-server 增加管理后台和首页功能

**Architecture:** 扩展现有 FastAPI + Jinja2 技术栈，新增管理 API 路由和前端模板，保持与现有代码风格一致

**Tech Stack:** Python 3.11+, FastAPI, MongoDB, Jinja2, 原生 HTML/CSS/JS

---

## 文件结构

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `sniffly-server/app/auth.py` | 添加 `require_admin` 装饰器 |
| `sniffly-server/app/models.py` | 添加管理相关 Pydantic 模型 |
| `sniffly-server/app/main.py` | 添加首页、登录页、管理后台路由 |
| `sniffly-server/app/routers/__init__.py` | 导出 admin router |

### 新建文件

| 文件 | 说明 |
|------|------|
| `sniffly-server/app/routers/admin.py` | 管理后台 API 路由 |
| `sniffly-server/templates/index.html` | 首页模板 |
| `sniffly-server/templates/login.html` | 登录页模板 |
| `sniffly-server/templates/admin/layout.html` | 管理后台布局模板 |
| `sniffly-server/templates/admin/index.html` | 管理后台首页 |
| `sniffly-server/templates/admin/users.html` | 用户管理页面 |
| `sniffly-server/templates/admin/shares.html` | 分享管理页面 |
| `sniffly-server/static/css/admin.css` | 管理后台样式 |
| `sniffly-server/static/js/admin.js` | 管理后台 JavaScript |

---

## Task 1: 扩展认证模块

**Files:**
- Modify: `sniffly-server/app/auth.py`

- [ ] **Step 1: 添加 require_admin 装饰器到 auth.py**

在文件末尾添加以下代码：

```python
from fastapi import HTTPException, status

async def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """检查当前用户是否为管理员"""
    from app.config import settings
    if current_user != settings.admin_username:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/auth.py
git commit -m "feat: add require_admin decorator for admin-only endpoints"
```

---

## Task 2: 扩展数据模型

**Files:**
- Modify: `sniffly-server/app/models.py`

- [ ] **Step 1: 在 models.py 末尾添加管理相关模型**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/app/models.py
git commit -m "feat: add admin-related Pydantic models"
```

---

## Task 3: 创建管理 API 路由

**Files:**
- Create: `sniffly-server/app/routers/admin.py`

- [ ] **Step 1: 创建 admin.py**

```python
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
```

- [ ] **Step 2: 更新 routers/__init__.py 导出 admin router**

在 `sniffly-server/app/routers/__init__.py` 中添加：

```python
from app.routers.admin import router as admin_router

__all__ = ["auth_router", "shares_router", "gallery_router", "admin_router"]
```

- [ ] **Step 3: Commit**

```bash
git add sniffly-server/app/routers/admin.py sniffly-server/app/routers/__init__.py
git commit -m "feat: add admin API routes for user and share management"
```

---

## Task 4: 创建管理后台模板

**Files:**
- Create: `sniffly-server/templates/admin/layout.html`
- Create: `sniffly-server/templates/admin/index.html`
- Create: `sniffly-server/templates/admin/users.html`
- Create: `sniffly-server/templates/admin/shares.html`

- [ ] **Step 1: 创建 templates/admin 目录和 layout.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin Dashboard{% endblock %} - Sniffly Server</title>
    <link rel="stylesheet" href="/static/css/admin.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
    <div class="admin-layout">
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>Admin Dashboard</h1>
            </div>
            <nav class="sidebar-nav">
                <a href="/admin" class="nav-item {% if active_page == 'overview' %}active{% endif %}">
                    <span class="nav-icon">📊</span>
                    <span>概览</span>
                </a>
                <a href="/admin/users" class="nav-item {% if active_page == 'users' %}active{% endif %}">
                    <span class="nav-icon">👥</span>
                    <span>用户管理</span>
                </a>
                <a href="/admin/shares" class="nav-item {% if active_page == 'shares' %}active{% endif %}">
                    <span class="nav-icon">📁</span>
                    <span>分享管理</span>
                </a>
            </nav>
            <div class="sidebar-footer">
                <a href="/" class="nav-item">
                    <span class="nav-icon">🏠</span>
                    <span>返回首页</span>
                </a>
                <a href="/auth/logout" class="nav-item">
                    <span class="nav-icon">🚪</span>
                    <span>退出</span>
                </a>
            </div>
        </aside>
        <main class="main-content">
            <header class="content-header">
                <h2>{% block page_title %}{% endblock %}</h2>
            </header>
            <div class="content-body">
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>

    <!-- Modal Template -->
    <div id="modal-overlay" class="modal-overlay" style="display: none;">
        <div class="modal">
            <div class="modal-header">
                <h3 id="modal-title">Modal</h3>
                <button type="button" class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modal-body">
            </div>
        </div>
    </div>

    <script src="/static/js/admin.js"></script>
</body>
</html>
```

- [ ] **Step 2: 创建 admin/index.html（概览页）**

```html
{% extends "admin/layout.html" %}

{% block title %}概览{% endblock %}
{% block page_title %}系统概览{% endblock %}

{% block content %}
<div class="stats-grid">
    <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
            <span class="stat-value">{{ stats.total_users }}</span>
            <span class="stat-label">总用户数</span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">✅</div>
        <div class="stat-content">
            <span class="stat-value">{{ stats.active_users }}</span>
            <span class="stat-label">活跃用户</span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">📁</div>
        <div class="stat-content">
            <span class="stat-value">{{ stats.total_shares }}</span>
            <span class="stat-label">总分享数</span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon">🌐</div>
        <div class="stat-content">
            <span class="stat-value">{{ stats.public_shares }}</span>
            <span class="stat-label">公开分享</span>
        </div>
    </div>
</div>

<section class="section">
    <h3>最近分享</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>项目名称</th>
                <th>创建者</th>
                <th>创建时间</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
            {% for share in stats.recent_shares %}
            <tr>
                <td>{{ share.project_name }}</td>
                <td>{{ share.created_by }}</td>
                <td>{{ share.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>
                    {% if share.is_public %}
                    <span class="badge badge-success">公开</span>
                    {% else %}
                    <span class="badge badge-secondary">私有</span>
                    {% endif %}
                </td>
                <td>
                    <a href="/share/{{ share.id }}" class="btn btn-sm btn-link" target="_blank">查看</a>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="5" class="empty-state">暂无分享</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</section>
{% endblock %}
```

- [ ] **Step 3: 创建 admin/users.html（用户管理页）**

```html
{% extends "admin/layout.html" %}

{% block title %}用户管理{% endblock %}
{% block page_title %}用户管理{% endblock %}

{% block content %}
<div class="page-actions">
    <button type="button" class="btn btn-primary" onclick="showCreateUserModal()">
        + 创建用户
    </button>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th>用户名</th>
            <th>创建时间</th>
            <th>状态</th>
            <th>分享数</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody id="users-tbody">
        <tr>
            <td colspan="5" class="loading-state">加载中...</td>
        </tr>
    </tbody>
</table>

<div class="pagination" id="users-pagination"></div>
{% endblock %}
```

- [ ] **Step 4: 创建 admin/shares.html（分享管理页）**

```html
{% extends "admin/layout.html" %}

{% block title %}分享管理{% endblock %}
{% block page_title %}分享管理{% endblock %}

{% block content %}
<table class="data-table">
    <thead>
        <tr>
            <th>项目名称</th>
            <th>创建者</th>
            <th>创建时间</th>
            <th>状态</th>
            <th>操作</th>
        </tr>
    </thead>
    <tbody id="shares-tbody">
        <tr>
            <td colspan="5" class="loading-state">加载中...</td>
        </tr>
    </tbody>
</table>

<div class="pagination" id="shares-pagination"></div>
{% endblock %}
```

- [ ] **Step 5: Commit**

```bash
git add sniffly-server/templates/admin/
git commit -m "feat: add admin dashboard templates"
```

---

## Task 5: 创建首页和登录页模板

**Files:**
- Create: `sniffly-server/templates/index.html`
- Create: `sniffly-server/templates/login.html`

- [ ] **Step 1: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sniffly Server - Internal Claude Code Analytics</title>
    <link rel="stylesheet" href="/static/css/share.css">
</head>
<body>
    <div class="container">
        <header class="header">
            <div class="header-content">
                <div class="logo">
                    <h1>Sniffly Server</h1>
                </div>
                <nav class="nav">
                    {% if current_user %}
                    <a href="/admin" class="nav-link">管理后台</a>
                    <a href="/auth/logout" class="nav-link">退出</a>
                    {% else %}
                    <a href="/login" class="nav-link nav-link-primary">Login</a>
                    {% endif %}
                    <a href="https://github.com/chiphuyen/sniffly" class="nav-link" target="_blank">GitHub</a>
                </nav>
            </div>
        </header>

        <main class="main">
            <section class="hero">
                <h2>Internal Claude Code Analytics</h2>
                <p>Track and share your Claude Code usage insights</p>
            </section>

            <section class="gallery">
                <h3>Public Dashboard Gallery</h3>
                {% if projects %}
                <div class="gallery-grid">
                    {% for project in projects %}
                    <a href="/share/{{ project.id }}" class="gallery-card">
                        <div class="card-content">
                            <h4>{{ project.project_name or 'Untitled' }}</h4>
                            <p class="card-meta">
                                by {{ project.created_by }} &middot;
                                {{ project.created_at.strftime('%Y-%m-%d') }}
                            </p>
                            <div class="card-stats">
                                <span>{{ project.stats.total_commands|default(0) }} commands</span>
                                <span>{{ project.stats.total_tokens|default(0)|int }} tokens</span>
                            </div>
                        </div>
                    </a>
                    {% endfor %}
                </div>
                {% else %}
                <p class="empty-state">No public shares yet.</p>
                {% endif %}
            </section>
        </main>

        <footer class="footer">
            <p>&copy; 2026 Sniffly Server</p>
        </footer>
    </div>
</body>
</html>
```

- [ ] **Step 2: 创建 login.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In - Sniffly Server</title>
    <link rel="stylesheet" href="/static/css/share.css">
</head>
<body>
    <div class="login-container">
        <div class="login-box">
            <div class="login-header">
                <h1>Sniffly Server</h1>
            </div>

            <form method="post" action="/login" class="login-form">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required autofocus>
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>

                {% if error %}
                <div class="error-message">{{ error }}</div>
                {% endif %}

                <button type="submit" class="btn btn-primary btn-block">Sign In</button>
            </form>
        </div>

        <div class="login-footer">
            <a href="/">&larr; Back to Home</a>
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add sniffly-server/templates/index.html sniffly-server/templates/login.html
git commit -m "feat: add index and login page templates"
```

---

## Task 6: 创建管理后台静态资源

**Files:**
- Create: `sniffly-server/static/css/admin.css`
- Create: `sniffly-server/static/js/admin.js`

- [ ] **Step 1: 创建 admin.css**

```css
/* Admin Dashboard Styles */

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

/* Layout */
.admin-layout {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: 240px;
    background: #1a1a2e;
    color: white;
    display: flex;
    flex-direction: column;
}

.sidebar-header {
    padding: 1.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-header h1 {
    font-size: 1.25rem;
    font-weight: 600;
}

.sidebar-nav {
    flex: 1;
    padding: 1rem 0;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.5rem;
    color: rgba(255,255,255,0.7);
    text-decoration: none;
    transition: all 0.2s;
}

.nav-item:hover, .nav-item.active {
    background: rgba(255,255,255,0.1);
    color: white;
}

.nav-item.active {
    border-left: 3px solid #667eea;
}

.nav-icon {
    font-size: 1.25rem;
}

.sidebar-footer {
    border-top: 1px solid rgba(255,255,255,0.1);
    padding: 1rem 0;
}

.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.content-header {
    background: white;
    padding: 1.5rem 2rem;
    border-bottom: 1px solid #e0e0e0;
}

.content-header h2 {
    font-size: 1.5rem;
    font-weight: 600;
}

.content-body {
    flex: 1;
    padding: 2rem;
}

/* Stats Grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 1rem;
}

.stat-icon {
    font-size: 2rem;
}

.stat-content {
    display: flex;
    flex-direction: column;
}

.stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: #667eea;
}

.stat-label {
    color: #666;
    font-size: 0.9rem;
}

/* Section */
.section {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.section h3 {
    margin-bottom: 1rem;
    font-size: 1.1rem;
}

/* Data Table */
.data-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.data-table th,
.data-table td {
    padding: 1rem;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
}

.data-table th {
    background: #f8f9fa;
    font-weight: 600;
    font-size: 0.9rem;
    color: #666;
}

.data-table tbody tr:hover {
    background: #f8f9fa;
}

.data-table .empty-state,
.data-table .loading-state {
    text-align: center;
    color: #999;
    padding: 2rem;
}

/* Buttons */
.btn {
    display: inline-block;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    text-decoration: none;
    transition: all 0.2s;
}

.btn-primary {
    background: #667eea;
    color: white;
}

.btn-primary:hover {
    background: #5a67d8;
}

.btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.85rem;
}

.btn-link {
    color: #667eea;
    background: none;
}

.btn-link:hover {
    text-decoration: underline;
}

.btn-danger {
    color: #e53e3e;
    background: none;
}

.btn-danger:hover {
    background: #fff5f5;
}

/* Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-success {
    background: #c6f6d5;
    color: #276749;
}

.badge-secondary {
    background: #e2e8f0;
    color: #4a5568;
}

/* Modal */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal {
    background: white;
    border-radius: 8px;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e0e0e0;
}

.modal-header h3 {
    margin: 0;
    font-size: 1.1rem;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #999;
}

.modal-close:hover {
    color: #333;
}

.modal-body {
    padding: 1.5rem;
}

/* Form */
.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

.form-group input[type="text"],
.form-group input[type="password"] {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

.form-group input:focus {
    outline: none;
    border-color: #667eea;
}

.checkbox-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.checkbox-group input {
    width: 1rem;
    height: 1rem;
}

.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
    margin-top: 1.5rem;
}

/* Pagination */
.pagination {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 1.5rem;
}

.pagination button {
    padding: 0.5rem 1rem;
    border: 1px solid #ddd;
    background: white;
    border-radius: 4px;
    cursor: pointer;
}

.pagination button:hover {
    background: #f5f5f5;
}

.pagination button.active {
    background: #667eea;
    color: white;
    border-color: #667eea;
}

.pagination button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

/* Page Actions */
.page-actions {
    margin-bottom: 1.5rem;
}
```

- [ ] **Step 2: 创建 admin.js**

```javascript
// Admin Dashboard JavaScript

const API_BASE = '/api/admin';
let currentUser = null;
let currentPage = { users: 1, shares: 1 };

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Check if on users page
    if (document.getElementById('users-tbody')) {
        loadUsers(1);
    }
    // Check if on shares page
    if (document.getElementById('shares-tbody')) {
        loadShares(1);
    }
});

// Modal functions
function showModal(title, content) {
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = content;
    document.getElementById('modal-overlay').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal-overlay').style.display = 'none';
}

// Close modal on overlay click
document.getElementById('modal-overlay')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closeModal();
    }
});

// Load users
async function loadUsers(page = 1) {
    currentPage.users = page;
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-state">加载中...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/users?page=${page}&limit=20`);
        if (!response.ok) throw new Error('Failed to load users');

        const data = await response.json();
        renderUsers(data);
        renderPagination('users-pagination', data.total, data.page, data.limit, currentPage.users);
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">加载失败</td></tr>';
    }
}

function renderUsers(data) {
    const tbody = document.getElementById('users-tbody');

    if (data.users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无用户</td></tr>';
        return;
    }

    tbody.innerHTML = data.users.map(user => `
        <tr>
            <td>${escapeHtml(user.username)}</td>
            <td>${new Date(user.created_at).toLocaleString('zh-CN')}</td>
            <td>
                ${user.is_active
                    ? '<span class="badge badge-success">启用</span>'
                    : '<span class="badge badge-secondary">禁用</span>'}
            </td>
            <td>${user.share_count}</td>
            <td>
                <button class="btn btn-sm btn-link" onclick="showEditUserModal('${escapeHtml(user.username)}', ${user.is_active})">编辑</button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser('${escapeHtml(user.username)}')">删除</button>
            </td>
        </tr>
    `).join('');
}

// Create user modal
function showCreateUserModal() {
    const content = `
        <form id="create-user-form">
            <div class="form-group">
                <label for="new-username">用户名</label>
                <input type="text" id="new-username" name="username" required minlength="1" maxlength="50">
            </div>
            <div class="form-group">
                <label for="new-password">密码</label>
                <input type="password" id="new-password" name="password" required minlength="8">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="new-is-active" name="is_active" checked>
                <label for="new-is-active">启用账号</label>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">创建</button>
            </div>
        </form>
    `;

    showModal('创建用户', content);

    document.getElementById('create-user-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {
            username: formData.get('username'),
            password: formData.get('password'),
            is_active: formData.get('is_active') === 'on'
        };

        try {
            const response = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '创建失败');
            }

            closeModal();
            loadUsers(currentPage.users);
        } catch (error) {
            alert('错误: ' + error.message);
        }
    });
}

// Edit user modal
async function showEditUserModal(username, isActive) {
    const content = `
        <form id="edit-user-form">
            <div class="form-group">
                <label>用户名</label>
                <p>${escapeHtml(username)}</p>
            </div>
            <div class="form-group">
                <label for="edit-password">新密码 (留空则不修改)</label>
                <input type="password" id="edit-password" name="password" minlength="8">
            </div>
            <div class="form-group checkbox-group">
                <input type="checkbox" id="edit-is-active" name="is_active" ${isActive ? 'checked' : ''}>
                <label for="edit-is-active">启用账号</label>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn" onclick="closeModal()">取消</button>
                <button type="submit" class="btn btn-primary">保存</button>
            </div>
        </form>
    `;

    showModal('编辑用户', content);

    document.getElementById('edit-user-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = {};

        const password = formData.get('password');
        if (password) data.password = password;

        const isActive = formData.get('is_active') === 'on';
        data.is_active = isActive;

        try {
            const response = await fetch(`${API_BASE}/users/${username}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '更新失败');
            }

            closeModal();
            loadUsers(currentPage.users);
        } catch (error) {
            alert('错误: ' + error.message);
        }
    });
}

// Delete user
async function deleteUser(username) {
    if (!confirm(`确定要删除用户 "${username}" 吗？`)) return;

    try {
        const response = await fetch(`${API_BASE}/users/${username}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }

        loadUsers(currentPage.users);
    } catch (error) {
        alert('错误: ' + error.message);
    }
}

// Load shares
async function loadShares(page = 1) {
    currentPage.shares = page;
    const tbody = document.getElementById('shares-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading-state">加载中...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/shares?page=${page}&limit=20`);
        if (!response.ok) throw new Error('Failed to load shares');

        const data = await response.json();
        renderShares(data);
        renderPagination('shares-pagination', data.total, data.page, data.limit, currentPage.shares);
    } catch (error) {
        console.error('Error loading shares:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">加载失败</td></tr>';
    }
}

function renderShares(data) {
    const tbody = document.getElementById('shares-tbody');

    if (data.shares.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无分享</td></tr>';
        return;
    }

    tbody.innerHTML = data.shares.map(share => `
        <tr>
            <td>${escapeHtml(share.project_name)}</td>
            <td>${escapeHtml(share.created_by)}</td>
            <td>${new Date(share.created_at).toLocaleString('zh-CN')}</td>
            <td>
                ${share.is_public
                    ? '<span class="badge badge-success">公开</span>'
                    : '<span class="badge badge-secondary">私有</span>'}
            </td>
            <td>
                <a href="/share/${share.id}" class="btn btn-sm btn-link" target="_blank">查看</a>
                <button class="btn btn-sm btn-danger" onclick="deleteShare('${share.id}')">删除</button>
            </td>
        </tr>
    `).join('');
}

// Delete share
async function deleteShare(shareId) {
    if (!confirm('确定要删除此分享吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/shares/${shareId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '删除失败');
        }

        loadShares(currentPage.shares);
    } catch (error) {
        alert('错误: ' + error.message);
    }
}

// Pagination
function renderPagination(containerId, total, page, limit, currentPage) {
    const container = document.getElementById(containerId);
    const totalPages = Math.ceil(total / limit);

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = `
        <button ${page === 1 ? 'disabled' : ''} onclick="${containerId.replace('-pagination', '')}Page(${page - 1})">
            上一页
        </button>
    `;

    for (let i = 1; i <= totalPages; i++) {
        if (i === page || (i <= 3) || (i > totalPages - 3) || (Math.abs(i - page) <= 1)) {
            html += `<button class="${i === page ? 'active' : ''}" onclick="${containerId.replace('-pagination', '')}Page(${i})">${i}</button>`;
        } else if (i === 4 || i === totalPages - 3) {
            html += '<button disabled>...</button>';
        }
    }

    html += `
        <button ${page === totalPages ? 'disabled' : ''} onclick="${containerId.replace('-pagination', '')}Page(${page + 1})">
            下一页
        </button>
    `;

    container.innerHTML = html;
}

// Pagination helpers
function usersPage(page) {
    loadUsers(page);
}

function sharesPage(page) {
    loadShares(page);
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

- [ ] **Step 3: Commit**

```bash
git add sniffly-server/static/css/admin.css sniffly-server/static/js/admin.js
git commit -m "feat: add admin dashboard styles and JavaScript"
```

---

## Task 7: 更新主应用添加路由

**Files:**
- Modify: `sniffly-server/app/main.py`

- [ ] **Step 1: 更新 main.py 添加新路由**

将 `app/main.py` 替换为以下内容：

```python
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
from app.routers.auth import router as auth_router


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
```

- [ ] **Step 2: 创建 login_success.html**

创建 `sniffly-server/templates/login_success.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Success - Sniffly Server</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }
        .success-box {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #667eea; margin-bottom: 1rem; }
        p { color: #666; margin-bottom: 1.5rem; }
        a {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        a:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="success-box">
        <h1>Login Successful</h1>
        <p>Welcome, {{ username }}!</p>
        <a href="/admin">Go to Admin Dashboard</a>
    </div>
    <script>
        // Store token in localStorage
        localStorage.setItem('sniffly_token', '{{ token }}');
        localStorage.setItem('sniffly_username', '{{ username }}');

        // Redirect after a short delay
        setTimeout(function() {
            window.location.href = '/admin';
        }, 1000);
    </script>
</body>
</html>
```

- [ ] **Step 3: 创建 error.html**

创建 `sniffly-server/templates/error.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error - Sniffly Server</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            background: #f5f5f5;
        }
        .error-box {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 400px;
        }
        h1 { color: #e53e3e; margin-bottom: 1rem; }
        p { color: #666; margin-bottom: 1.5rem; }
        a {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        a:hover { background: #5a67d8; }
    </style>
</head>
<body>
    <div class="error-box">
        <h1>Error</h1>
        <p>{{ error }}</p>
        <a href="/">Go to Home</a>
    </div>
</body>
</html>
```

- [ ] **Step 4: 更新 shares router 导入名称**

确保 `sniffly-server/app/routers/__init__.py` 正确导出：

```python
from app.routers.auth import router as auth_router
from app.routers.shares import router as shares_router
from app.routers.gallery import router as gallery_router
from app.routers.admin import router as admin_router

__all__ = ["auth_router", "shares_router", "gallery_router", "admin_router"]
```

同时检查并更新 `sniffly-server/app/routers/shares.py` 中的 router 定义，添加 `tags` 参数：

```python
router = APIRouter(prefix="/api/shares", tags=["shares"])
```

- [ ] **Step 5: Commit**

```bash
git add sniffly-server/app/main.py
git add sniffly-server/templates/login_success.html
git add sniffly-server/templates/error.html
git add sniffly-server/app/routers/__init__.py
git commit -m "feat: add index, login, and admin routes to main app"
```

---

## Task 8: 更新 share.css 添加首页和登录页样式

**Files:**
- Modify: `sniffly-server/static/css/share.css`

- [ ] **Step 1: 在 share.css 末尾添加首页和登录页样式**

```css
/* Index Page Styles */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0;
}

.header {
    background: white;
    border-bottom: 1px solid #e0e0e0;
    padding: 1rem 2rem;
}

.header-content {
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.logo h1 {
    font-size: 1.5rem;
    color: #667eea;
}

.nav {
    display: flex;
    gap: 1.5rem;
    align-items: center;
}

.nav-link {
    color: #666;
    text-decoration: none;
    font-size: 0.9rem;
}

.nav-link:hover {
    color: #333;
}

.nav-link-primary {
    background: #667eea;
    color: white;
    padding: 0.5rem 1rem;
    border-radius: 4px;
}

.nav-link-primary:hover {
    background: #5a67d8;
    color: white;
}

.main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 3rem 2rem;
}

.hero {
    text-align: center;
    margin-bottom: 3rem;
}

.hero h2 {
    font-size: 2.5rem;
    margin-bottom: 1rem;
    color: #1a1a2e;
}

.hero p {
    font-size: 1.2rem;
    color: #666;
}

.gallery {
    margin-top: 2rem;
}

.gallery h3 {
    font-size: 1.5rem;
    margin-bottom: 1.5rem;
    color: #1a1a2e;
}

.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
}

.gallery-card {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-decoration: none;
    color: inherit;
    transition: all 0.2s;
}

.gallery-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transform: translateY(-2px);
}

.gallery-card .card-content {
    padding: 1.5rem;
}

.gallery-card h4 {
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
    color: #1a1a2e;
}

.card-meta {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 1rem;
}

.card-stats {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
    color: #999;
}

.footer {
    text-align: center;
    padding: 2rem;
    color: #999;
    font-size: 0.9rem;
    border-top: 1px solid #e0e0e0;
    margin-top: 3rem;
}

/* Login Page Styles */
.login-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
}

.login-box {
    background: white;
    padding: 2.5rem;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    width: 100%;
    max-width: 400px;
}

.login-header {
    text-align: center;
    margin-bottom: 2rem;
}

.login-header h1 {
    color: #667eea;
    font-size: 1.75rem;
}

.login-form .form-group {
    margin-bottom: 1.25rem;
}

.login-form label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #333;
}

.login-form input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
    transition: border-color 0.2s;
}

.login-form input:focus {
    outline: none;
    border-color: #667eea;
}

.btn-block {
    width: 100%;
    padding: 0.875rem;
    font-size: 1rem;
}

.error-message {
    background: #fed7d7;
    color: #c53030;
    padding: 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
}

.login-footer {
    margin-top: 1.5rem;
    text-align: center;
}

.login-footer a {
    color: white;
    text-decoration: none;
    font-size: 0.9rem;
}

.login-footer a:hover {
    text-decoration: underline;
}

.empty-state {
    text-align: center;
    color: #999;
    padding: 3rem 1rem;
}
```

- [ ] **Step 2: Commit**

```bash
git add sniffly-server/static/css/share.css
git commit -m "feat: add index and login page styles to share.css"
```

---

## Task 9: 测试验证

- [ ] **Step 1: 启动 MongoDB 和 Redis**

```bash
cd sniffly-server
docker run -d -p 27017:27017 --name sniffly-mongo mongo:7
docker run -d -p 6379:6379 --name sniffly-redis redis:7-alpine
```

- [ ] **Step 2: 安装依赖并启动服务**

```bash
cd sniffly-server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

- [ ] **Step 3: 测试首页**

访问 `http://localhost:8080/` 验证首页正常显示

- [ ] **Step 4: 测试登录页**

访问 `http://localhost:8080/login` 验证登录页正常显示

- [ ] **Step 5: 测试登录**

使用 admin/admin 登录，验证成功跳转管理后台

- [ ] **Step 6: 测试管理后台**

- 访问 `/admin` 概览页面
- 访问 `/admin/users` 用户管理页面
- 测试创建用户、编辑用户、删除用户
- 访问 `/admin/shares` 分享管理页面

---

## Task 10: 清理和提交

- [ ] **Step 1: 停止 Docker 容器**

```bash
docker stop sniffly-mongo sniffly-redis
docker rm sniffly-mongo sniffly-redis
```

- [ ] **Step 2: 最终提交**

```bash
git add -A
git status
```

---

## 总结

### 新增文件

| 文件 | 说明 |
|------|------|
| `app/routers/admin.py` | 管理后台 API 路由 |
| `templates/index.html` | 首页 |
| `templates/login.html` | 登录页 |
| `templates/login_success.html` | 登录成功页 |
| `templates/error.html` | 错误页 |
| `templates/admin/layout.html` | 管理后台布局 |
| `templates/admin/index.html` | 管理后台概览 |
| `templates/admin/users.html` | 用户管理页 |
| `templates/admin/shares.html` | 分享管理页 |
| `static/css/admin.css` | 管理后台样式 |
| `static/js/admin.js` | 管理后台 JavaScript |

### 修改文件

| 文件 | 说明 |
|------|------|
| `app/auth.py` | 添加 require_admin 装饰器 |
| `app/models.py` | 添加管理相关模型 |
| `app/main.py` | 添加公开路由和管理后台路由 |
| `app/routers/__init__.py` | 导出 admin router |
| `static/css/share.css` | 添加首页和登录页样式 |

### 部署清单

- [ ] 在内网服务器部署更新后的 sniffly-server
- [ ] 更新 docker-compose.yml
- [ ] 配置环境变量 ADMIN_PASSWORD
