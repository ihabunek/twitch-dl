from pathlib import Path
from typing import Generator, List

import click
from twitchdl import twitch
from twitchdl.entities import Comment, Commenter, Video
from twitchdl.exceptions import ConsoleError
from twitchdl.naming import video_filename
from twitchdl.output import blue, print_found_video, print_log, print_status
from twitchdl.utils import format_time, parse_video_identifier


# Some nice colors taken from
# https://flatuicolors.com/
USER_COLORS = [
    "#16a085",  # GREEN SEA
    "#27ae60",  # NEPHRITIS
    "#2980b9",  # BELIZE HOLE
    "#686de0",  # EXODUS FRUIT
    "#7f8c8d",  # ASBESTOS
    "#9b59b6",  # AMETHYST
    "#be2edd",  # STEEL PINK
    "#c0392b",  # POMEGRANATE
    "#d35400",  # PUMPKIN
    "#e67e22",  # CARROT
    "#e74c3c",  # ALIZARIN
    "#f1c40f",  # SUN FLOWER
]


def get_commenter_color(commenter: Commenter) -> str:
    """Return a consistent random color for a commenter"""
    user_color_index = int(commenter["id"]) % len(USER_COLORS)
    return USER_COLORS[user_color_index]


def get_video(id: str) -> Video:
    video_id = parse_video_identifier(id)
    if not video_id:
        raise ConsoleError("Invalid video ID")

    print_log("Looking up video...")
    video = twitch.get_video(video_id)
    if not video:
        raise ConsoleError(f"Video {video_id} not found")

    print_found_video(video)

    return video


def get_target_path(video: Video, format: str, output: str, overwrite: bool) -> Path:
    target_path = Path(video_filename(video, format, output))
    print_log(f"Target: {blue(target_path)}")

    if not overwrite and target_path.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()

    return target_path


def get_all_comments(video: Video) -> List[Comment]:
    comments: List[Comment] = []
    total_duration = video["lengthSeconds"]
    for page in _generate_paged_comments(video["id"]):
        if page:
            comments.extend(page)
            offset_seconds = page[-1]["contentOffsetSeconds"]
            progress = _format_progress(offset_seconds, total_duration)
            print_status(f"Loading Comments {progress}", transient=True, dim=True)
    return comments


def _generate_paged_comments(video_id: str) -> Generator[List[Comment], None, None]:
    page = 1
    has_next = True
    cursor = None

    while has_next:
        video = twitch.get_comments(video_id, cursor=cursor)
        yield [comment["node"] for comment in video["comments"]["edges"]]

        has_next = video["comments"]["pageInfo"]["hasNextPage"]
        cursor = video["comments"]["edges"][-1]["cursor"]
        page += 1


def _format_progress(offset_seconds: int, total_duration: int):
    formatted = f"{format_time(offset_seconds)}/{format_time(total_duration)}"

    if total_duration > 0:
        percentage = round(100 * offset_seconds / total_duration)
        formatted += f" ({percentage}%)"

    return formatted
