"""Tests for WPTestClient — WordPress REST API test client with mocked urllib."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from phosphene.imi_wordpress.testing.wp_test_client import WPResponse, WPTestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(body: str | bytes = "{}", status: int = 200) -> MagicMock:
    """Create a mock urllib response context manager."""
    if isinstance(body, str):
        body = body.encode("utf-8")
    resp = MagicMock()
    resp.read.return_value = body
    resp.status = status
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


@pytest.fixture
def client() -> WPTestClient:
    """Provide a test WPTestClient instance."""
    return WPTestClient(
        url="https://staging.example.com",
        username="testuser",
        app_password="xxxx yyyy zzzz",
        timeout=10,
    )


# ---------------------------------------------------------------------------
# WPResponse dataclass
# ---------------------------------------------------------------------------


class TestWPResponse:
    """Tests for WPResponse frozen dataclass."""

    def test_fields_accessible(self) -> None:
        r = WPResponse(
            status=200,
            data={"id": 1},
            ok=True,
            error_code=None,
            error_message=None,
            raw_body='{"id":1}',
        )
        assert r.status == 200
        assert r.data == {"id": 1}
        assert r.ok is True
        assert r.raw_body == '{"id":1}'

    def test_frozen(self) -> None:
        r = WPResponse(
            status=200, data=None, ok=True, error_code=None, error_message=None, raw_body=""
        )
        with pytest.raises(AttributeError):
            r.status = 500  # type: ignore[misc]

    def test_error_fields(self) -> None:
        r = WPResponse(
            status=403,
            data=None,
            ok=False,
            error_code="forbidden",
            error_message="No access",
            raw_body="",
        )
        assert r.error_code == "forbidden"
        assert r.error_message == "No access"
        assert r.ok is False


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------


class TestAuth:
    """Tests for authentication header construction."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_auth_header_is_base64_encoded(
        self, mock_urlopen: MagicMock, client: WPTestClient
    ) -> None:
        mock_urlopen.return_value = _mock_response('{"id": 1}', 200)
        client.get("/wp-json/wp/v2/posts")

        req = mock_urlopen.call_args[0][0]
        auth = req.get_header("Authorization")
        assert auth is not None
        assert auth.startswith("Basic ")
        decoded = base64.b64decode(auth.split(" ", 1)[1]).decode()
        assert decoded == "testuser:xxxx yyyy zzzz"


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for GET requests."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_get_success(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response('{"id": 42, "title": "Test"}', 200)
        resp = client.get("/wp-json/wp/v2/posts/42")

        assert resp.ok is True
        assert resp.status == 200
        assert resp.data == {"id": 42, "title": "Test"}

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_get_sets_method(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("{}", 200)
        client.get("/wp-json/test")
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "GET"


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


class TestPost:
    """Tests for POST requests."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_post_success(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response('{"id": 99}', 201)
        resp = client.post("/wp-json/wp/v2/posts", data={"title": "New"})
        assert resp.status == 201
        assert resp.data == {"id": 99}
        # Verify body was sent
        req = mock_urlopen.call_args[0][0]
        assert req.data is not None
        sent = json.loads(req.data.decode())
        assert sent["title"] == "New"

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_post_sets_method(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("{}", 200)
        client.post("/wp-json/test", data={})
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "POST"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for DELETE requests."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_delete_success(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response('{"deleted": true}', 200)
        resp = client.delete("/wp-json/wp/v2/posts/42")
        assert resp.ok is True
        assert resp.data == {"deleted": True}

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_delete_sets_method(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("{}", 200)
        client.delete("/wp-json/test")
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "DELETE"


# ---------------------------------------------------------------------------
# OPTIONS
# ---------------------------------------------------------------------------


class TestOptions:
    """Tests for OPTIONS requests."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_options_sets_method(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("{}", 200)
        client.options("/wp-json/test")
        req = mock_urlopen.call_args[0][0]
        assert req.get_method() == "OPTIONS"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for HTTP and network error handling."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_http_error_parsed(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        body = json.dumps({"code": "rest_forbidden", "message": "Not allowed"}).encode()
        mock_urlopen.side_effect = HTTPError(
            url="https://staging.example.com/wp-json/test",
            code=403,
            msg="Forbidden",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=BytesIO(body),
        )
        resp = client.get("/wp-json/test")
        assert resp.ok is False
        assert resp.status == 403
        assert resp.error_code == "rest_forbidden"
        assert resp.error_message == "Not allowed"

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_network_error(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.side_effect = URLError("Connection refused")
        resp = client.get("/wp-json/test")
        assert resp.ok is False
        assert resp.status == 0
        assert resp.error_code == "network_error"
        assert "Connection refused" in (resp.error_message or "")

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_non_json_response(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("<html>Not JSON</html>", 200)
        resp = client.get("/wp-json/test")
        assert resp.ok is True
        assert resp.data is None
        assert resp.raw_body == "<html>Not JSON</html>"


# ---------------------------------------------------------------------------
# fetch_html
# ---------------------------------------------------------------------------


class TestFetchHtml:
    """Tests for fetch_html (unauthenticated HTML fetch)."""

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_fetch_html_returns_html(self, mock_urlopen: MagicMock, client: WPTestClient) -> None:
        mock_urlopen.return_value = _mock_response("<html><body>Hello</body></html>", 200)
        html = client.fetch_html("https://example.com/page")
        assert "Hello" in html

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_fetch_html_no_auth_header(
        self, mock_urlopen: MagicMock, client: WPTestClient
    ) -> None:
        mock_urlopen.return_value = _mock_response("<html></html>", 200)
        client.fetch_html("https://example.com/page")
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") is None

    @patch("phosphene.imi_wordpress.testing.wp_test_client.urlopen")
    def test_fetch_html_error_returns_empty(
        self, mock_urlopen: MagicMock, client: WPTestClient
    ) -> None:
        mock_urlopen.side_effect = URLError("Timeout")
        html = client.fetch_html("https://example.com/page")
        assert html == ""
