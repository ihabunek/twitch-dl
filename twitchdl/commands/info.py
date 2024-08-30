from typing import List

import click
import m3u8

from twitchdl import twitch, utils
from twitchdl.exceptions import ConsoleError
from twitchdl.naming import video_placeholders
from twitchdl.output import bold, dim, print_clip, print_json, print_log, print_table, print_video
from twitchdl.playlists import parse_playlists
from twitchdl.twitch import Chapter, Clip, Video


def info(id: str, *, json: bool = False):
    video_id = utils.parse_video_identifier(id)
    if video_id:
        print_log("Fetching video...")
        video = twitch.get_video(video_id)

        if not video:
            raise ConsoleError(f"Video {video_id} not found")

        print_log("Fetching access token...")
        access_token = twitch.get_access_token(video_id)

        print_log("Fetching playlists...")
        playlists = twitch.get_playlists(video_id, access_token)

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


def video_info(video: Video, playlists: str, chapters: List[Chapter]):
    click.echo()
    print_video(video)

    click.echo("Playlists:\n")

    playlist_headers = ["Name", "Group", "Resolution", "URL"]
    playlist_data = [
        [
            f"{p.name} {dim('source')}" if p.is_source else p.name,
            p.group_id,
            f"{p.resolution}",
            p.url,
        ]
        for p in parse_playlists(playlists)
    ]
    print_table(playlist_headers, playlist_data)

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
    print_table(["Placeholder", "Value"], placeholders)


def video_json(video: Video, playlists: str, chapters: List[Chapter]):
    playlists = m3u8.loads(playlists).playlists

    video["playlists"] = [
        {
            "bandwidth": p.stream_info.bandwidth,
            "resolution": p.stream_info.resolution,
            "codecs": p.stream_info.codecs,
            "video": p.stream_info.video,
            "uri": p.uri,
        }
        for p in playlists
    ]

    video["chapters"] = chapters

    print_json(video)


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
