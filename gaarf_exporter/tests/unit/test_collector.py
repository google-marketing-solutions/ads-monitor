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

import re

import pytest

from gaarf_exporter import collector as query_collector


def tokenize_sql(sql: str) -> list[str]:
  return list(filter(None, re.split(r'[\r\n\s]+', sql)))


# TODO: Ignores commas which are crucial
def assert_sql_functionally_equivalent(actual_sql, expected_sql):
  actual_sql_tokens = tokenize_sql(actual_sql)
  expected_sql_tokens = tokenize_sql(expected_sql)
  sorted_actual_sql_tokens = sorted(actual_sql_tokens)
  sorted_expected_sql_tokens = sorted(expected_sql_tokens)

  if sorted_actual_sql_tokens != sorted_expected_sql_tokens:
    print('\n')
    print(sorted_actual_sql_tokens)
    print(sorted_expected_sql_tokens)

  assert sorted_actual_sql_tokens == sorted_expected_sql_tokens


class TestCollector:
  def test_from_definition_with_query_spec_creates_correct_collector(self):
    collector_definition = {
      'name': 'test',
      'query_spec': {'level': 'ad_group', 'metrics': ['clicks']},
    }
    collector = query_collector.Collector.from_definition(collector_definition)
    expected_collector = query_collector.Collector(
      name='test',
      metrics='clicks',
      level=query_collector.CollectorLevel.AD_GROUP,
    )
    assert collector == expected_collector

  def test_from_definition_with_query_creates_correct_collector(self):
    collector_definition = {
      'name': 'test',
      'query': 'SELECT campaign.id FROM campaign',
    }
    collector = query_collector.Collector.from_definition(collector_definition)
    expected_collector = query_collector.Collector(
      name='test', query='SELECT campaign.id FROM campaign'
    )
    assert collector.query == expected_collector.query

  def test_create_conversion_split_collector_returns_correct_collector(self):
    test_collector = query_collector.Collector(
      name='test',
      metrics='clicks',
      level=query_collector.CollectorLevel.AD_GROUP,
    )
    conv_split_collector = test_collector.create_conversion_split_collector()
    expected_collector = query_collector.Collector(
      name='test_conversion_split',
      metrics='all_conversions,all_conversions_value',
      level=test_collector.level,
      dimensions=[
        query_collector.Field(
          'segments.conversion_action_category', 'conversion_category'
        ),
        query_collector.Field(
          'segments.conversion_action_name', 'conversion_name'
        ),
        query_collector.Field('segments.conversion_action~0', 'conversion_id'),
      ],
      resource_name=test_collector.resource_name,
      filters='metrics.all_conversions > 0',
    )
    assert conv_split_collector == expected_collector

  class TestCollectorQuery:
    def test_simple_collector_creates_correct_query(self):
      collector = query_collector.Collector(
        name='simple',
        metrics='impressions',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_complex_collector_creates_correct_query(self):
      collector = query_collector.Collector(
        metrics='impressions,clicks',
        level=query_collector.CollectorLevel.AD_GROUP,
        dimensions=[
          query_collector.Field(
            name='segments.conversion_action~0', alias='conversion_id'
          ),
          query_collector.Field(
            name='search_terms_view.search_term', alias='search_term'
          ),
        ],
      )
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
            metrics.clicks AS clicks,
            segments.conversion_action~0 AS conversion_id,
            search_terms_view.search_term AS search_term,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_complex_collector_with_virtual_column_creates_correct_query(self):
      collector = query_collector.Collector(
        metrics=[
          query_collector.Field(name='impressions'),
          query_collector.Field(name='clicks'),
          query_collector.Field(name='cost_micros * 1e6', alias='cost'),
          query_collector.Field(name='clicks / impressions', alias='ctr'),
          query_collector.Field(
            name='var1-var2/(1.05e3+var3)*100.5', alias='vc'
          ),
        ],
        level=query_collector.CollectorLevel.AD_GROUP,
        dimensions=[
          query_collector.Field(
            name='segments.conversion_action~0', alias='conversion_id'
          ),
          query_collector.Field(
            name='search_terms_view.search_term', alias='search_term'
          ),
        ],
      )
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
            metrics.clicks AS clicks,
            metrics.cost_micros * 1e6 AS cost,
            metrics.clicks / metrics.impressions AS ctr,
            metrics.var1 - metrics.var2 / ( 1.05e3 + metrics.var3 ) * 100.5
            AS vc,
            segments.conversion_action~0 AS conversion_id,
            search_terms_view.search_term AS search_term,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_service_collector_creates_correct_query(self):
      collector = query_collector.ServiceCollector(
        name='mapping',
        dimensions=[
          query_collector.Field(name='ad_group.id', alias='ad_group_id'),
          query_collector.Field(name='ad_group.name', alias='ad_group_name'),
          query_collector.Field(name='campaign.id', alias='campaign_id'),
          query_collector.Field(name='campaign.name', alias='campaign_name'),
          query_collector.Field(name='customer.id', alias='customer_id'),
          query_collector.Field(
            name='customer.descriptive_name', alias='account_name'
          ),
        ],
        filters=(
          'ad_group.status = ENABLED'
          ' AND campaign.status = ENABLED'
          ' AND customer.status = ENABLED'
        ),
      )

      expected_sql = """
          SELECT
              1 AS info,
              ad_group.id AS ad_group_id,
              ad_group.name AS ad_group_name,
              campaign.id AS campaign_id,
              campaign.name AS campaign_name,
              customer.id AS customer_id,
              customer.descriptive_name AS account_name,
          FROM ad_group
          WHERE ad_group.status = ENABLED
            AND campaign.status = ENABLED
            AND customer.status = ENABLED
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_service_collector_cannot_change_metrics_value(self):
      collector = query_collector.ServiceCollector(
        name='mapping',
        dimensions=[
          query_collector.Field(name='ad_group.id', alias='ad_group_id'),
        ],
      )
      with pytest.raises(ValueError):
        collector.metrics = query_collector.Field('ad_group.id')

    def test_mcc_level_collector_creates_correct_customer_level_query(self):
      collector = query_collector.Collector(
        name='simple_mcc_level',
        metrics='impressions',
        level=query_collector.CollectorLevel.MCC,
      )
      expected_sql = """
        SELECT
            customer.id AS customer_id,
            metrics.impressions AS impressions,
        FROM customer
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_ad_group_ad_level_collector_creates_correct_query(self):
      collector = query_collector.Collector(
        name='simple_ad_group_ad_level',
        metrics='impressions',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
      )

      expected_sql = """
        SELECT
            ad_group_ad.ad.id AS ad_id,
            metrics.impressions AS impressions,
        FROM ad_group_ad
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_ad_group_level_collector_with_resource_name_creates_correct_query(
      self,
    ):
      collector = query_collector.Collector(
        name='simple_with_resource',
        metrics='impressions',
        resource_name='search_term_view',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      assert f'FROM {collector.resource_name}' in collector.query

    def test_collector_with_not_unique_files_creates_query_with_unique_fields(
      self,
    ):
      collector = query_collector.Collector(
        name='simple',
        metrics='impressions',
        dimensions=[
          query_collector.Field('ad_group.id'),
        ],
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_collector_with_nested_fieds_names_creates_correct_query(self):
      collector = query_collector.Collector(
        name='bid_budget',
        metrics=[
          query_collector.Field('impressions'),
          query_collector.Field('campaign_budget.amount_micros', 'budget'),
          query_collector.Field(
            'campaign.target_cpa.target_cpa_micros', 'target_cpa'
          ),
        ],
        level=query_collector.CollectorLevel.CAMPAIGN,
      )
      expected_sql = """
        SELECT
            campaign.id AS campaign_id,
            metrics.impressions AS impressions,
            campaign_budget.amount_micros AS budget,
            campaign.target_cpa.target_cpa_micros AS target_cpa,
        FROM campaign
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    def test_collector_with_empty_metrics_creates_correct_query(self):
      collector = query_collector.Collector(
        name='disapproval',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
        dimensions=[
          query_collector.Field('campaign.id', 'campaign_id'),
          query_collector.Field(
            'ad_group_ad.policy_summary.approval_status', 'approval_status'
          ),
          query_collector.Field(
            'ad_group_ad.policy_summary.review_status', 'review_status'
          ),
        ],
        filters=(
          'campaign.status = ENABLED'
          ' AND ad_group.status = ENABLED'
          ' AND ad_group_ad.status = ENABLED'
          ' AND ad_group_ad.policy_summary.approval_status != APPROVED'
        ),
      )
      expected_sql = """
        SELECT
            ad_group_ad.ad.id AS ad_id,
            campaign.id AS campaign_id,
            ad_group_ad.policy_summary.approval_status AS approval_status,
            ad_group_ad.policy_summary.review_status AS review_status,
        FROM ad_group_ad
        WHERE campaign.status = ENABLED
            AND ad_group.status = ENABLED
            AND ad_group_ad.status = ENABLED
            AND ad_group_ad.policy_summary.approval_status != APPROVED
        """
      assert_sql_functionally_equivalent(collector.query, expected_sql)

    @pytest.mark.parametrize(
      'test_level, expected_sql',
      [
        (
          query_collector.CollectorLevel.AD_GROUP_AD,
          """
                SELECT
                    1 AS info,
                    ad_group_ad.ad.id AS ad_id,
                    ad_group_ad.ad.name AS ad_name,
                    ad_group.id AS ad_group_id,
                    ad_group.name AS ad_group_name,
                    campaign.id AS campaign_id,
                    campaign.name AS campaign_name,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM ad_group_ad
                WHERE ad_group_ad.status = ENABLED
                    AND ad_group.status = ENABLED
                    AND campaign.status = ENABLED
                    AND customer.status = ENABLED
            """,
        ),
        (
          query_collector.CollectorLevel.AD_GROUP,
          """
                SELECT
                    1 AS info,
                    ad_group.id AS ad_group_id,
                    ad_group.name AS ad_group_name,
                    campaign.id AS campaign_id,
                    campaign.name AS campaign_name,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM ad_group
                WHERE ad_group.status = ENABLED
                    AND campaign.status = ENABLED
                    AND customer.status = ENABLED
            """,
        ),
        (
          query_collector.CollectorLevel.CAMPAIGN,
          """
                SELECT
                    1 AS info,
                    campaign.id AS campaign_id,
                    campaign.name AS campaign_name,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM campaign
                WHERE campaign.status = ENABLED
                    AND customer.status = ENABLED
            """,
        ),
        (
          query_collector.CollectorLevel.CUSTOMER,
          """
                SELECT
                    1 AS info,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM customer
                WHERE customer.status = ENABLED
            """,
        ),
        (
          query_collector.CollectorLevel.MCC,
          """
                SELECT
                    1 AS info,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM customer
                WHERE customer.status = ENABLED
            """,
        ),
      ],
    )
    def test_create_default_service_collector_returns_correct_service_collector_query_for_level(  # pylint: disable=line-too-long
      self, test_level, expected_sql
    ):
      actual_collector = query_collector.create_default_service_collector(
        test_level
      )
      assert_sql_functionally_equivalent(actual_collector.query, expected_sql)

  class TestCollectorProperties:
    def test_metrics_returns_correct_fields(self):
      collector = query_collector.Collector(metrics='clicks')
      assert collector.metrics == {
        query_collector.Field(name='metrics.clicks', alias='clicks'),
      }

    def test_dimensions_returns_correct_fields(self):
      collector = query_collector.Collector(dimensions='segments.date')
      assert collector.dimensions == {
        query_collector.Field(name='segments.date', alias=None),
      }

    @pytest.mark.parametrize(
      'filters,expected_filter',
      [
        (
          'segments.date DURING YESTERDAY',
          'WHERE segments.date DURING YESTERDAY',
        ),
        (None, 'WHERE segments.date DURING TODAY'),
      ],
    )
    def test_filters_returns_correct_expression(self, filters, expected_filter):
      collector = query_collector.Collector(metrics='clicks', filters=filters)

      assert collector.formatted_filters == expected_filter

    def test_resource_name_returns_correct_expression_for_explicit_resource_name(
      self,
    ):
      resource_name = 'search_term_view'
      level = query_collector.CollectorLevel.AD_GROUP
      expected_resource_name = 'search_term_view'

      collector = query_collector.Collector(
        level=level, resource_name=resource_name
      )

      assert collector.resource_name == expected_resource_name

    def test_resource_name_returns_correct_expression_for_missing_resource_name(
      self,
    ):
      level = query_collector.CollectorLevel.CAMPAIGN
      expected_resource_name = 'campaign'

      collector = query_collector.Collector(level=level)

      assert collector.resource_name == expected_resource_name

    def test_resource_name_returns_correct_expression_for_missing_resource_name_and_level(  # pylint: disable=line-too-long
      self,
    ):
      expected_resource_name = 'ad_group'

      collector = query_collector.Collector()

      assert collector.resource_name == expected_resource_name

    def test_set_metrics_from_fields_returns_updated_fields(self):
      collector = query_collector.Collector(metrics='clicks')
      collector.metrics = [query_collector.Field(name='impressions')]
      assert collector.metrics == {
        query_collector.Field(name='metrics.impressions', alias='impressions'),
      }

    def test_set_metrics_from_strings_returns_updated_fields(self):
      collector = query_collector.Collector(metrics='clicks')
      collector.metrics = ['impressions']
      assert collector.metrics == {
        query_collector.Field(name='metrics.impressions', alias='impressions'),
      }

    def test_add_metrics_returns_updated_fields(self):
      collector = query_collector.Collector(metrics='clicks')
      collector.metrics.add(
        query_collector.Field(name='metrics.impressions', alias='impressions')
      )
      assert collector.metrics == {
        query_collector.Field(name='metrics.clicks', alias='clicks'),
        query_collector.Field(name='metrics.impressions', alias='impressions'),
      }

    def test_set_dimensions_from_fields_returns_updated_fields(self):
      collector = query_collector.Collector(dimensions='campaign.name')
      collector.dimensions = [query_collector.Field(name='campaign.id')]
      assert collector.dimensions == {
        query_collector.Field(name='campaign.id', alias='campaign_id'),
      }

    def test_set_dimensions_from_strings_returns_updated_fields(self):
      collector = query_collector.Collector(dimensions='campaign.name')
      collector.dimensions = ['campaign.id']
      assert collector.dimensions == {
        query_collector.Field(name='campaign.id', alias='campaign_id'),
      }

    def test_add_dimensions_returns_updated_fields(self):
      collector = query_collector.Collector(dimensions='campaign.name')
      collector.dimensions.add(query_collector.Field(name='campaign.id'))
      assert collector.dimensions == {
        query_collector.Field(name='campaign.name', alias='campaign_name'),
        query_collector.Field(name='campaign.id', alias='campaign_id'),
      }

    def test_get_filters_from_and_condition_returns_set(self):
      collector = query_collector.Collector(
        filters='campaign.status = ENABLED AND ad_group.status = ENABLED'
      )
      assert collector.filters == {
        'campaign.status = ENABLED',
        'ad_group.status = ENABLED',
      }

    def test_get_filters_from_collector_with_metrics_and_filters_adds_segment_date(  # pylint: disable=line-too-long
      self,
    ):
      collector = query_collector.Collector(
        metrics='impressions',
        filters='campaign.status = ENABLED AND ad_group.status = ENABLED',
      )
      assert collector.filters == {
        'campaign.status = ENABLED',
        'ad_group.status = ENABLED',
        'segments.date DURING TODAY',
      }

    def test_get_filters_from_collector_with_metrics_and_no_filters_adds_segment_date(  # pylint: disable=line-too-long
      self,
    ):
      collector = query_collector.Collector(
        metrics='impressions',
      )
      assert collector.filters == {
        'segments.date DURING TODAY',
      }

    def test_set_filters_from_strings_returns_updated_fields(self):
      collector = query_collector.Collector(filters='campaign.status = ENABLED')
      collector.filters = ['campaign.status = PAUSED']
      assert collector.filters == {
        'campaign.status = PAUSED',
      }

    def test_add_filters_returns_updated_fields(self):
      collector = query_collector.Collector(filters='campaign.status = ENABLED')
      collector.filters.add('ad_group.status = ENABLED')
      assert collector.filters == {
        'campaign.status = ENABLED',
        'ad_group.status = ENABLED',
      }

  class TestCollectorEquality:
    def test_collector_with_the_same_metrics_are_equal(self):
      collector1 = query_collector.Collector(
        name='collector1', metrics='clicks,conversions'
      )
      collector2 = query_collector.Collector(
        name='collector2', metrics='clicks,conversions'
      )

      assert collector1 == collector2

    def test_collectors_with_different_metrics_and_dimensions_are_not_equal(
      self,
    ):
      collector1 = query_collector.Collector(
        name='collector1', metrics='clicks,conversions'
      )
      collector2 = query_collector.Collector(
        name='collector2', dimensions='clicks,conversions'
      )

      assert collector1 != collector2

    def test_collectors_with_same_metrics_but_different_instantiations_are_equal(  # pylint: disable=line-too-long
      self,
    ):
      collector1 = query_collector.Collector(metrics='clicks,conversions')
      collector2 = query_collector.Collector(
        metrics=[
          query_collector.Field(name='clicks'),
          query_collector.Field(name='conversions'),
        ]
      )

      assert collector1 == collector2

    def test_collectors_with_different_order_of_metrics_are_equal(self):
      collector1 = query_collector.Collector(
        metrics=[
          query_collector.Field(name='conversions'),
          query_collector.Field(name='impressions', alias='imp'),
        ]
      )
      collector2 = query_collector.Collector(
        metrics=[
          query_collector.Field(name='impressions', alias='imp'),
          query_collector.Field(name='conversions'),
        ],
      )

      assert collector1 == collector2

  class TestCollectorSimilarity:
    def test_collectors_with_same_metrics_and_dimensions_are_similar(self):
      collector1 = query_collector.Collector(
        name='collector1',
        metrics='clicks,conversions',
        dimensions='segments.date',
        filters='segments.date DURING TODAY',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      collector2 = query_collector.Collector(
        name='collector2',
        metrics='clicks,conversions',
        dimensions='segments.date',
        filters='segments.date DURING TODAY',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
      )
      assert collector1.is_similar(collector2)
      assert collector1 != collector2

    def test_collectors_with_different_metrics_and_same_dimensions_are_not_similar(  # pylint: disable=line-too-long
      self,
    ):
      collector1 = query_collector.Collector(
        name='collector1',
        metrics='clicks',
        dimensions='segments.date',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      collector2 = query_collector.Collector(
        name='collector2',
        metrics='clicks,conversions',
        dimensions='segments.date',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
      )
      assert not collector1.is_similar(collector2)

    def test_collectors_with_same_metrics_and_different_dimensions_are_not_similar(  # pylint: disable=line-too-long
      self,
    ):
      collector1 = query_collector.Collector(
        name='collector1',
        metrics='clicks,conversions',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      collector2 = query_collector.Collector(
        name='collector2',
        metrics='clicks,conversions',
        dimensions='segments.date',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
      )
      assert not collector1.is_similar(collector2)

    def test_collectors_with_different_filters_are_not_similar(self):
      collector1 = query_collector.Collector(
        name='collector1',
        metrics='clicks,conversions',
        dimensions='segments.date',
        filters='segments.date DURING TODAY',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      collector2 = query_collector.Collector(
        name='collector2',
        metrics='clicks,conversions',
        dimensions='segments.date',
        filters='segments.date DURING YESTERDAY',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      assert not collector1.is_similar(collector2)

    def test_collectors_with_different_resource_names_are_not_similar(self):
      collector1 = query_collector.Collector(
        name='collector1',
        metrics='clicks,conversions',
        dimensions='segments.date',
        filters='segments.date DURING TODAY',
        resource_name='age_view',
        level=query_collector.CollectorLevel.AD_GROUP,
      )
      collector2 = query_collector.Collector(
        name='collector2',
        metrics='clicks,conversions',
        dimensions='segments.date',
        resource_name='gender_view',
        filters='segments.date DURING TODAY',
        level=query_collector.CollectorLevel.AD_GROUP_AD,
      )
      assert not collector1.is_similar(collector2)


@pytest.mark.parametrize(
  'collectors,expected',
  [
    (
      [
        query_collector.Collector(
          name='collector1',
          metrics='clicks,conversions',
          level=query_collector.CollectorLevel.CUSTOMER,
        ),
        query_collector.Collector(
          name='collector2',
          metrics='clicks,conversions',
          level=query_collector.CollectorLevel.AD_GROUP,
        ),
        query_collector.Collector(
          name='collector3',
          metrics='clicks,conversions',
          level=query_collector.CollectorLevel.AD_GROUP_AD,
        ),
        query_collector.Collector(
          name='collector4',
          metrics='clicks,conversions,impressions',
          level=query_collector.CollectorLevel.MCC,
        ),
      ],
      ['collector3', 'collector4'],
    ),
  ],
)
def test_collectors_similarity_check_returns_deduplicated_collectors(
  collectors, expected
):
  actual = query_collector.collectors_similarity_check(collectors)
  assert set([t.name for t in actual]) == set(expected)
