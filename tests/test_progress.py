from pathlib import Path

from twitchdl.progress import VideoDownloadProgress


def test_initial_values():
    progress = VideoDownloadProgress(10)
    assert progress.downloaded == 0
    assert progress.estimated_total is None
    assert progress.progress_perc == 0
    assert progress.remaining_time is None
    assert progress.speed is None
    assert progress.file_count == 10
    assert progress.downloaded_count == 0


def test_downloaded():
    progress = VideoDownloadProgress(3)
    progress.start(1, "foo1", Path("foo1"), 300)
    progress.start(2, "foo2", Path("foo2"), 300)
    progress.start(3, "foo3", Path("foo3"), 300)

    assert progress.downloaded == 0
    assert progress.progress_bytes == 0
    assert progress.progress_perc == 0

    progress.advance(1, 100)
    progress._recalculate()
    assert progress.downloaded == 100
    assert progress.progress_bytes == 100
    assert progress.progress_perc == 11

    progress.advance(2, 200)
    progress._recalculate()
    assert progress.downloaded == 300
    assert progress.progress_bytes == 300
    assert progress.progress_perc == 33

    progress.advance(3, 150)
    progress._recalculate()
    assert progress.downloaded == 450
    assert progress.progress_bytes == 450
    assert progress.progress_perc == 50

    progress.advance(1, 50)
    progress._recalculate()
    assert progress.downloaded == 500
    assert progress.progress_bytes == 500
    assert progress.progress_perc == 55

    progress.abort(2, Exception())
    progress._recalculate()
    assert progress.downloaded == 500
    assert progress.progress_bytes == 300
    assert progress.progress_perc == 33

    progress.start(2, "foo2", Path("foo2"), 300)

    progress.advance(1, 150)
    progress.advance(2, 300)
    progress.advance(3, 150)
    progress._recalculate()

    assert progress.downloaded == 1100
    assert progress.progress_bytes == 900
    assert progress.progress_perc == 100

    progress.end(1)
    progress.end(2)
    progress.end(3)

    assert progress.downloaded == 1100
    assert progress.progress_bytes == 900
    assert progress.progress_perc == 100


def test_estimated_total():
    progress = VideoDownloadProgress(3)
    assert progress.estimated_total is None

    progress.start(1, "foo1", Path("foo1"), 12000)
    progress._recalculate()
    assert progress.estimated_total == 12000 * 3

    progress.start(2, "foo2", Path("foo2"), 11000)
    progress._recalculate()
    assert progress.estimated_total == 11500 * 3

    progress.start(3, "foo3", Path("foo3"), 10000)
    progress._recalculate()
    assert progress.estimated_total == 11000 * 3


def test_vod_downloaded_count():
    progress = VideoDownloadProgress(3)

    progress.start(1, "foo1", Path("foo1"), 100)
    progress.start(2, "foo2", Path("foo2"), 100)
    progress.start(3, "foo3", Path("foo3"), 100)

    assert progress.downloaded_count == 0

    progress.advance(1, 100)
    progress.end(1)
    assert progress.downloaded_count == 1

    progress.advance(2, 100)
    progress.end(2)
    assert progress.downloaded_count == 2

    progress.advance(3, 100)
    progress.end(3)
    assert progress.downloaded_count == 3
