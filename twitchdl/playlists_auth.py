import json
import re
import shutil
import subprocess
from typing import List, NamedTuple, Optional
from urllib.parse import urlparse

import httpx

from twitchdl.entities import Video
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_warning
from twitchdl.playlists import Playlist, load_m3u8


class Resolution(NamedTuple):
    name: str
    group_id: str
    resolution: Optional[str]
    is_source: bool


# Known video resolutions on Twitch
RESOLUTIONS = [
    Resolution(name="1080p60", group_id="1080p60", resolution="1920x1080", is_source=False),
    Resolution(name="1080p", group_id="1080p30", resolution="1920x1080", is_source=False),
    Resolution(name="720p60", group_id="720p60", resolution="1280x720", is_source=False),
    Resolution(name="720p", group_id="720p30", resolution="1280x720", is_source=False),
    Resolution(name="480p", group_id="480p30", resolution="852x480", is_source=False),
    Resolution(name="360p", group_id="360p30", resolution="640x360", is_source=False),
    Resolution(name="160p", group_id="160p30", resolution="284x160", is_source=False),
    Resolution(name="144p", group_id="144p30", resolution="256x144", is_source=False),
    Resolution(name="Audio Only", group_id="audio_only", resolution=None, is_source=False),
]


def get_subonly_playlists(video: Video) -> List[Playlist]:
    """
    Attempt to get a list playlists for a given video without fetching them
    from Twitch directly.

    Used for sub-only videos which return HTTP 403 when fetching playlists.
    """
    source_playlist = get_source_playlist(video)
    other_playlists = [get_playlist(video, r) for r in RESOLUTIONS]
    playlists = [source_playlist] + other_playlists
    playlists = [p for p in playlists if p]

    if not playlists:
        raise ConsoleError(
            "Failed detecting sub-only playlists. "
            + "Use an auth token and/or report an issue to twitch-dl."
        )

    return playlists


def get_source_playlist(video: Video) -> Optional[Playlist]:
    """Source playlist is special because we cannot predict the resolution and
    framerate."""
    group_id = "chunked"
    playlist_url = get_playlist_url(video, group_id)
    with httpx.Client() as client:
        response = client.get(playlist_url)
        if not response.is_success:
            return None

        resolution = detect_source_resolution(playlist_url, response.text, group_id)
        # Don't break if unable to determine source stream parameters
        if not resolution:
            return Playlist(
                name="source",
                group_id=group_id,
                resolution="???",
                url=playlist_url,
                is_source=True,
            )

        return Playlist(
            name=resolution.name,
            group_id=resolution.group_id,
            resolution=resolution.resolution,
            url=playlist_url,
            is_source=True,
        )


def get_playlist(video: Video, resolution: Resolution) -> Optional[Playlist]:
    url = get_playlist_url(video, resolution.group_id)
    with httpx.Client() as client:
        response = client.get(url)
        if response.is_success:
            return Playlist(
                name=resolution.name,
                group_id=resolution.group_id,
                resolution=resolution.resolution,
                url=url,
                is_source=False,
            )


def get_playlist_url(video: Video, group_id: str):
    broadcast_type = video["broadcastType"]
    owner_login = video["owner"]["login"]

    previews_url = urlparse(video["seekPreviewsURL"])
    domain = previews_url.hostname
    paths = previews_url.path.split("/")
    vod_special_id = paths[paths.index("storyboards") - 1]

    if broadcast_type == "HIGHLIGHT":
        return f"https://{domain}/{vod_special_id}/{group_id}/highlight-{video['id']}.m3u8"

    if broadcast_type == "UPLOAD":
        return f"https://{domain}/{owner_login}/{video['id']}/{vod_special_id}/{group_id}/index-dvr.m3u8"

    if broadcast_type == "ARCHIVE":
        return f"https://{domain}/{vod_special_id}/{group_id}/index-dvr.m3u8"

    raise ConsoleError(f"Unknown broadcast type: {broadcast_type}")


def detect_source_resolution(
    playlist_url: str,
    playlists: str,
    group_id: str,
) -> Optional[Resolution]:
    """Attempt to determine video resolution and framerate by examining the first
    VOD in the playlist via ffprobe."""
    m3u8 = load_m3u8(playlists)
    vod_path = m3u8.segments[0].uri
    assert vod_path is not None
    base_url = re.sub("/[^/]+$", "/", playlist_url)
    vod_url = base_url + vod_path.replace("-unmuted", "-muted")

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        print_warning("ffprobe not found, cannot detect source resulution")
        return None

    process = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "v",
            vod_url,
        ],
        stdout=subprocess.PIPE,
    )

    if process.returncode != 0:
        print_warning("failed detecting source resolution")
        return None

    data = json.loads(process.stdout)
    stream = data["streams"][0]
    resolution = f"{stream['width']}x{stream['height']}"

    frame_rate_raw = stream["r_frame_rate"]
    frame_rate = _parse_frame_rate(frame_rate_raw)
    if not frame_rate:
        print_warning(f"failed detecting frame rate, cannot parse '{frame_rate_raw}'")
        return None

    # 30fps streams are named 1080p, 60fps streams are named 1080p60
    name = f"{stream['height']}p" if frame_rate == 30 else f"{stream['height']}p{frame_rate}"

    return Resolution(
        name=name,
        group_id=group_id,
        resolution=resolution,
        is_source=True,
    )


def _parse_frame_rate(value: str) -> Optional[int]:
    # Frame rate reported by ffprobe is usually "30/1" or "60/1"
    # Do the math to avoid cases where the second number is not 1
    try:
        left, right = value.split("/")
        return round(int(left) / int(right))
    except Exception:
        return None
