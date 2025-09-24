import json

import click

from twitchdl.chat.utils import get_all_comments, get_target_path, get_video
from twitchdl.output import print_log
from twitchdl.twitch import get_video_comments


def render_chat_json(id: str, output: str, overwrite: bool):
    format = "json"
    video = get_video(id)
    target_path = get_target_path(video, format, output, overwrite)

    print_log("Loading VideoComments...")
    video_comments = get_video_comments(video["id"])

    print_log("Loading Comments...")
    comments = get_all_comments(video)

    with open(target_path, "w", encoding="utf8") as f:
        obj = {
            "video": video,
            "video_comments": video_comments,
            "comments": comments,
        }
        json.dump(obj, f)

    click.echo(f"Chat saved to: {target_path}")
