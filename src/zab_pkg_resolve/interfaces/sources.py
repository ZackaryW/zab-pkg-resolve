from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from zab_pkg_resolve.models import ResolvedPackage


@dataclass(frozen=True)
class SourceConfig:
    name: str
    type: str
    location: str
    options: dict[str, Any] = field(default_factory=dict)


class SourceProvider(Protocol):
    name: str
    source_type: str
    location: str

    def can_resolve(self, target: str) -> bool: ...
    def resolve(self, target: str) -> ResolvedPackage: ...


class SourceFactory(Protocol):
    def __call__(self, config: SourceConfig) -> SourceProvider: ...