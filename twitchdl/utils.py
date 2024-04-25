import re
import unicodedata
from typing import Optional, Union

import click


def _format_size(value: float, digits: int, unit: str):
    if digits > 0:
        return f"{{:.{digits}f}}{unit}".format(value)
    else:
        return f"{int(value)}{unit}"


def format_size(bytes_: Union[int, float], digits: int = 1):
    if bytes_ < 1024:
        return _format_size(bytes_, digits, "B")

    kilo = bytes_ / 1024
    if kilo < 1024:
        return _format_size(kilo, digits, "kB")

    mega = kilo / 1024
    if mega < 1024:
        return _format_size(mega, digits, "MB")

    return _format_size(mega / 1024, digits, "GB")


def format_duration(total_seconds: Union[int, float]) -> str:
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = total_seconds % 60

    if hours:
        return f"{hours} h {minutes} min"

    if minutes:
        return f"{minutes} min {seconds} sec"

    return f"{seconds} sec"


def format_time(total_seconds: Union[int, float], force_hours: bool = False) -> str:
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = total_seconds % 60

    if hours or force_hours:
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    return f"{minutes:02}:{seconds:02}"


def read_int(msg: str, min: int, max: int, default: Optional[int] = None) -> int:
    while True:
        try:
            val = click.prompt(msg, default=default, type=int)
            if default and not val:
                return default
            if min <= int(val) <= max:
                return int(val)
        except ValueError:
            pass


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"[^\w\s_-]", "", value)
    value = re.sub(r"[\s_-]+", "_", value)
    return value.strip("_").lower()


def titlify(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value))
    value = re.sub(r"[^\w\s\[\]().-]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


VIDEO_PATTERNS = [
    r"^(?P<id>\d+)?$",
    r"^https://(www\.|m\.)?twitch\.tv/videos/(?P<id>\d+)(\?.+)?$",
]

CLIP_PATTERNS = [
    r"^(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)$",
    r"^https://(www\.|m\.)?twitch\.tv/\w+/clip/(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)(\?.+)?$",
    r"^https://clips\.twitch\.tv/(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)(\?.+)?$",
]


def parse_video_identifier(identifier: str) -> Optional[str]:
    """Given a video ID or URL returns the video ID, or null if not matched"""
    for pattern in VIDEO_PATTERNS:
        match = re.match(pattern, identifier)
        if match:
            return match.group("id")


def parse_clip_identifier(identifier: str) -> Optional[str]:
    """Given a clip slug or URL returns the clip slug, or null if not matched"""
    for pattern in CLIP_PATTERNS:
        match = re.match(pattern, identifier)
        if match:
            return match.group("slug")
