# How to configure Prometheus

Create `prometheus.yml` file and add it in the same folder as `docker-compose.yml`

```
global:
  scrape_interval: 30s
  evaluation_interval: 30s
alerting:
  alertmanagers:
    - static_configs:
      - targets:
        - localhost:9093
scrape_configs:
  - job_name: 'gaarf'
    honor_labels: true
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:9091']
```

Please refer to [prometheus.yml](../prometheus/prometheus.yml) example.

## Adding new target to existing prometheus.yml

Since `gaarf_exporter` push metrics to Pushgateway you need to add the following
target in your `prometheus.yml`.

```
- job_name: 'gaarf'
  honor_labels: true
  scrape_interval: 30s
  static_configs:
    - targets: ['pushgateway_url:9091']
```
