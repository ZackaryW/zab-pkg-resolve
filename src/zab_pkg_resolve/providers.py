from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from zab_pkg_resolve.models import ResolvedPackage
from zab_pkg_resolve.targets import cache_key, normalize_target


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