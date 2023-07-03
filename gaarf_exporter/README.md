# gaarf exporter

Prometheus exporter for Google Ads metrics with customizable metrics collectors.

## Installation and usage

### Locally

1. Install `gaarf-exporter` from pip:

```
pip install gaarf-exporter
```
2. Run `gaarf-exporter`:

```
gaarf-exporter
```

### Docker

```
docker run --network=host \
  -v /path/to/google-ads.yaml:/root/google-ads.yaml \
  -v `pwd`/gaarf_exporter.yaml:/app/gaarf_exporter.yaml \
  gaarf_exporter
```

```
docker run --network=host gaarf_exporter \
  --config gs://path/to/gaarf_config.yaml \
  --ads-config gs://path/to/google-ads.yaml

```

--network=host
By default it will start http_server on `localhost:8000` and will push some basic metrics to it.

### Customization

* `--ads-config` - path to `google-ads.yaml`
* `--config` - path to `gaarf_exporter.yaml`
* `--http_server.address` - address of your http server (`localhost` by default)
* `--http_server.port` - port of your http server (`8000` by default)
* `--pushgateway.address` - address of your pushgateway service (`None` by default)
* `--pushgateway.port` - port of your pushgateway (`None` by default)
* `--delay-minutes` - delay in minutes between scrapings (`15` by default)

### Collectors

You can specify collectors with `--collectors.<collector_name>` CLI argument. Some collectors available by default, other you need to specify explicitly.

### Default collectors

* `performance` - extract `clicks`, `impressions`, `cost`, `conversions` on by `ad_network` and `ad_group_id`
* `disapprovals` - extract `approval_status`, `review_status`, `policy_topic_type`, `policy_topics` by `ad_group_id` and `ad_id`
* `conversion_action` - extract `all_conversions` by `conversion_id` and `account_id`
* `mapping` - performance mapping between `ad_group_id`, `ad_group_name`, `campaign_id`, `campaign_name,` `campaign_status`, `account_id`, `account_name`

### Available collectors

* `search_terms` - extract `clicks`, `impressions`, `cost`, `conversions` on by `search_term` and `ad_group_id`
* `search_terms_conversion_split` - extract `all_conversions` by `search_term` and `conversion_id` on `ad_group_id` level
* `placements` - extract `clicks`, `impressions`, `cost`, `conversions` on by `placement_name` and `placement_type`
* `bid_budgets` - extract current values of bid (target_cpa, target_roas) and budget
