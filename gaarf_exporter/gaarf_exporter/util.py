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
"""Module for defining various helpers."""

from __future__ import annotations

import re

_TOKEN_PATTERNS = (
  r'(?i)(?P<INDEX>~\d+)'
  r'|(?P<NESTED_RESOURCE>:(\w+\.)+\w+)'
  r'|(?P<STRING>".*?")'
  r'|(?P<SEPARATOR>,)'
  r'|(?P<KEYWORD_AS>AS)'
  r'|(?P<KEYWORD_FROM>FROM)'
  r'|(?P<KEYWORD>SELECT|WHERE|DURING|TODAY|AND|OR|NOT)'
  r'|(?P<NUMBER>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)'
  r'|(?P<PREFIXED_IDENTIFIER>(\w+\.)+\w+)'
  r'|(?P<IDENTIFIER>\w+)'
  r'|(?P<MATH_OPERATOR>((\>\=)|(\<\=))|([\+\-\*/\(\)\=\>\<]))'
)

_RELATIVE_METRIC_PATTERNS = r'(?i)average_|_cpm|ctr|_percentage|_rate|_share'


def remove_spaces(s) -> str:
  return re.sub(r'\s+', '', s)


def tokenize(expression) -> list[tuple[str, str | None]]:
  tokens = []
  prev_token_type = None
  for match in re.finditer(_TOKEN_PATTERNS, expression):
    token_type = match.lastgroup
    token_value = match.group()
    tokens.append(
      (token_value, 'ALIAS' if prev_token_type == 'KEYWORD_AS' else token_type)
    )
    prev_token_type = token_type
  return tokens


def find_relative_metrics(query) -> list[str]:
  result = set()
  raw_tokens = tokenize(query)
  for token_value, token_type in raw_tokens:
    if token_type == 'KEYWORD_FROM':
      break

    if token_type in ('IDENTIFIER', 'PREFIXED_IDENTIFIER'):
      metric_name = token_value.split('.')[-1]
      if re.search(_RELATIVE_METRIC_PATTERNS, metric_name):
        result.add(metric_name)
  return list(result)
