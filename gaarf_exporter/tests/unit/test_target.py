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

from gaarf_exporter import query_elements
from gaarf_exporter import target as query_target


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


class TestTarget:

  class TestTargetQuery:

    def test_simple_target_creates_correct_query(self):
      target = query_target.Target(
          name='simple',
          metrics='impressions',
          level=query_target.TargetLevel.AD_GROUP)
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_complex_target_creates_correct_query(self):
      target = query_target.Target(
          metrics='impressions,clicks',
          level=query_target.TargetLevel.AD_GROUP,
          dimensions=[
              query_elements.Field(
                  name='segments.conversion_action',
                  alias='conversion_id',
                  customizer=query_elements.Customizer(
                      query_elements.CustomizerTypeEnum.INDEX, '0')),
              query_elements.Field(
                  name='search_terms_view.search_term', alias='search_term')
          ])
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
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_complex_target_with_virtual_column_creates_correct_query(self):
      target = query_target.Target(
          metrics=[
              query_elements.Field(name='impressions'),
              query_elements.Field(name='clicks'),
              query_elements.Field(name='cost_micros * 1e6', alias='cost'),
              query_elements.Field(name='clicks / impressions', alias='ctr'),
              query_elements.Field(
                  name='var1-var2/(1.05e3+var3)*100.5', alias='vc')
          ],
          level=query_target.TargetLevel.AD_GROUP,
          dimensions=[
              query_elements.Field(
                  name='segments.conversion_action',
                  alias='conversion_id',
                  customizer=query_elements.Customizer(
                      query_elements.CustomizerTypeEnum.INDEX, '0')),
              query_elements.Field(
                  name='search_terms_view.search_term', alias='search_term')
          ])
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
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_service_target_creates_correct_query(self):
      target = query_target.ServiceTarget(
          name='mapping',
          dimensions=[
              query_elements.Field(name='ad_group.id', alias='ad_group_id'),
              query_elements.Field(name='ad_group.name', alias='ad_group_name'),
              query_elements.Field(name='campaign.id', alias='campaign_id'),
              query_elements.Field(name='campaign.name', alias='campaign_name'),
              query_elements.Field(name='customer.id', alias='customer_id'),
              query_elements.Field(
                  name='customer.descriptive_name', alias='account_name'),
          ],
          filters=('ad_group.status = ENABLED'
                   ' AND campaign.status = ENABLED'
                   ' AND customer.status = ENABLED'))

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
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_service_target_cannot_change_metrics_value(self):
      target = query_target.ServiceTarget(
          name='mapping',
          dimensions=[
              query_elements.Field(name='ad_group.id', alias='ad_group_id'),
          ])
      with pytest.raises(ValueError):
        target.metrics = query_elements.Field('ad_group.id')

    def test_mcc_level_target_creates_correct_customer_level_query(self):
      target = query_target.Target(
          name='simple_mcc_level',
          metrics='impressions',
          level=query_target.TargetLevel.MCC)
      expected_sql = """
        SELECT
            customer.id AS customer_id,
            metrics.impressions AS impressions,
        FROM customer
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_ad_group_ad_level_target_creates_correct_query(self):
      target = query_target.Target(
          name='simple_ad_group_ad_level',
          metrics='impressions',
          level=query_target.TargetLevel.AD_GROUP_AD)

      expected_sql = """
        SELECT
            ad_group_ad.ad.id AS ad_id,
            metrics.impressions AS impressions,
        FROM ad_group_ad
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_ad_group_level_target_with_resource_name_creates_correct_query(
        self):
      target = query_target.Target(
          name='simple_with_resource',
          metrics='impressions',
          resource_name='search_term_view',
          level=query_target.TargetLevel.AD_GROUP)
      assert f'FROM {target.resource_name}' in target.query

    def test_target_with_not_unique_files_creates_query_with_unique_fields(
        self):
      target = query_target.Target(
          name='simple',
          metrics='impressions',
          dimensions=[
              query_elements.Field('ad_group.id'),
          ],
          level=query_target.TargetLevel.AD_GROUP)
      expected_sql = """
        SELECT
            ad_group.id AS ad_group_id,
            metrics.impressions AS impressions,
        FROM ad_group
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_target_with_nested_fieds_names_creates_correct_query(self):
      target = query_target.Target(
          name='bid_budget',
          metrics=[
              query_elements.Field('impressions'),
              query_elements.Field('campaign_budget.amount_micros', 'budget'),
              query_elements.Field('campaign.target_cpa.target_cpa_micros',
                                   'target_cpa'),
          ],
          level=query_target.TargetLevel.CAMPAIGN)
      expected_sql = """
        SELECT
            campaign.id AS campaign_id,
            metrics.impressions AS impressions,
            campaign_budget.amount_micros AS budget,
            campaign.target_cpa.target_cpa_micros AS target_cpa,
        FROM campaign
        WHERE segments.date DURING TODAY
        """
      assert_sql_functionally_equivalent(target.query, expected_sql)

    def test_target_with_empty_metrics_creates_correct_query(self):
      target = query_target.Target(
          name='disapproval',
          level=query_target.TargetLevel.AD_GROUP_AD,
          dimensions=[
              query_elements.Field('campaign.id', 'campaign_id'),
              query_elements.Field('ad_group_ad.policy_summary.approval_status',
                                   'approval_status'),
              query_elements.Field('ad_group_ad.policy_summary.review_status',
                                   'review_status')
          ],
          filters=(
              'campaign.status = ENABLED'
              ' AND ad_group.status = ENABLED'
              ' AND ad_group_ad.status = ENABLED'
              ' AND ad_group_ad.policy_summary.approval_status != APPROVED'))
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
      assert_sql_functionally_equivalent(target.query, expected_sql)

    @pytest.mark.parametrize('test_level, expected_sql', [
        (query_target.TargetLevel.AD_GROUP_AD, """
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
            """),
        (query_target.TargetLevel.AD_GROUP, """
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
            """),
        (query_target.TargetLevel.CAMPAIGN, """
                SELECT
                    1 AS info,
                    campaign.id AS campaign_id,
                    campaign.name AS campaign_name,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM campaign
                WHERE campaign.status = ENABLED
                    AND customer.status = ENABLED
            """),
        (query_target.TargetLevel.CUSTOMER, """
                SELECT
                    1 AS info,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM customer
                WHERE customer.status = ENABLED
            """),
        (query_target.TargetLevel.MCC, """
                SELECT
                    1 AS info,
                    customer.id AS customer_id,
                    customer.descriptive_name AS account_name,
                FROM customer
                WHERE customer.status = ENABLED
            """),
    ])
    def test_create_default_service_target_returns_correct_service_target_query_for_level(  # pylint: disable=line-too-long
        self, test_level, expected_sql):
      actual_target = query_target.create_default_service_target(test_level)
      assert_sql_functionally_equivalent(actual_target.query, expected_sql)

  class TestTargetProperties:

    def test_metrics_returns_correct_fields(self):
      target = query_target.Target(metrics='clicks')
      assert target.metrics == {
          query_elements.Field(name='metrics.clicks', alias='clicks'),
      }

    def test_dimensions_returns_correct_fields(self):
      target = query_target.Target(dimensions='segments.date')
      assert target.dimensions == {
          query_elements.Field(name='segments.date', alias=None),
      }

    @pytest.mark.parametrize('filters,expected_filter', [
        ('segments.date DURING YESTERDAY', 'segments.date DURING YESTERDAY'),
        (None, 'segments.date DURING TODAY'),
    ])
    def test_filters_returns_correct_expression(self, filters, expected_filter):
      target = query_target.Target(filters=filters)

      assert target.filters == expected_filter

    def test_resource_name_returns_correct_expression_for_explicit_resource_name(
        self):
      resource_name = 'search_term_view'
      level = query_target.TargetLevel.AD_GROUP
      expected_resource_name = 'search_term_view'

      target = query_target.Target(level=level, resource_name=resource_name)

      assert target.resource_name == expected_resource_name

    def test_resource_name_returns_correct_expression_for_missing_resource_name(
        self):
      level = query_target.TargetLevel.CAMPAIGN
      expected_resource_name = 'campaign'

      target = query_target.Target(level=level)

      assert target.resource_name == expected_resource_name

    def test_resource_name_returns_correct_expression_for_missing_resource_name_and_level(  # pylint: disable=line-too-long
        self):
      expected_resource_name = 'ad_group'

      target = query_target.Target()

      assert target.resource_name == expected_resource_name

  class TestTargetEquality:

    def test_target_with_the_same_metrics_are_equal(self):
      target1 = query_target.Target(
          name='target1', metrics='clicks,conversions')
      target2 = query_target.Target(
          name='target2', metrics='clicks,conversions')

      assert target1 == target2

    def test_targets_with_different_metrics_and_dimensions_are_not_equal(self):
      target1 = query_target.Target(
          name='target1', metrics='clicks,conversions')
      target2 = query_target.Target(
          name='target2', dimensions='clicks,conversions')

      assert target1 != target2

    def test_targets_with_same_metrics_but_different_instantiations_are_equal(
        self):
      target1 = query_target.Target(metrics='clicks,conversions')
      target2 = query_target.Target(metrics=[
          query_elements.Field(name='clicks'),
          query_elements.Field(name='conversions'),
      ])

      assert target1 == target2

    def test_targets_with_different_order_of_metrics_are_equal(self):
      target1 = query_target.Target(metrics=[
          query_elements.Field(name='conversions'),
          query_elements.Field(name='impressions', alias='imp'),
      ])
      target2 = query_target.Target(
          metrics=[
              query_elements.Field(name='impressions', alias='imp'),
              query_elements.Field(name='conversions')
          ],)

      assert target1 == target2

  class TestTargetSimilarity:

    def test_targets_with_same_metrics_and_dimensions_are_similar(self):
      target1 = query_target.Target(
          name='target1',
          metrics='clicks,conversions',
          dimensions='segments.date',
          filters='segments.date DURING TODAY',
          level=query_target.TargetLevel.AD_GROUP)
      target2 = query_target.Target(
          name='target2',
          metrics='clicks,conversions',
          dimensions='segments.date',
          filters='segments.date DURING TODAY',
          level=query_target.TargetLevel.AD_GROUP_AD)
      assert target1.is_similar(target2)
      assert target1 != target2

    def test_targets_with_different_metrics_and_same_dimensions_are_not_similar(
        self):
      target1 = query_target.Target(
          name='target1',
          metrics='clicks',
          dimensions='segments.date',
          level=query_target.TargetLevel.AD_GROUP)
      target2 = query_target.Target(
          name='target2',
          metrics='clicks,conversions',
          dimensions='segments.date',
          level=query_target.TargetLevel.AD_GROUP_AD)
      assert not target1.is_similar(target2)

    def test_targets_with_same_metrics_and_different_dimensions_are_not_similar(
        self):
      target1 = query_target.Target(
          name='target1',
          metrics='clicks,conversions',
          level=query_target.TargetLevel.AD_GROUP)
      target2 = query_target.Target(
          name='target2',
          metrics='clicks,conversions',
          dimensions='segments.date',
          level=query_target.TargetLevel.AD_GROUP_AD)
      assert not target1.is_similar(target2)

    def test_targets_with_different_filters_are_not_similar(self):
      target1 = query_target.Target(
          name='target1',
          metrics='clicks,conversions',
          dimensions='segments.date',
          filters='segments.date DURING TODAY',
          level=query_target.TargetLevel.AD_GROUP)
      target2 = query_target.Target(
          name='target2',
          metrics='clicks,conversions',
          dimensions='segments.date',
          filters='segments.date DURING YESTERDAY',
          level=query_target.TargetLevel.AD_GROUP)
      assert not target1.is_similar(target2)

    def test_targets_with_different_resource_names_are_not_similar(self):
      target1 = query_target.Target(
          name='target1',
          metrics='clicks,conversions',
          dimensions='segments.date',
          filters='segments.date DURING TODAY',
          resource_name='age_view',
          level=query_target.TargetLevel.AD_GROUP)
      target2 = query_target.Target(
          name='target2',
          metrics='clicks,conversions',
          dimensions='segments.date',
          resource_name='gender_view',
          filters='segments.date DURING TODAY',
          level=query_target.TargetLevel.AD_GROUP_AD)
      assert not target1.is_similar(target2)


@pytest.mark.parametrize('targets,expected', [
    ([
        query_target.Target(
            name='target1',
            metrics='clicks,conversions',
            level=query_target.TargetLevel.CUSTOMER),
        query_target.Target(
            name='target2',
            metrics='clicks,conversions',
            level=query_target.TargetLevel.AD_GROUP),
        query_target.Target(
            name='target3',
            metrics='clicks,conversions',
            level=query_target.TargetLevel.AD_GROUP_AD),
        query_target.Target(
            name='target4',
            metrics='clicks,conversions,impressions',
            level=query_target.TargetLevel.MCC)
    ], ['target3', 'target4']),
])
def test_targets_similarity_check_returns_deduplicated_targets(
    targets, expected):
  actual = query_target.targets_similarity_check(targets)
  assert set([t.name for t in actual]) == set(expected)
