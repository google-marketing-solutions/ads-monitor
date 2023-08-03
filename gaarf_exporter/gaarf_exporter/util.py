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

import re
from typing import Dict, List

TOKEN_PATTERNS = [
    (r'~\d+', 'INDEX'),
    (r':(\w+\.)+\w+', 'NESTED_RESOURCE'),
    (r'".*?"', 'STRING'),
    (r',', 'SEPARATOR'),
    (r'(?i)AS', 'KEYWORD_AS'),
    (r'(?i)FROM', 'KEYWORD_FROM'),
    (r'(?i)SELECT|WHERE|DURING|TODAY|AND|OR|NOT', 'KEYWORD'),
    (r'\d+(?:\.\d+)?(?:[eE][+-]?\d+)?', 'NUMBER'),
    (r'(\w+\.)+\w+', 'PREFIXED_IDENTIFIER'),
    (r'\w+', 'IDENTIFIER'),
    (r'((\>\=)|(\<\=))|([\+\-\*/\(\)\=\>\<])', 'MATH_OPERATOR'),
]


RELATIVE_METRIC_PATTERNS = r'(?i)average|cpm|ctr|percentage|rate|share'


def parse_other_args(other_args: List[str]) -> Dict[str, set]:
    result = {}

    for i in range(len(other_args)):
        if other_args[i].startswith('--'):
            if '=' in other_args[i]:
                parts = other_args[i][2:].split('=')
                if len(parts) != 2:
                    continue
                name, raw_val = parts
                result.setdefault(name, set()).update(
                    list(filter(None, raw_val.split(','))))
            else:
                arg_name = other_args[i][2:]
                result.setdefault(arg_name, set())
                while (i + 1 < len(other_args) and
                       not other_args[i + 1].startswith('--')):
                    i += 1
                    result.setdefault(arg_name, set()).update(
                        list(filter(None, other_args[i].split(','))))

    return result


def remove_spaces(s):
    return re.sub(r'\s+', '', s)


def tokenize(expression):
    all_patterns = '|'.join(
        '(?P<%s>%s)' % (pair[1], pair[0]) for pair in TOKEN_PATTERNS)

    tokens = []
    prev_token_type = None
    for match in re.finditer(all_patterns, expression):
        token_type = match.lastgroup
        token_value = match.group()
        tokens.append(
            (token_value,
             'ALIAS' if prev_token_type == 'KEYWORD_AS' else token_type))
        prev_token_type = token_type

    return tokens


def find_relative_metrics(query):
    result = set()
    raw_tokens = tokenize(query)
    for token_value, token_type in raw_tokens:
        if token_type == 'KEYWORD_FROM':
            break

        if token_type in ('IDENTIFIER', 'PREFIXED_IDENTIFIER'):
            metric_name = token_value.split('.')[-1]
            if re.search(RELATIVE_METRIC_PATTERNS, metric_name):
                result.add(metric_name)
    return list(result)
