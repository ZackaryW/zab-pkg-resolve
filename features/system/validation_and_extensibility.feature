Feature: Validation and provider extensibility
  The resolver must allow source providers and validation policies to be extended
  without changing package lifecycle code.

  Scenario: A custom source provider participates in resolution
    Given a custom source provider named "internal"
    And provider "internal" can resolve target "internal:zush.cron"
    When I resolve target "internal:zush.cron"
    Then the resolver should delegate to provider "internal"
    And the resolved package should record provider "internal"

  Scenario: A custom source type creates configured source instances
    Given a custom source type "internal-index" is registered
    And configured source "internal" uses type "internal-index" at "memory://internal"
    And source "internal" can resolve target "internal:zush.cron"
    When I resolve target "internal:zush.cron"
    Then the resolver should delegate to provider "internal"
    And source "internal" should remember location "memory://internal"

  Scenario: Validation policies reject an invalid package manifest
    Given a resolved package "zush.cron" with a manifest missing field "entrypoint"
    And a validation policy requires field "entrypoint"
    When package validation runs
    Then validation should fail with code "manifest-invalid"
    And the package should not be installed

  Scenario: Compatibility policies reject unsupported runtime constraints
    Given a resolved package "zush.cron" requires Python ">=3.13"
    And the active Python version is "3.12"
    When compatibility validation runs
    Then validation should fail with code "python-version-unsupported"
    And the package should not be installed