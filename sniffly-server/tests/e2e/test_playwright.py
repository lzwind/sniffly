"""
Playwright E2E Tests for Sniffly Server.

这些测试通过真实的浏览器会话验证完整的用户流程。
需要服务运行在 http://localhost:8080，可通过 Docker Compose 或本地 uvicorn 启动。

用法：
    # 启动服务后运行测试
    pytest sniffly-server/tests/e2e/test_playwright.py -v

    # 或指定 base_url
    BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e/test_playwright.py -v

环境变量：
    BASE_URL       - 服务地址，默认 http://localhost:8080
    ADMIN_USERNAME - 管理员用户名，默认 admin
    ADMIN_PASSWORD - 管理员密码，默认 admin
"""

import os
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "admin")


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def page(browser):
    """Provide a fresh browser page for each test."""
    return browser.new_page()


@pytest.fixture
def admin_token(page):
    """
    登录为管理员并返回 JWT token。
    token 通过登录成功页面的 localStorage 获取。
    """
    page.goto(f"{BASE_URL}/login")
    page.fill("#username", ADMIN_USER)
    page.fill("#password", ADMIN_PASS)
    page.click("button[type='submit']")
    # login_success.html 会将 token 存入 localStorage 后重定向到 /admin
    page.wait_for_url(f"{BASE_URL}/admin", timeout=5000)
    token = page.evaluate("localStorage.getItem('sniffly_token')")
    return token


# ==============================================================================
# Test: 首页 (Public Gallery)
# ==============================================================================

class TestIndexPage:
    """测试公开首页和画廊页面。"""

    def test_index_page_loads(self, page):
        """首页应正常加载并显示标题。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        assert "Sniffly Server" in page.title()
        assert page.locator("h2").first.inner_text() == "Internal Claude Code Analytics"

    def test_index_shows_public_gallery(self, page):
        """首页应展示公开分享画廊，即使为空也应有提示。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        gallery_heading = page.locator("h3").inner_text()
        assert "Public Dashboard Gallery" in gallery_heading

    def test_index_login_link_visible_when_not_authenticated(self, page):
        """未登录时导航栏应显示 Login 链接。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        login_link = page.locator('a.nav-link-primary')
        assert login_link.is_visible()
        assert login_link.inner_text() == "Login"

    def test_index_health_endpoint(self, page):
        """健康检查接口应返回 healthy 状态。"""
        response = page.request.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


# ==============================================================================
# Test: 登录流程
# ==============================================================================

class TestLogin:
    """测试登录页和认证流程。"""

    def test_login_page_loads(self, page):
        """登录页应正常加载。"""
        page.goto(f"{BASE_URL}/login")
        page.wait_for_load_state("networkidle")

        assert "Sign In" in page.title()
        assert page.locator("#username").is_visible()
        assert page.locator("#password").is_visible()
        assert page.locator("button[type='submit']").is_visible()

    def test_login_success_redirects_to_admin(self, page):
        """使用正确凭据登录后应跳转到管理后台。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")

        # login_success.html -> /admin 的重定向
        page.wait_for_url(f"{BASE_URL}/admin", timeout=8000)
        assert "/admin" in page.url

    def test_login_failure_shows_error(self, page):
        """使用错误密码登录应显示错误提示，不跳转。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", "wrong_password")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")

        error_msg = page.locator(".error-message")
        assert error_msg.is_visible()
        assert "Invalid" in error_msg.inner_text()
        # 不应跳转到 /admin
        assert page.url == f"{BASE_URL}/login"

    def test_login_already_authenticated_redirects_to_admin(self, page, admin_token):
        """已登录用户访问 /login 应直接重定向到 /admin。"""
        # admin_token fixture 已完成登录
        page.goto(f"{BASE_URL}/login")
        page.wait_for_url(f"{BASE_URL}/admin", timeout=5000)
        assert "/admin" in page.url

    def test_login_token_stored_in_localstorage(self, page):
        """登录成功后 token 应存入 localStorage。"""
        page.goto(f"{BASE_URL}/login")
        page.fill("#username", ADMIN_USER)
        page.fill("#password", ADMIN_PASS)
        page.click("button[type='submit']")

        page.wait_for_function("localStorage.getItem('sniffly_token') !== null", timeout=8000)
        token = page.evaluate("localStorage.getItem('sniffly_token')")
        assert token is not None
        assert len(token) > 20  # JWT token 应有一定长度


# ==============================================================================
# Test: 管理后台 - 认证保护
# ==============================================================================

class TestAdminAuthProtection:
    """测试管理后台的认证保护机制。"""

    def test_admin_redirects_to_login_when_not_authenticated(self, page):
        """未登录访问 /admin 应重定向到登录页。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login"

    def test_admin_users_redirects_to_login_when_not_authenticated(self, page):
        """未登录访问 /admin/users 应重定向到登录页。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login"

    def test_admin_shares_redirects_to_login_when_not_authenticated(self, page):
        """未登录访问 /admin/shares 应重定向到登录页。"""
        page.goto(f"{BASE_URL}/admin/shares")
        page.wait_for_url(f"{BASE_URL}/login", timeout=5000)
        assert page.url == f"{BASE_URL}/login"


# ==============================================================================
# Test: 管理后台 - 概览页
# ==============================================================================

class TestAdminOverview:
    """测试管理后台概览页面。"""

    def test_admin_overview_loads_when_authenticated(self, page, admin_token):
        """已登录用户访问 /admin 应正常显示概览页。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        # 概览页应包含统计卡片
        page.wait_for_selector(".sidebar", timeout=5000)
        assert page.locator(".sidebar").is_visible()

        # 侧边栏应有导航项
        nav_items = page.locator(".sidebar-nav .nav-item")
        assert nav_items.count() >= 3

    def test_admin_sidebar_navigation_links(self, page, admin_token):
        """侧边栏导航链接应正确指向各子页面。"""
        page.goto(f"{BASE_URL}/admin")
        page.wait_for_load_state("networkidle")

        # 点击"用户管理"
        page.click('a[href="/admin/users"]')
        page.wait_for_url(f"{BASE_URL}/admin/users", timeout=5000)
        assert "/admin/users" in page.url

        # 点击"分享管理"
        page.click('a[href="/admin/shares"]')
        page.wait_for_url(f"{BASE_URL}/admin/shares", timeout=5000)
        assert "/admin/shares" in page.url


# ==============================================================================
# Test: 管理后台 - 用户管理
# ==============================================================================

class TestAdminUsers:
    """测试管理后台用户管理页面（创建、编辑、删除）。"""

    def test_admin_users_page_loads(self, page, admin_token):
        """用户管理页应正常加载并显示用户表格。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")

        # 页面标题
        page.wait_for_selector("h2", timeout=5000)
        h2 = page.locator("h2").inner_text()
        assert "用户管理" in h2

        # "创建用户"按钮
        create_btn = page.locator('button:has-text("创建用户")')
        assert create_btn.is_visible()

    def test_create_user_modal_opens(self, page, admin_token):
        """点击"创建用户"应打开模态框。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        page.click('button:has-text("创建用户")')

        # 模态框应可见
        modal = page.locator("#modal-overlay")
        assert modal.is_visible()
        assert "创建用户" in page.locator("#modal-title").inner_text()

    def test_create_user_form_elements(self, page, admin_token):
        """创建用户表单应包含所有必要字段。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)

        assert page.locator("#new-username").is_visible()
        assert page.locator("#new-password").is_visible()
        assert page.locator("#new-is-active").is_visible()
        assert page.locator('button[type="submit"]').is_visible()

    def test_create_user_success(self, page, admin_token):
        """成功创建新用户后，表格应刷新并显示新用户。"""
        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        # 打开创建用户模态框
        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)

        # 填充表单
        test_username = f"testuser_{page.evaluate("Date.now()")}"
        page.fill("#new-username", test_username)
        page.fill("#new-password", "testpass123")

        # 提交
        page.locator("#create-user-form button[type='submit']").click()

        # 等待模态框关闭（成功创建后会自动关闭）
        page.wait_for_selector("#modal-overlay", state="hidden", timeout=5000)

        # 表格中应出现新用户名
        page.wait_for_selector(f"td:has-text('{test_username}')", timeout=5000)
        assert page.locator(f"td:has-text('{test_username}')").is_visible()

        # 清理：删除测试用户（通过 API）
        page.evaluate(f"""
            fetch('/api/admin/users/{test_username}', {{
                method: 'DELETE',
                headers: {{'Authorization': 'Bearer {admin_token}'}}
            }})
        """)

    def test_create_user_duplicate_shows_error(self, page, admin_token):
        """创建同名用户应显示错误提示，模态框不关闭。"""
        # 先创建一个用户
        test_username = f"dupuser_{page.evaluate("Date.now()")}"
        page.evaluate(f"""
            fetch('/api/admin/users', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {admin_token}'
                }},
                body: JSON.stringify({{
                    username: '{test_username}',
                    password: 'testpass123',
                    is_active: true
                }})
            }})
        """)

        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("#users-tbody", timeout=5000)

        # 尝试创建同名用户
        page.click('button:has-text("创建用户")')
        page.wait_for_selector("#modal-overlay", timeout=3000)
        page.fill("#new-username", test_username)
        page.fill("#new-password", "anotherpass123")
        page.locator("#create-user-form button[type='submit']").click()

        # 应显示错误 alert
        page.wait_for_event("dialog", timeout=5000)
        page.on("dialog", lambda d: d.dismiss())  # 关闭弹窗

        # 模态框应仍可见（未关闭）
        assert page.locator("#modal-overlay").is_visible()

        # 清理
        page.evaluate(f"""
            fetch('/api/admin/users/{test_username}', {{
                method: 'DELETE',
                headers: {{'Authorization': 'Bearer {admin_token}'}}
            }})
        """)

    def test_delete_user_removes_from_table(self, page, admin_token):
        """删除用户后，该用户应从表格中消失。"""
        # 先创建一个待删除的用户
        test_username = f"deleteuser_{page.evaluate("Date.now()")}"
        page.evaluate(f"""
            fetch('/api/admin/users', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {admin_token}'
                }},
                body: JSON.stringify({{
                    username: '{test_username}',
                    password: 'testpass123',
                    is_active: true
                }})
            }})
        """)

        page.goto(f"{BASE_URL}/admin/users")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(f"td:has-text('{test_username}')", timeout=5000)

        # 触发删除（page.locator + click 会处理 confirm 弹窗）
        page.on("dialog", lambda d: d.accept())  # 自动确认删除确认框
        page.locator(f"button:has-text('删除'):near(td:has-text('{test_username}'))").click()

        # 等待表格刷新，用户应消失
        page.wait_for_selector(f"td:has-text('{test_username}')", state="hidden", timeout=5000)


# ==============================================================================
# Test: 分享页面
# ==============================================================================

class TestSharePage:
    """测试公开分享页面。"""

    def test_share_page_loads_for_nonexistent_id(self, page):
        """访问不存在的分享 ID 应显示错误提示而非崩溃。"""
        page.goto(f"{BASE_URL}/share/nonexistent-id-12345")
        page.wait_for_load_state("networkidle")

        # 应显示"Share not found"相关提示
        content = page.content()
        # 分享页有 error 处理逻辑
        assert "Share not found" in content or "error" in content.lower()

    def test_share_page_public_shares_link_in_index(self, page):
        """首页画廊中的分享卡片应正确链接到分享页。"""
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")

        # 如果有分享卡片，检查链接格式
        cards = page.locator("a.gallery-card")
        if cards.count() > 0:
            href = cards.first.get_attribute("href")
            assert href.startswith("/share/")
