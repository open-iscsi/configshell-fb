#! /usr/bin/env python
'''
This file is part of ConfigShell.
Copyright (c) 2011-2013 by Datera, Inc

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.
'''

import os
import re
from setuptools import setup

# Get version without importing.
init_file_path = os.path.join(os.path.dirname(__file__), 'configshell/__init__.py')

with open(init_file_path) as f:
    for line in f:
        match = re.match(r"__version__.*'([0-9.]+)'", line)
        if match:
            version = match.group(1)
            break
    else:
        raise Exception("Couldn't find version in setup.py")

setup(
    name = 'configshell-fb',
    version = '1.1.28',
    description = 'A framework to implement simple but nice CLIs.',
    license = 'Apache 2.0',
    maintainer = 'Andy Grover',
    maintainer_email = 'agrover@redhat.com',
    url = 'http://github.com/open-iscsi/configshell-fb',
    packages = ['configshell', 'configshell_fb'],
    install_requires = [
        'pyparsing >= 2.0.2',
        'six',
        'urwid',
    ],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],
    )
