from __future__ import annotations

from zab_pkg_resolve.models import ResolvedPackage, ValidationResult


class RequiredFieldPolicy:
    def __init__(self, field: str) -> None:
        self.field = field

    def validate(self, package: ResolvedPackage) -> ValidationResult:
        if self.field not in package.manifest or package.manifest.get(self.field) in {None, ""}:
            return ValidationResult(False, "manifest-invalid")
        return ValidationResult(True)


class PythonVersionPolicy:
    def __init__(self, active_version: str) -> None:
        self.active_version = active_version

    def validate(self, package: ResolvedPackage) -> ValidationResult:
        requirement = package.requires_python
        if requirement is None or not requirement.startswith(">="):
            return ValidationResult(True)
        if self._active_version() < self._required_version(requirement):
            return ValidationResult(False, "python-version-unsupported")
        return ValidationResult(True)

    def _required_version(self, requirement: str) -> tuple[int, ...]:
        return self._version_tuple(requirement.removeprefix(">="))

    def _active_version(self) -> tuple[int, ...]:
        return self._version_tuple(self.active_version)

    def _version_tuple(self, version: str) -> tuple[int, ...]:
        return tuple(int(part) for part in version.split(".")[:2])


def run_validation(package: ResolvedPackage, policies: list[object]) -> ValidationResult:
    for policy in policies:
        result = policy.validate(package)
        if not result.ok:
            return result
    return ValidationResult(True)