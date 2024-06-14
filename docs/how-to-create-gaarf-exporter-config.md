# How to create gaarf_exporter.yaml

> It's recommended to use [collectors](../gaarf_exporter/README.md#collectors) whenever possible for getting data from Google Ads.

`gaarf_exporter.yaml` can be used to configure `gaarf_exporter` to execute a particular GAQL-query (based on [gaarf syntax](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md)).

It contains one or more queries with dimensions and metrics to be exposed to Prometheus.

```
- name: query_name
  query: |
    SELECT
        customer.id AS customer_id,
        campaign.id AS campaign_id,
        ad_group.id AS ad_group_id,
        segments.ad_network_type AS network,
        metrics.clicks AS clicks,
        metrics.impressions AS impressions,
        metrics.conversions AS conversions,
        metrics.conversions_value AS conversions_value,
        metrics.cost_micros / 1e6 AS cost
    FROM ad_group
    WHERE
        segments.date DURING TODAY
        AND campaign.status = ENABLED
        AND ad_group.status = ENABLED
        AND metrics.impressions > 0
  suffix: custom-suffix
```

`queries` must contains at least one key that identifies data being fetched
from Google Ads and consist of the following elements.

* `<query_name>` (i.e. `performance`)
* `query` - text of a query (based on [gaarf syntax](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md)).
* `suffix` - custom suffix for the metrics for the query.
  * By default `suffix` is the same and query name; so if you have a query `placements`
  the metric in Prometheus will look like `googleads_placements_impressions`.
  * If you specify `suffix` (i.e. `plc`) the metrics will look like `googleads_plc_impressions`.
  * You can remove suffix for some generic metrics by specifying `suffix: Remove`, in that case metric will look like `googleads_impressions`.

### Query: how to define metrics and labels

By default every element field in the query that starts with `metrics` will be
treated as metric that needs to be exposed to Prometheus.
Every [virtual column](https://github.com/google/ads-api-report-fetcher/blob/main/docs/how-to-write-queries.md#virtual-columns) will be treated as metric as well.
The rest will be a label for the metrics defined in the query.
> `gaarf_exporter` currently works with Gauges.

You can check example queries in [gaarf-config.yaml](../gaarf_exporter/gaarf_exporter.yaml).
