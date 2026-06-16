import pytest


@pytest.mark.concept("BAO-002")
def test_startup():
    # Basic import test
    import openbao_mcp

    assert openbao_mcp.__version__ == "0.31.0"


@pytest.mark.concept("BAO-007")
def test_agent_server_startup(monkeypatch):
    """CONCEPT:BAO-007 Test agent server startup orchestration."""
    from unittest.mock import MagicMock, patch

    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = MagicMock(
        mcp_url="http://localhost:5000",
        mcp_config="mcp_config.json",
        host="localhost",
        port=8000,
        provider="openai",
        model_id="gpt-4",
        base_url=None,
        api_key=None,
        custom_skills_directory=None,
        web=False,
        otel=False,
        otel_endpoint=None,
        otel_headers=None,
        otel_public_key=None,
        otel_secret_key=None,
        otel_protocol="http/protobuf",
        debug=True,
    )

    with (
        patch("agent_utilities.create_agent_parser", return_value=mock_parser),
        patch("agent_utilities.create_agent_server") as mock_server,
        patch("agent_utilities.initialize_workspace"),
        patch(
            "agent_utilities.load_identity",
            return_value={"name": "Test Agent", "description": "Test"},
        ),
    ):
        from openbao_mcp.agent_server import agent_server

        agent_server()

        mock_server.assert_called_once()
