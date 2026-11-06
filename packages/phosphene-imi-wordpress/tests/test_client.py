"""Tests for UrllibWPClient."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from phosphene.imi_wordpress.client import UrllibWPClient
from phosphene.imi_wordpress.config import WPConfig


@pytest.fixture
def wp_config() -> WPConfig:
    """Provide a test WPConfig."""
    return WPConfig(
        url="https://example.com",
        username="test",
        app_password="test-pass",
    )


@pytest.fixture
def client(wp_config: WPConfig) -> UrllibWPClient:
    """Provide a configured UrllibWPClient."""
    return UrllibWPClient(wp_config)


class TestCreatePost:
    """Tests for UrllibWPClient.create_post."""

    @patch("urllib.request.urlopen")
    def test_create_post_sends_correct_json(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """create_post sends JSON body matching the data argument."""
        response_data = {"id": 1, "title": {"rendered": "Hello"}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        data = {"title": "Hello", "status": "draft", "content": "Body text"}
        result = client.create_post("posts", data)

        # Verify the request body matches our data
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        sent_body = json.loads(req.data.decode("utf-8"))
        assert sent_body == data
        assert result == response_data

    @patch("urllib.request.urlopen")
    def test_create_post_sets_auth_header(
        self, mock_urlopen: MagicMock, client: UrllibWPClient, wp_config: WPConfig
    ) -> None:
        """create_post sets Authorization header with correct Basic base64 value."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": 1}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.create_post("posts", {"title": "Test"})

        call_args = mock_urlopen.call_args
        req = call_args[0][0]

        expected_creds = f"{wp_config.username}:{wp_config.app_password}"
        expected_encoded = base64.b64encode(expected_creds.encode()).decode()
        expected_header = f"Basic {expected_encoded}"

        assert req.get_header("Authorization") == expected_header
        assert req.get_header("Content-type") == "application/json"

    @patch("urllib.request.urlopen")
    def test_create_post_targets_correct_endpoint(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """create_post POSTs to /wp-json/wp/v2/<post_type>."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"id": 1}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        client.create_post("imi_registry", {"title": "Scholar"})

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://example.com/wp-json/wp/v2/imi_registry"
        assert req.method == "POST"

    @patch("urllib.request.urlopen")
    def test_create_post_returns_error_on_exception(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """create_post returns error dict on network failure — never raises."""
        mock_urlopen.side_effect = Exception("connection refused")

        result = client.create_post("posts", {"title": "Test"})

        assert result["error"] is True
        assert "connection refused" in result["message"]


class TestPostExists:
    """Tests for UrllibWPClient.post_exists."""

    @patch("urllib.request.urlopen")
    def test_post_exists_returns_true_when_found(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """post_exists returns True when the API returns a non-empty list."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([{"slug": "test-slug"}]).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert client.post_exists("posts", "test-slug") is True

    @patch("urllib.request.urlopen")
    def test_post_exists_returns_false_when_empty(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """post_exists returns False when the API returns an empty list."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([]).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert client.post_exists("posts", "nonexistent") is False

    @patch("urllib.request.urlopen")
    def test_post_exists_returns_false_on_error(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """post_exists returns False on exception — never raises."""
        mock_urlopen.side_effect = Exception("timeout")

        assert client.post_exists("posts", "any-slug") is False


class TestPostUrl:
    """Tests for UrllibWPClient.post_url."""

    def test_post_url_format(self, client: UrllibWPClient) -> None:
        """post_url builds the correct REST API query URL."""
        url = client.post_url("posts", "hello-world")
        assert url == "https://example.com/wp-json/wp/v2/posts?slug=hello-world"

    def test_post_url_with_custom_post_type(self, client: UrllibWPClient) -> None:
        """post_url works with custom post types."""
        url = client.post_url("imi_registry", "jane-smith")
        assert url == "https://example.com/wp-json/wp/v2/imi_registry?slug=jane-smith"


class TestUpdatePost:
    """Tests for UrllibWPClient.update_post."""

    @patch("urllib.request.urlopen")
    def test_update_post_sends_correct_payload(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """update_post sends POST to /wp-json/wp/v2/<post_type>/<id>."""
        response_data = {"id": 42, "meta": {"reg_doi_status": "active"}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(response_data).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        payload = {"meta": {"reg_doi_status": "active"}}
        result = client.update_post("imi_registry", 42, payload)

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://example.com/wp-json/wp/v2/imi_registry/42"
        assert req.method == "POST"
        sent_body = json.loads(req.data.decode("utf-8"))
        assert sent_body == payload
        assert result == response_data

    @patch("urllib.request.urlopen")
    def test_update_post_returns_error_on_exception(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """update_post returns error dict on failure — never raises."""
        mock_urlopen.side_effect = Exception("network error")
        result = client.update_post("imi_registry", 42, {"title": "Update"})
        assert result["error"] is True
        assert "network error" in result["message"]


class TestDeletePost:
    """Tests for UrllibWPClient.delete_post."""

    @patch("urllib.request.urlopen")
    def test_delete_post_by_id_calls_force_delete(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """delete_post by int sends DELETE /wp-json/wp/v2/<type>/<id>?force=true."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"deleted": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.delete_post(42, post_type="imi_registry")
        assert result == {"deleted": True}

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://example.com/wp-json/wp/v2/imi_registry/42?force=true"
        assert req.method == "DELETE"

    @patch("urllib.request.urlopen")
    def test_delete_post_by_url_with_query_param(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """delete_post parses ?p=102 from URL and deletes post 102."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"deleted": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = client.delete_post("https://example.com/?p=102", post_type="imi_registry")
        assert result == {"deleted": True}

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://example.com/wp-json/wp/v2/imi_registry/102?force=true"
        assert req.method == "DELETE"

    @patch("urllib.request.urlopen")
    def test_delete_post_returns_error_on_exception(
        self, mock_urlopen: MagicMock, client: UrllibWPClient
    ) -> None:
        """delete_post returns error dict on exception — never raises."""
        mock_urlopen.side_effect = Exception("forbidden")
        result = client.delete_post(42, post_type="imi_registry")
        assert result["error"] is True
        assert "forbidden" in result["message"]
