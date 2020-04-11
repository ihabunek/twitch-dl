import m3u8
import os
import pathlib
import re
import requests
import shutil
import subprocess
import tempfile

from urllib.parse import urlparse

from twitchdl import twitch, utils
from twitchdl.download import download_files
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_video


def videos(channel_name, limit, offset, sort, **kwargs):
    print_out("Looking up user...")
    user = twitch.get_user(channel_name)
    if not user:
        raise ConsoleError("User {} not found.".format(channel_name))

    print_out("Loading videos...")
    videos = twitch.get_channel_videos(user["id"], limit, offset, sort)
    count = len(videos['videos'])
    if not count:
        print_out("No videos found")
        return

    first = offset + 1
    last = offset + len(videos['videos'])
    total = videos["_total"]
    print_out("<yellow>Showing videos {}-{} of {}</yellow>".format(first, last, total))

    for video in videos['videos']:
        print_video(video)


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


def _parse_video_id(video_id):
    """This can be either a integer ID or an URL to the video on twitch."""
    if re.search(r"^\d+$", video_id):
        return int(video_id)

    match = re.search(r"^https://www.twitch.tv/videos/(\d+)(\?.+)?$", video_id)
    if match:
        return int(match.group(1))

    raise ConsoleError("Invalid video ID given, expected integer ID or Twitch URL")


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


def download(video_id, max_workers, format='mkv', start=None, end=None, keep=False, **kwargs):
    video_id = _parse_video_id(video_id)

    if start and end and end <= start:
        raise ConsoleError("End time must be greater than start time")

    print_out("Looking up video...")
    video = twitch.get_video(video_id)

    print_out("Found: <blue>{}</blue> by <yellow>{}</yellow>".format(
        video['title'], video['channel']['display_name']))

    print_out("Fetching access token...")
    access_token = twitch.get_access_token(video_id)

    print_out("Fetching playlists...")
    playlists = twitch.get_playlists(video_id, access_token)
    parsed = m3u8.loads(playlists)
    selected = _select_quality(parsed.playlists)

    print_out("\nFetching playlist...")
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
