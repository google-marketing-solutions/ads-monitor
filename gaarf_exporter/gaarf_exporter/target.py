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

from collections import namedtuple
import copy
from enum import Enum
import itertools
from typing import List, Optional, Union

from . import util
from .query_elements import Field


class TargetLevel(Enum):
    UNKNOWN = 0
    AD_GROUP_AD_ASSET = 1
    AD_GROUP_AD = 2
    AD_GROUP = 3
    CAMPAIGN = 4
    CUSTOMER = 5
    MCC = 6


Level = namedtuple('Level',
                   ['table', 'id', 'id_alias', 'name', 'name_alias', 'filter'])

LEVELS = (
    None,
    Level('ad_group_ad_asset_view', 'asset.id', 'asset_id',
          'asset.name', 'asset',
          "ad_group_ad_asset_view.enabled = TRUE"),
    Level('ad_group_ad', 'ad_group_ad.ad.id', 'ad_id',
          'ad_group_ad.ad.name', 'ad_name',
          "ad_group_ad.status = 'ENABLED'"),
    Level('ad_group', 'ad_group.id', 'ad_group_id', 'ad_group.name',
          'ad_group_name', "ad_group.status = 'ENABLED'"),
    Level('campaign', 'campaign.id', 'campaign_id', 'campaign.name',
          'campaign_name', "campaign.status = 'ENABLED'"),
    Level('customer', 'customer.id', 'customer_id',
          'customer.descriptive_name', 'account_name',
          "customer.status = 'ENABLED'"),
    Level('customer', 'customer.id', 'customer_id',
          'customer.descriptive_name', 'account_name',
          "customer.status = 'ENABLED'"),
)


class Target:

    def __init__(self,
                 name: Optional[str] = None,
                 metrics: Optional[Union[str, List[Field]]] = None,
                 level: TargetLevel | None = TargetLevel.AD_GROUP,
                 resource_name: Optional[str] = None,
                 dimensions: Optional[Union[str, List[Field]]] = None,
                 filters: Optional[str] = None,
                 suffix: Optional[str] = None) -> None:
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
    def _init_fields(fields: Union[str, List[Field]],
                     prefix: str = '') -> List[Field]:
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
        if self.level.value == 0:
            return ''
        level = LEVELS[self.level.value]
        return (f'{level.id} AS '
                f'{level.id_alias},\n')

    def _get_table(self):
        table = LEVELS[self.level.value].table if self.level.value != 0 else ''
        return self.resource_name or table.lower()

    def _get_filters(self):
        return self.filters if self.filters else 'segments.date DURING TODAY'

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
            metrics = ',\n'.join(
                [field.to_query_field() for field in select_fields])
        select_fields.clear()

        for field in self.dimensions:
            if field not in dedup:
                # should not add a name-only field with the same name as what
                # the level defines.
                if (not field.alias and not field.customizer
                        and self.level != 0
                        and field.name == LEVELS[self.level.value].id):
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
                f'FROM {self._get_table()}\n'
                f'WHERE {self._get_filters()}')

    @staticmethod
    def to_comparable_str(val: Optional[Union[str, List[Field]]]) -> str:
        if not val:
            return ''
        if isinstance(val, str):
            return util.remove_spaces(val)
        elif isinstance(val, List):
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


def create_default_service_target(level: TargetLevel):
    dimensions = []
    filters = ''

    current_level = level.value - 1 if level == TargetLevel.MCC else level.value
    while 0 < current_level <= TargetLevel.CUSTOMER.value:
        level_def = LEVELS[current_level]
        dimensions.append(Field(name=level_def.id, alias=level_def.id_alias))
        dimensions.append(
            Field(name=level_def.name, alias=level_def.name_alias))

        if filters:
            filters = filters + ' AND ' + level_def.filter
        else:
            filters = level_def.filter

        current_level += 1

    return ServiceTarget(name='mapping',
                         metrics=[Field(name='1', alias='info')],
                         dimensions=dimensions,
                         level=level,
                         filters=filters)


def targets_similarity_check(targets: List[Target]) -> List[Target]:
    cloned_targets = copy.deepcopy(targets)
    combinations = itertools.combinations(targets, 2)
    for target1, target2 in combinations:
        if target1.is_similar(target2):
            max_target = max(target1, target2)
            if max_target in cloned_targets:
                cloned_targets.remove(max_target)
    return cloned_targets
