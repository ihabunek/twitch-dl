import click
import pytest

from twitchdl import twitch
from twitchdl.entities import VideosType
from twitchdl.playlists import Playlist, parse_playlists, select_playlist_by_name
from twitchdl.subonly import get_subonly_playlists


def _playlist(name: str, group_id: str, resolution: str, is_source: bool = False) -> Playlist:
    return Playlist(
        name=name,
        group_id=group_id,
        resolution=resolution,
        url=f"https://example.com/{group_id}.m3u8",
        is_source=is_source,
    )


def test_select_playlist_by_name_source_falls_back_when_no_chunked_group():
    """
    Regression test for #189: some VODs don't have a "chunked" quality
    group even though other qualities are available. `--quality source`
    should fall back to the best available quality instead of failing.
    """
    playlists = [
        _playlist("1080p", "1080p30", "1920x1080"),
        _playlist("720p", "720p30", "1280x720"),
    ]

    selected = select_playlist_by_name(playlists, "source")

    assert selected.name == "1080p"


def test_select_playlist_by_name_source_prefers_chunked_group():
    playlists = [
        _playlist("720p", "720p30", "1280x720"),
        _playlist("1080p source", "chunked", "1920x1080", is_source=True),
    ]

    selected = select_playlist_by_name(playlists, "source")

    assert selected.group_id == "chunked"


def test_select_playlist_by_name_source_raises_when_no_playlists():
    with pytest.raises(click.ClickException):
        select_playlist_by_name([], "source")


# Allow failures because these are a bit flaky


@pytest.mark.xfail
@pytest.mark.parametrize("channel", ["baertaffy"])
@pytest.mark.parametrize("type", ["archive", "highlight", "upload"])
def test_sub_only_playlists(channel: str, type: VideosType):
    """
    This tests two methods of accessing playlists, one used in normal operation,
    and the other when the video is sub-only and compares the results.
    """
    video = _get_video(channel, type)
    access_token = twitch.get_access_token(video["id"])
    playlists_text = twitch.get_playlists(video["id"], access_token)
    regular_playlists = sorted(parse_playlists(playlists_text), key=lambda p: p.group_id)
    subonly_playlists = sorted(get_subonly_playlists(video), key=lambda p: p.group_id)

    assert regular_playlists == subonly_playlists


@pytest.mark.xfail
def test_sub_only_playlists_4k():
    # Known 4k video
    video = twitch.get_video("2177476725")
    assert video is not None
    access_token = twitch.get_access_token(video["id"])
    playlists_text = twitch.get_playlists(video["id"], access_token)
    regular_playlists = sorted(parse_playlists(playlists_text), key=lambda p: p.group_id)
    subonly_playlists = sorted(get_subonly_playlists(video), key=lambda p: p.group_id)

    assert regular_playlists == subonly_playlists


def _get_video(channel: str, type: VideosType):
    """Fetch the latest video of given type from a randomly chosen channel"""
    videos = twitch.get_channel_videos(channel, limit=1, sort="time", type=type)
    if not videos["edges"]:
        raise ValueError(f"Video of type '{type}' not found.")
    return videos["edges"][0]["node"]
