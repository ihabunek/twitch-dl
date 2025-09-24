import enum
import logging
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import List, Optional, Tuple

import click

from twitchdl import __version__
from twitchdl.cache import get_cache_dir, get_cache_subdirs
from twitchdl.chat.ytt import EdgeType, FontStyle, HorizontalAlignment, YttParams
from twitchdl.entities import DownloadOptions
from twitchdl.exceptions import ConsoleError
from twitchdl.naming import DEFAULT_CHAT_OUTPUT, DEFAULT_VIDEO_OUTPUT
from twitchdl.output import print_table, print_warning
from twitchdl.twitch import ClipsPeriod, VideosSort, VideosType
from twitchdl.utils import format_size, get_size

DEFAULT_VIDEO_FORMAT = "mp4"
"""Default format to pass to ffmpeg"""

# Tweak the Click context
# https://click.palletsprojects.com/en/8.1.x/api/#context
CONTEXT = dict(
    # Enable using environment variables to set options
    auto_envvar_prefix="TWITCH_DL",
    # Add shorthand -h for invoking help
    help_option_names=["-h", "--help"],
    # Always show default values for options
    show_default=True,
    # Make help a bit wider
    max_content_width=100,
)

json_option = click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Print data as JSON rather than human readable text",
)


def validate_positive(_ctx: click.Context, _param: click.Parameter, value: Optional[int]):
    if value is not None and value <= 0:
        raise click.BadParameter("must be greater than 0")
    return value


def validate_non_negative(_ctx: click.Context, _param: click.Parameter, value: Optional[int]):
    if value is not None and value < 0:
        raise click.BadParameter("must be greater or equal than 0")
    return value


def validate_time(_ctx: click.Context, _param: click.Parameter, value: str) -> Optional[int]:
    """Parse a time string (hh:mm or hh:mm:ss) to number of seconds."""
    if not value:
        return None

    parts = [int(p) for p in value.split(":")]

    if not 2 <= len(parts) <= 3:
        raise click.BadParameter("invalid time")

    hours = parts[0]
    minutes = parts[1]
    seconds = parts[2] if len(parts) > 2 else 0

    if hours < 0 or not (0 <= minutes <= 59) or not (0 <= seconds <= 59):
        raise click.BadParameter("invalid time")

    return hours * 3600 + minutes * 60 + seconds


def validate_rate(_ctx: click.Context, _param: click.Parameter, value: str) -> Optional[int]:
    if not value:
        return None

    match = re.search(r"^([0-9]+)(k|m|)$", value, flags=re.IGNORECASE)

    if not match:
        raise click.BadParameter("must be an integer, followed by an optional 'k' or 'm'")

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "k":
        return amount * 1024

    if unit == "m":
        return amount * 1024 * 1024

    return amount


# RGBA represented as color in #RRGGBB string and int opacity
ColorParam = Tuple[str, int]


def validate_color_rgba(_c: click.Context, _p: click.Parameter, value: str) -> Optional[ColorParam]:
    match = re.match(r"^#?([0-9a-f]{8})$", value, re.IGNORECASE)
    if not match:
        raise click.BadParameter("must be a color in #RRBBGGAA format")

    value = match.group(1)
    color = f"#{value[0:6]}"
    opacity = int(value[6:], 16)
    return color, opacity


def validate_color_rgb(_c: click.Context, _p: click.Parameter, value: str) -> Optional[str]:
    match = re.match(r"^#?([0-9a-f]{6})$", value, re.IGNORECASE)
    if not match:
        raise click.BadParameter("must be a color in #RRBBGG format")

    return f"#{match.group(1)}"


@click.group(context_settings=CONTEXT)
@click.option("--debug/--no-debug", default=False, help="Enable debug logging to stderr")
@click.option("--verbose/--no-verbose", default=False, help="More verbose debug logging")
@click.option("--color/--no-color", default=sys.stdout.isatty(), help="Use ANSI color in output")
@click.version_option(package_name="twitch-dl")
@click.pass_context
def cli(ctx: click.Context, color: bool, debug: bool, verbose: bool):
    """twitch-dl - twitch.tv downloader

    https://twitch-dl.bezdomni.net/
    """
    ctx.color = color

    if debug:
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARN)
        logging.getLogger("httpcore").setLevel(logging.WARN)
        logging.getLogger("PIL").setLevel(logging.WARN)


@cli.command()
@click.argument("channel_name")
@click.option(
    "-a",
    "--all",
    help="Fetch all clips, overrides --limit",
    is_flag=True,
)
@click.option(
    "-c",
    "--compact",
    help="Show clips in compact mode, one line per video",
    is_flag=True,
)
@click.option(
    "-d",
    "--download",
    help="Download clips in given period (in source quality)",
    is_flag=True,
)
@click.option(
    "-l",
    "--limit",
    help="Number of clips to fetch. Defaults to 40 in compact mode, 10 otherwise.",
    type=int,
    callback=validate_positive,
)
@click.option(
    "-p",
    "--pager",
    help="Number of clips to show per page. Disabled by default.",
    type=int,
    callback=validate_positive,
    is_flag=False,
    flag_value=10,
)
@click.option(
    "-P",
    "--period",
    help="Period from which to return clips",
    default="all_time",
    type=click.Choice(["last_day", "last_week", "last_month", "all_time"]),
)
@click.option(
    "-t",
    "--target-dir",
    help="Target directory when downloading clips",
    type=click.Path(
        file_okay=False,
        readable=False,
        writable=True,
        path_type=Path,
    ),
    default=Path(),
)
@click.option(
    "-w",
    "--workers",
    help="Number of workers for downloading clips concurrently",
    type=int,
    default=10,
)
@json_option
def clips(
    channel_name: str,
    all: bool,
    compact: bool,
    download: bool,
    json: bool,
    limit: Optional[int],
    pager: Optional[int],
    period: ClipsPeriod,
    target_dir: Path,
    workers: int,
):
    """List or download clips for given CHANNEL_NAME."""
    from twitchdl.commands.clips import clips

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    clips(
        channel_name,
        all=all,
        compact=compact,
        download=download,
        json=json,
        limit=limit,
        pager=pager,
        period=period,
        target_dir=target_dir,
        workers=workers,
    )


@cli.command()
@click.argument("ids", nargs=-1)
@click.option(
    "-a",
    "--auth-token",
    help="""Authentication token, passed to Twitch to access subscriber only
         VODs. Can be copied from the `auth_token` cookie in any browser logged
         in on Twitch.""",
)
@click.option(
    "-c",
    "--chapter",
    help="""Download a single chapter of the video. Specify the chapter number
         or use the flag without a number to display a chapter select prompt.
         """,
    type=int,
    is_flag=False,
    flag_value=0,
)
@click.option(
    "--concat",
    is_flag=True,
    help="""Do not use ffmpeg to join files, concat them instead. This will
         produce a .ts file by default.""",
)
@click.option(
    "-d",
    "--dry-run",
    help="Simulate the download provcess without actually downloading any files.",
    is_flag=True,
)
@click.option(
    "-e",
    "--end",
    help="Download video up to this time (hh:mm or hh:mm:ss), not supported for clips",
    callback=validate_time,
)
@click.option(
    "-f",
    "--format",
    help=f"""Video format to convert into, passed to ffmpeg as the target file
         extension. Defaults to `{DEFAULT_VIDEO_FORMAT}`. If `--concat` is
         passed, defaults to `ts`.""",
)
@click.option(
    "-k",
    "--keep",
    help="Don't delete downloaded VODs and playlists after merging.",
    is_flag=True,
)
@click.option(
    "--no-join",
    help="Don't run ffmpeg to join the downloaded vods, implies --keep.",
    is_flag=True,
)
@click.option(
    "--overwrite",
    help="Overwrite target file if it already exists",
    is_flag=True,
)
@click.option(
    "--skip-existing",
    help="Skip target file if it already exists",
    is_flag=True,
)
@click.option(
    "-o",
    "--output",
    help="Output file name template. See docs for details.",
    default=DEFAULT_VIDEO_OUTPUT,
)
@click.option(
    "-q",
    "--quality",
    help="Video quality, e.g. `720p`. Set to `source` to get best quality.",
)
@click.option(
    "-r",
    "--rate-limit",
    help="""Limit the maximum download speed in bytes per second. Use 'k' and
         'm' suffixes for kbps and mbps.""",
    callback=validate_rate,
)
@click.option(
    "-s",
    "--start",
    help="Download video from this time (hh:mm or hh:mm:ss), not supported for clips",
    callback=validate_time,
)
@click.option(
    "-w",
    "--max-workers",
    help="Number of workers for downloading vods concurrently",
    type=int,
    default=10,
)
@click.option(
    "--cache-dir",
    help="Folder where VODs are downloaded before joining. Uses placeholders similar to --output.",
    default=f"{get_cache_dir()}/videos/{{id}}/{{quality}}",
)
def download(
    ids: Tuple[str, ...],
    auth_token: Optional[str],
    chapter: Optional[int],
    concat: bool,
    dry_run: bool,
    end: Optional[int],
    format: str,
    keep: bool,
    no_join: bool,
    overwrite: bool,
    skip_existing: bool,
    output: str,
    quality: Optional[str],
    rate_limit: Optional[int],
    start: Optional[int],
    max_workers: int,
    cache_dir: str,
):
    """Download videos or clips.

    Pass one or more video ID, clip slug or Twitch URL to download.
    """
    from twitchdl.commands.download import download

    if not format:
        format = "ts" if concat else DEFAULT_VIDEO_FORMAT

    if start is not None and end is not None and end <= start:
        raise ConsoleError("End time must be greater than start time")

    options = DownloadOptions(
        auth_token=auth_token,
        chapter=chapter,
        concat=concat,
        dry_run=dry_run,
        end=end,
        format=format,
        keep=keep,
        no_join=no_join,
        overwrite=overwrite,
        skip_existing=skip_existing,
        output=output,
        quality=quality,
        rate_limit=rate_limit,
        start=start,
        max_workers=max_workers,
        cache_dir=cache_dir,
    )

    download(list(ids), options)


@cli.command()
def env():
    """Print environment information for inclusion in bug reports."""
    click.echo(f"twitch-dl {__version__}")
    click.echo(f"Python {sys.version}")
    click.echo(f"Platform: {platform.platform()}")

    click.echo("--")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        click.echo(f"ffmpeg path: {ffmpeg}")
        try:
            subprocess.run(["ffmpeg", "-version"])
        except Exception as ex:
            click.secho("Failed getting ffmpeg version:", fg="red")
            click.secho(f"{ex}", fg="red")
    else:
        click.secho("ffmpeg not found", err=True, fg="red")


@cli.command()
@click.argument("id")
@click.option(
    "-a",
    "--auth-token",
    help="""Authentication token, passed to Twitch to access subscriber only
         VODs. Can be copied from the `auth_token` cookie in any browser logged
         in on Twitch.""",
)
@click.option(
    "--sub-only",
    help="Use sub-only workaround to fetch playlists. Used for testing.",
    is_flag=True,
    hidden=True,
)
@json_option
def info(id: str, json: bool, auth_token: Optional[str], sub_only: bool):
    """Print information for a given Twitch URL, video ID or clip slug."""
    from twitchdl.commands.info import info

    info(id, json=json, auth_token=auth_token, sub_only=sub_only)


@cli.command()
@click.argument("channel_name")
@click.option(
    "-a",
    "--all",
    help="Fetch all videos, overrides --limit",
    is_flag=True,
)
@click.option(
    "-c",
    "--compact",
    help="Show videos in compact mode, one line per video",
    is_flag=True,
)
@click.option(
    "-l",
    "--limit",
    help="Number of videos to fetch. Defaults to 40 in compact mode, 10 otherwise.",
    type=int,
    callback=validate_positive,
)
@click.option(
    "-p",
    "--pager",
    help="Number of videos to show per page. Disabled by default.",
    type=int,
    callback=validate_positive,
    is_flag=False,
    flag_value=10,
)
@click.option(
    "-g",
    "--game",
    "games_tuple",
    help="Show videos of given game (can be given multiple times)",
    multiple=True,
)
@click.option(
    "-s",
    "--sort",
    help="Sorting order of videos",
    default="time",
    type=click.Choice(["views", "time"]),
)
@click.option(
    "-t",
    "--type",
    help="Broadcast type",
    default="archive",
    type=click.Choice(["archive", "highlight", "upload"]),
)
@json_option
def videos(
    channel_name: str,
    all: bool,
    compact: bool,
    games_tuple: Tuple[str, ...],
    json: bool,
    limit: Optional[int],
    pager: Optional[int],
    sort: VideosSort,
    type: VideosType,
):
    """List or download videos for given CHANNEL_NAME."""
    from twitchdl.commands.videos import videos

    # Click provides a tuple, make it a list instead
    games = list(games_tuple)

    videos(
        channel_name,
        all=all,
        compact=compact,
        games=games,
        json=json,
        limit=limit,
        pager=pager,
        sort=sort,
        type=type,
    )


# FOREGROUND_COLOR = "#FEFEFE"
# FOREGROUND_OPACITY = "254"
# BACKGROUND_COLOR = "#FEFEFE"
# BACKGROUND_OPACITY = "0"
# TEXT_EDGE_COLOR = "#000000"
# TEXT_EDGE_TYPE = EdgeType.SoftShadow.value
# FONT_STYLE = FontStyle.MonospacedSansSerif.value
# FONT_SIZE_PERCENT = 0
# TEXT_ALIGNMENT = HorizontalAlignment.Left.value


@cli.group()
def chat():
    """Render chat in various formats (experimental)"""
    print_warning("Chat commands are still experimental, try them out and report any bugs.")


@chat.command("video")
@click.argument("id")
@click.option(
    "-w",
    "--width",
    help="Chat width in pixels",
    type=int,
    default=400,
    callback=validate_positive,
)
@click.option(
    "-h",
    "--height",
    help="Chat height in pixels",
    type=int,
    default=1080,
    callback=validate_positive,
)
@click.option(
    "--font-size",
    help="Font size",
    type=int,
    default=20,
    callback=validate_positive,
)
@click.option(
    "--dark",
    help="Dark mode",
    is_flag=True,
)
@click.option(
    "--pad-x",
    help="Horizontal padding",
    type=int,
    callback=validate_non_negative,
    default=5,
)
@click.option(
    "--pad-y",
    help="Vertical padding",
    type=int,
    callback=validate_non_negative,
    default=5,
)
@click.option(
    "-o",
    "--output",
    help="Output file name template. See docs for details.",
    default=DEFAULT_CHAT_OUTPUT,
)
@click.option(
    "-f",
    "--format",
    help="Video format to convert into, passed to ffmpeg as the target file extension.",
    default="mp4",
)
@click.option(
    "-i",
    "--image-format",
    help="""Image format used to render individual frames, bmp (default) is fast
         but consumes a lot of space. You can switch to png to conserve space
         at cost of speed.""",
    default="bmp",
)
@click.option(
    "--overwrite",
    help="Overwrite the target file if it already exists without prompting.",
    is_flag=True,
)
@click.option(
    "-k",
    "--keep",
    help="Don't delete the generated intermediate frame images.",
    is_flag=True,
)
@click.option(
    "--no-join",
    help="Don't run ffmpeg to join the generated frames, implies --keep.",
    is_flag=True,
)
def chat_video(
    id: str,
    width: int,
    height: int,
    font_size: int,
    dark: bool,
    pad_x: int,
    pad_y: int,
    output: str,
    format: str,
    image_format: str,
    overwrite: bool,
    keep: bool,
    no_join: bool,
):
    """Render twitch chat as video"""
    try:
        from twitchdl.chat.video import render_chat

        render_chat(
            id,
            width,
            height,
            font_size,
            dark,
            (pad_x, pad_y),
            output,
            format,
            image_format,
            overwrite,
            keep,
            no_join,
        )
    except ModuleNotFoundError as ex:
        raise ConsoleError(
            dedent(f"""
                {ex}

                This command requires twitch-dl to be installed with optional "chat" dependencies:
                pipx install "twitch-dl[chat]"

                See documentation for more info:
                https://twitch-dl.bezdomni.net/commands/chat.html
            """)
        )


@chat.command("json")
@click.argument("id")
@click.option(
    "-o",
    "--output",
    help="Output file name template. See docs for details.",
    default=DEFAULT_CHAT_OUTPUT,
)
@click.option(
    "--overwrite",
    help="Overwrite the target file if it already exists without prompting.",
    is_flag=True,
)
def chat_json(id: str, output: str, overwrite: bool):
    """Render twitch chat as json"""
    from twitchdl.chat.json import render_chat_json

    render_chat_json(id, output, overwrite)


class HashType(enum.Enum):
    MD5 = enum.auto()
    SHA1 = enum.auto()


@chat.command("ytt")
@click.argument("id")
@click.option(
    "-f",
    "--foreground",
    default="#FEFEFEFE",
    help="Foreground color in #RRGGBBAA format",
    callback=validate_color_rgba,
)
@click.option(
    "-b",
    "--background",
    default="#FEFEFE00",
    help="Background color in #RRGGBBAA format",
    callback=validate_color_rgba,
)
@click.option(
    "--text-edge-color",
    default="#000000",
    help="Text edge color in #RRGGBB format",
    callback=validate_color_rgb,
)
@click.option(
    "--text-edge-type",
    type=click.Choice([x.name for x in EdgeType], case_sensitive=False),
    default=EdgeType.SoftShadow.name,
    help="Text edge type",
)
@click.option(
    "--text-align",
    type=click.Choice([x.name for x in HorizontalAlignment], case_sensitive=False),
    default=HorizontalAlignment.Left.name,
    help="Text alignemnt",
)
@click.option(
    "--font-style",
    type=click.Choice([x.name for x in FontStyle], case_sensitive=False),
    default=FontStyle.MonospacedSansSerif.name,
    help="Font style",
)
@click.option(
    "--font-size",
    type=click.IntRange(0, 300),
    default=100,
    help="Font size, values 0 - 300 are equivalent to relative 75% - 150% font size.",
)
@click.option(
    "-o",
    "--output",
    help="Output file name template. See docs for details.",
    default=DEFAULT_CHAT_OUTPUT,
)
@click.option(
    "--overwrite",
    help="Overwrite the target file if it already exists without prompting.",
    is_flag=True,
)
def chat_ytt(
    id: str,
    output: str,
    overwrite: bool,
    foreground: ColorParam,
    background: ColorParam,
    text_edge_color: str,
    text_edge_type: str,
    font_style: str,
    font_size: int,
    text_align: str,
):
    """Render twitch chat as youtube subtitles"""
    from twitchdl.chat.ytt import render_chat_ytt

    fg_color, fg_opacity = foreground
    bg_color, bg_opacity = background

    params = YttParams(
        foreground_color=fg_color,
        foreground_opacity=fg_opacity,
        background_color=bg_color,
        background_opacity=bg_opacity,
        text_edge_color=text_edge_color,
        text_edge_type=EdgeType[text_edge_type].value,
        font_style=FontStyle[font_style].value,
        font_size=font_size,
        text_align=text_align,
    )

    from pprint import pp

    pp(params)
    return

    render_chat_ytt(id, output, overwrite, params)


@cli.command
@click.option(
    "-c",
    "--clear",
    "clear_subdir",
    help="Clear cached files",
    type=click.Choice(["all", "fonts", "chats", "videos", "emotes", "badges"]),
)
def cache(clear_subdir: str):
    """View and manage cached files"""
    if clear_subdir:
        clear_path = get_cache_dir() if clear_subdir == "all" else get_cache_dir(clear_subdir)
        size = get_size(clear_path)
        shutil.rmtree(clear_path)
        click.echo(f"Cleared {clear_subdir} cache ({format_size(size)})")
        return

    cache_dir = get_cache_dir()
    click.echo(f"Cache dir: {cache_dir}")

    rows: List[List[str]] = []
    total_size = 0
    for directory in get_cache_subdirs():
        size = get_size(directory)
        rows.append([str(directory), format_size(size)])
        total_size += size

    if not rows:
        click.echo("No files cached")
        return

    click.echo()
    print_table(
        rows,
        headers=["Directory", "Size"],
        footers=["Total", format_size(total_size)],
        alignments={1: "right"},
    )
