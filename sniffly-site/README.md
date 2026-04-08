# Sniffly Site

Sniffly 的私有化部署版本，使用 Docker Compose 部署，支持内网环境。

## 目录结构

```
sniffly-site/
├── index.html              # 登录页
├── dashboard.html          # "我的分享"列表页
├── admin.html              # Admin 管理后台
├── share-template.html     # 分享仪表盘模板
├── share.html              # 由 build.py 从模板构建生成
├── build.py                # 构建脚本：打包 sniffly 静态资源
├── package.json            # Node.js 配置（便捷脚本）
│
├── static/                 # 静态资源
│   ├── css/
│   │   ├── style.css       # 主站和 Gallery 样式
│   │   └── admin.css       # Admin 管理后台样式
│   └── js/
│       ├── gallery.js      # Gallery 功能
│       ├── share-viewer.js # 渲染分享仪表盘
│       └── admin.js        # Admin 管理后台功能
│
├── api/                    # API 路由（FastAPI）
│   ├── __init__.py
│   ├── auth.py             # 认证 API
│   ├── shares.py           # 分享 CRUD API
│   └── users.py            # 用户管理 API（admin 专属）
│
├── fastapi_main.py         # FastAPI 入口，serve 所有页面和 API
├── models.py               # SQLAlchemy 数据模型
├── auth.py                 # 认证模块（OAuth2 Password Grant）
├── init.sql                # MySQL 初始化脚本
├── Dockerfile              # Docker 镜像构建
├── docker-compose.yml      # 生产环境容器编排
├── docker-compose.test.yml # 集成测试容器编排
├── pytest.ini              # pytest 配置
├── requirements.txt        # Python 依赖
└── tests/                  # 集成测试
    ├── conftest.py
    └── integration/
        ├── test_auth.py
        ├── test_shares.py
        └── test_users.py
```

## 工作原理

### 架构概览

```mermaid
flowchart TB
    subgraph Docker["Docker Compose"]
        subgraph API["API 服务"]
            A[FastAPI] --> B[API Routes]
            B --> C[SQLAlchemy ORM]
        end
        D[(MySQL 8)]
        A --> D
    end
    E[sniffly CLI] -->|HTTP API| A
    F[Browser] -->|Web UI| A
```

### 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI + uvicorn |
| 数据库 | MySQL 8 |
| ORM | SQLAlchemy |
| 认证 | OAuth2 Password Grant + Cookie Session |
| 前端 | HTML + CSS + Vanilla JS |
| 部署 | Docker Compose |

### 数据模型

#### Users 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK) | 用户 ID |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | bcrypt 密码哈希 |
| is_admin | BOOLEAN | 是否管理员 |
| created_at | DATETIME | 创建时间 |

#### Shares 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT (PK) | 分享 ID |
| uuid | VARCHAR(36) UNIQUE | 分享 UUID（URL 使用） |
| user_id | INT (FK) | 所属用户 |
| project_name | VARCHAR(255) | 项目名（用于合并判断） |
| stats | JSON | 统计数据（覆盖更新） |
| user_commands | JSON | 命令列表（合并去重） |
| is_public | BOOLEAN | 是否公开（保留字段，暂不使用） |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 最后更新时间 |

**唯一约束**: `(user_id, project_name)` 唯一确定一个分享。

#### 分享合并逻辑

当用户再次分享同名项目时：
- `stats` 字段：**全量覆盖**
- `user_commands` 字段：**按 `timestamp + content_hash` 去重合并**
- `uuid` 保持不变，访问链接一致

## API 设计

### 基础路径

`/api`

### 认证 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/auth/token` | OAuth2 Password Grant，获取 access_token | 公开 |
| POST | `/api/auth/login` | Web 登录 | 公开 |
| POST | `/api/auth/logout` | 登出 | 已登录 |
| GET | `/api/auth/me` | 获取当前用户信息 | 已登录 |

**Password Grant 流程**：
```bash
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=admin&grant_type=password"
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

### 用户 API（Admin 专属）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/users` | 列出所有用户 | admin |
| POST | `/api/users` | 创建新用户 | admin |
| GET | `/api/users/{id}/shares` | 查看某用户的分享列表 | admin |
| DELETE | `/api/users/{id}` | 删除用户 | admin |

### 页面路由

| 路径 | 说明 | 权限 |
|------|------|------|
| `/` | 登录页 | 公开 |
| `/dashboard` | "我的分享"列表页 | 已登录 |
| `/share/{uuid}` | 分享查看页 | 已登录 |
| `/admin` | 用户管理页 | admin |

## 本地开发

### 快速启动

```bash
cd sniffly-site
docker-compose up --build
# 访问 http://localhost:8000
# 默认账号: admin / admin
```

### 开发模式

```bash
# 1. 启动 MySQL
docker run -d -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=sniffly \
  -e MYSQL_USER=sniffly \
  -e MYSQL_PASSWORD=sniffly \
  -v $(pwd)/init.sql:/docker-entrypoint-initdb.d/init.sql \
  mysql:8

# 2. 安装依赖
uv venv --python 3.14
source .venv/bin/activate
pip install -r requirements.txt

# 3. 启动开发服务器
uvicorn fastapi_main:app --reload
# 访问 http://localhost:8000
```

### 运行集成测试

```bash
cd sniffly-site
uv venv --python 3.14
source .venv/bin/activate
pip install -r requirements.txt

# 启动测试环境并运行测试
docker-compose -f docker-compose.test.yml up -d --build
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down -v
```

## 部署

### Docker Compose 配置

```yaml
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
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

volumes:
  mysql_data:
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| DATABASE_URL | MySQL 连接字符串 | `mysql+pymysql://sniffly:sniffly@mysql:3306/sniffly` |
| SECRET_KEY | JWT 签名密钥 | `change-this-secret-key-in-production` |
| PORT | API 服务端口 | `8000` |

## 构建分享页面

```bash
python build.py
```

构建过程将 sniffly 静态资源打包进 `share.html`，使其可独立运行。

## 安全

- 密码使用 bcrypt 哈希存储
- JWT Token 认证，过期时间 7 天
- Admin 访问需要 `is_admin=true`
- 分享 UUID 使用 36 字符 UUID 确保唯一性

## 技术说明

- Python 开发服务器仅用于本地测试
- 生产环境使用 Docker Compose 部署
- 前端无框架依赖，纯原生 HTML/CSS/JS
