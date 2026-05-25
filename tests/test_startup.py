import sys
import pytest

def test_startup():
    # Basic import test
    import openbao_mcp
    assert openbao_mcp.__version__ == "0.15.0"
