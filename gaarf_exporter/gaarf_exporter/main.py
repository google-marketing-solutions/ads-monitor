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
"""Entrypoint for running GaarfExporter.

Defines GaarfExporter collectors, fetches data from Google Ads API
and expose them to Prometheus.
"""

from __future__ import annotations

import argparse
import logging
from concurrent import futures
from time import sleep, time

import prometheus_client
from gaarf.cli import utils as gaarf_utils

from gaarf_exporter import bootstrap, exporter, registry


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('--account', dest='account', default=None)
  parser.add_argument('-c', '--config', dest='config', default=None)
  parser.add_argument('--ads-config', dest='ads_config', default=None)
  parser.add_argument('--api-version', dest='api_version', default=None)
  parser.add_argument('--log', '--loglevel', dest='loglevel', default='info')
  parser.add_argument(
    '--http_server.address', dest='address', default='0.0.0.0'
  )
  parser.add_argument('--http_server.port', dest='port', type=int, default=8000)
  parser.add_argument(
    '--pushgateway.address', dest='pushgateway_address', default=None
  )
  parser.add_argument(
    '--pushgateway.port', dest='pushgateway_port', default=None
  )
  parser.add_argument('--logger', dest='logger', default='local')
  parser.add_argument('--iterations', dest='iterations', default=None, type=int)
  parser.add_argument(
    '--update-accounts-every-n-iterations',
    dest='iterations_left',
    default=4 * 24,
    type=int,
  )
  parser.add_argument('--delay-minutes', dest='delay', type=int, default=15)
  parser.add_argument(
    '--expose-metrics-with-zero-values',
    dest='zero_value_metrics',
    action='store_true',
  )
  parser.add_argument('--namespace', dest='namespace', default='googleads')
  parser.add_argument('--max-parallel', dest='parallel', default=None)
  parser.add_argument('--collectors', dest='collectors', default='default')
  parser.add_argument(
    '--no-deduplicate-collectors', dest='deduplicate', action='store_false'
  )
  parser.add_argument(
    '--no-service-collectors', dest='service_collectors', action='store_false'
  )
  parser.set_defaults(deduplicate=True)
  parser.set_defaults(service_collectors=True)
  args_bag = parser.parse_known_args()
  args = args_bag[0]

  logger = gaarf_utils.init_logging(
    loglevel=args.loglevel.upper(), logger_type=args.logger
  )

  params = gaarf_utils.ParamsParser(
    [
      'macro',
      'sql',
      'template',
    ]
  ).parse(args_bag[1])

  active_collectors = registry.initialize_collectors(
    config_file=args.config,
    collector_names=args.collectors,
    create_service_collectors=args.service_collectors,
    deduplicate_collectors=args.deduplicate,
  )

  dependencies = bootstrap.inject_dependencies(
    ads_config_path=args.ads_config,
    api_version=args.api_version,
    account=args.account,
  )
  report_fetcher, accounts = (
    dependencies.get('report_fetcher'),
    dependencies.get('accounts'),
  )
  gaarf_exporter_options = {
    'expose_metrics_with_zero_values': args.zero_value_metrics,
    'namespace': args.namespace,
  }

  if args.pushgateway_address and args.pushgateway_port:
    gaarf_exporter = exporter.GaarfExporter(
      pushgateway_url=f'{args.pushgateway_address}:{args.pushgateway_port}',
      **gaarf_exporter_options,
    )
  elif args.address and args.port:
    gaarf_exporter = exporter.GaarfExporter(
      http_server_url=f'{args.address}:{args.port}', **gaarf_exporter_options
    )
  else:
    raise ValueError(
      'Specify option for exposing data to Prometheus '
      '- either http_server or pushgateway'
    )

  if gaarf_exporter.http_server_url and not gaarf_exporter.pushgateway_url:
    prometheus_client.start_http_server(
      port=args.port, addr=args.address, registry=gaarf_exporter.registry
    )
    logger.info(
      'Started http_server at http://%s', gaarf_exporter.http_server_url
    )
  while True:
    if iterations_left := args.iterations_left:
      iterations_left -= 1
    if accounts and iterations_left == 0:
      accounts = report_fetcher.expand_mcc(args.account)
      iterations_left = args.iterations_left
    start_export_time = time()
    if not args.config and params:
      active_collectors.customize(params)
    for collector in active_collectors:
      if not (query_text := collector.query):
        raise ValueError(f'Missing query text for query "{collector.name}"')
      logger.info('Beginning export')
      if not accounts:
        report = report_fetcher.fetch(query_text, accounts)
      else:
        with futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
          future_to_account = {
            executor.submit(
              report_fetcher.fetch, collector.query, account
            ): account
            for account in accounts
          }
          for future in futures.as_completed(future_to_account):
            account = future_to_account[future]
            start = time()
            report = future.result()
            end = time()
            gaarf_exporter.report_fetcher_gauge.labels(
              collector=collector.name, account=account
            ).set(end - start)
            if dependencies.get('convert_fake_report'):
              report.is_fake = False
            logging.info(
              'Started export for query "[%s]" for account "[%s]"',
              collector.name,
              account,
            )
            gaarf_exporter.export(
              report=report,
              suffix=collector.suffix,
              collector=collector.name,
              account=account,
            )
            logging.info(
              'Ended export for query "[%s]" for account "[%s]"',
              collector.name,
              account,
            )
    logger.info('Export completed')
    end_export_time = time()
    gaarf_exporter.total_export_time_gauge.set(
      end_export_time - start_export_time
    )
    gaarf_exporter.delay_gauge.set(args.delay * 60)

    if gaarf_exporter.pushgateway_url:
      logger.info(
        'Saving data to pushgateway at %s', gaarf_exporter.pushgateway_url
      )
      exit()
    sleep(int(args.delay) * 60)
    if iterations := args.iterations:
      iterations -= 1
      if iterations == 0:
        break


if __name__ == '__main__':
  main()
