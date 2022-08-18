import sys

from twitchdl import twitch
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_paged_videos, print_video, print_json, print_video_compact


def videos(args):
    game_ids = _get_game_ids(args.game)

    # Set different defaults for limit for compact display
    limit = args.limit or (40 if args.compact else 10)

    # Ignore --limit if --pager or --all are given
    max_videos = sys.maxsize if args.all or args.pager else limit

    total_count, generator = twitch.channel_videos_generator(
        args.channel_name, max_videos, args.sort, args.type, game_ids=game_ids)

    if args.json:
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

    if args.pager:
        print_paged_videos(generator, args.pager, total_count)
        return

    count = 0
    for video in generator:
        if args.compact:
            print_video_compact(video)
        else:
            print_out()
            print_video(video)
        count += 1

    print_out()
    print_out("-" * 80)
    print_out("<yellow>Videos {}-{} of {}</yellow>".format(1, count, total_count))

    if total_count > count:
        print_out()
        print_out(
            "<dim>There are more videos. Increase the --limit, use --all or --pager to see the rest.</dim>"
        )


def _get_game_ids(names):
    if not names:
        return []

    game_ids = []
    for name in names:
        print_out("<dim>Looking up game '{}'...</dim>".format(name))
        game_id = twitch.get_game_id(name)
        if not game_id:
            raise ConsoleError("Game '{}' not found".format(name))
        game_ids.append(int(game_id))

    return game_ids
