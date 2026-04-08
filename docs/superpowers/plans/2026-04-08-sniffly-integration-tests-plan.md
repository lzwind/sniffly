# Sniffly Site 集成测试开发计划

## 目标

为 sniffly-site 创建 Docker Compose + pytest 集成测试套件，验证服务启动后 API 功能正常。

## 测试架构

```
┌─────────────────────────────────────────────────────────────┐
│                  docker-compose.test.yml                     │
│                                                             │
│  ┌─────────────┐              ┌─────────────┐             │
│  │  pytest     │  ──HTTP───   │  FastAPI    │             │
│  │  (test)     │              │  (api)      │             │
│  └─────────────┘              └─────────────┘             │
│         │                            │                      │
│         │                            │                      │
│         │              ┌─────────────┴─────────────┐       │
│         │              │        MySQL              │       │
│         │              │   (真实数据库)             │       │
│         │              └───────────────────────────┘       │
└─────────┴─────────────────────────────────────────────────┘
```

### 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 测试数据库 | 真实 MySQL | 确保测试环境与生产一致 |
| 服务启动等待 | healthcheck + polling | 可靠等待 MySQL 和 API 就绪 |
| 测试数据隔离 | 每个测试函数创建/清理 | 避免测试间相互影响 |
| Fixture 作用域 | `module` 级 Docker 服务 | 减少容器启停开销 |

---

## 文件结构

```
sniffly-site/
├── docker-compose.test.yml    # 测试专用 Docker Compose
├── pytest.ini                 # pytest 配置
└── tests/
    ├── __init__.py
    ├── conftest.py            # fixtures: docker_services, admin_token, api_client
    └── integration/
        ├── __init__.py
        ├── test_auth.py       # 认证 API 测试 (~8 cases)
        ├── test_shares.py      # 分享 API 测试 (~7 cases)
        └── test_users.py      # 用户管理 API 测试 (~9 cases)
```

---

## 任务分解

### Task 1: docker-compose.test.yml

**目标**: 创建测试专用 Docker Compose 配置

**内容**:
- `api` 服务: build，依赖 mysql，healthcheck 等待 `/` 返回 200
- `mysql` 服务: 同生产配置，init.sql 初始化
- 两个服务都映射端口（方便调试）
- 无需 nginx，所有请求直接到 api:8000

**验证**: `docker-compose -f docker-compose.test.yml config` 无报错

---

### Task 2: pytest 配置 + conftest.py

**目标**: 创建 pytest fixtures 和配置

**conftest.py fixtures**:
- `docker_services`: `module` 级别，自动启停 Docker
  - `down -v` 清理旧环境
  - `up -d --build` 启动
  - polling 等待 `/` 返回 200
  - teardown: `down -v`
- `admin_token`: 登录 admin 获取 token（依赖 docker_services）
- `api_client`: 返回 `http://localhost:8000`

**验证**: `pytest --collect-only` 能收集到测试用例

---

### Task 3: test_auth.py

**目标**: 测试认证 API

**测试用例**:

| 用例 | 方法 | 路径 | 预期 |
|------|------|------|------|
| 正确账号密码登录 | POST | /api/auth/login | 200 + token |
| 错误密码 | POST | /api/auth/login | 401 |
| 不存在用户 | POST | /api/auth/login | 401 |
| OAuth2 Password Grant | POST | /api/auth/token | 200 + token |
| 已登录获取用户信息 | GET | /api/auth/me | 200 + 用户信息 |
| 未登录访问 /me | GET | /api/auth/me | 401 |
| 无效 token 访问 /me | GET | /api/auth/me | 401 |
| 登出 | POST | /api/auth/logout | 200 |

**验证**: `pytest tests/integration/test_auth.py -v` 全部通过

---

### Task 4: test_shares.py

**目标**: 测试分享 API（含合并逻辑）

**测试用例**:

| 用例 | 方法 | 路径 | 预期 |
|------|------|------|------|
| 空列表 | GET | /api/shares | 200 + [] |
| 创建分享 | POST | /api/shares | 200 + uuid |
| 获取分享 | GET | /api/shares/{uuid} | 200 + 详情 |
| 更新分享(合并) | POST | /api/shares | uuid 不变，commands 去重合并 |
| 删除分享 | DELETE | /api/shares/{uuid} | 200 |
| 删除后获取 404 | GET | /api/shares/{uuid} | 404 |
| 不存在的分享 | GET | /api/shares/{uuid} | 404 |
| 未登录访问 | GET | /api/shares | 401 |

**合并测试重点**:
1. 创建分享 A（含 command1）
2. 同一项目名再分享（含 command1 + command2）
3. 验证 uuid 不变，commands 有 2 条（去重）

**验证**: `pytest tests/integration/test_shares.py -v` 全部通过

---

### Task 5: test_users.py

**目标**: 测试用户管理 API（admin 专属）

**测试用例**:

| 用例 | 方法 | 路径 | 预期 |
|------|------|------|------|
| admin 列出用户 | GET | /api/users | 200 + 用户列表 |
| 普通用户列用户 | GET | /api/users | 403 |
| admin 创建用户 | POST | /api/users | 200 + 用户信息 |
| 重复用户名 | POST | /api/users | 400 |
| admin 创建 admin | POST | /api/users is_admin=true | 200 |
| admin 删除用户 | DELETE | /api/users/{id} | 200 |
| admin 自删除 | DELETE | /api/users/{self} | 400 |
| admin 查看用户分享 | GET | /api/users/{id}/shares | 200 + 分享列表 |
| 未登录访问 | GET | /api/users | 401 |

**验证**: `pytest tests/integration/test_users.py -v` 全部通过

---

### Task 6: 完整验证

**目标**: 运行完整测试套件 + 冒烟测试脚本

**步骤**:
1. `docker-compose -f docker-compose.test.yml up -d --build`
2. `wait_for_service` 确认就绪
3. `pytest tests/integration/ -v`
4. `docker-compose -f docker-compose.test.yml down -v`

**验证**: 所有测试通过

---

## 依赖项

pytest 和 requests 需要添加到 `requirements.txt`:

```txt
pytest==8.0.0
requests==2.31.0
```

---

## 运行方式

```bash
# 方式 1: 直接运行
cd sniffly-site
pip install -r requirements.txt
docker-compose -f docker-compose.test.yml up -d --build
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down -v

# 方式 2: 使用 Makefile（可选）
make test-integration
```

---

## 预期耗时

| Task | 复杂度 | 预计时间 |
|------|--------|----------|
| Task 1: docker-compose.test.yml | 低 | 5 min |
| Task 2: pytest 配置 | 中 | 10 min |
| Task 3: test_auth.py | 中 | 10 min |
| Task 4: test_shares.py | 中 | 15 min |
| Task 5: test_users.py | 中 | 15 min |
| Task 6: 完整验证 | 低 | 5 min |
| **总计** | | **~60 min** |

---

## 验证清单

- [x] `docker-compose.test.yml config` 无报错
- [x] `pytest --collect-only` 收集到所有用例
- [x] `test_auth.py` 8/8 通过
- [x] `test_shares.py` 7/7 通过
- [x] `test_users.py` 9/9 通过
- [x] `docker-compose down -v` 清理干净

---

## 实现状态

**完成时间**: 2026-04-08

**实际测试结果**: 24/24 测试通过

### 实现过程中修复的问题

1. **MySQL JSON 默认值** - MySQL 8 不允许 JSON 列有默认值，移除 `init.sql` 中的 `DEFAULT '{}'` 和 `DEFAULT '[]'`

2. **端口冲突** - 本地 OrbStack 占用端口 8000，改为使用端口 8001

3. **SQLAlchemy 2.0 兼容性** - `models.py` 添加 `__allow_unmapped__ = True`

4. **bcrypt/passlib 兼容性** - `bcrypt>=5.0` 与 passlib 不兼容，锁定 `bcrypt==4.0.1`

5. **auth.py 依赖顺序** - `get_db` 函数定义在文件底部但在顶部被引用，重构文件结构

6. **API DATABASE_URL** - `auth.py` 硬编码 `localhost`，改为使用环境变量 `os.getenv("DATABASE_URL")`

### 新增/修改的文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `sniffly-site/docker-compose.test.yml` | 新增 | 测试专用 Docker Compose |
| `sniffly-site/init.sql` | 修改 | 移除 JSON 默认值，添加 admin 用户 seeding |
| `sniffly-site/pytest.ini` | 新增 | pytest 配置 |
| `sniffly-site/tests/conftest.py` | 新增 | fixtures |
| `sniffly-site/tests/integration/test_auth.py` | 新增 | 8 个测试 |
| `sniffly-site/tests/integration/test_shares.py` | 新增 | 7 个测试 |
| `sniffly-site/tests/integration/test_users.py` | 新增 | 9 个测试 |
| `sniffly-site/models.py` | 修改 | 添加 `__allow_unmapped__ = True` |
| `sniffly-site/auth.py` | 修改 | 重构依赖顺序，支持环境变量 DATABASE_URL |
| `sniffly-site/requirements.txt` | 修改 | 添加 pytest, requests; 锁定 bcrypt==4.0.1 |
| `sniffly-site/Dockerfile` | 修改 | 添加 curl 用于健康检查 |
