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

from typing import Dict, List, Optional, Sequence

import logging
from prometheus_client import Gauge, push_to_gateway, CollectorRegistry
from gaarf.query_editor import QuerySpecification
from gaarf.report import GaarfReport

logger = logging.getLogger(__name__)


class GaarfExporter:

    def __init__(self,
                 pushgateway_url: Optional[str] = None,
                 http_server_url: str = "localhost:8000",
                 namespace: str = "googleads",
                 job_name: str = "gaarf_exporter",
                 expose_metrics_with_zero_values: bool = False) -> None:
        if not pushgateway_url and not http_server_url:
            raise ValueError(
                "please specify either pushgateway or http server")
        self.pushgateway_url = pushgateway_url if pushgateway_url else None
        self.http_server_url = http_server_url if http_server_url else None
        if not namespace:
            raise ValueError("namespace cannot be empty")
        self.namespace = f"{namespace}" if namespace.endswith(
            "_") else f"{namespace}_"
        self.job_name = job_name
        self.expose_metrics_with_zero_values = expose_metrics_with_zero_values
        self.registry: CollectorRegistry = CollectorRegistry()
        logger.debug(str(self))

    def reset_registry(self):
        self.registry = CollectorRegistry()

    def export(self,
               report: GaarfReport,
               namespace: Optional[str] = None,
               suffix: str = "") -> None:
        metrics = self._define_metrics(report.query_specification, suffix)
        labels = self._define_labels(report.query_specification)
        if not report:
            return
        for row in report:
            label_values = [row.get(label) for label in labels]
            for name, metric in metrics.items():
                if (metric_value := getattr(row, name)
                        or self.expose_metrics_with_zero_values):
                    metric.labels(*label_values).set(metric_value)
        if self.pushgateway_url:
            push_to_gateway(self.pushgateway_url,
                            job=self.job_name,
                            registry=self.registry)
        else:
            self.registry.collect()

    # TODO (amarkin): Metric shouldn't be defined solely on query_specification
    # i.e. campaign_budget is a dimension but should be treated as metric
    def _define_metrics(self, query_specification: QuerySpecification,
                        suffix: str) -> Dict[str, Gauge]:
        metrics = {}
        labels = self._define_labels(query_specification)
        non_virtual_columns = self._get_non_virtual_columns(
            query_specification)
        for column, field in zip(non_virtual_columns,
                                 query_specification.fields):
            if "metrics" in field:
                metrics[column] = self._define_gauge(column, suffix, labels)
        if virtual_columns := query_specification.virtual_columns:
            for column, field in virtual_columns.items():
                metrics[column] = self._define_gauge(column, suffix, labels)
        logger.debug(f"metrics: {metrics}")
        return metrics

    def _define_labels(self,
                       query_specification: QuerySpecification) -> List[str]:
        labelnames = []
        non_virtual_columns = self._get_non_virtual_columns(
            query_specification)
        for column, field in zip(non_virtual_columns,
                                 query_specification.fields):
            if "metric" not in field:
                labelnames.append(str(column))
        logger.debug(f"labelnames: {labelnames}")
        return labelnames

    def _define_gauge(self, name: str, suffix: str,
                      labelnames: Sequence[str]) -> Gauge:

        if suffix and suffix != "Remove":
            gauge_name = f"{self.namespace}{suffix}_{name}"
        else:
            gauge_name = f"{self.namespace}{name}"
        return Gauge(name=gauge_name,
                     documentation=name,
                     labelnames=labelnames,
                     registry=self.registry)

    def _get_non_virtual_columns(
            self, query_specification: QuerySpecification) -> List[str]:
        return [
            column for column in query_specification.column_names
            if column not in query_specification.virtual_columns
        ]

    def __str__(self) -> str:
        return f"GaarfExporter(namespace={self.namespace}, job_name={self.job_name})"
