# How to create gaarf_exporter.yaml

`gaarf_exporter.yaml` is used to configure `gaarf_exporter` to execute a particular GAQL-query (based on [gaarf syntax](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md)).

It consists of two sections:

* `global` - used to configure `gaarf_exporter`
* `queries` - contains one or more queries with dimensions and metrics to be exposed to Prometheus

```
global:
  auth: ./google-ads.yaml
  mcc_id: "<YOUR_MCC_ID>"
  custom_callbacks_location: ./custom_callbacks.py
  pushgateway_url: "localhost:9091"
  namespace: googleads

queries:
  query_name:
    query: |
      SELECT
        ...
      FROM ...
      WHERE
          segments.date DURING TODAY
          AND campaign.status = "ENABLED"
          AND ad_group.status = "ENABLED"
          AND metrics.cost_micros > 0
    custom_callback: name_of_a_callback
    job_name: custom_job_name
    suffix: custom_suffix
```

## Global section

Elements:

* `auth` - path to `google-ads.yaml` file
> When running inside Docker container leave default value `./google-ads.yaml`.
* `mcc_id` - MCC account
* `custom_callback_location` - path to file which contains functions which post-process results of GAQL-query before exposing it to Prometheus.
* `pushgateway_url` - address and port of Pushgateway instance
* `namespace` - namespace for metrics (by default `googleads`, so metrics might look like this: `googleads_impressions`)

## Queries section

Consists of one or more queries.

* `<query_name>` (i.e. `impressions`)
* `query` - text of a query (based on [gaarf syntax](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md)).
* `job_name` - custom job name to be exposed to Pushgateway (by default the same as `<query_name>`
* `suffix` - custom suffix for the metrics for the query.
  * By default `suffix` is the same and query name; so if you have a query `placements`
  the metric in Prometheus will look like `googleads_placements_impressions`.
  * If you specify `suffix` (i.e. `plc`) the metrics will look like `googleads_plc_impressions`.
  * You can remove suffix for some generic metrics by specifying `suffix: Remove`
* `custom_callback` - name of the function in `custom_callback_location`
  that will be applied to the results of query execution before exposing them to Prometheus.

### Query: how to define metrics and labels

By default every element field in the query that starts with `metrics` will be
treated as metric that needs to be exposed to Prometheus.
Every [virtual column](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md#virtual-columns) will be treated as metric as well.
The rest will be a label for the metrics defined in the query.
> `gaarf_exporter` currently works with Gauges.

Useful virtual columns:

`1 AS column_name` - metric `namespace_suffix_column_name` will be exposed to Prometheus.
If no `custom_callback` is applied to the `column_name` its value will always will be `1`.


You can check example queries in [gaarf-config.yaml](../src/gaarf_config.yaml).
