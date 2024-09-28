import logging
import re
import sys
from os import path
from pathlib import Path
from typing import AsyncGenerator, AsyncIterable, Awaitable, Callable, List, Optional, Tuple
from urllib.parse import urlencode

import click

from twitchdl import twitch_async, utils
from twitchdl.entities import Clip, ClipsPeriod, VideoQuality
from twitchdl.http import download_all
from twitchdl.output import print_clip, print_clip_compact, print_json, print_paged_async
from twitchdl.progress import PrintingProgress

logger = logging.getLogger(__name__)


async def clips(
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

    generator = await twitch_async.channel_clips_generator(channel_name, period, limit)

    if json:
        return print_json([i async for i in generator])

    if download:
        return await _download_clips(target_dir, generator)

    print_fn = print_clip_compact if compact else print_clip

    if pager:
        await print_paged_async("Clips", generator, print_fn, pager)
        return

    await _print_all(generator, print_fn, all)


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


async def _download_clips(target_dir: Path, clips_generator: AsyncIterable[Clip]):
    target_dir.mkdir(parents=True, exist_ok=True)

    async def source_target_gen() -> AsyncGenerator[Tuple[Awaitable[str], Path], None]:
        async for clip in clips_generator:
            if clip["videoQualities"]:
                source = _get_authenticated_url(clip["slug"])
                target = target_dir / _target_filename(clip, clip["videoQualities"])
                yield (source, target)

    await download_all(
        source_target_gen(),
        worker_count=10,
        allow_failures=True,
        progress=PrintingProgress(),
        rate_limit=None,
        skip_existing=True,
    )


async def _print_all(
    clips: AsyncIterable[Clip],
    print_fn: Callable[[Clip], None],
    all: bool,
):
    async for clip in clips:
        print_fn(clip)

    if not all:
        click.secho(
            "\nThere may be more clips. "
            + "Increase the --limit, use --all or --pager to see the rest.",
            dim=True,
        )


async def _get_authenticated_url(slug: str) -> str:
    access_token = await twitch_async.get_clip_access_token(slug)

    # Source quality should be first
    url = access_token["videoQualities"][0]["sourceURL"]

    query = urlencode(
        {
            "sig": access_token["playbackAccessToken"]["signature"],
            "token": access_token["playbackAccessToken"]["value"],
        }
    )

    return f"{url}?{query}"
