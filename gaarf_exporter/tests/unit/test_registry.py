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
from gaarf_exporter import collector as query_collector
from gaarf_exporter import registry as collector_registry


class TestRegistry:
  @pytest.fixture(scope='class')
  def registry(self):
    return collector_registry.Registry.from_collector_definitions()

  def test_default_collectors_returns_correct_target_names(self, registry):
    default_collectors = registry.default_collectors
    expected = {
      'conversion_action',
      'mapping',
      'performance',
    }

    assert {collector.name for collector in default_collectors} == expected

  def test_extract_collector_targets_returns_correct_collectors_from_registry(
    self, registry
  ):
    actual = registry.find_collectors('performance,mapping')
    expected = {
      'mapping',
      'performance',
    }

    assert {collector.name for collector in actual} == expected

  def test_extract_collector_targets_returns_all_collectors_from_subregistry(
    self, registry
  ):
    actual = registry.find_collectors('default')
    expected = {
      'conversion_action',
      'mapping',
      'performance',
    }

    assert {collector.name for collector in actual} == expected

  def test_extract_collector_targets_returns_unique_collectors_from_registry_and_sub_registry(
    self, registry
  ):
    actual = registry.find_collectors('default,performance,mapping')
    expected = {
      'conversion_action',
      'mapping',
      'performance',
    }

    assert {collector.name for collector in actual} == expected

  def test_extract_collector_targets_returns_empty_set_when_collectors_are_not_found(
    self, registry
  ):
    actual = registry.find_collectors('non-existing-collector')

    assert actual == collector_registry.CollectorSet()


class TestCollectorSet:
  @pytest.fixture
  def simple_target(self):
    return query_collector.Collector(
      name='simple',
      metrics='impressions',
      level=query_collector.CollectorLevel.AD_GROUP,
    )

  @pytest.fixture
  def simple_target_at_customer_level(self):
    return query_collector.Collector(
      name='simple_customer_level',
      metrics='impressions',
      level=query_collector.CollectorLevel.CUSTOMER,
    )

  @pytest.fixture
  def no_metric_target(self):
    return query_collector.ServiceCollector(
      name='mapping',
      metrics=[
        query_collector.Field(name='1', alias='info'),
      ],
      dimensions=[
        query_collector.Field(name='ad_group.id', alias='ad_group_id'),
        query_collector.Field(name='ad_group.name', alias='ad_group_name'),
        query_collector.Field(name='campaign.id', alias='campaign_id'),
        query_collector.Field(name='campaign.name', alias='campaign_name'),
        query_collector.Field(name='customer.id', alias='customer_id'),
        query_collector.Field(
          name='customer.descriptive_name', alias='account_name'
        ),
      ],
      filters=(
        'ad_group.status = ENABLED'
        ' AND campaign.status = ENABLED'
        ' AND customer.status = ENABLED'
      ),
    )

  @pytest.fixture
  def collector_set(self):
    return collector_registry.CollectorSet(
      {query_collector.Collector(name='test', metrics='clicks')},
      service_collectors=False,
    )

  def test_collector_set_performs_deduplication(
    self, simple_target, simple_target_at_customer_level
  ):
    collector_set = collector_registry.CollectorSet(
      {simple_target, simple_target_at_customer_level}
    )
    assert simple_target_at_customer_level not in collector_set
    assert simple_target in collector_set

  def test_collector_set_generates_service_target(
    self, simple_target, no_metric_target
  ):
    collector_set = collector_registry.CollectorSet(
      {
        simple_target,
      }
    )
    assert no_metric_target in collector_set

  def test_customize_returns_modified_target_start_end_date(
    self, collector_set
  ):
    start_date = '2024-01-01'
    end_date = '2024-01-01'
    customize_dict = {
      'start_date': start_date,
      'end_date': end_date,
    }
    collector_set.customize(customize_dict)
    customized_collector = collector_set.collectors.pop()

    assert f"segments.date BETWEEN '{start_date}' AND '{end_date}'" in (
      customized_collector.query
    )

  @pytest.mark.parametrize('level', ['ad_group', 'campaign', 'customer'])
  def test_customize_returns_modified_target_level(self, collector_set, level):
    customize_dict = {
      'level': level,
    }
    collector_set.customize(customize_dict)
    customized_collector = collector_set.collectors.pop()

    assert f'FROM {level}' in customized_collector.query

  def test_customize_raises_key_error_on_incorrect_level(self, collector_set):
    customize_dict = {
      'level': 'unknown-level',
    }

    with pytest.raises(KeyError):
      collector_set.customize(customize_dict)


def test_initialize_collectors_from_config_file_loads_data_from_file(tmp_path):
  config_file = tmp_path / 'config.yaml'
  config = [
    {'name': 'performance', 'query': 'SELECT customer.id FROM customer'}
  ]
  with open(config_file, mode='w', encoding='utf-8') as f:
    yaml.dump(config, f)
  collectors = collector_registry.initialize_collectors(config_file=config_file)
  assert {
    'performance',
  } == {c.name for c in collectors}


def test_initialize_collectors_from_collector_names_returns_correct_collectors(
  tmp_path,
):
  collectors = collector_registry.initialize_collectors(
    collector_names='performance', create_service_collectors=False
  )
  assert {
    'performance',
  } == {c.name for c in collectors}


def test_initialize_collectors_from_collector_names_returns_correct_collectors(
  tmp_path,
):
  collectors = collector_registry.initialize_collectors(
    collector_names='performance', create_service_collectors=True
  )
  assert {'performance', 'mapping'} == {c.name for c in collectors}
