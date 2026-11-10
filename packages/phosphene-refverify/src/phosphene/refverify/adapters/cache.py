"""File-backed verification cache with TTL + per-run override.

Keyed on a hash of (provider, kind, query params). Values are provider
responses as normalized CandidateRecord dicts. Cache lives at
~/.cache/refverify (redirected to /data per cache policy). Pure I/O,
no domain logic -- the domain never imports this.
"""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import suppress
from pathlib import Path

DEFAULT_TTL_SECONDS = 7 * 86400  # references don't rot fast; a week is plenty
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "refverify"


class FileCache:
    def __init__(
        self,
        cache_dir: Path | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        enabled: bool = True,
    ) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.ttl = ttl_seconds
        self.enabled = enabled

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> dict | None:
        if not self.enabled:
            return None
        p = self._path(key)
        if not p.exists():
            return None
        try:
            payload = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            return None  # corrupt entry behaves as a miss
        if payload.get("_cached_at", 0) + self.ttl < time.time():
            return None  # expired behaves as a miss; file left for inspection
        return payload.get("value")

    def set(self, key: str, value: dict) -> None:
        if not self.enabled:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with suppress(OSError):
            self._path(key).write_text(
                json.dumps({"_cached_at": time.time(), "value": value})
            )  # cache writes must never fail the run
