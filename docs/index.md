# Ads Monitor

Ads Monitor provides a way to expose a set of custom defined Ads metrics and
dimensions in a Prometheus format which make it possible to reuse widely
available monitoring and alerting tool (i.e. Grafana and Alertmanager) to setup
a solid monitoring environment for your crucial Ads metrics and dimensions.

## Key features

* Collects data from your Google Ads frequently (i.e. every 15 minutes)
* Finds problems with metrics and dimensions
* Sends alerts
* Visualizes data in the pre-built or custom monitoring dashboards

## Installation

There are two ways to install Ads Monitor: using Google Cloud Platform (recommended) or manually using Docker Compose.

### Google Cloud

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

### Docker Compose

Alternatively, you can run Ads Monitor locally using Docker Compose.

Prerequisites:

* [Docker Compose](https://docs.docker.com/compose/install/) installed
* Google Ads API access and google-ads.yaml file


*Run*:

* Export required environment variables:

```bash
export GOOGLE_ADS_YAML=/path/to/google-ads.yaml
export GAARF_EXPORTER_ACCOUNT_ID=<YOUR_MCC_ID>
```
> If you don't specify the GOOGLE_ADS_YAML variable, Ads Monitor will look for google-ads.yaml in your $HOME directory.

* Start the containers:

```bash
docker compose up
```

This command will pull `gaarf_exporter` image and start scraping Google Ads every 15 minutes,
pull latest images of Prometheus, AlertManager and Grafana.

## Usage

Once Ads Monitor up and running you may proceed with the following steps:

* [Creating rules and alerts](ecosystem/prometheus.md)
* [Sending notifications](ecosystem/alertmanager.md)
* [Creating dashboards](ecosystem/grafana.md)
