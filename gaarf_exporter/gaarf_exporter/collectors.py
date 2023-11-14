# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import (Callable, Dict, List, Protocol, Type, TypeVar,
                    runtime_checkable)

from datetime import datetime
from gaarf.cli.utils import convert_date
from .target import Target, TargetLevel
from .query_elements import Field, Customizer, CustomizerTypeEnum


class BaseCollector(Protocol):
    name: str
    target: Target


T = TypeVar('T', bound='BaseCollector')


def collector(*registries: str) -> Callable:

    def class_collector(cls: Type[T]) -> Type[T]:
        for name in registries:
            if name not in registry:
                registry[name] = {}
            registry[name][cls.name] = cls
        return cls

    return class_collector


def create_conversion_split_collector(
        seed_collector: BaseCollector) -> type[BaseCollector]:
    name = seed_collector.__name__.replace("Collector", "")
    name = f"{name}ConversionSplitCollector"
    cls = type(name, (seed_collector, ),
               {"name": seed_collector.name + "_conversion_split"})
    cls.target = Target(name=cls.name,
                        metrics=DEFAULT_CONVERSION_SPLIT_METRICS,
                        level=seed_collector.target.level,
                        dimensions=DEFAULT_CONVERSION_SPLIT_DIMENSIONS,
                        filters=("segments.date DURING TODAY "
                                 "AND metrics.all_conversions > 0"))
    return cls


def register_conversion_split_collector(cls: Type[T]) -> Type[T]:
    conv_split_cls = create_conversion_split_collector(cls)
    registry[conv_split_cls.name] = {
        conv_split_cls.name: conv_split_cls,
        cls.name: cls
    }
    return cls


registry: Dict[str, Dict[str, Type[BaseCollector]]] = dict()

DEFAULT_METRICS = [
    Field("clicks"),
    Field("impressions"),
    Field("conversions"),
    Field("cost_micros / 1e6", "cost")
]

DEFAULT_CONVERSION_SPLIT_METRICS = [
    Field("all_conversions"),
    Field("all_conversions_value"),
]

DEFAULT_CONVERSION_SPLIT_DIMENSIONS = [
    Field("segments.conversion_action_category", "conversion_category"),
    Field("segments.conversion_action_name", "conversion_name"),
    Field("segments.conversion_action", "conversion_id",
          Customizer(CustomizerTypeEnum.INDEX, '0'))
]


class CollectorCustomizerMixin:

    def customize_target(target, **kwargs) -> None:
        CollectorCustomizerMixin._format_date_range(target, **kwargs)

    def _format_date_range(target, **kwargs) -> None:
        if kwargs and (start_date :=
                       kwargs.get("start_date")) and (end_date :=
                                                      kwargs.get("end_date")):
            start_date = convert_date(start_date)
            end_date = convert_date(end_date)
            target.filters = target.filters.replace(
                "DURING TODAY", f"BETWEEN '{start_date}' AND '{end_date}'")
            n_days = (datetime.strptime(end_date, "%Y-%m-%d") -
                      datetime.strptime(start_date, "%Y-%m-%d")).days + 1
            if target.dimensions:
                target.dimensions += [Field(str(n_days), "n_days")]
            else:
                target.dimensions = [Field(str(n_days), "n_days")]


# TODO (amarkin): Make collector dynamically customizable
@collector("default", "generic")
@register_conversion_split_collector
class PerformanceCollector(CollectorCustomizerMixin):
    name = "performance"
    target = Target(name=name,
                    metrics=DEFAULT_METRICS,
                    level=TargetLevel.AD_GROUP,
                    dimensions=[Field("segments.ad_network_type", "network")],
                    filters="segments.date DURING TODAY",
                    suffix="Remove")

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("default", "generic")
class DisapprovalCollector:
    name = "disapprovals"
    target = Target(
        name=name,
        level=TargetLevel.AD_GROUP_AD,
        dimensions=[
            Field("ad_group.id", "ad_group_id"),
            Field("ad_group_ad.policy_summary.approval_status",
                  "approval_status"),
            Field("ad_group_ad.policy_summary.review_status", "review_status"),
            Field("ad_group_ad.policy_summary.policy_topic_entries:type",
                  "topic_type"),
            Field("ad_group_ad.policy_summary.policy_topic_entries:topic",
                  "topic"),
            Field("1", "ad_count")
        ],
        filters=(
            "campaign.status = 'ENABLED'"
            " AND ad_group.status = 'ENABLED'"
            " AND ad_group_ad.status = 'ENABLED'"
            " AND ad_group_ad.policy_summary.approval_status != 'APPROVED'"))


@collector("disapprovals")
class AdGroupAdAssetDisapprovalCollector:
    name = "ad_group_ad_asset_disapprovals"
    target = Target(
        name=name,
        level=TargetLevel.AD_GROUP,
        dimensions=[
            Field("asset.id", "asset_id"),
            Field("ad_group_ad_asset_view.field_type", "field_type"),
            Field("ad_group_ad_asset_view.policy_summary:approval_status",
                  "approval_status"),
            Field("ad_group_ad_asset_view.policy_summary:review_status",
                  "review_status"),
            Field(
                "ad_group_ad_asset_view.policy_summary:policy_topic_entries.type",
                "topic_type"),
            Field(
                "ad_group_ad_asset_view.policy_summary:policy_topic_entries.topic",
                "topic"),
            Field("1", "ad_count")
        ],
        resource_name="ad_group_ad_asset_view",
        filters=("campaign.status = 'ENABLED'"
                 " AND ad_group.status = 'ENABLED'"
                 " AND ad_group_ad_asset_view.enabled = True"))


@collector("disapprovals")
class SitelinkDisapprovalCollector:
    name = "sitelink_disapprovals"
    target = Target(
        name=name,
        level=TargetLevel.UNKNOWN,
        dimensions=[
            Field("asset.id", "asset_id"),
            Field("asset.sitelink_asset.link_text", "sitelink_title"),
            Field("asset.sitelink_asset.description1", "sitelink_description1"),
            Field("asset.sitelink_asset.description2", "sitelink_description2"),
            Field("asset.policy_summary.approval_status", "approval_status"),
            Field("asset.policy_summary.review_status", "review_status"),
            Field("asset.policy_summary.policy_topic_entries:type",
                  "topic_type"),
            Field("asset.policy_summary.policy_topic_entries:topic", "topic"),
            Field("1", "ad_count")
        ],
        resource_name="asset",
        filters=
        ("asset.type = 'SITELINK' AND asset.policy_summary.approval_status != 'APPROVED'"
         ))


@collector("default", "generic")
class ConversionActionCollector:
    name = "conversion_action"
    target = Target(name=name,
                    metrics=[Field("all_conversions")],
                    level=TargetLevel.CUSTOMER,
                    dimensions=[
                        Field("customer.id", "account_id"),
                        Field("segments.conversion_action_name",
                              "conversion_name"),
                        Field("segments.conversion_action", "conversion_id",
                              Customizer(CustomizerTypeEnum.INDEX, '0'))
                    ],
                    filters=("segments.date DURING TODAY"
                             " AND metrics.all_conversions > 0"))


@collector("app")
class AppCampaignMappingCollector:
    name = "app_campaign_mapping"
    target = Target(name=name,
                    metrics=[Field("1", "info")],
                    level=TargetLevel.CAMPAIGN,
                    dimensions=[
                        Field("app_campaign_setting.app_id", "app_id"),
                        Field("app_campaign_setting.app_store", "app_store"),
                        Field(
                            "app_campaign_setting.bidding_strategy_goal_type",
                            "bidding_strategy")
                    ],
                    filters="campaign.status = 'ENABLED'")


@collector("default", "generic")
class MappingCollector:
    name = "mapping"
    target = Target(name=name,
                    metrics=[Field("1", "info")],
                    level=TargetLevel.AD_GROUP_AD,
                    dimensions=[
                        Field("customer.descriptive_name", "account_name"),
                        Field("customer.id", "account_id"),
                        Field("campaign.name", "campaign_name"),
                        Field("campaign.id", "campaign_id"),
                        Field("campaign.bidding_strategy_type",
                              "bidding_strategy_type"),
                        Field("campaign.advertising_channel_type",
                              "campaign_type"),
                        Field("campaign.advertising_channel_sub_type",
                              "campaign_sub_type"),
                        Field("campaign.start_date", "start_date"),
                        Field("ad_group.id", "ad_group_id"),
                        Field("ad_group.name", "ad_group_name")
                    ],
                    filters=("campaign.status = 'ENABLED'"
                             " AND ad_group.status = 'ENABLED'"
                             " AND ad_group_ad.status = 'ENABLED'"))


# TODO (amarkin): Support registering without argument
@collector("all", "search")
@register_conversion_split_collector
class SearchTermsCollector(CollectorCustomizerMixin):
    name = "search_terms"
    target = Target(
        name=name,
        metrics=DEFAULT_METRICS,
        level=TargetLevel.AD_GROUP,
        resource_name="search_term_view",
        dimensions=[Field("search_term_view.search_term", "search_term")],
        filters=("segments.date DURING TODAY "
                 "AND campaign.status = 'ENABLED' "
                 "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all")
@register_conversion_split_collector
class PlacementsCollector(CollectorCustomizerMixin):
    name = "placements"
    target = Target(name=name,
                    metrics=DEFAULT_METRICS,
                    level=TargetLevel.CUSTOMER,
                    resource_name="group_placement_view",
                    dimensions=[
                        Field("group_placement_view.display_name", "name"),
                        Field("group_placement_view.placement_type", "type")
                    ],
                    filters=("segments.date DURING TODAY "
                             "AND campaign.status = 'ENABLED' "
                             "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all")
class BidBudgetCollector:
    name = "bid_budgets"
    target = Target(
        name=name,
        level=TargetLevel.CAMPAIGN,
        metrics=[
            Field("campaign_budget.amount_micros/1e6", "budget"),
            Field("campaign.target_cpa.target_cpa_micros/1e6", "target_cpa"),
            Field("campaign.maximize_conversions.target_cpa_micros/1e6",
                  "max_conv_target_cpa"),
            Field("campaign.target_roas.target_roas", "target_roas"),
        ],
        filters="campaign.status = 'ENABLED'")


@collector("all")
@register_conversion_split_collector
class AssetPerformanceCollector(CollectorCustomizerMixin):
    name = "ad_group_asset"
    target = Target(
        name=name,
        level=TargetLevel.AD_GROUP_AD_ASSET,
        metrics=[
            Field("clicks"),
            Field("impressions"),
            Field("biddable_app_install_conversions", "installs"),
            Field("biddable_app_post_install_conversions", "inapps"),
            Field("cost_micros / 1e6", "cost"),
            Field("conversions_value")
        ],
        dimensions=[
            Field("ad_group_ad_asset_view.performance_label",
                  "performance_label"),
            Field("ad_group_ad_asset_view.field_type", "type"),
            Field("ad_group_ad_asset_view.policy_summary:review_status",
                  "review_status"),
            Field("ad_group_ad_asset_view.policy_summary:approval_status",
                  "approval_status"),
            Field(
                "ad_group_ad_asset_view.policy_summary:policy_topic_entries.type",
                "policy_topic_type"),
            Field(
                "ad_group_ad_asset_view.policy_summary:policy_topic_entries.topic",
                "policy_topics")
        ],
        filters=("segments.date DURING TODAY "
                 "AND campaign.status = 'ENABLED' "
                 "AND ad_group.status = 'ENABLED' "
                 "AND ad_group_ad_asset_view.enabled = TRUE"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all", "demographics")
@register_conversion_split_collector
class AgeRangeCollector(CollectorCustomizerMixin):
    name = "age"
    target = Target(
        name=name,
        metrics=DEFAULT_METRICS,
        level=TargetLevel.CAMPAIGN,
        resource_name="age_range_view",
        dimensions=[Field("ad_group_criterion.age_range.type", "age_range")],
        filters=("segments.date DURING TODAY "
                 "AND campaign.status = 'ENABLED' "
                 "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all", "demographics")
@register_conversion_split_collector
class GenderCollector(CollectorCustomizerMixin):
    name = "gender"
    target = Target(
        name=name,
        metrics=DEFAULT_METRICS,
        level=TargetLevel.CAMPAIGN,
        resource_name="gender_view",
        dimensions=[Field("ad_group_criterion.gender.type", "gender")],
        filters=("segments.date DURING TODAY "
                 "AND campaign.status = 'ENABLED' "
                 "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all", "search")
@register_conversion_split_collector
class KeywordsCollector(CollectorCustomizerMixin):
    name = "keywords"
    target = Target(
        name=name,
        metrics=DEFAULT_METRICS + [Field("historical_quality_score")],
        level=TargetLevel.AD_GROUP,
        resource_name="keyword_view",
        dimensions=[
            Field("ad_group_criterion.keyword.text", "keyword"),
            Field("ad_group_criterion.keyword.match_type", "match_type")
        ],
        filters=("segments.date DURING TODAY "
                 "AND campaign.status = 'ENABLED' "
                 "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all", "geo")
@register_conversion_split_collector
class UserLocationCollector(CollectorCustomizerMixin):
    name = "user_location"
    target = Target(name=name,
                    metrics=DEFAULT_METRICS,
                    level=TargetLevel.CAMPAIGN,
                    resource_name="user_location_view",
                    dimensions=[
                        Field("user_location_view.country_criterion_id",
                              "country_id"),
                        Field("campaign.status")
                    ],
                    filters=("segments.date DURING TODAY "
                             "AND campaign.status = 'ENABLED' "
                             "AND metrics.clicks > 0"))

    def __init__(self, **kwargs):
        CollectorCustomizerMixin.customize_target(self.target, **kwargs)


@collector("all")
class CampaignOptimizationScoreCollector:
    name = "optimization_score"
    target = Target(name=name,
                    metrics=[
                        Field("campaign.optimization_score",
                              "campaign_optimization_score")
                    ],
                    level=TargetLevel.CAMPAIGN,
                    filters=("campaign.status = 'ENABLED'"),
                    suffix="Remove")


@collector("all")
class AccountStatus:
    name = "account_status"
    target = Target(name=name,
                    metrics=[Field("1", "info")],
                    level=TargetLevel.CUSTOMER,
                    dimensions=[Field("customer.status", "status")])


# TODO (amarkin): Verify
class OfflineConversionsImportCollector:
    name = "offline_conversions_import"
    target = Target(
        name=name,
        dimensions=[
            Field("customer.offline_conversion_client_summaries:status",
                  "status"),
            Field(
                "customer.offline_conversion_client_summaries:total_event_count",
                "total_events"),
            Field(
                "customer.offline_conversion_client_summaries:successful_event_count",
                "successful_event_count"),
        ],
        level=TargetLevel.CUSTOMER)


# TODO: WIP
class RemarketingListCollector:
    name = "remarketing_list"
    target = Target(name=name,
                    resource_name="user_list",
                    metrics=[
                        Field("user_list.size_for_display",
                              "size_for_display"),
                        Field("user_list.size_for_search", "size_for_search")
                    ],
                    dimensions=[
                        Field("user_list.id", "id"),
                        Field("user_list.type", "type"),
                        Field("user_list.name", "name")
                    ],
                    level=TargetLevel.CUSTOMER)


@collector("all")
class CampaignServingStatusCollector:
    name = "campaign_serving_status"
    target = Target(name=name,
                    metrics=[Field("1", "info")],
                    dimensions=[
                        Field("campaign.id"),
                        Field("campaign.primary_status", "primary_status"),
                        Field("campaign.primary_status_reasons",
                              "primary_status_reasons")
                    ],
                    level=TargetLevel.CAMPAIGN,
                    filters=("campaign.primary_status NOT IN "
                             "('ELIGIBLE', 'ENDED', 'PAUSED', 'REMOVED')"))


def default_collectors(kwargs) -> List[Target]:
    return [
        collector(**kwargs).target for name, collectors in registry.items()
        for collector in collectors.values() if name == "default"
    ]
