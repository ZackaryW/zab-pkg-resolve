Feature: Local environment package provider
  As a runtime using zab package resolution
  I want to discover already-installed local Python packages by name pattern
  So that local zush extensions can be mounted without source index lookup

  Scenario: Matching local distributions expose module loadpoints
    Given the local environment contains distribution "zush-demo" version "1.2.3"
    And distribution "zush-demo" exposes top-level module "zush_demo"
    And module "zush_demo.__zush__" is importable
    When the local environment provider scans with pattern "^zush[-_].+"
    Then local package results should include package "zush-demo"
    And local package "zush-demo" should include module loadpoint "zush_demo.__zush__"
    And local package "zush-demo" should record provider "local"

  Scenario: Non-matching local distributions are ignored
    Given the local environment contains distribution "other-demo" version "1.0.0"
    And distribution "other-demo" exposes top-level module "other_demo"
    And module "other_demo.__zush__" is importable
    When the local environment provider scans with pattern "^zush[-_].+"
    Then local package results should not include package "other-demo"

  Scenario: Local provider resolves explicit local targets
    Given the local environment contains distribution "zush-tool" version "2.0.0"
    And distribution "zush-tool" exposes top-level module "zush_tool"
    And module "zush_tool.__zush__" is importable
    And a local environment source named "local" uses pattern "^zush[-_].+"
    When I resolve target "local:zush-tool"
    Then the resolver should delegate to provider "local"
    And the resolved package should have id "zush-tool"
    And the resolved package should include local module loadpoint "zush_tool.__zush__"
