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

from typing import Dict, List, Optional, Type, Set

from .collectors import BaseCollector
from .target import Target


def get_targets(
        collector_sets: Dict[str, Dict[str, Type[BaseCollector]]],
        collector_names: Optional[Set[str]] = None) -> Optional[List[Target]]:
    collector_dict = {}
    if not collector_names:
        return None

    for name in collector_names:
        if name in collector_sets:
            for collector_name in collector_sets[name]:
                if collector_name not in collector_dict:
                    collector = collector_sets[name][collector_name]
                    collector_dict[collector.name] = collector().target
        else:
            for registered_collectors in collector_sets.values():
                if name in registered_collectors:
                    if name not in collector_dict:
                        collector = registered_collectors[name]
                        collector_dict[collector.name] = collector().target
    return list(collector_dict.values())
