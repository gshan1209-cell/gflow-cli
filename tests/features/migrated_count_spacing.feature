@e2e @e2e_auth
Feature: Select the requested output count on the real Flow editor
  Scenario: A single output is selected without submitting a generation
    Given a signed-in Flow project for count verification
    When one output is selected on the real settings pane
    Then only one output is checked and no generation is submitted
