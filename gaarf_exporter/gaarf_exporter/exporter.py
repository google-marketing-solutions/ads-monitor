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
"""Module for defining GaarfExporter.

GaarfExporter specifies whether to push Prometheus metrics converted from
GaarfReport.
"""

from __future__ import annotations

import logging
import time
from collections import abc
from collections.abc import Sequence

import gaarf
import prometheus_client

logger = logging.getLogger(__name__)

_METRICS = (
  'campaign.target_cpa.target_cpa_micros',
  'campaign_budget.amount_micros',
  'campaign.target_roas.target_roas',
  'campaign.manual_cpm',
  'campaign.manual_cpv',
  'campaign.maximize_conversion_value.target_roas',
  'campaign.maximize_conversions.target_cpa_micros',
  'campaign.target_spend.cpc_bid_ceiling_micros',
  'campaign.target_spend.target_spend_micros',
  'campaign.target_roas.cpc_bid_ceiling_micros',
  'campaign.target_roas.cpc_bid_floor_micros',
  'campaign.target_cpa.cpc_bid_ceiling_micros',
  'campaign.target_cpa.cpc_bid_floor_micros',
  'ad_group.cpc_bid_micros',
  'ad_group.cpm_bid_micros',
  'ad_group.cpv_bid_micros',
  'ad_group.effective_target_cpa_micros',
  'ad_group.effective_target_cpa_source',
  'ad_group.effective_target_roas',
  'ad_group.percent_cpc_bid_micros',
  'ad_group.target_cpa_micros',
  'ad_group.target_cpm_micros',
  'ad_group.target_roas',
  'campaign.optimization_score',
  'customer.optimization_score',
)


class GaarfExporter:
  """Exposes reports from Ads API in Prometheus format.

  Attributes:
    pushgateway_url: Address when Pushgateway is running.
    http_server_url: Address of HTTP server to expose data.
    namespace: Global prefix for all Prometheus metrics.
    job_name: Name of export job in Prometheus.
    expose_metrics_with_zero_values: Whether to send zero metrics.
  """

  def __init__(
    self,
    pushgateway_url: str | None = None,
    http_server_url: str = 'localhost:8000',
    namespace: str = 'googleads',
    job_name: str = 'gaarf_exporter',
    expose_metrics_with_zero_values: bool = False,
  ) -> None:
    """Initializes GaarfExporter to serve metrics.

    Args:
      pushgateway_url: Address when Pushgateway is running.
      http_server_url: Address of HTTP server to expose data.
      namespace: Global prefix for all Prometheus metrics.
      job_name: Name of export job in Prometheus.
      expose_metrics_with_zero_values: Whether to send zero metrics.

    Raises:
      ValueError: If there's no correct namespace or URL for metrics exposure.
    """
    if not pushgateway_url and not http_server_url:
      raise ValueError('please specify either pushgateway or http server')
    self.pushgateway_url = pushgateway_url if pushgateway_url else None
    self.http_server_url = http_server_url if http_server_url else None
    if not namespace:
      raise ValueError('namespace cannot be empty')
    self.namespace = namespace
    self.job_name = job_name
    self.expose_metrics_with_zero_values = expose_metrics_with_zero_values
    self.registry: prometheus_client.CollectorRegistry = (
      prometheus_client.CollectorRegistry()
    )
    self._init_service_metrics(self.namespace)
    logger.debug(str(self))

  def _init_service_metrics(self, namespace: str = 'gaarf_') -> None:
    """Initializes metrics related to export/fetching of reports.

    Args:
      namespace: Global prefix for service metrics.
    """
    self.total_export_time_gauge = self._define_gauge(
      'exporting_seconds', suffix='Remove', namespace=namespace
    )
    self.report_fetcher_gauge = self._define_gauge(
      name='report_fetching_seconds',
      suffix='Remove',
      labelnames=(
        'collector',
        'account',
      ),
      namespace=namespace,
    )
    self.delay_gauge = self._define_gauge(
      'delay_seconds', suffix='Remove', namespace=namespace
    )

  def reset_registry(self) -> None:
    """Removes all metrics from registry before export."""
    self.registry._collector_to_names.clear()
    self.registry._names_to_collectors.clear()

  def export(
    self,
    report: gaarf.report.GaarfReport,
    namespace: str | None = None,
    suffix: str = '',
    collector: str | None = None,
    account: str | None = None,
  ) -> None:
    """Exports data from report into the format consumable by Prometheus.

    Iterates over each row or report and creates gauges (metrics with labels
    attached to them) and either exposes them as HTTP server or pushes to
    Pushgateway.

    Args:
      report: Report with Google Ads data.
      namespace: Global prefix for all Prometheus metrics.
      suffix: Common identifier to be added to a series of metrics.
      collector: Name of one of GaarfExporter collectors attached to report.
      account: Google Ads account id.
    """
    if not report:
      return
    start = time.time()
    export_time_gauge = self._define_gauge(
      name='query_export_time_seconds',
      suffix='Remove',
      labelnames=(
        'collector',
        'account',
      ),
      namespace='gaarf',
    )
    api_requests_counter = self._define_counter(name='api_requests_count')
    metrics = self._define_metrics(
      report.query_specification, suffix, namespace
    )
    labels = self._define_labels(report.query_specification)
    for row in report:
      label_values = []
      for label in labels:
        if isinstance(row.get(label), abc.MutableSequence):
          label_value = ','.join([str(r) for r in row.get(label)])
        else:
          label_value = row.get(label)
        label_values.append(label_value)
      for name, metric in metrics.items():
        if (
          metric_value := getattr(row, name)
          or self.expose_metrics_with_zero_values
        ):
          if not isinstance(metric_value, str):
            metric.labels(*label_values).set(metric_value)
    end = time.time()
    export_time_gauge.labels(collector=collector, account=account).set(
      end - start
    )
    api_requests_counter.inc()
    if self.pushgateway_url:
      prometheus_client.push_to_gateway(
        self.pushgateway_url, job=self.job_name, registry=self.registry
      )
    else:
      self.registry.collect()

  def _define_metrics(
    self,
    query_specification: gaarf.query_editor.QuerySpecification,
    suffix: str,
    namespace: str,
  ) -> dict[str, prometheus_client.Gauge]:
    """Defines metrics to be exposed Prometheus.

    Metrics are defined based on query_specification of report that needs to
    be exposed. It takes into account both virtual and non-virtual columns.

    Args:
      query_specification:
        QuerySpecification that contains all information about the query.
      suffix: Common identifier to be added to a series of metrics.
      namespace: Global prefix for all Prometheus metrics.

    Returns:
      Mapping between metrics alias in report and Gauge.
    """
    metrics = {}
    labels = self._define_labels(query_specification)
    non_virtual_columns = self._get_non_virtual_columns(query_specification)
    for column, field in zip(non_virtual_columns, query_specification.fields):
      if 'metrics' in field or field in _METRICS:
        metrics[column] = self._define_gauge(column, suffix, labels, namespace)
    if virtual_columns := query_specification.virtual_columns:
      for column, field in virtual_columns.items():
        metrics[column] = self._define_gauge(column, suffix, labels, namespace)
    logger.debug('metrics: %s', metrics)
    return metrics

  def _define_labels(
    self, query_specification: gaarf.query_editor.QuerySpecification
  ) -> list[str]:
    """Defines names of labels to be attached to metrics.

    Label names are build based on column names of the report. Later on each
    label name gets its own value (i.e. customer_id=1, campaign_type=DISPLAY).

    Args:
      query_specification:
        QuerySpecification that contains all information about the query.
      suffix: Common identifier to be added to a series of metrics.

    Returns:
      All possible labels names that can be attached to metrics.
    """
    labelnames = []
    non_virtual_columns = self._get_non_virtual_columns(query_specification)
    for column, field in zip(non_virtual_columns, query_specification.fields):
      if 'metric' not in field and field not in _METRICS:
        labelnames.append(str(column))
    logger.debug('labelnames: %s', labelnames)
    return labelnames

  def _define_gauge(
    self,
    name: str,
    suffix: str,
    labelnames: Sequence[str] = (),
    namespace: str | None = None,
  ) -> prometheus_client.Gauge:
    """Defines Gauge metric to be created in Prometheus and add labels to it.

    Gauge has the following structure '<namespace>_<suffix>_<name>' and might
    look like this `googleads_disappoved_ads_count` meaning that it comes from
    `googleads` namespace (usually common for all metrics), `disapproved_ads`
    signifies that one or several metrics are coming from a single data fetch
    and usually grouped logically, while `count` represent the metric itself.

    Args:
      name: Name of the metric to be exposed to Prometheus (without prefix).
      suffix: Common identifier to be added to a series of metrics.
      labelsnames: Dimensions attached to metric (i.e. ad_group_id, account).
      namespace: Global prefix for all Prometheus metrics.
    Returns:
      An instance of Counter that associated with registry.
    """
    if not namespace:
      namespace = self.namespace
    if suffix and suffix != 'Remove':
      gauge_name = f'{namespace}_{suffix}_{name}'
    else:
      gauge_name = f'{namespace}_{name}'
    if gauge_name in self.registry._names_to_collectors:
      return self.registry._names_to_collectors.get(gauge_name)
    return prometheus_client.Gauge(
      name=gauge_name,
      documentation=name,
      labelnames=labelnames,
      registry=self.registry,
    )

  def _define_counter(self, name: str) -> prometheus_client.Counter:
    """Define Counter metric based on provided name.

    Args:
      name: Name of the metric to be exposed to Prometheus (without prefix).
    Returns:
      An instance of Counter that associated with registry.
    """
    counter_name = f'gaarf_{name}'
    if counter_name in self.registry._names_to_collectors:
      return self.registry._names_to_collectors.get(counter_name)
    return prometheus_client.Counter(
      name=counter_name, documentation=name, registry=self.registry
    )

  def _get_non_virtual_columns(
    self, query_specification: gaarf.query_editor.QuerySpecification
  ) -> list[str]:
    """Returns all non-virtual columns from query.

    Virtual columns have special handling during the export so they need
    to be removed.

    Args:
      query_specification:
        QuerySpecification that contains all information about the query.

    Returns:
      All columns from the query that are not virtual.
    """
    return [
      column
      for column in query_specification.column_names
      if column not in query_specification.virtual_columns
    ]

  def __str__(self) -> str:
    return (
      f'GaarfExporter(namespace={self.namespace}, ' f'job_name={self.job_name})'
    )
