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

import pathlib
from setuptools import setup, find_packages


HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="gaarf-exporter",
    version="0.2.1",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Google Inc. (gTech gPS CSE team)",
    author_email="no-reply@google.com",
    license="Apache 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache Software License"
    ],
    packages=find_packages(),
    install_requires=[
        "prometheus-client", "google-ads-api-report-fetcher>=1.9.0"
    ],
    setup_requires=["pytest-runner"],
    tests_requires=["pytest"],
    entry_points={
        "console_scripts": [
            "gaarf-exporter=gaarf_exporter.main:main",
        ]
    })
