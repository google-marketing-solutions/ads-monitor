# Grafana

Ads Monitor uses [Grafana](https://prometheus.io/docs/visualization/grafana/) to visualize the metrics and / or alerts via dashboard.

## Pre-built dashboards

You can explore [existing Grafana dashboards](https://github.com/google-marketing-solutions/ads-monitor/tree/main/grafana) that are compatible with Ads Monitor

* [`default`](https://github.com/google-marketing-solutions/ads-monitor/blob/main/grafana/dashboard.json) - monitors base metrics such as clicks, impressions, cost, conversions.
* [`budgets`](https://github.com/google-marketing-solutions/ads-monitor/blob/main/grafana/dashboards/budgets.json) - monitors budget utilization.
* [`approvals`](https://github.com/google-marketing-solutions/ads-monitor/blob/main/grafana/dashboards/disapprovals.json) - monitors policy approval statuses.
* [`new entities`](https://github.com/google-marketing-solutions/ads-monitor/blob/main/grafana/dashboards/new_entities.json) - monitors new campaigns / ad groups in the accounts.
* [`internal_metrics`](https://github.com/google-marketing-solutions/ads-monitor/blob/main/grafana/internal_metrics_dashboard.json) - monitors health of Ads Monitor and API quota usage.
