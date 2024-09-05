import asyncio
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import click
import httpx

from twitchdl import twitch, utils
from twitchdl.entities import DownloadOptions
from twitchdl.exceptions import ConsoleError
from twitchdl.http import download_all, download_file
from twitchdl.naming import clip_filename, video_filename
from twitchdl.output import blue, bold, green, print_log, yellow
from twitchdl.playlists import (
    enumerate_vods,
    get_init_sections,
    load_m3u8,
    make_join_playlist,
    parse_playlists,
    select_playlist,
)
from twitchdl.twitch import Chapter, ClipAccessToken, Video


def download(ids: List[str], args: DownloadOptions):
    if not ids:
        print_log("No IDs to downlad given")
        return

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


def _join_vods(playlist_path: Path, metadata_path: Path, target: Path, overwrite: bool):
    command: List[str] = [
        "ffmpeg",
        "-i",
        str(playlist_path),
        "-i",
        str(metadata_path),
        "-map_metadata",
        "1",
        "-c",
        "copy",
        "-stats",
        "-loglevel",
        "warning",
        f"file:{target}",
    ]

    if overwrite:
        command.append("-y")

    click.secho(f"{shlex.join(command)}", dim=True)
    result = subprocess.run(command)
    if result.returncode != 0:
        raise ConsoleError("Joining files failed")


def _concat_vods(vod_paths: List[Path], target: Path):
    tool = "type" if platform.system() == "Windows" else "cat"
    command = [tool] + [str(p) for p in vod_paths]

    with open(target, "wb") as target_file:
        result = subprocess.run(command, stdout=target_file)
        if result.returncode != 0:
            raise ConsoleError(f"Joining files failed: {result.stderr}")


def _crete_temp_dir(base_uri: str) -> Path:
    """Create a temp dir to store downloads if it doesn't exist."""
    path = urlparse(base_uri).path.lstrip("/")
    temp_dir = Path(tempfile.gettempdir(), "twitch-dl", path)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def _get_clip_url(access_token: ClipAccessToken, quality: Optional[str]) -> str:
    qualities = access_token["videoQualities"]

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
    click.echo("\nAvailable qualities:")
    for n, q in enumerate(qualities):
        click.echo(f"{n + 1}) {bold(q['quality'])} [{q['frameRate']} fps]")
    click.echo()

    no = utils.read_int("Choose quality", min=1, max=len(qualities), default=1)
    selected_quality = qualities[no - 1]
    return selected_quality["sourceURL"]


def get_clip_authenticated_url(slug: str, quality: Optional[str]):
    print_log("Fetching access token...")
    access_token = twitch.get_clip_access_token(slug)

    if not access_token:
        raise ConsoleError(f"Access token not found for slug '{slug}'")

    url = _get_clip_url(access_token, quality)

    query = urlencode(
        {
            "sig": access_token["playbackAccessToken"]["signature"],
            "token": access_token["playbackAccessToken"]["value"],
        }
    )

    return f"{url}?{query}"


def _download_clip(slug: str, args: DownloadOptions) -> None:
    print_log("Looking up clip...")
    clip = twitch.get_clip(slug)

    if not clip:
        raise ConsoleError(f"Clip '{slug}' not found")

    title = clip["title"]
    user = clip["broadcaster"]["displayName"]
    game = clip["game"]["name"] if clip["game"] else "Unknown"
    duration = utils.format_duration(clip["durationSeconds"])
    click.echo(f"Found: {green(title)} by {yellow(user)}, playing {blue(game)} ({duration})")

    target = Path(clip_filename(clip, args.output))
    click.echo(f"Target: {blue(target)}")

    if not args.overwrite and target.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()
        args.overwrite = True

    url = get_clip_authenticated_url(slug, args.quality)
    print_log(f"Selected URL: {url}")

    if args.dry_run:
        click.echo("Dry run, clip not downloaded.")
    else:
        print_log("Downloading clip...")
        download_file(url, target)
        click.echo(f"Downloaded: {blue(target)}")


def _download_video(video_id: str, args: DownloadOptions) -> None:
    if args.start and args.end and args.end <= args.start:
        raise ConsoleError("End time must be greater than start time")

    print_log("Looking up video...")
    video = twitch.get_video(video_id)

    if not video:
        raise ConsoleError(f"Video {video_id} not found")

    click.echo(f"Found: {blue(video['title'])} by {yellow(video['creator']['displayName'])}")

    target = Path(video_filename(video, args.format, args.output))
    click.echo(f"Output: {blue(target)}")

    if not args.overwrite and target.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()
        args.overwrite = True

    print_log("Fetching chapters...")
    chapters = twitch.get_video_chapters(video_id)
    start, end = _determine_time_range(chapters, args)

    print_log("Fetching access token...")
    access_token = twitch.get_access_token(video_id, auth_token=args.auth_token)

    print_log("Fetching playlists...")
    playlists_text = twitch.get_playlists(video_id, access_token)
    playlists = parse_playlists(playlists_text)
    playlist = select_playlist(playlists, args.quality)

    print_log("Fetching playlist...")
    vods_text = http_get(playlist.url)
    vods_m3u8 = load_m3u8(vods_text)
    vods = enumerate_vods(vods_m3u8, start, end)

    if args.dry_run:
        click.echo("Dry run, video not downloaded.")
        return

    base_uri = re.sub("/[^/]+$", "/", playlist.url)
    target_dir = _crete_temp_dir(base_uri)

    # Create ffmpeg metadata file
    metadata_path = target_dir / "metadata.txt"
    _write_metadata(video, chapters, metadata_path)

    # Save playlists for debugging purposes
    with open(target_dir / "playlists.m3u8", "w") as f:
        f.write(playlists_text)
    with open(target_dir / "playlist.m3u8", "w") as f:
        f.write(vods_text)

    init_sections = get_init_sections(vods_m3u8)
    for uri in init_sections:
        print_log(f"Downloading init section {uri}...")
        download_file(f"{base_uri}{uri}", target_dir / uri)

    print_log(f"Downloading {len(vods)} VODs using {args.max_workers} workers to {target_dir}")

    sources = [base_uri + vod.path for vod in vods]
    targets = [target_dir / f"{vod.index:05d}.ts" for vod in vods]

    asyncio.run(
        download_all(
            zip(sources, targets),
            args.max_workers,
            rate_limit=args.rate_limit,
            count=len(vods),
        )
    )

    join_playlist = make_join_playlist(vods_m3u8, vods, targets)
    join_playlist_path = target_dir / "playlist_downloaded.m3u8"
    join_playlist.dump(join_playlist_path)  # type: ignore
    click.echo()

    if args.no_join:
        print_log("Skipping joining files...")
        click.echo(f"VODs downloaded to:\n{blue(target_dir)}")
        return

    if args.concat:
        print_log("Concating files...")
        _concat_vods(targets, target)
    else:
        print_log("Joining files...")
        _join_vods(join_playlist_path, metadata_path, target, args.overwrite)

    click.echo()

    if args.keep:
        click.echo(f"Temporary files not deleted: {yellow(target_dir)}")
    else:
        print_log("Deleting temporary files...")
        shutil.rmtree(target_dir)

    click.echo(f"Downloaded: {green(target)}")


def http_get(url: str) -> str:
    response = httpx.get(url)
    response.raise_for_status()
    return response.text


def _determine_time_range(chapters: List[Chapter], args: DownloadOptions):
    if args.start or args.end:
        return args.start, args.end

    if args.chapter is not None:
        if not chapters:
            raise ConsoleError("This video has no chapters")

        if args.chapter == 0:
            chapter = _choose_chapter_interactive(chapters)
        else:
            try:
                chapter = chapters[args.chapter - 1]
            except IndexError:
                raise ConsoleError(
                    f"Chapter {args.chapter} does not exist. This video has {len(chapters)} chapters."
                )

        click.echo(f'Chapter selected: {blue(chapter["description"])}\n')
        start = chapter["positionMilliseconds"] // 1000
        duration = chapter["durationMilliseconds"] // 1000
        return start, start + duration

    return None, None


def _choose_chapter_interactive(chapters: List[Chapter]):
    click.echo("\nChapters:")
    for index, chapter in enumerate(chapters):
        duration = utils.format_time(chapter["durationMilliseconds"] // 1000)
        click.echo(f'{index + 1}) {bold(chapter["description"])} ({duration})')
    index = utils.read_int("Select a chapter", 1, len(chapters))
    chapter = chapters[index - 1]
    return chapter


# See: https://ffmpeg.org/ffmpeg-formats.html#Metadata-2
def _write_metadata(video: Video, chapters: List[Chapter], path: Path):
    with open(path, "w") as f:
        # Header
        f.write(";FFMETADATA1\n")

        # Global metadata
        f.write(f"title={_escape_metadata(video['title'])}\n")
        f.write(f"artist={_escape_metadata(video['creator']['displayName'])}\n")
        f.write(f"description={_escape_metadata(video['description'])}\n")
        f.write("encoded_by=twitch-dl\n")

        # Chapter metadata
        for chapter in chapters:
            title = chapter["description"]
            start = chapter["positionMilliseconds"]
            end = chapter["positionMilliseconds"] + chapter["durationMilliseconds"]

            f.write("\n[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start}\n")
            f.write(f"END={end}\n")
            f.write(f"title={title}\n")


def _escape_metadata(text: Optional[str]):
    #  Metadata keys or values containing special characters
    # (‘=’, ‘;’, ‘#’, ‘\’ and a newline) must be escaped with a backslash ‘\’.
    text = text.strip() if text else ""
    return re.sub(r"([=;#\\\n])", r"\\\1", text.strip())
