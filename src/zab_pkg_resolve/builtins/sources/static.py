from __future__ import annotations

from dataclasses import replace

from zab_pkg_resolve.interfaces.sources import SourceConfig
from zab_pkg_resolve.models import ResolvedPackage
from zab_pkg_resolve.targets import cache_key, normalize_target


class StaticSourceProvider:
    def __init__(
        self,
        name: str | SourceConfig,
        source_type: str = "static",
        location: str = "",
    ) -> None:
        if isinstance(name, SourceConfig):
            config = name
            self.name = config.name
            self.source_type = config.type
            self.location = config.location
        else:
            self.name = name
            self.source_type = source_type
            self.location = location
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