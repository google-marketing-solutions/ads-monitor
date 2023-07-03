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

class Label:

    def __init__(self, name: str, value: str, operator: str = "=") -> None:
        self.name = name
        self.value = value
        # TODO: Add support for regexp operators
        self.operator = operator

    def __str__(self) -> str:
        return f'{self.name}{self.operator}"{self.value}"'


class MetricDefinition:

    def __init__(self, metric, label: Label):
        self.metric = metric
        self.label = str(label)

    def __str__(self) -> str:
        return f'{self.metric}{{{self.label}}}'

    # TODO: implement
    @classmethod
    def from_raw_string(cls, raw_string):
        pass


class AlertRule:

    def __init__(
            self,
            metric_definition: MetricDefinition,
            aggregation_level: str = "campaign_id",  # Available from Target only
            offset: str = "30m",
            threshold: float = 2.0) -> None:
        self.metric_definition = str(metric_definition)
        self.aggregation_level = aggregation_level
        self.offset = offset
        self.threshold = threshold

    def __str__(self):
        text = f"""
        sum by({self.aggregation_level}) ({self.metric_definition})
        / sum by({self.aggregation_level}) ({self.metric_definition} offset {self.offset})
        > {self.threshold}
        """
        return text

