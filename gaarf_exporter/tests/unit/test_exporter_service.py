# Copyright 2025 Google LLC
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

# pylint: disable=C0330, g-bad-import-order, g-multiple-import

import logging
import pathlib

import pytest
import yaml

from gaarf_exporter import exporter, exporter_service, registry

_SCRIPT_DIR = pathlib.Path(__file__).parent
COLLECTORS_REGISTRY = registry.Registry.from_collector_definitions()


def _generate_collectors(property_name: str) -> list[str]:
  return [
    collector.name for collector in getattr(COLLECTORS_REGISTRY, property_name)
  ]


class TestGaarfExporterService:
  @pytest.fixture(scope='class')
  def service(self):
    return exporter_service.GaarfExporterService()

  @pytest.mark.parametrize('collector', _generate_collectors('all_collectors'))
  def test_generate_metrics_from_collector_name_returns_correct_results(
    self, service, caplog, collector
  ):
    caplog.set_level(logging.INFO)
    test_exporter = exporter.GaarfExporter()
    test_request = exporter_service.GaarfExporterRequest(collectors=collector)

    service.generate_metrics(test_request, test_exporter)

    assert 'Beginning export' in caplog.text
    assert collector in caplog.text
    assert 'Export completed' in caplog.text

  @pytest.mark.parametrize(
    'collector', _generate_collectors('all_subregistries')
  )
  def test_generate_metrics_from_subregistry_name_returns_correct_results(
    self, service, caplog, collector
  ):
    caplog.set_level(logging.INFO)
    test_exporter = exporter.GaarfExporter()
    test_request = exporter_service.GaarfExporterRequest(collectors=collector)

    service.generate_metrics(test_request, test_exporter)

    assert 'Beginning export' in caplog.text
    assert collector in caplog.text
    assert 'Export completed' in caplog.text

  def test_generate_metrics_from_all_collectors_returns_correct_results(
    self, service, caplog
  ):
    caplog.set_level(logging.INFO)
    test_exporter = exporter.GaarfExporter()
    test_request = exporter_service.GaarfExporterRequest(collectors='all')

    service.generate_metrics(test_request, test_exporter)

    assert 'Beginning export' in caplog.text
    for collector in COLLECTORS_REGISTRY.all_collectors:
      assert collector.name in caplog.text
    assert 'Export completed' in caplog.text

  def test_generate_metrics_from_config_returns_correct_results(
    self, service, caplog
  ):
    caplog.set_level(logging.INFO)
    config_location = f'{_SCRIPT_DIR}/test_gaarf_exporter.yaml'
    with open(config_location, 'r', encoding='utf-8') as f:
      collector_data = yaml.safe_load(f)
    test_exporter = exporter.GaarfExporter()
    test_request = exporter_service.GaarfExporterRequest(
      collectors_path=config_location,
    )

    service.generate_metrics(test_request, test_exporter)

    assert 'Beginning export' in caplog.text
    for collector in collector_data:
      assert collector.get('name') in caplog.text
    assert 'Export completed' in caplog.text
