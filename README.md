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
* (Optional) `prometheus.yml` file configured. Learn more at [how to configure Prometheus](docs/how-to-configure-prometheus.md).
* (Optional) [Docker Compose](https://docs.docker.com/compose/install/) installed.


### Installation

There are two ways to install Ads Monitor: using Google Cloud Platform (recommended) or manually using Docker Compose.

#### Google Cloud Platform Installation

This method deploys Ads Monitor on Google Compute Engine with all necessary components configured automatically.

Prerequisites:
* Google Cloud project with billing enabled
* Google Ads API access and [google-ads.yaml](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-authenticate-ads-api.md#setting-up-using-google-adsyaml) file

1. Clone this repository and navigate to its directory

2. Run the deployment script:

```bash
bash deploy.sh deploy_all --account-id YOUR_MCC_ID [OPTIONS]
```

Available options:
* `--account-id`: (Required) Your Google Ads Account ID
* `--project-id`: Google Cloud project ID (defaults to current gcloud config)
* `--zone`: GCP zone for deployment (defaults to us-central1-a)
* `--expose-prometheus`: Flag to expose Prometheus and Alertmanager ports (optional)
* `--google-ads-yaml`: Path to your google-ads.yaml file (defaults to google-ads.yaml in current directory)

The script will:
* Create necessary GCP resources (Compute Instance, disk, firewall rules)
* Deploy and configure all components (Gaarf Exporter, Prometheus, Grafana, Alertmanager)
* Provide you with access URLs once deployment is complete

Note: When accessing Grafana for the first time, use the default credentials (username: admin, password: admin). You will be prompted to change the password upon first login.

To remove the deployment (or parts of it):
```bash
bash cleanup.sh [COMPONENT]
```
Where COMPONENT can be: mig, template, firewall, disk, or all (default)

#### Manual Installation (Docker Compose)

Alternatively, you can run Ads Monitor locally using Docker Compose.

Prerequisites:
* [Docker Compose](https://docs.docker.com/compose/install/) installed
* Google Ads API access and google-ads.yaml file

1. Export required environment variables:

```bash
export GOOGLE_ADS_YAML=/path/to/google-ads.yaml
export GAARF_EXPORTER_ACCOUNT_ID=<YOUR_MCC_ID>
```
> If you don't specify the GOOGLE_ADS_YAML variable, Ads Monitor will look for google-ads.yaml in your $HOME directory.

2. Start the containers:

```bash
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
  -v /path/to/google-ads.yaml:/google-ads.yaml \
  gaarf_exporter
```

`gaarf_exporter` expected these files to be mapped into containers:

* `google-ads.yaml` - file that contains authentication details to connect to Google Ads API.

> Change `--network=host` to the network where your Prometheus instance is running.

`gaarf_exporter` will push expose metrics on `localhost:8000` so they can later be scraped by Prometheus.

##### Skipping or including particular queries

When running `gaarf_exporter` you can specify which data to get from Google Ads.
The exporter some with a lot of built-in [collectors](gaarf_exporter/README.md#collectors)
you can specify by adding with `--collectors <collector_name>` CLI argument.

```
docker run --network=host \
  -v /path/to/google-ads.yaml:/google-ads.yaml \
  gaarf_exporter --collectors app,disapprovals
```

Alternatively you can pass an `--config` argument `gaarf_exporter`
> `--config` always has priority over `--collectors` flag.

```
docker run --network=host \
  -v /path/to/google-ads.yaml:/google-ads.yaml \
  -v /path/to/gaarf_exporter.yaml:/app/gaarf_exporter.yaml \
  gaarf_exporter --config /app/gaarf_exporter.yaml
```

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
