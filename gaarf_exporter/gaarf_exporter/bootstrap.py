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
"""Module for building necessary dependencies to run Gaarf Exporter."""

from __future__ import annotations

import smart_open
import yaml
from gaarf import api_clients, query_executor


def inject_dependencies(
  api_version: str | None = None,
  ads_config_path: str | None = None,
  account: str | None = None,
) -> dict[str, query_executor.AdsReportFetcher | list[str] | bool | None]:
  """Creates necessary dependencies to run export data.

  Args:
    api_version: Version of Google Ads API.
    ads_config_path: Path to google-ads.yaml file.
    account: Google Ads manager or child account.

  Returns:
    A dictionary with injected dependencies.

  Raises:
    ValueError: If there's no Google Ads account to get data from.
  """
  api_version = api_version or api_clients.GOOGLE_ADS_API_VERSION
  if not account or not ads_config_path:
    client = api_clients.BaseClient(api_version)
    report_fetcher = query_executor.AdsReportFetcher(client)
    accounts = None
    return {
      'report_fetcher': report_fetcher,
      'accounts': accounts,
      'convert_fake_report': True,
    }
  with smart_open.open(ads_config_path, 'r', encoding='utf-8') as f:
    google_ads_config_dict = yaml.safe_load(f)
  if not account:
    account = google_ads_config_dict.get('login_customer_id')
  if not account:
    raise ValueError(
      'No account found, please specify via --account CLI flag'
      'or add as login_customer_id in google-ads.yaml'
    )
  client = api_clients.GoogleAdsApiClient(
    config_dict=google_ads_config_dict, version=api_version
  )
  report_fetcher = query_executor.AdsReportFetcher(client)
  accounts = report_fetcher.expand_mcc(account)
  return {
    'report_fetcher': report_fetcher,
    'accounts': accounts,
    'convert_fake_report': False,
  }
