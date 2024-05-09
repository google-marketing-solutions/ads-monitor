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
"""Defines Target class and corresponding helper methods.

Target serves an important roles of building Google Ads queries from set of
diverse elements: metrics, dimensions, filters, resource names, etc.

Target can be:
  * similar (sharing the same metrics, dimensions and filters) which allows
    to perform similar target deduplication with the lowest common level.
  * equal (sharing the same attributes) - useful for checking target presence
    in the sets.

Metrics, dimensions and filters of a Target can be dynamically changed thus
allowing Target customization at the runtime.
"""
from __future__ import annotations

import copy
import dataclasses
import enum
import itertools
from collections.abc import Sequence

from gaarf_exporter import query_elements
from gaarf_exporter import util


class TargetLevel(enum.IntEnum):
  """Represents minimal level of entity.

  TargetLevel regulates which entity id (ad_id, ad_group_id, campaign_id, etc.)
  is associated with metrics and dimensions for a given target.
  Target levels are ordered hierarchically to support comparison operations.
  """
  UNKNOWN = 0
  AD_GROUP_AD_ASSET = 1
  AD_GROUP_AD = 2
  AD_GROUP = 3
  CAMPAIGN = 4
  CUSTOMER = 5
  MCC = 6

  @classmethod
  def contains(cls, *keys: str) -> bool:
    """Checks whether supplied keys are valid enum names."""
    return all(key.upper() in cls.__members__ for key in keys)


@dataclasses.dataclass
class LevelInfo:
  """Stores meta information for a particular TargetLevel.

  This meta information is used to correctly build query in the Target.

  Attributes:
    resource_name: Name of Google Ads reporting resource.
    id: Field name for entity id (i.e. ad_group.id, campaign.id) .
    id_alias: Alias for entity_id (i.e ad_group_id, campaign_id).
    name: Field name for entity content (i.e ad_group.name, campaign.name).
    name_alias: Alias for entity content (i.e ad_group_name, campaign_name).
    active_entities_filter: Filter to get only active entities.
  """
  resource_name: str
  id: str
  id_alias: str
  name: str
  name_alias: str
  active_entities_filter: str

  def to_query_field(self) -> str:
    """Returns field name with alias."""
    return f'{self.id} AS {self.id_alias}'

  def to_field(self) -> query_elements.Field:
    """Builds Field from level meta information."""
    return query_elements.Field(name=self.id, alias=self.id_alias)


_LEVELS = {
    TargetLevel.AD_GROUP_AD_ASSET:
        LevelInfo('ad_group_ad_asset_view', 'asset.id', 'asset_id',
                  'asset.name', 'asset',
                  'ad_group_ad_asset_view.enabled = TRUE'),
    TargetLevel.AD_GROUP_AD:
        LevelInfo('ad_group_ad', 'ad_group_ad.ad.id', 'ad_id',
                  'ad_group_ad.ad.name', 'ad_name',
                  'ad_group_ad.status = ENABLED'),
    TargetLevel.AD_GROUP:
        LevelInfo('ad_group', 'ad_group.id', 'ad_group_id', 'ad_group.name',
                  'ad_group_name', 'ad_group.status = ENABLED'),
    TargetLevel.CAMPAIGN:
        LevelInfo('campaign', 'campaign.id', 'campaign_id', 'campaign.name',
                  'campaign_name', 'campaign.status = ENABLED'),
    TargetLevel.CUSTOMER:
        LevelInfo('customer', 'customer.id', 'customer_id',
                  'customer.descriptive_name', 'account_name',
                  'customer.status = ENABLED'),
    TargetLevel.MCC:
        LevelInfo('customer', 'customer.id', 'customer_id',
                  'customer.descriptive_name', 'account_name',
                  'customer.status = ENABLED'),
}


class Target:
  """Represents collection of query elements needed to build a Google Ads query.

  Attributes:
    name: Unique identifier of a target.
    level: Minimal entity level in the target (ad_group, campaign, customer).
    metrics: All metrics (started with `metrics.`) associated with the target.
    dimensions: All segments and resources associated with the target.
    filters: Text conditions for limiting the query.
    resource_name: Name of resource to get data from (used in FROM statement).
    query: Full text of the query to be sent to Google Ads API.
    suffix: Optional custom identifier to the target.
  """

  def __init__(self,
               name: str | None = None,
               metrics: str | list[query_elements.Field] | None = None,
               level: TargetLevel | None = TargetLevel.AD_GROUP,
               resource_name: str | None = None,
               dimensions: str | list[query_elements.Field] | None = None,
               filters: str | None = None,
               suffix: str | None = None) -> None:
    """Initializes Target.

    Args:
      name: Unique identifier of a target.
      metrics: All metrics (started with `metrics.`) associated with the target.
      level: Minimal entity level in the target (ad_group, campaign, customer).
      resource_name: Name of resource to get data from (used in FROM statement).
      dimensions: All segments and resources associated with the target.
      filters: Text conditions for limiting the query.
      suffix: Optional custom identifier to the target.
    """
    self.name = name
    self._level = level
    self._resource_name = resource_name
    self._filters = filters
    self._metrics = self._init_fields(metrics, 'metrics')
    self._dimensions = self._init_fields(dimensions)
    self.suffix = suffix if suffix else name

  @property
  def level(self) -> TargetLevel | None:
    """Represents entity level of a target."""
    return self._level

  @level.setter
  def level(self, value: TargetLevel) -> None:
    """Changes saved level of a target."""
    self._level = value

  @property
  def metrics(self) -> set[query_elements.Field]:
    """Returns unique metrics."""
    return set(self._metrics)

  @metrics.setter
  def metrics(self, values: Sequence[query_elements.Field]) -> None:
    """Changes saved metrics of a target."""
    self._metrics = set(values)

  @property
  def dimensions(self) -> set[query_elements.Field]:
    """Returns unique metrics."""
    return set(self._dimensions)

  @dimensions.setter
  def dimensions(self, values: Sequence[query_elements.Field]) -> None:
    """Changes saved dimensions of a target."""
    self._dimensions = values

  @property
  def filters(self) -> str:
    """Returns filters or default placeholder."""
    return self._filters or 'segments.date DURING TODAY'

  @filters.setter
  def filters(self, values: str) -> None:
    """Changes saved dimensions of a target."""
    self._filters = values

  def _init_fields(self,
                   fields: str | list[query_elements.Field],
                   prefix: str = '') -> list[query_elements.Field]:
    """Transforms fields to proper Field format based on optional prefix.

    Args:
      fields: Query fields that needs to be initialized.
      prefix: Optional prefix that needs to be added before each field.

    Returns:
      Formatted list of Fields.

    Raises:
      ValueError: If fields has non-aliased virtual column.
    """
    if not fields:
      return []

    if fields and isinstance(fields, str):
      field_list = [
          query_elements.Field(name=field) for field in fields.split(',')
      ]
    else:
      field_list = fields

    if not prefix:
      return field_list

    for field in field_list:
      raw_tokens = util.tokenize(field.name)
      if not field.alias:
        if len(raw_tokens) > 1:
          raise ValueError('virtual column need an alias.')
        field.alias = field.name

      processed_tokens = []
      for value, token_type in raw_tokens:
        identifier = value
        if token_type == 'IDENTIFIER':
          identifier = f'{prefix}.{value}'
        processed_tokens.append(identifier)

      field.name = ' '.join(processed_tokens)

    return field_list

  @property
  def level_info(self) -> LevelInfo | None:
    """Returns meta information related to a target level."""
    return _LEVELS.get(self.level)

  @property
  def formatted_level(self) -> str:
    """Returns formatted level as field name with alias."""
    if level_info := self.level_info:
      return f'{level_info.to_query_field()},\n'
    return ''

  @property
  def formatted_metrics(self) -> str:
    """Returns formatted metrics as field names with aliases."""
    if not self.metrics:
      return '\n'
    metrics_info = ',\n'.join(
        [field.to_query_field() for field in sorted(self.metrics)])
    return f'{metrics_info},\n'

  @property
  def formatted_dimensions(self) -> str:
    """Returns formatted metrics as field names with aliases."""
    if not (dimensions := self.dimensions):
      return '\n'
    if level_info := self.level_info:
      dimensions = set(dimensions).difference(set([level_info.to_field()]))
    if not dimensions:
      return '\n'
    dimensions_info = ',\n'.join(
        [field.to_query_field() for field in sorted(dimensions)])
    return f'{dimensions_info},\n'

  @property
  def resource_name(self) -> str:
    """Gets resource_name or infers it from target level."""
    if self._resource_name:
      return self._resource_name
    if level_info := self.level_info:
      return level_info.resource_name.lower()
    return self.level.name

  @property
  def query(self) -> str:
    """Formats query based on elements."""
    return (f'SELECT {self.formatted_level}{self.formatted_metrics}'
            f'{self.formatted_dimensions}'
            f'FROM {self.resource_name}\n'
            f'WHERE {self.filters}')

  def is_similar(self, other: Target) -> bool:
    """Compares similarity between two targets.

    Similarity first checks whether two targets are coming from different
    non TargetLevel specific resouce_names, if they are different then
    targets are not similar.
    Then is compares all  metrics, dimensions and filters between two targets.

    Returns:
      Whether two targets are similar.
    """
    if not other or not isinstance(other, Target):
      return False

    if (self.resource_name != other.resource_name and
        not (TargetLevel.contains(self.resource_name, other.resource_name))):
      return False
    if (self.metrics, self.dimensions,
        self.filters) == (other.metrics, other.dimensions, other.filters):
      return True
    return False

  def __eq__(self, other: Target) -> bool:
    """Compares two targets based on similarity, resource_name and level."""
    if not self.is_similar(other):
      return False
    if self.level != other.level:
      return False
    return True

  def __lt__(self, other: Target) -> bool:
    """Compares targets by level values."""
    if self.level.value < other.level.value:
      return True
    return False

  def __gt__(self, other: Target) -> bool:
    """Compares targets by level values."""
    if self.level.value > other.level.value:
      return True
    return False

  def __hash__(self):
    return hash(self.query)


class ServiceTarget(Target):
  """Helper class for targets without metrics."""

  @property
  def metrics(self) -> set[query_elements.Field]:
    """Returns default info metric."""
    return {
        query_elements.Field(name='1', alias='info'),
    }

  @metrics.setter
  def metrics(self, value: query_elements.Field) -> None:
    """Ensures that metrics cannot be overwritten."""
    raise ValueError('Cannot change value of "metrics"!')


def create_default_service_target(level: TargetLevel) -> ServiceTarget:
  """Generates correct ServiceTarget based on provided level.

   Based on level (AD_GROUP, CAMPAIGN, ACCOUNT, etc.) corresponding
   ServiceTarget is created that contains all necessary mapping information
   downstream. I.e. if 'level=AD_GROUP' then information on ad_group, campaign
   and customer will be included in to the mapping.

   Returns:
    ServiceTarget called 'mapping' for an appropriate level.

  """
  if level == TargetLevel.MCC:
    level = TargetLevel.CUSTOMER
  dimensions = []
  filters = ''

  for target_level in TargetLevel:
    if (target_level not in (TargetLevel.MCC, TargetLevel.AD_GROUP_AD_ASSET) and
        level <= target_level and (level_info := _LEVELS.get(target_level))):
      dimensions.extend([
          query_elements.Field(name=level_info.id, alias=level_info.id_alias),
          query_elements.Field(
              name=level_info.name, alias=level_info.name_alias),
      ])
      if filters:
        filters = filters + ' AND ' + level_info.active_entities_filter
      else:
        filters = level_info.active_entities_filter

  return ServiceTarget(
      name='mapping', dimensions=dimensions, level=level, filters=filters)


def targets_similarity_check(targets: list[Target]) -> list[Target]:
  """Dedupicates targets.

  If there are similar target in the list return only those with the lowest
  level.

  Args:
    targets: Possible target values.

  Returns:
    Deduplicated targets.
  """
  cloned_targets = copy.deepcopy(targets)
  combinations = itertools.combinations(targets, 2)
  for target1, target2 in combinations:
    if target1.is_similar(target2):
      max_target = max(target1, target2)
      if max_target in cloned_targets:
        cloned_targets.remove(max_target)
  return cloned_targets
