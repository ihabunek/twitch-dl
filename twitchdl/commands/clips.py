import re
import sys

from itertools import islice
from os import path

from twitchdl import twitch, utils
from twitchdl.commands.download import get_clip_authenticated_url
from twitchdl.download import download_file
from twitchdl.output import print_out, print_clip, print_json


def clips(args):
    # Ignore --limit if --pager or --all are given
    limit = sys.maxsize if args.all or args.pager else args.limit

    generator = twitch.channel_clips_generator(args.channel_name, args.period, limit)

    if args.json:
        return print_json(list(generator))

    if args.download:
        return _download_clips(generator)

    if args.pager:
        print(args)
        return _print_paged(generator, args.pager)

    return _print_all(generator, args)


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
    date = "".join(match.groups())

    name = "_".join([
        date,
        clip["id"],
        clip["broadcaster"]["login"],
        utils.slugify(clip["title"]),
    ])

    return "{}.{}".format(name, ext)


def _download_clips(generator):
    for clip in generator:
        target = _target_filename(clip)

        if path.exists(target):
            print_out("Already downloaded: <green>{}</green>".format(target))
        else:
            url = get_clip_authenticated_url(clip["slug"], "source")
            print_out("Downloading: <yellow>{}</yellow>".format(target))
            download_file(url, target)


def _print_all(generator, args):
    for clip in generator:
        print_out()
        print_clip(clip)

    if not args.all:
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
        print_out("<yellow>Clips {}-{}</yellow>".format(first, last))

        first = first + len(page)
        last = first + 1

        page = list(islice(iterator, page_size))
        if not page or not _continue():
            break
