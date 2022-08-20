# -*- coding: utf-8 -*-

import json
import sys
import re

from itertools import islice
from twitchdl import utils
from typing import Any, Match


START_CODES = {
    'b': '\033[1m',
    'dim': '\033[2m',
    'i': '\033[3m',
    'u': '\033[4m',
    'red': '\033[91m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'blue': '\033[94m',
    'magenta': '\033[95m',
    'cyan': '\033[96m',
}

END_CODE = '\033[0m'

START_PATTERN = "<(" + "|".join(START_CODES.keys()) + ")>"
END_PATTERN = "</(" + "|".join(START_CODES.keys()) + ")>"

USE_ANSI_COLOR = "--no-color" not in sys.argv


def start_code(match: Match[str]) -> str:
    name = match.group(1)
    return START_CODES[name]


def colorize(text: str) -> str:
    text = re.sub(START_PATTERN, start_code, text)
    text = re.sub(END_PATTERN, END_CODE, text)

    return text


def strip_tags(text: str) -> str:
    text = re.sub(START_PATTERN, '', text)
    text = re.sub(END_PATTERN, '', text)

    return text


def truncate(string: str, length: int) -> str:
    if len(string) > length:
        return string[:length - 1] + "…"

    return string


def print_out(*args, **kwargs):
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, **kwargs)


def print_json(data: Any):
    print(json.dumps(data))


def print_err(*args, **kwargs):
    args = ["<red>{}</red>".format(a) for a in args]
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, file=sys.stderr, **kwargs)


def print_log(*args, **kwargs):
    args = ["<dim>{}</dim>".format(a) for a in args]
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, file=sys.stderr, **kwargs)


def print_video(video):
    published_at = video["publishedAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(video["lengthSeconds"])

    channel = "<blue>{}</blue>".format(video["creator"]["displayName"]) if video["creator"] else ""
    playing = "playing <blue>{}</blue>".format(video["game"]["name"]) if video["game"] else ""

    # Can't find URL in video object, strange
    url = "https://www.twitch.tv/videos/{}".format(video["id"])

    print_out("<b>Video {}</b>".format(video["id"]))
    print_out("<green>{}</green>".format(video["title"]))

    if channel or playing:
        print_out(" ".join([channel, playing]))

    print_out("Published <blue>{}</blue>  Length: <blue>{}</blue> ".format(published_at, length))
    print_out("<i>{}</i>".format(url))


def print_video_compact(video):
    id = video["id"]
    date = video["publishedAt"][:10]
    game = video["game"]["name"] if video["game"] else ""
    title = truncate(video["title"], 80).ljust(80)
    print_out(f'<b>{id}</b> {date} <green>{title}</green> <blue>{game}</blue>')


def print_paged_videos(generator, page_size, total_count):
    iterator = iter(generator)
    page = list(islice(iterator, page_size))

    first = 1
    last = first + len(page) - 1

    while True:
        print_out("-" * 80)

        print_out()
        for video in page:
            print_video(video)
            print_out()

        last = first + len(page) - 1

        print_out("-" * 80)
        print_out("<yellow>Videos {}-{} of {}</yellow>".format(first, last, total_count))

        first = first + len(page)
        last = first + 1

        page = list(islice(iterator, page_size))
        if not page or not _continue():
            break


def print_clip(clip):
    published_at = clip["createdAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(clip["durationSeconds"])
    channel = clip["broadcaster"]["displayName"]
    playing = (
        "playing <blue>{}</blue>".format(clip["game"]["name"])
        if clip["game"] else ""
    )

    print_out("Clip <b>{}</b>".format(clip["slug"]))
    print_out("<green>{}</green>".format(clip["title"]))
    print_out("<blue>{}</blue> {}".format(channel, playing))
    print_out(
        "Published <blue>{}</blue>"
        "  Length: <blue>{}</blue>"
        "  Views: <blue>{}</blue>".format(published_at, length, clip["viewCount"]))
    print_out("<i>{}</i>".format(clip["url"]))


def _continue():
    print_out("Press <green><b>Enter</green> to continue, <yellow><b>Ctrl+C</yellow> to break.")

    try:
        input()
    except KeyboardInterrupt:
        return False

    return True
