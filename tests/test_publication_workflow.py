from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_development_skill_is_source_backed():
    skill = (ROOT / "openbao_mcp/skills/openbao-mcp-development/SKILL.md").read_text()

    for fragment in (
        "Rapid delivery: the 5-minute contract",
        "openbao_mcp/__init__.py",
        "openbao_mcp/mcp_server.py",
        "openbao_mcp/mcp/mcp_auth.py",
        "openbao_mcp/mcp/mcp_secrets.py",
        "openbao_mcp/mcp/mcp_ssh.py",
        "openbao_mcp/mcp/mcp_sys.py",
        "OPENBAO_URL",
        "OPENBAO_TOKEN",
        "scion_sdk.cli:serve",
        "tests/test_governed_http.py",
    ):
        assert fragment in skill

    assert "openbao-agent" not in skill
    assert 'OPENBAO_TOKEN="' not in skill


def test_pages_and_package_contract_are_documented_by_actual_files():
    package = (ROOT / "pyproject.toml").read_text()

    for tree in ("skills/**", "ontology/**", "connectors/**"):
        assert tree in package
