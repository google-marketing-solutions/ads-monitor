Feature: gaarf-exporter selects correct collectors

  Scenario: Return default collector
    Given collector registry is initialized
    When I don't specify collectors
    Then default collectors are returned

  Scenario: Return concrete collector
    Given collector registry is initialized
    When I specify performance collector
    Then performance collector is returned

  Scenario: Return concrete subregistry
    Given collector registry is initialized
    When I specify search subregistry
    Then all collectors from search subregistry returned

  Scenario: Return concrete collectors
    Given collector registry is initialized
    When I specify performance and keywords collector
    Then performance, keywords and mapping collectors are returned

  Scenario: Return concrete collectors from mix of registry / collector
    Given collector registry is initialized
    When I specify default registry and keywords collector
    Then performance, mapping, keywords, ad_disapprovals, conversion_action collectors are returned

  Scenario: Return unique collectors from mix of registry / collector
    Given collector registry is initialized
    When I specify default registry and performance collector
    Then performance, mapping, ad_disapprovals, conversion_action collectors are returned
