from zab_pkg_resolve.models import (
    CanonicalTarget,
    ConsumerPackageRecord,
    IndexSource,
    InstalledPackageRecord,
    Loadpoint,
    PackageCandidate,
    ResolvedPackage,
)
from zab_pkg_resolve.resolver import LocalEnvironmentProvider, ManagedStore, ResolverRegistry, SourceConfig, SourceProvider, cache_key, normalize_target


def main() -> None:
    print("zab-pkg-resolve")


__all__ = [
    "CanonicalTarget",
    "ConsumerPackageRecord",
    "IndexSource",
    "InstalledPackageRecord",
    "Loadpoint",
    "LocalEnvironmentProvider",
    "ManagedStore",
    "PackageCandidate",
    "ResolvedPackage",
    "ResolverRegistry",
    "SourceConfig",
    "SourceProvider",
    "cache_key",
    "main",
    "normalize_target",
]