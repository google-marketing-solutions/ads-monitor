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

from typing import Dict, List, Optional, Union
from gaarf.api_clients import BaseClient, GoogleAdsApiClient
from gaarf.query_executor import AdsReportFetcher
from smart_open import open
import yaml


def inject_dependencies(
    ads_config_path: Optional[str] = None,
    api_version: int = 13,
    account: Optional[str] = None
) -> Dict[str, Union[AdsReportFetcher, Optional[List[str]], bool]]:
    if not account:
        client = BaseClient(version=f"v{api_version}")
        report_fetcher = AdsReportFetcher(client)
        accounts = None
        return {
            "report_fetcher": report_fetcher,
            "accounts": accounts,
            "convert_fake_report": True
        }
    with open(ads_config_path, "r", encoding="utf-8") as f:
        google_ads_config_dict = yaml.safe_load(f)
    if not (account := account):
        account = google_ads_config_dict.get("login_customer_id")
    if not account:
        raise ValueError(
            "No account found, please specify via --account CLI flag"
            "or add as login_customer_id in google-ads.yaml")
    client = GoogleAdsApiClient(config_dict=google_ads_config_dict,
                                version=f"v{api_version}")
    report_fetcher = AdsReportFetcher(client)
    accounts = report_fetcher.expand_mcc(account)
    return {
        "report_fetcher": report_fetcher,
        "accounts": accounts,
        "convert_fake_report": False
    }
