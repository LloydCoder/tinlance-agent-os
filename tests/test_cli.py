from tinlance_agent_os.cli import main


def test_cli_returns_success(capsys) -> None:
    assert main() == 0
    assert "Tinlance Agentic OS foundation" in capsys.readouterr().out
