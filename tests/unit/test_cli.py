from tinlance_agent_os import cli


def test_cli_main(capsys) -> None:
    assert cli.main() == 0
    assert "Tinlance Agentic OS" in capsys.readouterr().out
