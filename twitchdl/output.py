import click
import json

from itertools import islice
from twitchdl import utils
from typing import Any, Generator

from twitchdl.entities import Data


def truncate(string: str, length: int) -> str:
    if len(string) > length:
        return string[:length - 1] + "…"

    return string


def print_json(data: Any):
    click.echo(json.dumps(data))


def print_log(message: Any):
    click.secho(message, err=True, dim=True)


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


def print_video(video: Data):
    published_at = video["publishedAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(video["lengthSeconds"])

    channel = blue(video['creator']['displayName']) if video["creator"] else ""
    playing = f"playing {blue(video['game']['name'])}" if video["game"] else ""

    # Can't find URL in video object, strange
    url = f"https://www.twitch.tv/videos/{video['id']}"

    click.secho(f"Video {video['id']}", bold=True)
    click.secho(f"{video['title']}", fg="green")

    if channel or playing:
        click.echo(" ".join([channel, playing]))

    if video["description"]:
        click.echo(f"Description: {video['description']}")

    click.echo(f"Published {blue(published_at)}  Length: {blue(length)} ")
    click.secho(url, italic=True)


def print_video_compact(video: Data):
    id = video["id"]
    date = video["publishedAt"][:10]
    game = video["game"]["name"] if video["game"] else ""
    title = truncate(video["title"], 80).ljust(80)
    click.echo(f"{bold(id)} {date} {green(title)} {blue(game)}")


def print_paged_videos(generator: Generator[Data, None, None], page_size: int, total_count: int):
    iterator = iter(generator)
    page = list(islice(iterator, page_size))

    first = 1
    last = first + len(page) - 1

    while True:
        click.echo("-" * 80)

        click.echo()
        for video in page:
            print_video(video)
            click.echo()

        last = first + len(page) - 1

        click.echo("-" * 80)
        click.echo(f"Videos {first}-{last} of {total_count}")

        first = first + len(page)
        last = first + 1

        page = list(islice(iterator, page_size))
        if not page or not _continue():
            break


def print_clip(clip: Data):
    published_at = clip["createdAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(clip["durationSeconds"])
    channel = clip["broadcaster"]["displayName"]
    playing = f"playing {blue(clip['game']['name'])}" if clip["game"] else ""

    click.echo(f"Clip {bold(clip['slug'])}")
    click.secho(clip["title"], fg="green")
    click.echo(f"{blue(channel)} {playing}")
    click.echo(
        f"Published {blue(published_at)}" +
        f"  Length: {blue(length)}" +
        f"  Views: {blue(clip['viewCount'])}"
    )
    click.secho(clip["url"], italic=True)


def _continue():
    enter = click.style("Enter", bold=True, fg="green")
    ctrl_c = click.style("Ctrl+C", bold=True, fg="yellow")
    click.echo(f"Press {enter} to continue, {ctrl_c} to break.")

    try:
        input()
    except KeyboardInterrupt:
        return False

    return True


# Shorthand functions for coloring output

def blue(text: Any) -> str:
    return click.style(text, fg="blue")


def cyan(text: Any) -> str:
    return click.style(text, fg="cyan")


def green(text: Any) -> str:
    return click.style(text, fg="green")


def yellow(text: Any) -> str:
    return click.style(text, fg="yellow")


def bold(text: Any) -> str:
    return click.style(text, bold=True)


def dim(text: Any) -> str:
    return click.style(text, dim=True)
