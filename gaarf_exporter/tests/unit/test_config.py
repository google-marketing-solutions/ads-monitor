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

import yaml

from gaarf_exporter import config


class TestConfig:

  def test_config_contains_correct_regular_target_mapping(self, simple_target):
    test_config = config.Config([simple_target])

    assert test_config.regular_targets == {simple_target.name: simple_target}

  def test_config_creates_service_target_when_regular_target_is_defined(
      self, simple_target, simple_target_at_customer_level, no_metric_target):
    test_config = config.Config(
        [simple_target, simple_target_at_customer_level])

    assert test_config.service_queries == {
        'mapping': {
            'query': no_metric_target.query
        }
    }

  def test_config_creates_service_target_at_the_lowest_regular_target_level(
      self, simple_target, simple_target_at_customer_level, no_metric_target):
    test_config = config.Config(
        [simple_target, simple_target_at_customer_level])

    assert simple_target.level == (
        test_config.service_targets.get('mapping').level)

  def test_config_creates_service_target_when_only_service_target_is_provided(
      self, no_metric_target):
    test_config = config.Config([no_metric_target])

    assert test_config.service_queries == {
        'mapping': {
            'query': no_metric_target.query
        }
    }

  def test_save_config_returns_correct_queries(self, no_metric_target,
                                               simple_target):
    simple_config = config.Config([no_metric_target, simple_target])

    simple_config.save('/tmp/config.yaml')
    with open('/tmp/config.yaml', encoding='utf-8') as f:
      loaded_config = yaml.safe_load(f)

    assert 'queries' in loaded_config.keys()
    assert tuple(loaded_config['queries']) == ('mapping', 'simple')
