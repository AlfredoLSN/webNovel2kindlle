from typer.testing import CliRunner

from webnovel2kindle.cli import app

runner = CliRunner()


def test_scan_rejects_non_centralnovel_url() -> None:
    result = runner.invoke(app, ["scan", "https://example.com/novel"])

    assert result.exit_code != 0
    assert "Central Novel" in result.output
