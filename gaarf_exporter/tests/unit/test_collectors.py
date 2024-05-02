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

from gaarf_exporter import collectors
from gaarf_exporter import target


class TestRegistry:

  @pytest.fixture(scope='class')
  def registry(self):
    return collectors.Registry()

  def test_default_collectors_returns_correct_target_names(self, registry):
    default_collectors = registry.default_collectors
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in default_collectors.targets} == expected

  def test_extract_collector_targets_returns_correct_collectors_from_registry(
      self, registry):
    actual = registry.find_collectors('performance,mapping')
    expected = {
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_all_collectors_from_subregistry(
      self, registry):
    actual = registry.find_collectors('default')
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_unique_collectors_from_registry_and_sub_registry(
      self, registry):
    actual = registry.find_collectors('default,performance,mapping')
    expected = {
        'conversion_action',
        'ad_disapprovals',
        'mapping',
        'performance',
    }

    assert {target.name for target in actual.targets} == expected

  def test_extract_collector_targets_returns_empty_set_when_collectors_are_not_found(
      self, registry):
    actual = registry.find_collectors('non-existing-collector')

    assert actual == collectors.CollectorSet()

  def test_add_collectors(self, registry):

    class SampleCollector:
      name = 'sample'
      target = target.Target(name='sample')

    registry.add_collectors([SampleCollector])
    found_collector_set = registry.find_collectors('sample')

    assert SampleCollector in found_collector_set
