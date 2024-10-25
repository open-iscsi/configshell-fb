"""
configshell_fb.py - Backwards compatibility module for configshell

This module provides backwards compatibility for code that imports 'configshell_fb'.
It re-exports all public names from the 'configshell' module.

Usage:
    from configshell_fb import ConfigNode, Log, Console  # etc.

Note: This compatibility layer may be deprecated in future versions.
Please consider updating your imports to use 'configshell' directly.
"""

import configshell
from configshell import *  # noqa: F403

# Explicitly import and re-export submodules
from configshell import console, log, node, prefs, shell  # noqa: F401

# Re-export all public names from configshell
__all__ = configshell.__all__
