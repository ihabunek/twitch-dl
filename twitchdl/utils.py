import re
import unicodedata


def _format_size(value, digits, unit):
    if digits > 0:
        return "{{:.{}f}}{}".format(digits, unit).format(value)
    else:
        return "{{:d}}{}".format(unit).format(value)


def format_size(bytes_, digits=1):
    if bytes_ < 1024:
        return _format_size(bytes_, digits, "B")

    kilo = bytes_ / 1024
    if kilo < 1024:
        return _format_size(kilo, digits, "kB")

    mega = kilo / 1024
    if mega < 1024:
        return _format_size(mega, digits, "MB")

    return _format_size(mega / 1024, digits, "GB")


def format_duration(total_seconds):
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = total_seconds % 60

    if hours:
        return "{} h {} min".format(hours, minutes)

    if minutes:
        return "{} min {} sec".format(minutes, seconds)

    return "{} sec".format(seconds)


def read_int(msg, min, max, default):
    msg = msg + " [default {}]: ".format(default)

    while True:
        try:
            val = input(msg)
            if not val:
                return default
            if min <= int(val) <= max:
                return int(val)
        except ValueError:
            pass


def slugify(value):
    re_pattern = re.compile(r'[^\w\s-]', flags=re.U)
    re_spaces = re.compile(r'[-\s]+', flags=re.U)
    value = str(value)
    value = unicodedata.normalize('NFKC', value)
    value = re_pattern.sub('', value).strip().lower()
    return re_spaces.sub('_', value)


VIDEO_PATTERNS = [
    r"^(?P<id>\d+)?$",
    r"^https://(www.)?twitch.tv/videos/(?P<id>\d+)(\?.+)?$",
]

CLIP_PATTERNS = [
    r"^(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)$",
    r"^https://(www.)?twitch.tv/\w+/clip/(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)(\?.+)?$",
    r"^https://clips.twitch.tv/(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9_-]{16})?)(\?.+)?$",
]


def parse_video_identifier(identifier):
    """Given a video ID or URL returns the video ID, or null if not matched"""
    for pattern in VIDEO_PATTERNS:
        match = re.match(pattern, identifier)
        if match:
            return match.group("id")


def parse_clip_identifier(identifier):
    """Given a clip slug or URL returns the clip slug, or null if not matched"""
    for pattern in CLIP_PATTERNS:
        match = re.match(pattern, identifier)
        if match:
            return match.group("slug")
