"""Go-equivalent OpenBao API structures, utilities, and components for Python."""

import os
import re
from typing import Any

import requests
import requests.structures

from openbao_mcp.api.api_client_base import ApiClientBase


# Utilities
def CheckHCLKeys(node: Any, valid: list[str]) -> Any:
    return None


def DefaultRetryPolicy(ctx: Any, resp: Any, err: Any) -> tuple[bool, Any]:
    if err is not None:
        return True, err
    if resp is not None and getattr(resp, "status_code", 200) >= 500:
        return True, None
    return False, None


def SudoPaths() -> dict[str, re.Pattern]:
    return {"sys": re.compile(r"^sys/.*"), "auth": re.compile(r"^auth/.*")}


def IsSudoPath(path: str) -> bool:
    for pat in SudoPaths().values():
        if pat.match(path):
            return True
    return False


def LookupBaoVariable(name: str) -> tuple[str, bool]:
    val = os.getenv(name)
    return (val, True) if val is not None else ("", False)


def ReadBaoVariable(name: str) -> str:
    return os.getenv(name, "")


def VaultPluginTLSProvider(apiTLSConfig: Any) -> Any:
    return lambda: None


def VaultPluginTLSProviderContext(ctx: Any, apiTLSConfig: Any) -> Any:
    return lambda: None


class PluginType:
    @classmethod
    def ParsePluginType(cls, plugin_type: str) -> "PluginType":
        return cls()

    def String(self) -> str:
        return "database"


class OutputPolicyError(Exception):
    def HCLString(self) -> str:
        return ""


class OutputStringError(Exception):
    def CurlString(self) -> str:
        return ""


class AutopilotConfig:
    def MarshalJSON(self) -> bytes:
        return b"{}"

    def UnmarshalJSON(self, b: bytes) -> None:
        raise RuntimeError("Not implemented")


class KVOption:
    @classmethod
    def WithCheckAndSet(cls, cas: int) -> "KVOption":
        return cls()

    @classmethod
    def WithMergeMethod(cls, method: str) -> "KVOption":
        return cls()

    @classmethod
    def WithOption(cls, key: str, value: Any) -> "KVOption":
        return cls()


class Secret:
    @classmethod
    def ParseSecret(cls, r: Any) -> "Secret":
        return cls()

    def TokenAccessor(self) -> str:
        return ""

    def TokenID(self) -> str:
        return ""

    def TokenIsRenewable(self) -> bool:
        return True

    def TokenMetadata(self) -> dict[str, str]:
        return {}

    def TokenPolicies(self) -> list[str]:
        return []

    def TokenRemainingUses(self) -> int:
        return 0

    def TokenTTL(self) -> Any:
        return 0


class Request:
    def ResetJSONBody(self) -> None:
        raise RuntimeError("Not implemented")

    def SetJSONBody(self, val: Any) -> None:
        raise RuntimeError("Not implemented")

    def ToHTTP(self) -> Any:
        return None


class Response:
    def DecodeJSON(self, out: Any) -> None:
        raise RuntimeError("Not implemented")

    def Error(self) -> Any:
        return None


# Config
class Config:
    def __init__(self, address: str = "http://localhost:8200"):
        self.address = address
        self.tls_config = None

    @classmethod
    def DefaultConfig(cls) -> "Config":
        cfg = cls()
        cfg.ReadEnvironment()
        return cfg

    def ConfigureTLS(self, t: Any) -> None:
        self.tls_config = t

    def ParseAddress(self, address: str) -> Any:
        from urllib.parse import urlparse

        return urlparse(address)

    def ReadEnvironment(self) -> None:
        self.address = os.getenv("VAULT_ADDR") or os.getenv("BAO_ADDR") or self.address

    def TLSConfig(self) -> Any:
        return self.tls_config


# Components
class Logical:
    def __init__(self, client: "Client"):
        self.client = client

    def Delete(self, path: str) -> dict:
        return self.client.request("DELETE", f"/v1/{path}")

    def DeleteWithContext(self, ctx: Any, path: str) -> dict:
        return self.Delete(path)

    def DeleteWithData(self, path: str, data: dict) -> dict:
        return self.client.request("DELETE", f"/v1/{path}", data=data)

    def DeleteWithDataWithContext(self, ctx: Any, path: str, data: dict) -> dict:
        return self.DeleteWithData(path, data)

    def JSONMergePatch(self, ctx: Any, path: str, data: dict) -> dict:
        return self.client.request("PATCH", f"/v1/{path}", data=data)

    def List(self, path: str) -> dict:
        return self.client.request("LIST", f"/v1/{path}")

    def ListPage(self, path: str, after: str, limit: int) -> dict:
        return self.client.request(
            "LIST", f"/v1/{path}", params={"after": after, "limit": limit}
        )

    def ListPageWithContext(self, ctx: Any, path: str, after: str, limit: int) -> dict:
        return self.ListPage(path, after, limit)

    def ListWithContext(self, ctx: Any, path: str) -> dict:
        return self.List(path)

    def Read(self, path: str) -> dict:
        return self.client.request("GET", f"/v1/{path}")

    def ReadRaw(self, path: str) -> dict:
        return self.client.request("GET", f"/v1/{path}")

    def ReadRawWithContext(self, ctx: Any, path: str) -> dict:
        return self.ReadRaw(path)

    def ReadRawWithData(self, path: str, data: dict) -> dict:
        return self.client.request("GET", f"/v1/{path}", data=data)

    def ReadRawWithDataWithContext(self, ctx: Any, path: str, data: dict) -> dict:
        return self.ReadRawWithData(path, data)

    def ReadWithContext(self, ctx: Any, path: str) -> dict:
        return self.Read(path)

    def ReadWithData(self, path: str, data: dict) -> dict:
        return self.client.request("GET", f"/v1/{path}", data=data)

    def ReadWithDataWithContext(self, ctx: Any, path: str, data: dict) -> dict:
        return self.ReadWithData(path, data)

    def Unwrap(self, wrapping_token: str) -> dict:
        return self.client.request(
            "POST", "/v1/sys/wrapping/unwrap", headers={"X-Vault-Token": wrapping_token}
        )

    def UnwrapWithContext(self, ctx: Any, wrapping_token: str) -> dict:
        return self.Unwrap(wrapping_token)

    def Write(self, path: str, data: dict) -> dict:
        return self.client.request("POST", f"/v1/{path}", data=data)

    def WriteBytes(self, path: str, data: bytes) -> dict:
        import json

        payload = json.loads(data.decode("utf-8")) if data else {}
        return self.Write(path, payload)

    def WriteBytesWithContext(self, ctx: Any, path: str, data: bytes) -> dict:
        return self.WriteBytes(path, data)

    def WriteWithContext(self, ctx: Any, path: str, data: dict) -> dict:
        return self.Write(path, data)


class KVv1:
    def __init__(self, client: "Client", mount_path: str):
        self.client = client
        self.mount_path = mount_path.strip("/")

    def Delete(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/{secret_path.lstrip('/')}"
        return self.client.request("DELETE", f"/v1/{path}")

    def Get(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/{secret_path.lstrip('/')}"
        return self.client.request("GET", f"/v1/{path}")

    def Put(self, ctx: Any, secret_path: str, data: dict) -> dict:
        path = f"{self.mount_path}/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data=data)


class KVv2:
    def __init__(self, client: "Client", mount_path: str):
        self.client = client
        self.mount_path = mount_path.strip("/")

    def Delete(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/data/{secret_path.lstrip('/')}"
        return self.client.request("DELETE", f"/v1/{path}")

    def DeleteMetadata(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/metadata/{secret_path.lstrip('/')}"
        return self.client.request("DELETE", f"/v1/{path}")

    def DeleteVersions(self, ctx: Any, secret_path: str, versions: list[int]) -> dict:
        path = f"{self.mount_path}/delete/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data={"versions": versions})

    def Destroy(self, ctx: Any, secret_path: str, versions: list[int]) -> dict:
        path = f"{self.mount_path}/destroy/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data={"versions": versions})

    def Get(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/data/{secret_path.lstrip('/')}"
        return self.client.request("GET", f"/v1/{path}")

    def GetMetadata(self, ctx: Any, secret_path: str) -> dict:
        path = f"{self.mount_path}/metadata/{secret_path.lstrip('/')}"
        return self.client.request("GET", f"/v1/{path}")

    def GetVersion(self, ctx: Any, secret_path: str, version: int) -> dict:
        path = f"{self.mount_path}/data/{secret_path.lstrip('/')}"
        return self.client.request("GET", f"/v1/{path}", params={"version": version})

    def GetVersionsAsList(self, ctx: Any, secret_path: str) -> list:
        metadata = self.GetMetadata(ctx, secret_path)
        return metadata.get("data", {}).get("versions", [])

    def Patch(self, ctx: Any, secret_path: str, new_data: dict) -> dict:
        path = f"{self.mount_path}/data/{secret_path.lstrip('/')}"
        return self.client.request("PATCH", f"/v1/{path}", data={"data": new_data})

    def PatchMetadata(self, ctx: Any, secret_path: str, metadata: dict) -> dict:
        path = f"{self.mount_path}/metadata/{secret_path.lstrip('/')}"
        return self.client.request("PATCH", f"/v1/{path}", data=metadata)

    def Put(self, ctx: Any, secret_path: str, data: dict) -> dict:
        path = f"{self.mount_path}/data/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data={"data": data})

    def PutMetadata(self, ctx: Any, secret_path: str, metadata: dict) -> dict:
        path = f"{self.mount_path}/metadata/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data=metadata)

    def Rollback(self, ctx: Any, secret_path: str, to_version: int) -> dict:
        secret = self.GetVersion(ctx, secret_path, to_version)
        data = secret.get("data", {}).get("data", {})
        return self.Put(ctx, secret_path, data)

    def Undelete(self, ctx: Any, secret_path: str, versions: list[int]) -> dict:
        path = f"{self.mount_path}/undelete/{secret_path.lstrip('/')}"
        return self.client.request("POST", f"/v1/{path}", data={"versions": versions})


class LifetimeWatcher:
    def __init__(self, client: "Client", input_data: Any):
        self.client = client
        self.input_data = input_data

    def DoneCh(self) -> Any:
        return None

    def Renew(self) -> None:
        raise RuntimeError("Not implemented")

    def RenewCh(self) -> Any:
        return None

    def Start(self) -> None:
        raise RuntimeError("Not implemented")

    def Stop(self) -> None:
        raise RuntimeError("Not implemented")


class TokenAuth:
    def __init__(self, client: "Client"):
        self.client = client

    def Create(self, opts: dict) -> dict:
        return self.client.request("POST", "/v1/auth/token/create", data=opts)

    def CreateOrphan(self, opts: dict) -> dict:
        return self.client.request("POST", "/v1/auth/token/create-orphan", data=opts)

    def CreateOrphanWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.CreateOrphan(opts)

    def CreateWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.Create(opts)

    def CreateWithRole(self, opts: dict, role_name: str) -> dict:
        return self.client.request(
            "POST", f"/v1/auth/token/create/{role_name}", data=opts
        )

    def CreateWithRoleWithContext(self, ctx: Any, opts: dict, role_name: str) -> dict:
        return self.CreateWithRole(opts, role_name)

    def Lookup(self, token: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/lookup", data={"token": token}
        )

    def LookupAccessor(self, accessor: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/lookup-accessor", data={"accessor": accessor}
        )

    def LookupAccessorWithContext(self, ctx: Any, accessor: str) -> dict:
        return self.LookupAccessor(accessor)

    def LookupSelf(self) -> dict:
        return self.client.request("GET", "/v1/auth/token/lookup-self")

    def LookupSelfWithContext(self, ctx: Any) -> dict:
        return self.LookupSelf()

    def LookupWithContext(self, ctx: Any, token: str) -> dict:
        return self.Lookup(token)

    def Renew(self, token: str, increment: int) -> dict:
        return self.client.request(
            "POST",
            "/v1/auth/token/renew",
            data={"token": token, "increment": increment},
        )

    def RenewAccessor(self, accessor: str, increment: int) -> dict:
        return self.client.request(
            "POST",
            "/v1/auth/token/renew-accessor",
            data={"accessor": accessor, "increment": increment},
        )

    def RenewAccessorWithContext(self, ctx: Any, accessor: str, increment: int) -> dict:
        return self.RenewAccessor(accessor, increment)

    def RenewSelf(self, increment: int) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/renew-self", data={"increment": increment}
        )

    def RenewSelfWithContext(self, ctx: Any, increment: int) -> dict:
        return self.RenewSelf(increment)

    def RenewTokenAsSelf(self, token: str, increment: int) -> dict:
        return self.Renew(token, increment)

    def RenewTokenAsSelfWithContext(self, ctx: Any, token: str, increment: int) -> dict:
        return self.Renew(token, increment)

    def RenewWithContext(self, ctx: Any, token: str, increment: int) -> dict:
        return self.Renew(token, increment)

    def RevokeAccessor(self, accessor: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/revoke-accessor", data={"accessor": accessor}
        )

    def RevokeAccessorWithContext(self, ctx: Any, accessor: str) -> dict:
        return self.RevokeAccessor(accessor)

    def RevokeOrphan(self, token: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/revoke-orphan", data={"token": token}
        )

    def RevokeOrphanWithContext(self, ctx: Any, token: str) -> dict:
        return self.RevokeOrphan(token)

    def RevokeSelf(self, token: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/revoke-self", data={"token": token}
        )

    def RevokeSelfWithContext(self, ctx: Any, token: str) -> dict:
        return self.RevokeSelf(token)

    def RevokeTree(self, token: str) -> dict:
        return self.client.request(
            "POST", "/v1/auth/token/revoke", data={"token": token}
        )

    def RevokeTreeWithContext(self, ctx: Any, token: str) -> dict:
        return self.RevokeTree(token)


class Auth:
    def __init__(self, client: "Client"):
        self.client = client

    def Login(self, ctx: Any, auth_method: Any) -> dict:
        mount = getattr(auth_method, "mount", "auth/userpass")
        path = f"v1/{mount}/login"
        creds = getattr(auth_method, "data", {})
        res = self.client.request("POST", path, data=creds)
        if res and "auth" in res and "client_token" in res["auth"]:
            self.client.SetToken(res["auth"]["client_token"])
        return res

    def MFALogin(self, ctx: Any, auth_method: Any, *creds: str) -> dict:
        if hasattr(auth_method, "data"):
            auth_method.data["mfa_creds"] = list(creds)
        return self.Login(ctx, auth_method)

    def MFAValidate(self, ctx: Any, mfa_secret: Any, payload: dict) -> dict:
        return self.client.request("POST", "/v1/sys/mfa/validate", data=payload)

    def Token(self) -> TokenAuth:
        return TokenAuth(self.client)


class SSH:
    def __init__(self, client: "Client", mount_point: str = "ssh"):
        self.client = client
        self.mount_point = mount_point.strip("/")

    def Credential(self, role: str, data: dict) -> dict:
        return self.client.request(
            "POST", f"/v1/{self.mount_point}/creds/{role}", data=data
        )

    def CredentialWithContext(self, ctx: Any, role: str, data: dict) -> dict:
        return self.Credential(role, data)

    def SignKey(self, role: str, data: dict) -> dict:
        return self.client.request(
            "POST", f"/v1/{self.mount_point}/sign/{role}", data=data
        )

    def SignKeyWithContext(self, ctx: Any, role: str, data: dict) -> dict:
        return self.SignKey(role, data)


class SSHHelper:
    def __init__(self, client: "Client", mount_point: str = "ssh"):
        self.client = client
        self.mount_point = mount_point.strip("/")

    def Verify(self, otp: str) -> dict:
        return self.client.request(
            "POST", f"/v1/{self.mount_point}/verify", data={"otp": otp}
        )

    def VerifyWithContext(self, ctx: Any, otp: str) -> dict:
        return self.Verify(otp)


class Sys:
    def __init__(self, client: "Client"):
        self.client = client

    def AuditHash(self, path: str, input_str: str) -> str:
        res = self.client.request(
            "POST", f"/v1/sys/audit-hash/{path}", data={"input": input_str}
        )
        return res.get("hash", "")

    def AuditHashWithContext(self, ctx: Any, path: str, input_str: str) -> str:
        return self.AuditHash(path, input_str)

    def CORSStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/config/cors")

    def CORSStatusWithContext(self, ctx: Any) -> dict:
        return self.CORSStatus()

    def Capabilities(self, token: str, path: str) -> list[str]:
        res = self.client.request(
            "POST", "/v1/sys/capabilities", data={"token": token, "path": path}
        )
        return res.get("capabilities", [])

    def CapabilitiesSelf(self, path: str) -> list[str]:
        res = self.client.request(
            "POST", "/v1/sys/capabilities-self", data={"path": path}
        )
        return res.get("capabilities", [])

    def CapabilitiesSelfWithContext(self, ctx: Any, path: str) -> list[str]:
        return self.CapabilitiesSelf(path)

    def CapabilitiesWithContext(self, ctx: Any, token: str, path: str) -> list[str]:
        return self.Capabilities(token, path)

    def ConfigureCORS(self, req: dict) -> dict:
        return self.client.request("POST", "/v1/sys/config/cors", data=req)

    def ConfigureCORSWithContext(self, ctx: Any, req: dict) -> dict:
        return self.ConfigureCORS(req)

    def DeletePolicy(self, name: str) -> dict:
        return self.client.request("DELETE", f"/v1/sys/policy/{name}")

    def DeletePolicyWithContext(self, ctx: Any, name: str) -> dict:
        return self.DeletePolicy(name)

    def DeregisterPlugin(self, i: dict) -> dict:
        name = i.get("name", "")
        plugin_type = i.get("type", "database")
        return self.client.request(
            "DELETE", f"/v1/sys/plugins/catalog/{plugin_type}/{name}"
        )

    def DeregisterPluginWithContext(self, ctx: Any, i: dict) -> dict:
        return self.DeregisterPlugin(i)

    def DisableAudit(self, path: str) -> dict:
        return self.client.request("DELETE", f"/v1/sys/audit/{path}")

    def DisableAuditWithContext(self, ctx: Any, path: str) -> dict:
        return self.DisableAudit(path)

    def DisableAuth(self, path: str) -> dict:
        return self.client.request("DELETE", f"/v1/sys/auth/{path}")

    def DisableAuthWithContext(self, ctx: Any, path: str) -> dict:
        return self.DisableAuth(path)

    def DisableCORS(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/config/cors")

    def DisableCORSWithContext(self, ctx: Any) -> dict:
        return self.DisableCORS()

    def EnableAudit(self, path: str, audit_type: str, desc: str, opts: dict) -> dict:
        return self.client.request(
            "POST",
            f"/v1/sys/audit/{path}",
            data={"type": audit_type, "description": desc, "options": opts},
        )

    def EnableAuditWithOptions(self, path: str, options: dict) -> dict:
        return self.client.request("POST", f"/v1/sys/audit/{path}", data=options)

    def EnableAuditWithOptionsWithContext(
        self, ctx: Any, path: str, options: dict
    ) -> dict:
        return self.EnableAuditWithOptions(path, options)

    def EnableAuth(self, path: str, auth_type: str, desc: str) -> dict:
        return self.client.request(
            "POST",
            f"/v1/sys/auth/{path}",
            data={"type": auth_type, "description": desc},
        )

    def EnableAuthWithOptions(self, path: str, options: dict) -> dict:
        return self.client.request("POST", f"/v1/sys/auth/{path}", data=options)

    def EnableAuthWithOptionsWithContext(
        self, ctx: Any, path: str, options: dict
    ) -> dict:
        return self.EnableAuthWithOptions(path, options)

    def GenerateRecoveryOperationTokenCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/generate-recovery-token/attempt")

    def GenerateRecoveryOperationTokenCancelWithContext(self, ctx: Any) -> dict:
        return self.GenerateRecoveryOperationTokenCancel()

    def GenerateRecoveryOperationTokenInit(self, otp: str, pgp_key: str) -> dict:
        return self.client.request(
            "POST",
            "/v1/sys/generate-recovery-token/attempt",
            data={"otp": otp, "pgp_key": pgp_key},
        )

    def GenerateRecoveryOperationTokenInitWithContext(
        self, ctx: Any, otp: str, pgp_key: str
    ) -> dict:
        return self.GenerateRecoveryOperationTokenInit(otp, pgp_key)

    def GenerateRecoveryOperationTokenStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/generate-recovery-token/attempt")

    def GenerateRecoveryOperationTokenStatusWithContext(self, ctx: Any) -> dict:
        return self.GenerateRecoveryOperationTokenStatus()

    def GenerateRecoveryOperationTokenUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT",
            "/v1/sys/generate-recovery-token/update",
            data={"key": shard, "nonce": nonce},
        )

    def GenerateRecoveryOperationTokenUpdateWithContext(
        self, ctx: Any, shard: str, nonce: str
    ) -> dict:
        return self.GenerateRecoveryOperationTokenUpdate(shard, nonce)

    def GenerateRootCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/generate-root/attempt")

    def GenerateRootCancelWithContext(self, ctx: Any) -> dict:
        return self.GenerateRootCancel()

    def GenerateRootInit(self, otp: str, pgp_key: str) -> dict:
        return self.client.request(
            "POST",
            "/v1/sys/generate-root/attempt",
            data={"otp": otp, "pgp_key": pgp_key},
        )

    def GenerateRootInitWithContext(self, ctx: Any, otp: str, pgp_key: str) -> dict:
        return self.GenerateRootInit(otp, pgp_key)

    def GenerateRootStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/generate-root/attempt")

    def GenerateRootStatusWithContext(self, ctx: Any) -> dict:
        return self.GenerateRootStatus()

    def GenerateRootUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT", "/v1/sys/generate-root/update", data={"key": shard, "nonce": nonce}
        )

    def GenerateRootUpdateWithContext(self, ctx: Any, shard: str, nonce: str) -> dict:
        return self.GenerateRootUpdate(shard, nonce)

    def GetPlugin(self, i: dict) -> dict:
        name = i.get("name", "")
        plugin_type = i.get("type", "database")
        return self.client.request(
            "GET", f"/v1/sys/plugins/catalog/{plugin_type}/{name}"
        )

    def GetPluginWithContext(self, ctx: Any, i: dict) -> dict:
        return self.GetPlugin(i)

    def GetPolicy(self, name: str) -> str:
        res = self.client.request("GET", f"/v1/sys/policy/{name}")
        return res.get("rules", "")

    def GetPolicyWithContext(self, ctx: Any, name: str) -> str:
        return self.GetPolicy(name)

    def HAStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/ha-status")

    def HAStatusWithContext(self, ctx: Any) -> dict:
        return self.HAStatus()

    def Health(self) -> dict:
        return self.client.request("GET", "/v1/sys/health")

    def HealthWithContext(self, ctx: Any) -> dict:
        return self.Health()

    def Init(self, opts: dict) -> dict:
        return self.client.request("PUT", "/v1/sys/init", data=opts)

    def InitStatus(self) -> bool:
        res = self.client.request("GET", "/v1/sys/init")
        return res.get("initialized", False)

    def InitStatusWithContext(self, ctx: Any) -> bool:
        return self.InitStatus()

    def InitWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.Init(opts)

    def KeyStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/key-status")

    def KeyStatusWithContext(self, ctx: Any) -> dict:
        return self.KeyStatus()

    def Leader(self) -> dict:
        return self.client.request("GET", "/v1/sys/leader")

    def LeaderWithContext(self, ctx: Any) -> dict:
        return self.Leader()

    def ListAudit(self) -> dict:
        return self.client.request("GET", "/v1/sys/audit")

    def ListAuditWithContext(self, ctx: Any) -> dict:
        return self.ListAudit()

    def ListAuth(self) -> dict:
        return self.client.request("GET", "/v1/sys/auth")

    def ListAuthWithContext(self, ctx: Any) -> dict:
        return self.ListAuth()

    def ListMounts(self) -> dict:
        return self.client.request("GET", "/v1/sys/mounts")

    def ListMountsWithContext(self, ctx: Any) -> dict:
        return self.ListMounts()

    def ListPlugins(self, i: dict) -> dict:
        plugin_type = i.get("type", "database")
        return self.client.request("GET", f"/v1/sys/plugins/catalog/{plugin_type}")

    def ListPluginsWithContext(self, ctx: Any, i: dict) -> dict:
        return self.ListPlugins(i)

    def ListPolicies(self) -> list[str]:
        res = self.client.request("GET", "/v1/sys/policy")
        return res.get("policies", [])

    def ListPoliciesWithContext(self, ctx: Any) -> list[str]:
        return self.ListPolicies()

    def Lookup(self, id: str) -> dict:
        return self.client.request("POST", "/v1/sys/lookup", data={"id": id})

    def LookupWithContext(self, ctx: Any, id: str) -> dict:
        return self.Lookup(id)

    def MFAValidate(self, request_id: str, payload: dict) -> dict:
        payload["request_id"] = request_id
        return self.client.request("POST", "/v1/sys/mfa/validate", data=payload)

    def MFAValidateWithContext(self, ctx: Any, request_id: str, payload: dict) -> dict:
        return self.MFAValidate(request_id, payload)

    def Monitor(self, ctx: Any, log_level: str, log_format: str) -> Any:
        yield "System Monitor Log Initialized"

    def Mount(self, path: str, mount_info: dict) -> dict:
        return self.client.request("POST", f"/v1/sys/mounts/{path}", data=mount_info)

    def MountConfig(self, path: str) -> dict:
        return self.client.request("GET", f"/v1/sys/mounts/{path}/tune")

    def MountConfigWithContext(self, ctx: Any, path: str) -> dict:
        return self.MountConfig(path)

    def MountWithContext(self, ctx: Any, path: str, mount_info: dict) -> dict:
        return self.Mount(path, mount_info)

    def PutPolicy(self, name: str, rules: str) -> dict:
        return self.client.request(
            "PUT", f"/v1/sys/policy/{name}", data={"rules": rules}
        )

    def PutPolicyWithContext(self, ctx: Any, name: str, rules: str) -> dict:
        return self.PutPolicy(name, rules)

    def PutRaftAutopilotConfiguration(self, opts: dict) -> dict:
        return self.client.request(
            "POST", "/v1/sys/storage/raft/autopilot/configuration", data=opts
        )

    def PutRaftAutopilotConfigurationWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.PutRaftAutopilotConfiguration(opts)

    def RaftAutopilotConfiguration(self) -> dict:
        return self.client.request(
            "GET", "/v1/sys/storage/raft/autopilot/configuration"
        )

    def RaftAutopilotConfigurationWithContext(self, ctx: Any) -> dict:
        return self.RaftAutopilotConfiguration()

    def RaftAutopilotConfigurationWithDRToken(self, dr_token: str) -> dict:
        return self.client.request(
            "GET",
            "/v1/sys/storage/raft/autopilot/configuration",
            headers={"X-Vault-DR-Token": dr_token},
        )

    def RaftAutopilotState(self) -> dict:
        return self.client.request("GET", "/v1/sys/storage/raft/autopilot/state")

    def RaftAutopilotStateWithContext(self, ctx: Any) -> dict:
        return self.RaftAutopilotState()

    def RaftAutopilotStateWithDRToken(self, dr_token: str) -> dict:
        return self.client.request(
            "GET",
            "/v1/sys/storage/raft/autopilot/state",
            headers={"X-Vault-DR-Token": dr_token},
        )

    def RaftJoin(self, opts: dict) -> dict:
        return self.client.request("POST", "/v1/sys/storage/raft/join", data=opts)

    def RaftJoinWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.RaftJoin(opts)

    def RaftSnapshot(self, snap_writer: Any) -> dict:
        res = self.client.request("GET", "/v1/sys/storage/raft/snapshot")
        if hasattr(snap_writer, "write"):
            snap_writer.write(
                res.encode("utf-8")
                if isinstance(res, str)
                else str(res).encode("utf-8")
            )
        return {"status": "success"}

    def RaftSnapshotRestore(self, snap_reader: Any, force: bool) -> dict:
        data = snap_reader.read() if hasattr(snap_reader, "read") else snap_reader
        return self.client.request(
            "POST",
            "/v1/sys/storage/raft/snapshot-force"
            if force
            else "/v1/sys/storage/raft/snapshot",
            data={"data": data},
        )

    def RaftSnapshotRestoreWithContext(
        self, ctx: Any, snap_reader: Any, force: bool
    ) -> dict:
        return self.RaftSnapshotRestore(snap_reader, force)

    def RaftSnapshotWithContext(self, ctx: Any, snap_writer: Any) -> dict:
        return self.RaftSnapshot(snap_writer)

    def RegisterPlugin(self, i: dict) -> dict:
        name = i.get("name", "")
        plugin_type = i.get("type", "database")
        return self.client.request(
            "PUT", f"/v1/sys/plugins/catalog/{plugin_type}/{name}", data=i
        )

    def RegisterPluginWithContext(self, ctx: Any, i: dict) -> dict:
        return self.RegisterPlugin(i)

    def RekeyCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey/init")

    def RekeyCancelWithContext(self, ctx: Any) -> dict:
        return self.RekeyCancel()

    def RekeyDeleteBackup(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey/backup")

    def RekeyDeleteBackupWithContext(self, ctx: Any) -> dict:
        return self.RekeyDeleteBackup()

    def RekeyDeleteRecoveryBackup(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey-recovery-key/backup")

    def RekeyDeleteRecoveryBackupWithContext(self, ctx: Any) -> dict:
        return self.RekeyDeleteRecoveryBackup()

    def RekeyInit(self, config: dict) -> dict:
        return self.client.request("POST", "/v1/sys/rekey/init", data=config)

    def RekeyInitWithContext(self, ctx: Any, config: dict) -> dict:
        return self.RekeyInit(config)

    def RekeyRecoveryKeyCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey-recovery-key/init")

    def RekeyRecoveryKeyCancelWithContext(self, ctx: Any) -> dict:
        return self.RekeyRecoveryKeyCancel()

    def RekeyRecoveryKeyInit(self, config: dict) -> dict:
        return self.client.request(
            "POST", "/v1/sys/rekey-recovery-key/init", data=config
        )

    def RekeyRecoveryKeyInitWithContext(self, ctx: Any, config: dict) -> dict:
        return self.RekeyRecoveryKeyInit(config)

    def RekeyRecoveryKeyStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey-recovery-key/init")

    def RekeyRecoveryKeyStatusWithContext(self, ctx: Any) -> dict:
        return self.RekeyRecoveryKeyStatus()

    def RekeyRecoveryKeyUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT",
            "/v1/sys/rekey-recovery-key/update",
            data={"key": shard, "nonce": nonce},
        )

    def RekeyRecoveryKeyUpdateWithContext(
        self, ctx: Any, shard: str, nonce: str
    ) -> dict:
        return self.RekeyRecoveryKeyUpdate(shard, nonce)

    def RekeyRecoveryKeyVerificationCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey-recovery-key/verify")

    def RekeyRecoveryKeyVerificationCancelWithContext(self, ctx: Any) -> dict:
        return self.RekeyRecoveryKeyVerificationCancel()

    def RekeyRecoveryKeyVerificationStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey-recovery-key/verify")

    def RekeyRecoveryKeyVerificationStatusWithContext(self, ctx: Any) -> dict:
        return self.RekeyRecoveryKeyVerificationStatus()

    def RekeyRecoveryKeyVerificationUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT",
            "/v1/sys/rekey-recovery-key/verify/update",
            data={"key": shard, "nonce": nonce},
        )

    def RekeyRecoveryKeyVerificationUpdateWithContext(
        self, ctx: Any, shard: str, nonce: str
    ) -> dict:
        return self.RekeyRecoveryKeyVerificationUpdate(shard, nonce)

    def RekeyRetrieveBackup(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey/backup")

    def RekeyRetrieveBackupWithContext(self, ctx: Any) -> dict:
        return self.RekeyRetrieveBackup()

    def RekeyRetrieveRecoveryBackup(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey-recovery-key/backup")

    def RekeyRetrieveRecoveryBackupWithContext(self, ctx: Any) -> dict:
        return self.RekeyRetrieveRecoveryBackup()

    def RekeyStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey/init")

    def RekeyStatusWithContext(self, ctx: Any) -> dict:
        return self.RekeyStatus()

    def RekeyUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT", "/v1/sys/rekey/update", data={"key": shard, "nonce": nonce}
        )

    def RekeyUpdateWithContext(self, ctx: Any, shard: str, nonce: str) -> dict:
        return self.RekeyUpdate(shard, nonce)

    def RekeyVerificationCancel(self) -> dict:
        return self.client.request("DELETE", "/v1/sys/rekey/verify")

    def RekeyVerificationCancelWithContext(self, ctx: Any) -> dict:
        return self.RekeyVerificationCancel()

    def RekeyVerificationStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/rekey/verify")

    def RekeyVerificationStatusWithContext(self, ctx: Any) -> dict:
        return self.RekeyVerificationStatus()

    def RekeyVerificationUpdate(self, shard: str, nonce: str) -> dict:
        return self.client.request(
            "PUT", "/v1/sys/rekey/verify/update", data={"key": shard, "nonce": nonce}
        )

    def RekeyVerificationUpdateWithContext(
        self, ctx: Any, shard: str, nonce: str
    ) -> dict:
        return self.RekeyVerificationUpdate(shard, nonce)

    def ReloadPlugin(self, i: dict) -> str:
        res = self.client.request("PUT", "/v1/sys/plugins/reload/backend", data=i)
        return res.get("reload_id", "")

    def ReloadPluginStatus(self, reload_status_input: dict) -> dict:
        reload_id = reload_status_input.get("reload_id", "")
        return self.client.request(
            "GET", f"/v1/sys/plugins/reload/backend/status/{reload_id}"
        )

    def ReloadPluginStatusWithContext(
        self, ctx: Any, reload_status_input: dict
    ) -> dict:
        return self.ReloadPluginStatus(reload_status_input)

    def ReloadPluginWithContext(self, ctx: Any, i: dict) -> str:
        return self.ReloadPlugin(i)

    def Remount(self, from_path: str, to_path: str) -> dict:
        return self.client.request(
            "POST", "/v1/sys/remount", data={"from": from_path, "to": to_path}
        )

    def RemountStatus(self, migration_id: str) -> dict:
        return self.client.request("GET", f"/v1/sys/remount/status/{migration_id}")

    def RemountStatusWithContext(self, ctx: Any, migration_id: str) -> dict:
        return self.RemountStatus(migration_id)

    def RemountWithContext(self, ctx: Any, from_path: str, to_path: str) -> dict:
        return self.Remount(from_path, to_path)

    def Renew(self, id: str, increment: int) -> dict:
        return self.client.request(
            "POST",
            "/v1/sys/leases/renew",
            data={"lease_id": id, "increment": increment},
        )

    def RenewWithContext(self, ctx: Any, id: str, increment: int) -> dict:
        return self.Renew(id, increment)

    def ResetUnsealProcess(self) -> dict:
        return self.client.request("PUT", "/v1/sys/unseal", data={"reset": True})

    def ResetUnsealProcessWithContext(self, ctx: Any) -> dict:
        return self.ResetUnsealProcess()

    def Revoke(self, id: str) -> dict:
        return self.client.request("PUT", f"/v1/sys/leases/revoke/{id}")

    def RevokeForce(self, id: str) -> dict:
        return self.client.request("PUT", f"/v1/sys/leases/revoke-force/{id}")

    def RevokeForceWithContext(self, ctx: Any, id: str) -> dict:
        return self.RevokeForce(id)

    def RevokePrefix(self, id: str) -> dict:
        return self.client.request("PUT", f"/v1/sys/leases/revoke-prefix/{id}")

    def RevokePrefixWithContext(self, ctx: Any, id: str) -> dict:
        return self.RevokePrefix(id)

    def RevokeWithContext(self, ctx: Any, id: str) -> dict:
        return self.Revoke(id)

    def RevokeWithOptions(self, opts: dict) -> dict:
        return self.client.request("PUT", "/v1/sys/leases/revoke-opts", data=opts)

    def RevokeWithOptionsWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.RevokeWithOptions(opts)

    def Rotate(self) -> dict:
        return self.client.request("POST", "/v1/sys/rotate")

    def RotateWithContext(self, ctx: Any) -> dict:
        return self.Rotate()

    def Seal(self) -> dict:
        return self.client.request("PUT", "/v1/sys/seal")

    def SealStatus(self) -> dict:
        return self.client.request("GET", "/v1/sys/seal-status")

    def SealStatusWithContext(self, ctx: Any) -> dict:
        return self.SealStatus()

    def SealWithContext(self, ctx: Any) -> dict:
        return self.Seal()

    def StartRemount(self, from_path: str, to_path: str) -> dict:
        return self.client.request(
            "POST", "/v1/sys/remount/start", data={"from": from_path, "to": to_path}
        )

    def StartRemountWithContext(self, ctx: Any, from_path: str, to_path: str) -> dict:
        return self.StartRemount(from_path, to_path)

    def StepDown(self) -> dict:
        return self.client.request("PUT", "/v1/sys/step-down")

    def StepDownWithContext(self, ctx: Any) -> dict:
        return self.StepDown()

    def TuneMount(self, path: str, config: dict) -> dict:
        return self.client.request("POST", f"/v1/sys/mounts/{path}/tune", data=config)

    def TuneMountWithContext(self, ctx: Any, path: str, config: dict) -> dict:
        return self.TuneMount(path, config)

    def Unmount(self, path: str) -> dict:
        return self.client.request("DELETE", f"/v1/sys/mounts/{path}")

    def UnmountWithContext(self, ctx: Any, path: str) -> dict:
        return self.Unmount(path)

    def Unseal(self, shard: str) -> dict:
        return self.client.request("PUT", "/v1/sys/unseal", data={"key": shard})

    def UnsealWithContext(self, ctx: Any, shard: str) -> dict:
        return self.Unseal(shard)

    def UnsealWithOptions(self, opts: dict) -> dict:
        return self.client.request("PUT", "/v1/sys/unseal", data=opts)

    def UnsealWithOptionsWithContext(self, ctx: Any, opts: dict) -> dict:
        return self.UnsealWithOptions(opts)


class Client(ApiClientBase):
    def __init__(
        self,
        config_or_base_url: Any = "http://localhost:8200",
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify: bool | str | None = True,
        base_url: str | None = None,
    ):
        if base_url:
            actual_base_url = base_url
        elif isinstance(config_or_base_url, str):
            actual_base_url = config_or_base_url
        elif hasattr(config_or_base_url, "address"):
            actual_base_url = config_or_base_url.address
        else:
            actual_base_url = "http://localhost:8200"

        verify_val = True if verify is None else verify
        super().__init__(actual_base_url, token, username, password, verify_val)
        self._address = actual_base_url
        self._token = token
        self._namespace = ""
        self._headers: dict[str, Any] = {}

    @classmethod
    def NewClient(cls, c: Config) -> "Client":
        return cls(c)

    def Address(self) -> str:
        return self._address

    def SetAddress(self, addr: str) -> None:
        self._address = addr
        self.base_url = addr

    def Token(self) -> str:
        return self._token or ""

    def SetToken(self, token: str) -> None:
        self._token = token
        self._session.headers.update({"X-Vault-Token": token, "X-Bao-Token": token})

    def Namespace(self) -> str:
        return self._namespace

    def SetNamespace(self, namespace: str) -> None:
        self._namespace = namespace
        self._session.headers.update(
            {"X-Vault-Namespace": namespace, "X-Bao-Namespace": namespace}
        )

    def ClearNamespace(self) -> None:
        self._namespace = ""
        self._session.headers.pop("X-Vault-Namespace", None)
        self._session.headers.pop("X-Bao-Namespace", None)

    def ClearToken(self) -> None:
        self._token = None
        self._session.headers.pop("Authorization", None)
        self._session.headers.pop("X-Vault-Token", None)
        self._session.headers.pop("X-Bao-Token", None)

    def AddHeader(self, key: str, value: str) -> None:
        self._headers[key] = value
        self._session.headers.update({key: value})

    def Headers(self) -> Any:
        h = requests.structures.CaseInsensitiveDict()
        for k, v in self._headers.items():
            h[k] = v
        return h

    def SetHeaders(self, headers: dict) -> None:
        self._headers = headers
        self._session.headers.update(headers)

    def Clone(self) -> "Client":
        cloned = Client(
            self._address,
            self._token,
            self.username,
            self.password,
            self._session.verify,
        )
        cloned.SetNamespace(self._namespace)
        cloned.SetHeaders(dict(self._headers))
        return cloned

    def CloneWithHeaders(self) -> "Client":
        return self.Clone()

    def WithNamespace(self, namespace: str) -> "Client":
        cloned = self.Clone()
        cloned.SetNamespace(namespace)
        return cloned

    @property
    def logical(self) -> Logical:
        return Logical(self)

    def Logical(self) -> Logical:
        return self.logical

    @property
    def sys(self) -> Sys:
        return Sys(self)

    def Sys(self) -> Sys:
        return self.sys

    @property
    def auth(self) -> Auth:
        return Auth(self)

    def Auth(self) -> Auth:
        return self.auth

    @property
    def ssh(self) -> Any:
        return SSH(self)

    def SSH(self) -> Any:
        return self.ssh

    def SSHWithMountPoint(self, mount_point: str) -> Any:
        return SSH(self, mount_point)

    @property
    def ssh_helper(self) -> Any:
        return SSHHelper(self)

    def SSHHelper(self) -> Any:
        return self.ssh_helper

    def SSHHelperWithMountPoint(self, mount_point: str) -> Any:
        return SSHHelper(self, mount_point)

    def KVv1(self, mount_path: str) -> KVv1:
        return KVv1(self, mount_path)

    def KVv2(self, mount_path: str) -> KVv2:
        return KVv2(self, mount_path)

    def Help(self, path: str) -> dict:
        return self.request("GET", f"/v1/{path}?help=1")

    def HelpWithContext(self, ctx: Any, path: str) -> dict:
        return self.Help(path)

    # Retry and config methods/properties mapping Go signatures
    def CheckRetry(self) -> Any:
        return None

    def ClientTimeout(self) -> Any:
        return 0

    def CloneConfig(self) -> Config:
        cfg = Config(self._address)
        return cfg

    def CloneHeaders(self) -> bool:
        return True

    def CloneToken(self) -> bool:
        return True

    def CurrentWrappingLookupFunc(self) -> Any:
        return None

    def DisableKeepAlives(self) -> bool:
        return False

    def Limiter(self) -> Any:
        return None

    def MaxIdleConnections(self) -> int:
        return 0

    def MaxRetries(self) -> int:
        return 0

    def MaxRetryWait(self) -> Any:
        return 0

    def MinRetryWait(self) -> Any:
        return 0

    def NewLifetimeWatcher(self, i: Any) -> LifetimeWatcher:
        return LifetimeWatcher(self, i)

    def NewRenewer(self, i: Any) -> LifetimeWatcher:
        return self.NewLifetimeWatcher(i)

    def NewRequest(self, method: str, request_path: str) -> Request:
        return Request()

    def OutputCurlString(self) -> bool:
        return False

    def OutputPolicy(self) -> bool:
        return False

    def RawRequest(self, r: Any) -> Response:
        return Response()

    def RawRequestWithContext(self, ctx: Any, r: Any) -> Response:
        return Response()

    def SRVLookup(self) -> bool:
        return False

    def SetBackoff(self, backoff: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetCheckRedirect(self, f: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetCheckRetry(self, checkRetry: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetClientTimeout(self, timeout: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetCloneHeaders(self, cloneHeaders: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetCloneToken(self, cloneToken: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetDisableKeepAlives(self, disable: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetLimiter(self, rateLimit: float, burst: int) -> None:
        raise RuntimeError("Not implemented")

    def SetLogger(self, logger: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetMFACreds(self, creds: list[str]) -> None:
        raise RuntimeError("Not implemented")

    def SetMaxIdleConnections(self, idle: int) -> None:
        raise RuntimeError("Not implemented")

    def SetMaxRetries(self, retries: int) -> None:
        raise RuntimeError("Not implemented")

    def SetMaxRetryWait(self, retryWait: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetMinRetryWait(self, retryWait: Any) -> None:
        raise RuntimeError("Not implemented")

    def SetOutputCurlString(self, curl: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetOutputPolicy(self, isSet: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetPolicyOverride(self, override: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetSRVLookup(self, srv: bool) -> None:
        raise RuntimeError("Not implemented")

    def SetWrappingLookupFunc(self, lookupFunc: Any) -> None:
        raise RuntimeError("Not implemented")

    def WithRequestCallbacks(self, *callbacks: Any) -> "Client":
        return self

    def WithResponseCallbacks(self, *callbacks: Any) -> "Client":
        return self
