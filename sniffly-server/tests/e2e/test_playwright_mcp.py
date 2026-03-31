"""
Playwright E2E Tests for Sniffly Server — MCP 版本

通过 Playwright Python SDK 直接驱动浏览器，验证完整用户流程。
适合在有 Playwright MCP 工具（mcp__plugin_playwright_playwright__browser_*）的环境中运行，
也可以独立 python 脚本方式执行。

前置条件：
    pip install playwright
    playwright install chromium

用法：
    # 独立脚本运行（自动使用 MCP Playwright 工具）
    python -m sniffly_server.tests.e2e.test_playwright_mcp

    # 或指定环境变量
    BASE_URL=http://localhost:8080 ADMIN_USERNAME=admin ADMIN_PASSWORD=admin \\
        python -m sniffly_server.tests.e2e.test_playwright_mcp

    # pytest 模式（需安装 pytest-playwright）
    pytest sniffly_server/tests/e2e/test_playwright_mcp.py -v
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Generator

import pytest

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8080")
ADMIN_USER: str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS: str = os.getenv("ADMIN_PASSWORD", "admin")


# ------------------------------------------------------------------
# Playwright Driver — 兼容 MCP 和独立运行两种模式
# ------------------------------------------------------------------

def _get_playwright():
    """
    优先尝试从 MCP 工具环境获取 Playwright 实例，
    否则回退到独立 playwright 安装。
    """
    try:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        return pw
    except ImportError:
        raise RuntimeError(
            "Playwright not found. Install with: pip install playwright && playwright install chromium"
        )


class PlaywrightSession:
    """
    封装 Playwright 浏览器会话，提供简洁的 context/page 接口。
    兼容 MCP Playwright 工具链（通过 mcp__ide__executeCode 调用）。
    """

    def __init__(self, headless: bool = True, viewport: dict | None = None):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self._pw = None
        self._browser = None
        self._context = None

    def __enter__(self):
        self._pw = _get_playwright()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(viewport=self.viewport)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        return False

    def new_page(self):
        """创建新页面。"""
        return self._context.new_page()

    def request(self):
        """创建 API 请求上下文（httpx / aiohttp 风格）。"""
        return self._context.request


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

class E2ETestError(AssertionError):
    """E2E 测试专用异常，包含更详细的上下文信息。"""
    pass


def assert_url(page, expected_path: str, msg: str | None = None):
    """断言当前页面 URL 包含指定路径。"""
    actual = page.url
    if expected_path not in actual:
        raise E2ETestError(
            msg or f"Expected URL containing '{expected_path}', got '{actual}'"
        )


def assert_element(page, selector: str, msg: str | None = None):
    """断言指定选择器对应的元素存在且可见。"""
    el = page.locator(selector)
    if not el.is_visible():
        raise E2ETestError(
            msg or f"Element '{selector}' not visible. Page title: {page.title()}"
        )


# ------------------------------------------------------------------
# Test Fixtures (pytest 模式)
# ------------------------------------------------------------------

@pytest.fixture(scope="session")
def pw_session():
    """Session 级别的 Playwright 实例，所有测试共享浏览器。"""
    with PlaywrightSession(headless=True) as session:
        yield session


@pytest.fixture
def page(pw_session) -> Generator:
    """每个测试获得一个独立的新页面。"""
    p = pw_session.new_page()
    yield p
    p.close()


@pytest.fixture
def admin_auth(page) -> str:
    """
    以管理员身份登录并返回 JWT token。
    登录成功后 token 存入 localStorage，fixture 返回 token 供后续调用。
    """
    page.goto(f"{BASE_URL}/login")
    page.fill("#username", ADMIN_USER)
    page.fill("#password", ADMIN_PASS)
    page.click("button[type='submit']")
    page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)

    token = page.evaluate("localStorage.getItem('sniffly_token')")
    if not token:
        raise E2ETestError("Login succeeded but token not found in localStorage")

    # 回到首页，保留登录状态（cookie / storage）
    page.goto(f"{BASE_URL}/")
    return token


# ------------------------------------------------------------------
# Test Cases
# ------------------------------------------------------------------

class TestHealthAndIndex:
    """健康检查与公开首页。"""

    def test_health_returns_healthy(self, pw_session):
        """GET /health 应返回 200 + healthy 状态。"""
        resp = pw_session.request().get(f"{BASE_URL}/health")
        assert resp.ok, f"Health check failed: {resp.status_code}"
        assert resp.json()["status"] == "healthy"

    def test_index_page_loads(self, page):
        """首页应正常加载，显示正确标题和 Hero 区域。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        assert "Sniffly Server" in page.title()
        assert page.locator("h2").first.inner_text() == "Internal Claude Code Analytics"

    def test_index_shows_gallery_section(self, page):
        """首页应包含公开画廊区域。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        gallery = page.locator("h3", has_text="Public Dashboard Gallery")
        assert gallery.is_visible()

    def test_index_login_link_visible_when_anonymous(self, page):
        """未登录时导航栏应显示 Login 入口。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        login_link = page.locator('a.nav-link-primary')
        assert login_link.is_visible()
        assert "Login" in login_link.inner_text()


class TestLoginFlow:
    """登录与认证流程。"""

    def test_login_page_loads(self, page):
        """登录页应显示用户名、密码输入框和提交按钮。"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        assert page.locator("#username").is_visible()
        assert page.locator("#password").is_visible()
        assert page.locator("button[type='submit']").is_visible()

    def test_login_success_redirects_to_admin(self, page):
        """正确凭据登录后应跳转到 /admin。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")

        page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)
        assert "/admin" in page.url

    def test_login_failure_shows_error_message(self, page):
        """错误密码应显示错误提示，不跳转。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", "wrong_password_xyz")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        error = page.locator(".error-message")
        assert error.is_visible()
        assert "Invalid" in error.inner_text()
        assert "/login" in page.url

    def test_login_token_stored_in_localstorage(self, page):
        """登录成功后 JWT token 应被写入 localStorage。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")

        page.wait_for_function(
            "localStorage.getItem('sniffly_token') !== null",
            timeout=8000
        )
        token = page.evaluate("localStorage.getItem('sniffly_token')")
        assert token is not None and len(token) > 20

    def test_authenticated_user_login_redirects_to_admin(self, page):
        """已登录用户访问 /login 应直接跳转到 /admin。"""
        # 先登录
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")
        page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)

        # 再访问 /login
        page.goto(f"{BASE_URL}/login")
        page.wait_for_url(f"{BASE_URL}/admin", timeout=5000)
        assert "/admin" in page.url


class TestAuthProtection:
    """认证保护：未登录访问管理后台应重定向。"""

    def _check_redirect_to_login(self, page, path: str):
        page.goto(f"{BASE_URL}{path}")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login"

    def test_admin_overview_requires_auth(self, page):
        self._check_redirect_to_login(page, "/admin")

    def test_admin_users_requires_auth(self, page):
        self._check_redirect_to_login(page, "/admin/users")

    def test_admin_shares_requires_auth(self, page):
        self._check_redirect_to_login(page, "/admin/shares")


class TestAdminOverview:
    """管理后台概览页。"""

    def test_overview_page_loads(self, page, admin_auth):
        """已登录用户访问 /admin 应显示侧边栏和统计概览。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".sidebar", timeout=5000)

        assert page.locator(".sidebar").is_visible()

    def test_sidebar_navigation_users(self, page, admin_auth):
        """侧边栏"用户管理"链接应跳转到 /admin/users。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        page.click('a[href="/admin/users"]')
        page.wait_for_url(f"{BASE_URL}/admin/users", timeout=5000)
        assert "/admin/users" in page.url

    def test_sidebar_navigation_shares(self, page, admin_auth):
        """侧边栏"分享管理"链接应跳转到 /admin/shares。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        page.click('a[href="/admin/shares"]')
        page.wait_for_url(f"{BASE_URL}/admin/shares", timeout=5000)
        assert "/admin/shares" in page.url

    def test_logout_link_works(self, page, admin_auth):
        """退出链接应清除登录状态并重定向到首页。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        page.click('a[href="/auth/logout"]')
        page.wait_for_url(f"{BASE_URL}/", timeout=5000)

        # 再次访问 /admin 应被重定向到登录页
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)


class TestAdminUsersCRUD:
    """用户管理 CRUD 操作。"""

    def test_users_page_loads(self, page, admin_auth):
        """用户管理页应正常加载，显示表格和"创建用户"按钮。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("h2", timeout=5000)

        assert "用户管理" in page.locator("h2").inner_text()
        assert page.locator('button:has-text("创建用户")').is_visible()

    def test_create_user_modal_opens(self, page, admin_auth):
        """点击"创建用户"应打开模态框。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        page.click('button:has-text("创建用户")')
        modal = page.locator("#modal-overlay")
        assert modal.is_visible()
        assert "创建用户" in page.locator("#modal-title").inner_text()

    def test_create_user_form_has_required_fields(self, page, admin_auth):
        """创建用户表单应包含用户名、密码、启用复选框和提交按钮。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)

        assert page.locator("#new-username").is_visible()
        assert page.locator("#new-password").is_visible()
        assert page.locator("#new-is-active").is_visible()
        assert page.locator("#create-user-form button[type='submit']").is_visible()

    def test_create_user_and_verify_in_table(self, page, admin_auth):
        """创建用户后，表格应刷新并显示新用户。"""
        ts = page.evaluate("Date.now()")
        test_username = f"e2e_user_{ts}"

        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)
        page.fill("#new-username", test_username)
        page.fill("#new-password", "testpass123")
        page.locator("#create-user-form button[type='submit']").click()

        # 成功创建后模态框自动关闭
        page.wait_for_selector("#modal-overlay", state="hidden", timeout=5000)
        page.wait_for_selector(f"td:has-text('{test_username}')", timeout=5000)

        # 清理 — 通过 API 删除测试用户
        resp = page.request.delete(
            f"{BASE_URL}/api/admin/users/{test_username}",
            headers={"Authorization": f"Bearer {admin_auth}"}
        )
        assert resp.status_code in (204, 404), f"Cleanup failed: {resp.status_code}"

    def test_create_duplicate_user_shows_error(self, page, admin_auth):
        """创建同名用户应弹出错误提示，模态框保持打开。"""
        ts = page.evaluate("Date.now()")
        dup_username = f"dup_user_{ts}"

        # 先创建一个用户
        page.request.post(
            f"{BASE_URL}/api/admin/users",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_auth}",
            },
            data={
                "username": dup_username,
                "password": "firstpass123",
                "is_active": True,
            },
        )

        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)
        page.fill("#new-username", dup_username)
        page.fill("#new-password", "secondpass123")

        # 监听 alert 弹窗
        page.on("dialog", lambda d: d.dismiss())
        page.locator("#create-user-form button[type='submit']").click()

        # 应触发错误提示（alert）
        page.wait_for_event("dialog", timeout=5000)
        # 模态框仍处于打开状态
        assert page.locator("#modal-overlay").is_visible()

        # 清理
        page.request.delete(
            f"{BASE_URL}/api/admin/users/{dup_username}",
            headers={"Authorization": f"Bearer {admin_auth}"},
        )

    def test_delete_user_removes_from_table(self, page, admin_auth):
        """删除用户后，该用户应从表格中消失。"""
        ts = page.evaluate("Date.now()")
        del_username = f"del_user_{ts}"

        # 先创建一个待删除用户
        page.request.post(
            f"{BASE_URL}/api/admin/users",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {admin_auth}",
            },
            data={
                "username": del_username,
                "password": "testpass123",
                "is_active": True,
            },
        )

        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(f"td:has-text('{del_username}')", timeout=5000)

        # 自动确认删除确认框
        page.on("dialog", lambda d: d.accept())
        page.locator(
            f"button:has-text('删除'):near(td:has-text('{del_username}'))"
        ).click()

        # 等待表格刷新，用户应消失
        page.wait_for_selector(
            f"td:has-text('{del_username}')", state="hidden", timeout=5000
        )


class TestSharePage:
    """分享页面。"""

    def test_share_page_nonexistent_shows_error(self, page):
        """访问不存在的分享应显示友好错误提示。"""
        page.goto(f"{BASE_URL}/share/nonexistent-id-abc123")
        page.wait_for_load_state("networkidle")

        content = page.content()
        assert "Share not found" in content or "error" in content.lower()

    def test_gallery_card_links_to_share_page(self, page):
        """首页画廊中的分享卡片应包含正确格式的 /share/ 链接。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        cards = page.locator("a.gallery-card")
        if cards.count() > 0:
            href = cards.first.get_attribute("href")
            assert href.startswith("/share/"), f"Invalid share link: {href}"


# ------------------------------------------------------------------
# Standalone Runner（直接 python 运行，非 pytest）
# ------------------------------------------------------------------

def _run_standalone():
    """
    直接运行此文件时以 standalone 模式执行所有测试。
    输出格式：[PASS] / [FAIL] test_name — reason
    """
    from urllib.request import urlopen
    from urllib.error import URLError

    print(f"\n{'='*60}")
    print(f"  Sniffly Server E2E Tests (Standalone Mode)")
    print(f"  BASE_URL={BASE_URL}")
    print(f"{'='*60}\n")

    passed = failed = 0

    # 前置检查：服务是否可达
    try:
        urlopen(BASE_URL + "/health", timeout=5)
    except URLError:
        print(f"[FATAL] Cannot reach {BASE_URL}/health — is the server running?")
        print(f"  Hint: cd sniffly-server && docker-compose up -d")
        sys.exit(1)

    # 收集测试
    test_classes = [
        TestHealthAndIndex,
        TestLoginFlow,
        TestAuthProtection,
        TestAdminOverview,
        TestAdminUsersCRUD,
        TestSharePage,
    ]

    with PlaywrightSession(headless=True) as pw_sess:
        for cls in test_classes:
            print(f"\n{cls.__name__}")
            print("-" * 40)
            instance = cls()
            for name in [m for m in dir(instance) if m.startswith("test_")]:
                method = getattr(instance, name)
                try:
                    # 准备 fixture
                    page = pw_sess.new_page()
                    if hasattr(instance, "__init__") and instance.__init__ is not object.__init__:
                        instance.page = page

                    # 调用 test method
                    sig_params = list(method.__code__.co_varnames[: method.__code__.co_argcount])
                    if "page" in sig_params:
                        method(page)
                    else:
                        method()

                    print(f"  [\033[92mPASS\033[0m] {name}")
                    passed += 1
                except Exception as e:
                    print(f"  [\033[91mFAIL\033[0m] {name} — {e}")
                    failed += 1
                finally:
                    page.close()

    print(f"\n{'='*60}")
    print(f"  Results: \033[92m{passed} passed\033[0m, \033[91m{failed} failed\033[0m")
    print(f"{'='*60}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    _run_standalone()
