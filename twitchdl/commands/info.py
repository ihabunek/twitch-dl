from typing import List, Optional

import click
import m3u8

from twitchdl import twitch, utils
from twitchdl.exceptions import ConsoleError, PlaylistAuthRequireError
from twitchdl.naming import video_placeholders
from twitchdl.output import bold, dim, print_clip, print_json, print_log, print_table, print_video
from twitchdl.playlists import Playlist, parse_playlists
from twitchdl.subonly import get_subonly_playlists
from twitchdl.twitch import Chapter, Clip, Video

def info(id: str, *, json: bool = False, auth_token: Optional[str], sub_only: bool):
    video_id = utils.parse_video_identifier(id)
    if video_id:
        print_log("Fetching video...")
        video = twitch.get_video(video_id)

        if not video:
            raise ConsoleError(f"Video {video_id} not found")

        print_log("Fetching access token...")
        access_token = twitch.get_access_token(video_id, auth_token)

        if sub_only:
            print_log("Fetching sub-only playlists...")
            playlists = get_subonly_playlists(video)
        else:
            print_log("Fetching playlists...")
            try:
                playlists_text = twitch.get_playlists(video["id"], access_token)
                playlists = parse_playlists(playlists_text)
            except PlaylistAuthRequireError:
                print_log("Possible subscriber-only VOD, attempting workaround...")
                playlists = get_subonly_playlists(video)

        print_log("Fetching chapters...")
        chapters = twitch.get_video_chapters(video_id)

        if json:
            video_json(video, playlists, chapters)
        else:
            video_info(video, playlists, chapters)
        return

    clip_slug = utils.parse_clip_identifier(id)
    if clip_slug:
        print_log("Fetching clip...")
        clip = twitch.get_clip(clip_slug)
        if not clip:
            raise ConsoleError(f"Clip {clip_slug} not found")

        if json:
            print_json(clip)
        else:
            clip_info(clip)
        return

    raise ConsoleError(f"Invalid input: {id}")


def video_info(video: Video, playlists: List[Playlist], chapters: List[Chapter]):
    click.echo()
    print_video(video)

    click.echo("Playlists:\n")

    playlist_data = [
        [
            f"{p.name} {dim('source')}" if p.is_source else p.name,
            p.group_id,
            f"{p.resolution}",
            p.url,
        ]
        for p in playlists
    ]
    print_table(playlist_data, headers=["Name", "Group", "Resolution", "URL"])

    if chapters:
        click.echo()
        click.echo("Chapters:")
        for chapter in chapters:
            start = utils.format_time(chapter["positionMilliseconds"] // 1000, force_hours=True)
            duration = utils.format_time(chapter["durationMilliseconds"] // 1000)
            click.echo(f'{start} {bold(chapter["description"])} ({duration})')

    placeholders = video_placeholders(video, format="mkv")
    placeholders = [[f"{{{k}}}", v] for k, v in placeholders.items()]
    click.echo("")
    print_table(placeholders, headers=["Placeholder", "Value"])


def video_json(video: Video, playlists: List[Playlist], chapters: List[Chapter]):
    info = {**video, "playlists": [p.__dict__ for p in playlists], "chapters": chapters}
    print_json(info)


def clip_info(clip: Clip):
    click.echo()
    print_clip(clip)
    click.echo()
    click.echo("Download links:")

    if clip["videoQualities"]:
        for q in clip["videoQualities"]:
            click.echo(f"{bold(q['quality'])} [{q['frameRate']} fps] {q['sourceURL']}")
    else:
        click.echo("No download URLs found")
