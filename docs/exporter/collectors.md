# Collectors

Exporting data from Google Ads is done via collectors. Collector represents a query associated with a short alias. Collectors can be bundled into registries to simplify getting common set of metrics.

You can specify collectors with `--collectors <collector_name>` CLI argument. Some collectors available by default, other you need to specify explicitly.

There are two types of collectors - *registry* (contains other collectors grouped logically) and *collectors* themselves.

## Registries

### `default`

* `performance` - extracts *clicks*, *impressions*, *cost*, *conversions* on by *ad_network* and *ad_group_id*
* `conversion_action` - extracts *all_conversions* by *conversion_id* and *account_id*
* `mapping` - performance mapping between *ad_group_id*, *ad_group_name*, *campaign_id*, *campaign_name,* *campaign_status*, *account_id*, *account_name*

### *disapprovals*

* `ad_disapprovals` - extracts *approval_status*, *review_status*, *topic*, *topic_type* by *ad_group_id* and *ad_id* only for not approved ads
* `ad_group_ad_asset_disapprovals` - extracts *approval_status*, *review_status*, *topic*, *topic_type* by *ad_group_id* and *asset_id* only for enabled assets.
* `sitelink_disapprovals` - extracts *approval_status*, *review_status*, *topic*, *topic_type* by *asset_id*,   *sitelink_title* and both sitelink descriptions only for not approved sitelinks.
* `pmax_disapprovals` - extracts *approval_status*, *review_status*, *topic*, *topic_type* by *asset_id*,   *asset_group_id* for active asset group assets.

### *app*

* `app_campaign_mapping` - performs mapping between *campaign_id*, *app_id*, *app_store*, *and bidding_strategy* only for active campaigns.
* `app_asset_mapping` - performs mapping between *asset_id* and its type, source, and content (*name*, *text*, *video_id*) only for app assets (HTML5, TEXT, IMAGE, VIDEO).
* `asset_performance` - extracts *clicks*, *impressions*, *cost*, *installs*, *inapps*, and *conversions_value* by *ad_group_id*, *ad_network* and *asset_id*
* `asset_perf_label` - extracts *performance_label* by *ad_group_id* and *asset_id*

### *pmax*

* `pmax_mapping` - performs mapping between *asset_group_id*, *asset_group_name*, and meta information on campaign and account only for active campaigns and enabled asset groups.
* `pmax_performance` - extracts *clicks*, *impressions*, *cost*, *installs*, *inapps*, and *conversions_value* by *asset_group_id*.
* `pmax_disapprovals` - extracts *approval_status*, *review_status*, *topic*, *topic_type* by *asset_id*,   *asset_group_id* for active asset group assets.

### *search*

* `search_terms` - extracts *clicks*, *impressions*, *cost*, *conversions* on by *search_term* and *ad_group_id*
* `search_terms_conversion_split` - extracts *all_conversions* by *search_term* and *conversion_id* on *ad_group_id* level
* `keywords` - extracts *clicks*, *impressions*, *cost*, *conversions*, and *historical auality_score*  by *keyword* and *match_type* on ad_group level.
* `keywords_conversion_split` - extracts *all_conversions* by *keyword* and *match_type* on ad_group level.

### *placements*

* `placements` - extracts *clicks*, *impressions*, *cost*, *conversions* on by *placement_name* and *placement_type* for each account.
* `placements_conversion_split` - extracts *all_conversions* by *placement_type* and *placement_type* for each account.

### *demographics*

* `age` - extracts *clicks*, *impressions*, *cost*, *conversions* by *age_range* and *campaign_id*
* `age_conversion_split` - extracts *all_conversions* by *age_range* and *conversion_id* on *campaign_id* level
* `gender` - extracts *clicks*, *impressions*, *cost*, *conversions* by *gender* and *campaign_id*
* `gender_conversion_split` - extracts *all_conversions* by *gender* and *conversion_id* on *campaign_id* level

### *geo*

* `user_location` - extracts *clicks*, *impressions*, *cost*, *conversions* by *country_id* and *campaign_id* only for active campaigns.
* `user_location_conversion_split` - extracts *all_conversions* by *country_id*  and *campaign_id*only for active campaigns.

## collectors without registry

* `bid_budgets` - extracts current values of bid (target_cpa, target_roas) and campaign budgets.
* `bids` - extracts current values of bid (target_cpa, target_roas).
* `budgets` - extracts current values of campaign budgets.
* `account_status` - extracts *customer_status* for each account.
* `campaign_service_status` - extracts *primary_status* for each campaign.
