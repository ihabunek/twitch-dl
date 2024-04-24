import sys
from typing import List, Optional

import click

from twitchdl import twitch
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_json, print_log, print_paged, print_video, print_video_compact


def videos(
    channel_name: str,
    *,
    all: bool,
    compact: bool,
    games: List[str],
    json: bool,
    limit: Optional[int],
    pager: Optional[int],
    sort: twitch.VideosSort,
    type: twitch.VideosType,
):
    game_ids = get_game_ids(games)

    # Set different defaults for limit for compact display
    limit = limit or (40 if compact else 10)

    # Ignore --limit if --pager or --all are given
    max_videos = sys.maxsize if all or pager else limit

    total_count, generator = twitch.channel_videos_generator(
        channel_name, max_videos, sort, type, game_ids=game_ids
    )

    if json:
        videos = list(generator)
        print_json({"count": len(videos), "totalCount": total_count, "videos": videos})
        return

    if total_count == 0:
        click.echo("No videos found")
        return

    if pager:
        print_fn = print_video_compact if compact else print_video
        print_paged("Videos", generator, print_fn, pager, total_count)
        return

    count = 0
    for video in generator:
        if compact:
            print_video_compact(video)
        else:
            click.echo()
            print_video(video)
        count += 1

    click.echo()
    click.echo("-" * 80)
    click.echo(f"Videos 1-{count} of {total_count}")

    if total_count > count:
        click.secho(
            "\nThere are more videos. "
            + "Increase the --limit, use --all or --pager to see the rest.",
            dim=True,
        )


def get_game_ids(names: List[str]) -> List[str]:
    return [get_game_id(name) for name in names]


def get_game_id(name: str) -> str:
    print_log(f"Looking up game '{name}'...")
    game_id = twitch.get_game_id(name)
    if not game_id:
        raise ConsoleError(f"Game '{name}' not found")
    return game_id
