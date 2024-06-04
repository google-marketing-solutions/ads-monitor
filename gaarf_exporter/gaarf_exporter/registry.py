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

import itertools
import logging
import os
import pathlib
from collections import defaultdict
from collections.abc import MutableSet

import yaml

from gaarf_exporter import collector as query_collector

_SCRIPT_DIR = pathlib.Path(__file__).parent


class Registry:
  """Maps collector names to corresponding classes.

  Registry simplifies searching for collectors.

  Attributes:
    collectors: Mapping between collector names and corresponding class.
  """

  def __init__(self, collectors: dict | None = None) -> None:
    """Creates Registry based on module level variable _REGISTRY."""
    self.collectors = dict(collectors) or dict()

  @classmethod
  def from_collector_definitions(
    cls,
    path_to_definitions: str
    | os.Pathlike = f'{_SCRIPT_DIR}/collector_definitions/',
  ) -> Registry:
    """Builds Registry from one or multiple definitions.

    Args:
      path_to_definition: Path to file / folder with collector definitions.

    Returns:
      Initialized collector registry.
    """
    collectors: dict = defaultdict(dict)
    results = _load_collector_data(path_to_definitions)
    for data in results:
      for collector_data in data:
        if collector_data.get('type') == 'service' or collector_data.get(
          'type', {}
        ).get('service'):
          coll = query_collector.ServiceCollector.from_definition(
            collector_data
          )
        else:
          coll = query_collector.Collector.from_definition(collector_data)
        collectors[coll.name] = coll
        if subregistries := collector_data.get('registries'):
          for subregistry in subregistries:
            collectors[subregistry].update({coll.name: coll})
        if 'has_conversion_split' in collector_data:
          conv_coll = coll.create_conversion_split_collector()
          collectors[conv_coll.name] = conv_coll
    return cls(collectors)

  @property
  def default_collectors(self) -> CollectorSet:
    """Helper for getting only default collectors from the registry."""
    return CollectorSet(collectors=set(self.collectors.get('default').values()))

  @property
  def all_subregistries(self) -> CollectorSet:
    """Helper for getting only sub-registries."""
    collector_names = set()
    for name, collector in self.collectors.items():
      if isinstance(collector, dict):
        collector_names.add(name)
    subregistries_collector_names = ','.join(collector_names)
    return self.find_collectors(collector_names=subregistries_collector_names)

  @property
  def all_collectors(self) -> CollectorSet:
    """Helper for getting all collectors from the registry."""
    all_collector_names = ','.join(self.collectors.keys())
    return self.find_collectors(
      collector_names=all_collector_names,
      deduplicate=False,
      service_collectors=False,
    )

  def find_collectors(
    self,
    collector_names: str | None = None,
    service_collectors: bool = True,
    deduplicate: bool = True,
  ) -> CollectorSet:
    """Extracts collectors from registry and returns their initialized targets.

    Args:
      collector_names:
        Names of collectors that need to be fetched from registry.
      service_collectors:
        Whether to generate default service collector for the set.
      deduplicate: Whether to perform deduplication of collectors.

    Returns:
      Found collectors.
    """
    if not collector_names:
      return CollectorSet()
    if collector_names == 'all':
      return self.all_collectors
    collectors_subset = [
      collector
      for name, collector in self.collectors.items()
      if name in collector_names.strip().split(',')
    ]
    found_collectors = set()
    for collector in collectors_subset:
      if isinstance(collector, dict):
        for collector_ in collector.values():
          found_collectors.add(collector_)
      else:
        found_collectors.add(collector)
    return CollectorSet(
      collectors=set(found_collectors),
      deduplicate=deduplicate,
      service_collectors=service_collectors,
    )


class CollectorSet(MutableSet):
  """Represent a set of collectors returned from Registry."""

  def __init__(
    self,
    collectors: set[query_collector.Collector] | None = None,
    service_collectors: bool = True,
    deduplicate: bool = True,
  ) -> None:
    """Initializes CollectorSet based on provided collectors.

    Args:
      collectors:
        Collectors to add to the set.
      service_collectors:
        Whether to generate default service collector for the set.
      deduplicate:
        Whether to perform deduplication of collectors in the set.
    """
    self._collectors = collectors or set()
    self._service_collectors = service_collectors
    self._deduplicate = deduplicate

  @property
  def collectors(self) -> set[query_collector.Collector]:
    """Returns deduplicated collectors with default service collector.

    Collectors in CollectorSet can be similar (same metrics, dimensions, etc.)
    but have different levels (i.e. ad_group and campaign). Getting the same
    data twice is wasteful so we leave only collectors with the lowest level.
    If needed the default service collector is generated at the lowest level
    (i.e. ad_group) to ensure proper mapping between ids and names of entities.
    """
    if self._deduplicate:
      self.deduplicate_collectors()
    if self._service_collectors:
      has_service_collector = any(
        [
          isinstance(collector, query_collector.ServiceCollector)
          for collector in self._collectors
        ]
      )
      if not has_service_collector:
        valid_collector_levels = [
          collector.level
          for collector in self._collectors
          if collector.level != query_collector.CollectorLevel.UNKNOWN
        ]
        if valid_collector_levels:
          default_service_collector = (
            query_collector.create_default_service_collector(
              min(valid_collector_levels)
            )
          )
          self._collectors.add(default_service_collector)

    return self._collectors

  def deduplicate_collectors(self) -> None:
    """Deduplicates collectors in the set.

    If there are similar collectors in the list return only those with
    the lowest level.
    """
    combinations = itertools.combinations(self._collectors, 2)
    for collector_1, collector_2 in combinations:
      if collector_1.is_similar(collector_2):
        max_collector = max(collector_1, collector_2)
        self._collectors.remove(max_collector)

  def customize(
    self, collector_customization: query_collector.CollectorCustomization
  ) -> None:
    """Changes collectors in the set based on provided arguments mapping.

    Args:
      collector_customization:
        Mapping between name and values of elements in collector to be
        customized.
    """
    for collector in self.collectors:
      collector.customize(collector_customization)

  def __bool__(self):
    return bool(self.collectors)

  def __eq__(self, other) -> bool:
    return self.collectors == other.collectors

  def __contains__(self, key: query_collector.Collector) -> bool:
    return key in self.collectors

  def __iter__(self):
    return iter(self.collectors)

  def __len__(self) -> int:
    return len(self.collectors)

  def add(self, collector) -> None:
    self._collectors.add(collector)

  def discard(self, collector) -> None:
    self._collectors.discard(collector)


def initialize_collectors(
  config_file: str | None = None,
  collector_names: str | None = None,
  create_service_collectors: bool = True,
  deduplicate_collectors: bool = True,
) -> CollectorSet():
  """Initializes collectors either from file or CLI.

  Args:
    config_file: Path to file with collector definitions.
    collector_names: Comma-separated string with collector names.

  Returns:
    All found collectors.

  Raises:
    ValueError: When neither collector_file nor collector_names were provided.
  """
  if config_file:
    collectors_registry = Registry.from_collector_definitions(config_file)
    return collectors_registry.find_collectors(
      collector_names='all', deduplicate=False, service_collectors=False
    )
  if collector_names:
    collectors_registry = Registry.from_collector_definitions()
    if not (
      active_collectors := collectors_registry.find_collectors(
        collector_names,
        deduplicate=deduplicate_collectors,
        service_collectors=create_service_collectors,
      )
    ):
      logging.warning(
        'Failed to get "%s" collectors, using default ones', collector_names
      )
      active_collectors = collectors_registry.default_collectors
  return active_collectors
  raise ValueError('Neither collector_file nor collector_names were provided')


def _load_collector_data(
  path_to_definitions: str | os.Pathlike,
) -> list[query_collector.CollectorDefinition]:
  """Loads collectors data from file or folder.

  Args:
    path_to_definition: Local path to file / folder with collector definitions.
  Returns:
    Loaded collector definitions.
  """
  if isinstance(path_to_definitions, str):
    path_to_definitions = pathlib.Path(path_to_definitions)
  results = []
  if path_to_definitions.is_file():
    with open(path_to_definitions, 'r', encoding='utf-8') as f:
      results.append(yaml.safe_load(f))
  else:
    for file in path_to_definitions.iterdir():
      if file.suffix == '.yaml':
        with open(file, 'r', encoding='utf-8') as f:
          results.append(yaml.safe_load(f))
  return results
