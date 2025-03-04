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

"""Handles exporting all metrics based on a request."""

from __future__ import annotations

import logging
import os
from concurrent import futures
from time import time
from typing import Literal

import pydantic

import gaarf_exporter
from gaarf_exporter import bootstrap, registry


class GaarfExporterRuntimeOptions(pydantic.BaseModel):
  """Options to finetune exporting process.

  Attributes:
    expose_type: Type of exposition (http or pushgateway).
    host: Address of expose endpoint.
    port: Port of expose endpoint.
    iterations: Optional number of iterations to perform.
    accounts_refresh_frequency: How often to perform MCC expansion.
    delay_minutes: Delay between exports.
    namespace: Prefix for all metrics exposed to Prometheus.
    job_name: Job name attached to each metric.
    create_service_collectors:
      Whether to create corresponding service collectors.
    deduplicate_collectors:
      Whether to perform collector deduplication.
    fetching_timeout:
      Period to abort fetching if not data from Google Ads API returned.
    max_workers: Maximum number of parallel fetching from Google Ads API.
  """

  host: str = '0.0.0.0'
  port: int = 8000
  expose_type: Literal['http', 'pushgateway'] = 'http'
  iterations: int | None = None
  accounts_refresh_frequency: int = 4 * 24
  delay_minutes: int = 15
  namespace: str = 'googleads'
  job_name: str = 'gaarf_exporter'
  create_service_collectors: bool = True
  deduplicate_collectors: bool = True
  fetching_timeout: int = 120
  max_workers: int | None = None


class GaarfExporterRequest(pydantic.BaseModel):
  """Request to Google Ads API to perform export to Prometheus.

  Attributes:
    account: Google Ads account(s). Can be child accounts or MCCs.
    ads_config_path: Path to google-ads.yaml.
    api_version: Version of Ads API to use.
    collectors: One or several gaarf exporter collectors.
    collectors_config: Path to YAML file with collector definitions.
    macros: Optional macros to refine queries in collectors.
    runtime_options: Options to finetune exporting process.
  """

  account: str | None = None
  ads_config_path: os.PathLike[str] | str | None = None
  api_version: str | None = None
  collectors: str = 'default'
  collectors_config: os.PathLike[str] | str | None = None
  macros: dict[str, str] | None = None
  runtime_options: GaarfExporterRuntimeOptions = GaarfExporterRuntimeOptions()


def generate_metrics(
  request: GaarfExporterRequest, exporter: gaarf_exporter.GaarfExporter
):
  """Generates metrics based on API request."""
  active_collectors = registry.initialize_collectors(
    config_file=request.collectors_config,
    collector_names=request.collectors,
    create_service_collectors=request.runtime_options.create_service_collectors,
    deduplicate_collectors=request.runtime_options.deduplicate_collectors,
  )

  dependencies = bootstrap.inject_dependencies(
    ads_config_path=request.ads_config_path,
    api_version=request.api_version,
    account=request.account,
  )
  report_fetcher, accounts = (
    dependencies.get('report_fetcher'),
    dependencies.get('accounts'),
  )
  if request.account:
    accounts = report_fetcher.expand_mcc(request.account)
  logging.info('Beginning export')
  start_export_time = time()
  exporter.export_started.set(start_export_time)
  for collector in active_collectors:
    logging.info('Exporting from collector: %s', collector.name)
    if not (query_text := collector.query):
      raise ValueError(f'Missing query text for query "{collector.name}"')
    if not accounts:
      report = report_fetcher.fetch(query_text, accounts)
    else:
      with futures.ThreadPoolExecutor(
        max_workers=request.runtime_options.max_workers
      ) as executor:
        future_to_account = {
          executor.submit(report_fetcher.fetch, query_text, account): account
          for account in accounts
        }
        for future in futures.as_completed(
          future_to_account, timeout=request.runtime_options.fetching_timeout
        ):
          account = future_to_account[future]
          start = time()
          report = future.result()
          end = time()
          exporter.report_fetcher_gauge.labels(
            collector=collector.name, account=account
          ).set(end - start)
          if dependencies.get('convert_fake_report'):
            report.is_fake = False
          exporter.export(
            report=report,
            suffix=collector.suffix,
            collector=collector.name,
            account=account,
          )
  logging.info('Export completed')
  end_export_time = time()
  exporter.export_completed.set(end_export_time)
  exporter.total_export_time_gauge.set(end_export_time - start_export_time)
  exporter.delay_gauge.set(request.runtime_options.delay_minutes * 60)
