from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from zab_pkg_resolve.indexes import IndexManager
from zab_pkg_resolve.models import (
    CanonicalTarget,
    ConsumerPackageRecord,
    LockRecord,
    PackageCandidate,
    ResolvedPackage,
    ValidationResult,
)
from zab_pkg_resolve.providers import ResolverRegistry
from zab_pkg_resolve.store import ManagedStore


class ScenarioWorkspace:
    def __init__(self) -> None:
        self._tmp = TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.indexes = IndexManager()
        self.providers = ResolverRegistry()
        self.store = ManagedStore(self.base / "store")
        self.resolved_package: ResolvedPackage | None = None
        self.search_results: list[PackageCandidate] = []
        self.consumer_results: list[ConsumerPackageRecord] = []
        self.cache_keys: list[str] = []
        self.lock_records: list[LockRecord] = []
        self.validation_result: ValidationResult | None = None
        self.validation_policies: list[object] = []
        self.normalized_targets: dict[str, CanonicalTarget] = {}
        self.resolutions: list[tuple[str, str]] = []

    def close(self) -> None:
        self._tmp.cleanup()