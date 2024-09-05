import pytest

from twitchdl.utils import parse_clip_identifier, parse_video_identifier

TEST_VIDEO_PATTERNS = [
    ("702689313", "702689313"),
    ("702689313", "https://twitch.tv/videos/702689313"),
    ("702689313", "https://www.twitch.tv/videos/702689313"),
    ("702689313", "https://m.twitch.tv/videos/702689313"),
    ("2223719525", "https://www.twitch.tv/r0dn3y/video/2223719525"),
]

TEST_CLIP_PATTERNS = {
    ("AbrasivePlayfulMangoMau5", "AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://clips.twitch.tv/AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://www.twitch.tv/dracul1nx/clip/AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://m.twitch.tv/dracul1nx/clip/AbrasivePlayfulMangoMau5"),
    ("AbrasivePlayfulMangoMau5", "https://twitch.tv/dracul1nx/clip/AbrasivePlayfulMangoMau5"),
    ("HungryProudRadicchioDoggo", "HungryProudRadicchioDoggo"),
    ("HungryProudRadicchioDoggo", "https://clips.twitch.tv/HungryProudRadicchioDoggo"),
    ("HungryProudRadicchioDoggo", "https://www.twitch.tv/bananasaurus_rex/clip/HungryProudRadicchioDoggo?filter=clips&range=7d&sort=time"),
    ("HungryProudRadicchioDoggo", "https://m.twitch.tv/bananasaurus_rex/clip/HungryProudRadicchioDoggo?filter=clips&range=7d&sort=time"),
    ("HungryProudRadicchioDoggo", "https://twitch.tv/bananasaurus_rex/clip/HungryProudRadicchioDoggo?filter=clips&range=7d&sort=time"),
    ("GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ", "GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ"),
    ("GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ", "https://twitch.tv/dracul1nx/clip/GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ"),
    ("GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ", "https://twitch.tv/dracul1nx/clip/GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ?filter=clips&range=7d&sort=time"),
    ("GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ", "https://www.twitch.tv/dracul1nx/clip/GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ?filter=clips&range=7d&sort=time"),
    ("GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ", "https://m.twitch.tv/dracul1nx/clip/GloriousColdbloodedTortoiseRuleFive-E017utJ4DZmHVpfQ?filter=clips&range=7d&sort=time"),

    # Can contain underscores
    ("TemperedGlamorousSpiderMikeHogu-u0r0y1y_lKQ_BDAP", "TemperedGlamorousSpiderMikeHogu-u0r0y1y_lKQ_BDAP"),
    ("TemperedGlamorousSpiderMikeHogu-u0r0y1y_lKQ_BDAP", "https://www.twitch.tv/tsoding/clip/TemperedGlamorousSpiderMikeHogu-u0r0y1y_lKQ_BDAP?filter=clips&range=all&sort=time"),
}


@pytest.mark.parametrize("expected,input", TEST_VIDEO_PATTERNS)
def test_video_patterns(expected: str, input: str):
    assert parse_video_identifier(input) == expected


@pytest.mark.parametrize("expected,input", TEST_CLIP_PATTERNS)
def test_clip_patterns(expected: str, input: str):
    assert parse_clip_identifier(input) == expected
