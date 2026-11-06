"""Unit tests for dedicated DOI regex parsing and protocol stripping utility."""

from __future__ import annotations

import pytest

from phosphene.imi_wordpress.doi_regex import (
    is_valid_doi,
    split_doi,
    strip_protocol_prefix,
)


@pytest.mark.parametrize(
    "candidate",
    [
        "10.67767/imi.2026.001",
        "10.1000/182",
        "10.1038/nphys1170",
        "10.1002/(SICI)1097-0142(19980101)82:1<4::AID-CNCR1>3.0.CO;2-H",
    ],
)
def test_is_valid_doi_positive(candidate: str) -> None:
    assert is_valid_doi(candidate) is True


@pytest.mark.parametrize(
    "candidate",
    [
        "not-a-doi",
        "10.123/",
        "/suffix-only",
        "9.67767/invalid",
        "10.12/s",
        "",
        "   ",
    ],
)
def test_is_valid_doi_negative(candidate: str) -> None:
    assert is_valid_doi(candidate) is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://doi.org/10.67767/imi.2026.001", "10.67767/imi.2026.001"),
        ("http://doi.org/10.67767/imi.2026.001", "10.67767/imi.2026.001"),
        ("https://dx.doi.org/10.67767/imi.2026.001", "10.67767/imi.2026.001"),
        ("doi:10.67767/imi.2026.001", "10.67767/imi.2026.001"),
        ("  https://doi.org/10.67767/imi.2026.001  ", "10.67767/imi.2026.001"),
    ],
)
def test_strip_protocol_prefix(raw: str, expected: str) -> None:
    assert strip_protocol_prefix(raw) == expected


def test_split_doi_valid() -> None:
    res = split_doi("https://doi.org/10.67767/imi.2026.042")
    assert res is not None
    prefix, suffix = res
    assert prefix == "10.67767"
    assert suffix == "imi.2026.042"


def test_split_doi_invalid() -> None:
    assert split_doi("invalid-doi") is None
