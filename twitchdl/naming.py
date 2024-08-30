import os
from typing import Dict

from twitchdl import utils
from twitchdl.entities import Clip, Video
from twitchdl.exceptions import ConsoleError

DEFAULT_OUTPUT_TEMPLATE = "{date}_{id}_{channel_login}_{title_slug}.{format}"


def video_filename(video: Video, format: str, output: str) -> str:
    subs = video_placeholders(video, format)
    return _format(output, subs)


def video_placeholders(video: Video, format: str) -> Dict[str, str]:
    date, time = video["publishedAt"].split("T")
    game = video["game"]["name"] if video["game"] else "Unknown"

    return {
        "channel": video["creator"]["displayName"],
        "channel_login": video["creator"]["login"],
        "date": date,
        "datetime": video["publishedAt"],
        "format": format,
        "game": game,
        "game_slug": utils.slugify(game),
        "id": video["id"],
        "time": time,
        "title": utils.titlify(video["title"]),
        "title_slug": utils.slugify(video["title"]),
    }


def clip_filename(clip: Clip, output: str):
    subs = clip_placeholders(clip)
    return _format(output, subs)


def clip_placeholders(clip: Clip) -> Dict[str, str]:
    date, time = clip["createdAt"].split("T")
    game = clip["game"]["name"] if clip["game"] else "Unknown"

    if clip["videoQualities"]:
        url = clip["videoQualities"][0]["sourceURL"]
        _, ext = os.path.splitext(url)
        ext = ext.lstrip(".")
    else:
        ext = "mp4"

    return {
        "channel": clip["broadcaster"]["displayName"],
        "channel_login": clip["broadcaster"]["login"],
        "date": date,
        "datetime": clip["createdAt"],
        "format": ext,
        "game": game,
        "game_slug": utils.slugify(game),
        "id": clip["id"],
        "slug": clip["slug"],
        "time": time,
        "title": utils.titlify(clip["title"]),
        "title_slug": utils.slugify(clip["title"]),
    }


def _format(output: str, subs: Dict[str, str]) -> str:
    try:
        return output.format(**subs)
    except KeyError as e:
        supported = ", ".join(subs.keys())
        raise ConsoleError(f"Invalid key {e} used in --output. Supported keys are: {supported}")
