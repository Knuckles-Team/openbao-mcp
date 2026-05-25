#!/usr/bin/env python
from openbao_mcp.api.api_client_base import ApiClientBase
from openbao_mcp.api.api_client_secrets import Api as SecretsApi
from openbao_mcp.api.api_client_sys import Api as SysApi

__version__ = "0.15.0"

class Api(SecretsApi, SysApi):
    pass
