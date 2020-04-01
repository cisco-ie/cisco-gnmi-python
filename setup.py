#!/usr/bin/env python
"""Copyright 2020 Cisco Systems
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

 * Redistributions of source code must retain the above copyright
 notice, this list of conditions and the following disclaimer.

The contents of this file are licensed under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
"""

"""Derived from Flask
https://github.com/pallets/flask/blob/master/setup.py
"""

import io
import re

from setuptools import find_packages
from setuptools import setup

with io.open("README.md", "rt", encoding="utf8") as f:
    readme = f.read()

with io.open("src/cisco_gnmi/__init__.py", "rt", encoding="utf8") as f:
    version = re.search(r'__version__ = "(.*?)"', f.read()).group(1)

setup(
    name="cisco_gnmi",
    version=version,
    url="https://github.com/cisco-ie/cisco-gnmi-python",
    project_urls={
        "Code": "https://github.com/cisco-ie/cisco-gnmi-python",
        "Issue Tracker": "https://github.com/cisco-ie/cisco-gnmi-python/issues",
    },
    license="Apache License (2.0)",
    author="Cisco Innovation Edge",
    author_email="cisco-ie@cisco.com",
    maintainer="Cisco Innovation Edge",
    maintainer_email="cisco-ie@cisco.com",
    description="This library wraps gNMI functionality to ease usage with Cisco implementations.",
    long_description=readme,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: System :: Networking",
        "Topic :: System :: Networking :: Monitoring",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4",
    install_requires=[
        "grpcio",
        "protobuf",
        "six",
        "cryptography",
    ],
    extras_require={
        "dev": [
            "grpcio-tools",
            "googleapis-common-protos",
            "pylint",
            "twine",
            "setuptools",
            "wheel",
            "pytest",
            "pytest-cov",
            "pytest-mock",
            "coverage",
        ],
    },
    entry_points={"console_scripts": ["cisco-gnmi = cisco_gnmi.cli:main"]},
)
