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

import pytest
import yaml

from gaarf_exporter.config import Config


@pytest.fixture
def simple_config(no_metric_target, simple_target):
    return Config.from_targets([no_metric_target, simple_target])


def test_create_config_from_one_simple_target_contains_one_query(
        simple_target):
    config = Config.from_targets([simple_target])
    assert len(config.queries) == 1


def test_create_service_target_when_regular_target_is_defined(
        simple_target, simple_target_at_customer_level, no_metric_target):
    config = Config.from_targets([
        simple_target, simple_target_at_customer_level])
    assert len(config.service_queries) == 1
    assert config.service_queries.get("mapping") == {
        'query': no_metric_target.query
    }
    assert (simple_target.level == config.service_targets.get('mapping').level)


def test_create_service_target_automatically(no_metric_target):
    config = Config.from_targets([no_metric_target])
    assert len(config.service_queries) == 1
    assert config.service_queries.get("mapping") == {
        'query': no_metric_target.query
    }


def test_write_to_yaml(simple_config):
    simple_config.save('/tmp/config.yaml')
    with open('/tmp/config.yaml') as f:
        loaded_config = yaml.safe_load(f)

    assert 'queries' in loaded_config.keys()
    assert tuple(loaded_config['queries']) == ('mapping', 'simple')
