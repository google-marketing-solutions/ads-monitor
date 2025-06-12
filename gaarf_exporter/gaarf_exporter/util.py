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


def tokenize(expression: str) -> list[tuple[str, str | None]]:
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
