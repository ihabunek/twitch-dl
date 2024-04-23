"""
Parse and manipulate m3u8 playlists.
"""

from dataclasses import dataclass
from typing import Generator, Optional, OrderedDict

import click
import m3u8

from twitchdl import utils
from twitchdl.output import bold, dim


@dataclass
class Playlist:
    name: str
    resolution: Optional[str]
    url: str


@dataclass
class Vod:
    index: int
    """Ordinal number of the VOD in the playlist"""
    path: str
    """Path part of the VOD URL"""
    duration: int
    """Segment duration in seconds"""


def parse_playlists(playlists_m3u8: str):
    def _parse(source: str) -> Generator[Playlist, None, None]:
        document = load_m3u8(source)

        for p in document.playlists:
            if p.stream_info.resolution:
                name = p.media[0].name
                resolution = "x".join(str(r) for r in p.stream_info.resolution)
            else:
                name = p.media[0].group_id
                resolution = None

            yield Playlist(name, resolution, p.uri)

    # Move audio to bottom, it has no resolution
    return sorted(_parse(playlists_m3u8), key=lambda p: p.resolution is None)


def load_m3u8(playlist_m3u8: str) -> m3u8.M3U8:
    return m3u8.loads(playlist_m3u8)


def enumerate_vods(
    document: m3u8.M3U8,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> list[Vod]:
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
    vods: list[Vod],
    targets: list[str],
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


def select_playlist(playlists: list[Playlist], quality: Optional[str]) -> Playlist:
    return (
        select_playlist_by_name(playlists, quality)
        if quality is not None
        else select_playlist_interactive(playlists)
    )


def select_playlist_by_name(playlists: list[Playlist], quality: str) -> Playlist:
    if quality == "source":
        return playlists[0]

    for playlist in playlists:
        if playlist.name == quality:
            return playlist

    available = ", ".join([p.name for p in playlists])
    msg = f"Quality '{quality}' not found. Available qualities are: {available}"
    raise click.ClickException(msg)


def select_playlist_interactive(playlists: list[Playlist]) -> Playlist:
    click.echo("\nAvailable qualities:")
    for n, playlist in enumerate(playlists):
        if playlist.resolution:
            click.echo(f"{n + 1}) {bold(playlist.name)} {dim(f'({playlist.resolution})')}")
        else:
            click.echo(f"{n + 1}) {bold(playlist.name)}")

    no = utils.read_int("Choose quality", min=1, max=len(playlists) + 1, default=1)
    playlist = playlists[no - 1]
    return playlist
