"""Unit tests for dedicated ORCID regex validation and URI generation utility."""

from __future__ import annotations

import pytest

from phosphene.imi_wordpress.orcid_regex import (
    canonicalize_orcid,
    is_valid_orcid,
    to_orcid_uri,
)


@pytest.mark.parametrize(
    "candidate",
    [
        "0000-0002-1825-0097",
        "0000-0001-5109-3700",
        "0000-0002-1694-233X",
    ],
)
def test_is_valid_orcid_positive(candidate: str) -> None:
    assert is_valid_orcid(candidate) is True


@pytest.mark.parametrize(
    "candidate",
    [
        "not-an-orcid",
        "0000-0002-1825-009",
        "0000000218250097",
        "0000-0002-1825-009Y",
        "",
        "   ",
    ],
)
def test_is_valid_orcid_negative(candidate: str) -> None:
    assert is_valid_orcid(candidate) is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://orcid.org/0000-0002-1825-0097", "0000-0002-1825-0097"),
        ("http://orcid.org/0000-0002-1825-0097", "0000-0002-1825-0097"),
        ("  0000-0002-1825-0097  ", "0000-0002-1825-0097"),
    ],
)
def test_canonicalize_orcid(raw: str, expected: str) -> None:
    assert canonicalize_orcid(raw) == expected


def test_to_orcid_uri() -> None:
    assert to_orcid_uri("0000-0002-1825-0097") == "https://orcid.org/0000-0002-1825-0097"
    assert (
        to_orcid_uri("https://orcid.org/0000-0002-1825-0097")
        == "https://orcid.org/0000-0002-1825-0097"
    )
    assert to_orcid_uri("") == ""
