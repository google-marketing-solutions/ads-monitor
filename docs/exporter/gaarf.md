gaarf exporter - Prometheus exporter for Google Ads.

[![PyPI](https://img.shields.io/pypi/v/gaarf-exporter?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/gaarf-exporter)
[![Downloads PyPI](https://img.shields.io/pypi/dw/gaarf-exporter?logo=pypi)](https://pypi.org/project/gaarf-exporter/)

## Installation

/// tab | pip
```bash
pip install gaarf-exporter
```
///

## Usage

You can use `gaarf-exporter` both locally and in Docker container.

By default it will start http_server on `localhost:8000` and will push some basic metrics to it.

/// tab | locally
```bash
gaarf-exporter
```
///

/// tab | docker

```bash
docker run --network=host \
  -v /path/to/google-ads.yaml:/google-ads.yaml \
  -v `pwd`/gaarf_exporter.yaml:/app/gaarf_exporter.yaml \
  gaarf_exporter
```
///


## Customization

* `--ads-config` - path to `google-ads.yaml`
  >  `ads-config` can be taken from local storage or remote storage (gs, s3, azure, ssh, stfp, scrp, hdfs, webhdfs).
* `--config` - path to `gaarf_exporter.yaml`
  >  `config` can be taken from local storage or remote storage (same as `--ads-config`).
* `--collectors` - names of one or more [collectors](collectors.md) (separated by comma).
* `--expose-type` - type of exposition (`http` or `pushgateway`, `http` is used by default)
* `--host` - address of your http server (`localhost` by default)
* `--port` - port of your http server (`8000` by default)
* `--delay-minutes` - delay in minutes between scrapings (`15` by default)

### Macros

### Customizing fetching dates

By default `gaarf-exporter` fetches performance data for TODAY; if you want to
customize it you can provide optional flags:
* `--macro.start_date=:YYYYMMDD-N`, where `N` is number of days starting from today
* `--macro.end_date=:YYYYMMDD-M`, where `N` is number of days starting from today

It will add an additional metric to be exposed to Prometheus `*_n_days` (i.e.
`googleads_clicks_n_days`).
