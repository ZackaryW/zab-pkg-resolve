Feature: Index source management
  As a tool author building on zab-pkg-resolve
  I want package indexes to be registered, prioritized, and queried consistently
  So that consumers can resolve packages without knowing where each index lives

  Background:
    Given a user-level index source named "public" at "https://example.test/zab/index.json"

  Scenario: Project-level index source overrides a user-level source with the same name
    Given a project-level index source named "public" at "./registry/index.json"
    When the resolver loads configured index sources
    Then the active source named "public" should use "./registry/index.json"
    And the overridden user-level source named "public" should not be queried

  Scenario: Querying multiple index sources returns normalized package candidates
    Given a project-level index source named "private" at "./private/index.json"
    And the "public" index contains package "zush.cron" version "1.0.0"
    And the "private" index contains package "zush.github" version "0.3.0"
    When the resolver searches all active indexes for packages matching "zush.*"
    Then the search results should include package "zush.cron" from source "public"
    And the search results should include package "zush.github" from source "private"
    And each result should include a canonical target descriptor

  Scenario: Resolving an index package records the exact artifact target
    Given the "public" index contains package "zush.cron" version "1.0.0"
    And package "zush.cron" points to git artifact "https://github.com/example/zush-cron.git" ref "main"
    When I resolve package "zush.cron" from source "public"
    Then the resolved package should have id "zush.cron"
    And the resolved package should record source "public"
    And the resolved package should record git ref "main"
    And the resolved package should include an immutable resolved revision