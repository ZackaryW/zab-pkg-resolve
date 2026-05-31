Feature: Package install and uninstall lifecycle
  As a consumer of package resolution services
  I want installs and uninstalls to update a central userspace record
  So that applications can trust the installed package state after each operation

  Scenario: Installing a resolved package writes an installed package record
    Given a resolved package "zush.cron" with artifact hash "abc123"
    And the resolved package exposes entrypoint "zush_cron.extension:extension"
    When I install the resolved package
    Then the package should be installed under the managed install store
    And the central userspace record should contain package "zush.cron"
    And the package record should include artifact hash "abc123"
    And the package record should include entrypoint "zush_cron.extension:extension"
    And the package record should be marked active

  Scenario: Uninstalling a package removes the active install without losing provenance
    Given package "zush.cron" is installed and active
    When I uninstall package "zush.cron"
    Then package "zush.cron" should no longer be active
    And the managed install directory for package "zush.cron" should be removed
    And the central userspace record should retain the last resolved source metadata

  Scenario: Reinstalling the same resolved package reuses the cached artifact
    Given a resolved package "zush.cron" with artifact hash "abc123"
    And artifact hash "abc123" already exists in the cache
    When I install the resolved package
    Then the installer should use the cached artifact
    And the central userspace record should point to the new active install
    And no duplicate artifact cache entry should be created

  Scenario: Reinstalling an unchanged resolved package reports no surface change
    Given a resolved package "zush.cron" with artifact hash "abc123"
    And I install the resolved package
    When I install the resolved package
    Then the install result should report no package change

  Scenario: Updating a resolved package with a new artifact reports a surface change
    Given a resolved package "zush.cron" with artifact hash "abc123"
    And I install the resolved package
    And the resolved package artifact hash becomes "def456"
    When I install the resolved package
    Then the install result should report a package change