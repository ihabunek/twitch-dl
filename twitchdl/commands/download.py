import m3u8
import re
import requests
import shutil
import subprocess
import tempfile

from os import path
from pathlib import Path
from urllib.parse import urlparse, urlencode

from twitchdl import twitch, utils
from twitchdl.download import download_file, download_files
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out


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


def _join_vods(playlist_path, target, overwrite, video):
    command = [
        "ffmpeg",
        "-i", playlist_path,
        "-c", "copy",
        "-metadata", "artist={}".format(video["creator"]["displayName"]),
        "-metadata", "title={}".format(video["title"]),
        "-metadata", "encoded_by=twitch-dl",
        "-stats",
        "-loglevel", "warning",
        target,
    ]

    if overwrite:
        command.append("-y")

    print_out("<dim>{}</dim>".format(" ".join(command)))
    result = subprocess.run(command)
    if result.returncode != 0:
        raise ConsoleError("Joining files failed")


def _video_target_filename(video, format):
    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", video['publishedAt'])
    date = "".join(match.groups())

    name = "_".join([
        date,
        video['id'],
        video['creator']['login'],
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
        clip["broadcaster"]["login"],
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
    return str(temp_dir)


def download(args):
    video_id = utils.parse_video_identifier(args.video)
    if video_id:
        return _download_video(video_id, args)

    clip_slug = utils.parse_clip_identifier(args.video)
    if clip_slug:
        return _download_clip(clip_slug, args)

    raise ConsoleError("Invalid input: {}".format(args.video))


def _get_clip_url(clip, quality):
    qualities = clip["videoQualities"]

    # Quality given as an argument
    if quality:
        if quality == "source":
            return qualities[0]["sourceURL"]

        selected_quality = quality.rstrip("p")  # allow 720p as well as 720
        for q in qualities:
            if q["quality"] == selected_quality:
                return q["sourceURL"]

        available = ", ".join([str(q["quality"]) for q in qualities])
        msg = "Quality '{}' not found. Available qualities are: {}".format(quality, available)
        raise ConsoleError(msg)

    # Ask user to select quality
    print_out("\nAvailable qualities:")
    for n, q in enumerate(qualities):
        print_out("{}) {} [{} fps]".format(n + 1, q["quality"], q["frameRate"]))
    print_out()

    no = utils.read_int("Choose quality", min=1, max=len(qualities), default=1)
    selected_quality = qualities[no - 1]
    return selected_quality["sourceURL"]


def get_clip_authenticated_url(slug, quality):
    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_clip_access_token(slug)

    if not access_token:
        raise ConsoleError("Access token not found for slug '{}'".format(slug))

    url = _get_clip_url(access_token, quality)

    query = urlencode({
        "sig": access_token["playbackAccessToken"]["signature"],
        "token": access_token["playbackAccessToken"]["value"],
    })

    return "{}?{}".format(url, query)


def _download_clip(slug, args):
    print_out("<dim>Looking up clip...</dim>")
    clip = twitch.get_clip(slug)

    if not clip:
        raise ConsoleError("Clip '{}' not found".format(slug))

    print_out("<dim>Fetching access token...</dim>")
    access_token = twitch.get_clip_access_token(slug)

    if not access_token:
        raise ConsoleError("Access token not found for slug '{}'".format(slug))

    print_out("Found: <green>{}</green> by <yellow>{}</yellow>, playing <blue>{}</blue> ({})".format(
        clip["title"],
        clip["broadcaster"]["displayName"],
        clip["game"]["name"],
        utils.format_duration(clip["durationSeconds"])
    ))

    url = get_clip_authenticated_url(slug, args.quality)
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

    if not video:
        raise ConsoleError("Video {} not found".format(video_id))

    print_out("Found: <blue>{}</blue> by <yellow>{}</yellow>".format(
        video['title'], video['creator']['displayName']))

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
    _join_vods(playlist_path, target, args.overwrite, video)

    if args.keep:
        print_out("\n<dim>Temporary files not deleted: {}</dim>".format(target_dir))
    else:
        print_out("\n<dim>Deleting temporary files...</dim>")
        shutil.rmtree(target_dir)

    print_out("\nDownloaded: <green>{}</green>".format(target))
