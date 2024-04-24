import logging
import platform
import re
import sys
from typing import Optional, Tuple

import click

from twitchdl import __version__
from twitchdl.entities import DownloadOptions
from twitchdl.twitch import ClipsPeriod, VideosSort, VideosType

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


@click.group(context_settings=CONTEXT)
@click.option("--debug/--no-debug", default=False, help="Log debug info to stderr")
@click.option("--color/--no-color", default=sys.stdout.isatty(), help="Use ANSI color in output")
@click.version_option(package_name="twitch-dl")
@click.pass_context
def cli(ctx: click.Context, color: bool, debug: bool):
    """twitch-dl - twitch.tv downloader

    https://twitch-dl.bezdomni.net/
    """
    ctx.color = color

    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("httpx").setLevel(logging.WARN)
        logging.getLogger("httpcore").setLevel(logging.WARN)


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
):
    """List or download clips for given CHANNEL_NAME."""
    from twitchdl.commands.clips import clips

    clips(
        channel_name,
        all=all,
        compact=compact,
        download=download,
        json=json,
        limit=limit,
        pager=pager,
        period=period,
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
    help="Download video up to this time (hh:mm or hh:mm:ss)",
    callback=validate_time,
)
@click.option(
    "-f",
    "--format",
    help="""Video format to convert into, passed to ffmpeg as the target file
         extension. Defaults to `mkv`. If `--concat` is passed, defaults to
         `ts`.""",
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
    help="Overwrite the target file if it already exists without prompting.",
    is_flag=True,
)
@click.option(
    "-o",
    "--output",
    help="Output file name template. See docs for details.",
    default="{date}_{id}_{channel_login}_{title_slug}.{format}",
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
    help="Download video from this time (hh:mm or hh:mm:ss)",
    callback=validate_time,
)
@click.option(
    "-w",
    "--max-workers",
    help="Number of workers for downloading vods concurrently",
    type=int,
    default=5,
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
    output: str,
    quality: Optional[str],
    rate_limit: Optional[int],
    start: Optional[int],
    max_workers: int,
):
    """Download videos or clips.

    Pass one or more video ID, clip slug or Twitch URL to download.
    """
    from twitchdl.commands.download import download

    if not format:
        format = "ts" if concat else "mkv"

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
        output=output,
        quality=quality,
        rate_limit=rate_limit,
        start=start,
        max_workers=max_workers,
    )

    download(list(ids), options)


@cli.command()
def env():
    """Print environment information for inclusion in bug reports."""
    click.echo(f"twitch-dl {__version__}")
    click.echo(f"Python {sys.version}")
    click.echo(f"Platform: {platform.platform()}")


@cli.command()
@click.argument("id")
@json_option
def info(id: str, json: bool):
    """Print information for a given Twitch URL, video ID or clip slug."""
    from twitchdl.commands.info import info

    info(id, json=json)


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
    """List or download clips for given CHANNEL_NAME."""
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
