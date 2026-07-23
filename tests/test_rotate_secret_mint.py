"""Regression tests for rotate_secret.py's in-house OpenBao token minting.

Loads ``skills/secret-vault-manager/scripts/rotate_secret.py`` by path (same
pattern as test_rotation_lib.py) and exercises the mint-decision logic
without any live kubectl/cluster/OpenBao access -- ``mint_openbao_token`` is
monkeypatched so no subprocess is ever spawned. This pins:

  - OPENBAO_TOKEN (registered in AUTO_MINTABLE) auto-mints via the in-house
    path instead of refusing.
  - Anything NOT registered (e.g. MATTERMOST_TOKEN, a Keycloak client
    secret) still returns None -- the hard refusal in cmd_execute is
    unchanged for credential types this tool has no verified mint path for.
  - The safe description returned alongside the minted value never contains
    the value itself.
  - mint_openbao_token is invoked with exactly the policy/ttl registered for
    that credential (least-privilege: OPENBAO_TOKEN mints agent-apps-rw
    tokens, never anything broader).
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "openbao_mcp"
    / "skills"
    / "secret-vault-manager"
    / "scripts"
    / "rotate_secret.py"
)

_spec = importlib.util.spec_from_file_location("rotate_secret", _SCRIPT)
rs = importlib.util.module_from_spec(_spec)
sys.modules["rotate_secret"] = rs
_spec.loader.exec_module(rs)


def test_auto_mintable_registry_is_least_privilege():
    # Only OpenBao's own token type is auto-mintable, and only with the
    # agent-apps-rw policy -- never anything broader (e.g. never "root").
    assert set(rs.AUTO_MINTABLE.keys()) == {"OPENBAO_TOKEN"}
    policy, ttl = rs.AUTO_MINTABLE["OPENBAO_TOKEN"]
    assert policy == "agent-apps-rw"
    assert ttl


def test_mint_provider_value_returns_none_for_unregistered_credential():
    # Mattermost tokens have no in-house mint path -- must fall back to the
    # existing refusal, never silently invent something.
    assert rs.mint_provider_value("MATTERMOST_TOKEN") is None
    assert rs.mint_provider_value("SOME_OTHER_CLIENT_SECRET") is None


def test_mint_provider_value_auto_mints_openbao_token(monkeypatch):
    calls = []

    def fake_mint(policy, ttl):
        calls.append((policy, ttl))
        return "FAKE-TOKEN-VALUE-NEVER-LOGGED", "acc-123"

    monkeypatch.setattr(rs, "mint_openbao_token", fake_mint)

    result = rs.mint_provider_value("OPENBAO_TOKEN")
    assert result is not None
    new_value, description = result

    assert new_value == "FAKE-TOKEN-VALUE-NEVER-LOGGED"
    assert calls == [("agent-apps-rw", "768h")]

    # The safe description must never leak the minted value itself.
    assert "FAKE-TOKEN-VALUE-NEVER-LOGGED" not in description
    assert "acc-123" in description
    assert "agent-apps-rw" in description


def test_mint_openbao_token_raises_on_helper_error(monkeypatch):
    class FakeCompletedProcess:
        stdout = '{"error": "OPENBAO_ADMIN_TOKEN not set on this pod"}\n'

    def fake_run(*args, **kwargs):
        return FakeCompletedProcess()

    monkeypatch.setattr(rs.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="OPENBAO_ADMIN_TOKEN not set"):
        rs.mint_openbao_token("agent-apps-rw", "768h")


def test_mint_openbao_token_returns_token_and_accessor_on_success(monkeypatch):
    class FakeCompletedProcess:
        stdout = '{"client_token": "s.abcdefghijklmnop", "accessor": "acc-999"}\n'

    def fake_run(*args, **kwargs):
        return FakeCompletedProcess()

    monkeypatch.setattr(rs.subprocess, "run", fake_run)

    token, accessor = rs.mint_openbao_token("agent-apps-rw", "768h")
    assert token == "s.abcdefghijklmnop"
    assert accessor == "acc-999"
