"""Shared fixtures for integration tests — programmatic WP setup, no shell scripts.

Session-scoped fixture starts WordPress, installs Elementor, generates
app password, and provides REST client + DB client + parity harness to
all integration tests.
"""

from __future__ import annotations

import os

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.config import WPConfig
from phosphene.imi_wordpress.db_client import WPEngineDBClient
from phosphene.imi_wordpress.parity_harness import WordPressDualHarness
from phosphene.imi_wordpress.test_setup import WPTestEnvironment, setup_wordpress


@pytest.fixture(scope="session")
def wp_env() -> WPTestEnvironment:
    """Set up WordPress test environment (session-scoped).

    Runs once per test session. If WP_INTEGRATION is not set, skips.
    Otherwise: finds the Docker container, installs WP + Elementor,
    generates app password, verifies mu-plugin gateway.
    """
    if not os.environ.get("WP_INTEGRATION"):
        pytest.skip("WP_INTEGRATION not set")
    return setup_wordpress()


@pytest.fixture(scope="session")
def rest_client(wp_env: WPTestEnvironment) -> UrllibWPClient:
    """REST API client connected to the Docker WordPress."""
    config = WPConfig(
        url=wp_env.url,
        username=wp_env.username,
        app_password=wp_env.app_password,
    )
    return UrllibWPClient(config)


@pytest.fixture(scope="session")
def db_client(wp_env: WPTestEnvironment) -> WPEngineDBClient:
    """DB gateway client connected to the Docker WordPress."""
    return WPEngineDBClient(wp_env.url, wp_env.db_token)


@pytest.fixture(scope="session")
def harness(
    rest_client: UrllibWPClient,
    db_client: WPEngineDBClient,
) -> WordPressDualHarness:
    """Dual-layer parity harness with real clients."""
    return WordPressDualHarness(rest_client, db_client)
