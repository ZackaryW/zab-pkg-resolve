# zab-pkg-resolve

`zab-pkg-resolve` is a small resolver and install-record boundary for Python package runtimes. It keeps source lookup, target normalization, cache/install state, validation, and consumer-facing package records outside the runtime that loads and dispatches installed packages.

The first consumer is `zush`, but the package is intentionally runtime-agnostic: it records what was resolved and installed, then projects a compact record that another runtime can use to load the package surface.

## Install

```bash
pip install zab-pkg-resolve
```

Python 3.12 or newer is required.

## What It Provides

- Canonical target normalization for package references such as GitHub shorthand and explicit URLs.
- Source/provider registration through `ResolverRegistry` and `SourceProvider` implementations.
- Managed cache and install records through `ManagedStore`.
- Runtime-facing `ConsumerPackageRecord` projection without resolver credentials or registry internals.
- Structured `Loadpoint` values for module and path based package surfaces.
- `InstallResult.changed` so consumers can skip runtime reloads when an update did not change the active artifact or load surface.
- Validation policies for manifest fields and Python version constraints.

## Basic Usage

```python
from pathlib import Path

from zab_pkg_resolve import CanonicalTarget, Loadpoint, ManagedStore, ResolvedPackage

store = ManagedStore(Path(".zab"))

package = ResolvedPackage(
	id="zush.cron",
	target=CanonicalTarget("package", "zush.cron"),
	artifact_hash="abc123",
	loadpoint=Loadpoint.module("zush_cron.__zush__", callable="extension"),
	capabilities=["zush.extension"],
)

result = store.install(package)

if result.changed:
	for record in store.consumer_records():
		print(record.as_dict())
```

## Loadpoints

A loadpoint tells a consumer runtime where the installed package surface lives and which callable to execute.

```python
Loadpoint.module("package_name.__zush__", callable="extension")
Loadpoint.path("C:/workspace/package_name", callable="extension")
```

Consumers receive loadpoints through `ConsumerPackageRecord.as_dict()`:

```python
{
	"id": "zush.cron",
	"installed_path": ".zab/installed/zush.cron",
	"entrypoint": None,
	"loadpoint": {
		"kind": "module",
		"ref": "zush_cron.__zush__",
		"callable": "extension",
	},
	"capabilities": ["zush.extension"],
}
```

## Development

```bash
uv run --extra dev behave
uv run python -m unittest discover -s tests
uv build
```

## License

MIT
