import sys

from twitchdl import twitch
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_paged_videos, print_video, print_json, print_video_compact


def videos(
    channel_name: str,
    *,
    all: bool,
    compact: bool,
    games: list[str],
    json: bool,
    limit: int | None,
    pager: int | None,
    sort: twitch.VideosSort,
    type: twitch.VideosType,
):
    game_ids = _get_game_ids(games)

    # Set different defaults for limit for compact display
    limit = limit or (40 if compact else 10)

    # Ignore --limit if --pager or --all are given
    max_videos = sys.maxsize if all or pager else limit

    total_count, generator = twitch.channel_videos_generator(
        channel_name, max_videos, sort, type, game_ids=game_ids)

    if json:
        videos = list(generator)
        print_json({
            "count": len(videos),
            "totalCount": total_count,
            "videos": videos
        })
        return

    if total_count == 0:
        print_out("<yellow>No videos found</yellow>")
        return

    if pager:
        print_paged_videos(generator, pager, total_count)
        return

    count = 0
    for video in generator:
        if compact:
            print_video_compact(video)
        else:
            print_out()
            print_video(video)
        count += 1

    print_out()
    print_out("-" * 80)
    print_out(f"<yellow>Videos 1-{count} of {total_count}</yellow>")

    if total_count > count:
        print_out()
        print_out(
            "<dim>There are more videos. Increase the --limit, use --all or --pager to see the rest.</dim>"
        )


def _get_game_ids(names: list[str]) -> list[str]:
    if not names:
        return []

    game_ids = []
    for name in names:
        print_out(f"<dim>Looking up game '{name}'...</dim>")
        game_id = twitch.get_game_id(name)
        if not game_id:
            raise ConsoleError(f"Game '{name}' not found")
        game_ids.append(int(game_id))

    return game_ids
