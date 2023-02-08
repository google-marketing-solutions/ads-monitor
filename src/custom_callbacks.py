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
# See the License for the specific language governing permissions and limitations under the License.

from typing import Dict
from dataclasses import dataclass
from collections import defaultdict
import yaml
from importlib import import_module
from gaarf.report import GaarfReport


def approvals_callback(approvals: GaarfReport) -> GaarfReport:

    @dataclass(frozen=True)
    class CampaignApprovalInfo:
        campaign_id: int
        approval_status: str
        review_status: str

    approvals_dict: Dict[CampaignApprovalInfo, int] = defaultdict(lambda: 0)
    for r in approvals:
        approvals_dict[CampaignApprovalInfo(r.campaign_id, r.approval_status,
                                            r.review_status)] += 1
    results = []
    for key, value in approvals_dict.items():
        results.append(
            (key.campaign_id, key.approval_status, key.review_status, value))
    return GaarfReport(results=results, column_names=approvals.column_names)
