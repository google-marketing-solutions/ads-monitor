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
