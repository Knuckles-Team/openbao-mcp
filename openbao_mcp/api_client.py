from openbao_mcp.api.api_client_full import Client
from openbao_mcp.api.api_client_secrets import Api as SecretsApi
from openbao_mcp.api.api_client_sys import Api as SysApi

__version__ = "0.31.0"


class Api(SecretsApi, SysApi, Client):
    def __init__(
        self,
        config_or_base_url="http://localhost:8200",
        token=None,
        username=None,
        password=None,
        verify=True,
        base_url=None,
    ):
        super().__init__(
            config_or_base_url=config_or_base_url,
            token=token,
            username=username,
            password=password,
            verify=verify,
            base_url=base_url,
        )
