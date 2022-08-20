"""
These tests depend on the channel having some videos and clips published.
"""

import httpx
import m3u8
from twitchdl import twitch
from twitchdl.commands.download import _parse_playlists, get_clip_authenticated_url

TEST_CHANNEL = "bananasaurus_rex"


def test_get_videos():
    videos = twitch.get_channel_videos(TEST_CHANNEL, 3, "time")
    assert videos["pageInfo"]
    assert len(videos["edges"]) > 0

    video_id = videos["edges"][0]["node"]["id"]
    video = twitch.get_video(video_id)
    assert video["id"] == video_id

    access_token = twitch.get_access_token(video_id)
    assert "signature" in access_token
    assert "value" in access_token

    playlists = twitch.get_playlists(video_id, access_token)
    assert playlists.startswith("#EXTM3U")

    name, res, url = next(_parse_playlists(playlists))
    playlist = httpx.get(url).text
    assert playlist.startswith("#EXTM3U")

    playlist = m3u8.loads(playlist)
    vod_path = playlist.segments[0].uri
    assert vod_path == "0.ts"


def test_get_clips():
    """
    This test depends on the channel having some videos published.
    """
    clips = twitch.get_channel_clips(TEST_CHANNEL, "all_time", 3)
    assert clips["pageInfo"]
    assert len(clips["edges"]) > 0

    slug = clips["edges"][0]["node"]["slug"]
    clip = twitch.get_clip(slug)
    assert clip["slug"] == slug

    assert get_clip_authenticated_url(slug, "source")
