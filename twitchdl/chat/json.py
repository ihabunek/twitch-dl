"""Generate chat as JSON"""

import json
from pathlib import Path
from typing import Generator, List

import click

from twitchdl.entities import Comment, Video
from twitchdl.output import print_log, print_status
from twitchdl.twitch import get_comments, get_video_comments
from twitchdl.utils import format_time


def generate_chat_json(video: Video, target_path: Path):
    print_log("Loading VideoComments...")
    video_comments = get_video_comments(video["id"])

    comments: List[Comment] = []
    total_duration = video["lengthSeconds"]
    for page in generate_paged_comments(video["id"]):
        if page:
            comments.extend(page)
            offset_seconds = page[-1]["contentOffsetSeconds"]
            print_status(
                f"Loading Comments {format_time(offset_seconds)}/{format_time(total_duration)}",
                transient=True,
                dim=True,
            )

    with open(target_path, "w", encoding="utf8") as f:
        obj = {
            "video": video,
            "video_comments": video_comments,
            "comments": comments,
        }
        json.dump(obj, f)

    click.echo(f"Chat saved to: {target_path}")


def generate_paged_comments(video_id: str) -> Generator[List[Comment], None, None]:
    page = 1
    has_next = True
    cursor = None

    while has_next:
        video = get_comments(video_id, cursor=cursor)
        yield [comment["node"] for comment in video["comments"]["edges"]]

        has_next = video["comments"]["pageInfo"]["hasNextPage"]
        cursor = video["comments"]["edges"][-1]["cursor"]
        page += 1
