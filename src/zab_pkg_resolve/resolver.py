from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from zab_pkg_resolve.models import (
    CanonicalTarget,
    ConsumerPackageRecord,
    IndexSource,
    InstallResult,
    InstalledPackageRecord,
    LockRecord,
    PackageCandidate,
    ResolvedPackage,
    ValidationResult,
)


def normalize_target(raw: str, *, default_ref: str = "main") -> CanonicalTarget:
    value = raw.strip()
    if value.startswith("gh:"):
        owner_repo = value.removeprefix("gh:")
        return CanonicalTarget("git", f"https://github.com/{owner_repo}.git", default_ref)
    if value.startswith("github:"):
        owner_repo = value.removeprefix("github:")
        return CanonicalTarget("git", f"https://github.com/{owner_repo}.git", default_ref)
    if value.startswith("https://") or value.startswith("http://"):
        url, separator, ref = value.partition("#")
        return CanonicalTarget("git", url, ref if separator else default_ref)
    return CanonicalTarget("package", value, default_ref)


def cache_key(target: CanonicalTarget) -> str:
    payload = json.dumps(target.descriptor(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SourceProvider(Protocol):
    name: str

    def can_resolve(self, target: str) -> bool: ...
    def resolve(self, target: str) -> ResolvedPackage: ...


class StaticSourceProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self._packages: dict[str, ResolvedPackage] = {}
        self.resolved_targets: list[str] = []

    def add(self, target: str, package_id: str | None = None) -> None:
        normalized = normalize_target(target)
        self._packages[target] = ResolvedPackage(
            id=package_id or target.split(":", 1)[-1],
            target=normalized,
            provider=self.name,
            revision=cache_key(normalized)[:12],
            artifact_hash=cache_key(normalized),
        )

    def can_resolve(self, target: str) -> bool:
        return target in self._packages

    def resolve(self, target: str) -> ResolvedPackage:
        self.resolved_targets.append(target)
        return replace(self._packages[target])


class IndexManager:
    def __init__(self) -> None:
        self.user_sources: dict[str, IndexSource] = {}
        self.project_sources: dict[str, IndexSource] = {}
        self.active_sources: dict[str, IndexSource] = {}
        self.queries: list[str] = []
        self.indexes: dict[str, dict[str, PackageCandidate]] = {}

    def add_source(self, name: str, location: str, level: str) -> None:
        source = IndexSource(name=name, location=location, level=level)
        if level == "project":
            self.project_sources[name] = source
        else:
            self.user_sources[name] = source

    def load(self) -> dict[str, IndexSource]:
        self.active_sources = {**self.user_sources, **self.project_sources}
        return self.active_sources

    def was_queried(self, name: str) -> bool:
        return name in self.queries

    def add_package(self, source: str, package_id: str, version: str) -> None:
        target = normalize_target(f"github:example/{package_id.replace('.', '-')}")
        self.indexes.setdefault(source, {})[package_id] = PackageCandidate(
            id=package_id,
            version=version,
            source=source,
            target=target,
        )

    def set_git_artifact(self, package_id: str, git_url: str, ref: str) -> None:
        target = CanonicalTarget("git", git_url, ref)
        for packages in self.indexes.values():
            if package_id in packages:
                existing = packages[package_id]
                packages[package_id] = replace(existing, target=target)

    def search(self, pattern: str) -> list[PackageCandidate]:
        if not self.active_sources:
            self.load()
        results: list[PackageCandidate] = []
        for source_name in self.active_sources:
            self.queries.append(source_name)
            for candidate in self.indexes.get(source_name, {}).values():
                if fnmatch.fnmatch(candidate.id, pattern):
                    results.append(candidate)
        return results

    def resolve(self, package_id: str, source: str) -> ResolvedPackage:
        candidate = self.indexes[source][package_id]
        return ResolvedPackage(
            id=candidate.id,
            source=source,
            target=candidate.target,
            revision=cache_key(candidate.target)[:12],
            artifact_hash=cache_key(candidate.target),
        )


class ResolverRegistry:
    def __init__(self) -> None:
        self.providers: dict[str, SourceProvider] = {}
        self.last_provider: str | None = None

    def register(self, provider: SourceProvider) -> None:
        self.providers[provider.name] = provider

    def resolve(self, target: str) -> ResolvedPackage:
        for provider in self.providers.values():
            if provider.can_resolve(target):
                self.last_provider = provider.name
                return provider.resolve(target)
        raise KeyError(target)


class ManagedStore:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.cache_dir = base / "cache"
        self.install_dir = base / "installed"
        self.transaction_dir = base / "transactions"
        self.records: dict[str, InstalledPackageRecord] = {}
        self.cache_entries: set[str] = set()
        self.last_install_result: InstallResult | None = None
        self.recovery_report = ""
        self.base.mkdir(parents=True, exist_ok=True)

    def add_cache_entry(self, artifact_hash: str) -> None:
        self.cache_entries.add(artifact_hash)
        (self.cache_dir / artifact_hash).mkdir(parents=True, exist_ok=True)

    def install(self, package: ResolvedPackage) -> InstallResult:
        used_cache = package.artifact_hash in self.cache_entries
        self.add_cache_entry(package.artifact_hash)
        package_dir = self.install_dir / package.id
        package_dir.mkdir(parents=True, exist_ok=True)
        record = InstalledPackageRecord(
            id=package.id,
            install_path=package_dir,
            artifact_hash=package.artifact_hash,
            entrypoint=package.entrypoint,
            capabilities=list(package.capabilities),
            active=True,
            source_metadata={
                "source": package.source,
                "provider": package.provider,
                "revision": package.revision,
                "target": package.target.descriptor(),
            },
        )
        self.records[package.id] = record
        self.last_install_result = InstallResult(record=record, used_cache=used_cache)
        return self.last_install_result

    def uninstall(self, package_id: str) -> None:
        record = self.records[package_id]
        if record.install_path.exists():
            shutil.rmtree(record.install_path)
        record.active = False

    def active_record(self, package_id: str) -> InstalledPackageRecord | None:
        record = self.records.get(package_id)
        if record is None or not record.active:
            return None
        return record

    def consumer_records(self) -> list[ConsumerPackageRecord]:
        records: list[ConsumerPackageRecord] = []
        for record in self.records.values():
            if not record.active or record.disabled:
                continue
            records.append(
                ConsumerPackageRecord(
                    id=record.id,
                    installed_path=record.install_path,
                    entrypoint=record.entrypoint,
                    capabilities=tuple(record.capabilities),
                )
            )
        return records

    def mark_disabled(self, package_id: str) -> None:
        self.records[package_id].disabled = True

    def garbage_collect_cache(self) -> None:
        referenced = {record.artifact_hash for record in self.records.values() if record.active}
        for artifact_hash in list(self.cache_entries):
            if artifact_hash in referenced:
                continue
            self.cache_entries.remove(artifact_hash)
            shutil.rmtree(self.cache_dir / artifact_hash, ignore_errors=True)

    def start_failed_install(self, package: ResolvedPackage) -> None:
        path = self.transaction_dir / package.id
        path.mkdir(parents=True, exist_ok=True)

    def recover_install(self, package_id: str) -> None:
        self.records.pop(package_id, None)
        shutil.rmtree(self.transaction_dir / package_id, ignore_errors=True)
        self.recovery_report = f"cleaned failed install for {package_id}"

    def commit_install(self, package: ResolvedPackage) -> InstallResult:
        return self.install(package)

    def start_failed_uninstall(self, package_id: str) -> None:
        (self.transaction_dir / package_id).mkdir(parents=True, exist_ok=True)

    def recover_uninstall(self, package_id: str) -> None:
        record = self.records[package_id]
        record.active = record.install_path.exists()
        if not record.active:
            record.install_path.mkdir(parents=True, exist_ok=True)
            record.active = True
        shutil.rmtree(self.transaction_dir / package_id, ignore_errors=True)
        self.recovery_report = f"restored record and install directory for {package_id}"


def write_lock_records(resolutions: list[tuple[str, str]]) -> list[LockRecord]:
    return [LockRecord(target=normalize_target(target), revision=revision) for target, revision in resolutions]


class RequiredFieldPolicy:
    def __init__(self, field: str) -> None:
        self.field = field

    def validate(self, package: ResolvedPackage) -> ValidationResult:
        if self.field not in package.manifest or package.manifest.get(self.field) in {None, ""}:
            return ValidationResult(False, "manifest-invalid")
        return ValidationResult(True)


class PythonVersionPolicy:
    def __init__(self, active_version: str) -> None:
        self.active_version = active_version

    def validate(self, package: ResolvedPackage) -> ValidationResult:
        requirement = package.requires_python
        if requirement is None or not requirement.startswith(">="):
            return ValidationResult(True)
        required = tuple(int(part) for part in requirement.removeprefix(">=").split(".")[:2])
        active = tuple(int(part) for part in self.active_version.split(".")[:2])
        if active < required:
            return ValidationResult(False, "python-version-unsupported")
        return ValidationResult(True)


def run_validation(package: ResolvedPackage, policies: list[object]) -> ValidationResult:
    for policy in policies:
        result = policy.validate(package)
        if not result.ok:
            return result
    return ValidationResult(True)


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