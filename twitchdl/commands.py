import m3u8
import re
import requests
import shutil
import subprocess
import tempfile

from os import path
from pathlib import Path
from urllib.parse import urlparse

from twitchdl import twitch, utils
from twitchdl.download import download_file, download_files
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_clip, print_video, print_json


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


def _clips_json(args):
    clips = twitch.get_channel_clips(args.channel_name, args.period, args.limit)
    nodes = list(edge["node"] for edge in clips["edges"])
    print_json(nodes)


def _clips_download(args):
    generator = twitch.channel_clips_generator(args.channel_name, args.period, 100)
    for clips, _ in generator:
        for clip in clips["edges"]:
            clip = clip["node"]
            url = clip["videoQualities"][0]["sourceURL"]
            target = _clip_target_filename(clip)
            if path.exists(target):
                print_out("Already downloaded: <green>{}</green>".format(target))
            else:
                print_out("Downloading: <yellow>{}</yellow>".format(target))
                download_file(url, target)


def clips(args):
    if args.json:
        return _clips_json(args)

    if args.download:
        return _clips_download(args)

    print_out("<dim>Loading clips...</dim>")
    generator = twitch.channel_clips_generator(args.channel_name, args.period, args.limit)

    first = 1

    for clips, has_more in generator:
        count = len(clips["edges"]) if "edges" in clips else 0
        last = first + count - 1

        print_out("-" * 80)
        print_out("<yellow>Showing clips {}-{} of ??</yellow>".format(first, last))

        for clip in clips["edges"]:
            print_clip(clip["node"])

        if not args.pager:
            print_out(
                "\n<dim>There are more clips. "
                "Increase the --limit or use --pager to see the rest.</dim>"
            )
            break

        if not has_more or not _continue():
            break

        first += count
    else:
        print_out("<yellow>No clips found</yellow>")


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

        if not args.pager and has_more:
            print_out(
                "\n<dim>There are more videos. "
                "Increase the --limit or use --pager to see the rest.</dim>"
            )
            break

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
    if quality == "source":
        _, _, uri = playlists[0]
        return uri

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


def _join_vods(playlist_path, target, overwrite):
    command = [
        "ffmpeg",
        "-i", playlist_path,
        "-c", "copy",
        target,
        "-stats",
        "-loglevel", "warning",
    ]

    if overwrite:
        command.append("-y")

    print_out("<dim>{}</dim>".format(" ".join(command)))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise ConsoleError("Joining files failed")


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


def _clip_target_filename(clip):
    url = clip["videoQualities"][0]["sourceURL"]
    _, ext = path.splitext(url)
    ext = ext.lstrip(".")

    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", clip["createdAt"])
    date = "".join(match.groups())

    name = "_".join([
        date,
        clip["id"],
        clip["broadcaster"]["channel"]["name"],
        utils.slugify(clip["title"]),
    ])

    return "{}.{}".format(name, ext)


def _get_vod_paths(playlist, start, end):
    """Extract unique VOD paths for download from playlist."""
    files = []
    vod_start = 0
    for segment in playlist.segments:
        vod_end = vod_start + segment.duration

        # `vod_end > start` is used here becuase it's better to download a bit
        # more than a bit less, similar for the end condition
        start_condition = not start or vod_end > start
        end_condition = not end or vod_start < end

        if start_condition and end_condition and segment.uri not in files:
            files.append(segment.uri)

        vod_start = vod_end

    return files


def _crete_temp_dir(base_uri):
    """Create a temp dir to store downloads if it doesn't exist."""
    path = urlparse(base_uri).path.lstrip("/")
    temp_dir = Path(tempfile.gettempdir(), "twitch-dl", path)
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


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
        if args.quality == "source":
            return qualities[0]["sourceURL"]

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

    target = _clip_target_filename(clip)

    print_out("Downloading clip...")
    download_file(url, target)

    print_out("Downloaded: {}".format(target))


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
    vod_paths = _get_vod_paths(playlist, args.start, args.end)

    # Save playlists for debugging purposes
    with open(path.join(target_dir, "playlists.m3u8"), "w") as f:
        f.write(playlists_m3u8)
    with open(path.join(target_dir, "playlist.m3u8"), "w") as f:
        f.write(response.text)

    print_out("\nDownloading {} VODs using {} workers to {}".format(
        len(vod_paths), args.max_workers, target_dir))
    path_map = download_files(base_uri, target_dir, vod_paths, args.max_workers)

    # Make a modified playlist which references downloaded VODs
    # Keep only the downloaded segments and skip the rest
    org_segments = playlist.segments.copy()
    playlist.segments.clear()
    for segment in org_segments:
        if segment.uri in path_map:
            segment.uri = path_map[segment.uri]
            playlist.segments.append(segment)

    playlist_path = path.join(target_dir, "playlist_downloaded.m3u8")
    playlist.dump(playlist_path)

    if args.no_join:
        print_out("\n\n<dim>Skipping joining files...</dim>")
        print_out("VODs downloaded to:\n<blue>{}</blue>".format(target_dir))
        return

    print_out("\n\nJoining files...")
    target = _video_target_filename(video, args.format)
    _join_vods(playlist_path, target, args.overwrite)

    if args.keep:
        print_out("\n<dim>Temporary files not deleted: {}</dim>".format(target_dir))
    else:
        print_out("\n<dim>Deleting temporary files...</dim>")
        shutil.rmtree(target_dir)

    print_out("\nDownloaded: <green>{}</green>".format(target))
