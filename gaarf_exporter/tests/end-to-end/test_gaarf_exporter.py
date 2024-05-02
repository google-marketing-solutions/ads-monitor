from __future__ import annotations

import subprocess


def test_gaarf_exporter():
  result = subprocess.run([
      'gaarf-exporter', '--expose-metrics-with-zero-values', '--iterations=1',
      '--delay=0',
      '--api-version=16',
  ],
                          capture_output=True,
                          text=True)
  out = result.stdout
  assert not result.stderr
  assert 'Started http_server at http://0.0.0.0:8000' in out
  assert 'Beginning export' in out
  assert 'Export completed' in out
