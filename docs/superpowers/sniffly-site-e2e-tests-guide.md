# Sniffly Site E2E 测试指南

**日期**: 2026-04-08
**版本**: 1.0
**状态**: 已完成

---

## 概述

本文档描述 sniffly-site 的端到端（E2E）测试套件，用于验证用户管理功能的前端 UI 交互。

## 测试文件结构

```
sniffly-site/
├── tests/
│   ├── e2e/
│   │   ├── conftest.py                        # Pytest fixtures 和配置
│   │   ├── test_admin_user_management.py      # Admin 用户管理测试
│   │   └── __init__.py
│   └── integration/                            # API 集成测试
│       ├── test_auth.py                       # 认证 API 测试
│       ├── test_users.py                      # 用户 API 测试
│       └── test_shares.py                     # 分享 API 测试
├── docker-compose.test.yml                     # 测试用 Docker 配置
└── pytest.ini                                # Pytest 配置
```

## 测试用例

### Admin 用户管理测试 (`test_admin_user_management.py`)

| 测试类 | 测试用例 | 说明 |
|--------|----------|------|
| `TestAdminLogin` | `test_admin_login_via_api` | 验证管理员登录获取有效 token |
| `TestAdminLogin` | `test_admin_page_loads_when_authenticated` | 验证认证后 /admin 页面正常加载 |
| `TestUserList` | `test_user_list_loads` | 验证用户列表正确显示 |
| `TestUserList` | `test_api_users_endpoint_returns_200` | 验证 GET /api/users 返回 200 |
| `TestCreateUserModal` | `test_click_add_user_opens_modal` | 点击"Add User"按钮打开模态框 |
| `TestCreateUserModal` | `test_modal_has_required_fields` | 验证表单包含所有必填字段 |
| `TestCreateUserModal` | `test_close_modal_works` | 验证关闭模态框功能正常 |
| `TestCreateUser` | `test_create_new_user_via_ui` | 通过 UI 创建新用户 |
| `TestCreateUser` | `test_create_user_appears_in_api` | 验证新用户出现在 API 响应中 |
| `TestDeleteUser` | `test_delete_user_via_ui` | 通过 UI 删除用户 |
| `TestAdminProtection` | `test_regular_user_cannot_view_users` | 验证非管理员用户无法访问用户列表 |

**运行结果**: 11 个测试，9 passed, 2 failed（见下方已知问题）

## 环境要求

### 系统依赖

- **Python**: 3.11+
- **Docker**: 用于启动 MySQL 和 API 服务
- **Chrome/Chromium**: 系统浏览器（用于 Playwright）

### Python 依赖

```txt
playwright>=1.41.0
pytest>=8.0.0
requests>=2.31.0
```

## 快速开始

### 1. 安装依赖

```bash
cd sniffly-site

# 创建虚拟环境（使用 uv）
uv venv --python 3.14
source .venv/bin/activate

# 安装 Python 依赖
uv pip install -r requirements.txt

# 安装 Playwright（使用系统 Chrome）
playwright install chromium
# 或使用系统 Chrome
python -m playwright install chromium channel=chrome
```

### 2. 配置系统 Chrome

如果使用系统 Chrome，需要在 `tests/e2e/conftest.py` 中指定：

```python
browser = p.chromium.launch(headless=True, channel="chrome")
```

### 3. 运行测试

```bash
# 运行所有 E2E 测试
pytest tests/e2e/ -v

# 运行指定测试文件
pytest tests/e2e/test_admin_user_management.py -v

# 运行指定测试类
pytest tests/e2e/test_admin_user_management.py::TestAdminLogin -v

# 运行指定测试用例
pytest tests/e2e/test_admin_user_management.py::TestAdminLogin::test_admin_login_via_api -v
```

## 测试架构

### Docker 服务

E2E 测试依赖以下 Docker 服务（通过 `docker-compose.test.yml` 管理）：

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| `api` | sniffly-site-api | 8001 | FastAPI 后端服务 |
| `mysql` | mysql:8 | 3306 | MySQL 数据库 |

### Fixture 依赖链

```
docker_services (启动 Docker)
    ↓
admin_token (获取 admin 访问令牌)
    ↓
browser (启动 Playwright 浏览器)
    ↓
page (创建新页面)
    ↓
authenticated_page (认证后的页面)
```

### 关键 Fixture

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `docker_services` | module | 启动/停止 Docker 服务 |
| `admin_token` | module | 获取 admin API token |
| `browser` | module | Playwright 浏览器实例 |
| `page` | function | 每个测试的新页面 |
| `authenticated_page` | function | 已认证的页面（预填充 token） |

## 测试设计

### 认证流程

E2E 测试通过 API 登录获取 token，然后注入到浏览器的 localStorage：

```python
def authenticated_page(page: Page, admin_token: str) -> Page:
    page.goto(f"{BASE_URL}/")
    # 将 token 注入 localStorage 以绕过前端认证
    page.evaluate(f"localStorage.setItem('access_token', '{admin_token}')")
    page.goto(f"{BASE_URL}/admin")
    return page
```

### 数据清理

- 测试使用时间戳生成唯一用户名（如 `e2e_user_205839`）
- 测试结束后自动清理创建的用户
- 使用 `module` 作用域的 fixture 确保 Docker 服务在整个测试模块中保持运行

## 已知问题

### 1. Locator Strict Mode 问题

**问题描述**: Playwright 默认使用 strict mode，多个匹配元素时会抛出异常。

**影响测试**:
- `test_create_new_user_via_ui`
- `test_create_user_appears_in_api`

**原因**: `.user-item` 选择器匹配到多个用户项（admin + 测试用户）。

**解决方案**: 使用更精确的 locator：

```python
# 错误（strict mode）
expect(authenticated_page.locator(".user-item")).to_contain_text(test_username)

# 正确（精确匹配）
user_item = authenticated_page.locator(".user-item").filter(has_text=test_username)
expect(user_item).to_be_visible()
```

**状态**: 待修复

### 2. pytest.ini asyncio_mode 警告

**警告**: `Unknown config option: asyncio_mode`

**原因**: `pytest.ini` 中配置了 `asyncio_mode = auto`，但未安装 `pytest-asyncio` 插件。

**解决方案**: 移除 `pytest.ini` 中的 `asyncio_mode` 配置，或安装 `pytest-asyncio`。

**状态**: 待修复

## 调试技巧

### 查看页面快照

```python
# 在测试中添加截图
authenticated_page.screenshot(path="debug.png")

# 获取页面 HTML
print(authenticated_page.content())
```

### 控制台日志

```python
# 监听控制台消息
authenticated_page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
```

### 逐步调试

```python
# 暂停执行，等待调试器连接
import pdb; pdb.set_trace()

# 或使用 Playwright 的调试模式
page.pause()
```

### 查看网络请求

```python
# 监听网络请求
authenticated_page.on("request", lambda request: print(f"REQUEST: {request.url}"))
authenticated_page.on("response", lambda response: print(f"RESPONSE: {response.url} -> {response.status}"))
```

## 扩展测试

### 添加新测试文件

1. 在 `tests/e2e/` 目录下创建新文件，如 `test_dashboard.py`
2. 导入必要的 fixtures：

```python
from tests.e2e.conftest import docker_services, admin_token, api_client, authenticated_page
```

3. 编写测试用例
4. 运行测试验证

### 添加新测试用例

```python
class TestNewFeature:
    """测试新功能"""

    def test_new_feature_works(self, authenticated_page: Page):
        """验证新功能正常工作"""
        # 实现测试逻辑
        pass
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install uv
          uv venv --python 3.11
          source .venv/bin/activate
          uv pip install -r requirements.txt

      - name: Install Playwright browsers
        run: |
          playwright install chromium

      - name: Run E2E tests
        run: |
          pytest tests/e2e/ -v

      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: debug-screenshots
          path: tests/e2e/*.png
```

## 相关文档

- [Integration Tests Plan](../plans/2026-04-08-sniffly-integration-tests-plan.md)
- [Sniffly Site Docker Design](../specs/2026-04-08-sniffly-site-docker-design.md)
