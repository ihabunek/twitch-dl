import re

from collections import OrderedDict
from datetime import timedelta
from twitchdl.exceptions import ConsoleError


def parse_playlists(data):
    media_pattern = re.compile(r'^#EXT-X-MEDIA:TYPE=VIDEO,GROUP-ID="(?P<group>\w+)",NAME="(?P<name>\w+)"')

    playlists = OrderedDict()
    n = 1
    name = None
    for line in data.split():
        match = re.match(media_pattern, line)
        if match:
            name = match.group('name')
        elif line.startswith('http'):
            playlists[n] = (name, line)
            n += 1

    return playlists


def _get_files(playlist, start, end):
    matches = re.findall(r"#EXTINF:(\d+)(\.\d+)?,.*?\s+(\d+.ts)", playlist)
    vod_start = 0
    for m in matches:
        filename = m[2]
        vod_duration = int(m[0])
        vod_end = vod_start + vod_duration

        # `vod_end > start` is used here becuase it's better to download a bit
        # more than a bit less, similar for the end condition
        start_condition = not start or vod_end > start
        end_condition = not end or vod_start < end

        if start_condition and end_condition:
            yield filename

        vod_start = vod_end


def parse_playlist(url, playlist, start, end):
    base_url = re.sub("/[^/]+$", "/{}", url)

    match = re.search(r"#EXT-X-TWITCH-TOTAL-SECS:(\d+)(.\d+)?", playlist)
    total_seconds = int(match.group(1))

    # Now that video duration is known, validate start and end max values
    if start and start > total_seconds:
        raise ConsoleError("Start time {} greater than video duration {}".format(
            timedelta(seconds=start),
            timedelta(seconds=total_seconds)
        ))

    if end and end > total_seconds:
        raise ConsoleError("End time {} greater than video duration {}".format(
            timedelta(seconds=end),
            timedelta(seconds=total_seconds)
        ))

    files = list(_get_files(playlist, start, end))
    return base_url, files
