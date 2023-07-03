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

from typing import List, Optional, Union, Sequence
from enum import Enum, auto

from . import util


class CustomizerTypeEnum(Enum):
    INDEX = auto()
    NESTED_RESOURCE = auto()


class Customizer:

    def __init__(self, customizer_type: CustomizerTypeEnum,
                 value: str) -> None:
        self.type = customizer_type
        self.value = value

    def to_raw_string(self):
        if self.type == CustomizerTypeEnum.INDEX:
            return f'~{self.value}'
        if self.type == CustomizerTypeEnum.NESTED_RESOURCE:
            return f':{self.value}'

    def __str__(self):
        return self.to_raw_string()

    def __repr__(self):
        return f'Customizer(type={self.type}, value={self.value})'

    def __eq__(self, other):
        if not other or not isinstance(other, Customizer):
            return False
        return self.type == other.type and self.value == other.value

    def __hash__(self):
        return hash((self.type, self.value))


class Field:

    def __init__(self,
                 name: str,
                 alias: Optional[str] = None,
                 customizer: Optional[Customizer] = None) -> None:
        self.name = name
        self.alias = alias
        self.customizer = customizer

    def to_query_field(self) -> str:
        name = self.name

        if self.customizer:
            name = f'{name}{self.customizer.to_raw_string()}'

        return f'{name} AS {self.alias}' if self.alias else name

    def __str__(self):
        return self.to_query_field()

    def __repr__(self):
        return f'Field(name={self.name}, alias={self.alias})'

    def __eq__(self, other):
        if not other or not isinstance(other, Field):
            return False
        return util.remove_spaces(str(self)) == util.remove_spaces(str(other))

    def __lt__(self, other):
        return util.remove_spaces(str(self)) < util.remove_spaces(str(other))

    def __gt__(self, other):
        return util.remove_spaces(str(self)) > util.remove_spaces(str(other))

    def __hash__(self):
        return hash(
            (util.remove_spaces(self.name),
             util.remove_spaces(self.alias if self.alias else ''),
             util.remove_spaces(str(self.customizer) if self.customizer else '')
             ))
