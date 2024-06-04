# Copyright 2024 Google LLC
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
from __future__ import annotations

import pathlib
import random
import subprocess

import pytest
from gaarf_exporter import registry

_SCRIPT_DIR = pathlib.Path(__file__).parent
_START_PORT = 30000
_END_PORT = 60000
collectors_registry = registry.Registry.from_collector_definitions()


def _generate_collector_port_pairs(
  property_name: str, start_port: int = _START_PORT
) -> list[tuple[str, int]]:
  start_port = random.randint(start_port, _END_PORT)
  collector_names = [
    collector.name for collector in getattr(collectors_registry, property_name)
  ]
  ports = list(range(start_port, start_port + len(collector_names)))
  return list(zip(collector_names, ports))


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize(
  'collector,port', _generate_collector_port_pairs('all_collectors')
)
def test_gaarf_exporter_run_all_collectors_by_one(collector, port):
  result = subprocess.run(
    [
      'gaarf-exporter',
      '--expose-metrics-with-zero-values',
      '--iterations=1',
      f'--collectors={collector}',
      f'--http_server.port={port}',
      '--delay=0',
      '--api-version=16',
    ],
    capture_output=True,
    text=True,
  )
  out = result.stdout
  assert not result.stderr
  assert f'Started http_server at http://0.0.0.0:{port}' in out
  assert 'Beginning export' in out
  assert 'Export completed' in out


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize(
  'collector,port', _generate_collector_port_pairs('all_subregistries', 40000)
)
def test_gaarf_exporter_run_all_subregistries_by_one(collector, port):
  result = subprocess.run(
    [
      'gaarf-exporter',
      '--expose-metrics-with-zero-values',
      '--iterations=1',
      f'--collectors={collector}',
      f'--http_server.port={port}',
      '--delay=0',
      '--api-version=16',
    ],
    capture_output=True,
    text=True,
  )
  out = result.stdout
  assert not result.stderr
  assert f'Started http_server at http://0.0.0.0:{port}' in out
  assert 'Beginning export' in out
  assert 'Export completed' in out


@pytest.mark.e2e
def test_gaarf_exporter_run_all_collectors_at_once():
  result = subprocess.run(
    [
      'gaarf-exporter',
      '--expose-metrics-with-zero-values',
      '--iterations=1',
      '--collectors=all',
      '--delay=0',
      '--api-version=16',
    ],
    capture_output=True,
    text=True,
  )
  out = result.stdout
  assert not result.stderr
  assert 'Started http_server at http://0.0.0.0:8000' in out
  assert 'Beginning export' in out
  assert 'Export completed' in out


@pytest.mark.e2e
def test_gaarf_exporter_run_selected_collectors_from_config_file():
  result = subprocess.run(
    [
      'gaarf-exporter',
      '--expose-metrics-with-zero-values',
      '--iterations=1',
      f'-c={_SCRIPT_DIR}/test_gaarf_exporter.yaml',
      '--delay=0',
      '--api-version=16',
    ],
    capture_output=True,
    text=True,
  )
  out = result.stdout
  assert not result.stderr
  assert 'Started http_server at http://0.0.0.0:8000' in out
  assert 'Beginning export' in out
  assert 'Export completed' in out
