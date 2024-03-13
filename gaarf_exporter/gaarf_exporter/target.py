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
from __future__ import annotations

import copy
import dataclasses
import enum
import itertools

from gaarf_exporter import util
from gaarf_exporter.query_elements import Field


class TargetLevel(enum.IntEnum):
  UNKNOWN = 0
  AD_GROUP_AD_ASSET = 1
  AD_GROUP_AD = 2
  AD_GROUP = 3
  CAMPAIGN = 4
  CUSTOMER = 5
  MCC = 6


@dataclasses.dataclass
class LevelInfo:
  resource_name: str
  id: str
  id_alias: str
  name: str
  name_alias: str
  active_entities_filter: str


_LEVELS = {
    TargetLevel.AD_GROUP_AD_ASSET:
        LevelInfo('ad_group_ad_asset_view', 'asset.id', 'asset_id',
                  'asset.name', 'asset',
                  'ad_group_ad_asset_view.enabled = TRUE'),
    TargetLevel.AD_GROUP_AD:
        LevelInfo('ad_group_ad', 'ad_group_ad.ad.id', 'ad_id',
                  'ad_group_ad.ad.name', 'ad_name',
                  "ad_group_ad.status = 'ENABLED'"),
    TargetLevel.AD_GROUP:
        LevelInfo('ad_group', 'ad_group.id', 'ad_group_id', 'ad_group.name',
                  'ad_group_name', "ad_group.status = 'ENABLED'"),
    TargetLevel.CAMPAIGN:
        LevelInfo('campaign', 'campaign.id', 'campaign_id', 'campaign.name',
                  'campaign_name', "campaign.status = 'ENABLED'"),
    TargetLevel.CUSTOMER:
        LevelInfo('customer', 'customer.id', 'customer_id',
                  'customer.descriptive_name', 'account_name',
                  "customer.status = 'ENABLED'"),
    TargetLevel.MCC:
        LevelInfo('customer', 'customer.id', 'customer_id',
                  'customer.descriptive_name', 'account_name',
                  "customer.status = 'ENABLED'"),
}


class Target:

  def __init__(self,
               name: str | None = None,
               metrics: str | list[Field] | None = None,
               level: TargetLevel | None = TargetLevel.AD_GROUP,
               resource_name: str | None = None,
               dimensions: str | list[Field] | None = None,
               filters: str | None = None,
               suffix: str | None = None) -> None:
    self.name = name
    self.level = level
    self.resource_name = resource_name
    self.filters = filters
    self.metrics = self._init_fields(metrics, 'metrics')
    self.dimensions = self._init_fields(dimensions)
    self.suffix = suffix if suffix else name

  @staticmethod
  def is_number(token):
    try:
      float(token)
      return True
    except ValueError:
      pass
    return False

  @staticmethod
  def is_math_operator(token):
    return token in ['+', '-', '*', '/']

  @staticmethod
  def _init_fields(fields: str | list[Field], prefix: str = '') -> list[Field]:
    if not fields:
      return []

    if fields and isinstance(fields, str):
      field_list = [Field(name=field) for field in fields.split(',')]
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

  def _get_level(self):
    if level_info := _LEVELS.get(self.level):
      return (f'{level_info.id} AS '
              f'{level_info.id_alias},\n')
    return ''

  @property
  def _resource_name(self) -> str:
    if self.resource_name:
      return self.resource_name
    if level_info := _LEVELS.get(self.level):
      return level_info.resource_name.lower()

  @property
  def _filters(self) -> str:
    return self.filters or 'segments.date DURING TODAY'

  @property
  def query(self):
    select_fields = []
    dedup = set()
    for field in self.metrics:
      if field not in dedup:
        select_fields.append(field)
        dedup.add(field)
    metrics = ''
    if select_fields:
      metrics = ',\n'.join([field.to_query_field() for field in select_fields])
    select_fields.clear()

    for field in self.dimensions:
      if field not in dedup:
        # should not add a name-only field with the same name as what
        # the level defines.
        if (not field.alias and not field.customizer and
            self.level != TargetLevel.UNKNOWN and
            field.name == _LEVELS[self.level].id):
          continue
        select_fields.append(field)
        dedup.add(field)
    dimensions = ''
    if select_fields:
      dimensions = ',\n'.join(
          [field.to_query_field() for field in select_fields])
      if metrics:
        dimensions = ',\n' + dimensions

    return (f'SELECT {self._get_level()}{metrics}{dimensions}\n'
            f'FROM {self._resource_name}\n'
            f'WHERE {self._filters}')

  @staticmethod
  def to_comparable_str(val: str | list[Field] | None) -> str:
    if not val:
      return ''
    if isinstance(val, str):
      return util.remove_spaces(val)
    elif isinstance(val, list):
      return util.remove_spaces(''.join(sorted([str(f) for f in val])))

  def is_similar(self, other):
    if not other or not isinstance(other, Target):
      return False

    if (self.to_comparable_str(self.metrics)
        != self.to_comparable_str(other.metrics)):
      return False

    if (self.to_comparable_str(self.dimensions)
        != self.to_comparable_str(other.dimensions)):
      return False

    if (self.to_comparable_str(self.filters)
        != self.to_comparable_str(other.filters)):
      return False

    if (self.to_comparable_str(self.resource_name)
        != self.to_comparable_str(other.resource_name)):
      return False
    return True

  def __eq__(self, other):
    if not self.is_similar(other):
      return False

    if self.level != other.level:
      return False

    return True

  def __lt__(self, other):
    if self.level.value < other.level.value:
      return True
    return False

  def __gt__(self, other):
    if self.level.value > other.level.value:
      return True
    return False

  def __hash__(self):
    return hash((self.to_comparable_str(self.metrics),
                 self.to_comparable_str(self.dimensions),
                 self.to_comparable_str(self.filters),
                 self.to_comparable_str(self.resource_name), self.level))


class ServiceTarget(Target):

  def _get_level(self):
    return ''


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
          Field(name=level_info.id, alias=level_info.id_alias),
          Field(name=level_info.name, alias=level_info.name_alias),
      ])
      if filters:
        filters = filters + ' AND ' + level_info.active_entities_filter
      else:
        filters = level_info.active_entities_filter

  return ServiceTarget(
      name='mapping',
      metrics=[
          Field(name='1', alias='info'),
      ],
      dimensions=dimensions,
      level=level,
      filters=filters)


def targets_similarity_check(targets: list[Target]) -> list[Target]:
  cloned_targets = copy.deepcopy(targets)
  combinations = itertools.combinations(targets, 2)
  for target1, target2 in combinations:
    if target1.is_similar(target2):
      max_target = max(target1, target2)
      if max_target in cloned_targets:
        cloned_targets.remove(max_target)
  return cloned_targets
