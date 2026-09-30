'''
Deprecated alias of the configshell package.

The configshell_fb module has been renamed to configshell. This module
only keeps existing "import configshell_fb" code working, new code should
import configshell instead.

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

import importlib
import pkgutil
import sys
import warnings

import configshell

warnings.warn(
    "The 'configshell_fb' module is deprecated, import 'configshell' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Alias configshell_fb and all of its submodules to the configshell module
# objects, so that classes and exceptions are shared, e.g. an ExecutionError
# raised by configshell is caught by "except configshell_fb.ExecutionError".
for _module in pkgutil.iter_modules(configshell.__path__):
    sys.modules[f"{__name__}.{_module.name}"] = \
        importlib.import_module(f"configshell.{_module.name}")
sys.modules[__name__] = configshell
