"""Identity-scoped mount auto-load (CONCEPT:AU-OS.identity.identity-scoped-resource-autoload).

The caller's entitled OpenBao secret-engine mounts auto-load in ``get_mounts``,
covering both the modern ``{"data": {...}}`` envelope and the legacy
top-level-keyed response. Tests the filtering logic with the entitlement
source mocked (the resolver itself is tested in agent-utilities).
"""

from openbao_mcp.api import api_client_sys
from openbao_mcp.api.api_client_sys import Api


def _client(monkeypatch, entitled):
    monkeypatch.setattr(
        api_client_sys,
        "_entitled",
        lambda namespace, names: [n for n in names if n in entitled],
    )
    api = object.__new__(Api)  # bypass ApiClientBase.__init__ (no network)
    return api


def test_get_mounts_filters_data_envelope(monkeypatch):
    api = _client(monkeypatch, {"secret/"})
    monkeypatch.setattr(
        api,
        "request",
        lambda *a, **k: {
            "data": {
                "secret/": {"type": "kv"},
                "cubbyhole/": {"type": "cubbyhole"},
            },
            "request_id": "abc",
        },
    )
    result = api.get_mounts()
    assert set(result["data"].keys()) == {"secret/"}
    assert result["request_id"] == "abc"


def test_get_mounts_filters_legacy_top_level(monkeypatch):
    api = _client(monkeypatch, {"secret/"})
    monkeypatch.setattr(
        api,
        "request",
        lambda *a, **k: {
            "secret/": {"type": "kv"},
            "cubbyhole/": {"type": "cubbyhole"},
            "request_id": "abc",
        },
    )
    result = api.get_mounts()
    assert "secret/" in result
    assert "cubbyhole/" not in result
    assert result["request_id"] == "abc"


def test_get_mounts_no_denial_returns_unchanged(monkeypatch):
    api = _client(monkeypatch, {"secret/", "cubbyhole/"})
    raw = {"data": {"secret/": {"type": "kv"}, "cubbyhole/": {"type": "cubbyhole"}}}
    monkeypatch.setattr(api, "request", lambda *a, **k: raw)
    assert api.get_mounts() == raw


def test_missing_resolver_degrades_to_full_list(monkeypatch):
    """A broken/absent import of the shared resolver fails open to the full list."""
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "agent_utilities.security.entitlements":
            raise ImportError("simulated: resolver not available")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)
    assert api_client_sys._entitled("mount", ["a", "b"]) == ["a", "b"]
