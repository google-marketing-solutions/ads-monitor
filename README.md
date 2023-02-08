# Ads Monitor

## Problem statement

Well defined monitoring in Ads allows users quickly respond to any unexpected
fluctuation in the accounts. But monitoring Ads in smaller time increments (i.e.
every 15 minutes) to identify any problems in performance or approvals can be
time consuming and error-prone.

## Solution

Ads Monitor provides a way to expose a set of custom defined Ads metrics and
dimensions in a Prometheus format which make it possible to reuse widely
available monitoring and alerting tool (i.e. Grafana and Alertmanager) to setup
a solid monitoring environment for your crucial Ads metrics and dimensions.

## Deliverable (implementation)

Ads Monitor provides you with a Grafana dashboard and a set of default alerts.
Data that powers the dashboard and alerts are extracted from Google Ads API and
stored in a Prometheus.

## Deployment

### Prerequisites

* Google Ads API access
* Python 3.8+
* Access to repository configured. In order to clone this repository you need
	to do the following:

	*   Visit https://professional-services.googlesource.com/new-password and
			login with your account. Once authenticated please copy all lines in box
			and paste them in the terminal.

* `prometheus.yml` file configured. Learn more at [how to configure Prometheus](docs/how-to-configure-prometheus.md).


### Installation

An easiest way of trying the solution is to use Docker Compose.

```
docker compose up
```

It will build `gaarf_exporter` container and pull latest images of Prometheus,
Pushgateway, AlertManager and Grafana.


#### Manual installation

You can build and run `gaarf_exporter` container on your own (given that you have
instance of Pushgateway up and running).

1. Build `gaarf_exporter` container:

```
cd src
docker build -t gaarf_exporter .
```

2. Run `gaarf_exporter` container:

```
docker run --network=host \
		-v /path/to/google-ads.yaml:/app/google-ads.yaml \
		-v `pwd`/gaarf_exporter.yaml:/app/gaarf_exporter.yaml \
		-v `pwd`/custom_callbacks.py:/app/custom_callbacks.py \
		gaarf_exporter
```

`gaarf_exporter` expected these files to be mapped into containers:

* `google-ads.yaml` - file that contains authentication details to connect to
	Google Ads API.
* `gaarf_exporter.yaml` - configuration file that specify which metrics should
	be exposed to Prometheus - learn [how to create a gaarf_exporter.yaml](docs/how-to-create-gaarf-exporter-config.md).
* (Optional) `custom_callbacks.py` - file with callbacks that might be associated
	with a particular query.


`gaarf_exporter` will push metrics to Pushgateway so they can later be scraped by Prometheus.

### Usage

Once the metrics are scraped by Prometheus you can open Grafana
(usually located at `http://localhost:3000`) and create a New dashboard
by copying content of `dashboard.json` located in `grafana` folder.

## Disclaimer
This is not an officially supported Google product.
