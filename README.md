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


### Installation

An easiest way to try the solution is to run it via [Docker Compose](https://docs.docker.com/compose/install/).

1. expose environmental variable `GOOGLE_ADS_YAML`:

```
export GOOGLE_ADS_YAML=/path/to/google-ads.yaml
```
> If you don't specify the environmental variable Ads Monitor will be expecting `google.yaml` file in your $HOME directory.

2. update `src/gaarf_exporter.yaml`:

* in `globals` section add your MCC account under `mcc_id` key.


3. start the containers:

```
docker compose up
```

This command will build `gaarf_exporter` image, pull latest images of Prometheus,
Pushgateway, AlertManager and Grafana and perform the initial scrape of metrics
from Google Ads.

> To perform regular export of Google Ads metrics set up a cronjob, i.e.
> use the command below to run the scraping every 10 minutes:
> ```
> */10 * * * * bash /path/to/ads_monitor_folder/scripts/run-gaarf-exporter.sh
> ```


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

* `google-ads.yaml` - file that contains authentication details to connect to Google Ads API.
* `gaarf_exporter.yaml` - configuration file that specify which metrics should be exposed to Prometheus - learn [how to create a gaarf_exporter.yaml](docs/how-to-create-gaarf-exporter-config.md).
* (Optional) `custom_callbacks.py` - file with callbacks that might be associated	with a particular query.

> Change `--network=host` to the network that where your Pushgateway instance is running.

`gaarf_exporter` will push metrics to Pushgateway so they can later be scraped by Prometheus.

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
