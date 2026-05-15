"""Plugin registry for JARVIS Cowork.

Provides a simple in-memory registry and dynamic loader for plugin modules under backend.plugins
"""
from typing import Dict, Any
import importlib

_plugins: Dict[str, Dict[str, Any]] = {}


def register(name: str, metadata: Dict[str, Any]) -> None:
    _plugins[name] = metadata


def list_plugins() -> Dict[str, Dict[str, Any]]:
    return dict(_plugins)


def load_plugin(module_name: str) -> bool:
    """Dynamically import a plugin module and call its optional setup() function."""
    m = importlib.import_module(module_name)
    if hasattr(m, 'setup'):
        m.setup()
    _plugins[module_name] = {'module': module_name}
    return True


def unload_plugin(name: str) -> bool:
    return _plugins.pop(name, None) is not None
