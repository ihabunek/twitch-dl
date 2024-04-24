"""
These tests depend on the channel having some videos and clips published.
"""

import httpx
import pytest

from twitchdl import twitch
from twitchdl.commands.download import get_clip_authenticated_url
from twitchdl.commands.videos import get_game_ids
from twitchdl.exceptions import ConsoleError
from twitchdl.playlists import enumerate_vods, load_m3u8, parse_playlists

TEST_CHANNEL = "bananasaurus_rex"


def test_get_videos():
    videos = twitch.get_channel_videos(TEST_CHANNEL, 3, "time")
    assert videos["pageInfo"]
    assert len(videos["edges"]) > 0

    video_id = videos["edges"][0]["node"]["id"]
    video = twitch.get_video(video_id)
    assert video is not None
    assert video["id"] == video_id

    access_token = twitch.get_access_token(video_id)
    assert "signature" in access_token
    assert "value" in access_token

    playlists_txt = twitch.get_playlists(video_id, access_token)
    assert playlists_txt.startswith("#EXTM3U")

    playlists = parse_playlists(playlists_txt)
    playlist_url = playlists[0].url

    playlist_txt = httpx.get(playlist_url).text
    assert playlist_txt.startswith("#EXTM3U")

    playlist_m3u8 = load_m3u8(playlist_txt)
    vods = enumerate_vods(playlist_m3u8)
    assert vods[0].path == "0.ts"


def test_get_clips():
    """
    This test depends on the channel having some videos published.
    """
    clips = twitch.get_channel_clips(TEST_CHANNEL, "all_time", 3)
    assert clips["pageInfo"]
    assert len(clips["edges"]) > 0

    slug = clips["edges"][0]["node"]["slug"]
    clip = twitch.get_clip(slug)
    assert clip is not None
    assert clip["slug"] == slug

    assert get_clip_authenticated_url(slug, "source")


def test_get_games():
    assert get_game_ids([]) == []
    assert get_game_ids(["Bioshock"]) == ["15866"]
    assert get_game_ids(["Bioshock", "Portal"]) == ["15866", "6187"]


def test_get_games_not_found():
    with pytest.raises(ConsoleError) as ex:
        get_game_ids(["the game which does not exist"])
    assert str(ex.value) == "Game 'the game which does not exist' not found"
