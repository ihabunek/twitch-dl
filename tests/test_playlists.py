import pytest

from twitchdl import twitch
from twitchdl.entities import VideosType
from twitchdl.playlists import parse_playlists
from twitchdl.playlists_auth import fetch_auth_playlist

TEST_CHANNEL = "baertaffy"


@pytest.mark.parametrize("type", ["archive", "highlight", "upload"])
def test_sub_only_playlists(type: VideosType):
    """
    This tests two methods of accessing playlists, one used in normal operation,
    and the other when the video is sub-only and compares the results.
    """
    video = _get_video_by_type(type)
    access_token = twitch.get_access_token(video["id"])
    playlists_text = twitch.get_playlists(video["id"], access_token)
    regular_playlists = sorted(parse_playlists(playlists_text), key=lambda p: p.group_id)
    subonly_playlists = sorted(fetch_auth_playlist(video), key=lambda p: p.group_id)

    assert regular_playlists == subonly_playlists


def _get_video_by_type(type: VideosType):
    """Fetch the latest video of given type from a randomly chosen channel"""
    videos = twitch.get_channel_videos(TEST_CHANNEL, limit=1, sort="time", type = type)
    if not videos["edges"]:
        raise ValueError(f"Video of type '{type}' not found.")
    return videos["edges"][0]["node"]
