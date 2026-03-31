# Playwright E2E 测试

使用 Playwright 进行端到端浏览器测试，覆盖 sniffly-server 的所有主要用户流程。

## 前置条件

### 1. 安装浏览器

```bash
playwright install chromium
```

### 2. 启动被测服务

**方式一：Docker Compose（推荐）**

```bash
cd sniffly-server
docker-compose up -d
```

**方式二：本地 uvicorn（需自行启动 MongoDB 和 Redis）**

```bash
cd sniffly-server
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## 运行测试

```bash
# 使用默认地址 http://localhost:8080
BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e -v

# 使用 Docker Compose 启动的地址
BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e -v -s

# 只运行特定测试类
BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e::TestLogin -v

# 显示浏览器窗口（调试模式）
BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e -v --headed
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_URL` | `http://localhost:8080` | 被测服务地址 |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD` | `admin` | 管理员密码 |

## 测试覆盖

| 测试类 | 覆盖场景 |
|--------|----------|
| `TestIndexPage` | 首页加载、公开画廊、健康检查 |
| `TestLogin` | 登录成功/失败、token 存储、重复登录重定向 |
| `TestAdminAuthProtection` | 未授权访问重定向到登录页 |
| `TestAdminOverview` | 管理后台概览页、侧边栏导航 |
| `TestAdminUsers` | 用户管理 CRUD（创建/编辑/删除/重复检测） |
| `TestSharePage` | 分享页错误处理、首页画廊链接 |

## 测试设计原则

1. **每个测试独立**：使用 `browser.new_page()` 为每个测试创建独立的浏览器页面
2. **认证复用**：`admin_token` fixture 完成登录并返回 JWT，避免重复填写表单
3. **真实浏览器行为**：完整走浏览器请求流程，包括重定向和 localStorage 交互
4. **清理机制**：创建/删除操作在测试结束后清理数据

## 调试技巧

```bash
# 打开浏览器窗口（--headed）实时观察
pytest sniffly-server/tests/e2e -v --headed

# 测试结束后保留浏览器窗口（--pause）
pytest sniffly-server/tests/e2e -v --pause

# 查看控制台输出
pytest sniffly-server/tests/e2e -v -s

# 只运行最后一个失败的测试
pytest sniffly-server/tests/e2e --lf -v
```
