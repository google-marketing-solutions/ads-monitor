# Copyright 2023 Google LLC
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
"""Module for defining collectors.

Collectors are converted to gaarf queries that are sent to Ads API.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Callable
from typing import Protocol
from typing import TypeVar

from gaarf.cli import utils as gaarf_utils

from gaarf_exporter import query_elements
from gaarf_exporter import target as query_target

_REGISTRY: dict[str, dict[str, type[BaseCollector]]] = {}

_DEFAULT_METRICS = [
    query_elements.Field('clicks'),
    query_elements.Field('impressions'),
    query_elements.Field('conversions'),
    query_elements.Field('cost_micros / 1e6', 'cost')
]

_DEFAULT_CONVERSION_SPLIT_METRICS = [
    query_elements.Field('all_conversions'),
    query_elements.Field('all_conversions_value'),
]

_DEFAULT_CONVERSION_SPLIT_DIMENSIONS = [
    query_elements.Field('segments.conversion_action_category',
                         'conversion_category'),
    query_elements.Field('segments.conversion_action_name', 'conversion_name'),
    query_elements.Field(
        'segments.conversion_action', 'conversion_id',
        query_elements.Customizer(query_elements.CustomizerTypeEnum.INDEX, '0'))
]

_T = TypeVar('_T', bound='BaseCollector')


class BaseCollector(Protocol):
  """Default interface for all collectors.

  Attributes:
    name: Unique name that identifies the collector.
    target: query_target.Target definition of the collector.
  """
  name: str
  target: query_target.Target


def register(*registries: str) -> Callable:
  """Decorator for adding collector class to one or several registries.

  Args:
    registries: Name of all registries collector should be added to.
  Returns:
    Added collector.
  """

  def class_collector(cls: type[_T]) -> type[_T]:
    _REGISTRY[cls.name] = cls
    for name in registries:
      if name not in _REGISTRY:
        _REGISTRY[name] = {}
      _REGISTRY[name][cls.name] = cls
    return cls

  return class_collector


def _create_conversion_split_collector(
    seed_collector: BaseCollector) -> type[BaseCollector]:
  """Helper for generating collectors for conversion split.

  Based on existing collector (set of dimensions and a level) creates new
  collector that fetches conversion split metrics.

  Args:
    seed_collector: Collector class to base new collector on.
  Returns:
    Collector with conversion split metrics.
  """
  name = seed_collector.__name__.replace('Collector', '')
  name = f'{name}ConversionSplitCollector'
  cls = type(name, (seed_collector,),
             {'name': seed_collector.name + '_conversion_split'})
  cls.target = query_target.Target(
      name=cls.name,
      metrics=_DEFAULT_CONVERSION_SPLIT_METRICS,
      level=seed_collector.target.level,
      resource_name=seed_collector.target.resource_name,
      dimensions=_DEFAULT_CONVERSION_SPLIT_DIMENSIONS,
      filters=('segments.date DURING TODAY '
               'AND metrics.all_conversions > 0'))
  return cls


def register_conversion_split_collector(cls: type[_T]) -> type[_T]:
  """Decorator for creating and adding conversion collector class registries.

  Args:
    cls: Collector class to base new conversion collector on.
  Returns:
    Added conversion split collector.
  """
  conv_split_cls = _create_conversion_split_collector(cls)
  _REGISTRY[conv_split_cls.name] = {
      conv_split_cls.name: conv_split_cls,
      cls.name: cls
  }
  return cls


class CollectorCustomizerMixin:
  """Mixin for dynamically changing targets in collectors."""

  def customize_target(target: query_target.Target,
                       **kwargs: str) -> query_target.Target:
    """Executes a series of customizations on a target based on provided kwargs.

    Args:
      target: An instance of query_target.Target that needs to be customized.
      kwargs: Arguments for target customization.

    Returns:
      Modified target.
    """
    target = CollectorCustomizerMixin._format_date_range(target, **kwargs)
    target = CollectorCustomizerMixin._format_level(target, **kwargs)
    return target

  def _format_date_range(target: query_target.Target,
                         **kwargs: str) -> query_target.Target:
    """Changes default period in report to custom one.

    Args:
      target: An instance of query_target.Target that needs to be customized.
      kwargs: Arguments for target customization.

    Returns:
      Modified target.
    """
    if kwargs and (start_date :=
                   kwargs.get('start_date')) and (end_date :=
                                                  kwargs.get('end_date')):
      start_date = gaarf_utils.convert_date(start_date)
      end_date = gaarf_utils.convert_date(end_date)
      target.filters = target.filters.replace(
          'DURING TODAY', f"BETWEEN '{start_date}' AND '{end_date}'")
      n_days = (datetime.strptime(end_date, '%Y-%m-%d') -
                datetime.strptime(start_date, '%Y-%m-%d')).days + 1
      if target.dimensions:
        target.dimensions.add(query_elements.Field(str(n_days), 'n_days'))
      else:
        target.dimensions = [query_elements.Field(str(n_days), 'n_days')]
    return target

  def _format_level(target: query_target.Target,
                    **kwargs: str) -> query_target.Target:
    """Changes default level in report to custom one.

    Args:
      target: An instance of query_target.Target that needs to be customized.
      kwargs: Arguments for target customization.

    Returns:
      Modified target.
    """
    if kwargs and (level := kwargs.get('level')):
      target.level = query_target.TargetLevel[level.upper()]
    return target


# TODO (amarkin): Make collector dynamically customizable
@register('default')
@register_conversion_split_collector
class PerformanceCollector(CollectorCustomizerMixin):
  """Gets performance metrics (clicks, impressions, cost) for ad groups."""
  name = 'performance'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.AD_GROUP,
      dimensions=[
          query_elements.Field('segments.ad_network_type', 'network'),
      ],
      filters='segments.date DURING TODAY',
      suffix='Remove')

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('default', 'disapprovals')
class DisapprovalCollector:
  """Gets ad_group_ad approval and review status info."""
  name = 'ad_disapprovals'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.AD_GROUP_AD,
      dimensions=[
          query_elements.Field('ad_group.id', 'ad_group_id'),
          query_elements.Field('ad_group_ad.policy_summary.approval_status',
                               'approval_status'),
          query_elements.Field('ad_group_ad.policy_summary.review_status',
                               'review_status'),
          query_elements.Field(
              'ad_group_ad.policy_summary.policy_topic_entries:type',
              'topic_type'),
          query_elements.Field(
              'ad_group_ad.policy_summary.policy_topic_entries:topic', 'topic'),
          query_elements.Field('1', 'ad_count'),
      ],
      filters=("campaign.status = 'ENABLED'"
               " AND ad_group.status = 'ENABLED'"
               " AND ad_group_ad.status = 'ENABLED'"
               " AND ad_group_ad.policy_summary.approval_status != 'APPROVED'"),
      suffix='disapprovals')


@register('disapprovals')
class AdGroupAdAssetDisapprovalCollector:
  """Gets ad_group_ad_asset approval and review status info."""
  name = 'ad_group_ad_asset_disapprovals'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.AD_GROUP,
      dimensions=[
          query_elements.Field('asset.id', 'asset_id'),
          query_elements.Field('ad_group_ad_asset_view.field_type',
                               'field_type'),
          query_elements.Field(
              'ad_group_ad_asset_view.policy_summary:approval_status',
              'approval_status'),
          query_elements.Field(
              'ad_group_ad_asset_view.policy_summary:review_status',
              'review_status'),
          query_elements.Field(
              'ad_group_ad_asset_view.policy_summary:policy_topic_entries.type',
              'topic_type'),
          query_elements.Field(
              'ad_group_ad_asset_view.policy_summary:'
              'policy_topic_entries.topic', 'topic'),
          query_elements.Field('1', 'asset_count'),
      ],
      resource_name='ad_group_ad_asset_view',
      filters=("campaign.status = 'ENABLED'"
               " AND ad_group.status = 'ENABLED'"
               ' AND ad_group_ad_asset_view.enabled = True'))


@register('disapprovals')
class SitelinkDisapprovalCollector:
  """Gets sitelink approval and review status info."""
  name = 'sitelink_disapprovals'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.UNKNOWN,
      dimensions=[
          query_elements.Field('asset.id', 'asset_id'),
          query_elements.Field('asset.sitelink_asset.link_text',
                               'sitelink_title'),
          query_elements.Field('asset.sitelink_asset.description1',
                               'sitelink_description1'),
          query_elements.Field('asset.sitelink_asset.description2',
                               'sitelink_description2'),
          query_elements.Field('asset.policy_summary.approval_status',
                               'approval_status'),
          query_elements.Field('asset.policy_summary.review_status',
                               'review_status'),
          query_elements.Field('asset.policy_summary.policy_topic_entries:type',
                               'topic_type'),
          query_elements.Field(
              'asset.policy_summary.policy_topic_entries:topic', 'topic'),
          query_elements.Field('1', 'sitelink_count'),
      ],
      resource_name='asset',
      filters=("asset.type = 'SITELINK' "
               "AND asset.policy_summary.approval_status != 'APPROVED'"))


@register('default')
class ConversionActionCollector:
  """Gets information on number of conversion by conversion_name."""
  name = 'conversion_action'
  target = query_target.Target(
      name=name,
      metrics=[
          query_elements.Field('all_conversions'),
      ],
      level=query_target.TargetLevel.CUSTOMER,
      dimensions=[
          query_elements.Field('customer.id', 'account_id'),
          query_elements.Field('segments.conversion_action_name',
                               'conversion_name'),
          query_elements.Field(
              'segments.conversion_action', 'conversion_id',
              query_elements.Customizer(query_elements.CustomizerTypeEnum.INDEX,
                                        '0')),
      ],
      filters=('segments.date DURING TODAY'
               ' AND metrics.all_conversions > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('app')
class AppCampaignMappingCollector:
  """Maps campaign_id to app campaign meta information for active campaigns."""
  name = 'app_campaign_mapping'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.CAMPAIGN,
      dimensions=[
          query_elements.Field('campaign.app_campaign_setting.app_id',
                               'app_id'),
          query_elements.Field('campaign.app_campaign_setting.app_store',
                               'app_store'),
          query_elements.Field(
              'campaign.app_campaign_setting.bidding_strategy_goal_type',
              'bidding_strategy'),
      ],
      filters=('campaign.status = ENABLED'
               ' AND campaign.advertising_channel_type = MULTI_CHANNEL'))


@register('app')
class AppAssetMappingCollector:
  """Maps campaign_id to app campaign meta information for active campaigns."""
  name = 'app_asset_mapping'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.UNKNOWN,
      dimensions=[
          query_elements.Field('asset.id', 'asset_id'),
          query_elements.Field('asset.type', 'asset_type'),
          query_elements.Field('asset.source', 'source'),
          query_elements.Field('asset.name', 'asset_name'),
          query_elements.Field('asset.text_asset.text', 'text'),
          query_elements.Field('asset.youtube_video_asset.youtube_video_id',
                               'video_id'),
      ],
      resource_name='asset',
      filters='asset.type IN (IMAGE, TEXT, YOUTUBE_VIDEO, MEDIA_BUNDLE)')


@register('pmax')
class PmaxPerformanceCollector:
  """Gets performance metrics for pMax asset groups."""
  name = 'pmax_performance'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.UNKNOWN,
      dimensions=[
          query_elements.Field('asset_group.id', 'asset_group_id'),
      ],
      resource_name='asset_group',
      filters=('campaign.advertising_channel_type = PERFORMANCE_MAX'
               ' AND metrics.impressions > 0'))


@register('pmax')
class PmaxMappingCollector:
  """Maps asset group id to pMax ad_group/campaign meta information."""
  name = 'pmax_mapping'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.UNKNOWN,
      dimensions=[
          query_elements.Field('customer.descriptive_name', 'account_name'),
          query_elements.Field('customer.id', 'account_id'),
          query_elements.Field('campaign.name', 'campaign_name'),
          query_elements.Field('campaign.id', 'campaign_id'),
          query_elements.Field('campaign.bidding_strategy_type',
                               'bidding_strategy_type'),
          query_elements.Field('campaign.advertising_channel_type',
                               'campaign_type'),
          query_elements.Field('campaign.advertising_channel_sub_type',
                               'campaign_sub_type'),
          query_elements.Field('campaign.start_date', 'start_date'),
          query_elements.Field('asset_group.id', 'ad_group_id'),
          query_elements.Field('asset_group.name', 'ad_group_name'),
      ],
      resource_name='asset_group',
      filters=('campaign.status = ENABLED'
               ' AND campaign.advertising_channel_type = PERFORMANCE_MAX'
               ' AND asset_group.status = ENABLED'))


@register('pmax', 'disapprovals')
class PmaxDisapprovalsCollector:
  """Gets asset_id approval and review status info for pMax campaigns."""
  name = 'pmax_disapprovals'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.UNKNOWN,
      dimensions=[
          query_elements.Field(
              'asset_group_asset.asset', 'asset_id',
              query_elements.Customizer(query_elements.CustomizerTypeEnum.INDEX,
                                        '0')),
          query_elements.Field(
              'asset_group_asset.asset_group', 'asset_group_id',
              query_elements.Customizer(query_elements.CustomizerTypeEnum.INDEX,
                                        '0')),
          query_elements.Field(
              'asset_group_asset.policy_summary.approval_status',
              'approval_status'),
          query_elements.Field('asset_group_asset.policy_summary.review_status',
                               'review_status'),
          query_elements.Field(
              'asset_group_asset.policy_summary.policy_topic_entries:type',
              'topic_type'),
          query_elements.Field(
              'asset_group_asset.policy_summary.policy_topic_entries:topic',
              'topic'),
          query_elements.Field('1', 'asset_count'),
      ],
      resource_name='asset_group_asset',
      filters=('campaign.status = ENABLED'
               ' AND campaign.advertising_channel_type = PERFORMANCE_MAX'
               ' AND asset_group_asset.status = ENABLED'))


@register('default')
class MappingCollector:
  """Maps ad_group_ad to ad_group/campaign meta information."""
  name = 'mapping'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.AD_GROUP_AD,
      dimensions=[
          query_elements.Field('customer.descriptive_name', 'account_name'),
          query_elements.Field('customer.id', 'account_id'),
          query_elements.Field('campaign.name', 'campaign_name'),
          query_elements.Field('campaign.id', 'campaign_id'),
          query_elements.Field('campaign.bidding_strategy_type',
                               'bidding_strategy_type'),
          query_elements.Field('campaign.advertising_channel_type',
                               'campaign_type'),
          query_elements.Field('campaign.advertising_channel_sub_type',
                               'campaign_sub_type'),
          query_elements.Field('campaign.start_date', 'start_date'),
          query_elements.Field('ad_group.id', 'ad_group_id'),
          query_elements.Field('ad_group.name', 'ad_group_name'),
      ],
      filters=("campaign.status = 'ENABLED'"
               " AND ad_group.status = 'ENABLED'"
               " AND ad_group_ad.status = 'ENABLED'"))


@register()
class AdGroupMappingCollector:
  """Maps ad_group to basic campaign/account meta information."""
  name = 'ad_group_mapping'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.AD_GROUP,
      dimensions=[
          query_elements.Field('customer.descriptive_name', 'account_name'),
          query_elements.Field('customer.id', 'account_id'),
          query_elements.Field('campaign.name', 'campaign_name'),
          query_elements.Field('campaign.id', 'campaign_id'),
          query_elements.Field('ad_group.id', 'ad_group_id'),
          query_elements.Field('ad_group.name', 'ad_group_name'),
      ],
      filters='campaign.status = ENABLED AND ad_group.status = ENABLED')


@register('search')
@register_conversion_split_collector
class SearchTermsCollector(CollectorCustomizerMixin):
  """Gets basic performance metrics for search terms on ad_group level."""
  name = 'search_terms'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.AD_GROUP,
      resource_name='search_term_view',
      dimensions=[
          query_elements.Field('search_term_view.search_term', 'search_term')
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register()
@register_conversion_split_collector
class PlacementsCollector(CollectorCustomizerMixin):
  """Gets basic performance metrics for placements on ad_group level."""
  name = 'placements'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.CUSTOMER,
      resource_name='group_placement_view',
      dimensions=[
          query_elements.Field('group_placement_view.display_name', 'name'),
          query_elements.Field('group_placement_view.placement_type', 'type'),
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register()
class BidBudgetCollector:
  """Gets bid and budget states for active campaigns."""
  name = 'bid_budgets'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.CAMPAIGN,
      metrics=[
          query_elements.Field('campaign_budget.amount_micros/1e6', 'budget'),
          query_elements.Field('campaign.target_cpa.target_cpa_micros/1e6',
                               'target_cpa'),
          query_elements.Field(
              'campaign.maximize_conversions.target_cpa_micros/1e6',
              'max_conv_target_cpa'),
          query_elements.Field('campaign.target_roas.target_roas',
                               'target_roas'),
      ],
      filters="campaign.status = 'ENABLED'")


@register()
class BudgetCollector:
  """Gets budget states for active campaigns."""
  name = 'budgets'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.CAMPAIGN,
      metrics=[
          query_elements.Field('campaign_budget.amount_micros/1e6', 'budget'),
      ],
      filters="campaign.status = 'ENABLED'")


@register()
class BidCollector:
  """Gets bid states for active campaigns."""
  name = 'bids'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.CAMPAIGN,
      metrics=[
          query_elements.Field('campaign.target_cpa.target_cpa_micros/1e6',
                               'target_cpa'),
          query_elements.Field(
              'campaign.maximize_conversions.target_cpa_micros/1e6',
              'max_conv_target_cpa'),
          query_elements.Field('campaign.target_roas.target_roas',
                               'target_roas'),
      ],
      filters="campaign.status = 'ENABLED'")


@register('app')
class AssetPerformanceCollector(CollectorCustomizerMixin):
  """Gets performance and approval/review status for app campaigns."""
  name = 'asset_performance'
  target = query_target.Target(
      name=name,
      level=query_target.TargetLevel.AD_GROUP_AD_ASSET,
      metrics=[
          query_elements.Field('clicks'),
          query_elements.Field('impressions'),
          query_elements.Field('biddable_app_install_conversions', 'installs'),
          query_elements.Field('biddable_app_post_install_conversions',
                               'inapps'),
          query_elements.Field('cost_micros / 1e6', 'cost'),
          query_elements.Field('conversions_value'),
      ],
      dimensions=[
          query_elements.Field('ad_group.id', 'ad_group_id'),
          query_elements.Field('segments.ad_network_type', 'network'),
          query_elements.Field('ad_group_ad_asset_view.performance_label',
                               'performance_label'),
          query_elements.Field('ad_group_ad_asset_view.field_type', 'type'),
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               "AND ad_group.status = 'ENABLED' "
               'AND ad_group_ad_asset_view.enabled = TRUE'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('app')
class AssetPerformanceGroupppingCollector(CollectorCustomizerMixin):
  """Gets performance and approval/review status for app campaigns."""
  name = 'asset_perf_label'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.AD_GROUP_AD_ASSET,
      dimensions=[
          query_elements.Field('ad_group.id', 'ad_group_id'),
          query_elements.Field('ad_group_ad_asset_view.performance_label',
                               'performance_label'),
          query_elements.Field('ad_group_ad_asset_view.field_type', 'type'),
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               "AND ad_group.status = 'ENABLED' "
               'AND ad_group_ad_asset_view.enabled = TRUE'))


@register('demographics')
@register_conversion_split_collector
class AgeRangeCollector(CollectorCustomizerMixin):
  """Gets performance information for age range."""
  name = 'age'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.CAMPAIGN,
      resource_name='age_range_view',
      dimensions=[
          query_elements.Field('ad_group_criterion.age_range.type',
                               'age_range'),
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('demographics')
@register_conversion_split_collector
class GenderCollector(CollectorCustomizerMixin):
  """Gets performance information for gender."""
  name = 'gender'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.CAMPAIGN,
      resource_name='gender_view',
      dimensions=[
          query_elements.Field('ad_group_criterion.gender.type', 'gender'),
      ],
      filters=('segments.date DURING TODAY '
               "AND campaign.status = 'ENABLED' "
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('search')
@register_conversion_split_collector
class KeywordsCollector(CollectorCustomizerMixin):
  """Gets basic performance metrics for keywords."""
  name = 'keywords'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.AD_GROUP,
      resource_name='keyword_view',
      dimensions=[
          query_elements.Field('ad_group_criterion.keyword.text', 'keyword'),
          query_elements.Field('ad_group_criterion.keyword.match_type',
                               'match_type'),
      ],
      filters=('segments.date DURING TODAY '
               'AND campaign.status = ENABLED '
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


class KeywordQualityScoreCollector(CollectorCustomizerMixin):
  """Gets quality score for keywords."""
  name = 'keyword_quality_score'
  target = query_target.Target(
      name=name,
      metrics=[
          query_elements.Field('historical_quality_score'),
      ],
      level=query_target.TargetLevel.AD_GROUP,
      resource_name='keyword_view',
      dimensions=[
          query_elements.Field('ad_group_criterion.keyword.text', 'keyword'),
          query_elements.Field('ad_group_criterion.keyword.match_type',
                               'match_type'),
      ],
      filters=('segments.date DURING YESTERDAY '
               'AND campaign.status = ENABLED '
               'AND metrics.clicks > 0'))


@register('search')
class CampaignSearchClickShareCollector(CollectorCustomizerMixin):
  """Gets search click share for each campaign."""
  name = 'campaign_click_share'
  target = query_target.Target(
      name=name,
      metrics=[
          query_elements.Field('search_click_share', 'click_share'),
      ],
      level=query_target.TargetLevel.CAMPAIGN,
      filters='segments.date DURING TODAY')

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register('geo')
@register_conversion_split_collector
class UserLocationCollector(CollectorCustomizerMixin):
  """Gets performance information for user_location (country_id)."""
  name = 'user_location'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      level=query_target.TargetLevel.CAMPAIGN,
      resource_name='user_location_view',
      dimensions=[
          query_elements.Field('user_location_view.country_criterion_id',
                               'country_id'),
      ],
      filters=('segments.date DURING TODAY '
               'AND metrics.clicks > 0'))

  def __init__(self, **kwargs):
    self.target = CollectorCustomizerMixin.customize_target(
        self.target, **kwargs)


@register()
class CampaignOptimizationScoreCollector:
  """Gets optimization score by each campaign."""
  name = 'optimization_score'
  target = query_target.Target(
      name=name,
      metrics=[
          query_elements.Field('campaign.optimization_score',
                               'campaign_optimization_score'),
      ],
      level=query_target.TargetLevel.CAMPAIGN,
      filters=("campaign.status = 'ENABLED'"),
      suffix='Remove')


@register()
class AccountStatus:
  """Gets status each account."""
  name = 'account_status'
  target = query_target.ServiceTarget(
      name=name,
      level=query_target.TargetLevel.CUSTOMER,
      dimensions=[
          query_elements.Field('customer.status', 'status'),
      ])


# TODO (amarkin): Verify
class OfflineConversionsImportCollector:
  """Gets status of offline conversion import for each account."""
  name = 'offline_conversions_import'
  target = query_target.Target(
      name=name,
      dimensions=[
          query_elements.Field(
              'customer.offline_conversion_client_summaries:status', 'status'),
          query_elements.Field(
              'customer.offline_conversion_client_summaries:total_event_count',
              'total_events'),
          query_elements.Field(
              'customer.offline_conversion_client_summaries:'
              'successful_event_count', 'successful_event_count'),
      ],
      level=query_target.TargetLevel.CUSTOMER)


# TODO: WIP
class RemarketinglistCollector:
  """Gets sizes of remarketing lists for each account."""
  name = 'remarketing_list'
  target = query_target.Target(
      name=name,
      resource_name='user_list',
      metrics=[
          query_elements.Field('user_list.size_for_display',
                               'size_for_display'),
          query_elements.Field('user_list.size_for_search', 'size_for_search'),
      ],
      dimensions=[
          query_elements.Field('user_list.id', 'id'),
          query_elements.Field('user_list.type', 'type'),
          query_elements.Field('user_list.name', 'name'),
      ],
      level=query_target.TargetLevel.CUSTOMER)


@register()
class LandingPagePerformanceCollector:
  """Gets serving status for each campaign."""
  name = 'landing_page'
  target = query_target.Target(
      name=name,
      metrics=_DEFAULT_METRICS,
      dimensions=[
          query_elements.Field('landing_page_view.unexpanded_final_url',
                               'landing_page'),
      ],
      level=query_target.TargetLevel.CUSTOMER,
      resource_name='landing_page_view',
      filters=('metrics.impressions > 0'))


@register()
class CampaignServingStatusCollector:
  """Gets serving status for each campaign."""
  name = 'campaign_serving_status'
  target = query_target.ServiceTarget(
      name=name,
      dimensions=[
          query_elements.Field('campaign.id'),
          query_elements.Field('campaign.primary_status', 'primary_status'),
          query_elements.Field('campaign.primary_status_reasons',
                               'primary_status_reasons'),
      ],
      level=query_target.TargetLevel.CAMPAIGN,
      filters=('campaign.primary_status NOT IN '
               "('ELIGIBLE', 'ENDED', 'PAUSED', 'REMOVED')"))


class Registry:
  """Maps collector names to corresponding classes.

  Registry simplifies searching for collectors as well as addding new ones.

  Attributes:
    collectors: Mapping between collector names and corresponding class.
  """

  def __init__(self, collectors: dict | None = None) -> None:
    """Creates Registry based on module level variable _REGISTRY."""
    if collectors:
      self.collectors = dict(collectors)
    else:
      self.collectors = dict(_REGISTRY)

  @property
  def default_collectors(self) -> CollectorSet:
    """Helper for getting only default collectors from the registry."""
    return CollectorSet(collectors=set(self.collectors.get('default').values()))

  @property
  def all_collectors(self) -> CollectorSet:
    """Helper for getting all collectors from the registry."""
    all_collector_names = ','.join(self.collectors.keys())
    return self.find_collectors(collector_names=all_collector_names)

  def find_collectors(self, collector_names: str | None = None) -> CollectorSet:
    """Extracts collectors from registry and returns their initialized targets.

    Args:
      collector_names:
        Names of collectors that need to be fetched from registry.

    Returns:
      Found collectors.
    """
    if not collector_names:
      return CollectorSet()
    if collector_names == 'all':
      return self.all_collectors
    collectors_subset = [
        collector for name, collector in self.collectors.items()
        if name in collector_names.strip().split(',')
    ]
    found_collectors = set()
    for collector in collectors_subset:
      if isinstance(collector, dict):
        for collector_ in collector.values():
          found_collectors.add(collector_)
      else:
        found_collectors.add(collector)
    return CollectorSet(collectors=set(found_collectors))

  def add_collectors(self, collectors: Sequence[BaseCollector]) -> None:
    """Ads collectors to the registry.

    Args:
      collectors: Collectors classes to be added to registry.
    """
    for collector in collectors:
      self.collectors[collector.name] = collector


class CollectorSet:
  """Represent a set of collectors returned from Registry."""

  def __init__(self, collectors: set[BaseCollector] | None = None) -> None:
    """Initializes CollectorSet based on provided collectors."""
    self._collectors = collectors or set()
    self._customized_collectors: set[BaseCollector] = set()

  @property
  def collectors(self) -> set[BaseCollector]:
    """Return customized or original collectors of the CollectorSet."""
    return self._customized_collectors or self._collectors

  def customize(self, kwargs: dict) -> None:
    """Changes collectors in the set based on provided arguments mapping.

    Args:
      kwargs:
        Mapping between name and values of elements in collector to be
        customized.
    """
    self._customized_collectors.clear()
    customized_collectors = set()
    for collector in self.collectors:
      if issubclass(collector, CollectorCustomizerMixin):
        customized_collectors.add(collector(**kwargs))
      else:
        customized_collectors.add(collector)
    self._customized_collectors = customized_collectors

  @property
  def targets(self) -> set[query_target.Target]:
    """Gets target from collectors in the set."""
    return {collector.target for collector in self.collectors}

  def __bool__(self):
    return bool(self.collectors)

  def __eq__(self, other) -> bool:
    return self.collectors == other.collectors

  def __contains__(self, key: BaseCollector) -> bool:
    return key in self.collectors
