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

from gaarf_exporter import util


EQUALS_SIGN_SEPARATOR = ['--collectors=performance,mapping']
SPACE_SEPARATOR = ['--collectors', 'mapping', 'disapproval,conversion']
OTHER_ARG = ['--other_arg_1', 'other_val_1', 'other_val_2,other_val_3',
             '--other_arg_2=other_val_4,other_val_5', 'other_arg_0',
             '--other_arg_3']


def test_parse_args_equals_sign_separator():
    actual = util.parse_other_args(EQUALS_SIGN_SEPARATOR)
    expected = {
        'collectors': {'performance', 'mapping'}
    }
    assert actual == expected


def test_parse_args_space_separator():
    actual = util.parse_other_args(SPACE_SEPARATOR)
    expected = {
        'collectors': {'mapping', 'disapproval', 'conversion'}
    }
    assert actual == expected


def test_parse_args_mixed():
    test_input = list(EQUALS_SIGN_SEPARATOR)
    test_input.extend(SPACE_SEPARATOR)
    actual = util.parse_other_args(test_input)
    expected = {
        'collectors': {'performance', 'mapping', 'disapproval', 'conversion'}
    }
    assert actual == expected


def test_parse_args_multiple_args():
    test_input = list(EQUALS_SIGN_SEPARATOR)
    test_input.extend(SPACE_SEPARATOR)
    test_input.extend(OTHER_ARG)
    actual = util.parse_other_args(test_input)
    expected = {
        'collectors': {'performance', 'mapping', 'disapproval', 'conversion'},
        'other_arg_1': {'other_val_1', 'other_val_2', 'other_val_3'},
        'other_arg_2': {'other_val_4', 'other_val_5'},
        'other_arg_3': set()
    }
    assert actual == expected


@pytest.mark.parametrize(
    'expression, expected',
    [
        ('clicks',
         [('clicks', 'IDENTIFIER')]),
        ('metrics.clicks',
         [('metrics.clicks', 'PREFIXED_IDENTIFIER')]),
        ('prefix_1.metrics.clicks',
         [('prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER')]),
        ('prefix_2.prefix_1.metrics.clicks',
         [('prefix_2.prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER')]),
        ('(prefix_1.metrics.clicks + var1)/20',
         [
             ('(', 'MATH_OPERATOR'),
             ('prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER'),
             ('+', 'MATH_OPERATOR'),
             ('var1', 'IDENTIFIER'),
             (')', 'MATH_OPERATOR'),
             ('/', 'MATH_OPERATOR'),
             ('20', 'NUMBER')
         ])
    ]
)
def test_tokenize_expression(expression, expected):
    actual = util.tokenize(expression)
    assert actual == expected


@pytest.mark.parametrize(
    'query,expected',
    [
        (
            """
              SeLeCt
                  average_cost
                  metrics.active_view_cpm as cpm
                  metrics.metrics.active_view_ctr As ctr,
                  metrics.absolute_top_impression_percentage~0 as p,
                  metrics.all_conversions_from_interactions_rate:prefix.field aS rate,
                  (metrics.auction_insight_search_impression_share + 100) / 1e6 AS share
              from campaign
              WHERE
                  segments.date DURING TODAY
                  AND campaign.status = "ENABLED"
                  AND ad_group.status = "ENABLED"
                  AND metrics.cost_micros >= 0
            """,
            ['absolute_top_impression_percentage', 'active_view_cpm',
             'active_view_ctr', 'all_conversions_from_interactions_rate',
             'auction_insight_search_impression_share','average_cost']
        )
    ]
)
def test_find_relative_metrics(query, expected):
    actual = util.find_relative_metrics(query)
    assert sorted(actual) == expected
