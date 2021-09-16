"""
These tests depend on the channel having some videos and clips published.
"""

from twitchdl import twitch

TEST_CHANNEL = "bananasaurus_rex"


def test_get_videos():
    videos = twitch.get_channel_videos(TEST_CHANNEL, 3, "time")
    assert videos["pageInfo"]
    assert len(videos["edges"]) > 0

    video_id = videos["edges"][0]["node"]["id"]
    video = twitch.get_video(video_id)
    assert video["id"] == video_id


def test_get_clips():
    """
    This test depends on the channel having some videos published.
    """
    clips = twitch.get_channel_clips(TEST_CHANNEL, "all_time", 3)
    assert clips["pageInfo"]
    assert len(clips["edges"]) > 0

    clip_slug = clips["edges"][0]["node"]["slug"]
    clip = twitch.get_clip(clip_slug)
    assert clip["slug"] == clip_slug
