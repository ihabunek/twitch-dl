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


def _get_game_ids(names):
    if not names:
        return []

    game_ids = []
    for name in names:
        print_out("<dim>Looking up game '{}'...</dim>".format(name))
        game_id = twitch.get_game_id(name)
        if not game_id:
            raise ConsoleError("Game '{}' not found".format(name))
        game_ids.append(int(game_id))

    return game_ids


def videos(args):
    game_ids = _get_game_ids(args.game)

    print_out("<dim>Loading videos...</dim>")
    generator = twitch.channel_videos_generator(
        args.channel_name, args.limit, args.sort, args.type, game_ids=game_ids)

    first = 1

    for videos, has_more in generator:
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
    else:
        print_out("<yellow>No videos found</yellow>")


def _parse_playlists(playlists_m3u8):
    playlists = m3u8.loads(playlists_m3u8)

    for p in playlists.playlists:
        name = p.media[0].name if p.media else ""
        resolution = "x".join(str(r) for r in p.stream_info.resolution)
        yield name, resolution, p.uri


def _get_playlist_by_name(playlists, quality):
    for name, _, uri in playlists:
        if name == quality:
            return uri

    available = ", ".join([name for (name, _, _) in playlists])
    msg = "Quality '{}' not found. Available qualities are: {}".format(quality, available)
    raise ConsoleError(msg)


def _select_playlist_interactive(playlists):
    print_out("\nAvailable qualities:")
    for n, (name, resolution, uri) in enumerate(playlists):
        print_out("{}) {} [{}]".format(n + 1, name, resolution))

    no = utils.read_int("Choose quality", min=1, max=len(playlists) + 1, default=1)
    _, _, uri = playlists[no - 1]
    return uri


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
    r"^https://(www.)?twitch.tv/videos/(?P<id>\d+)(\?.+)?$",
]

CLIP_PATTERNS = [
    r"^(?P<slug>[A-Za-z0-9]+)$",
    r"^https://(www.)?twitch.tv/\w+/clip/(?P<slug>[A-Za-z0-9]+)(\?.+)?$",
    r"^https://clips.twitch.tv/(?P<slug>[A-Za-z0-9]+)(\?.+)?$",
]


def download(args):
    for pattern in VIDEO_PATTERNS:
        match = re.match(pattern, args.video)
        if match:
            video_id = match.group('id')
            return _download_video(video_id, args)

    for pattern in CLIP_PATTERNS:
        match = re.match(pattern, args.video)
        if match:
            clip_slug = match.group('slug')
            return _download_clip(clip_slug, args)

    raise ConsoleError("Invalid video: {}".format(args.video))


def _get_clip_url(clip, args):
    qualities = clip["videoQualities"]

    # Quality given as an argument
    if args.quality:
        selected_quality = args.quality.rstrip("p")  # allow 720p as well as 720
        for q in qualities:
            if q["quality"] == selected_quality:
                return q["sourceURL"]

        available = ", ".join([str(q["quality"]) for q in qualities])
        msg = "Quality '{}' not found. Available qualities are: {}".format(args.quality, available)
        raise ConsoleError(msg)

    # Ask user to select quality
    print_out("\nAvailable qualities:")
    for n, q in enumerate(qualities):
        print_out("{}) {} [{} fps]".format(n + 1, q["quality"], q["frameRate"]))
    print_out()

    no = utils.read_int("Choose quality", min=1, max=len(qualities), default=1)
    selected_quality = qualities[no - 1]
    return selected_quality["sourceURL"]


def _download_clip(slug, args):
    print_out("<dim>Looking up clip...</dim>")
    clip = twitch.get_clip(slug)

    if not clip:
        raise ConsoleError("Clip '{}' not found".format(slug))

    print_out("Found: <green>{}</green> by <yellow>{}</yellow>, playing <blue>{}</blue> ({})".format(
        clip["title"],
        clip["broadcaster"]["displayName"],
        clip["game"]["name"],
        utils.format_duration(clip["durationSeconds"])
    ))

    url = _get_clip_url(clip, args)
    print_out("<dim>Selected URL: {}</dim>".format(url))

    url_path = urlparse(url).path
    extension = Path(url_path).suffix
    filename = "{}_{}{}".format(
        clip["broadcaster"]["login"],
        utils.slugify(clip["title"]),
        extension
    )

    print_out("Downloading clip...")
    download_file(url, filename)

    print_out("Downloaded: {}".format(filename))


def _download_video(video_id, args):
    if args.start and args.end and args.end <= args.start:
        raise ConsoleError("End time must be greater than start time")

    print_out("<dim>Looking up video...</dim>")
    video = twitch.get_video(video_id)

    print_out("Found: <blue>{}</blue> by <yellow>{}</yellow>".format(
        video['title'], video['channel']['display_name']))

    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_access_token(video_id)

    print_out("<dim>Fetching playlists...</dim>")
    playlists_m3u8 = twitch.get_playlists(video_id, access_token)
    playlists = list(_parse_playlists(playlists_m3u8))
    playlist_uri = (_get_playlist_by_name(playlists, args.quality) if args.quality
            else _select_playlist_interactive(playlists))

    print_out("<dim>Fetching playlist...</dim>")
    response = requests.get(playlist_uri)
    response.raise_for_status()
    playlist = m3u8.loads(response.text)

    base_uri = re.sub("/[^/]+$", "/", playlist_uri)
    target_dir = _crete_temp_dir(base_uri)
    filenames = list(_get_files(playlist, args.start, args.end))

    # Save playlists for debugging purposes
    with open(target_dir + "playlists.m3u8", "w") as f:
        f.write(playlists_m3u8)
    with open(target_dir + "playlist.m3u8", "w") as f:
        f.write(response.text)

    print_out("\nDownloading {} VODs using {} workers to {}".format(
        len(filenames), args.max_workers, target_dir))
    file_paths = download_files(base_uri, target_dir, filenames, args.max_workers)

    print_out("\n\nJoining files...")
    target = _video_target_filename(video, args.format)
    _join_vods(target_dir, file_paths, target)

    if args.keep:
        print_out("\nTemporary files not deleted: {}".format(target_dir))
    else:
        print_out("\nDeleting temporary files...")
        shutil.rmtree(target_dir)

    print_out("Downloaded: {}".format(target))
