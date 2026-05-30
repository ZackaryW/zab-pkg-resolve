from __future__ import annotations

from behave import given, then, when

from zab_pkg_resolve.models import CanonicalTarget, ResolvedPackage
from zab_pkg_resolve.resolver import (
	PythonVersionPolicy,
	RequiredFieldPolicy,
	ScenarioWorkspace,
	StaticSourceProvider,
	cache_key,
	normalize_target,
	run_validation,
	write_lock_records,
)


def _workspace(context) -> ScenarioWorkspace:
	return context.workspace


def _record(context, package_id: str):
	return _workspace(context).store.records[package_id]


def _consumer_record(context, package_id: str):
	for record in _workspace(context).consumer_results:
		if record.id == package_id:
			return record
	raise AssertionError(f"No consumer record for {package_id}")


@given('a user-level index source named "{name}" at "{location}"')
def add_user_index_source(context, name: str, location: str):
	_workspace(context).indexes.add_source(name, location, "user")


@given('a project-level index source named "{name}" at "{location}"')
def add_project_index_source(context, name: str, location: str):
	_workspace(context).indexes.add_source(name, location, "project")


@when("the resolver loads configured index sources")
def load_index_sources(context):
	_workspace(context).indexes.load()


@then('the active source named "{name}" should use "{location}"')
def assert_active_source_location(context, name: str, location: str):
	source = _workspace(context).indexes.active_sources[name]
	assert source.location == location


@then('the overridden user-level source named "{name}" should not be queried')
def assert_overridden_source_not_queried(context, name: str):
	assert not _workspace(context).indexes.was_queried(name)


@given('the "{source}" index contains package "{package_id}" version "{version}"')
def add_index_package(context, source: str, package_id: str, version: str):
	_workspace(context).indexes.add_package(source, package_id, version)


@given('package "{package_id}" points to git artifact "{url}" ref "{ref}"')
def set_package_git_artifact(context, package_id: str, url: str, ref: str):
	_workspace(context).indexes.set_git_artifact(package_id, url, ref)


@when('the resolver searches all active indexes for packages matching "{pattern}"')
def search_indexes(context, pattern: str):
	_workspace(context).search_results = _workspace(context).indexes.search(pattern)


@then('the search results should include package "{package_id}" from source "{source}"')
def assert_search_result(context, package_id: str, source: str):
	assert any(result.id == package_id and result.source == source for result in _workspace(context).search_results)


@then("each result should include a canonical target descriptor")
def assert_search_results_have_targets(context):
	assert _workspace(context).search_results
	for result in _workspace(context).search_results:
		assert result.target.descriptor()["kind"]
		assert result.target.descriptor()["url"]


@when('I resolve package "{package_id}" from source "{source}"')
def resolve_index_package(context, package_id: str, source: str):
	_workspace(context).resolved_package = _workspace(context).indexes.resolve(package_id, source)


@then('the resolved package should have id "{package_id}"')
def assert_resolved_package_id(context, package_id: str):
	assert _workspace(context).resolved_package.id == package_id


@then('the resolved package should record source "{source}"')
def assert_resolved_package_source(context, source: str):
	assert _workspace(context).resolved_package.source == source


@then('the resolved package should record git ref "{ref}"')
def assert_resolved_package_git_ref(context, ref: str):
	assert _workspace(context).resolved_package.target.ref == ref


@then("the resolved package should include an immutable resolved revision")
def assert_resolved_package_revision(context):
	assert _workspace(context).resolved_package.revision


@given('a resolved package "{package_id}" with artifact hash "{artifact_hash}"')
def given_resolved_package(context, package_id: str, artifact_hash: str):
	_workspace(context).resolved_package = ResolvedPackage(
		id=package_id,
		target=CanonicalTarget("package", package_id),
		source="fixture",
		revision=artifact_hash[:12],
		artifact_hash=artifact_hash,
		manifest={"entrypoint": "fixture:extension"},
	)


@given('the resolved package exposes entrypoint "{entrypoint}"')
def set_resolved_entrypoint(context, entrypoint: str):
	_workspace(context).resolved_package.entrypoint = entrypoint
	_workspace(context).resolved_package.manifest["entrypoint"] = entrypoint


@when("I install the resolved package")
def install_resolved_package(context):
	_workspace(context).store.install(_workspace(context).resolved_package)


@then("the package should be installed under the managed install store")
def assert_installed_under_store(context):
	result = _workspace(context).store.last_install_result
	assert result is not None
	assert result.record.install_path.exists()
	assert _workspace(context).store.install_dir in result.record.install_path.parents


@then('the central userspace record should contain package "{package_id}"')
def assert_central_record_contains(context, package_id: str):
	assert package_id in _workspace(context).store.records


@then('the package record should include artifact hash "{artifact_hash}"')
def assert_record_artifact_hash(context, artifact_hash: str):
	assert _workspace(context).store.last_install_result.record.artifact_hash == artifact_hash


@then('the package record should include entrypoint "{entrypoint}"')
def assert_record_entrypoint(context, entrypoint: str):
	assert _workspace(context).store.last_install_result.record.entrypoint == entrypoint


@then("the package record should be marked active")
def assert_record_active(context):
	assert _workspace(context).store.last_install_result.record.active


@given('package "{package_id}" is installed and active')
def given_package_installed_active(context, package_id: str):
	package = ResolvedPackage(
		id=package_id,
		target=CanonicalTarget("package", package_id),
		source="fixture",
		revision="fixture-rev",
		artifact_hash=f"{package_id}-hash",
		entrypoint=None,
	)
	_workspace(context).store.install(package)


@when('I uninstall package "{package_id}"')
def uninstall_package(context, package_id: str):
	_workspace(context).store.uninstall(package_id)


@then('package "{package_id}" should no longer be active')
def assert_package_not_active(context, package_id: str):
	assert _workspace(context).store.active_record(package_id) is None


@then('the managed install directory for package "{package_id}" should be removed')
def assert_install_dir_removed(context, package_id: str):
	assert not _record(context, package_id).install_path.exists()


@then("the central userspace record should retain the last resolved source metadata")
def assert_record_preserves_source_metadata(context):
	assert _workspace(context).store.last_install_result.record.source_metadata["source"] == "fixture"


@given('artifact hash "{artifact_hash}" already exists in the cache')
def given_cache_entry(context, artifact_hash: str):
	_workspace(context).store.add_cache_entry(artifact_hash)


@then("the installer should use the cached artifact")
def assert_installer_used_cache(context):
	assert _workspace(context).store.last_install_result.used_cache


@then("the central userspace record should point to the new active install")
def assert_record_points_to_active_install(context):
	record = _workspace(context).store.last_install_result.record
	assert record.active
	assert record.install_path.exists()


@then("no duplicate artifact cache entry should be created")
def assert_no_duplicate_cache_entry(context):
	package = _workspace(context).resolved_package
	assert list(_workspace(context).store.cache_entries).count(package.artifact_hash) == 1


@given('package "{package_id}" exposes entrypoint "{entrypoint}"')
def set_installed_entrypoint(context, package_id: str, entrypoint: str):
	_record(context, package_id).entrypoint = entrypoint


@given('package "{package_id}" declares capability "{capability}"')
def set_installed_capability(context, package_id: str, capability: str):
	_record(context, package_id).capabilities.append(capability)


@given('package "{package_id}" is installed and disabled')
def given_package_installed_disabled(context, package_id: str):
	given_package_installed_active(context, package_id)
	_workspace(context).store.mark_disabled(package_id)


@when("a consumer lists active installed packages")
def list_consumer_records(context):
	_workspace(context).consumer_results = _workspace(context).store.consumer_records()


@then('the consumer record for "{package_id}" should include id "{expected}"')
def assert_consumer_record_id(context, package_id: str, expected: str):
	assert _consumer_record(context, package_id).id == expected


@then('the consumer record for "{package_id}" should include its installed path')
def assert_consumer_record_path(context, package_id: str):
	assert _consumer_record(context, package_id).installed_path.exists()


@then('the consumer record for "{package_id}" should include entrypoint "{entrypoint}"')
def assert_consumer_record_entrypoint(context, package_id: str, entrypoint: str):
	assert _consumer_record(context, package_id).entrypoint == entrypoint


@then('the consumer record for "{package_id}" should include capability "{capability}"')
def assert_consumer_record_capability(context, package_id: str, capability: str):
	assert capability in _consumer_record(context, package_id).capabilities


@then('the consumer record for "{package_id}" should not include registry authentication details')
def assert_consumer_record_hides_auth(context, package_id: str):
	assert "registry_authentication" not in _consumer_record(context, package_id).as_dict()


@then('the consumer records should include package "{package_id}"')
def assert_consumer_records_include(context, package_id: str):
	assert any(record.id == package_id for record in _workspace(context).consumer_results)


@then('the consumer records should not include package "{package_id}"')
def assert_consumer_records_exclude(context, package_id: str):
	assert all(record.id != package_id for record in _workspace(context).consumer_results)


@given('target "{raw}" normalizes to git URL "{url}" ref "{ref}"')
def given_target_normalizes(context, raw: str, url: str, ref: str):
	target = normalize_target(raw)
	assert target == CanonicalTarget("git", url, ref)
	_workspace(context).normalized_targets[raw] = target


@when("cache keys are calculated for both targets")
def calculate_cache_keys(context):
	_workspace(context).cache_keys = [cache_key(target) for target in _workspace(context).normalized_targets.values()]


@then("both targets should produce the same SHA256 cache key")
def assert_same_cache_key(context):
	keys = _workspace(context).cache_keys
	assert len(keys) == 2
	assert keys[0] == keys[1]
	assert len(keys[0]) == 64


@then("the cache key should be calculated from the canonical target descriptor")
def assert_cache_key_uses_descriptor(context):
	target = next(iter(_workspace(context).normalized_targets.values()))
	assert _workspace(context).cache_keys[0] == cache_key(target)


@given('target "{raw}" resolves to revision "{revision}"')
def given_target_revision(context, raw: str, revision: str):
	_workspace(context).resolutions.append((raw, revision))


@given('target "{raw}" later resolves to revision "{revision}"')
def given_target_later_revision(context, raw: str, revision: str):
	_workspace(context).resolutions.append((raw, revision))


@when("lock records are written for both resolutions")
def write_locks(context):
	_workspace(context).lock_records = write_lock_records(_workspace(context).resolutions)


@then("the lock records should have different resolved revisions")
def assert_lock_revisions_differ(context):
	records = _workspace(context).lock_records
	assert records[0].revision != records[1].revision


@then("each lock record should preserve the original canonical target descriptor")
def assert_lock_preserves_target(context):
	for record in _workspace(context).lock_records:
		assert record.target.descriptor()["url"]


@given('artifact cache entry "{artifact_hash}" is referenced by an active package record')
def given_referenced_cache_entry(context, artifact_hash: str):
	package = ResolvedPackage(
		id=f"pkg-{artifact_hash}",
		target=CanonicalTarget("package", artifact_hash),
		source="fixture",
		revision=artifact_hash,
		artifact_hash=artifact_hash,
	)
	_workspace(context).store.install(package)


@given('artifact cache entry "{artifact_hash}" is unreferenced')
def given_unreferenced_cache_entry(context, artifact_hash: str):
	_workspace(context).store.add_cache_entry(artifact_hash)


@when("cache garbage collection runs")
def run_cache_gc(context):
	_workspace(context).store.garbage_collect_cache()


@then('artifact cache entry "{artifact_hash}" should remain')
def assert_cache_entry_remains(context, artifact_hash: str):
	assert artifact_hash in _workspace(context).store.cache_entries


@then('artifact cache entry "{artifact_hash}" should be removed')
def assert_cache_entry_removed(context, artifact_hash: str):
	assert artifact_hash not in _workspace(context).store.cache_entries


@given("the install operation fails before the final install directory is committed")
def given_failed_install(context):
	_workspace(context).store.start_failed_install(_workspace(context).resolved_package)


@when("the install transaction is recovered")
def recover_install_transaction(context):
	_workspace(context).store.recover_install(_workspace(context).resolved_package.id)


@then('package "{package_id}" should not be marked active')
def assert_not_marked_active(context, package_id: str):
	assert _workspace(context).store.active_record(package_id) is None


@then('no consumer-facing record should be returned for package "{package_id}"')
def assert_no_consumer_record(context, package_id: str):
	assert all(record.id != package_id for record in _workspace(context).store.consumer_records())


@then('temporary transaction files for package "{package_id}" should be cleaned up')
def assert_transaction_cleaned(context, package_id: str):
	assert not (_workspace(context).store.transaction_dir / package_id).exists()


@when("the install transaction commits successfully")
def commit_install_transaction(context):
	_workspace(context).store.commit_install(_workspace(context).resolved_package)


@then("the managed install directory should exist")
def assert_managed_install_dir_exists(context):
	assert _workspace(context).store.last_install_result.record.install_path.exists()


@then('the central userspace record should mark package "{package_id}" active')
def assert_central_record_active(context, package_id: str):
	assert _workspace(context).store.records[package_id].active


@then("the package record should point to the committed install directory")
def assert_record_points_to_committed_dir(context):
	assert _workspace(context).store.last_install_result.record.install_path.exists()


@given("the uninstall operation fails before the central record is updated")
def given_failed_uninstall(context):
	_workspace(context).store.start_failed_uninstall("zush.cron")


@when("the uninstall transaction is recovered")
def recover_uninstall_transaction(context):
	_workspace(context).store.recover_uninstall("zush.cron")


@then('package "{package_id}" should have a consistent active state')
def assert_consistent_active_state(context, package_id: str):
	record = _workspace(context).store.records[package_id]
	assert record.active == record.install_path.exists()


@then("the recovery report should explain whether the install directory or record was restored")
def assert_recovery_report(context):
	assert "record" in _workspace(context).store.recovery_report
	assert "install directory" in _workspace(context).store.recovery_report


@given('a custom source provider named "{name}"')
def given_custom_provider(context, name: str):
	provider = StaticSourceProvider(name)
	_workspace(context).providers.register(provider)


@given('provider "{name}" can resolve target "{target}"')
def provider_can_resolve(context, name: str, target: str):
	provider = _workspace(context).providers.providers[name]
	provider.add(target, package_id=target.split(":", 1)[-1])


@when('I resolve target "{target}"')
def resolve_target(context, target: str):
	_workspace(context).resolved_package = _workspace(context).providers.resolve(target)


@then('the resolver should delegate to provider "{name}"')
def assert_delegated_provider(context, name: str):
	assert _workspace(context).providers.last_provider == name


@then('the resolved package should record provider "{name}"')
def assert_resolved_provider(context, name: str):
	assert _workspace(context).resolved_package.provider == name


@given('a resolved package "{package_id}" with a manifest missing field "{field}"')
def given_package_missing_manifest_field(context, package_id: str, field: str):
	given_resolved_package(context, package_id, "abc123")
	_workspace(context).resolved_package.manifest.pop(field, None)


@given('a validation policy requires field "{field}"')
def given_required_field_policy(context, field: str):
	_workspace(context).validation_policies.append(RequiredFieldPolicy(field))


@when("package validation runs")
def run_package_validation(context):
	_workspace(context).validation_result = run_validation(
		_workspace(context).resolved_package,
		_workspace(context).validation_policies,
	)


@then('validation should fail with code "{code}"')
def assert_validation_code(context, code: str):
	assert not _workspace(context).validation_result.ok
	assert _workspace(context).validation_result.code == code


@then("the package should not be installed")
def assert_package_not_installed(context):
	package = _workspace(context).resolved_package
	assert package.id not in _workspace(context).store.records


@given('a resolved package "{package_id}" requires Python "{requirement}"')
def given_package_requires_python(context, package_id: str, requirement: str):
	given_resolved_package(context, package_id, "abc123")
	_workspace(context).resolved_package.requires_python = requirement


@given('the active Python version is "{version}"')
def given_active_python_version(context, version: str):
	_workspace(context).validation_policies.append(PythonVersionPolicy(version))


@when("compatibility validation runs")
def run_compatibility_validation(context):
	run_package_validation(context)