import json
from itertools import islice
from typing import Any, Callable, Generator, List, Optional, TypeVar

import click

from twitchdl import utils
from twitchdl.twitch import Clip, Video

T = TypeVar("T")


def truncate(string: str, length: int) -> str:
    if len(string) > length:
        return string[: length - 1] + "…"

    return string


def print_json(data: Any):
    click.echo(json.dumps(data))


def print_log(message: Any):
    click.secho(message, err=True, dim=True)


def visual_len(text: str):
    return len(click.unstyle(text))


def ljust(text: str, width: int):
    diff = width - visual_len(text)
    return text + (" " * diff) if diff > 0 else text


def print_table(headers: List[str], data: List[List[str]]):
    widths = [[visual_len(cell) for cell in row] for row in data + [headers]]
    widths = [max(width) for width in zip(*widths)]
    underlines = ["-" * width for width in widths]

    def print_row(row: List[str]):
        for idx, cell in enumerate(row):
            width = widths[idx]
            click.echo(ljust(cell, width), nl=False)
            click.echo("  ", nl=False)
        click.echo()

    print_row(headers)
    print_row(underlines)

    for row in data:
        print_row(row)


def print_paged(
    label: str,
    generator: Generator[T, Any, Any],
    print_fn: Callable[[T], None],
    page_size: int,
    total_count: Optional[int] = None,
):
    iterator = iter(generator)
    page = list(islice(iterator, page_size))

    first = 1
    last = first + len(page) - 1

    while True:
        click.echo("-" * 80)

        click.echo()
        for item in page:
            print_fn(item)

        last = first + len(page) - 1

        click.echo("-" * 80)
        click.echo(f"{label} {first}-{last} of {total_count or '???'}")

        first = first + len(page)
        last = first + 1

        page = list(islice(iterator, page_size))
        if not page or not prompt_continue():
            break


def print_video(video: Video):
    published_at = video["publishedAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(video["lengthSeconds"])

    channel = blue(video["creator"]["displayName"]) if video["creator"] else ""
    playing = f"playing {blue(video['game']['name'])}" if video["game"] else ""

    # Can't find URL in video object, strange
    url = f"https://www.twitch.tv/videos/{video['id']}"

    click.secho(f"Video {video['id']}", bold=True)
    click.secho(video["title"], fg="green")

    if channel or playing:
        click.echo(" ".join([channel, playing]))

    if video["description"]:
        click.echo(f"Description: {video['description']}")

    click.echo(f"Published {blue(published_at)}  Length: {blue(length)} ")
    click.secho(url, italic=True)
    click.echo()


def print_video_compact(video: Video):
    id = video["id"]
    date = video["publishedAt"][:10]
    game = video["game"]["name"] if video["game"] else ""
    title = truncate(video["title"], 80).ljust(80)
    click.echo(f"{bold(id)} {date} {green(title)} {blue(game)}")


def print_clip(clip: Clip):
    published_at = clip["createdAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(clip["durationSeconds"])
    channel = clip["broadcaster"]["displayName"]
    playing = f"playing {blue(clip['game']['name'])}" if clip["game"] else ""

    click.echo(f"Clip {bold(clip['slug'])}")
    click.secho(clip["title"], fg="green")
    click.echo(f"{blue(channel)} {playing}")
    click.echo(
        f"Published {blue(published_at)}"
        + f"  Length: {blue(length)}"
        + f"  Views: {blue(clip['viewCount'])}"
    )
    click.secho(clip["url"], italic=True)
    click.echo()


def print_clip_compact(clip: Clip):
    slug = clip["slug"]
    date = clip["createdAt"][:10]
    title = truncate(clip["title"], 50).ljust(50)
    game = clip["game"]["name"] if clip["game"] else ""
    game = truncate(game, 30).ljust(30)

    click.echo(f"{date} {green(title)} {blue(game)} {bold(slug)}")


def prompt_continue():
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
