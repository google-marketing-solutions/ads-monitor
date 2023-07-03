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

from typing import Sequence
import yaml

from .target import Target, TargetLevel, ServiceTarget, create_default_service_target


class Config:

    def __init__(self, targets: Sequence[Target]) -> None:
        self.targets = list(targets)

    @property
    def queries(self):
        return {target.name: {
            'query': target.query} for target in self.targets if not isinstance(
                target, ServiceTarget)}

    @property
    def service_queries(self):
        return {target.name: {
            'query': target.query} for target in self.targets if isinstance(
                target, ServiceTarget)
        }

    @property
    def service_targets(self):
        return {target.name: target for target in self.targets if isinstance(
            target, ServiceTarget)
        }

    @property
    def lowest_target_level(self):
        return TargetLevel(min([target.level.value for target in self.targets]))

    @classmethod
    def from_targets(cls, targets: Sequence[Target]):
        has_service_target = any(
            [isinstance(target, ServiceTarget) for target in targets])
        if not has_service_target:
            min_level = TargetLevel(min(
                [target.level.value for target in targets]))
            default_service_target = create_default_service_target(min_level)
            targets = list(targets)
            targets.append(default_service_target)
        return cls(targets)

    def save(self, path):
        all_queries = dict(self.queries)
        all_queries.update(self.service_queries)
        config_yaml = yaml.safe_dump({'queries': all_queries})
        with open(path, 'w') as file_handle:
            file_handle.write(config_yaml)
