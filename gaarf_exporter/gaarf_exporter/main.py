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
'''Entrypoint for running GaarfExporter.

Defines GaarfExporter collectors, fetches data from Google Ads API
and expose them to Prometheus.

'''
from __future__ import annotations

import argparse
import logging
from concurrent import futures
from time import sleep
from time import time

import yaml
from gaarf.cli.utils import init_logging
from gaarf.cli.utils import ParamsParser
from prometheus_client import start_http_server
from smart_open import open

from gaarf_exporter import collectors
from gaarf_exporter.bootstrap import inject_dependencies
from gaarf_exporter.config import Config
from gaarf_exporter.exporter import GaarfExporter
from gaarf_exporter.util import find_relative_metrics


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('--account', dest='account', default=None)
  parser.add_argument('-c', dest='config', default=None)
  parser.add_argument('--ads-config', dest='ads_config', default=None)
  parser.add_argument('--api-version', dest='api_version', default=14)
  parser.add_argument('--queries.exclude', dest='exclude_queries', default=None)
  parser.add_argument('--queries.include', dest='include_queries', default=None)
  parser.add_argument('--log', '--loglevel', dest='loglevel', default='info')
  parser.add_argument(
      '--http_server.address', dest='address', default='0.0.0.0')
  parser.add_argument('--http_server.port', dest='port', type=int, default=8000)
  parser.add_argument(
      '--pushgateway.address', dest='pushgateway_address', default=None)
  parser.add_argument(
      '--pushgateway.port', dest='pushgateway_port', default=None)
  parser.add_argument('--logger', dest='logger', default='local')
  parser.add_argument('--iterations', dest='iterations', default=None, type=int)
  parser.add_argument('--delay-minutes', dest='delay', type=int, default=15)
  parser.add_argument(
      '--expose-metrics-with-zero-values',
      dest='zero_value_metrics',
      action='store_true')
  parser.add_argument('--namespace', dest='namespace', default='googleads')
  parser.add_argument('--collectors', dest='collectors', default='default')
  args_bag = parser.parse_known_args()
  args = args_bag[0]

  logger = init_logging(loglevel=args.loglevel.upper(), logger_type=args.logger)

  params = ParamsParser(['macro', 'sql', 'template']).parse(args_bag[1])
  collectors_registry = collectors.Registry()
  macros = params.get('macro', {})
  if config_file := args.config:
    with open(config_file, encoding='utf-8') as f:
      config = yaml.safe_load(f)
      queries = config.get('queries')
  else:
    if not (active_collectors := collectors_registry.find_collectors(
        args.collectors)):
      logger.warning('Failed to get "%s" collectors, using default ones',
                     args.collectors)
      active_collectors = collectors_registry.default_collectors
    if macros:
      active_collectors.customize(macros)
    config = Config(active_collectors.targets)
    queries = config.queries
  for query_name, query in queries.items():
    if relative_metrics := find_relative_metrics(query['query']):
      logger.warning(
          'In query %s, relative metrics: [%s] are found, which might '
          'not be useful.', query_name, ', '.join(relative_metrics))
  runtime_options = {
      'exclude_queries':
          args.exclude_queries.split(',') if args.exclude_queries else None,
      'include_queries':
          args.include_queries.split(',') if args.include_queries else None,
  }

  dependencies = inject_dependencies(
      ads_config_path=args.ads_config,
      api_version=args.api_version,
      account=args.account)
  report_fetcher, accounts = dependencies.get(
      'report_fetcher'), dependencies.get('accounts')
  gaarf_exporter_options = {
      'expose_metrics_with_zero_values': args.zero_value_metrics,
      'namespace': args.namespace
  }

  if args.pushgateway_address and args.pushgateway_port:
    gaarf_exporter = GaarfExporter(
        pushgateway_url=f'{args.pushgateway_address}:{args.pushgateway_port}',
        **gaarf_exporter_options)
  elif (args.address and args.port):
    gaarf_exporter = GaarfExporter(
        http_server_url=f'{args.address}:{args.port}', **gaarf_exporter_options)
  else:
    raise ValueError('Specify option for exposing data to Prometheus '
                     '- either http_server or pushgateway')

  if gaarf_exporter.http_server_url and not gaarf_exporter.pushgateway_url:
    start_http_server(
        port=args.port, addr=args.address, registry=gaarf_exporter.registry)
    logger.info('Started http_server at http://%s',
                gaarf_exporter.http_server_url)
  while True:
    start_export_time = time()
    if macros:
      active_collectors.customize(macros)
    config = Config(active_collectors.targets)
    queries = config.queries
    for name, content in queries.items():
      if not (query_text := content.get('query')):
        raise ValueError(f'Missing query text for query "{name}"')
      if include_queries := runtime_options.get('include_queries'):
        if name not in include_queries:
          continue
      if exclude_queries := runtime_options.get('exclude_queries'):
        if name in exclude_queries:
          continue
      suffix = content.get('suffix') or name
      logger.info('Beginning export')
      if not accounts:
        report = report_fetcher.fetch(query_text, accounts)
      else:
        with futures.ThreadPoolExecutor() as executor:
          future_to_account = {
              executor.submit(report_fetcher.fetch, query_text, account):
                  account for account in accounts
          }
          for future in futures.as_completed(future_to_account):
            account = future_to_account[future]
            start = time()
            report = future.result()
            end = time()
            gaarf_exporter.report_fetcher_gauge.labels(
                collector=name, account=account).set(end - start)
            if dependencies.get('convert_fake_report'):
              report.is_fake = False
            logging.info('Started export for query "[%s]" for account "[%s]"',
                         name, account)
            gaarf_exporter.export(
                report=report, suffix=suffix, collector=name, account=account)
            logging.info('Ended export for query "[%s]" for account "[%s]"',
                         name, account)
    logger.info('Export completed')
    end_export_time = time()
    gaarf_exporter.total_export_time_gauge.set(end_export_time -
                                               start_export_time)
    gaarf_exporter.delay_gauge.set(args.delay * 60)

    if gaarf_exporter.pushgateway_url:
      logger.info('Saving data to pushgateway at %s',
                  gaarf_exporter.pushgateway_url)
      exit()
    sleep(int(args.delay) * 60)
    if iterations := args.iterations:
      iterations -= 1
      if iterations == 0:
        break


if __name__ == '__main__':
  main()
