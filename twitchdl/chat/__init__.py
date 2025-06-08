from pathlib import Path
from typing import Tuple

import click

from twitchdl.chat.json import generate_chat_json
from twitchdl.chat.video import generate_chat_video
from twitchdl.chat.ytt import generate_chat_ytt
from twitchdl.exceptions import ConsoleError
from twitchdl.naming import video_filename
from twitchdl.output import blue, print_found_video, print_log
from twitchdl.twitch import get_video
from twitchdl.utils import parse_video_identifier


def render_chat(
    id: str,
    width: int,
    height: int,
    font_size: int,
    dark: bool,
    padding: Tuple[int, int],
    output: str,
    format: str,
    image_format: str,
    overwrite: bool,
    keep: bool,
    no_join: bool,
    json: bool,
    ytt: bool,
):
    video_id = parse_video_identifier(id)
    if not video_id:
        raise ConsoleError("Invalid video ID")

    print_log("Looking up video...")
    video = get_video(video_id)
    if not video:
        raise ConsoleError(f"Video {video_id} not found")
    print_found_video(video)

    target_path = Path(video_filename(video, format, output))
    print_log(f"Target: {blue(target_path)}")

    if not overwrite and target_path.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()
        overwrite = True

    if json:
        generate_chat_json(video, target_path)
        return

    if ytt:
        generate_chat_ytt(video, target_path)
        return

    generate_chat_video(
        video,
        width,
        height,
        font_size,
        dark,
        padding,
        image_format,
        overwrite,
        keep,
        no_join,
        target_path,
    )
