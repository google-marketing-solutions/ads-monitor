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
from __future__ import annotations

import pytest

from gaarf_exporter import util


@pytest.mark.parametrize(
  'expression, expected',
  [
    (
      'clicks',
      [
        ('clicks', 'IDENTIFIER'),
      ],
    ),
    (
      'metrics.clicks',
      [
        ('metrics.clicks', 'PREFIXED_IDENTIFIER'),
      ],
    ),
    (
      'prefix_1.metrics.clicks',
      [
        ('prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER'),
      ],
    ),
    (
      'prefix_2.prefix_1.metrics.clicks',
      [
        ('prefix_2.prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER'),
      ],
    ),
    (
      '(prefix_1.metrics.clicks + var1)/20',
      [
        ('(', 'MATH_OPERATOR'),
        ('prefix_1.metrics.clicks', 'PREFIXED_IDENTIFIER'),
        ('+', 'MATH_OPERATOR'),
        ('var1', 'IDENTIFIER'),
        (')', 'MATH_OPERATOR'),
        ('/', 'MATH_OPERATOR'),
        ('20', 'NUMBER'),
      ],
    ),
  ],
)
def test_tokenize_return_correct_expression(expression, expected):
  actual = util.tokenize(expression)
  assert actual == expected
