import re
import subprocess
import tempfile

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from urllib.request import urlretrieve

from twitchdl import twitch
from twitchdl.output import print_out


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


def format_length(seconds):
    hours = seconds // 3600
    remainder = seconds % 3600
    minutes = remainder // 60

    if hours:
        return "{}h {}min".format(hours, minutes)

    return "{}min".format(minutes)


def _print_video(video):
    published_at = video['published_at'].replace('T', ' @ ').replace('Z', '')
    length = format_length(video['length'])
    name = video['channel']['display_name']

    print_out("\n<bold>{}</bold>".format(video['_id'][1:]))
    print_out("<green>{}</green>".format(video["title"]))
    print_out("<cyan>{}</cyan> playing <cyan>{}</cyan>".format(name, video['game']))
    print_out("Published <cyan>{}</cyan>  Length: <cyan>{}</cyan> ".format(published_at, length))


def videos(channel_name, **kwargs):
    videos = twitch.get_channel_videos(channel_name)

    print("Found {} videos".format(videos["_total"]))

    for video in videos['videos']:
        _print_video(video)


def _select_playlist_by_quality(playlists):
    print("\nAvailable qualities:")
    for no, v in playlists.items():
        print("{}) {}".format(no, v[0]))

    keys = list(playlists.keys())
    no = read_int("Choose quality", min=min(keys), max=max(keys), default=keys[0])

    return playlists[no][1]


def _print_progress(futures):
    counter = 1
    total = len(futures)

    for future in as_completed(futures):
        msg = "Downloaded {}/{} ({}%)".format(counter, total, 100 * counter // total)
        print("\r" + msg, end='')
        counter += 1


def _download_files(base_url, directory, filenames, max_workers):
    args = [(base_url.format(f), "/".join([directory, f])) for f in filenames]

    fns = [partial(urlretrieve, url, path) for url, path in args]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fn) for fn in fns]
        _print_progress(futures)

    return [f.result()[0] for f in futures]


def _join_vods(directory, filenames, target):
    input_path = "{}/files.txt".format(directory)

    with open(input_path, 'w') as f:
        for filename in filenames:
            f.write('file {}\n'.format(filename))

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
    dttm = re.sub(r'\D+', '-', video['published_at'][:16])
    name = " - ".join([dttm, video['channel']['display_name'], video['game']])
    return "{}.{}".format(name, format)


def download(video_id, max_workers, format='mkv', **kwargs):
    print("Looking up video...")
    video = twitch.get_video(video_id)

    print("Fetching access token...")
    access_token = twitch.get_access_token(video_id)

    print("Fetching playlists...")
    playlists = twitch.get_playlists(video_id, access_token)
    playlist_url = _select_playlist_by_quality(playlists)

    print("\nFetching playlist...")
    base_url, filenames = twitch.get_playlist_urls(playlist_url)

    target = _video_target_filename(video, format)

    with tempfile.TemporaryDirectory() as directory:
        print("Downloading...")
        _download_files(base_url, directory, filenames, max_workers)

        print("\n\nJoining files...")
        _join_vods(directory, filenames, target)

    print("\nDownloaded: {}".format(target))
