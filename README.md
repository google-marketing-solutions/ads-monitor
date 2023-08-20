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

Ads Monitor provides you with a Grafana dashboard and a set of default [alerts](prometheus/alerts.yml).
Data that powers the dashboard and alerts are extracted from Google Ads API and
stored in a Prometheus.

## Deployment

### Prerequisites

* Google Ads API access and [google-ads.yaml](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-authenticate-ads-api.md#setting-up-using-google-adsyaml) file - follow documentation on [API authentication](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-authenticate-ads-api.md).
* Access to repository configured. In order to clone this repository you need
to do the following:

  *   Visit https://professional-services.googlesource.com/new-password and login with your account.
  *   Once authenticated please copy all lines in box and paste them in the terminal.
* (Optional) `prometheus.yml` file configured. Learn more at [how to configure Prometheus](docs/how-to-configure-prometheus.md).
* (Optional) [Docker Compose](https://docs.docker.com/compose/install/) installed.

### Deploy to VM
[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

### Installation

An easiest way to try the solution is to run it via [Docker Compose](https://docs.docker.com/compose/install/).

1. expose environmental variables `GOOGLE_ADS_YAML` and `GAARF_EXPORTER_ACCOUNT_ID`:

```
export GOOGLE_ADS_YAML=/path/to/google-ads.yaml
export GAARF_EXPORTER_ACCOUNT_ID=<YOUR_MCC_ID>
```
> If you don't specify the environmental variable Ads Monitor will be expecting `google.yaml` file in your $HOME directory.

3. start the containers:

```
docker compose up
```

This command will build `gaarf_exporter` image and start scraping Google Ads every 15 minutes,
pull latest images of Prometheus, AlertManager and Grafana.


#### Manual installation

You can build and run `gaarf_exporter` container on your own.

1. Build `gaarf_exporter` container:

```
cd gaarf_exporter
docker build -t gaarf_exporter .
```

2. Run `gaarf_exporter` container:

```
docker run --network=host \
  -v /path/to/google-ads.yaml:/root/google-ads.yaml \
  gaarf_exporter
```

`gaarf_exporter` expected these files to be mapped into containers:

* `google-ads.yaml` - file that contains authentication details to connect to Google Ads API.

> Change `--network=host` to the network that where your Pushgateway instance is running.

`gaarf_exporter` will push expose metrics on `localhost:8000` so they can later be scraped by Prometheus.

##### Skipping or including particular queries

When running `gaarf_exporter` there are two CLI flags that can help fine-tuning
which queries from config file should be run:

* `--queries.include` - comma-separated query names (i.e. `performance,search_terms`) that will be taken from `gaarf_exporter.yaml` for fetching.
* `--queries.exclude` - comma-separated query names (i.e. `performance,search_terms`) that will be will be excluded from fetching despite being in the `gaarf_exporter.yaml` config.

### Usage

#### Creating Grafana dashboard

Once the metrics are scraped by Prometheus you can open Grafana
(usually located at `http://localhost:3000`):

1. Create [Prometheus datasource](https://prometheus.io/docs/visualization/grafana/#creating-a-prometheus-data-source)
2. [Import dashboard](https://grafana.com/docs/grafana/latest/dashboards/manage-dashboards/#import-a-dashboard) by copying content of `dashboard.json` located in `grafana` folder.
3. Associate Prometheus datasource with in an imported dashboard with the created Prometheus datasource on step 1.


#### Configuring Alertmanager

[Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) is responsible for sending alerts to various receivers (email, Slack, Telegram, etc).
To configure Alertmanager to send updates to Slack open `alertmanager/alertmanager.yml` and under `receivers` section add the following block:

```
- name: slack
  api_url: https://hooks.slack.com/services/XXXXXXXX/XXXXX/XXXXXXXX
  slack_configs:
    - channel: "#your-slack-channel"
```

Please refer to Alertmanager [documentation](https://prometheus.io/docs/alerting/latest/configuration/)
for additional configuration opportunities.

## Disclaimer
This is not an officially supported Google product.
