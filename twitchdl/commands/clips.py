import re
import sys
from os import path
from pathlib import Path
from typing import Callable, Generator, List, Optional

import click

from twitchdl import twitch, utils
from twitchdl.commands.download import get_clip_authenticated_url
from twitchdl.entities import VideoQuality
from twitchdl.http import download_file
from twitchdl.output import green, print_clip, print_clip_compact, print_json, print_paged, yellow
from twitchdl.twitch import Clip, ClipsPeriod


def clips(
    channel_name: str,
    *,
    all: bool = False,
    compact: bool = False,
    download: bool = False,
    json: bool = False,
    limit: Optional[int] = None,
    pager: Optional[int] = None,
    period: ClipsPeriod = "all_time",
    target_dir: Path = Path(),
):
    # Set different defaults for limit for compact display
    default_limit = 40 if compact else 10

    # Ignore --limit if --pager or --all are given
    limit = sys.maxsize if all or pager else (limit or default_limit)

    generator = twitch.channel_clips_generator(channel_name, period, limit)

    if json:
        return print_json(list(generator))

    if download:
        return _download_clips(target_dir, generator)

    print_fn = print_clip_compact if compact else print_clip

    if pager:
        return print_paged("Clips", generator, print_fn, pager)

    return _print_all(generator, print_fn, all)


def _target_filename(clip: Clip, video_qualities: List[VideoQuality]):
    url = video_qualities[0]["sourceURL"]
    _, ext = path.splitext(url)
    ext = ext.lstrip(".")

    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", clip["createdAt"])
    if not match:
        raise ValueError(f"Failed parsing date from: {clip['createdAt']}")
    date = "".join(match.groups())

    name = "_".join(
        [
            date,
            clip["id"],
            clip["broadcaster"]["login"],
            utils.slugify(clip["title"]),
        ]
    )

    return f"{name}.{ext}"


def _download_clips(target_dir: Path, generator: Generator[Clip, None, None]):
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    for clip in generator:
        # videoQualities can be null in some circumstances, see:
        # https://github.com/ihabunek/twitch-dl/issues/160
        if not clip["videoQualities"]:
            continue

        target = target_dir / _target_filename(clip, clip["videoQualities"])

        if target.exists():
            click.echo(f"Already downloaded: {green(target)}")
        else:
            try:
                url = get_clip_authenticated_url(clip["slug"], "source")
                click.echo(f"Downloading: {yellow(target)}")
                download_file(url, target)
            except Exception as ex:
                click.secho(ex, err=True, fg="red")


def _print_all(
    generator: Generator[Clip, None, None],
    print_fn: Callable[[Clip], None],
    all: bool,
):
    for clip in generator:
        print_fn(clip)

    if not all:
        click.secho(
            "\nThere may be more clips. "
            + "Increase the --limit, use --all or --pager to see the rest.",
            dim=True,
        )
