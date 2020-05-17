import m3u8
import os
import pathlib
import re
import requests
import shutil
import subprocess
import tempfile

from pathlib import Path
from urllib.parse import urlparse

from twitchdl import twitch, utils
from twitchdl.download import download_file, download_files
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_video


def _continue():
    print_out(
        "\nThere are more videos. "
        "Press <green><b>Enter</green> to continue, "
        "<yellow><b>Ctrl+C</yellow> to break."
    )

    try:
        input()
    except KeyboardInterrupt:
        return False

    return True

def videos(channel_name, limit, sort, type, **kwargs):
    print_out("Loading videos...")
    generator = twitch.channel_videos_generator(channel_name, limit, sort, type)

    first = 1

    for videos, has_more in generator:
        if "edges" not in videos:
            break

        count = len(videos["edges"]) if "edges" in videos else 0
        total = videos["totalCount"]
        last = first + count - 1

        print_out("-" * 80)
        print_out("<yellow>Showing videos {}-{} of {}</yellow>".format(first, last, total))

        for video in videos["edges"]:
            print_video(video["node"])

        if not has_more or not _continue():
            break

        first += count


def _select_quality(playlists):
    print_out("\nAvailable qualities:")
    for n, p in enumerate(playlists):
        name = p.media[0].name if p.media else ""
        resolution = "x".join(str(r) for r in p.stream_info.resolution)
        print_out("{}) {} [{}]".format(n + 1, name, resolution))

    no = utils.read_int("Choose quality", min=1, max=len(playlists) + 1, default=1)

    return playlists[no - 1]


def _join_vods(directory, file_paths, target):
    input_path = "{}/files.txt".format(directory)

    with open(input_path, 'w') as f:
        for path in file_paths:
            f.write('file {}\n'.format(os.path.basename(path)))

    result = subprocess.run([
        "ffmpeg",
        "-f", "concat",
        "-i", input_path,
        "-c", "copy",
        target,
        "-stats",
        "-loglevel", "warning",
    ])

    result.check_returncode()


def _video_target_filename(video, format):
    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", video['published_at'])
    date = "".join(match.groups())

    name = "_".join([
        date,
        video['_id'][1:],
        video['channel']['name'],
        utils.slugify(video['title']),
    ])

    return name + "." + format


def _get_files(playlist, start, end):
    """Extract files for download from playlist."""
    vod_start = 0
    for segment in playlist.segments:
        vod_end = vod_start + segment.duration

        # `vod_end > start` is used here becuase it's better to download a bit
        # more than a bit less, similar for the end condition
        start_condition = not start or vod_end > start
        end_condition = not end or vod_start < end

        if start_condition and end_condition:
            yield segment.uri

        vod_start = vod_end


def _crete_temp_dir(base_uri):
    """Create a temp dir to store downloads if it doesn't exist."""
    path = urlparse(base_uri).path
    directory = '{}/twitch-dl{}'.format(tempfile.gettempdir(), path)
    pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
    return directory


VIDEO_PATTERNS = [
    r"^(?P<id>\d+)?$",
    r"^https://www.twitch.tv/videos/(?P<id>\d+)(\?.+)?$",
]

CLIP_PATTERNS = [
    r"^(?P<slug>[A-Za-z]+)$",
    r"^https://www.twitch.tv/\w+/clip/(?P<slug>[A-Za-z]+)(\?.+)?$",
    r"^https://clips.twitch.tv/(?P<slug>[A-Za-z]+)(\?.+)?$",
]


def download(video, **kwargs):
    for pattern in CLIP_PATTERNS:
        match = re.match(pattern, video)
        if match:
            clip_slug = match.group('slug')
            return _download_clip(clip_slug, **kwargs)

    for pattern in VIDEO_PATTERNS:
        match = re.match(pattern, video)
        if match:
            video_id = match.group('id')
            return _download_video(video_id, **kwargs)

    raise ConsoleError("Invalid video: {}".format(video))


def _download_clip(slug, **kwargs):
    print_out("<dim>Looking up clip...</dim>")
    clip = twitch.get_clip(slug)

    print_out("Found: <green>{}</green> by <yellow>{}</yellow>, playing <blue>{}</blue> ({})".format(
        clip["title"],
        clip["broadcaster"]["displayName"],
        clip["game"]["name"],
        utils.format_duration(clip["durationSeconds"])
    ))

    print_out("\nAvailable qualities:")
    qualities = clip["videoQualities"]
    for n, q in enumerate(qualities):
        print_out("{}) {} [{} fps]".format(n + 1, q["quality"], q["frameRate"]))

    no = utils.read_int("Choose quality", min=1, max=len(qualities), default=1)
    selected_quality = qualities[no - 1]
    url = selected_quality["sourceURL"]

    url_path = urlparse(url).path
    extension = Path(url_path).suffix
    filename = "{}_{}{}".format(
        clip["broadcaster"]["login"],
        utils.slugify(clip["title"]),
        extension
    )

    print("Downloading clip...")
    download_file(url, filename)

    print("Downloaded: {}".format(filename))


def _download_video(video_id, max_workers, format='mkv', start=None, end=None, keep=False, **kwargs):
    if start and end and end <= start:
        raise ConsoleError("End time must be greater than start time")

    print_out("<dim>Looking up video...</dim>")
    video = twitch.get_video(video_id)

    print_out("Found: <blue>{}</blue> by <yellow>{}</yellow>".format(
        video['title'], video['channel']['display_name']))

    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_access_token(video_id)

    print_out("<dim>Fetching playlists...</dim>")
    playlists = twitch.get_playlists(video_id, access_token)
    parsed = m3u8.loads(playlists)
    selected = _select_quality(parsed.playlists)

    print_out("<dim>\nFetching playlist...</dim>")
    response = requests.get(selected.uri)
    response.raise_for_status()
    playlist = m3u8.loads(response.text)

    base_uri = re.sub("/[^/]+$", "/", selected.uri)
    target_dir = _crete_temp_dir(base_uri)
    filenames = list(_get_files(playlist, start, end))

    # Save playlists for debugging purposes
    with open(target_dir + "playlists.m3u8", "w") as f:
        f.write(playlists)
    with open(target_dir + "playlist.m3u8", "w") as f:
        f.write(response.text)

    print_out("\nDownloading {} VODs using {} workers to {}".format(
        len(filenames), max_workers, target_dir))
    file_paths = download_files(base_uri, target_dir, filenames, max_workers)

    print_out("\n\nJoining files...")
    target = _video_target_filename(video, format)
    _join_vods(target_dir, file_paths, target)

    if keep:
        print_out("\nTemporary files not deleted: {}".format(target_dir))
    else:
        print_out("\nDeleting temporary files...")
        shutil.rmtree(target_dir)

    print_out("Downloaded: {}".format(target))
