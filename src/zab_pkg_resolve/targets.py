from __future__ import annotations

import hashlib
import json

from zab_pkg_resolve.models import CanonicalTarget


def normalize_target(raw: str, *, default_ref: str = "main") -> CanonicalTarget:
    value = raw.strip()
    if value.startswith("gh:"):
        return _github_target(value.removeprefix("gh:"), default_ref)
    if value.startswith("github:"):
        return _github_target(value.removeprefix("github:"), default_ref)
    if value.startswith("https://") or value.startswith("http://"):
        return _http_target(value, default_ref)
    return CanonicalTarget("package", value, default_ref)


def cache_key(target: CanonicalTarget) -> str:
    payload = json.dumps(target.descriptor(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _github_target(owner_repo: str, default_ref: str) -> CanonicalTarget:
    return CanonicalTarget("git", f"https://github.com/{owner_repo}.git", default_ref)


def _http_target(value: str, default_ref: str) -> CanonicalTarget:
    url, separator, ref = value.partition("#")
    return CanonicalTarget("git", url, ref if separator else default_ref)