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

from gaarf_exporter.collectors import registry
from gaarf_exporter.target_util import get_targets


def test_get_targets_with_multiple_counters():
    actual = get_targets(registry, {'performance', 'mapping'})
    expected = ['mapping', 'performance']
    assert sorted([target.name for target in actual]) == expected


def test_get_targets_with_single_counter_set():
    actual = get_targets(registry, {'default'})
    expected = ['conversion_action', 'disapproval', 'mapping', 'performance']
    assert sorted([target.name for target in actual]) == expected


def test_get_targets_with_counters_and_counter_set():
    actual = get_targets(registry, {'default', 'performance', 'mapping'})
    expected = ['conversion_action', 'disapproval', 'mapping', 'performance']
    assert sorted([target.name for target in actual]) == expected
