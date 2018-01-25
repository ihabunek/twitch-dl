import re

from collections import OrderedDict


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


def parse_playlist(url, data):
    base_url = re.sub("/[^/]+$", "/{}", url)

    filenames = [line for line in data.split() if re.match(r"\d+\.ts", line)]

    return base_url, filenames
