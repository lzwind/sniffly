"""
Playwright E2E 测试配置。

本模块通过 pytest-playwright 提供浏览器测试环境。
运行测试前需要安装浏览器：
    playwright install chromium

依赖：
    pip install pytest-playwright

启动被测服务（任选其一）：
    # Docker Compose
    cd sniffly-server && docker-compose up -d

    # 或本地 uvicorn（需提前启动 MongoDB 和 Redis）
    uvicorn app.main:app --host 0.0.0.0 --port 8080

运行测试：
    BASE_URL=http://localhost:8080 pytest sniffly-server/tests/e2e -v
"""

import os
import pytest


def pytest_configure(config):
    """注册自定义标记。"""
    config.addinivalue_line(
        "markers", "e2e: 端到端浏览器测试，需要服务运行"
    )


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """为所有浏览器上下文设置默认参数。"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
    }
