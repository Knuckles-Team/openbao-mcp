"""CONCEPT:ECO-4.0 Unified ecosystem initialization dynamic check."""

import importlib
import inspect
from typing import Any

__version__ = "0.18.0"
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

_loaded_optional_modules = {}


def _import_module_safely(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def __getattr__(name: str) -> Any:
    if name == "_MCP_AVAILABLE":
        mcp_key = next((k for k in OPTIONAL_MODULES if "mcp_server" in k), None)
        return _import_module_safely(mcp_key) is not None if mcp_key else False
    if name == "_AGENT_AVAILABLE":
        agent_key = next((k for k in OPTIONAL_MODULES if "agent_server" in k), None)
        return _import_module_safely(agent_key) is not None if agent_key else False

    for module_name in OPTIONAL_MODULES:
        if module_name not in _loaded_optional_modules:
            module = _import_module_safely(module_name)
            if module is not None:
                _loaded_optional_modules[module_name] = module
                _expose_members(module)

        module = _loaded_optional_modules.get(module_name)
        if module is not None and hasattr(module, name):
            return getattr(module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
