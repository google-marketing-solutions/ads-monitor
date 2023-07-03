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

import pytest

from gaarf_exporter.query_elements import Customizer, CustomizerTypeEnum, Field


@pytest.mark.parametrize('customizer_1,customizer_2,expected',
                         [(Customizer(CustomizerTypeEnum.INDEX, '0'),
                           Customizer(CustomizerTypeEnum.INDEX, '0'), True),
                          (Customizer(CustomizerTypeEnum.INDEX, '1'),
                           Customizer(CustomizerTypeEnum.INDEX, '0'), False),
                          (Customizer(CustomizerTypeEnum.NESTED_RESOURCE, '0'),
                           Customizer(CustomizerTypeEnum.INDEX, '0'), False),
                          (Customizer(CustomizerTypeEnum.INDEX, '0'),
                           Customizer(CustomizerTypeEnum.NESTED_RESOURCE,
                                      'target_cpa_micros'), False)])
def test_customizer_equality(customizer_1, customizer_2, expected):
    actual_equality = customizer_1 == customizer_2
    actual_hash_equality = hash(customizer_1) == hash(customizer_2)
    assert actual_equality == expected
    assert actual_hash_equality == expected


@pytest.mark.parametrize(
    'field_1,field_2,expected',
    [(Field(name='clicks / impressions',
            alias='ctr'), Field(name='clicks/impressions', alias='ctr'), True),
     (Field(name='impressions/clicks', alias='ctr'),
      Field(name='clicks/impressions', alias='ctr'), False),
     (Field(name='conversions',
            alias='ctr',
            customizer=Customizer(CustomizerTypeEnum.INDEX, '0')),
      Field(name='conversions',
            alias='ctr',
            customizer=Customizer(CustomizerTypeEnum.INDEX, '0')), True)])
def test_field_equality(field_1, field_2, expected):
    actual_equality = field_1 == field_2
    actual_hash_equality = hash(field_1) == hash(field_2)
    assert actual_equality == expected
    assert actual_hash_equality == expected


@pytest.mark.parametrize('field_1,field_2,expected', [
    (Field(name='clicks',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')),
     Field(name='impressions',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')), 'less'),
    (Field(name='impressions',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')),
     Field(name='impressions',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')), 'equal'),
    (Field(name='impressions',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')),
     Field(name='clicks',
           alias='ctr',
           customizer=Customizer(CustomizerTypeEnum.INDEX, '0')), 'greater'),
])
def test_field_order(field_1, field_2, expected):

    def compare(field_1, field_2):
        if field_1 == field_2:
            return 'equal'
        if field_1 > field_2:
            return 'greater'
        if field_1 < field_2:
            return 'less'

    actual = compare(field_1, field_2)
    assert actual == expected
