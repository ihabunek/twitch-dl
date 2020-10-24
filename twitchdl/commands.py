import m3u8
import re
import requests
import shutil
import subprocess
import tempfile
from pathlib import Path
import os
import json

from os import path
from pathlib import Path
from urllib.parse import urlparse

from twitchdl import twitch, utils
from twitchdl.download import download_file, download_files
from twitchdl.exceptions import ConsoleError
from twitchdl.output import print_out, print_video

def get_len(filename):
   result = subprocess.Popen(["ffprobe", filename, '-print_format', 'json', '-show_streams', '-loglevel', 'quiet'],
     stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
   return float(json.loads(result.stdout.read())['streams'][0]['duration'])

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

        if not args.pager:
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


def _join_vods(playlist_path, target, overwrite, anion):
  url = "https://api.twitch.tv/kraken/videos/" + anion + "?client_id=9kr7kfumdnzkcr9rgg4g0qtfnk2618&api_version=5&limit=100"
  r = requests.get(str(url))
  content = r.text
  lengther = len(content)
  getjder = json.loads(content)
  if bool(getjder.get("length")):
    video_length = getjder["length"]
    print("Video Length is: " + str(video_length))
  else:
    video_length = int(20000)
    print("Video Length Not Found, Defaulted to " + str(video_length))
  size = sum(f.stat().st_size for f in Path("/tmp/twitch-dl").glob('**/*') if f.is_file() and f.name[len(f.name) - 3:len(f.name)] == '.ts')
  print("Size in bytes is: " + str(size))
  global command
  if size > 301990590:
    command = 'ffmpeg -hwaccel cuvid -hwaccel_output_format cuda -vcodec h264 -r 24 -i "' + playlist_path + '" -b:a 96000 -b:v ' + str((301990590 * 4.5) / video_length) + ' -preset ultrafast -c:a copy -s 1280x720 "' + str(target) +  '" -stats -loglevel warning'
  else: 
    command = 'ffmpeg -i "' + str(playlist_path) + '" -c copy "' + str(target) + '" -stats -loglevel warning'

  if overwrite:
    command.append(" -y")

  print(command)
  os.popen(command).read()


def _video_target_filename(video, format):
    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", video['published_at'])
    date = "".join(match.groups())
    
    if os.name == "posix":
      name = date + " " + video['_id'][1:] + " " + video['channel']['name'] + " " + str(video.get('game').replace("/", "")) + " " + str(video.get('title').replace("/", "")) + " " + str(video.get("fps").get("chunked")) + " " + str(video.get("resolutions").get("chunked")) + " " + str(video.get("length"))
    else:
      name = date + " " + video['_id'][1:] + " " + video['channel']['name'] + " " + str(str(utils.slugify(video.get('game'))).replace("/", "")) + " " + str(str(utils.slugify(video.get('title'))).replace("/", "")) + " " + str(video.get("fps").get("chunked")) + " " + str(video.get("resolutions").get("chunked")) + " " + str(video.get("length"))
    
    print(name + "." + format)
      
    return name + "." + format


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
    
    letsgo = video_id
    print_out("\n\nJoining files...")
    target = _video_target_filename(video, args.format)
    _join_vods(playlist_path, target, args.overwrite, letsgo)

    if args.keep:
        print_out("\n<dim>Temporary files not deleted: {}</dim>".format(target_dir))
    else:
        print_out("\n<dim>Deleting temporary files...</dim>")
        shutil.rmtree(target_dir)

    print_out("\nDownloaded: <green>{}</green>".format(target))
