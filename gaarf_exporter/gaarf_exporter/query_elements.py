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
'''Module for defining classes helping with constructing Gaarf query.'''
from __future__ import annotations

from gaarf_exporter import util


class Field:
  """Helper class for defining Google Ads API field.

  Field can be a metric, dimension or segment.

  Attributes:
      name: Name of the field, i.e. metric.clicks.
      alias: Optional alias for the field, i.e. clicks.
  """

  def __init__(self, name: str, alias: str | None = None) -> None:
    """Initializes Field.

    Args:
      name: Name of the field, i.e. metric.clicks.
      alias: Optional alias for the field, i.e. clicks.
    """
    self.name = name
    self.alias = alias or name.replace('.', '_')

  def to_query_field(self) -> str:
    """Converts Field to format 'name AS alias'."""
    return f'{self.name} AS {self.alias}' if self.alias else self.name

  def __str__(self) -> str:
    return self.to_query_field()

  def __repr__(self) -> str:
    return f'Field(name={self.name}, alias={self.alias})'

  def __eq__(self, other: Field) -> bool:
    if not other or not isinstance(other, Field):
      return False
    return util.remove_spaces(str(self)) == util.remove_spaces(str(other))

  def __lt__(self, other: Field) -> bool:
    return util.remove_spaces(str(self)) < util.remove_spaces(str(other))

  def __gt__(self, other: Field) -> bool:
    return util.remove_spaces(str(self)) > util.remove_spaces(str(other))

  def __hash__(self):
    return hash((util.remove_spaces(self.name),
                 util.remove_spaces(self.alias if self.alias else '')))
