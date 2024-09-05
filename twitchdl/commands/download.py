import asyncio
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode, urlparse

import click
import httpx

from twitchdl import twitch, utils
from twitchdl.entities import Clip, DownloadOptions
from twitchdl.exceptions import ConsoleError
from twitchdl.http import download_all, download_file
from twitchdl.naming import clip_filename, video_filename
from twitchdl.output import blue, bold, green, print_error, print_log, underlined, yellow
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


def download_one(id_or_slug: str, args: DownloadOptions):
    video_id = utils.parse_video_identifier(id_or_slug)
    if video_id:
        print_log("Looking up video...")
        video = twitch.get_video(video_id)
        if video:
            _download_video(video, args)
        else:
            print_error(f"Video '{video_id}' not found")
        return

    slug = utils.parse_clip_identifier(id_or_slug)
    if slug:
        print_log("Looking up clip...")
        clip = twitch.get_clip(slug)

        if clip:
            _download_clip(clip, args)
        else:
            print_error(f"Clip '{slug}' not found")
        return

    print_error(f"Not a valid video ID or clip slug: {id_or_slug}")


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


def _download_clip(clip: Clip, args: DownloadOptions) -> None:
    target = Path(clip_filename(clip, args.output))
    _print_found_clip(clip)
    print_log(f"Target: {target}")

    if target.exists():
        if args.skip_existing:
            click.echo(f"Clip already downloaded: {green(target)}")
            return

        if not args.overwrite:
            response = _prompt_overwrite()
            if response == Overwrite.OVERWRITE_ALL:
                args.overwrite = True
            elif response == Overwrite.SKIP:
                click.echo(f"Skipping clip: {green(target)}")
                return
            elif response == Overwrite.SKIP_ALL:
                args.skip_existing = True
                click.echo(f"Skipping clip: {green(target)}")
                return
            elif response == Overwrite.ABORT:
                raise click.Abort()

    url = get_clip_authenticated_url(clip["slug"], args.quality)
    print_log(f"Downloading from: {url}")

    if args.dry_run:
        click.echo("Dry run, clip not downloaded.")
    else:
        download_file(url, target)
        click.echo(f"Downloaded clip: {green(target)}")


def _print_found_clip(clip: Clip):
    print_log(
        "Found clip:",
        green(clip["title"]),
        "by",
        yellow(clip["broadcaster"]["displayName"]),
        "playing",
        blue(clip["game"]["name"] if clip["game"] else "Unknown"),
        f"({utils.format_time(clip['durationSeconds'])})",
    )


def _download_video(video: Video, args: DownloadOptions) -> None:
    target = Path(video_filename(video, args.format, args.output))
    _print_found_video(video)
    print_log(f"Target: {blue(target)}")

    overwrite = args.overwrite
    if target.exists():
        if args.skip_existing:
            click.echo(f"Video already downloaded: {green(target)}")
            return

        if not overwrite:
            response = _prompt_overwrite()
            if response == Overwrite.OVERWRITE:
                overwrite = True
            elif response == Overwrite.OVERWRITE_ALL:
                overwrite = True
                args.overwrite = True
            elif response == Overwrite.SKIP:
                click.echo(f"Skipping clip: {green(target)}")
                return
            elif response == Overwrite.SKIP_ALL:
                args.skip_existing = True
                click.echo(f"Skipping clip: {green(target)}")
                return
            elif response == Overwrite.ABORT:
                raise click.Abort()

    print_log("Fetching chapters...")
    chapters = twitch.get_video_chapters(video["id"])
    start, end = _determine_time_range(chapters, args)

    print_log("Fetching access token...")
    access_token = twitch.get_access_token(video["id"], auth_token=args.auth_token)

    print_log("Fetching playlists...")
    playlists_text = twitch.get_playlists(video["id"], access_token)
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
    _write_metadata(video, chapters, metadata_path, start, end)

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
        _join_vods(join_playlist_path, metadata_path, target, overwrite)

    click.echo()

    if args.keep:
        click.echo(f"Temporary files not deleted: {yellow(target_dir)}")
    else:
        print_log("Deleting temporary files...")
        shutil.rmtree(target_dir)

    click.echo(f"Downloaded: {green(target)}")


def _print_found_video(video: Video):
    print_log(
        "Found video:",
        green(video["title"]),
        "by",
        yellow(video["creator"]["displayName"]),
        "playing",
        blue(video["game"]["name"] if video["game"] else "Unknown"),
        f"({utils.format_time(video['lengthSeconds'])})",
    )


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
def _write_metadata(
    video: Video,
    chapters: List[Chapter],
    path: Path,
    start_offset: Optional[int],
    end_offset: Optional[int],
):
    start_offset_ms = 1000 * (start_offset or 0)
    end_offset_ms = 1000 * (end_offset or video["lengthSeconds"])

    title = _escape_metadata(video["title"])
    artist = _escape_metadata(video["creator"]["displayName"])
    description = _escape_metadata(video["description"])

    with open(path, "w") as f:
        # Header
        f.write(";FFMETADATA1\n")

        # Global metadata
        f.write(f"title={title}\n")
        f.write(f"artist={artist}\n")
        if description:
            f.write(f"description={description}\n")
        f.write("encoded_by=twitch-dl\n")

        # Chapter metadata
        for chapter in chapters:
            title = chapter["description"]
            chapter_start_ms = chapter["positionMilliseconds"]
            chapter_end_ms = chapter["positionMilliseconds"] + chapter["durationMilliseconds"]

            if chapter_start_ms >= start_offset_ms and chapter_start_ms <= end_offset_ms:
                if chapter_end_ms > end_offset_ms:
                    chapter_end_ms = end_offset_ms

                start_ms = chapter_start_ms - start_offset_ms
                end_ms = chapter_end_ms - start_offset_ms

                f.write("\n[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")
                f.write(f"START={start_ms}\n")
                f.write(f"END={end_ms}\n")
                f.write(f"title={title}\n")


def _escape_metadata(text: Optional[str]):
    #  Metadata keys or values containing special characters
    # (‘=’, ‘;’, ‘#’, ‘\’ and a newline) must be escaped with a backslash ‘\’.
    text = text.strip() if text else ""
    return re.sub(r"([=;#\\\n])", r"\\\1", text.strip())


class Overwrite(Enum):
    OVERWRITE = auto()
    OVERWRITE_ALL = auto()
    SKIP = auto()
    SKIP_ALL = auto()
    ABORT = auto()


def _prompt_overwrite() -> Overwrite:
    prompt = (
        "File exists. Do you want to: "
        + f"{underlined('O')}verwrite, "
        + f"Overwrite {underlined('A')}ll, "
        + f"{underlined('S')}kip, "
        + f"S{underlined('k')}ip all, "
        + f"A{underlined('b')}ort"
    )

    while True:
        response = click.prompt(prompt, default="O").lower().strip()

        if response == "o":
            return Overwrite.OVERWRITE
        elif response == "a":
            return Overwrite.OVERWRITE_ALL
        elif response == "s":
            return Overwrite.SKIP
        elif response == "k":
            return Overwrite.SKIP_ALL
        elif response == "b":
            return Overwrite.ABORT

        print_error(f"Invalid response: {response}")
