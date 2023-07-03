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

import pytest

from gaarf_exporter.target import Target, TargetLevel, ServiceTarget
from gaarf_exporter.query_elements import Field, Customizer, CustomizerTypeEnum


@pytest.fixture
def simple_target():
    return Target(name='simple',
                  metrics="impressions",
                  level=TargetLevel.AD_GROUP)


@pytest.fixture
def simple_target_at_customer_level():
    return Target(name='simple_customer_level',
                  metrics="impressions",
                  level=TargetLevel.CUSTOMER)


@pytest.fixture
def simple_target_at_mcc_level():
    return Target(name='simple_mcc_level',
                  metrics="impressions",
                  level=TargetLevel.MCC)


@pytest.fixture
def simple_target_at_ad_group_ad_level():
    return Target(name='simple_ad_group_ad_level',
                  metrics="impressions",
                  level=TargetLevel.AD_GROUP_AD)


@pytest.fixture
def complex_target():
    return Target(metrics="impressions,clicks",
                  level=TargetLevel.AD_GROUP,
                  dimensions=[
                      Field(name="segments.conversion_action",
                            alias="conversion_id",
                            customizer=Customizer(CustomizerTypeEnum.INDEX,
                                                  '0')),
                      Field(name="search_terms_view.search_term",
                            alias='search_term')
                  ])


@pytest.fixture
def no_metric_target():
    return ServiceTarget(
        name='mapping',
        metrics=[Field(name='1', alias='info')],
        dimensions=[
            Field(name='ad_group.id', alias='ad_group_id'),
            Field(name='ad_group.name', alias='ad_group_name'),
            Field(name='campaign.id', alias='campaign_id'),
            Field(name='campaign.name', alias='campaign_name'),
            Field(name='customer.id', alias='customer_id'),
            Field(name='customer.descriptive_name', alias='account_name'),
        ],
        # level = config.lowest_target_level,
        filters=(f"ad_group.status = 'ENABLED'"
                 f" AND campaign.status = 'ENABLED'"
                 f" AND customer.status = 'ENABLED'"))


@pytest.fixture
def complex_target_with_virtual_column():
    return Target(metrics=[
        Field(name='impressions'),
        Field(name='clicks'),
        Field(name='cost_micros * 1e6', alias='cost'),
        Field(name='clicks / impressions', alias='ctr'),
        Field(name='var1-var2/(1.05e3+var3)*100.5', alias='vc')
    ],
                  level=TargetLevel.AD_GROUP,
                  dimensions=[
                      Field(name="segments.conversion_action",
                            alias="conversion_id",
                            customizer=Customizer(CustomizerTypeEnum.INDEX,
                                                  '0')),
                      Field(name="search_terms_view.search_term",
                            alias='search_term')
                  ])


@pytest.fixture()
def empty_metric_target():
    return Target(
            name='disapproval',
            level=TargetLevel.AD_GROUP_AD,
            dimensions=[Field("campaign.id", "campaign_id"),
                        Field("ad_group_ad.policy_summary.approval_status",
                              "approval_status"),
                        Field("ad_group_ad.policy_summary.review_status",
                              "review_status")],
            filters=(
              f"campaign.status = 'ENABLED'"
              f" AND ad_group.status = 'ENABLED'"
              f" AND ad_group_ad.status = 'ENABLED'"
              f" AND ad_group_ad.policy_summary.approval_status != 'APPROVED'"))
