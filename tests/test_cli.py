from unittest.mock import MagicMock, patch

from ilearn.cli.main import _build_orchestrator


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
