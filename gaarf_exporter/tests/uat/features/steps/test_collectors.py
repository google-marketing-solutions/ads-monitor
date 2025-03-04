# Copyright 2024 Google LLC
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

import behave

from gaarf_exporter import registry


class TestCollector:
  @behave.given('collector registry is initialized')
  def init_registry(ctx):
    ctx.registry = registry.Registry.from_collector_definitions()

  @behave.when("I don't specify collectors")
  def get_default_collectors(ctx):
    ctx.collector_set = registry.initialize_collectors(
      collector_names='default'
    )

  @behave.then('default collectors are returned')
  def check_default_collector_set(ctx):
    assert {
      'performance',
      'conversion_action',
      'mapping',
    } == {c.name for c in ctx.collector_set}

  @behave.when('I specify performance collector')
  def get_performance_collector(ctx):
    ctx.collector_set = registry.initialize_collectors(
      collector_names='performance'
    )

  @behave.then('performance collector is returned')
  def performance_collector(ctx):
    assert 'performance' in {c.name for c in ctx.collector_set}

  @behave.when('I specify search subregistry')
  def get_search_subregistry(ctx):
    ctx.collector_set = registry.initialize_collectors(collector_names='search')

  @behave.then('all collectors from search subregistry returned')
  def search_subregistry_collectors(ctx):
    assert {
      'keywords',
      'search_terms',
      'keyword_quality_score',
      'click_share',
      'mapping',
    } == {c.name for c in ctx.collector_set}

  @behave.when('I specify performance and keywords collector')
  def get_performance_keywords_collectors(ctx):
    ctx.collector_set = registry.initialize_collectors(
      collector_names='performance,keywords'
    )

  @behave.then('performance, keywords and mapping collectors are returned')
  def performance_search_and_default_mapping_collectors(ctx):
    assert {'performance', 'mapping', 'keywords'} == {
      c.name for c in ctx.collector_set
    }

  @behave.when('I specify default registry and keywords collector')
  def get_default_registry_default_collector(ctx):
    ctx.collector_set = registry.initialize_collectors(
      collector_names='default,keywords'
    )

  @behave.then(
    'performance, mapping, keywords, '
    'conversion_action collectors are returned'
  )
  def collector_from_default_registry_and_keywords(ctx):
    assert {
      'performance',
      'conversion_action',
      'mapping',
      'keywords',
    } == {c.name for c in ctx.collector_set}

  @behave.when('I specify default registry and performance collector')
  def get_default_registry_performance_collector(ctx):
    ctx.collector_set = registry.initialize_collectors(
      collector_names='default,performance'
    )

  @behave.then(
    'performance, mapping, conversion_action collectors are returned'
  )
  def collector_from_default_registry_returned(ctx):
    assert {
      'performance',
      'conversion_action',
      'mapping',
    } == {c.name for c in ctx.collector_set}
