"""
Parse and manipulate m3u8 playlists.
"""

from dataclasses import dataclass
from typing import Generator, List, Optional, OrderedDict

import click
import m3u8

from twitchdl import utils
from twitchdl.output import bold, dim, print_table


@dataclass
class Playlist:
    name: str
    group_id: str
    resolution: Optional[str]
    url: str
    is_source: bool


@dataclass
class Vod:
    index: int
    """Ordinal number of the VOD in the playlist"""
    path: str
    """Path part of the VOD URL"""
    duration: int
    """Segment duration in seconds"""


def parse_playlists(playlists_m3u8: str) -> List[Playlist]:
    def _parse(source: str) -> Generator[Playlist, None, None]:
        document = load_m3u8(source)

        for p in document.playlists:
            resolution = (
                "x".join(str(r) for r in p.stream_info.resolution)
                if p.stream_info.resolution
                else None
            )

            media = p.media[0]
            is_source = media.group_id == "chunked"
            yield Playlist(media.name, media.group_id, resolution, p.uri, is_source)

    return list(_parse(playlists_m3u8))


def load_m3u8(playlist_m3u8: str) -> m3u8.M3U8:
    return m3u8.loads(playlist_m3u8)


def enumerate_vods(
    document: m3u8.M3U8,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> List[Vod]:
    """Extract VODs for download from document."""
    vods = []
    vod_start = 0

    for index, segment in enumerate(document.segments):
        vod_end = vod_start + segment.duration

        # `vod_end > start` is used here becuase it's better to download a bit
        # more than a bit less, similar for the end condition
        start_condition = not start or vod_end > start
        end_condition = not end or vod_start < end

        if start_condition and end_condition:
            vods.append(Vod(index, segment.uri, segment.duration))

        vod_start = vod_end

    return vods


def make_join_playlist(
    playlist: m3u8.M3U8,
    vods: List[Vod],
    targets: List[str],
) -> m3u8.Playlist:
    """
    Make a modified playlist which references downloaded VODs
    Keep only the downloaded segments and skip the rest
    """
    org_segments = playlist.segments.copy()

    path_map = OrderedDict(zip([v.path for v in vods], targets))
    playlist.segments.clear()
    for segment in org_segments:
        if segment.uri in path_map:
            segment.uri = path_map[segment.uri]
            playlist.segments.append(segment)

    return playlist


def select_playlist(playlists: List[Playlist], quality: Optional[str]) -> Playlist:
    return (
        select_playlist_by_name(playlists, quality)
        if quality is not None
        else select_playlist_interactive(playlists)
    )


def select_playlist_by_name(playlists: List[Playlist], quality: str) -> Playlist:
    if quality == "source":
        for playlist in playlists:
            if playlist.is_source:
                return playlist
        raise click.ClickException("Source quality not found, please report an issue on github.")

    for playlist in playlists:
        if playlist.name == quality or playlist.group_id == quality:
            return playlist

    available = ", ".join([p.name for p in playlists])
    msg = f"Quality '{quality}' not found. Available qualities are: {available}"
    raise click.ClickException(msg)


def select_playlist_interactive(playlists: List[Playlist]) -> Playlist:
    playlists = sorted(playlists, key=_playlist_key)
    headers = ["#", "Name", "Group ID", "Resolution"]

    rows = [
        [
            f"{n + 1})",
            bold(playlist.name),
            dim(playlist.group_id),
            dim(playlist.resolution or ""),
        ]
        for n, playlist in enumerate(playlists)
    ]

    click.echo()
    print_table(headers, rows)

    default = 1
    for index, playlist in enumerate(playlists):
        if playlist.is_source:
            default = index + 1

    no = utils.read_int("\nChoose quality", min=1, max=len(playlists) + 1, default=default)
    playlist = playlists[no - 1]
    return playlist


MAX = 1_000_000


def _playlist_key(playlist: Playlist) -> int:
    """Attempt to sort playlists so that source quality is on top, audio only
    is on bottom and others are sorted descending by resolution."""
    if playlist.is_source:
        return 0

    if playlist.group_id == "audio_only":
        return MAX

    try:
        return MAX - int(playlist.name.split("p")[0])
    except Exception:
        pass

    return MAX
