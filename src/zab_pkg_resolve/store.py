from __future__ import annotations

import shutil
from pathlib import Path

from zab_pkg_resolve.models import ConsumerPackageRecord, InstallResult, InstalledPackageRecord, ResolvedPackage


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
        self._cache_path(artifact_hash).mkdir(parents=True, exist_ok=True)

    def install(self, package: ResolvedPackage) -> InstallResult:
        used_cache = package.artifact_hash in self.cache_entries
        self.add_cache_entry(package.artifact_hash)
        record = self._write_install_record(package)
        self.last_install_result = InstallResult(record=record, used_cache=used_cache)
        return self.last_install_result

    def uninstall(self, package_id: str) -> None:
        record = self.records[package_id]
        self._remove_path(record.install_path)
        record.active = False

    def active_record(self, package_id: str) -> InstalledPackageRecord | None:
        record = self.records.get(package_id)
        if record is None or not record.active:
            return None
        return record

    def consumer_records(self) -> list[ConsumerPackageRecord]:
        return [self._consumer_record(record) for record in self.records.values() if record.active and not record.disabled]

    def mark_disabled(self, package_id: str) -> None:
        self.records[package_id].disabled = True

    def garbage_collect_cache(self) -> None:
        referenced = {record.artifact_hash for record in self.records.values() if record.active}
        for artifact_hash in list(self.cache_entries - referenced):
            self.cache_entries.remove(artifact_hash)
            self._remove_path(self._cache_path(artifact_hash))

    def start_failed_install(self, package: ResolvedPackage) -> None:
        self._transaction_path(package.id).mkdir(parents=True, exist_ok=True)

    def recover_install(self, package_id: str) -> None:
        self.records.pop(package_id, None)
        self._remove_path(self._transaction_path(package_id))
        self.recovery_report = f"cleaned failed install for {package_id}"

    def commit_install(self, package: ResolvedPackage) -> InstallResult:
        return self.install(package)

    def start_failed_uninstall(self, package_id: str) -> None:
        self._transaction_path(package_id).mkdir(parents=True, exist_ok=True)

    def recover_uninstall(self, package_id: str) -> None:
        record = self.records[package_id]
        self._restore_record_path(record)
        self._remove_path(self._transaction_path(package_id))
        self.recovery_report = f"restored record and install directory for {package_id}"

    def _write_install_record(self, package: ResolvedPackage) -> InstalledPackageRecord:
        package_dir = self.install_dir / package.id
        package_dir.mkdir(parents=True, exist_ok=True)
        record = self._record_for(package, package_dir)
        self.records[package.id] = record
        return record

    def _record_for(self, package: ResolvedPackage, install_path: Path) -> InstalledPackageRecord:
        return InstalledPackageRecord(
            id=package.id,
            install_path=install_path,
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

    def _consumer_record(self, record: InstalledPackageRecord) -> ConsumerPackageRecord:
        return ConsumerPackageRecord(
            id=record.id,
            installed_path=record.install_path,
            entrypoint=record.entrypoint,
            capabilities=tuple(record.capabilities),
        )

    def _restore_record_path(self, record: InstalledPackageRecord) -> None:
        record.active = record.install_path.exists()
        if record.active:
            return
        record.install_path.mkdir(parents=True, exist_ok=True)
        record.active = True

    def _cache_path(self, artifact_hash: str) -> Path:
        return self.cache_dir / artifact_hash

    def _transaction_path(self, package_id: str) -> Path:
        return self.transaction_dir / package_id

    def _remove_path(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)