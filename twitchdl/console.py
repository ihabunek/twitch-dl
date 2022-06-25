# -*- coding: utf-8 -*-

import logging
import sys

from argparse import ArgumentParser, ArgumentTypeError
from collections import namedtuple

from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_err
from twitchdl.twitch import GQLError
from . import commands, __version__


Command = namedtuple("Command", ["name", "description", "arguments"])

CLIENT_WEBSITE = 'https://github.com/ihabunek/twitch-dl'


def time(value):
    """Parse a time string (hh:mm or hh:mm:ss) to number of seconds."""
    parts = [int(p) for p in value.split(":")]

    if not 2 <= len(parts) <= 3:
        raise ArgumentTypeError()

    hours = parts[0]
    minutes = parts[1]
    seconds = parts[2] if len(parts) > 2 else 0

    if hours < 0 or not (0 <= minutes <= 59) or not (0 <= seconds <= 59):
        raise ArgumentTypeError()

    return hours * 3600 + minutes * 60 + seconds


def pos_integer(value):
    try:
        value = int(value)
    except ValueError:
        raise ArgumentTypeError("must be an integer")

    if value < 1:
        raise ArgumentTypeError("must be positive")

    return value


COMMANDS = [
    Command(
        name="videos",
        description="List videos for a channel.",
        arguments=[
            (["channel_name"], {
                "help": "Name of the channel to list videos for.",
                "type": str,
            }),
            (["-g", "--game"], {
                "help": "Show videos of given game (can be given multiple times)",
                "action": "append",
                "type": str,
            }),
            (["-l", "--limit"], {
                "help": "Number of videos to fetch. Defaults to 10.",
                "type": pos_integer,
                "default": 10,
            }),
            (["-a", "--all"], {
                "help": "Fetch all videos, overrides --limit",
                "action": "store_true",
                "default": False,
            }),
            (["-s", "--sort"], {
                "help": "Sorting order of videos. Defaults to `time`.",
                "type": str,
                "choices": ["views", "time"],
                "default": "time",
            }),
            (["-t", "--type"], {
                "help": "Broadcast type. Defaults to `archive`.",
                "type": str,
                "choices": ["archive", "highlight", "upload"],
                "default": "archive",
            }),
            (["-j", "--json"], {
                "help": "Show results as JSON. Ignores `--pager`.",
                "action": "store_true",
                "default": False,
            }),
            (["-p", "--pager"], {
                "help": "Print videos in pages. Ignores `--limit`. Defaults to 10.",
                "type": pos_integer,
                "nargs": "?",
                "const": 10,
            }),
        ],
    ),
    Command(
        name="clips",
        description="List or download clips for a channel.",
        arguments=[
            (["channel_name"], {
                "help": "Name of the channel to list clips for.",
                "type": str,
            }),
            (["-l", "--limit"], {
                "help": "Number of videos to fetch (default 10, max 100)",
                "type": pos_integer,
                "default": 10,
            }),
            (["-a", "--all"], {
                "help": "Fetch all videos, overrides --limit",
                "action": "store_true",
                "default": False,
            }),
            (["-P", "--period"], {
                "help": "Period from which to return clips. Defaults to `all_time`.",
                "type": str,
                "choices": ["last_day", "last_week", "last_month", "all_time"],
                "default": "all_time",
            }),
            (["-j", "--json"], {
                "help": "Show results as JSON. Ignores `--pager`.",
                "action": "store_true",
                "default": False,
            }),
            (["-p", "--pager"], {
                "help": "Number of clips to show per page. Disabled by default.",
                "type": pos_integer,
                "nargs": "?",
                "const": 10,
            }),
            (["-d", "--download"], {
                "help": "Download all videos in given period (in source quality)",
                "action": "store_true",
                "default": False,
            }),
        ],
    ),
    Command(
        name="download",
        description="Download a video or clip.",
        arguments=[
            (["video"], {
                "help": "Video ID, clip slug, or URL",
                "type": str,
            }),
            (["-w", "--max-workers"], {
                "help": "Maximal number of threads for downloading vods "
                        "concurrently (default 20)",
                "type": int,
                "default": 20,
            }),
            (["-s", "--start"], {
                "help": "Download video from this time (hh:mm or hh:mm:ss)",
                "type": time,
                "default": None,
            }),
            (["-e", "--end"], {
                "help": "Download video up to this time (hh:mm or hh:mm:ss)",
                "type": time,
                "default": None,
            }),
            (["-f", "--format"], {
                "help": "Video format to convert into, passed to ffmpeg as the "
                        "target file extension. Defaults to `mkv`.",
                "type": str,
                "default": "mkv",
            }),
            (["-k", "--keep"], {
                "help": "Don't delete downloaded VODs and playlists after merging.",
                "action": "store_true",
                "default": False,
            }),
            (["-q", "--quality"], {
                "help": "Video quality, e.g. 720p. Set to 'source' to get best quality.",
                "type": str,
            }),
            (["-a", "--auth"], {
                "help": "Authentication token, passed to Twitch to access subscriber only "
                        "VODs. Can be copied from the 'auth_token' cookie in any browser "
                        "logged in on Twitch.",
                "type": str,
                "default": None,
            }),
            (["--no-join"], {
                "help": "Don't run ffmpeg to join the downloaded vods, implies --keep.",
                "action": "store_true",
                "default": False,
            }),
            (["--overwrite"], {
                "help": "Overwrite the target file if it already exists without prompting.",
                "action": "store_true",
                "default": False,
            }),
            (["-o", "--output"], {
                "help": "Output file name template. See docs for details.",
                "type": str,
                "default": "{date}_{id}_{channel_login}_{title_slug}.{format}"
            })
        ],
    ),
    Command(
        name="info",
        description="Print information for a given Twitch URL, video ID or clip slug.",
        arguments=[
            (["video"], {
                "help": "Video ID, clip slug, or URL",
                "type": str,
            }),
            (["-j", "--json"], {
                "help": "Show results as JSON",
                "action": "store_true",
                "default": False,
            }),
        ],
    ),
    Command(
        name="env",
        description="Print environment information for inclusion in bug reports.",
        arguments=[],
    )
]

COMMON_ARGUMENTS = [
    (["--debug"], {
        "help": "show debug log in console",
        "action": 'store_true',
        "default": False,
    }),
    (["--no-color"], {
        "help": "disable ANSI colors in output",
        "action": 'store_true',
        "default": False,
    })
]


def get_parser():
    description = "A script for downloading videos from Twitch"

    parser = ArgumentParser(prog='twitch-dl', description=description, epilog=CLIENT_WEBSITE)
    parser.add_argument("--version", help="show version number", action='store_true')

    subparsers = parser.add_subparsers(title="commands")

    for command in COMMANDS:
        sub = subparsers.add_parser(
            command.name,
            description=command.description,
            epilog=CLIENT_WEBSITE
        )

        # Set the function to call to the function of same name in the "commands" package
        sub.set_defaults(func=commands.__dict__.get(command.name))

        for args, kwargs in command.arguments + COMMON_ARGUMENTS:
            sub.add_argument(*args, **kwargs)

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if "--debug" in sys.argv:
        logging.basicConfig(level=logging.DEBUG)

    if args.version:
        print("twitch-dl v{}".format(__version__))
        return

    if "func" not in args:
        parser.print_help()
        return

    try:
        args.func(args)
    except ConsoleError as e:
        print_err(e)
        sys.exit(1)
    except KeyboardInterrupt:
        print_err("Operation canceled")
        sys.exit(1)
    except GQLError as e:
        print_err(e)
        for err in e.errors:
            print_err("*", err["message"])
        sys.exit(1)
