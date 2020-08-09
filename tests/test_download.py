import pytest

from unittest.mock import patch
from twitchdl.commands import download
from collections import namedtuple

Args = namedtuple("args", ["video"])


TEST_VIDEO_PATTERNS = [
    ("702689313", "702689313"),
    ("702689313", "https://twitch.tv/videos/702689313"),
    ("702689313", "https://www.twitch.tv/videos/702689313"),
]

TEST_CLIP_PATTERNS = {
    ("AbrasivePlayfulMangoMau5", "AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://clips.twitch.tv/AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://www.twitch.tv/dracul1nx/clip/AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://twitch.tv/dracul1nx/clip/AbrasivePlayfulMangoMau5"),
    ("HungryProudRadicchioDoggo", "HungryProudRadicchioDoggo"),
    ("HungryProudRadicchioDoggo", "https://clips.twitch.tv/HungryProudRadicchioDoggo"),
    ("HungryProudRadicchioDoggo", "https://www.twitch.tv/bananasaurus_rex/clip/HungryProudRadicchioDoggo?filter=clips&range=7d&sort=time"),
    ("HungryProudRadicchioDoggo", "https://twitch.tv/bananasaurus_rex/clip/HungryProudRadicchioDoggo?filter=clips&range=7d&sort=time"),
}


@patch("twitchdl.commands._download_clip")
@patch("twitchdl.commands._download_video")
@pytest.mark.parametrize("expected,input", TEST_VIDEO_PATTERNS)
def test_video_patterns(video_dl, clip_dl, expected, input):
    args = Args(video=input)
    download(args)
    video_dl.assert_called_once_with(expected, args)
    clip_dl.assert_not_called()


@patch("twitchdl.commands._download_clip")
@patch("twitchdl.commands._download_video")
@pytest.mark.parametrize("expected,input", TEST_CLIP_PATTERNS)
def test_clip_patterns(video_dl, clip_dl, expected, input):
    args = Args(video=input)
    download(args)
    clip_dl.assert_called_once_with(expected, args)
    video_dl.assert_not_called()
