from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ilearn.cli.main import _build_orchestrator, app as cli_app


@patch("ilearn.cli.main.Orchestrator")
@patch("ilearn.cli.main.LLMClient.from_env")
@patch("ilearn.cli.main.load_dotenv")
def test_cli_loads_dotenv_and_wires_available_llm(
    mock_load_dotenv,
    mock_from_env,
    mock_orchestrator,
    tmp_path,
):
    llm = MagicMock()
    llm.available.return_value = True
    mock_from_env.return_value = llm

    _build_orchestrator(tmp_path)

    mock_load_dotenv.assert_called_once()
    assert mock_orchestrator.call_args.kwargs["llm"] is llm


def test_cli_agents_run_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("ILEARN_SESSIONS_DIR", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "agents",
            "run",
            "--region",
            "北京",
            "--grade",
            "5",
            "--age",
            "11",
            "--offline",
        ],
    )
    assert result.exit_code == 0
    assert "phase" in result.stdout.lower() or "会话" in result.stdout
