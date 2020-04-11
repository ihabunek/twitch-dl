# -*- coding: utf-8 -*-

import sys
import re

from twitchdl import utils


START_CODES = {
    'bold': '\033[1m',
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


def print_err(*args, **kwargs):
    args = ["<red>{}</red>".format(a) for a in args]
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, file=sys.stderr, **kwargs)


def print_video(video):
    published_at = video['published_at'].replace('T', ' @ ').replace('Z', '')
    length = utils.format_duration(video['length'])
    name = video['channel']['display_name']

    print_out("\n<bold>{}</bold>".format(video['_id'][1:]))
    print_out("<green>{}</green>".format(video["title"]))
    print_out("<cyan>{}</cyan> playing <cyan>{}</cyan>".format(name, video['game']))
    print_out("Published <cyan>{}</cyan>  Length: <cyan>{}</cyan> ".format(published_at, length))
    print_out("<i>{}</i>".format(video["url"]))
