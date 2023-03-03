#!/bin/bash

# Copyright 2022 Google LLC
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

while :; do
case $1 in
	-n|--network)
		shift
		network=$1
		;;
	-g|--google-ads-config)
		shift
		ads_config=$1
		;;
	*)
		break
	esac
	shift
done

current_dir=$(dirname $(readlink -f $0))
docker run --network="${network:-host}" \
	-v ${ads_config:-$HOME/google-ads.yaml}:/app/google-ads.yaml \
	-v "${current_dir}/../src/gaarf_exporter.yaml:/app/gaarf_exporter.yaml" \
	-v "${current_dir}/../src/custom_callbacks.py:/app/custom_callbacks.py" \
	gaarf_exporter
