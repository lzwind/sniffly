# Sniffly Site Docker 私有化部署设计

## 背景

将 sniffly-site 从 Cloudflare Pages + R2 的部署方式，改为 Docker Compose 私有化部署。后端使用 FastAPI + MySQL，移除 Google OAuth 认证，改为简易账号密码体系。

## 目标

- 完全本地化部署，不依赖外部服务
- 支持内网私有部署
- 支持外部客户端（sniffly CLI）通过 API 上传数据

---

## 架构

```
┌──────────────────────────────────────────────────────────┐
│                    Docker Compose                         │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │  FastAPI    │  │    MySQL    │  │    nginx     │     │
│  │  (uvicorn)  │  │  (JSON存储)  │  │  (生产静态)   │     │
│  └─────────────┘  └─────────────┘  └──────────────┘     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 开发 vs 生产

| 环境 | 服务 | 说明 |
|------|------|------|
| 开发 | `uvicorn fastapi_main:app` | FastAPI 直接 serve 静态文件 |
| 生产 | nginx 反向代理 + uvicorn | nginx 处理静态文件 + HTTPS（可选） |

---

## 数据模型

### Users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK, AUTO_INCREMENT) | 用户 ID |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | bcrypt 密码哈希 |
| is_admin | BOOLEAN DEFAULT FALSE | 是否管理员 |
| created_at | DATETIME | 创建时间 |

### Shares 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK, AUTO_INCREMENT) | 分享 ID |
| uuid | VARCHAR(36) UNIQUE | 分享 UUID（URL 使用） |
| user_id | INT (FK → users.id) | 所属用户 |
| project_name | VARCHAR(255) | 项目名（用于合并判断） |
| stats | JSON | 统计数据（覆盖更新） |
| user_commands | JSON | 命令列表（合并去重） |
| is_public | BOOLEAN DEFAULT FALSE | 是否公开（保留字段，暂不使用） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最后更新时间 |

**唯一约束**: `(user_id, project_name)` 唯一确定一个分享。

### 分享合并逻辑

当用户再次分享同名项目时：
- `stats` 字段：**全量覆盖**
- `user_commands` 字段：**按 `timestamp + content_hash` 去重合并**
- `uuid` 保持不变，访问链接一致

---

## API 设计

### 基础路径

`/api`

### 认证 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/token` | OAuth2 Password Grant，获取 access_token | 公开 |
| POST | `/api/auth/login` | Web 登录（Cookie Session） | 公开 |
| POST | `/api/auth/logout` | 登出 | 已登录 |
| GET | `/api/auth/me` | 获取当前用户信息 | 已登录 |

**Password Grant 流程**：
```
POST /api/auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin&grant_type=password
```
返回：
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### 分享 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/shares` | 列出当前用户的分享列表 | 已登录 |
| POST | `/api/shares` | 创建/更新分享（合并逻辑） | 已登录 |
| GET | `/api/shares/{uuid}` | 获取单个分享详情 | 已登录 |
| DELETE | `/api/shares/{uuid}` | 删除分享 | 已登录（本人或 admin） |

**POST /api/shares 请求体**：
```json
{
  "project_name": "my-project",
  "stats": { "total_commands": 100, ... },
  "user_commands": [
    { "timestamp": "2024-01-01T00:00:00Z", "content": "ls -la", "hash": "abc123" }
  ]
}
```

**响应**：
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "project_name": "my-project",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

### 用户 API（Admin 专属）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/users` | 列出所有用户 | admin |
| POST | `/api/users` | 创建新用户 | admin |
| GET | `/api/users/{id}/shares` | 查看某用户的分享列表 | admin |
| DELETE | `/api/users/{id}` | 删除用户 | admin |

---

## 页面路由

| 路径 | 说明 | 权限 |
|------|------|------|
| `/` | 登录页 | 公开 |
| `/dashboard` | "我的分享"列表页 | 已登录 |
| `/share/{uuid}` | 分享查看页 | 已登录 |
| `/admin` | 用户管理页 | admin |

---

## 前端改造

### 现有文件改动

| 文件 | 改动 |
|------|------|
| `index.html` | 改为登录页（移除 Gallery 内容） |
| `share.html` | **保留原有布局设计**，仅改动认证相关部分 |
| `admin.html` | 保留，改为 API 驱动 + 账号密码认证 |
| `share-template.html` | 保留，构建 share.html 用 |

**share.html 布局原则**：原有页面样式、组件布局保持不变，仅替换认证逻辑（Google OAuth → 账号密码）。

### 新增文件

| 文件 | 说明 |
|------|------|
| `dashboard.html` | "我的分享"列表页 |
| `fastapi_main.py` | FastAPI 入口，serve 所有页面和 API |

### 移除内容

- Google Analytics 相关代码
- Google OAuth 相关代码和依赖

---

## 认证机制

### Web 前端
- 使用 Cookie Session
- 登录后 Session 存储在 MySQL 中

### API 客户端（sniffly CLI）
- OAuth2 Password Grant
- 客户端存储 access_token，调用 API 时带 `Authorization: Bearer {token}`

---

## 初始化

1. Docker Compose 首次启动时，MySQL 执行初始化脚本
2. 创建默认 admin 账号：`admin` / `admin`
3. admin 登录后可创建其他普通用户

---

## Docker Compose 结构

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://sniffly:sniffly@mysql:3306/sniffly
    depends_on:
      - mysql

  mysql:
    image: mysql:8
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=sniffly
      - MYSQL_USER=sniffly
      - MYSQL_PASSWORD=sniffly
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  mysql_data:
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI + uvicorn |
| 数据库 | MySQL 8 |
| ORM | SQLAlchemy |
| 认证 | OAuth2 Password Grant + Cookie Session |
| 前端 | HTML + CSS + Vanilla JS（现有代码复用） |
| 部署 | Docker Compose |

---

## 结论

- **nginx**：生产环境使用，开发阶段用 uvicorn 直接服务静态文件
- **API 认证**：Password Grant（OAuth2），已确认

---

## 实现状态

**状态：✅ 已完成实现**

所有计划中的功能已完成实现，代码已提交到 git 仓库。

### 相关提交

| 提交 | 说明 |
|------|------|
| a401826 | feat: add Python dependencies for FastAPI backend |
| 4920f08 | feat: add SQLAlchemy models for User and Share |
| eacc83a | feat: replace Google OAuth with Password Grant auth module |
| 235d846 | feat: add OAuth2 token endpoint and auth API routes |
| 382f691 | feat: add shares API with merge logic |
| c1c6239 | feat: add FastAPI main entry point with static file serving |
| 7b8ef7b | feat: add Docker configuration for local deployment |
| 2ed7d61 | feat(site): convert index.html to login page |
| 139ddc4 | feat: add dashboard page for listing user's shares |
| 5baa8e8 | feat: complete Docker deployment setup for sniffly-site |

### 快速启动

```bash
cd sniffly-site
docker-compose up --build
# 访问 http://localhost:8000
# 默认账号: admin / admin
```
