# Copyright 2023 Google LLC
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

"""Entrypoint for running GaarfExporter.

Defines GaarfExporter collectors, fetches data from Google Ads API
and expose them to Prometheus.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import datetime
import logging

import fastapi
import prometheus_client
import requests
import uvicorn
from gaarf.cli import utils as gaarf_utils

import gaarf_exporter
from gaarf_exporter import exporter_service


class GaarfExporterError(Exception):
  """Base class for GaarfExporter errors."""


def healthcheck(host: str, port: int) -> bool:
  """Validates that the GaarfExporter export happened recently.

  Healthcheck compares the time passed since the last successful export with
  the delay between exports. If this delta if greater than 1.5 check is failed.

  Args:
    host: Hostname gaarf-exporter http server (i.e. localhost).
    port: Port gaarf-exporter http server is running (i.e. 8000).


  Returns:
    Whether or not the check is successful.
  """
  try:
    res = requests.get(f'http://{host}:{port}/metrics/').text.split('\n')
  except requests.exceptions.ConnectionError:
    return False
  last_exported = [r for r in res if 'export_completed_seconds 1' in r][
    0
  ].split(' ')[1]
  delay = None
  for result in [r for r in res if 'delay_seconds' in r]:
    _, *value = result.split(' ', maxsplit=2)
    with contextlib.suppress(ValueError):
      delay = float(value[0])
  if not delay:
    return False

  max_allowed_delta = 1.5
  is_lagged_export = (
    datetime.datetime.now().timestamp() - float(last_exported)
  ) > (max_allowed_delta * delay)

  return not is_lagged_export


app = fastapi.FastAPI(debug=False)
exporter = gaarf_exporter.GaarfExporter()
metrics_app = prometheus_client.make_asgi_app(registry=exporter.registry)
app.mount('/metrics', metrics_app)

logger = gaarf_utils.init_logging(
  loglevel='INFO',
  logger_type='rich',
  name='gaarf-exporter',
)


async def start_metric_generation(
  request: exporter_service.GaarfExporterRequest,
):
  """Continuously exports metrics from Google Ads API."""
  gaarf_exporter_service = exporter_service.GaarfExporterService(
    ads_config_path=request.ads_config_path, account=request.account
  )
  logging.info(
    'Starting exporting metrics from accounts: %s',
    gaarf_exporter_service.accounts,
  )
  iterations = None
  export_metrics = True
  refresh_accounts = False
  while export_metrics:
    if iterations_left := request.runtime_options.account_update:
      iterations_left -= 1
    if iterations_left == 0:
      refresh_accounts = True
    gaarf_exporter_service.generate_metrics(request, exporter, refresh_accounts)
    if request.runtime_options.expose_type == 'pushgateway':
      prometheus_client.push_to_gateway(
        request.runtime_parameters.address,
        job=request.runtime_parameters.job_name,
        registry=exporter.registry,
      )
      export_metrics = False
    await asyncio.sleep(request.runtime_options.delay_minutes * 60)
    if iterations := iterations or request.runtime_options.iterations:
      iterations -= 1
      if iterations == 0:
        export_metrics = False


async def startup_event(
  request: exporter_service.GaarfExporterRequest,
):
  """Start async task for metrics export."""
  asyncio.create_task(start_metric_generation(request))


@app.get('/health')
def health(request: fastapi.Request):
  """Defines healthcheck endpoint for GaarfExporter."""
  host = request.url.hostname
  port = request.url.port
  if not healthcheck(host, port):
    raise fastapi.HTTPException(status_code=404, detail='Not updated properly')


def main() -> None:  # noqa: D103
  parser = argparse.ArgumentParser()
  parser.add_argument('--account', dest='account', default=None)
  parser.add_argument('-c', '--config', dest='config', default=None)
  parser.add_argument('--ads-config', dest='ads_config', default=None)
  parser.add_argument('--log', '--loglevel', dest='loglevel', default='info')
  parser.add_argument(
    '--expose-type',
    dest='expose_type',
    choices=['http', 'pushgateway'],
    default='http',
  )
  parser.add_argument('--host', dest='host', default='0.0.0.0')
  parser.add_argument('--port', dest='port', type=int, default=8000)
  parser.add_argument('--logger', dest='logger', default='local')
  parser.add_argument('--iterations', dest='iterations', default=None, type=int)
  parser.add_argument(
    '--update-accounts-every-n-iterations',
    dest='account_update',
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
  parser.add_argument(
    '--fetching-timeout-seconds', dest='fetching_timeout', default=120, type=int
  )
  parser.add_argument('--collectors', dest='collectors', default='default')
  parser.add_argument(
    '--no-deduplicate-collectors', dest='deduplicate', action='store_false'
  )
  parser.add_argument(
    '--no-service-collectors', dest='service_collectors', action='store_false'
  )
  parser.add_argument('-v', '--version', dest='version', action='store_true')
  parser.set_defaults(deduplicate=True)
  parser.set_defaults(service_collectors=True)
  args, kwargs = parser.parse_known_args()
  macros = gaarf_utils.ParamsParser(['macro']).parse(kwargs).get('macro')
  runtime_options = exporter_service.GaarfExporterRuntimeOptions(
    expose_type=args.expose_type,
    host=args.host,
    port=args.port,
    namespace=args.namespace,
    fetching_timeout=args.fetching_timeout,
    iterations=args.iterations,
    delay_minutes=args.delay,
    update_accounts_on_iterations=args.account_update,
  )
  if not args.account and args.ads_config:
    request = exporter_service.GaarfExporterRequest(
      collectors=args.collectors,
      collectors_config=args.config,
      macros=macros,
      runtime_options=runtime_options,
    )
  else:
    request = exporter_service.GaarfExporterRequest(
      account=args.account,
      collectors=args.collectors,
      ads_config_path=args.ads_config,
      collectors_config=args.config,
      macros=macros,
      runtime_options=runtime_options,
    )
  exporter.namespace = request.runtime_options.namespace

  async def start_uvicorn():
    await startup_event(request)
    config = uvicorn.Config(
      app,
      host=request.runtime_options.host,
      port=request.runtime_options.port,
      reload=True,
    )
    server = uvicorn.Server(config)
    await server.serve()

  asyncio.run(start_uvicorn())


if __name__ == '__main__':
  main()
