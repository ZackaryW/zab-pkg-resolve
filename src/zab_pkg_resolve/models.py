from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CanonicalTarget:
    kind: str
    url: str
    ref: str = "main"

    def descriptor(self) -> dict[str, str]:
        return {"kind": self.kind, "url": self.url, "ref": self.ref}


@dataclass(frozen=True)
class IndexSource:
    name: str
    location: str
    level: str


@dataclass(frozen=True)
class PackageCandidate:
    id: str
    version: str
    source: str
    target: CanonicalTarget


@dataclass(frozen=True)
class Loadpoint:
    kind: str
    ref: str
    callable: str = "extension"

    @classmethod
    def module(cls, ref: str, *, callable: str = "extension") -> Loadpoint:
        return cls(kind="module", ref=ref, callable=callable)

    @classmethod
    def path(cls, ref: str, *, callable: str = "extension") -> Loadpoint:
        return cls(kind="path", ref=ref, callable=callable)

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "ref": self.ref, "callable": self.callable}


@dataclass
class ResolvedPackage:
    id: str
    target: CanonicalTarget
    source: str | None = None
    provider: str | None = None
    revision: str = ""
    artifact_hash: str = ""
    entrypoint: str | None = None
    loadpoint: Loadpoint | None = None
    capabilities: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    requires_python: str | None = None


@dataclass
class InstalledPackageRecord:
    id: str
    install_path: Path
    artifact_hash: str
    entrypoint: str | None = None
    loadpoint: Loadpoint | None = None
    capabilities: list[str] = field(default_factory=list)
    active: bool = True
    disabled: bool = False
    source_metadata: dict[str, Any] = field(default_factory=dict)
    registry_authentication: dict[str, Any] | None = None


@dataclass(frozen=True)
class ConsumerPackageRecord:
    id: str
    installed_path: Path
    entrypoint: str | None
    loadpoint: Loadpoint | None
    capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "installed_path": str(self.installed_path),
            "entrypoint": self.entrypoint,
            "loadpoint": self.loadpoint.as_dict() if self.loadpoint is not None else None,
            "capabilities": list(self.capabilities),
        }


@dataclass(frozen=True)
class LockRecord:
    target: CanonicalTarget
    revision: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    code: str | None = None


@dataclass(frozen=True)
class InstallResult:
    record: InstalledPackageRecord
    used_cache: bool
    changed: bool = True