from typer.testing import CliRunner

from ilearn.cli.main import app


def test_eval_completeness_flag_prints_metrics():
    runner = CliRunner()
    result = runner.invoke(app, ["eval", "--completeness"])
    assert result.exit_code == 0
    assert "completeness:" in result.stdout
    assert "total:" in result.stdout
