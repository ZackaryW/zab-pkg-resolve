from __future__ import annotations

from zab_pkg_resolve.builtins.sources.static import StaticSourceProvider
from zab_pkg_resolve.interfaces.sources import SourceConfig, SourceFactory, SourceProvider


class ResolverRegistry:
    def __init__(self) -> None:
        self.providers: dict[str, SourceProvider] = {}
        self.source_types: dict[str, SourceFactory] = {}
        self.last_provider: str | None = None

    def register(self, provider: SourceProvider) -> None:
        self.providers[provider.name] = provider

    def register_type(self, source_type: str, factory: SourceFactory) -> None:
        self.source_types[source_type] = factory

    def add_source(
        self,
        name: str,
        source_type: str,
        location: str,
        options: dict[str, object] | None = None,
    ) -> SourceProvider:
        factory = self.source_types[source_type]
        provider = factory(SourceConfig(name=name, type=source_type, location=location, options=options or {}))
        self.register(provider)
        return provider

    def resolve(self, target: str) -> ResolvedPackage:
        for provider in self.providers.values():
            if provider.can_resolve(target):
                self.last_provider = provider.name
                return provider.resolve(target)
        raise KeyError(target)