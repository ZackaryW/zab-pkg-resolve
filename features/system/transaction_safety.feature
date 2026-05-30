Feature: Install transaction safety
  Install and uninstall operations must be recoverable so interrupted operations
  do not appear as complete packages to consumers.

  Scenario: Failed install leaves no active package record
    Given a resolved package "zush.cron" with artifact hash "abc123"
    And the install operation fails before the final install directory is committed
    When the install transaction is recovered
    Then package "zush.cron" should not be marked active
    And no consumer-facing record should be returned for package "zush.cron"
    And temporary transaction files for package "zush.cron" should be cleaned up

  Scenario: Successful install commits record and directory atomically
    Given a resolved package "zush.cron" with artifact hash "abc123"
    When the install transaction commits successfully
    Then the managed install directory should exist
    And the central userspace record should mark package "zush.cron" active
    And the package record should point to the committed install directory

  Scenario: Failed uninstall keeps the previous active record recoverable
    Given package "zush.cron" is installed and active
    And the uninstall operation fails before the central record is updated
    When the uninstall transaction is recovered
    Then package "zush.cron" should have a consistent active state
    And the recovery report should explain whether the install directory or record was restored