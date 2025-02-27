import asyncio
import os
import re
import sys
from os import path
from pathlib import Path
from typing import Callable, Generator, List, NamedTuple, Optional
from urllib.parse import urlencode

import click
import httpx

from twitchdl import twitch, twitch_async, utils
from twitchdl.entities import ClipAccessToken, VideoQuality
from twitchdl.exceptions import ConsoleError
from twitchdl.http import CHUNK_SIZE, TIMEOUT
from twitchdl.output import (
    green,
    print_clip,
    print_clip_compact,
    print_json,
    print_paged,
    print_status,
)
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

    if download:
        asyncio.run(_download_clips(channel_name, period, limit, target_dir))
        return

    generator = twitch.channel_clips_generator(channel_name, period, limit)

    if json:
        return print_json(list(generator))

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


# TODO: add --quality
# TODO: add --limit
# TODO: add --workers


async def _download_clips(channel_name: str, period: ClipsPeriod, limit: int, target_dir: Path):
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    generator = twitch.channel_clips_page_generator(channel_name, period, 100)

    for page in generator:
        print_status(f"Fetched page {page.page_no} of {page.size} clips", dim=True)
        await _download_page(page.items, target_dir)


class Task(NamedTuple):
    slug: str
    target: Path


async def _download_page(clips: List[Clip], target_dir: Path):
    queue: asyncio.Queue[Task] = asyncio.Queue()

    # Fill the download queue
    for clip in clips:
        # videoQualities can be null in some circumstances, see:
        # https://github.com/ihabunek/twitch-dl/issues/160
        if clip["videoQualities"]:
            target = target_dir / _target_filename(clip, clip["videoQualities"])
            if target.exists():
                print_status(f"Clip exists: {green(target)}")
            else:
                await queue.put(Task(clip["slug"], target))

    tasks = [asyncio.create_task(_download_worker(queue)) for _ in range(10)]

    await queue.join()

    # Cleanup
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def _download_worker(queue: asyncio.Queue[Task]):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while True:
            task = await queue.get()
            tmp_target = Path(f"{task.target}.tmp")

            try:
                print_status(f"Downloading {task.target}...", dim=True, transient=True)
                url = await _get_clip_authenticated_url(client, task.slug, "source")
                await _download_file(client, url, tmp_target)
                os.rename(tmp_target, task.target)
                print_status(f"Downloaded {green(task.target)}")
            except Exception as ex:
                click.secho(f"Failed downloading {task.slug}: {ex}", err=True, fg="red")
                tmp_target.unlink(missing_ok=True)

            queue.task_done()


async def _download_file(client: httpx.AsyncClient, url: str, target: Path):
    with open(target, "wb") as f:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                f.write(chunk)


async def _get_clip_authenticated_url(client: httpx.AsyncClient, slug: str, quality: str):
    access_token = await twitch_async.get_clip_access_token(client, slug)

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


def _get_clip_url(access_token: ClipAccessToken, quality: str) -> str:
    qualities = access_token["videoQualities"]

    if quality == "source":
        return qualities[0]["sourceURL"]

    selected_quality = quality.rstrip("p")  # allow 720p as well as 720
    for q in qualities:
        if q["quality"] == selected_quality:
            return q["sourceURL"]

    available = ", ".join([str(q["quality"]) for q in qualities])
    msg = f"Quality '{quality}' not found. Available qualities are: {available}"
    raise ConsoleError(msg)


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
