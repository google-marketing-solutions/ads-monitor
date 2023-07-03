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
from gaarf.report import GaarfReport
from gaarf.query_editor import QuerySpecification

from gaarf_exporter.exporter import GaarfExporter

from prometheus_client.samples import Sample


@pytest.fixture
def gaarf_exporter():
    return GaarfExporter()


@pytest.fixture
def query():
    return "SELECT campaign.id, metrics.clicks AS clicks FROM campaign"


@pytest.fixture
def report(query):
    query_specification = QuerySpecification(query).generate()
    return GaarfReport(results=[[1, 10], [2, 20]],
                       column_names=["campaign_id", "clicks"],
                       query_specification=query_specification)


class TestGaaarfExporter:

    def test_gaarf_exporter_defaults(self, gaarf_exporter):
        assert gaarf_exporter.http_server_url
        assert gaarf_exporter.namespace
        assert gaarf_exporter.job_name
        assert not gaarf_exporter.pushgateway_url
        assert not gaarf_exporter.registry.get_target_info()

    def test_gaarf_exporter_exporter_report_returns_correct_metric_name(
            self, gaarf_exporter, report):
        gaarf_exporter.export(report)
        [metric] = list(gaarf_exporter.registry.collect())
        assert metric.name == "googleads_clicks"

    def test_gaarf_exporter_exporter_report_returns_correct_metric_documentation(
            self, gaarf_exporter, report):
        gaarf_exporter.export(report)
        [metric] = list(gaarf_exporter.registry.collect())
        assert metric.documentation == "clicks"
        assert len(metric.samples) == len(report.results)

    def test_gaarf_exporter_exporter_report_returns_correct_metric_samples(
            self, gaarf_exporter, report):
        gaarf_exporter.export(report)
        [metric] = list(gaarf_exporter.registry.collect())
        assert len(metric.samples) == len(report.results)

    @pytest.mark.parametrize('expected_samples', [[
        Sample(
            name='googleads_clicks', labels={'campaign_id': '1'}, value=10.0),
        Sample(
            name='googleads_clicks', labels={'campaign_id': '2'}, value=20.0)
    ]])
    def test_gaarf_exporter_exporter_report_returns_correct_metric_samples_values(
            self, gaarf_exporter, report, query, expected_samples):
        gaarf_exporter.export(report, query)
        [metric] = list(gaarf_exporter.registry.collect())
        assert metric.samples == expected_samples

    def test_gaarf_exporter_raises_value_error_when_url_not_provided(self):
        with pytest.raises(ValueError):
            GaarfExporter(http_server_url=None)

    def test_gaarf_exporter_raises_value_error_when_namespace_is_empty(self):
        with pytest.raises(ValueError):
            GaarfExporter(namespace=None)
