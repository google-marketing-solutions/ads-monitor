# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

import pytest
import yaml

from gaarf_exporter.alert_elements import AlertRule, Label, MetricDefinition
from gaarf_exporter.alert import Alert


def test_label():
    label = Label("sample_label", 2)
    assert str(label) == 'sample_label="2"'


def test_metric_definition():
    metric_definition = MetricDefinition("googleads_impressions",
                                         Label("network", "CONTENT"))
    assert str(metric_definition) == 'googleads_impressions{network="CONTENT"}'


def test_alert_rule():
    metric_definition = MetricDefinition("googleads_impressions",
                                         Label("network", "CONTENT"))
    alert_rule = AlertRule(metric_definition)
    expected_alert_rule = 'sum by(campaign_id) (googleads_impressions{network="CONTENT"}) / sum by(campaign_id) (googleads_impressions{network="CONTENT"} offset 30m) > 2.0'
    # substitute \s+ to nothing for comparison
    actual_alert_rule = re.sub(r'\s+', '', str(alert_rule))
    expected_alert_rule = re.sub(r'\s+', '', expected_alert_rule)
    assert actual_alert_rule == expected_alert_rule


def test_create_alert():
    metric_definition = MetricDefinition('googleads_cost',
                                         Label('network', 'CONTENT'))
    alert = Alert('sample_alert', AlertRule(metric_definition=metric_definition))
    expected_yaml = """
        alert: sample_alert
        expr: |
          sum by(campaign_id) (googleads_cost{network="CONTENT"}) / sum by(campaign_id) (googleads_cost{network="CONTENT"} offset 30m) > 2.0
        for: 1h
    """
    expected = yaml.safe_load(expected_yaml)
    actual = yaml.safe_load(alert.text)
    # substitute \s+ to nothing for comparison
    expected['expr'] = re.sub(r'\s+', '', expected['expr'])
    actual['expr'] = re.sub(r'\s+', '', actual['expr'])
    assert actual == expected
