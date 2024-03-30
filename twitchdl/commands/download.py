import asyncio
import platform
import httpx
import m3u8
import os
import re
import shutil
import subprocess
import tempfile

from os import path
from pathlib import Path
from typing import List, Optional, OrderedDict
from urllib.parse import urlparse, urlencode

from twitchdl import twitch, utils
from twitchdl.download import download_file
from twitchdl.entities import Data, DownloadOptions
from twitchdl.exceptions import ConsoleError
from twitchdl.http import download_all
from twitchdl.output import print_out


def download(ids: list[str], args: DownloadOptions):
    for video_id in ids:
        download_one(video_id, args)


def download_one(video: str, args: DownloadOptions):
    video_id = utils.parse_video_identifier(video)
    if video_id:
        return _download_video(video_id, args)

    clip_slug = utils.parse_clip_identifier(video)
    if clip_slug:
        return _download_clip(clip_slug, args)

    raise ConsoleError(f"Invalid input: {video}")


def _parse_playlists(playlists_m3u8):
    playlists = m3u8.loads(playlists_m3u8)

    for p in sorted(playlists.playlists, key=lambda p: p.stream_info.resolution is None):
        if p.stream_info.resolution:
            name = p.media[0].name
            description = "x".join(str(r) for r in p.stream_info.resolution)
        else:
            name = p.media[0].group_id
            description = None

        yield name, description, p.uri


def _get_playlist_by_name(playlists, quality):
    if quality == "source":
        _, _, uri = playlists[0]
        return uri

    for name, _, uri in playlists:
        if name == quality:
            return uri

    available = ", ".join([name for (name, _, _) in playlists])
    msg = f"Quality '{quality}' not found. Available qualities are: {available}"
    raise ConsoleError(msg)


def _select_playlist_interactive(playlists):
    print_out("\nAvailable qualities:")
    for n, (name, resolution, uri) in enumerate(playlists):
        if resolution:
            print_out(f"{n + 1}) <b>{name}</b> <dim>({resolution})</dim>")
        else:
            print_out(f"{n + 1}) <b>{name}</b>")

    no = utils.read_int("Choose quality", min=1, max=len(playlists) + 1, default=1)
    _, _, uri = playlists[no - 1]
    return uri


def _join_vods(playlist_path: str, target: str, overwrite: bool, video):
    description = video["description"] or ""
    description = description.strip()

    command = [
        "ffmpeg",
        "-i", playlist_path,
        "-c", "copy",
        "-metadata", f"artist={video['creator']['displayName']}",
        "-metadata", f"title={video['title']}",
        "-metadata", f"description={description}",
        "-metadata", "encoded_by=twitch-dl",
        "-stats",
        "-loglevel", "warning",
        f"file:{target}",
    ]

    if overwrite:
        command.append("-y")

    print_out(f"<dim>{' '.join(command)}</dim>")
    result = subprocess.run(command)
    if result.returncode != 0:
        raise ConsoleError("Joining files failed")

def _concat_vods(vod_paths: list[str], target: str):
    tool = "type" if platform.system() == "Windows" else "cat"
    command = [tool] + vod_paths

    with open(target, "wb") as target_file:
        result = subprocess.run(command, stdout=target_file)
        if result.returncode != 0:
            raise ConsoleError(f"Joining files failed: {result.stderr}")


def get_video_placeholders(video: Data, format: str) -> Data:
    date, time = video['publishedAt'].split("T")
    game = video["game"]["name"] if video["game"] else "Unknown"

    return {
        "channel": video["creator"]["displayName"],
        "channel_login": video["creator"]["login"],
        "date": date,
        "datetime": video["publishedAt"],
        "format": format,
        "game": game,
        "game_slug": utils.slugify(game),
        "id": video["id"],
        "time": time,
        "title": utils.titlify(video["title"]),
        "title_slug": utils.slugify(video["title"]),
    }


def _video_target_filename(video: Data, args: DownloadOptions):
    subs = get_video_placeholders(video, args.format)

    try:
        return args.output.format(**subs)
    except KeyError as e:
        supported = ", ".join(subs.keys())
        raise ConsoleError(f"Invalid key {e} used in --output. Supported keys are: {supported}")


def _clip_target_filename(clip, args: DownloadOptions):
    date, time = clip["createdAt"].split("T")
    game = clip["game"]["name"] if clip["game"] else "Unknown"

    url = clip["videoQualities"][0]["sourceURL"]
    _, ext = path.splitext(url)
    ext = ext.lstrip(".")

    subs = {
        "channel": clip["broadcaster"]["displayName"],
        "channel_login": clip["broadcaster"]["login"],
        "date": date,
        "datetime": clip["createdAt"],
        "format": ext,
        "game": game,
        "game_slug": utils.slugify(game),
        "id": clip["id"],
        "slug": clip["slug"],
        "time": time,
        "title": utils.titlify(clip["title"]),
        "title_slug": utils.slugify(clip["title"]),
    }

    try:
        return args.output.format(**subs)
    except KeyError as e:
        supported = ", ".join(subs.keys())
        raise ConsoleError(f"Invalid key {e} used in --output. Supported keys are: {supported}")


def _get_vod_paths(playlist, start: Optional[int], end: Optional[int]) -> List[str]:
    """Extract unique VOD paths for download from playlist."""
    files = []
    vod_start = 0
    for segment in playlist.segments:
        vod_end = vod_start + segment.duration

        # `vod_end > start` is used here becuase it's better to download a bit
        # more than a bit less, similar for the end condition
        start_condition = not start or vod_end > start
        end_condition = not end or vod_start < end

        if start_condition and end_condition and segment.uri not in files:
            files.append(segment.uri)

        vod_start = vod_end

    return files


def _crete_temp_dir(base_uri: str) -> str:
    """Create a temp dir to store downloads if it doesn't exist."""
    path = urlparse(base_uri).path.lstrip("/")
    temp_dir = Path(tempfile.gettempdir(), "twitch-dl", path)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return str(temp_dir)


def _get_clip_url(clip, quality):
    qualities = clip["videoQualities"]

    # Quality given as an argument
    if quality:
        if quality == "source":
            return qualities[0]["sourceURL"]

        selected_quality = quality.rstrip("p")  # allow 720p as well as 720
        for q in qualities:
            if q["quality"] == selected_quality:
                return q["sourceURL"]

        available = ", ".join([str(q["quality"]) for q in qualities])
        msg = f"Quality '{quality}' not found. Available qualities are: {available}"
        raise ConsoleError(msg)

    # Ask user to select quality
    print_out("\nAvailable qualities:")
    for n, q in enumerate(qualities):
        print_out(f"{n + 1}) {q['quality']} [{q['frameRate']} fps]")
    print_out()

    no = utils.read_int("Choose quality", min=1, max=len(qualities), default=1)
    selected_quality = qualities[no - 1]
    return selected_quality["sourceURL"]


def get_clip_authenticated_url(slug, quality):
    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_clip_access_token(slug)

    if not access_token:
        raise ConsoleError(f"Access token not found for slug '{slug}'")

    url = _get_clip_url(access_token, quality)

    query = urlencode({
        "sig": access_token["playbackAccessToken"]["signature"],
        "token": access_token["playbackAccessToken"]["value"],
    })

    return f"{url}?{query}"


def _download_clip(slug: str, args: DownloadOptions) -> None:
    print_out("<dim>Looking up clip...</dim>")
    clip = twitch.get_clip(slug)

    if not clip:
        raise ConsoleError(f"Clip '{slug}' not found")


    title = clip["title"]
    user = clip["broadcaster"]["displayName"]
    game = clip["game"]["name"] if clip["game"] else "Unknown"
    duration = utils.format_duration(clip["durationSeconds"])

    print_out(
        f"Found: <green>{title}</green> by <yellow>{user}</yellow>, "+
        f"playing <blue>{game}</blue> ({duration})"
    )

    target = _clip_target_filename(clip, args)
    print_out(f"Target: <blue>{target}</blue>")

    if not args.overwrite and path.exists(target):
        response = input("File exists. Overwrite? [Y/n]: ")
        if response.lower().strip() not in ["", "y"]:
            raise ConsoleError("Aborted")
        args.overwrite = True

    url = get_clip_authenticated_url(slug, args.quality)
    print_out(f"<dim>Selected URL: {url}</dim>")

    print_out("<dim>Downloading clip...</dim>")

    if (args.dry_run is False):
        download_file(url, target)

    print_out(f"Downloaded: <blue>{target}</blue>")


def _download_video(video_id, args: DownloadOptions) -> None:
    if args.start and args.end and args.end <= args.start:
        raise ConsoleError("End time must be greater than start time")

    print_out("<dim>Looking up video...</dim>")
    video = twitch.get_video(video_id)

    if not video:
        raise ConsoleError(f"Video {video_id} not found")

    title = video['title']
    user = video['creator']['displayName']
    print_out(f"Found: <blue>{title}</blue> by <yellow>{user}</yellow>")

    target = _video_target_filename(video, args)
    print_out(f"Output: <blue>{target}</blue>")

    if not args.overwrite and path.exists(target):
        response = input("File exists. Overwrite? [Y/n]: ")
        if response.lower().strip() not in ["", "y"]:
            raise ConsoleError("Aborted")
        args.overwrite = True

    # Chapter select or manual offset
    start, end = _determine_time_range(video_id, args)

    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_access_token(video_id, auth_token=args.auth_token)

    print_out("<dim>Fetching playlists...</dim>")
    playlists_m3u8 = twitch.get_playlists(video_id, access_token)
    playlists = list(_parse_playlists(playlists_m3u8))
    playlist_uri = (_get_playlist_by_name(playlists, args.quality) if args.quality
            else _select_playlist_interactive(playlists))

    print_out("<dim>Fetching playlist...</dim>")
    response = httpx.get(playlist_uri)
    response.raise_for_status()
    playlist = m3u8.loads(response.text)

    base_uri = re.sub("/[^/]+$", "/", playlist_uri)
    target_dir = _crete_temp_dir(base_uri)
    vod_paths = _get_vod_paths(playlist, start, end)

    # Save playlists for debugging purposes
    with open(path.join(target_dir, "playlists.m3u8"), "w") as f:
        f.write(playlists_m3u8)
    with open(path.join(target_dir, "playlist.m3u8"), "w") as f:
        f.write(response.text)

    print_out(f"\nDownloading {len(vod_paths)} VODs using {args.max_workers} workers to {target_dir}")
    sources = [base_uri + path for path in vod_paths]
    targets = [os.path.join(target_dir, f"{k:05d}.ts") for k, _ in enumerate(vod_paths)]
    asyncio.run(download_all(sources, targets, args.max_workers, rate_limit=args.rate_limit))

    # Make a modified playlist which references downloaded VODs
    # Keep only the downloaded segments and skip the rest
    org_segments = playlist.segments.copy()

    path_map = OrderedDict(zip(vod_paths, targets))
    playlist.segments.clear()
    for segment in org_segments:
        if segment.uri in path_map:
            segment.uri = path_map[segment.uri]
            playlist.segments.append(segment)

    playlist_path = path.join(target_dir, "playlist_downloaded.m3u8")
    playlist.dump(playlist_path)

    print_out("")

    if args.no_join:
        print_out("<dim>Skipping joining files...</dim>")
        print_out(f"VODs downloaded to:\n<blue>{target_dir}</blue>")
        return

    if args.concat:
        print_out("<dim>Concating files...</dim>")
        _concat_vods(targets, target)
    else:
        print_out("<dim>Joining files...</dim>")
        _join_vods(playlist_path, target, args.overwrite, video)

    if args.keep:
        print_out(f"\n<dim>Temporary files not deleted: {target_dir}</dim>")
    else:
        print_out("\n<dim>Deleting temporary files...</dim>")
        shutil.rmtree(target_dir)

    print_out(f"\nDownloaded: <green>{target}</green>")


def _determine_time_range(video_id, args: DownloadOptions):
    if args.start or args.end:
        return args.start, args.end

    if args.chapter is not None:
        print_out("<dim>Fetching chapters...</dim>")
        chapters = twitch.get_video_chapters(video_id)

        if not chapters:
            raise ConsoleError("This video has no chapters")

        if args.chapter == 0:
            chapter = _choose_chapter_interactive(chapters)
        else:
            try:
                chapter = chapters[args.chapter - 1]
            except IndexError:
                raise ConsoleError(f"Chapter {args.chapter} does not exist. This video has {len(chapters)} chapters.")

        print_out(f'Chapter selected: <blue>{chapter["description"]}</blue>\n')
        start = chapter["positionMilliseconds"] // 1000
        duration = chapter["durationMilliseconds"] // 1000
        return start, start + duration

    return None, None


def _choose_chapter_interactive(chapters):
    print_out("\nChapters:")
    for index, chapter in enumerate(chapters):
        duration = utils.format_time(chapter["durationMilliseconds"] // 1000)
        print_out(f'{index + 1}) <b>{chapter["description"]}</b> <dim>({duration})</dim>')
    index = utils.read_int("Select a chapter", 1, len(chapters))
    chapter = chapters[index - 1]
    return chapter
