"""Cache unit tests — file-backed, TTL, override. No network."""

from __future__ import annotations

from pathlib import Path

from phosphene.refverify.adapters.cache import FileCache


def test_set_then_get_roundtrip(tmp_path: Path) -> None:
    cache = FileCache(cache_dir=tmp_path)
    cache.set("k1", {"title": "x"})
    assert cache.get("k1") == {"title": "x"}


def test_miss_returns_none(tmp_path: Path) -> None:
    cache = FileCache(cache_dir=tmp_path)
    assert cache.get("missing") is None


def test_disabled_bypasses(tmp_path: Path) -> None:
    cache = FileCache(cache_dir=tmp_path, enabled=False)
    cache.set("k", {"a": 1})
    assert cache.get("k") is None


def test_ttl_expiry(tmp_path: Path) -> None:
    cache = FileCache(cache_dir=tmp_path, ttl_seconds=0)
    cache.set("k", {"a": 1})
    assert cache.get("k") is None  # ttl 0 → immediately stale


def test_corrupt_entry_behaves_as_miss(tmp_path: Path) -> None:
    cache = FileCache(cache_dir=tmp_path)
    cache.set("k", {"a": 1})
    cache._path("k").write_text("{not json")
    assert cache.get("k") is None
