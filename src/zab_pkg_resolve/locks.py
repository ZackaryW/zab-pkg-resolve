from __future__ import annotations

from zab_pkg_resolve.models import LockRecord
from zab_pkg_resolve.targets import normalize_target


def write_lock_records(resolutions: list[tuple[str, str]]) -> list[LockRecord]:
    return [LockRecord(target=normalize_target(target), revision=revision) for target, revision in resolutions]