"""Tests for UrllibWPClient error recovery — timeout, network failure, bad responses."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.config import WPConfig


@pytest.fixture
def client(monkeypatch) -> UrllibWPClient:
    monkeypatch.setenv("WP_URL", "https://example.com")
    monkeypatch.setenv("WP_USERNAME", "user")
    monkeypatch.setenv("WP_APP_PASSWORD", "pass")
    return UrllibWPClient(WPConfig.from_env())


class TestCreatePostErrorRecovery:
    def test_timeout_returns_error_dict_not_raises(self, client):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert isinstance(result, dict)
        assert result.get("error") or "id" not in result

    def test_connection_refused_returns_error_dict(self, client):
        err = urllib.error.URLError("Connection refused")
        with patch("urllib.request.urlopen", side_effect=err):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert isinstance(result, dict)
        assert result.get("error") or "id" not in result

    def test_http_500_returns_error_dict(self, client):
        http_err = urllib.error.HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs=MagicMock(),
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert isinstance(result, dict)
        assert result.get("error") or "id" not in result

    def test_http_429_returns_error_dict(self, client):
        http_err = urllib.error.HTTPError(
            url="https://example.com",
            code=429,
            msg="Too Many Requests",
            hdrs=MagicMock(),
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert isinstance(result, dict)
        assert result.get("error") or "id" not in result

    def test_malformed_json_returns_error_dict(self, client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"not valid json {"
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert isinstance(result, dict)
        assert result.get("error") or "id" not in result

    def test_successful_create_returns_post_dict(self, client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({"id": 42, "slug": "test"}).encode()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.create_post("imi_registry", {"title": "Test"})
        assert result["id"] == 42
        assert result["slug"] == "test"


class TestPostExistsErrorRecovery:
    def test_timeout_returns_false_not_raises(self, client):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = client.post_exists("imi_registry", "some-slug")
        assert result is False

    def test_network_error_returns_false(self, client):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            result = client.post_exists("imi_registry", "some-slug")
        assert result is False

    def test_empty_list_returns_false(self, client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b"[]"
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.post_exists("imi_registry", "missing-slug")
        assert result is False

    def test_non_empty_list_returns_true(self, client):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps([{"id": 1, "slug": "found"}]).encode()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.post_exists("imi_registry", "found")
        assert result is True
