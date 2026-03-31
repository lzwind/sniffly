# Playwright E2E 测试

使用 Playwright 进行端到端浏览器测试，覆盖 sniffly-server 的所有主要用户流程。

## 前置条件

### 1. 安装依赖

```bash
source /Users/iceleaf/Workspaces/tech-documents/.venv/bin/activate
pip install playwright
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
# 标准运行（无头模式）
python tests/e2e/test_suite.py

# 显示浏览器窗口（调试用）
HEADLESS=false python tests/e2e/test_suite.py

# 自定义配置
BASE_URL=http://localhost:8080 ADMIN_USERNAME=admin ADMIN_PASSWORD=admin \
  python tests/e2e/test_suite.py
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BASE_URL` | `http://localhost:8080` | 被测服务地址 |
| `ADMIN_USERNAME` | `admin` | 管理员用户名 |
| `ADMIN_PASSWORD` | `admin` | 管理员密码 |
| `HEADLESS` | `true` | 是否无头运行，设为 `false` 可显示浏览器窗口 |
| `CHROME_PATH` | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | Chrome 可执行文件路径 |

## 测试覆盖

| 场景 | 验证内容 |
|------|----------|
| 首页加载 | 页面标题、公开画廊、Login 链接 |
| 健康检查 | `/health` 返回 `{"status":"healthy"}` |
| 登录成功 | 凭据正确 → 跳转到 `/admin`，token 存入 localStorage |
| 登录失败 | 凭据错误 → 显示错误提示，不跳转 |
| 认证保护 | 未登录访问 `/admin` → 重定向到 `/login` |
| 管理后台概览 | 侧边栏导航、统计卡片加载 |
| 用户管理页 | 表格数据加载、创建/删除用户流程 |
| 分享管理页 | 表格数据加载 |
| 退出登录 | 清除 session Cookie，访问受保护页重定向 |
| 分享页错误处理 | 不存在的分享显示友好错误提示 |

## 测试设计原则

1. **独立运行**：不依赖 pytest 或任何测试框架，直接 `python test_suite.py` 执行
2. **每个测试独立**：使用独立的浏览器 page 执行每个测试用例
3. **真实浏览器行为**：完整走浏览器请求流程，包括重定向和 localStorage 交互
4. **清理机制**：创建/删除操作在测试结束后自动清理数据

## 调试技巧

```bash
# 显示浏览器窗口，逐步观察
HEADLESS=false python tests/e2e/test_suite.py

# 查看完整输出
python tests/e2e/test_suite.py 2>&1
```
