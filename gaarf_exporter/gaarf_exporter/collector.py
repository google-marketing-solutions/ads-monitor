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
"""Defines Collector class and corresponding helper methods.

Collector serves an important roles of building Google Ads queries from set of
diverse elements: metrics, dimensions, filters, resource names, etc.

Collector can be:
  * similar (sharing the same metrics, dimensions and filters) which allows
    to perform similar collector deduplication with the lowest common level.
  * equal (sharing the same attributes) - useful for checking collector presence
    in the sets.

Metrics, dimensions and filters of a Collector can be dynamically changed thus
allowing Collector customization at the runtime.
"""

from __future__ import annotations

import copy
import dataclasses
import enum
import itertools
from collections.abc import Mapping, MutableSequence, Sequence
from datetime import datetime
from typing import TypedDict

from gaarf.cli import utils as gaarf_utils

from gaarf_exporter import util


class QueryField(TypedDict):
  field: str


class QuerySpec(TypedDict):
  level: str | None
  metrics: list[str] | list[QueryField] | None
  dimensions: list[QueryField] | None
  resource_name: str | None
  customizable: list[str] | None
  filters: list[str] | None


class CollectorDefinition(TypedDict):
  name: str
  type: str | dict[str, str] | None
  query_spec: QuerySpec | None
  query: str | None
  has_conversion_split: str | None
  registries: list[str]


class CollectorCustomization(TypedDict):
  start_date: str
  end_date: str
  level: str
  metrics: list[str] | list[QueryField]
  dimensions: list[str] | list[QueryField]
  filters: list[str]


class Field:
  """Helper class for defining Google Ads API field.

  Field can be a metric, dimension or segment.

  Attributes:
      name: Name of the field, i.e. metric.clicks.
      alias: Optional alias for the field, i.e. clicks.
  """

  def __init__(self, name: str, alias: str | None = None) -> None:
    """Initializes Field.

    Args:
      name: Name of the field, i.e. metric.clicks.
      alias: Optional alias for the field, i.e. clicks.
    """
    self.name = name
    self.alias = alias or name.replace('.', '_')

  def to_query_field(self) -> str:
    """Converts Field to format 'name AS alias'."""
    return f'{self.name} AS {self.alias}' if self.alias else self.name

  def __str__(self) -> str:
    return self.to_query_field()

  def __repr__(self) -> str:
    return f'Field(name={self.name}, alias={self.alias})'

  def __eq__(self, other: Field) -> bool:
    if not other or not isinstance(other, Field):
      return False
    return util.remove_spaces(str(self)) == util.remove_spaces(str(other))

  def __lt__(self, other: Field) -> bool:
    return util.remove_spaces(str(self)) < util.remove_spaces(str(other))

  def __gt__(self, other: Field) -> bool:
    return util.remove_spaces(str(self)) > util.remove_spaces(str(other))

  def __hash__(self):
    return hash(
      (
        util.remove_spaces(self.name),
        util.remove_spaces(self.alias if self.alias else ''),
      )
    )


class CollectorLevel(enum.IntEnum):
  """Represents minimal level of entity.

  CollectorLevel regulates which entity id (ad_id, ad_group_id, campaign_id, etc.)
  is associated with metrics and dimensions for a given collector.
  Collector levels are ordered hierarchically to support comparison operations.
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
  """Stores meta information for a particular CollectorLevel.

  This meta information is used to correctly build query in the Collector.

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

  def to_field(self) -> Field:
    """Builds Field from level meta information."""
    return Field(name=self.id, alias=self.id_alias)


_LEVELS = {
  CollectorLevel.AD_GROUP_AD_ASSET: LevelInfo(
    'ad_group_ad_asset_view',
    'asset.id',
    'asset_id',
    'asset.name',
    'asset',
    'ad_group_ad_asset_view.enabled = TRUE',
  ),
  CollectorLevel.AD_GROUP_AD: LevelInfo(
    'ad_group_ad',
    'ad_group_ad.ad.id',
    'ad_id',
    'ad_group_ad.ad.name',
    'ad_name',
    'ad_group_ad.status = ENABLED',
  ),
  CollectorLevel.AD_GROUP: LevelInfo(
    'ad_group',
    'ad_group.id',
    'ad_group_id',
    'ad_group.name',
    'ad_group_name',
    'ad_group.status = ENABLED',
  ),
  CollectorLevel.CAMPAIGN: LevelInfo(
    'campaign',
    'campaign.id',
    'campaign_id',
    'campaign.name',
    'campaign_name',
    'campaign.status = ENABLED',
  ),
  CollectorLevel.CUSTOMER: LevelInfo(
    'customer',
    'customer.id',
    'customer_id',
    'customer.descriptive_name',
    'account_name',
    'customer.status = ENABLED',
  ),
  CollectorLevel.MCC: LevelInfo(
    'customer',
    'customer.id',
    'customer_id',
    'customer.descriptive_name',
    'account_name',
    'customer.status = ENABLED',
  ),
}


class Collector:
  """Represents collection of query elements needed to build a Google Ads query.

  Attributes:
    name: Unique identifier of a collector.
    level: Minimal entity level in the collector (ad_group, campaign, customer).
    metrics: All metrics (started with `metrics.`) associated with the collector.
    dimensions: All segments and resources associated with the collector.
    filters: Text conditions for limiting the query.
    resource_name: Name of resource to get data from (used in FROM statement).
    query: Full text of the query to be sent to Google Ads API.
    suffix: Optional custom identifier to the collector.
  """

  def __init__(
    self,
    name: str | None = None,
    metrics: str | list[Field] | None = None,
    level: CollectorLevel | None = CollectorLevel.AD_GROUP,
    resource_name: str | None = None,
    dimensions: str | list[Field] | None = None,
    filters: str | None = None,
    suffix: str | None = None,
    query: str | None = None,
  ) -> None:
    """Initializes Collector.

    Args:
      name: Unique identifier of a collector.
      metrics: All metrics (started with `metrics.`) associated with the collector.
      level: Minimal entity level in the collector (ad_group, campaign, customer).
      resource_name: Name of resource to get data from (used in FROM statement).
      dimensions: All segments and resources associated with the collector.
      filters: Text conditions for limiting the query.
      suffix: Optional custom identifier to the collector.
      query: Full query_text.
    """
    self.name = name
    self._level = level
    self._resource_name = resource_name
    self._filters = filters or set()
    self._metrics = self._init_fields(metrics, 'metrics')
    self._dimensions = self._init_fields(dimensions)
    self.suffix = suffix if suffix else name
    self._query = query

  @classmethod
  def from_definition(cls, definition: CollectorDefinition) -> Collector:
    """Creates Collector from a dictionary.

    Args:
      definition: Necessary data to create Collector.

    Returns:
      Initialized Collector.
    """
    if query := definition.get('query'):
      return cls(
        name=definition.get('name'),
        query=query,
        suffix=definition.get('suffix'),
      )
    query_spec = definition.get('query_spec', {})
    if definition.get('type') == 'service':
      metrics = [Field(name='1', alias='info')]
    elif service_alias := definition.get('type', {}).get('service'):
      metrics = [Field(name='1', alias=service_alias.get('alias'))]
    else:
      metrics = query_spec.get('metrics')

    if level_string := query_spec.get('level'):
      level = CollectorLevel[level_string.upper()]
    else:
      level = CollectorLevel.AD_GROUP
    return cls(
      name=definition.get('name'),
      suffix=definition.get('suffix'),
      metrics=metrics,
      dimensions=query_spec.get('dimensions'),
      filters=query_spec.get('filters'),
      resource_name=query_spec.get('resource_name'),
      level=level,
    )

  def create_conversion_split_collector(self) -> Collector:
    """Builds new Collector with conversions metric and dimensions.

    Returns:
        New Collector on the same level as the seed one.
    """
    return Collector(
      name=f'{self.name}_conversion_split',
      suffix=self.suffix,
      level=self.level,
      metrics='all_conversions,all_conversions_value',
      dimensions=[
        Field('segments.conversion_action_category', 'conversion_category'),
        Field('segments.conversion_action_name', 'conversion_name'),
        Field('segments.conversion_action~0', 'conversion_id'),
      ],
      resource_name=self.resource_name,
      filters='metrics.all_conversions > 0',
    )

  @property
  def level(self) -> CollectorLevel | None:
    """Represents entity level of a collector."""
    return self._level

  @level.setter
  def level(self, value: CollectorLevel) -> None:
    """Changes saved level of a collector."""
    self._level = value

  @property
  def metrics(self) -> set[Field]:
    """Returns unique metrics."""
    return self._metrics

  @metrics.setter
  def metrics(self, values: Sequence[Field]) -> None:
    """Changes saved metrics of a collector."""
    self._metrics = self._init_fields(values, 'metrics')

  @property
  def dimensions(self) -> set[Field]:
    """Returns unique metrics."""
    return self._dimensions

  @dimensions.setter
  def dimensions(self, values: Sequence[Field]) -> None:
    """Changes saved dimensions of a collector."""
    self._dimensions = self._init_fields(values)

  @property
  def filters(self) -> str:
    """Returns filters or default placeholder.

    If collector has any metric inject a placeholder filter to fetch data
    only for today.
    """
    if isinstance(self._filters, str):
      self._filters = set(self._filters.split(' AND '))
    else:
      self._filters = set(self._filters)
    if isinstance(self, ServiceCollector) or not self._metrics:
      return self._filters
    if not self._filters:
      self._filters.add('segments.date DURING TODAY')
    elif not any('segments.date' in _filter for _filter in self._filters):
      self._filters.add('segments.date DURING TODAY')
    return self._filters

  @filters.setter
  def filters(self, values: str) -> None:
    """Changes saved dimensions of a collector."""
    self._filters = values

  def _init_fields(
    self, fields: str | list[Field], prefix: str = ''
  ) -> set[Field]:
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
      return set()

    if isinstance(fields, str):
      field_list = [Field(name=field) for field in fields.split(',')]
    elif isinstance(fields, MutableSequence):
      field_list = []
      for field in fields:
        if isinstance(field, Field):
          element = field
        elif isinstance(field, Mapping):
          for alias, values in field.items():
            element = Field(name=values.get('field'), alias=alias)
        else:
          element = Field(name=field)
        field_list.append(element)
    else:
      field_list = fields

    if not prefix:
      return set(field_list)

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

    return set(field_list)

  @property
  def level_info(self) -> LevelInfo | None:
    """Returns meta information related to a collector level."""
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
      [field.to_query_field() for field in sorted(self.metrics)]
    )
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
      [field.to_query_field() for field in sorted(dimensions)]
    )
    return f'{dimensions_info},\n'

  @property
  def formatted_filters(self) -> str:
    """Returns formatted filters with WHERE statement."""
    if not self.filters:
      return ''
    filters = ' AND '.join(self.filters)
    return f'WHERE {filters}'

  @property
  def resource_name(self) -> str:
    """Gets resource_name or infers it from collector level."""
    if self._resource_name:
      return self._resource_name
    if level_info := self.level_info:
      return level_info.resource_name.lower()
    return self.level.name

  @property
  def query(self) -> str:
    """Formats query based on elements."""
    if self._query:
      return self._query
    return (
      f'SELECT {self.formatted_level}{self.formatted_metrics}'
      f'{self.formatted_dimensions}'
      f'FROM {self.resource_name}\n'
      f'{self.formatted_filters}'
    )

  def customize(self, collector_customization: CollectorCustomization) -> None:
    """Customizes collector elements based on provided customization mapping.

    Based on provided collector_customization mapping this method changes
    elements of Customizer instance (metrics, level, dimensions, filters).

    Args:
      collector_customization:
        Provides mapping between names of customized parameter and its updated
        values.
    """
    if level := collector_customization.get('level'):
      self.level = CollectorLevel[level.upper()]
    if (start_date := collector_customization.get('start_date')) and (
      end_date := collector_customization.get('end_date')
    ):
      start_date = gaarf_utils.convert_date(start_date)
      end_date = gaarf_utils.convert_date(end_date)
      if not self.filters or 'segments.date DURING TODAY' in self.filters:
        self.filters.add(
          f"segments.date BETWEEN '{start_date}' AND '{end_date}'"
        )
        self.filters.remove('segments.date DURING TODAY')
      n_days = (
        datetime.strptime(end_date, '%Y-%m-%d')
        - datetime.strptime(start_date, '%Y-%m-%d')
      ).days + 1
      self.dimensions.add(Field(str(n_days), 'n_days'))

  def is_similar(self, other: Collector) -> bool:
    """Compares similarity between two collectors.

    Similarity first checks whether two collectors are coming from different
    non CollectorLevel specific resouce_names, if they are different then
    collectors are not similar.
    Then is compares all  metrics, dimensions and filters between two collectors.

    Returns:
      Whether two collectors are similar.
    """
    if not other or not isinstance(other, Collector):
      return False

    if self.resource_name != other.resource_name and not (
      CollectorLevel.contains(self.resource_name, other.resource_name)
    ):
      return False
    if (self.metrics, self.dimensions, self.filters) == (
      other.metrics,
      other.dimensions,
      other.filters,
    ):
      return True
    return False

  def __eq__(self, other: Collector) -> bool:
    """Compares two collectors based on similarity, resource_name and level."""
    if not self.is_similar(other):
      return False
    if self.level != other.level:
      return False
    return True

  def __lt__(self, other: Collector) -> bool:
    """Compares collectors by level values."""
    if self.level.value < other.level.value:
      return True
    return False

  def __gt__(self, other: Collector) -> bool:
    """Compares collectors by level values."""
    if self.level.value > other.level.value:
      return True
    return False

  def __hash__(self):
    return hash(self.query)


class ServiceCollector(Collector):
  """Helper class for collectors without metrics."""

  @property
  def metrics(self) -> set[Field]:
    """Returns default info metric."""
    return self._metrics or {
      Field(name='1', alias='info'),
    }

  @metrics.setter
  def metrics(self, value: Field) -> None:
    """Ensures that metrics cannot be overwritten."""
    raise ValueError('Cannot change value of "metrics"!')


def create_default_service_collector(level: CollectorLevel) -> ServiceCollector:
  """Generates correct ServiceCollector based on provided level.

  Based on level (AD_GROUP, CAMPAIGN, ACCOUNT, etc.) corresponding
  ServiceCollector is created that contains all necessary mapping information
  downstream. I.e. if 'level=AD_GROUP' then information on ad_group, campaign
  and customer will be included in to the mapping.

  Returns:
   ServiceCollector called 'mapping' for an appropriate level.

  """
  if level == CollectorLevel.MCC:
    level = CollectorLevel.CUSTOMER
  dimensions = []
  filters = ''

  for collector_level in CollectorLevel:
    if (
      collector_level
      not in (CollectorLevel.MCC, CollectorLevel.AD_GROUP_AD_ASSET)
      and level <= collector_level
      and (level_info := _LEVELS.get(collector_level))
    ):
      dimensions.extend(
        [
          Field(name=level_info.id, alias=level_info.id_alias),
          Field(name=level_info.name, alias=level_info.name_alias),
        ]
      )
      if filters:
        filters = filters + ' AND ' + level_info.active_entities_filter
      else:
        filters = level_info.active_entities_filter

  return ServiceCollector(
    name='mapping', dimensions=dimensions, level=level, filters=filters
  )


def collectors_similarity_check(collectors: list[Collector]) -> list[Collector]:
  """Dedupicates collectors.

  If there are similar collector in the list return only those with the lowest
  level.

  Args:
    collectors: Possible collector values.

  Returns:
    Deduplicated collectors.
  """
  cloned_collectors = copy.deepcopy(collectors)
  combinations = itertools.combinations(collectors, 2)
  for collector1, collector2 in combinations:
    if collector1.is_similar(collector2):
      max_collector = max(collector1, collector2)
      if max_collector in cloned_collectors:
        cloned_collectors.remove(max_collector)
  return cloned_collectors
