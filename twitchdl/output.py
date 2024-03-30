import click
import json
import re
import sys

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
    click.echo(json.dumps(data))


def print_log(*args, **kwargs):
    args = [f"<dim>{a}</dim>" for a in args]
    args = [colorize(a) if USE_ANSI_COLOR else strip_tags(a) for a in args]
    print(*args, file=sys.stderr, **kwargs)


def print_table(headers: list[str], data: list[list[str]]):
    widths = [[len(cell) for cell in row] for row in data + [headers]]
    widths = [max(width) for width in zip(*widths)]
    underlines = ["-" * width for width in widths]

    def print_row(row: list[str]):
        for idx, cell in enumerate(row):
            width = widths[idx]
            click.echo(cell.ljust(width), nl=False)
            click.echo("  ", nl=False)
        click.echo()

    print_row(headers)
    print_row(underlines)

    for row in data:
        print_row(row)


def print_video(video):
    published_at = video["publishedAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(video["lengthSeconds"])

    channel = f"<blue>{video['creator']['displayName']}</blue>" if video["creator"] else ""
    playing = f"playing <blue>{video['game']['name']}</blue>" if video["game"] else ""

    # Can't find URL in video object, strange
    url = f"https://www.twitch.tv/videos/{video['id']}"

    print_out(f"<b>Video {video['id']}</b>")
    print_out(f"<green>{video['title']}</green>")

    if channel or playing:
        print_out(" ".join([channel, playing]))

    if video["description"]:
        print_out(f"Description: {video['description']}")

    print_out(f"Published <blue>{published_at}</blue>  Length: <blue>{length}</blue> ")
    print_out(f"<i>{url}</i>")


def print_video_compact(video):
    id = video["id"]
    date = video["publishedAt"][:10]
    game = video["game"]["name"] if video["game"] else ""
    title = truncate(video["title"], 80).ljust(80)
    print_out(f'<b>{id}</b> {date} <green>{title}</green> <blue>{game}</blue>')


def print_paged_videos(generator, page_size: int, total_count: int):
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
        print_out(f"<yellow>Videos {first}-{last} of {total_count}</yellow>")

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
        f"playing <blue>{clip['game']['name']}</blue>"
        if clip["game"] else ""
    )

    print_out(f"Clip <b>{clip['slug']}</b>")
    print_out(f"<green>{clip['title']}</green>")
    print_out(f"<blue>{channel}</blue> {playing}")
    print_out(
        f"Published <blue>{published_at}</blue>" +
        f"  Length: <blue>{length}</blue>" +
        f"  Views: <blue>{clip["viewCount"]}</blue>"
    )
    print_out(f"<i>{clip['url']}</i>")


def _continue():
    print_out("Press <green><b>Enter</green> to continue, <yellow><b>Ctrl+C</yellow> to break.")

    try:
        input()
    except KeyboardInterrupt:
        return False

    return True
