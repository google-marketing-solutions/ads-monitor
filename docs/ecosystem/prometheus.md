# Prometheus

`gaarf_exporter` exports data in the format that can be easily scraped by Prometheus.

## Configuring

Create `prometheus.yml` file.

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
    scrape_interval: 30s
    static_configs:
      - targets: ['localhost:8000']
```

### Adding new target to existing prometheus.yml

Since `gaarf_exporter` exposed metrics as HTTP server you need to add the following
target in your `prometheus.yml`.

```
- job_name: 'gaarf'
  honor_labels: true
  scrape_interval: 30s
  static_configs:
    - targets: ['gaarf_exporter:8000']
```

## Defining rules

Please refer to [alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) documentation  on prometheus.io for more details.
