# -*- coding: utf-8 -*-

import json
import sys
import re

from twitchdl import utils


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


def start_code(match):
    name = match.group(1)
    return START_CODES[name]


def colorize(text):
    text = re.sub(START_PATTERN, start_code, text)
    text = re.sub(END_PATTERN, END_CODE, text)

    return text


def strip_tags(text):
    text = re.sub(START_PATTERN, '', text)
    text = re.sub(END_PATTERN, '', text)

    return text


def print_out(*args, **kwargs):
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, **kwargs)


def print_json(data):
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
    channel = video["creator"]["displayName"]
    playing = (
        "playing <blue>{}</blue>".format(video["game"]["name"])
        if video["game"] else ""
    )

    # Can't find URL in video object, strange
    url = "https://www.twitch.tv/videos/{}".format(video["id"])

    print_out("<b>Video {}</b>".format(video["id"]))
    print_out("<green>{}</green>".format(video["title"]))
    print_out("<blue>{}</blue> {}".format(channel, playing))
    print_out("Published <blue>{}</blue>  Length: <blue>{}</blue> ".format(published_at, length))
    print_out("<i>{}</i>".format(url))


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


def print_clip_urls(clip):
    from pprint import pprint
    pprint(clip)