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

import argparse
import yaml
import logging
from rich.logging import RichHandler
from rich.pretty import pprint
from gaarf.api_clients import GoogleAdsApiClient
from gaarf.query_executor import AdsReportFetcher
from gaarf.utils import get_customer_ids

from gaarf_exporter import GaarfExporter, import_custom_callback


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c",
                        dest="config",
                        default="./gaarf_exporter.yaml")
    parser.add_argument("--log", "--loglevel", dest="loglevel", default="info")
    args = parser.parse_args()

    logging.basicConfig(format="%(message)s",
                        level=args.loglevel.upper(),
                        datefmt="%Y-%m-%d %H:%M:%S",
                        handlers=[RichHandler(rich_tracebacks=True)])
    logging.getLogger("google.ads.googleads.client").setLevel(logging.WARNING)
    logging.getLogger("smart_open.smart_open_lib").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logger = logging.getLogger(__name__)

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    queries = config.get("queries")
    settings = config.get("global")
    if not (namespace := settings.get("namespace")):
        namespace = "googleads"
    client = GoogleAdsApiClient(settings.get("auth"))
    report_fetcher = AdsReportFetcher(
        client, get_customer_ids(client, settings.get("mcc_id")))

    GaarfExporter.options(report_fetcher=report_fetcher,
                          pushgateway_url=settings.get("pushgateway_url"))
    for name, content in queries.items():
        suffix = content.get("suffix") or name
        job_name = content.get("job_name") or name
        if callback_name := content.get("custom_callback"):
            custom_callback = import_custom_callback(
                callback_location=settings.get("custom_callbacks_location"),
                callback_name=callback_name)
        else:
            custom_callback = None
        logger.info(f"Running query {name}")
        GaarfExporter(query_text=content.get("query"),
                      namespace=namespace,
                      suffix=suffix,
                      job_name=job_name).export(callback=custom_callback)
