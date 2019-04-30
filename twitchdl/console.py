# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from collections import namedtuple

from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_err
from . import commands


Command = namedtuple("Command", ["name", "description", "arguments"])

CLIENT_WEBSITE = 'https://github.com/ihabunek/twitch-dl'

COMMANDS = [
    Command(
        name="videos",
        description="List videos from a channel",
        arguments=[
            (["channel_name"], {
                "help": "channel name",
                "type": str,
            }),
        ],
    ),
    Command(
        name="download",
        description="Download a video",
        arguments=[
            (["video_id"], {
                "help": "video ID",
                "type": str,
            }),
            (["-w", "--max_workers"], {
                "help": "maximal number of threads for downloading vods concurrently (default 5)",
                "type": int,
                "default": 20,
            }),
        ],
    ),
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
    subparsers = parser.add_subparsers(title="commands")

    for command in COMMANDS:
        sub = subparsers.add_parser(command.name, help=command.description)

        # Set the function to call to the function of same name in the "commands" package
        sub.set_defaults(func=commands.__dict__.get(command.name))

        for args, kwargs in command.arguments + COMMON_ARGUMENTS:
            sub.add_argument(*args, **kwargs)

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if "func" not in args:
        parser.print_help()
        return

    try:
        args.func(**args.__dict__)
    except ConsoleError as e:
        print_err(e)
