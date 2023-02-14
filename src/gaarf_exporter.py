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
# See the License for the specific language governing permissions and limitations under the License.

from typing import Callable, Optional

import logging
import re
from importlib import import_module
from prometheus_client import Gauge, push_to_gateway, CollectorRegistry
from gaarf.query_executor import AdsReportFetcher
from gaarf.query_editor import QuerySpecification

logger = logging.getLogger(__name__)


class GaarfExporter:

    report_fetcher: AdsReportFetcher = None
    pushgateway_url = None

    def __init__(self,
                 query_text: str,
                 namespace: str = "googleads",
                 suffix: str = "",
                 job_name: Optional[str] = None) -> None:
        if not self.pushgateway_url:
            raise ValueError(
                "Pushgateway if not found, specify via "
                "`GaarfExporter.options(pushgateway_url='<YOUR_PUSHGATEWAY_URL>'`"
            )
        if not self.report_fetcher:
            raise ValueError(
                "Instance of AdsReportFetcher is not found, specify via "
                "`GaarfExporter.options(report_fetcher=YOUR_REPORT_FETCHER_INSTANCE`"
            )
        self.query_specification = QuerySpecification(query_text).generate()
        if not namespace:
            raise ValueError("namespace cannot be empty")
        self.namespace = f"{namespace}" if namespace.endswith(
            "_") else f"{namespace}_"
        self.suffix = f"{suffix}_" if suffix else ""
        self.job_name = job_name
        self.registry: CollectorRegistry = CollectorRegistry()
        logger.debug(str(self))

    @classmethod
    def options(cls, **kwargs) -> None:
        for key, value in kwargs.items():
            if key in dir(cls):
                setattr(cls, key, value)

    def export(self,
               optimize_strategy: str = "NONE",
               callback: Callable = None):
        self._define_metrics()
        result = self.report_fetcher.fetch(self.query_specification,
                                           optimize_strategy)
        if callback:
            result = callback(result)
        for row in result:
            label_values = [row.get(label) for label in self.labelnames]
            for name, metric in self.metrics.items():
                metric.labels(*label_values).set(getattr(row, name))
        push_to_gateway(self.pushgateway_url,
                        job=self.job_name,
                        registry=self.registry)

    def _define_metrics(self) -> None:
        metrics = {}
        self._define_labels()
        for column, field in zip(self.query_specification.column_names,
                                 self.query_specification.fields):
            if "metric" in field:
                metrics[column] = self._define_gauge(column)
        if virtual_attributes := self.query_specification.virtual_attributes:
            for column, field in virtual_attributes.items():
                metrics[column] = self._define_gauge(column)
        self.metrics = metrics
        logger.debug(f"metrics: {self.metrics}")

    def _define_labels(self) -> None:
        labelnames = []
        for column, field in zip(self.query_specification.column_names,
                                 self.query_specification.fields):
            if "metric" not in field:
                labelnames.append(str(column))
        self.labelnames = labelnames
        logger.debug(f"labelsnames: {self.labelnames}")

    def _define_gauge(self, name: str) -> Gauge:
        return Gauge(name=f"{self.namespace}{self.suffix}{name}",
                     documentation=name,
                     labelnames=self.labelnames,
                     registry=self.registry)

    def __str__(self) -> str:
        return f"GaarfExporter(namespace={self.namespace}, suffix={self.suffix}, job_name={self.job_name})"


def import_custom_callback(callback_location: str,
                           callback_name: str) -> Callable:
    callback_location = re.sub("\.py$", "", callback_location)
    callback_location = re.sub("^\./", "", callback_location)
    callback_location = re.sub("/", ".", callback_location)
    callbacks_module = import_module(callback_location)
    return getattr(callbacks_module, callback_name)
