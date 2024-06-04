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
"""Module for building Prometheus alert."""

from __future__ import annotations

import yaml

from gaarf_exporter.alert_elements import AlertRule


class Alert:
  def __init__(
    self,
    name: str,
    alert_rule: AlertRule,
    labels: str | None = None,
    duration: str = '1h',
  ) -> None:
    self.name = name
    self.alert_rule = str(alert_rule)
    self.labels = labels
    self.duration = duration

  @property
  def text(self) -> dict[str, str]:
    d = {'alert': self.name, 'expr': self.alert_rule, 'for': self.duration}
    return yaml.safe_dump(d)
