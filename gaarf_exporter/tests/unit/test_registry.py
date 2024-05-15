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
from __future__ import annotations

import pytest

from gaarf_exporter import collector as query_collector
from gaarf_exporter import registry


class TestRegistry:

  @pytest.fixture(scope='class')
  def collector_registry(self):
    return registry.Registry()

  def test_from_collector_definitions(self):
    collector_registry = registry.Registry.from_collector_definitions(
        'test_collector_definitions.yaml')
    assert collector_registry.collectors is not None

  def test_default_collectors_returns_correct_target_names(self, collector_registry):
    default_collectors = collector_registry.default_collectors
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in default_collectors.targets} == expected

  def test_extract_collector_targets_returns_correct_collectors_from_registry(
      self, collector_registry):
    actual = collector_registry.find_collectors('performance,mapping')
    expected = {
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_all_collectors_from_subregistry(
      self, collector_registry):
    actual = collector_registry.find_collectors('default')
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_unique_collectors_from_registry_and_sub_registry(
      self, collector_registry):
    actual = collector_registry.find_collectors('default,performance,mapping')
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_empty_set_when_collectors_are_not_found(
      self, collector_registry):
    actual = collector_registry.find_collectors('non-existing-collector')

    assert actual == registry.CollectorSet()

  def test_add_collectors(self, collector_registry):

    class SampleCollector:
      name = 'sample'
      target = query_collector.Collector(name='sample')

    collector_registry.add_collectors([SampleCollector])
    found_collector_set = collector_registry.find_collectors('sample')

    assert SampleCollector in found_collector_set


class TestCollectorSet:

  @pytest.fixture
  def collector_set(self):
    return registry.CollectorSet({
        registry.PerformanceCollector,
    })

  def test_customize_returns_modified_target_start_end_date(
      self, collector_set):
    start_date = '2024-01-01'
    end_date = '2024-01-01'
    customize_dict = {
        'start_date': start_date,
        'end_date': end_date,
    }
    collector_set.customize(customize_dict)
    customized_target = collector_set.targets.pop()

    assert f"segments.date BETWEEN '{start_date}' AND '{end_date}'" in (
        customized_target.query)

  @pytest.mark.parametrize('level', ['ad_group', 'campaign', 'customer'])
  def test_customize_returns_modified_target_level(self, collector_set, level):
    customize_dict = {
        'level': level,
    }
    collector_set.customize(customize_dict)
    customized_target = collector_set.targets.pop()

    assert f'FROM {level}' in customized_target.query

  def test_customize_raises_key_error_on_incorrect_level(self, collector_set):
    customize_dict = {
        'level': 'unknown-level',
    }

    with pytest.raises(KeyError):
      collector_set.customize(customize_dict)
