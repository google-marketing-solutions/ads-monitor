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
'''Module for defining gaarf GaarfExporter config to hold queries.'''
from __future__ import annotations

import functools
from collections.abc import Sequence

import yaml

from gaarf_exporter import target


class Config:
  """Holds all regular and service targets to be converted to API requests.

  Attributes:
    targets: All targets for the config.
    regular_targets: All targets that fetching states or performance.
    queries: Query texts and suffixes from regular targets.
    service_targets: All targets that fetching mapping of entities.
    service_queries: Query texts and suffixes from regular targets.
    lowest_target_level: Lowest level (AD_GROUP, CAMPAIGN, etc.) of all targets.
  """

  def __init__(self, targets: Sequence[target.Target]) -> None:
    """Initializes Config from targets."""
    self._targets = list(targets)

  @functools.cached_property
  def targets(self):
    """Converts targets passed during init to regular and service targets."""
    targets = target.targets_similarity_check(self._targets)
    has_service_target = any(
        [isinstance(target_, target.ServiceTarget) for target_ in targets])
    if not has_service_target:
      min_level = target.TargetLevel(
          min([target_.level.value for target_ in targets]))
      default_service_target = target.create_default_service_target(min_level)
      targets.append(default_service_target)
    return targets

  @property
  def regular_targets(self) -> dict[str, target.Target]:
    """Mapping between name of non-service target to itself."""
    return {
        target_.name: target_
        for target_ in self.targets
        if not isinstance(target_, target.ServiceTarget)
    }

  @property
  def queries(self) -> dict[str, dict[str, str]]:
    """Mapping between regular target name to its text and suffix."""
    return {
        name: {
            'query': target_.query,
            'suffix': target_.suffix
        } for name, target_ in self.regular_targets.items()
    }

  @property
  def service_targets(self) -> dict[str, target.Target]:
    """Mapping between name of service target to itself."""
    return {
        target_.name: target_
        for target_ in self.targets
        if isinstance(target_, target.ServiceTarget)
    }

  @property
  def service_queries(self) -> dict[str, dict[str, str]]:
    """Mapping between service target name to its text."""
    return {
        name: {
            'query': target_.query
        } for name, target_ in self.service_targets.items()
    }

  @property
  def lowest_target_level(self):
    """Lowest level (AD_GROUP, CAMPAIGN, etc.) of all targets."""
    return target.TargetLevel(
        min([target_.level.value for target_ in self.targets]))

  def save(self, path: str) -> None:
    """Saves target to yaml.

    Args:
      path: Local path to save config to.
    """
    all_queries = dict(self.queries)
    all_queries.update(self.service_queries)
    config_yaml = yaml.safe_dump({
        'queries': all_queries,
    })
    with open(path, 'w', encoding='utf-8') as file_handle:
      file_handle.write(config_yaml)
