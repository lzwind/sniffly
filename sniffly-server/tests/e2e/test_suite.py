"""
Sniffly Server E2E 测试用例集

通过 Playwright 驱动真实浏览器，验证完整用户流程。

前置条件：
    pip install playwright
    playwright install chromium

用法：
    # 标准运行
    python tests/e2e/test_suite.py

    # 自定义配置
    BASE_URL=http://localhost:8080 \\
    ADMIN_USERNAME=admin \\
    ADMIN_PASSWORD=admin \\
    HEADLESS=true \\
    python tests/e2e/test_suite.py

    # 显示浏览器窗口（调试用）
    HEADLESS=false python tests/e2e/test_suite.py
"""

from __future__ import annotations

import os
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from typing import Optional

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8080")
ADMIN_USER: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS: str = os.getenv("ADMIN_PASSWORD", "admin")
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() != "false"
CHROME_PATH: str = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# ------------------------------------------------------------------
# Test Result Tracking
# ------------------------------------------------------------------

class TestResult:
    """测试结果记录器"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[tuple[str, str]] = []  # (test_name, error_msg)

    def record(self, name: str, passed: bool, error: Optional[str] = None):
        if passed:
            self.passed += 1
            status = "\033[92mPASS\033[0m"
        else:
            self.failed += 1
            self.errors.append((name, error or "Unknown error"))
            status = f"\033[91mFAIL\033[0m"
        print(f"  [{status}] {name}")
        if error and not passed:
            print(f"         \033[91m{error}\033[0m")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print(f"\n  Failed tests:")
            for name, err in self.errors:
                print(f"    - {name}: {err}")
        print(f"{'='*60}\n")
        return self.failed == 0


# ------------------------------------------------------------------
# Playwright Browser Session
# ------------------------------------------------------------------

def create_browser_session():
    """创建 Playwright 浏览器会话"""
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=HEADLESS,
        executable_path=CHROME_PATH,
        slow_mo=100 if not HEADLESS else 0
    )
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    return pw, browser, context, page


def close_browser_session(pw, browser, context):
    """关闭浏览器会话"""
    context.close()
    browser.close()
    pw.stop()


# ------------------------------------------------------------------
# Test Cases
# ------------------------------------------------------------------

def check_server_reachable() -> bool:
    """检查服务是否可达"""
    try:
        urlopen(BASE_URL + "/health", timeout=5)
        return True
    except URLError:
        return False


def test_index_page(page, result: TestResult):
    """测试首页加载"""
    name = "首页加载 - 标题和内容"
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        assert "Sniffly Server" in page.title(), f"Title: {page.title()}"
        assert page.locator("h2").first.inner_text() == "Internal Claude Code Analytics"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_public_gallery(page, result: TestResult):
    """测试公开画廊"""
    name = "公开画廊 - 画廊区域可见"
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        gallery = page.locator("h3", has_text="Public Dashboard Gallery")
        assert gallery.is_visible(), "Gallery section not visible"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_login_link_visible(page, result: TestResult):
    """测试未登录时显示登录链接"""
    name = "登录链接 - 未登录时可见"
    try:
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        login_link = page.locator('a.nav-link-primary')
        assert login_link.is_visible(), "Login link not visible"
        assert "Login" in login_link.inner_text()
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_health_endpoint(page, result: TestResult):
    """测试健康检查接口"""
    name = "健康检查 - /health 返回 healthy"
    try:
        resp = page.request.get(f"{BASE_URL}/health")
        assert resp.status_code == 200, f"Status: {resp.status_code}"
        data = resp.json()
        assert data.get("status") == "healthy", f"Response: {data}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_login_page_loads(page, result: TestResult):
    """测试登录页加载"""
    name = "登录页 - 页面元素完整"
    try:
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        assert page.locator("#username").is_visible(), "Username field not visible"
        assert page.locator("#password").is_visible(), "Password field not visible"
        assert page.locator("button[type='submit']").is_visible(), "Submit button not visible"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_login_success(page, result: TestResult):
    """测试登录成功"""
    name = "登录成功 - 正确凭据跳转 /admin"
    try:
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)
        assert "/admin" in page.url, f"URL: {page.url}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_login_failure(page, result: TestResult):
    """测试登录失败"""
    name = "登录失败 - 错误密码显示提示不跳转"
    try:
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", "wrong_password_xyz")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        error_msg = page.locator(".error-message")
        assert error_msg.is_visible(), "Error message not visible"
        assert "Invalid" in error_msg.inner_text()
        assert "/login" in page.url, f"URL: {page.url}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_login_token_stored(page, result: TestResult):
    """测试登录后 token 存储"""
    name = "登录 token - 存入 localStorage"
    try:
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")
        page.wait_for_function("localStorage.getItem('sniffly_token') !== null", timeout=8000)

        token = page.evaluate("localStorage.getItem('sniffly_token')")
        assert token is not None and len(token) > 20, f"Token: {token}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_auth_redirect_admin(page, result: TestResult):
    """测试未登录访问 /admin 重定向"""
    name = "认证保护 - 未登录访问 /admin 重定向到 /login"
    try:
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login", f"URL: {page.url}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_auth_redirect_users(page, result: TestResult):
    """测试未登录访问 /admin/users 重定向"""
    name = "认证保护 - 未登录访问 /admin/users 重定向到 /login"
    try:
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login", f"URL: {page.url}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_auth_redirect_shares(page, result: TestResult):
    """测试未登录访问 /admin/shares 重定向"""
    name = "认证保护 - 未登录访问 /admin/shares 重定向到 /login"
    try:
        page.goto(f"{BASE_URL}/admin/shares")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login", f"URL: {page.url}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def admin_login(page):
    """执行管理员登录，返回 token"""
    page.goto(f"{BASE_URL}/login")
    page.fill("#username", ADMIN_USER)
    page.fill("#password", ADMIN_PASS)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)
    return page.evaluate("localStorage.getItem('sniffly_token')")


def test_admin_overview(page, result: TestResult):
    """测试管理后台概览页"""
    name = "管理后台概览 - 侧边栏加载"
    token = None
    try:
        token = admin_login(page)
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".sidebar", timeout=5000)

        assert page.locator(".sidebar").is_visible(), "Sidebar not visible"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))
    return token


def test_sidebar_navigation(page, result: TestResult, _token: str):
    """测试侧边栏导航"""
    name = "侧边栏导航 - 用户管理/分享管理链接"
    try:
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        # 点击用户管理
        page.click('a[href="/admin/users"]')
        page.wait_for_url(f"{BASE_URL}/admin/users", timeout=5000)
        assert "/admin/users" in page.url

        # 点击分享管理
        page.click('a[href="/admin/shares"]')
        page.wait_for_url(f"{BASE_URL}/admin/shares", timeout=5000)
        assert "/admin/shares" in page.url
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_users_page_loads(page, result: TestResult, _token: str):
    """测试用户管理页加载"""
    name = "用户管理页 - 表格和按钮加载"
    try:
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("h2", timeout=5000)

        assert "用户管理" in page.locator("h2").inner_text()
        assert page.locator('button:has-text("创建用户")').is_visible()
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_create_user_modal(page, result: TestResult, _token: str):
    """测试创建用户模态框"""
    name = "创建用户 - 模态框打开和表单字段"
    try:
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)

        assert page.locator("#modal-overlay").is_visible()
        assert page.locator("#new-username").is_visible()
        assert page.locator("#new-password").is_visible()
        assert page.locator("#new-is-active").is_visible()
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_create_and_delete_user(page, result: TestResult, _token: str):
    """测试创建和删除用户"""
    name = "创建/删除用户 - 完整流程"
    try:
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        # 创建用户
        test_username = f"e2e_user_{int(time.time())}"
        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)
        page.fill("#new-username", test_username)
        page.fill("#new-password", "testpass123")
        page.locator("#create-user-form button[type='submit']").click()

        # 等待模态框关闭
        page.wait_for_selector("#modal-overlay", state="hidden", timeout=5000)
        page.wait_for_selector(f"td:has-text('{test_username}')", timeout=5000)

        # 删除用户
        page.on("dialog", lambda d: d.accept())
        page.locator(f"button:has-text('删除'):near(td:has-text('{test_username}'))").click()
        page.wait_for_selector(f"td:has-text('{test_username}')", state="hidden", timeout=5000)

        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_shares_page_loads(page, result: TestResult, _token: str):
    """测试分享管理页加载"""
    name = "分享管理页 - 页面加载"
    try:
        page.goto(f"{BASE_URL}/admin/shares")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#shares-tbody", timeout=5000)
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_logout(page, result: TestResult):
    """测试退出登录"""
    name = "退出登录 - 清除状态并重定向"
    try:
        admin_login(page)  # 确保已登录
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".sidebar", timeout=5000)

        page.click('a[href="/auth/logout"]')
        page.wait_for_url(f"{BASE_URL}/", timeout=5000)

        # 验证 cookies 已清除
        cookies = [c["name"] for c in page.context.cookies()]
        assert "sniffly_session" not in cookies, f"Session cookie still exists: {cookies}"

        # 验证访问 /admin 被重定向
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


def test_share_page_not_found(page, result: TestResult):
    """测试分享页不存在的处理"""
    name = "分享页 - 不存在的分享显示错误"
    try:
        page.goto(f"{BASE_URL}/share/nonexistent-id-abc12345")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "Share not found" in content or "error" in content.lower(), f"Content: {content[:200]}"
        result.record(name, True)
    except Exception as e:
        result.record(name, False, str(e))


# ------------------------------------------------------------------
# Test Suite Runner
# ------------------------------------------------------------------

def run_tests():
    """运行所有测试用例"""
    print(f"\n{'='*60}")
    print(f"  Sniffly Server E2E Test Suite")
    print(f"  BASE_URL:  {BASE_URL}")
    print(f"  ADMIN_USER: {ADMIN_USER}")
    print(f"  HEADLESS:  {HEADLESS}")
    print(f"{'='*60}\n")

    # 前置检查
    if not check_server_reachable():
        print(f"\033[91m[FATAL] Cannot reach {BASE_URL}/health — is the server running?\033[0m")
        print(f"  Hint: cd sniffly-server && docker-compose up -d")
        sys.exit(1)

    result = TestResult()
    pw, browser, context, page = create_browser_session()

    try:
        # --- 公开页面测试 ---
        print("\033[1m[Public Pages]\033[0m")
        test_index_page(page, result)
        test_public_gallery(page, result)
        test_login_link_visible(page, result)
        test_health_endpoint(page, result)

        # --- 登录流程测试 ---
        print("\n\033[1m[Login Flow]\033[0m")
        test_login_page_loads(page, result)
        test_login_success(page, result)
        test_login_failure(page, result)
        test_login_token_stored(page, result)

        # --- 认证保护测试 ---
        print("\n\033[1m[Auth Protection]\033[0m")
        test_auth_redirect_admin(page, result)
        test_auth_redirect_users(page, result)
        test_auth_redirect_shares(page, result)

        # --- 管理后台测试（需登录） ---
        print("\n\033[1m[Admin Dashboard]\033[0m")
        token = test_admin_overview(page, result)
        test_sidebar_navigation(page, result, token)
        test_users_page_loads(page, result, token)
        test_create_user_modal(page, result, token)
        test_create_and_delete_user(page, result, token)
        test_shares_page_loads(page, result, token)
        test_logout(page, result)

        # --- 分享页测试 ---
        print("\n\033[1m[Share Page]\033[0m")
        test_share_page_not_found(page, result)

    finally:
        close_browser_session(pw, browser, context)

    success = result.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    run_tests()
