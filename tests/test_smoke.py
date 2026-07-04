"""Smoke tests that don't require network or API keys."""
from code_review_agent.tools import grep_code, list_directory, read_file


def test_tool_schemas_well_formed():
    """Each tool exports a TOOL_SCHEMA dict with the right shape."""
    for mod in [read_file, list_directory, grep_code]:
        schema = mod.TOOL_SCHEMA
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"


def test_read_file_missing():
    result = read_file.run("nonexistent/path/here")
    assert result["ok"] is False
    assert "not found" in result["error"]


def test_list_directory_filters_junk():
    result = list_directory.run(".")
    assert result["ok"] is True
    names = {e["name"] for e in result["entries"]}
    # Ignored entries should not appear
    assert "__pycache__" not in names
    assert ".git" not in names


def test_agent_module_imports():
    """Agent module imports cleanly."""
    from code_review_agent import agent
    assert hasattr(agent, "TOOLS")
    assert "read_file" in agent.TOOLS
    assert len(agent.TOOLS) == 5
