from unittest.mock import MagicMock

import pytest

from openbao_mcp.api.api_client_full import (
    CheckHCLKeys,
    DefaultRetryPolicy,
    IsSudoPath,
    LookupBaoVariable,
    ReadBaoVariable,
    SudoPaths,
    VaultPluginTLSProvider,
    VaultPluginTLSProviderContext,
)
from openbao_mcp.api_client import Api


@pytest.mark.concept("BAO-001")
def test_api_client_basic_mock(mock_ctx):
    """CONCEPT:BAO-001 Test basic mock initialization of client facade."""
    assert mock_ctx is not None
    assert hasattr(mock_ctx, "info")


@pytest.mark.concept("BAO-001")
def test_api_client_endpoints(mock_ctx):
    """CONCEPT:BAO-001 Verify endpoint configuration on dynamic client."""
    from openbao_mcp.auth import get_client

    client = get_client()
    assert client is not None
    assert hasattr(client, "request")


@pytest.mark.concept("BAO-001")
def test_global_utility_functions(monkeypatch):
    # IsSudoPath / SudoPaths
    assert IsSudoPath("sys/auth") is True
    assert IsSudoPath("secret/data") is False
    assert len(SudoPaths()) > 0

    # LookupBaoVariable / ReadBaoVariable
    monkeypatch.setenv("BAO_VAR_TEST", "value123")
    val, found = LookupBaoVariable("BAO_VAR_TEST")
    assert found is True
    assert val == "value123"
    assert ReadBaoVariable("BAO_VAR_TEST") == "value123"

    # DefaultRetryPolicy
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    should_retry, err = DefaultRetryPolicy(None, mock_resp, None)
    assert should_retry is True

    mock_resp.status_code = 200
    should_retry, err = DefaultRetryPolicy(None, mock_resp, None)
    assert should_retry is False

    # CheckHCLKeys
    # Should not throw for valid / no keys
    assert CheckHCLKeys(None, ["key1"]) is None

    # TLS Providers
    tls_prov = VaultPluginTLSProvider(None)
    assert callable(tls_prov)
    tls_prov_ctx = VaultPluginTLSProviderContext(None, None)
    assert callable(tls_prov_ctx)


@pytest.mark.concept("BAO-001")
def test_full_logical_and_kv_apis():
    client = Api(base_url="http://localhost:8200")
    client.request = MagicMock(return_value={"data": "mocked"})  # type: ignore

    # Logical API
    client.Logical().Read("secret/foo")
    client.request.assert_called_with("GET", "/v1/secret/foo")

    client.Logical().Write("secret/foo", {"bar": "baz"})
    client.request.assert_called_with("POST", "/v1/secret/foo", data={"bar": "baz"})

    client.Logical().Delete("secret/foo")
    client.request.assert_called_with("DELETE", "/v1/secret/foo")

    client.Logical().List("secret/foo")
    client.request.assert_called_with("LIST", "/v1/secret/foo")

    client.Logical().Unwrap("some-token")
    client.request.assert_called_with(
        "POST", "/v1/sys/wrapping/unwrap", headers={"X-Vault-Token": "some-token"}
    )

    client.Logical().WriteBytes("secret/raw", b'{"a": 1}')
    client.request.assert_called_with("POST", "/v1/secret/raw", data={"a": 1})

    # KVv2 API
    client.KVv2("custom_secret").Get(None, "foo")
    client.request.assert_called_with("GET", "/v1/custom_secret/data/foo")

    client.KVv2("custom_secret").Put(None, "foo", {"data": {"a": 1}})
    client.request.assert_called_with(
        "POST", "/v1/custom_secret/data/foo", data={"data": {"data": {"a": 1}}}
    )

    client.KVv2("custom_secret").Delete(None, "foo")
    client.request.assert_called_with("DELETE", "/v1/custom_secret/data/foo")

    client.KVv2("custom_secret").Patch(None, "foo", {"data": {"b": 2}})
    client.request.assert_called_with(
        "PATCH", "/v1/custom_secret/data/foo", data={"data": {"data": {"b": 2}}}
    )

    # KVv1 API
    client.KVv1("custom_secret").Get(None, "foo")
    client.request.assert_called_with("GET", "/v1/custom_secret/foo")

    client.KVv1("custom_secret").Put(None, "foo", {"a": 1})
    client.request.assert_called_with("POST", "/v1/custom_secret/foo", data={"a": 1})

    client.KVv1("custom_secret").Delete(None, "foo")
    client.request.assert_called_with("DELETE", "/v1/custom_secret/foo")


@pytest.mark.concept("BAO-001")
def test_full_sys_auth_and_ssh_apis():
    client = Api(base_url="http://localhost:8200")
    client.request = MagicMock(return_value={"data": "mocked"})  # type: ignore

    # Sys API
    client.Sys().Init({"secret_shares": 5})
    client.request.assert_called_with("PUT", "/v1/sys/init", data={"secret_shares": 5})

    client.Sys().InitStatus()
    client.request.assert_called_with("GET", "/v1/sys/init")

    client.Sys().Seal()
    client.request.assert_called_with("PUT", "/v1/sys/seal")

    client.Sys().Unseal("shard-123")
    client.request.assert_called_with(
        "PUT", "/v1/sys/unseal", data={"key": "shard-123"}
    )

    client.Sys().SealStatus()
    client.request.assert_called_with("GET", "/v1/sys/seal-status")

    client.Sys().Health()
    client.request.assert_called_with("GET", "/v1/sys/health")

    client.Sys().Leader()
    client.request.assert_called_with("GET", "/v1/sys/leader")

    client.Sys().HAStatus()
    client.request.assert_called_with("GET", "/v1/sys/ha-status")

    client.Sys().RaftJoin({"leader_api_addr": "http://127.0.0.1:8200"})
    client.request.assert_called_with(
        "POST",
        "/v1/sys/storage/raft/join",
        data={"leader_api_addr": "http://127.0.0.1:8200"},
    )

    client.Sys().RaftAutopilotState()
    client.request.assert_called_with("GET", "/v1/sys/storage/raft/autopilot/state")

    # Auth and Token API
    # Login Method
    class MockMethod:
        mount = "auth/userpass"
        data = {"username": "foo", "password": "bar"}

    client.Auth().Login(None, MockMethod())
    client.request.assert_called_with(
        "POST", "v1/auth/userpass/login", data={"username": "foo", "password": "bar"}
    )

    # MFALogin Method
    client.Auth().MFALogin(None, MockMethod(), "mfa-cred-1", "mfa-cred-2")
    client.request.assert_called_with(
        "POST",
        "v1/auth/userpass/login",
        data={
            "username": "foo",
            "password": "bar",
            "mfa_creds": ["mfa-cred-1", "mfa-cred-2"],
        },
    )

    # MFAValidate Method
    client.Auth().MFAValidate(None, "mfa-secret-123", {"passcode": "123456"})
    client.request.assert_called_with(
        "POST", "/v1/sys/mfa/validate", data={"passcode": "123456"}
    )

    # TokenAuth API
    client.Auth().Token().Create({"id": "custom-token"})
    client.request.assert_called_with(
        "POST", "/v1/auth/token/create", data={"id": "custom-token"}
    )

    client.Auth().Token().Lookup("token-123")
    client.request.assert_called_with(
        "POST", "/v1/auth/token/lookup", data={"token": "token-123"}
    )

    client.Auth().Token().Renew("token-123", 3600)
    client.request.assert_called_with(
        "POST", "/v1/auth/token/renew", data={"token": "token-123", "increment": 3600}
    )

    client.Auth().Token().RevokeTree("token-123")
    client.request.assert_called_with(
        "POST", "/v1/auth/token/revoke", data={"token": "token-123"}
    )

    # SSH API
    client.SSH().Credential("my-role", {"ip": "127.0.0.1"})
    client.request.assert_called_with(
        "POST", "/v1/ssh/creds/my-role", data={"ip": "127.0.0.1"}
    )

    client.SSH().SignKey("my-role", {"public_key": "ssh-rsa ..."})
    client.request.assert_called_with(
        "POST", "/v1/ssh/sign/my-role", data={"public_key": "ssh-rsa ..."}
    )

    # SSH Helper API
    client.SSHHelper().Verify("my-otp")
    client.request.assert_called_with("POST", "/v1/ssh/verify", data={"otp": "my-otp"})
