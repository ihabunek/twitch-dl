from twitchdl.playlists import Vod, filter_vods


def test_filter_vods():
    vods = [Vod(index, path=f"vod_{index}.ts", duration=10.0) for index in range(100)]

    # No cropping required
    filtered_vods, crop_start, crop_duration = filter_vods(vods, 60, 120)
    assert filtered_vods[0].index == 6
    assert filtered_vods[-1].index == 11
    assert crop_start is None
    assert crop_duration is None

    # Croping required at start
    filtered_vods, crop_start, crop_duration = filter_vods(vods, 63, 120)
    assert filtered_vods[0].index == 6
    assert filtered_vods[-1].index == 11
    assert crop_start == 3
    assert crop_duration is None

    # Croping required at end
    filtered_vods, crop_start, crop_duration = filter_vods(vods, 60, 115)
    assert filtered_vods[0].index == 6
    assert filtered_vods[-1].index == 11
    assert crop_start is None
    assert crop_duration == 55

    # Croping required at start and end
    filtered_vods, crop_start, crop_duration = filter_vods(vods, 63, 115)
    assert filtered_vods[0].index == 6
    assert filtered_vods[-1].index == 11
    assert crop_start == 3
    assert crop_duration == 52
