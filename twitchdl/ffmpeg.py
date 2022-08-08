import asyncio
import json
import logging
import re

from asyncio.subprocess import PIPE
from pprint import pprint
from typing import Optional

from twitchdl.output import print_out


async def join_vods(playlist_path: str, target: str, overwrite: bool, video: dict):
    command = [
        "ffmpeg",
        "-i", playlist_path,
        "-c", "copy",
        "-metadata", "artist={}".format(video["creator"]["displayName"]),
        "-metadata", "title={}".format(video["title"]),
        "-metadata", "encoded_by=twitch-dl",
        "-stats",
        "-loglevel", "warning",
        f"file:{target}",
    ]

    if overwrite:
        command.append("-y")

    # command = ["ls", "-al"]

    print_out("<dim>{}</dim>".format(" ".join(command)))
    process = await asyncio.create_subprocess_exec(*command, stdout=PIPE, stderr=PIPE)

    assert process.stderr is not None

    await asyncio.gather(
        # _read_stream("stdout", process.stdout),
        _print_progress("stderr", process.stderr),
        process.wait()
    )

    print(process.returncode)


async def _read_stream(name: str, stream: Optional[asyncio.StreamReader]):
    if stream:
        async for line in readlines(stream):
            print(name, ">", line)


async def _print_progress(stream: asyncio.StreamReader):
    async for line in readlines(stream):
        print(name, ">", line)


pattern = re.compile(br"[\r\n]+")


async def readlines(stream: asyncio.StreamReader):
    data = bytearray()

    while not stream.at_eof():
        lines = pattern.split(data)
        data[:] = lines.pop(-1)

        for line in lines:
            yield line

        data.extend(await stream.read(1024))


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    video = json.loads('{"id": "1555108011", "title": "Cult of the Lamb", "publishedAt": "2022-08-07T17:00:30Z", "broadcastType": "ARCHIVE", "lengthSeconds": 17948, "game": {"name": "Cult of the Lamb"}, "creator": {"login": "bananasaurus_rex", "displayName": "Bananasaurus_Rex"}, "playlists": [{"bandwidth": 8446533, "resolution": [1920, 1080], "codecs": "avc1.64002A,mp4a.40.2", "video": "chunked", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/chunked/index-dvr.m3u8"}, {"bandwidth": 3432426, "resolution": [1280, 720], "codecs": "avc1.4D0020,mp4a.40.2", "video": "720p60", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/720p60/index-dvr.m3u8"}, {"bandwidth": 1445268, "resolution": [852, 480], "codecs": "avc1.4D001F,mp4a.40.2", "video": "480p30", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/480p30/index-dvr.m3u8"}, {"bandwidth": 215355, "resolution": null, "codecs": "mp4a.40.2", "video": "audio_only", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/audio_only/index-dvr.m3u8"}, {"bandwidth": 705523, "resolution": [640, 360], "codecs": "avc1.4D001E,mp4a.40.2", "video": "360p30", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/360p30/index-dvr.m3u8"}, {"bandwidth": 285614, "resolution": [284, 160], "codecs": "avc1.4D000C,mp4a.40.2", "video": "160p30", "uri": "https://d1m7jfoe9zdc1j.cloudfront.net/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/160p30/index-dvr.m3u8"}]}')
    playlist_path = "/tmp/twitch-dl/278bcbd011d28f96b856_bananasaurus_rex_40035345017_1659891626/160p30/playlist_downloaded.m3u8"
    asyncio.run(join_vods(playlist_path, "out.mkv", True, video), debug=True)
