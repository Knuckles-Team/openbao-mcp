import pytest


@pytest.mark.concept("BO-OS.governance.bao-2")
def test_startup():
    # Basic import test
    import openbao_mcp

    assert openbao_mcp.__version__ == "2.1.0"
