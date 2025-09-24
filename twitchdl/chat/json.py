from __future__ import annotations

import json
from pathlib import Path
from typing import List

import click

from twitchdl.chat.video import generate_paged_comments
from twitchdl.entities import Comment, Video
from twitchdl.exceptions import ConsoleError
from twitchdl.naming import video_filename
from twitchdl.output import blue, print_found_video, print_log, print_status
from twitchdl.twitch import get_video, get_video_comments
from twitchdl.utils import format_time, parse_video_identifier


def render_chat_json(id: str, output: str, overwrite: bool):
    video_id = parse_video_identifier(id)
    if not video_id:
        raise ConsoleError("Invalid video ID")

    print_log("Looking up video...")
    video = get_video(video_id)
    if not video:
        raise ConsoleError(f"Video {video_id} not found")
    print_found_video(video)

    target_path = Path(video_filename(video, "json", output))
    print_log(f"Target: {blue(target_path)}")

    if not overwrite and target_path.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()
        overwrite = True

    print_log("Loading VideoComments...")
    video_comments = get_video_comments(video["id"])

    comments: List[Comment] = []
    total_duration = video["lengthSeconds"]
    for page in generate_paged_comments(video["id"]):
        if page:
            comments.extend(page)
            offset_seconds = page[-1]["contentOffsetSeconds"]
            progress = _format_progress(offset_seconds, total_duration)
            print_status(f"Loading Comments {progress}", transient=True, dim=True)

    with open(target_path, "w", encoding="utf8") as f:
        obj = {
            "video": video,
            "video_comments": video_comments,
            "comments": comments,
        }
        json.dump(obj, f)

    click.echo(f"Chat saved to: {target_path}")


def _format_progress(offset_seconds: int, total_duration: int):
    formatted = f"{format_time(offset_seconds)}/{format_time(total_duration)}"

    if total_duration > 0:
        percentage = round(100 * offset_seconds / total_duration)
        formatted += f" ({percentage}%)"

    return formatted
