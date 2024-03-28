import re
import sys

from typing import Literal
from itertools import islice
from os import path

from twitchdl import twitch, utils
from twitchdl.commands.download import get_clip_authenticated_url
from twitchdl.download import download_file
from twitchdl.output import print_out, print_clip, print_json

ClipsPeriod = Literal["last_day", "last_week", "last_month", "all_time"]


def clips(
    channel_name: str,
    *,
    all: bool = False,
    download: bool = False,
    json: bool = False,
    limit: int = 10,
    pager: int | None = None,
    period: ClipsPeriod = "all_time",
):
    # Ignore --limit if --pager or --all are given
    limit = sys.maxsize if all or pager else limit

    generator = twitch.channel_clips_generator(channel_name, period, limit)

    if json:
        return print_json(list(generator))

    if download:
        return _download_clips(generator)

    if pager:
        return _print_paged(generator, pager)

    return _print_all(generator, all)


def _continue():
    print_out("Press <green><b>Enter</green> to continue, <yellow><b>Ctrl+C</yellow> to break.")

    try:
        input()
    except KeyboardInterrupt:
        return False

    return True


def _target_filename(clip):
    url = clip["videoQualities"][0]["sourceURL"]
    _, ext = path.splitext(url)
    ext = ext.lstrip(".")

    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", clip["createdAt"])
    if not match:
        raise ValueError(f"Failed parsing date from: {clip['createdAt']}")
    date = "".join(match.groups())

    name = "_".join([
        date,
        clip["id"],
        clip["broadcaster"]["login"],
        utils.slugify(clip["title"]),
    ])

    return f"{name}.{ext}"


def _download_clips(generator):
    for clip in generator:
        target = _target_filename(clip)

        if path.exists(target):
            print_out(f"Already downloaded: <green>{target}</green>")
        else:
            url = get_clip_authenticated_url(clip["slug"], "source")
            print_out(f"Downloading: <yellow>{target}</yellow>")
            download_file(url, target)


def _print_all(generator, all: bool):
    for clip in generator:
        print_out()
        print_clip(clip)

    if not all:
        print_out(
            "\n<dim>There may be more clips. " +
            "Increase the --limit, use --all or --pager to see the rest.</dim>"
        )


def _print_paged(generator, page_size):
    iterator = iter(generator)
    page = list(islice(iterator, page_size))

    first = 1
    last = first + len(page) - 1

    while True:
        print_out("-" * 80)

        print_out()
        for clip in page:
            print_clip(clip)
            print_out()

        last = first + len(page) - 1

        print_out("-" * 80)
        print_out(f"<yellow>Clips {first}-{last}</yellow>")

        first = first + len(page)
        last = first + 1

        page = list(islice(iterator, page_size))
        if not page or not _continue():
            break
