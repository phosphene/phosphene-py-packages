"""Tests for package version advertising and metadata.

@dft
- A1 (pure-io-separation): pure unit tests validating version constants and user agents.
- A5 (mock-doubles): no I/O needed.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout

from phosphene.imi_wordpress import __version__, __version_info__
from phosphene.imi_wordpress.client import USER_AGENT as CLIENT_UA
from phosphene.imi_wordpress.db_client import USER_AGENT as DB_CLIENT_UA
from phosphene.imi_wordpress.foundry_cli import main as cli_main
from phosphene.imi_wordpress.parity_harness import USER_AGENT as HARNESS_UA


def test_package_version_format() -> None:
    """Package version should follow semantic versioning."""
    assert __version__ == "1.0.0"
    assert __version_info__ == (1, 0, 0)


def test_user_agents_advertise_version() -> None:
    """All HTTP client User-Agents must include package name and version."""
    assert CLIENT_UA == "UrllibWPClient/1.0.0"
    assert DB_CLIENT_UA == "WPEngineDBClient/1.0.0"
    assert HARNESS_UA == "WordPressDualHarness/1.0.0"


def test_cli_version_flag(monkeypatch: object) -> None:
    """CLI --version flag prints package version."""
    import sys

    monkeypatch.setattr(sys, "argv", ["foundry_cli", "--version"])
    buf = io.StringIO()
    with redirect_stdout(buf):
        ret = cli_main()

    assert ret == 0
    assert buf.getvalue().strip() == "imi-wordpress 1.0.0"
