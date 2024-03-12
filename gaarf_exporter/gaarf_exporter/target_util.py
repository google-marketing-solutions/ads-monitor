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
'''Module for various utils functions related to Target.'''
from __future__ import annotations

from typing import Type

from gaarf_exporter.collectors import BaseCollector
from gaarf_exporter.target import Target


def get_targets(collector_sets: dict[str, dict[str, Type[BaseCollector]]],
                collector_names: set[str] | None = None,
                kwargs: dict[str, str] = {}) -> list[Target] | None:
  collector_dict = {}
  if not collector_names:
    return None

  for name in collector_names:
    if name in collector_sets:
      for collector_name in collector_sets[name]:
        if collector_name not in collector_dict:
          collector = collector_sets[name][collector_name]
          collector_dict[collector.name] = collector(**kwargs).target
    else:
      for registered_collectors in collector_sets.values():
        if name in registered_collectors:
          if name not in collector_dict:
            collector = registered_collectors[name]
            collector_dict[collector.name] = collector(**kwargs).target
  return list(collector_dict.values())
