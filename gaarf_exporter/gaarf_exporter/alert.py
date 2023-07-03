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

from typing import Optional
import yaml

from .alert_elements import AlertRule
from .target import Target


class Alert:

    def __init__(self,
                 name: str,
                 alert_rule: AlertRule,
                 labels: Optional[str] = None,
                 duration: str = '1h',
                 target: Optional[Target] = None) -> None:
        self.name = name
        self.alert_rule = str(alert_rule)
        self.labels = labels
        self.duration = duration
        self.target = target

    @property
    def text(self):
        d = {
            'alert': self.name,
            'expr': self.alert_rule,
            'for': self.duration
        }
        return yaml.safe_dump(d)
