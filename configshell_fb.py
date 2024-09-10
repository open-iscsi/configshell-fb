# Providing backwards compatibility for modules importing 'configshell_fb'

from configshell import Console, Log, ConfigNode, ExecutionError, Prefs, ConfigShell

__all__ = [
    'Console',
    'Log',
    'ConfigNode',
    'ExecutionError',
    'Prefs',
    'ConfigShell',
]
