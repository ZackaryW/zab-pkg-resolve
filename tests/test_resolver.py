from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from zab_pkg_resolve.models import CanonicalTarget, ResolvedPackage
from zab_pkg_resolve.resolver import (
    ManagedStore,
    PythonVersionPolicy,
    RequiredFieldPolicy,
    ResolverRegistry,
    StaticSourceProvider,
    cache_key,
    normalize_target,
    run_validation,
)


class TargetNormalizationTests(unittest.TestCase):
    def test_equivalent_github_targets_share_cache_key(self) -> None:
        shorthand = normalize_target("gh:example/zush-cron")
        explicit = normalize_target("https://github.com/example/zush-cron.git#main")

        self.assertEqual(shorthand, explicit)
        self.assertEqual(cache_key(shorthand), cache_key(explicit))


class ManagedStoreTests(unittest.TestCase):
    def test_install_writes_active_record_and_consumer_projection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManagedStore(Path(temp_dir))
            package = ResolvedPackage(
                id="zush.cron",
                target=CanonicalTarget("package", "zush.cron"),
                source="fixture",
                revision="abc123",
                artifact_hash="abc123",
                entrypoint="zush_cron.extension:extension",
                capabilities=["zush.extension"],
            )

            result = store.install(package)
            consumer_records = store.consumer_records()

            self.assertTrue(result.record.active)
            self.assertTrue(result.record.install_path.exists())
            self.assertEqual(result.record.artifact_hash, "abc123")
            self.assertEqual(consumer_records[0].id, "zush.cron")
            self.assertEqual(consumer_records[0].capabilities, ("zush.extension",))

    def test_uninstall_preserves_record_but_removes_active_projection(self) -> None:
        with TemporaryDirectory() as temp_dir:
            store = ManagedStore(Path(temp_dir))
            package = ResolvedPackage(
                id="zush.cron",
                target=CanonicalTarget("package", "zush.cron"),
                source="fixture",
                revision="abc123",
                artifact_hash="abc123",
            )

            store.install(package)
            store.uninstall("zush.cron")

            self.assertIn("zush.cron", store.records)
            self.assertIsNone(store.active_record("zush.cron"))
            self.assertEqual(store.consumer_records(), [])


class ValidationPolicyTests(unittest.TestCase):
    def test_required_manifest_field_policy_fails_missing_entrypoint(self) -> None:
        package = ResolvedPackage(
            id="zush.cron",
            target=CanonicalTarget("package", "zush.cron"),
            artifact_hash="abc123",
            manifest={},
        )

        result = run_validation(package, [RequiredFieldPolicy("entrypoint")])

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "manifest-invalid")

    def test_python_version_policy_rejects_newer_requirement(self) -> None:
        package = ResolvedPackage(
            id="zush.cron",
            target=CanonicalTarget("package", "zush.cron"),
            artifact_hash="abc123",
            requires_python=">=3.13",
        )

        result = run_validation(package, [PythonVersionPolicy("3.12")])

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "python-version-unsupported")


class SourceRegistryTests(unittest.TestCase):
    def test_registered_source_type_creates_configured_source_instance(self) -> None:
        registry = ResolverRegistry()
        registry.register_type("internal-index", StaticSourceProvider)

        source = registry.add_source("internal", "internal-index", "memory://internal")
        source.add("internal:zush.cron")
        package = registry.resolve("internal:zush.cron")

        self.assertEqual(registry.last_provider, "internal")
        self.assertEqual(source.location, "memory://internal")
        self.assertEqual(package.provider, "internal")


if __name__ == "__main__":
    unittest.main()