from __future__ import annotations

import fnmatch
from dataclasses import replace

from zab_pkg_resolve.models import CanonicalTarget, IndexSource, PackageCandidate, ResolvedPackage
from zab_pkg_resolve.targets import cache_key, normalize_target


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
            return
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
            self._replace_artifact_target(packages, package_id, target)

    def search(self, pattern: str) -> list[PackageCandidate]:
        self._ensure_active_sources()
        results: list[PackageCandidate] = []
        for source_name in self.active_sources:
            results.extend(self._matching_candidates(source_name, pattern))
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

    def _ensure_active_sources(self) -> None:
        if not self.active_sources:
            self.load()

    def _matching_candidates(self, source_name: str, pattern: str) -> list[PackageCandidate]:
        self.queries.append(source_name)
        return [candidate for candidate in self.indexes.get(source_name, {}).values() if fnmatch.fnmatch(candidate.id, pattern)]

    def _replace_artifact_target(
        self,
        packages: dict[str, PackageCandidate],
        package_id: str,
        target: CanonicalTarget,
    ) -> None:
        if package_id not in packages:
            return
        packages[package_id] = replace(packages[package_id], target=target)