"""CONCEPT:AU-ECO.messaging.native-backend-abstraction Unified ecosystem initialization dynamic check."""

import importlib
import inspect
from typing import Any

__version__ = "2.1.0"
__all__: list[str] = []

CORE_MODULES = ["openbao_mcp.api_client"]
OPTIONAL_MODULES = {
    "openbao_mcp.agent_server": "agent",
    "openbao_mcp.mcp_server": "mcp",
}


def _expose_members(module):
    for name, obj in inspect.getmembers(module):
        if (inspect.isclass(obj) or inspect.isfunction(obj)) and not name.startswith(
            "_"
        ):
            globals()[name] = obj
            if name not in __all__:
                __all__.append(name)


for module_name in CORE_MODULES:
    module = importlib.import_module(module_name)
    _expose_members(module)

_loaded_optional_modules: dict[str, Any] = {}


def _import_module_safely(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def _optional_module_importable(name_fragment: str) -> bool:
    """Whether the optional module whose name contains `name_fragment` imports cleanly."""
    module_name = next((k for k in OPTIONAL_MODULES if name_fragment in k), None)
    return module_name is not None and _import_module_safely(module_name) is not None


def _load_optional_module(module_name: str):
    if module_name not in _loaded_optional_modules:
        module = _import_module_safely(module_name)
        if module is not None:
            _loaded_optional_modules[module_name] = module
            _expose_members(module)
    return _loaded_optional_modules.get(module_name)


def _resolve_from_optional_modules(name: str) -> Any:
    for module_name in OPTIONAL_MODULES:
        module = _load_optional_module(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __getattr__(name: str) -> Any:
    if name == "_MCP_AVAILABLE":
        return _optional_module_importable("mcp_server")
    if name == "_AGENT_AVAILABLE":
        return _optional_module_importable("agent_server")
    return _resolve_from_optional_modules(name)


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
