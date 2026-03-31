# Playwright E2E 测试指南

本文档描述如何启动服务并运行 Playwright 端到端测试。

---

## 前置条件

### 1. 启动 MongoDB 和 Redis

```bash
# 启动 MongoDB
docker run -d --name sniffly-mongo -p 27017:27017 mongo:7

# 启动 Redis
docker run -d --name sniffly-redis -p 6379:6379 redis:7-alpine

# 验证
docker exec sniffly-mongo mongosh --eval "db.adminCommand('ping')"
```

> 如果端口 27017 或 6379 已被占用，先删除旧容器：
> `docker rm -f sniffly-mongo sniffly-redis`

### 2. 安装 Python 依赖

```bash
cd /path/to/sniffly
source .venv/bin/activate
uv pip install playwright
```

> `playwright` 已包含在 `requirements-dev.txt` 中，可通过项目虚拟环境安装。

### 3. 确认 Chrome 路径

```bash
ls /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
```

路径：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`

---

## 启动服务

```bash
cd /Users/iceleaf/Workspaces/third-party/sniffly/sniffly-server

MONGODB_URL=mongodb://localhost:27017/sniffly \
REDIS_URL=redis://localhost:6379 \
JWT_SECRET=test-secret \
ADMIN_USERNAME=admin \
ADMIN_PASSWORD=admin \
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

服务地址：`http://localhost:8080`

---

## 运行测试

### 方式一：运行测试用例集（推荐）

测试用例集位于 `tests/e2e/test_suite.py`，包含所有场景的完整验证。

```bash
source /Users/iceleaf/Workspaces/tech-documents/.venv/bin/activate

cd /Users/iceleaf/Workspaces/third-party/sniffly/sniffly-server

# 标准运行（无头模式）
python tests/e2e/test_suite.py

# 显示浏览器窗口（调试用）
HEADLESS=false python tests/e2e/test_suite.py

# 自定义配置
BASE_URL=http://localhost:8080 \\
ADMIN_USERNAME=admin \\
ADMIN_PASSWORD=admin \\
python tests/e2e/test_suite.py
```

### 调试模式（显示浏览器窗口）

```bash
# 修改测试脚本中的 launch() 调用
browser = p.chromium.launch(
    headless=False,           # 显示浏览器窗口
    executable_path=chrome_path,
    slow_mo=500              # 减慢操作便于观察
)
```

---

## 快速验证命令（不启动完整浏览器）

```bash
# 1. 登录获取 Cookie
curl -s -c /tmp/sc.txt -X POST http://localhost:8080/login \
  -d "username=admin&password=admin" -D - -o /dev/null | grep set-cookie

# 2. 带 Cookie 请求用户列表 API
curl -s -b /tmp/sc.txt http://localhost:8080/api/admin/users | python3 -m json.tool

# 3. 退出（清除 Cookie）
curl -s -b /tmp/sc.txt -D - http://localhost:8080/auth/logout -o /dev/null | grep set-cookie
```

---

## 常见问题

### 端口被占用

```bash
# 查找占用 8080 端口的进程
lsof -ti:8080 | xargs kill -9
```

### Playwright 报错 "browser closed"

MCP 会话的浏览器已关闭，需要重启 Claude Code 的 Playwright MCP 插件。使用 Python 独立脚本不受此影响。

### MongoDB/Redis 未启动

```bash
docker start sniffly-mongo sniffly-redis
```

### 认证失败 401

确认 `JWT_SECRET` 在启动服务和登录时一致。如果不一致，之前签发的 token 全部失效，需要重新登录。

---

## 测试覆盖范围

| 场景 | 验证内容 |
|------|----------|
| 首页加载 | 页面标题、公开画廊、Login 链接 |
| 健康检查 | `/health` 返回 `{"status":"healthy"}` |
| 登录成功 | 凭据正确 → 跳转到 `/admin`，设置 Cookie |
| 登录失败 | 凭据错误 → 显示错误提示，不跳转 |
| 概览页 | 侧边栏导航、统计卡片加载 |
| 用户管理页 | 表格数据通过 API 加载（带 Bearer Token） |
| 分享管理页 | 表格数据加载 |
| 退出登录 | 清除 `sniffly_session` Cookie |
| 退出后访问受保护页 | `/admin` → 302 `/login` |
