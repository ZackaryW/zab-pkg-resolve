from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from importlib import metadata
from importlib.util import find_spec
import re
from typing import Any, Callable, Iterable

from zab_pkg_resolve.interfaces.sources import SourceConfig
from zab_pkg_resolve.models import CanonicalTarget, Loadpoint, ResolvedPackage


DistributionSource = Callable[[], Iterable[Any]]
ModuleFinder = Callable[[str], object | None]


class LocalEnvironmentProvider:
    def __init__(
        self,
        name: str | SourceConfig = "local",
        source_type: str = "local-env",
        location: str = r"^zush[-_].+",
        *,
        distributions: DistributionSource | None = None,
        module_finder: ModuleFinder | None = None,
    ) -> None:
        if isinstance(name, SourceConfig):
            config = name
            self.name = config.name
            self.source_type = config.type
            self.location = config.location or location
        else:
            self.name = name
            self.source_type = source_type
            self.location = location
        self._distributions = distributions or metadata.distributions
        self._module_finder = module_finder or find_spec
        self.resolved_targets: list[str] = []

    def scan(self, pattern: str | None = None) -> list[ResolvedPackage]:
        matcher = re.compile(pattern or self.location)
        packages: list[ResolvedPackage] = []
        for distribution in self._distributions():
            package_name = self._distribution_name(distribution)
            if not package_name or not matcher.search(package_name):
                continue
            loadpoint = self._loadpoint_for(distribution, package_name)
            if loadpoint is None:
                continue
            packages.append(self._package_for(distribution, package_name, loadpoint))
        return packages

    def can_resolve(self, target: str) -> bool:
        return self._target_package_id(target) in {package.id for package in self.scan()}

    def resolve(self, target: str) -> ResolvedPackage:
        self.resolved_targets.append(target)
        package_id = self._target_package_id(target)
        for package in self.scan():
            if package.id == package_id:
                return replace(package)
        raise KeyError(target)

    def _target_package_id(self, target: str) -> str:
        prefix = f"{self.name}:"
        return target[len(prefix):] if target.startswith(prefix) else target

    def _distribution_name(self, distribution: Any) -> str:
        metadata_payload = getattr(distribution, "metadata", {})
        name = metadata_payload.get("Name") if hasattr(metadata_payload, "get") else None
        return str(name or "")

    def _distribution_version(self, distribution: Any) -> str:
        return str(getattr(distribution, "version", ""))

    def _loadpoint_for(self, distribution: Any, package_name: str) -> Loadpoint | None:
        for module_name in self._module_candidates(distribution, package_name):
            loadpoint_ref = f"{module_name}.__zush__"
            if self._module_exists(loadpoint_ref):
                return Loadpoint.module(loadpoint_ref, callable="extension")
        return None

    def _module_candidates(self, distribution: Any, package_name: str) -> list[str]:
        candidates: list[str] = []
        top_level = self._read_top_level(distribution)
        if top_level:
            candidates.extend(self._valid_module_name(line.strip()) for line in top_level.splitlines())
        candidates.append(self._normalize_module_name(package_name))
        return [candidate for candidate in dict.fromkeys(candidates) if candidate]

    def _read_top_level(self, distribution: Any) -> str | None:
        read_text = getattr(distribution, "read_text", None)
        if not callable(read_text):
            return None
        try:
            return read_text("top_level.txt")
        except OSError:
            return None

    def _valid_module_name(self, value: str) -> str:
        if not value or not value.replace("_", "").isalnum():
            return ""
        return value

    def _normalize_module_name(self, package_name: str) -> str:
        return re.sub(r"[-.]+", "_", package_name)

    def _module_exists(self, module_ref: str) -> bool:
        try:
            return self._module_finder(module_ref) is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def _package_for(self, distribution: Any, package_name: str, loadpoint: Loadpoint) -> ResolvedPackage:
        version = self._distribution_version(distribution)
        target = CanonicalTarget("local-env", package_name, ref=version or "installed")
        artifact_hash = sha256(f"{package_name}:{version}:{loadpoint.ref}".encode()).hexdigest()
        return ResolvedPackage(
            id=package_name,
            target=target,
            source=self.name,
            provider=self.name,
            revision=version,
            artifact_hash=artifact_hash,
            loadpoint=loadpoint,
        )
