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
from typing import List

import pytest

from gaarf_exporter.query_elements import Field, Customizer, CustomizerTypeEnum
from gaarf_exporter.target import Target, TargetLevel, create_default_service_target, targets_similarity_check


def tokenize_sql(sql: str) -> List[str]:
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


def test_simple_target_create_query(simple_target):
    expected_sql = """
    SELECT
        ad_group.id AS ad_group_id,
        metrics.impressions AS impressions
    FROM ad_group
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(simple_target.query, expected_sql)


def test_complex_target_create_query(complex_target):
    expected_sql = """
    SELECT
        ad_group.id AS ad_group_id,
        metrics.impressions AS impressions,
        metrics.clicks AS clicks,
        segments.conversion_action~0 AS conversion_id,
        search_terms_view.search_term AS search_term
    FROM ad_group
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(complex_target.query, expected_sql)


def test_complex_target_with_virtual_column_create_query(
        complex_target_with_virtual_column):
    expected_sql = """
    SELECT
        ad_group.id AS ad_group_id,
        metrics.impressions AS impressions,
        metrics.clicks AS clicks,
        metrics.cost_micros * 1e6 AS cost,
        metrics.clicks / metrics.impressions AS ctr,
        metrics.var1 - metrics.var2 / ( 1.05e3 + metrics.var3 ) * 100.5 AS vc,
        segments.conversion_action~0 AS conversion_id,
        search_terms_view.search_term AS search_term
    FROM ad_group
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(
        complex_target_with_virtual_column.query, expected_sql)


def test_no_metric_target(no_metric_target):
    expected_sql = """
      SELECT
          1 AS info,
          ad_group.id AS ad_group_id,
          ad_group.name AS ad_group_name,
          campaign.id AS campaign_id,
          campaign.name AS campaign_name,
          customer.id AS customer_id,
          customer.descriptive_name AS account_name
      FROM ad_group
      WHERE ad_group.status = 'ENABLED'
        AND campaign.status = 'ENABLED'
        AND customer.status = 'ENABLED'
    """
    assert_sql_functionally_equivalent(no_metric_target.query, expected_sql)


def test_target_at_mcc_level_create_query(simple_target_at_mcc_level):
    expected_sql = """
    SELECT
        customer.id AS customer_id,
        metrics.impressions AS impressions
    FROM customer
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(simple_target_at_mcc_level.query,
                                       expected_sql)


def test_target_at_ad_group_ad_level_create_query(
    simple_target_at_ad_group_ad_level):
    expected_sql = """
    SELECT
        ad_group_ad.ad.id AS ad_group_ad_ad_id,
        metrics.impressions AS impressions
    FROM ad_group_ad
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(
        simple_target_at_ad_group_ad_level.query, expected_sql)


@pytest.mark.parametrize(
    'test_level, expected_sql',
    [
        (TargetLevel.AD_GROUP_AD, """
            SELECT
                1 AS info,
                ad_group_ad.ad.id AS ad_group_ad_ad_id,
                ad_group_ad.ad.name AS ad_group_ad_ad_name,
                ad_group.id AS ad_group_id,
                ad_group.name AS ad_group_name,
                campaign.id AS campaign_id,
                campaign.name AS campaign_name,
                customer.id AS customer_id,
                customer.descriptive_name AS account_name
            FROM ad_group_ad
            WHERE ad_group_ad.status = 'ENABLED'
                AND ad_group.status = 'ENABLED'
                AND campaign.status = 'ENABLED'
                AND customer.status = 'ENABLED'
        """),
    (TargetLevel.AD_GROUP, """
            SELECT
                1 AS info,
                ad_group.id AS ad_group_id,
                ad_group.name AS ad_group_name,
                campaign.id AS campaign_id,
                campaign.name AS campaign_name,
                customer.id AS customer_id,
                customer.descriptive_name AS account_name
            FROM ad_group
            WHERE ad_group.status = 'ENABLED'
                AND campaign.status = 'ENABLED'
                AND customer.status = 'ENABLED'
        """),
    (TargetLevel.CAMPAIGN, """
            SELECT
                1 AS info,
                campaign.id AS campaign_id,
                campaign.name AS campaign_name,
                customer.id AS customer_id,
                customer.descriptive_name AS account_name
            FROM campaign
            WHERE campaign.status = 'ENABLED'
                AND customer.status = 'ENABLED'
        """),
    (TargetLevel.CUSTOMER, """
            SELECT
                1 AS info,
                customer.id AS customer_id,
                customer.descriptive_name AS account_name
            FROM customer
            WHERE customer.status = 'ENABLED'
        """),
    (TargetLevel.MCC, """
            SELECT
                1 AS info,
                customer.id AS customer_id,
                customer.descriptive_name AS account_name
            FROM customer
            WHERE customer.status = 'ENABLED'
        """),
])
def test_create_default_service_target_at_ad_group_ad_level(
        test_level, expected_sql):
    actual_target = create_default_service_target(test_level)
    assert_sql_functionally_equivalent(actual_target.query, expected_sql)


def test_target_with_empty_metric_create_query(empty_metric_target):
    expected_sql = """
    SELECT
        ad_group_ad.ad.id AS ad_group_ad_ad_id,
        campaign.id AS campaign_id,
        ad_group_ad.policy_summary.approval_status AS approval_status,
        ad_group_ad.policy_summary.review_status AS review_status
    FROM ad_group_ad
    WHERE campaign.status = 'ENABLED'
        AND ad_group.status = 'ENABLED'
        AND ad_group_ad.status = 'ENABLED'
        AND ad_group_ad.policy_summary.approval_status != 'APPROVED'
    """
    assert_sql_functionally_equivalent(empty_metric_target.query, expected_sql)


@pytest.fixture
def simple_target_with_resource():
    return Target(name='simple_with_resource',
                  metrics="impressions",
                  resource_name="search_term_view",
                  level=TargetLevel.AD_GROUP)


def test_target_with_resource_name_selects_from_resource_name(
        simple_target_with_resource):
    assert (f"FROM {simple_target_with_resource.resource_name}"
            in simple_target_with_resource.query)


def test_target_returns_only_unique_query_fields():
    target = Target(name='simple',
                    metrics="impressions",
                    dimensions=[Field("ad_group.id")],
                    level=TargetLevel.AD_GROUP)
    expected_sql = """
    SELECT
        ad_group.id AS ad_group_id,
        metrics.impressions AS impressions
    FROM ad_group
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(target.query, expected_sql)


def test_target_can_handle_complex_metrics_with_three_components():
    target = Target(name='bid_budget',
                    metrics=[
                        Field("impressions"),
                        Field("campaign_budget.amount_micros", "budget"),
                        Field("campaign.target_cpa.target_cpa_micros",
                              "target_cpa"),
                    ],
                    level=TargetLevel.CAMPAIGN)
    expected_sql = """
    SELECT
        campaign.id AS campaign_id,
        metrics.impressions AS impressions,
        campaign_budget.amount_micros AS budget,
        campaign.target_cpa.target_cpa_micros AS target_cpa
    FROM campaign
    WHERE segments.date DURING TODAY
    """
    assert_sql_functionally_equivalent(target.query, expected_sql)


@pytest.mark.parametrize(
    'target1, target2, expected',
    [
        (
            Target(),
            Target(),
            True
        ),
        (
            Target(name='target1', metrics='clicks,conversions'),
            Target(name='target2', metrics='clicks,conversions'),
            True
        ),
        (
            Target(name='target1', metrics='clicks,conversions'),
            Target(name='target2', dimensions='clicks,conversions'),
            False
        ),
        (
            Target(metrics='clicks,conversions'),
            Target(metrics=[Field(name='clicks'), Field(name='conversions')]),
            True
        ),
        (
            Target(metrics='conversions,impressions'),
            Target(metrics=[
                Field(name='impressions'), Field(name='conversions')]),
            True
        ),
        (
            Target(
                metrics=[Field(name='conversions'),
                         Field(name='impressions', alias='imp')]),
            Target(
                metrics=[Field(name='impressions', alias='imp'),
                         Field(name='conversions')]),
            True
        ),
        (
            Target(
                metrics=[
                    Field(
                        name='conversions',
                        customizer=Customizer(
                            CustomizerTypeEnum.INDEX, '0')),
                    Field(name='impressions', alias='imp')]),
            Target(
                metrics=[
                    Field(name='impressions', alias='imp'),
                    Field(
                        name='conversions',
                        customizer=Customizer(
                            CustomizerTypeEnum.INDEX, '0'))]
            ),
            True
        ),
        (
            Target(
                metrics=[
                    Field(
                        name='conversions',
                        customizer=Customizer(
                            CustomizerTypeEnum.INDEX, '0')),
                    Field(name='impressions', alias='imp')],
                dimensions=[Field(name='cost * 1e6', alias='cost')]),
            Target(
                metrics=[
                    Field(name='impressions', alias='imp'),
                    Field(
                        name='conversions',
                        customizer=Customizer(
                            CustomizerTypeEnum.INDEX, '0'))],
                dimensions=[Field(name='cost*1e6', alias='cost')]
            ),
            True
        ),
    ]
)
def test_targets_equality(target1, target2, expected):
    actual_equality = target1 == target2
    actual_hash_equality = hash(target1) == hash(target2)
    assert actual_equality == expected
    assert actual_hash_equality == expected


@pytest.mark.parametrize(
    'target1, target2, expected_similarity, expected_equality',
    [
        (
            Target(name='target1', metrics='clicks,conversions',
                   level=TargetLevel.AD_GROUP),
            Target(name='target2', metrics='clicks,conversions',
                   level=TargetLevel.AD_GROUP_AD),
            True,
            False
        ),
    ]
)
def test_target_similarity(
        target1, target2, expected_similarity, expected_equality):
    actual_similarity = target1.is_similar(target2)
    actual_equality = target1 == target2
    assert actual_similarity == expected_similarity
    assert actual_equality == expected_equality


@pytest.mark.parametrize(
    'targets,expected',
    [
        (
            [Target(name='target1', metrics='clicks,conversions',
                    level=TargetLevel.CUSTOMER),
             Target(name='target2', metrics='clicks,conversions',
                    level=TargetLevel.AD_GROUP),
             Target(name='target3', metrics='clicks,conversions',
                    level=TargetLevel.AD_GROUP_AD),
             Target(name='target4', metrics='clicks,conversions,impressions',
                    level=TargetLevel.MCC)
             ],
            ['target3', 'target4']
        ),
    ]
)
def test_targets_similarity_check(targets, expected):
    actual = targets_similarity_check(targets)
    assert set([t.name for t in actual]) == set(expected)
