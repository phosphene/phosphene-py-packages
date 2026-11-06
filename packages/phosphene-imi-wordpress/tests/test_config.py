"""Tests for WPConfig."""

from __future__ import annotations

import pytest

from phosphene.imi_wordpress.config import WPConfig


class TestWPConfig:
    """WPConfig construction and validation tests."""

    def test_missing_env_var_raises_with_var_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing env vars produce EnvironmentError naming the missing variable."""
        monkeypatch.delenv("WP_URL", raising=False)
        monkeypatch.delenv("WP_USERNAME", raising=False)
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(EnvironmentError, match="WP_URL"):
            WPConfig.from_env()

    def test_partial_missing_names_specific_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When only some vars are missing, the error names them specifically."""
        monkeypatch.setenv("WP_URL", "https://example.com")
        monkeypatch.setenv("WP_USERNAME", "admin")
        monkeypatch.delenv("WP_APP_PASSWORD", raising=False)

        with pytest.raises(EnvironmentError, match="WP_APP_PASSWORD"):
            WPConfig.from_env()

    def test_all_vars_present_constructs_correctly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All required env vars present produces a valid WPConfig."""
        monkeypatch.setenv("WP_URL", "https://independentmediainstitute.org")
        monkeypatch.setenv("WP_USERNAME", "flow@ind.media")
        monkeypatch.setenv("WP_APP_PASSWORD", "secret-password")

        config = WPConfig.from_env()

        assert config.url == "https://independentmediainstitute.org"
        assert config.username == "flow@ind.media"
        assert config.app_password == "secret-password"

    def test_config_is_frozen(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """WPConfig instances are immutable."""
        monkeypatch.setenv("WP_URL", "https://example.com")
        monkeypatch.setenv("WP_USERNAME", "admin")
        monkeypatch.setenv("WP_APP_PASSWORD", "pass")

        config = WPConfig.from_env()
        with pytest.raises(AttributeError):
            config.url = "https://other.com"  # type: ignore[misc]
