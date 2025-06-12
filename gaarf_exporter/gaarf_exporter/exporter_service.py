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
from typing import Literal, Optional, Union

import pydantic
import smart_open
import yaml
from gaarf import api_clients, report_fetcher

import gaarf_exporter
from gaarf_exporter import exceptions, registry


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
    account_update: Number between iterations to refresh account list.
  """

  host: str = '0.0.0.0'
  port: int = 8000
  expose_type: Literal['http', 'pushgateway'] = 'http'
  iterations: Optional[int] = None
  accounts_refresh_frequency: int = 4 * 24
  delay_minutes: int = 15
  namespace: str = 'googleads'
  job_name: str = 'gaarf_exporter'
  create_service_collectors: bool = True
  deduplicate_collectors: bool = True
  fetching_timeout: int = 120
  max_workers: Optional[int] = None
  account_update: Optional[int] = None


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

  account: Optional[str] = None
  ads_config_path: Union[os.PathLike[str], str, None] = None
  api_version: Optional[str] = None
  collectors: str = 'default'
  collectors_config: Union[os.PathLike[str], str, None] = None
  macros: Optional[dict[str, str]] = None
  runtime_options: GaarfExporterRuntimeOptions = GaarfExporterRuntimeOptions()


class GaarfExporterService:
  """Responsible for getting data from Ads and exposing it to Prometheus.

  Attributes:
    ads_config_path: Path to google-ads.yaml (local or remote).
    account: Child or MCC account.
    fetcher: Initialized AdsReportFetcher to perform fetching from Ads.
    accounts: All child accounts expanded from provided account.
  """

  def __init__(
    self,
    ads_config_path: Optional[os.PathLike[str] | str] = None,
    account: Optional[str] = None,
  ) -> None:
    """Initializes GaarfExporterService."""
    self.ads_config_path = ads_config_path
    self.account = account
    self._report_fetcher = None
    self._accounts = None
    self._convert_fake_report = False

  @property
  def fetcher(self) -> report_fetcher.AdsReportFetcher:
    """Initialized AdsReportFetcher for fetching data from Ads API."""
    if self._report_fetcher:
      return self._report_fetcher
    if not self.account or not self.ads_config_path:
      self._report_fetcher = report_fetcher.AdsReportFetcher(
        api_clients.BaseClient(api_clients.GOOGLE_ADS_API_VERSION)
      )
      self._convert_fake_report = True
      return self._report_fetcher
    with smart_open.open(self.ads_config_path, 'r', encoding='utf-8') as f:
      google_ads_config_dict = yaml.safe_load(f)
    if not self.account and not google_ads_config_dict.get('login_customer_id'):
      raise exceptions.GaarfExporterError(
        'No account found, please specify as `account` argument'
        'or add as login_customer_id in google-ads.yaml'
      )
    self._report_fetcher = report_fetcher.AdsReportFetcher(
      api_clients.GoogleAdsApiClient(config_dict=google_ads_config_dict)
    )
    return self._report_fetcher

  @property
  def accounts(self) -> list[str]:
    """All child accounts to get data from."""
    if self.account and not self._accounts:
      self._accounts = self.fetcher.expand_mcc(self.account)
    return self._accounts

  @accounts.setter
  def accounts(self, new_accounts: list[str]) -> None:
    """All child accounts to get data from."""
    self._accounts = new_accounts

  def generate_metrics(
    self,
    request: GaarfExporterRequest,
    exporter: gaarf_exporter.GaarfExporter,
    refresh_accounts: bool = False,
  ) -> None:
    """Generates metrics based on API request.

    Args:
      request: Complete request to fetch and expose data.
      exporter: Initialized GaarfExporter.
      refresh_accounts: Whether to refresh list of accounts under MCC.
    """
    active_collectors = registry.initialize_collectors(
      config_file=request.collectors_config,
      collector_names=request.collectors,
      create_service_collectors=request.runtime_options.create_service_collectors,
      deduplicate_collectors=request.runtime_options.deduplicate_collectors,
    )

    if refresh_accounts:
      logging.info('Refreshing accounts...')
      self.accounts = self.fetcher.expand_mcc(self.account)
    logging.info('Beginning export')
    start_export_time = time()
    exporter.export_started.set(start_export_time)
    for collector in active_collectors:
      logging.info('Exporting from collector: %s', collector.name)
      if not (query_text := collector.query):
        raise exceptions.GaarfExporterError(
          f'Missing query text for query "{collector.name}"'
        )
      if not self.accounts:
        report = self.fetcher.fetch(query_text, self.accounts)
      else:
        with futures.ThreadPoolExecutor(
          max_workers=request.runtime_options.max_workers
        ) as executor:
          future_to_account = {
            executor.submit(self.fetcher.fetch, query_text, account): account
            for account in self.accounts
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
            if self._convert_fake_report:
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
