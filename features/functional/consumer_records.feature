Feature: Consumer-facing installed records
  As zush or another runtime consumer
  I want a small installed package record that hides resolver mechanics
  So that runtime feature definitions stay focused on loading and activation

  Scenario: Listing installed packages exposes only runtime-relevant fields
    Given package "zush.cron" is installed and active
    And package "zush.cron" exposes entrypoint "zush_cron.extension:extension"
    And package "zush.cron" declares capability "zush.extension"
    When a consumer lists active installed packages
    Then the consumer record for "zush.cron" should include id "zush.cron"
    And the consumer record for "zush.cron" should include its installed path
    And the consumer record for "zush.cron" should include entrypoint "zush_cron.extension:extension"
    And the consumer record for "zush.cron" should include capability "zush.extension"
    But the consumer record for "zush.cron" should not include registry authentication details

  Scenario: Disabled packages are omitted from active consumer records
    Given package "zush.cron" is installed and active
    And package "zush.github" is installed and disabled
    When a consumer lists active installed packages
    Then the consumer records should include package "zush.cron"
    And the consumer records should not include package "zush.github"