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

from collections import abc
import logging
from prometheus_client import Counter, Gauge, push_to_gateway, CollectorRegistry
from gaarf.query_editor import QuerySpecification
from gaarf.report import GaarfReport
import time

logger = logging.getLogger(__name__)

METRICS = ("campaign.target_cpa.target_cpa_micros",
           "campaign_budget.amount_micros", "campaign.target_roas.target_roas",
           "campaign.manual_cpm", "campaign.manual_cpv",
           "campaign.maximize_conversion_value.target_roas",
           "campaign.maximize_conversions.target_cpa_micros",
           "campaign.target_spend.cpc_bid_ceiling_micros",
           "campaign.target_spend.target_spend_micros",
           "campaign.target_roas.cpc_bid_ceiling_micros",
           "campaign.target_roas.cpc_bid_floor_micros",
           "campaign.target_cpa.cpc_bid_ceiling_micros",
           "campaign.target_cpa.cpc_bid_floor_micros",
           "ad_group.cpc_bid_micros", "ad_group.cpm_bid_micros",
           "ad_group.cpv_bid_micros", "ad_group.effective_target_cpa_micros",
           "ad_group.effective_target_cpa_source",
           "ad_group.effective_target_roas", "ad_group.percent_cpc_bid_micros",
           "ad_group.target_cpa_micros", "ad_group.target_cpm_micros",
           "ad_group.target_roas", "campaign.optimization_score",
           "customer.optimization_score")


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
        self._init_service_metrics()
        logger.debug(str(self))

    def _init_service_metrics(self, namespace: str = "gaarf_") -> None:
        self.total_export_time_gauge = self._define_gauge("exporting_seconds",
                                                          suffix="Remove",
                                                          namespace=namespace)
        self.report_fetcher_gauge = self._define_gauge(
            name="report_fetching_seconds",
            suffix="Remove",
            labelnames=("collector", "account"),
            namespace=namespace)
        self.delay_gauge = self._define_gauge("delay_seconds",
                                              suffix="Remove",
                                              namespace=namespace)

    def reset_registry(self):
        self.registry._collector_to_names.clear()
        self.registry._names_to_collectors.clear()

    def export(self,
               report: GaarfReport,
               namespace: Optional[str] = None,
               suffix: str = "",
               collector: Optional[str] = None,
               account: Optional[str] = None) -> None:
        start = time.time()
        export_time_gauge = self._define_gauge(
            name="query_export_time_seconds",
            suffix="Remove",
            labelnames=("collector", "account"),
            namespace="gaarf_")
        api_requests_counter = self._define_counter(name="api_requests_count")
        metrics = self._define_metrics(report.query_specification, suffix)
        labels = self._define_labels(report.query_specification)
        if not report:
            return
        for row in report:
            label_values = []
            for label in labels:
                if isinstance(row.get(label), abc.MutableSequence):
                    label_value = ",".join([str(r) for r in row.get(label)])
                else:
                    label_value = row.get(label)
                label_values.append(label_value)
            for name, metric in metrics.items():
                if (metric_value := getattr(row, name)
                        or self.expose_metrics_with_zero_values):
                    if not isinstance(metric_value, str):
                        metric.labels(*label_values).set(metric_value)
        end = time.time()
        export_time_gauge.labels(collector=collector,
                                 account=account).set(end - start)
        api_requests_counter.inc()
        if self.pushgateway_url:
            push_to_gateway(self.pushgateway_url,
                            job=self.job_name,
                            registry=self.registry)
        else:
            self.registry.collect()

    def _define_metrics(self, query_specification: QuerySpecification,
                        suffix: str) -> Dict[str, Gauge]:
        metrics = {}
        labels = self._define_labels(query_specification)
        non_virtual_columns = self._get_non_virtual_columns(
            query_specification)
        for column, field in zip(non_virtual_columns,
                                 query_specification.fields):
            if "metrics" in field or field in METRICS:
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
            if "metric" not in field and field not in METRICS:
                labelnames.append(str(column))
        logger.debug(f"labelnames: {labelnames}")
        return labelnames

    def _define_gauge(self,
                      name: str,
                      suffix: str,
                      labelnames: Sequence[str] = (),
                      namespace: Optional[str] = None) -> Gauge:

        if not namespace:
            namespace = self.namespace
        if suffix and suffix != "Remove":
            gauge_name = f"{namespace}{suffix}_{name}"
        else:
            gauge_name = f"{namespace}{name}"
        if gauge_name in self.registry._names_to_collectors:
            return self.registry._names_to_collectors.get(gauge_name)
        return Gauge(name=gauge_name,
                     documentation=name,
                     labelnames=labelnames,
                     registry=self.registry)

    def _define_counter(self, name: str) -> Counter:
        counter_name = f"gaarf_{name}"
        if counter_name in self.registry._names_to_collectors:
            return self.registry._names_to_collectors.get(counter_name)
        return Counter(name=counter_name,
                       documentation=name,
                       registry=self.registry)

    def _get_non_virtual_columns(
            self, query_specification: QuerySpecification) -> List[str]:
        return [
            column for column in query_specification.column_names
            if column not in query_specification.virtual_columns
        ]

    def __str__(self) -> str:
        return f"GaarfExporter(namespace={self.namespace}, job_name={self.job_name})"
