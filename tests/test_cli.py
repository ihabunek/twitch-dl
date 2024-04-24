import json

import pytest
from click.testing import CliRunner, Result

from twitchdl import cli


@pytest.fixture(scope="session")
def runner():
    return CliRunner(mix_stderr=False)


def assert_ok(result: Result):
    if result.exit_code != 0:
        raise AssertionError(
            f"Command failed with exit code {result.exit_code}\nStderr: {result.stderr}"
        )


def test_info_video(runner: CliRunner):
    result = runner.invoke(cli.info, ["2090131595"])
    assert_ok(result)

    assert "Frost Fatales 2024 Day 1" in result.stdout
    assert "frozenflygone playing Tomb Raider" in result.stdout


def test_info_video_json(runner: CliRunner):
    result = runner.invoke(cli.info, ["2090131595", "--json"])
    assert_ok(result)

    video = json.loads(result.stdout)
    assert video["title"] == "Frost Fatales 2024 Day 1"
    assert video["game"] == {"id": "2770", "name": "Tomb Raider"}
    assert video["creator"] == {"login": "frozenflygone", "displayName": "frozenflygone"}


def test_info_clip(runner: CliRunner):
    result = runner.invoke(cli.info, ["PoisedTalentedPuddingChefFrank"])
    assert_ok(result)

    assert "AGDQ Crashes during Bioshock run" in result.stdout
    assert "GamesDoneQuick playing BioShock" in result.stdout


def test_info_clip_json(runner: CliRunner):
    result = runner.invoke(cli.info, ["PoisedTalentedPuddingChefFrank", "--json"])
    assert_ok(result)

    clip = json.loads(result.stdout)
    assert clip["slug"] == "PoisedTalentedPuddingChefFrank"
    assert clip["title"] == "AGDQ Crashes during Bioshock run"
    assert clip["game"] == {"id": "15866", "name": "BioShock"}
    assert clip["broadcaster"] == {"displayName": "GamesDoneQuick", "login": "gamesdonequick"}


def test_info_not_found(runner: CliRunner):
    result = runner.invoke(cli.info, ["banana"])
    assert result.exit_code == 1
    assert "Clip banana not found" in result.stderr

    result = runner.invoke(cli.info, ["12345"])
    assert result.exit_code == 1
    assert "Video 12345 not found" in result.stderr

    result = runner.invoke(cli.info, [""])
    assert result.exit_code == 1
    assert "Invalid input" in result.stderr
