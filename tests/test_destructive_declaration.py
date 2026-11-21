"""CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R005: destructive tools are declared destructive."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec("CONN-OPENBAO-MCP-CONNECTOR-CONTENT-R005")

MCP = Path(__file__).resolve().parents[1] / "openbao_mcp" / "mcp"
DESTRUCTIVE_TOOLS = {
    "openbao_auth_token_revoke": "mcp_auth.py",
    "openbao_kv1_delete": "mcp_secrets.py",
    "openbao_kv2_delete": "mcp_secrets.py",
    "openbao_logical_delete": "mcp_secrets.py",
}


def _declares_destructive(node: ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        for sub in ast.walk(decorator):
            if isinstance(sub, ast.Dict):
                for key, value in zip(sub.keys, sub.values, strict=True):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "destructiveHint"
                        and isinstance(value, ast.Constant)
                        and value.value is True
                    ):
                        return True
    return False


def test_destructive_tools_declare_the_destructive_hint() -> None:
    for name, module in DESTRUCTIVE_TOOLS.items():
        tree = ast.parse((MCP / module).read_text())
        found = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == name
        ]
        assert found, f"{name} is not registered in {module}"
        assert _declares_destructive(found[0]), f"{name} is not declared destructive"
