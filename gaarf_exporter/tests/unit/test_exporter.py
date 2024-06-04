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
from gaarf.query_editor import QuerySpecification
from gaarf.report import GaarfReport
from gaarf_exporter.exporter import GaarfExporter
from prometheus_client import samples


class TestGaaarfExporter:
  @pytest.fixture
  def gaarf_exporter(self):
    return GaarfExporter()

  @pytest.fixture
  def report(self):
    query = 'SELECT campaign.id, metrics.clicks AS clicks FROM campaign'
    query_specification = QuerySpecification(query).generate()
    return GaarfReport(
      results=[
        [1, 10],
        [2, 20],
      ],
      column_names=[
        'campaign_id',
        'clicks',
      ],
      query_specification=query_specification,
    )

  @pytest.fixture
  def report_with_virtual_column(self):
    query = 'SELECT campaign.id, 1 AS info FROM campaign'
    query_specification = QuerySpecification(query).generate()
    return GaarfReport(
      results=[
        [1, 1],
        [2, 1],
      ],
      column_names=[
        'campaign_id',
        'info',
      ],
      query_specification=query_specification,
    )

  def test_gaarf_exporter_has_default_values(self, gaarf_exporter):
    assert gaarf_exporter.http_server_url
    assert gaarf_exporter.namespace
    assert gaarf_exporter.job_name
    assert not gaarf_exporter.pushgateway_url
    assert not gaarf_exporter.registry.get_target_info()

  def test_export_returns_correct_metric_name(self, gaarf_exporter, report):
    gaarf_exporter.export(report)
    metrics = list(gaarf_exporter.registry.collect())
    assert 'googleads_clicks' in [metric.name for metric in metrics]

  def test_export_returns_correct_metric_name_with_suffix_and_namespace(
    self, gaarf_exporter, report
  ):
    namespace = 'ads'
    suffix = 'performance'
    gaarf_exporter.export(report=report, namespace=namespace, suffix=suffix)
    metrics = list(gaarf_exporter.registry.collect())
    assert f'{namespace}_{suffix}_clicks' in [metric.name for metric in metrics]

  def test_export_returns_correct_virtual_metric_name(
    self, gaarf_exporter, report_with_virtual_column
  ):
    gaarf_exporter.export(report=report_with_virtual_column)
    metrics = list(gaarf_exporter.registry.collect())
    assert 'googleads_info' in [metric.name for metric in metrics]

  def test_export_returns_correct_metric_documentation(
    self, gaarf_exporter, report
  ):
    gaarf_exporter.export(report)
    metrics = list(gaarf_exporter.registry.collect())
    assert 'clicks' in [metric.documentation for metric in metrics]

  def test_export_returns_correct_metric_samples(self, gaarf_exporter, report):
    gaarf_exporter.export(report)
    metrics = list(gaarf_exporter.registry.collect())
    for metric in metrics:
      if metric.name == 'googleads_clicks':
        assert len(metric.samples) == len(report.results)

  @pytest.mark.parametrize(
    'expected_samples',
    [
      [
        samples.Sample(
          name='googleads_clicks', labels={'campaign_id': '1'}, value=10.0
        ),
        samples.Sample(
          name='googleads_clicks', labels={'campaign_id': '2'}, value=20.0
        ),
      ]
    ],
  )
  def test_export_returns_correct_metric_samples_values(
    self, gaarf_exporter, report, expected_samples
  ):
    gaarf_exporter.export(report)
    metrics = list(gaarf_exporter.registry.collect())
    for metric in metrics:
      if metric.name == 'googleads_clicks':
        assert metric.samples == expected_samples

  def test_gaarf_exporter_raises_value_error_when_url_not_provided(self):
    with pytest.raises(ValueError):
      GaarfExporter(http_server_url=None)

  def test_gaarf_exporter_raises_value_error_when_namespace_is_empty(self):
    with pytest.raises(ValueError):
      GaarfExporter(namespace=None)
