from decimal import Decimal

from twitchdl.commands.download import filter_vods
from twitchdl.playlists import Vod

VODS = [
    Vod(index=1, path="1.ts", duration=Decimal("10.0")),
    Vod(index=2, path="2.ts", duration=Decimal("10.0")),
    Vod(index=3, path="3.ts", duration=Decimal("10.0")),
    Vod(index=4, path="4.ts", duration=Decimal("10.0")),
    Vod(index=5, path="5.ts", duration=Decimal("10.0")),
    Vod(index=6, path="6.ts", duration=Decimal("10.0")),
    Vod(index=7, path="7.ts", duration=Decimal("10.0")),
    Vod(index=8, path="8.ts", duration=Decimal("10.0")),
    Vod(index=9, path="9.ts", duration=Decimal("10.0")),
    Vod(index=10, path="10.ts", duration=Decimal("3.15")),
]


def test_filter_vods_no_start_no_end():
    vods, start_offset, duration = filter_vods(VODS, None, None)
    assert vods == VODS
    assert start_offset == Decimal("0")
    assert duration == Decimal("93.15")


def test_filter_vods_start():
    # Zero offset
    vods, start_offset, duration = filter_vods(VODS, 0, None)
    assert [v.index for v in vods] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert start_offset == Decimal("0")
    assert duration == Decimal("93.15")

    # Mid-vod
    vods, start_offset, duration = filter_vods(VODS, 13, None)
    assert [v.index for v in vods] == [2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert start_offset == Decimal("3.0")
    assert duration == Decimal("80.15")

    # Between vods
    vods, start_offset, duration = filter_vods(VODS, 50, None)
    assert [v.index for v in vods] == [6, 7, 8, 9, 10]
    assert start_offset == Decimal("0")
    assert duration == Decimal("43.15")

    # Close to end
    vods, start_offset, duration = filter_vods(VODS, 93, None)
    assert [v.index for v in vods] == [10]
    assert start_offset == Decimal("3.0")
    assert duration == Decimal("0.15")


def test_filter_vods_end():
    # Zero offset
    vods, start_offset, duration = filter_vods(VODS, 0, None)
    assert [v.index for v in vods] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert start_offset == Decimal("0")
    assert duration == Decimal("93.15")

    # Mid-vod
    vods, start_offset, duration = filter_vods(VODS, None, 56)
    assert [v.index for v in vods] == [1, 2, 3, 4, 5, 6]
    assert start_offset == Decimal("0")
    assert duration == Decimal("56")

    # Between vods
    vods, start_offset, duration = filter_vods(VODS, None, 30)
    assert [v.index for v in vods] == [1, 2, 3]
    assert start_offset == Decimal("0")
    assert duration == Decimal("30")


def test_filter_vods_start_end():
    # Zero offset
    vods, start_offset, duration = filter_vods(VODS, 0, 0)
    assert [v.index for v in vods] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert start_offset == Decimal("0")
    assert duration == Decimal("93.15")

    # Mid-vod
    vods, start_offset, duration = filter_vods(VODS, 32, 56)
    assert [v.index for v in vods] == [4, 5, 6]
    assert start_offset == Decimal("2")
    assert duration == Decimal("24")

    # Between vods
    vods, start_offset, duration = filter_vods(VODS, 20, 60)
    assert [v.index for v in vods] == [3, 4, 5, 6]
    assert start_offset == Decimal("0")
    assert duration == Decimal("40")
