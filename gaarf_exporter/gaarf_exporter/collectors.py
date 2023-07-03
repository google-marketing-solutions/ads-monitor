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
from .target import Target, TargetLevel
from .query_elements import Field, Customizer, CustomizerTypeEnum

T = TypeVar('T', bound='BaseCollector')


def collector(*registries: str) -> Callable:

    def class_collector(cls: Type[T]) -> Type[T]:
        for name in registries:
            if name not in registry:
                registry[name] = {}
            registry[name][cls.name] = cls
        return cls

    return class_collector


@runtime_checkable
class BaseCollector(Protocol):
    name: str
    target: Target


registry: Dict[str, Dict[str, Type[BaseCollector]]] = dict()

DEFAULT_METRICS = [
    Field("clicks"),
    Field("impressions"),
    Field("conversions"),
    Field("cost_micros / 1e6", "cost")
]


# TODO (amarkin): Make collector dynamically customizable
@collector("default", "generic")
class PerformanceCollector:
    name = "performance"

    def __init__(self) -> None:
        self.target = Target(
            name=self.name,
            metrics=DEFAULT_METRICS,
            level=TargetLevel.AD_GROUP,
            dimensions=[Field("segments.ad_network_type", "network")])


@collector("default", "generic")
class DisapprovalCollector:
    name = "disapproval"

    def __init__(self) -> None:
        self.target = Target(
            name=self.name,
            level=TargetLevel.AD_GROUP_AD,
            dimensions=[
                Field("campaign.id", "campaign_id"),
                Field("ad_group_ad.policy_summary.approval_status",
                      "approval_status"),
                Field("ad_group_ad.policy_summary.review_status",
                      "review_status")
            ],
            filters=(
                "campaign.status = 'ENABLED'"
                " AND ad_group.status = 'ENABLED'"
                " AND ad_group_ad.status = 'ENABLED'"
                " AND ad_group_ad.policy_summary.approval_status != 'APPROVED'"
            ))


@collector("default", "generic")
class ConversionActionCollector:
    name = "conversion_action"

    def __init__(self) -> None:
        self.target = Target(name=self.name,
                             metrics=[Field("all_conversions")],
                             level=TargetLevel.CUSTOMER,
                             dimensions=[
                                 Field("customer.id", "account_id"),
                                 Field(
                                     "segments.conversion_action",
                                     "conversion_id",
                                     Customizer(CustomizerTypeEnum.INDEX, '0'))
                             ],
                             filters=("segments.date DURING TODAY"
                                      " AND metrics.all_conversions > 0"))


@collector("default", "generic")
class MappingCollector:
    name = "mapping"

    def __init__(self) -> None:
        self.target = Target(name=self.name,
                             metrics=[Field("1", "info")],
                             level=TargetLevel.AD_GROUP,
                             dimensions=[
                                 Field("customer.descriptive_name",
                                       "account_name"),
                                 Field("campaign.name", "campaign_name"),
                                 Field("ad_group.id", "ad_group_id"),
                                 Field("ad_group.name", "ad_group_name")
                             ],
                             filters=("campaign.status = 'ENABLED'"
                                      " AND ad_group.status = 'ENABLED'"))


# TODO (amarkin): Support registering without argument
@collector("all")
class SearchTermsCollector:
    name = "search_terms"

    def __init__(self) -> None:
        self.target = Target(
            name=self.name,
            metrics=DEFAULT_METRICS,
            level=TargetLevel.CUSTOMER,
            resource_name="search_term_view",
            dimensions=[Field("search_term_view.search_term", "search_term")],
            filters="search_term_view.status = 'ADDED' AND metrics.clicks > 0"
        )


@collector("all")
class PlacementsCollector:
    name = "placements"

    def __init__(self) -> None:
        self.target = Target(
            name=self.name,
            metrics=DEFAULT_METRICS,
            level=TargetLevel.CUSTOMER,
            resource_name="group_placement_view",
            dimensions=[
                Field("group_placement_view.display_name", "name"),
                Field("group_placement_view.placement_type", "type")
            ],
            filters=
            "segments.date DURING TODAY AND campaign.status = 'ENABLED' AND metrics.cost_micros > 0"
        )


@collector("all")
class BidBudgetCollector:
    name = "bid_budgets"

    def __init__(self) -> None:
        self.target = Target(
            name=self.name,
            level=TargetLevel.CAMPAIGN,
            metrics=[
                Field("campaign_budget.amount_micros/1e6", "budget"),
                Field("campaign.target_cpa.target_cpa_micros/1e6",
                      "target_cpa"),
                # TODO (amarkin): Adding ROAS breaks labels of metric
                Field("campaign.target_roas.target_roas", "target_roas"),
            ],
            filters="campaign.status = 'ENABLED'")


def default_collectors() -> List[Target]:
    return [
        collector().target for name, collectors in registry.items()
        for collector in collectors.values() if name == "default"
    ]
