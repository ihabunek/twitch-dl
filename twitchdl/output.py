import json
import sys
import traceback
from itertools import islice
from typing import (
    Any,
    AsyncIterable,
    Callable,
    Generator,
    List,
    Literal,
    Mapping,
    Optional,
    TypeVar,
)

import click

from twitchdl import utils
from twitchdl.entities import Clip, Video

T = TypeVar("T")


def cursor_previous_line():
    sys.stdout.write("\033[1F")


def clear_line():
    sys.stdout.write("\033[2K")
    sys.stdout.write("\r")


def truncate(string: str, length: int) -> str:
    if len(string) > length:
        return string[: length - 1] + "…"

    return string


def print_json(data: Any):
    click.echo(json.dumps(data))


def print_log(*args: Any):
    message = " ".join(click.style(a, dim=True) for a in args)
    click.secho(message, err=True)


def print_error(message: Any):
    click.secho(message, err=True, fg="red")


def print_exception(ex: BaseException):
    for line in traceback.format_exception_only(ex):  # type: ignore
        print_error(line)


_prev_transient = False


def print_status(message: str, transient: bool = False, dim: bool = False):
    global _prev_transient

    if _prev_transient:
        cursor_previous_line()
        clear_line()

    click.secho(message, err=True, dim=dim)
    _prev_transient = transient


def visual_len(text: str):
    return len(click.unstyle(text))


# Additional lenght to take into account due to invisible chars like ansi codes
def _extra_len(text: str):
    return len(text) - visual_len(text)


def ljust(text: str, width: int):
    return text.ljust(width + _extra_len(text))


def rjust(text: str, width: int):
    return text.rjust(width + _extra_len(text))


def center(text: str, width: int):
    return text.center(width + _extra_len(text))


Align = Literal["left", "right", "center"]


def print_table(
    data: List[List[str]],
    *,
    alignments: Mapping[int, Align] = {},
    headers: Optional[List[str]] = None,
    footers: Optional[List[str]] = None,
):
    all_rows = data + ([headers] if headers else []) + ([footers] if footers else [])
    widths = [[visual_len(cell) for cell in row] for row in all_rows]
    widths = [max(width) for width in zip(*widths)]
    underlines = ["-" * width for width in widths]

    def format_cell(cell: str, idx: int):
        width = widths[idx]
        align = alignments.get(idx, "left")

        if align == "right":
            return rjust(cell, width)
        elif align == "center":
            return center(cell, width)
        else:
            return ljust(cell, width)

    def print_row(row: List[str]):
        parts = (format_cell(cell, idx) for idx, cell in enumerate(row))
        click.echo("  ".join(parts).strip())

    if headers:
        print_row([bold(h) for h in headers])
        print_row(underlines)

    for row in data:
        print_row(row)

    if footers:
        print_row(underlines)
        print_row([bold(f) for f in footers])


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


async def batch_async(iterable: AsyncIterable[T], batch_size: int) -> AsyncIterable[List[T]]:
    batch: List[T] = []
    async for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:  # Yield any remaining items
        yield batch


async def print_paged_async(
    label: str,
    iterable: AsyncIterable[T],
    print_fn: Callable[[T], None],
    page_size: int,
    total_count: Optional[int] = None,
):
    first = 1

    async for page in batch_async(iterable, page_size):
        if not page or (first > 1 and not prompt_continue()):
            break

        click.echo("-" * 80)
        click.echo()
        for item in page:
            print_fn(item)

        last = first + len(page) - 1
        click.echo("-" * 80)
        click.echo(f"{label} {first}-{last} of {total_count or '???'}")
        first = first + len(page)


def print_video(video: Video):
    published_at = video["publishedAt"].replace("T", " @ ").replace("Z", "")
    length = utils.format_duration(video["lengthSeconds"])

    channel = blue(video["owner"]["displayName"]) if video["owner"] else ""
    playing = f"playing {blue(video['game']['name'])}" if video["game"] else ""

    # Can't find URL in video object, strange
    url = f"https://www.twitch.tv/videos/{video['id']}"

    click.secho(f"Video {video['id']}", bold=True)
    click.secho(video["title"], fg="green")

    if channel or playing:
        click.echo(" ".join([channel, playing]))

    click.echo(f"Published {blue(published_at)}  Length: {blue(length)} ")
    click.secho(url, italic=True)

    if video["description"]:
        click.echo(f"\nDescription:\n{video['description']}")

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


def red(text: Any) -> str:
    return click.style(text, fg="red")


def yellow(text: Any) -> str:
    return click.style(text, fg="yellow")


def bold(text: Any) -> str:
    return click.style(text, bold=True)


def dim(text: Any) -> str:
    return click.style(text, dim=True)


def underlined(text: Any) -> str:
    return click.style(text, underline=True)
