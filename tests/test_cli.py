import json
from functools import lru_cache

import pytest
from click.testing import CliRunner, Result

from twitchdl import cli, twitch
from twitchdl.entities import Clip, Video


@pytest.fixture(scope="session")
def runner():
    return CliRunner()


def assert_ok(result: Result):
    if result.exit_code != 0:
        raise AssertionError(
            f"Command failed with exit code {result.exit_code}\nStderr: {result.stderr}"
        )


@lru_cache
def get_some_video() -> Video:
    """Returns a video for testing"""
    response = twitch.get_channel_videos("gamesdonequick", 1, "time")
    return response["edges"][0]["node"]


@lru_cache
def get_some_clip() -> Clip:
    """Returns a clip for testing"""
    response = twitch.get_channel_clips("gamesdonequick", "all_time", 1)
    return response["edges"][0]["node"]


def test_info_video(runner: CliRunner):
    video = get_some_video()

    result = runner.invoke(cli.info, [video["id"]])
    assert_ok(result)

    assert f"Video {video['id']}" in result.output
    assert video["title"] in result.output
    if video["game"]:
        assert video["game"]["name"] in result.output


def test_info_video_json(runner: CliRunner):
    video = get_some_video()

    result = runner.invoke(cli.info, [video["id"], "--json"])
    assert_ok(result)

    result = json.loads(result.stdout)
    assert result["id"] == video["id"]
    assert result["title"] == video["title"]
    assert result["game"] == video["game"]
    assert result["creator"] == video["creator"]
    assert result["owner"] == video["owner"]


def test_info_clip(runner: CliRunner):
    clip = get_some_clip()

    result = runner.invoke(cli.info, [clip["slug"]])
    assert_ok(result)

    assert clip["slug"] in result.output
    assert clip["title"] in result.output


def test_info_clip_json(runner: CliRunner):
    clip = get_some_clip()

    result = runner.invoke(cli.info, [clip["slug"], "--json"])
    assert_ok(result)

    result = json.loads(result.stdout)
    assert result["slug"] == clip["slug"]
    assert result["title"] == clip["title"]
    assert result["game"] == clip["game"]
    assert result["broadcaster"] == clip["broadcaster"]


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


def test_download_clip(runner: CliRunner):
    clip = get_some_clip()

    result = runner.invoke(cli.download, [clip["slug"], "-q", "source", "--dry-run"])
    assert_ok(result)
    assert f"Found clip: {clip['title']}" in result.output
    assert "Dry run, clip not downloaded." in result.stdout


def test_download_video(runner: CliRunner):
    video = get_some_video()
    result = runner.invoke(cli.download, [video["id"], "-q", "source", "--dry-run"])

    assert_ok(result)
    assert f"Found video: {video['title']}" in result.output
    assert "Dry run, video not downloaded." in result.output


def test_videos(runner: CliRunner):
    result = runner.invoke(cli.videos, ["gamesdonequick", "--json"])
    assert_ok(result)
    videos = json.loads(result.stdout)

    assert videos["count"] == 10
    assert videos["totalCount"] > 0
    video = videos["videos"][0]

    result = runner.invoke(cli.videos, "gamesdonequick")
    assert_ok(result)

    assert f"Video {video['id']}" in result.stdout
    assert video["title"] in result.stdout

    result = runner.invoke(cli.videos, ["gamesdonequick", "--compact"])
    assert_ok(result)

    assert video["id"] in result.stdout
    assert video["title"][:60] in result.stdout


def test_videos_channel_not_found(runner: CliRunner):
    result = runner.invoke(cli.videos, ["doesnotexisthopefully"])
    assert result.exit_code == 1
    assert result.output.strip() == "Error: Channel doesnotexisthopefully not found"


def test_clips(runner: CliRunner):
    result = runner.invoke(cli.clips, ["gamesdonequick", "--json"])
    assert_ok(result)
    clips = json.loads(result.stdout)
    clip = clips[0]

    result = runner.invoke(cli.clips, "gamesdonequick")
    assert_ok(result)

    assert f"Clip {clip['slug']}" in result.stdout
    assert clip["title"] in result.stdout

    result = runner.invoke(cli.clips, ["gamesdonequick", "--compact"])
    assert_ok(result)

    assert clip["slug"] in result.stdout
    assert clip["title"][:60] in result.stdout
