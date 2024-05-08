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
import yaml

from gaarf_exporter import config
from gaarf_exporter import query_elements
from gaarf_exporter import target as query_target


class TestConfig:

  @pytest.fixture
  def simple_target(self):
    return query_target.Target(
        name='simple',
        metrics='impressions',
        level=query_target.TargetLevel.AD_GROUP)

  @pytest.fixture
  def simple_target_at_customer_level(self):
    return query_target.Target(
        name='simple_customer_level',
        metrics='impressions',
        level=query_target.TargetLevel.CUSTOMER)

  @pytest.fixture
  def no_metric_target(self):
    return query_target.ServiceTarget(
        name='mapping',
        metrics=[
            query_elements.Field(name='1', alias='info'),
        ],
        dimensions=[
            query_elements.Field(name='ad_group.id', alias='ad_group_id'),
            query_elements.Field(name='ad_group.name', alias='ad_group_name'),
            query_elements.Field(name='campaign.id', alias='campaign_id'),
            query_elements.Field(name='campaign.name', alias='campaign_name'),
            query_elements.Field(name='customer.id', alias='customer_id'),
            query_elements.Field(
                name='customer.descriptive_name', alias='account_name'),
        ],
        filters=('ad_group.status = ENABLED'
                 ' AND campaign.status = ENABLED'
                 ' AND customer.status = ENABLED'))

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
      self, simple_target, simple_target_at_customer_level):
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
                                               simple_target, tmp_path):
    simple_config = config.Config([no_metric_target, simple_target])

    output = tmp_path / 'config.yaml'
    simple_config.save(output)
    with open(output, encoding='utf-8') as f:
      loaded_config = yaml.safe_load(f)

    assert 'queries' in loaded_config.keys()
    assert tuple(loaded_config['queries']) == ('mapping', 'simple')
