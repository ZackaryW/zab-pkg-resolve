Feature: Cache identity and central records
  The resolver must create stable cache identities and durable userspace records
  so install state can be reproduced, inspected, and garbage collected safely.

  Scenario: Canonically equivalent targets share one cache identity
    Given target "gh:example/zush-cron" normalizes to git URL "https://github.com/example/zush-cron.git" ref "main"
    And target "https://github.com/example/zush-cron.git#main" normalizes to git URL "https://github.com/example/zush-cron.git" ref "main"
    When cache keys are calculated for both targets
    Then both targets should produce the same SHA256 cache key
    And the cache key should be calculated from the canonical target descriptor

  Scenario: Different resolved revisions produce distinct lock records
    Given target "github:example/zush-cron" resolves to revision "111aaa"
    And target "github:example/zush-cron" later resolves to revision "222bbb"
    When lock records are written for both resolutions
    Then the lock records should have different resolved revisions
    And each lock record should preserve the original canonical target descriptor

  Scenario: Cache garbage collection preserves referenced artifacts
    Given artifact cache entry "abc123" is referenced by an active package record
    And artifact cache entry "def456" is unreferenced
    When cache garbage collection runs
    Then artifact cache entry "abc123" should remain
    And artifact cache entry "def456" should be removed