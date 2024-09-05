from __future__ import annotations

import re
import shutil
import subprocess
import time
from itertools import groupby
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple
from urllib.parse import urlparse

import click
from PIL import Image, ImageDraw

from twitchdl import cache
from twitchdl.entities import Badge, Comment, Emote, Video
from twitchdl.exceptions import ConsoleError
from twitchdl.fonts import Font, char_name, group_by_font, load_font, make_group_by_font
from twitchdl.naming import video_filename
from twitchdl.output import green, print_json, print_log, print_status
from twitchdl.twitch import get_comments, get_video, get_video_comments
from twitchdl.utils import format_time, iterate_with_next, parse_video_identifier

# Use NotoSans for latin, greek, cyrillic
# Use NotoSansCJK for Chinese, Japanese, and Korean
# This should cover most text used in twitch chat
# TODO: Make fonts configurable so users can choose their own
TEXT_FONTS = [
    "https://github.com/notofonts/notofonts.github.io/raw/main/fonts/NotoSans/full/variable-ttf/NotoSans[wdth,wght].ttf",
    "https://github.com/googlefonts/noto-cjk/raw/main/Sans/Variable/OTC/NotoSansCJK-VF.ttf.ttc",
]

# Use NotoColorEmoji for rendering Emoji
BITMAP_FONTS = [
    ("https://github.com/googlefonts/noto-emoji/raw/main/fonts/NotoColorEmoji.ttf", 109),
]


def render_chat(
    id: str,
    width: int,
    height: int,
    font_size: int,
    dark: bool,
    padding: Tuple[int, int],
    output: str,
    format: str,
    overwrite: bool,
    json: bool,
):
    video_id = parse_video_identifier(id)
    if not video_id:
        raise ConsoleError("Invalid video ID")

    print_log("Looking up video...")
    video = get_video(video_id)
    if not video:
        raise ConsoleError(f"Video {video_id} not found")
    total_duration = video["lengthSeconds"]

    if json:
        render_chat_json(video)
        return

    target_path = Path(video_filename(video, format, output))
    if not overwrite and target_path.exists():
        response = click.prompt("File exists. Overwrite? [Y/n]", default="Y", show_default=False)
        if response.lower().strip() != "y":
            raise click.Abort()
        overwrite = True

    print_log("Loading video comments...")
    video_comments = get_video_comments(video_id)
    badges_by_id = {badge["id"]: badge for badge in video_comments["badges"]}

    fonts = load_fonts(font_size)
    foreground = "#ffffff" if dark else "#000000"
    background = "#000000" if dark else "#ffffff"
    screen = Screen(width, height, fonts, foreground, background, padding)
    frames: List[Tuple[Path, int]] = []

    cache_dir = cache.get_cache_dir(f"chat/{video_id}")

    first = True
    start = time.monotonic()
    for group_index, offset, duration, comments in group_comments(video_id, total_duration):
        if group_index == 0:
            # Save the initial empty frame
            frame_path = cache_dir / f"chat_{0:05d}.bmp"
            screen.padded_image().save(frame_path)
            frames.append((frame_path, offset))

        for comment in comments:
            if not first:
                screen.next_line()
            draw_comment(screen, comment, dark, badges_by_id)
            first = False

        frame_path = cache_dir / f"chat_{offset:05d}.bmp"
        screen.padded_image().save(frame_path)
        frames.append((frame_path, duration))
        _print_progress(group_index, offset, start, total_duration)

    spec_path = cache_dir / "concat.txt"
    with open(spec_path, "w") as f:
        for path, duration in frames:
            f.write(f"file '{path.resolve()}'\n")
            f.write(f"duration {duration}\n")

    print_status("Generating chat video...", dim=True)
    generate_video(spec_path, target_path, overwrite)

    print_status("Deleting cache...", dim=True)
    shutil.rmtree(cache_dir)


def render_chat_json(video: Video):
    print_log("Loading VideoComments...")
    video_comments = get_video_comments(video["id"])

    print_log("Loading Comments...")
    comments = list(generate_comments(video["id"]))

    print_json(
        {
            "video": video,
            "video_comments": video_comments,
            "comments": comments,
        }
    )


def load_fonts(font_size: int):
    fonts: List[Font] = []

    def print_font_info(font: Font):
        print_log(f"    Name: {font.name}")
        print_log(f"    Codepoints: {len(font.codepoints)}")
        print_log(f"    Variations: {', '.join(font.variations)}")

    for url in TEXT_FONTS:
        filename = Path(urlparse(url).path).name
        path = cache.download_cached(url, filename=filename, subdir="fonts")
        print_log(f"Loading text font: {path}")
        font = load_font(path, False, font_size)
        print_font_info(font)
        fonts.append(font)

    for url, font_size in BITMAP_FONTS:
        filename = Path(urlparse(url).path).name
        path = cache.download_cached(url, filename=filename, subdir="fonts")
        print_log(f"Loading bitmap font: {path}")
        font = load_font(path, True, font_size)
        print_font_info(font)
        fonts.append(font)

    return fonts


def _print_progress(index: int, offset: int, start: float, total_duration: int):
    perc = 100 * offset / total_duration
    duration = time.monotonic() - start
    print_status(
        f"Rendering chat frame {index} at {index / duration:.1f}fps, "
        + f"{format_time(offset)}/{format_time(total_duration)} ({perc:.0f}%)",
        transient=True,
    )


def add_frame_to_spec(concat_spec: str, frame_path: Path, duration: int) -> str:
    concat_spec += f"file '{frame_path.resolve()}'\n"
    concat_spec += f"duration {duration}\n"
    return concat_spec


def draw_comment(screen: Screen, comment: Comment, dark: bool, badges_by_id: Dict[str, Badge]):
    time = format_time(comment["contentOffsetSeconds"])
    screen.draw_text(time + " ", "gray")

    for message_badge in comment["message"]["userBadges"]:
        # Skip 'empty' badges
        if message_badge["id"] == "Ozs=":
            continue
        badge = badges_by_id.get(message_badge["id"])
        if not badge:
            print_status(f"Badge not found: {message_badge}")
            continue
        badge_path = download_badge(badge)
        if not badge_path:
            print_status(f"Failed downloading badge {message_badge}")
            continue
        badge_image = Image.open(badge_path)
        screen.draw_image(badge_image)

    if comment["message"]["userBadges"]:
        screen.draw_text(" ")

    user = comment["commenter"]["displayName"] if comment["commenter"] else "UNKWNOW"
    user_color = comment["message"]["userColor"]

    screen.draw_text(user, user_color)
    screen.draw_text(": ")

    for fragment in comment["message"]["fragments"]:
        if fragment["emote"]:
            emote_path = download_emote(fragment["emote"], dark)
            if emote_path:
                emote_image = Image.open(emote_path)
                screen.draw_image(emote_image)
            else:
                print_status(f"Failed downloading emote {fragment['emote']}")
                screen.draw_text(fragment["text"])
        else:
            screen.draw_text(fragment["text"])


class Screen:
    def __init__(
        self,
        width: int,
        height: int,
        fonts: List[Font],
        foreground: str,
        background: str,
        padding: Tuple[int, int],
    ):
        self.foreground = foreground
        self.background = background
        self.padding = padding
        self.fonts = fonts
        self.x: int = 0
        self.y: int = 0

        self.group_by_font = make_group_by_font(fonts, self.on_char_not_found)

        self.line_height = max(f.height for f in fonts if not f.is_bitmap)
        left, _, right, _ = fonts[0].image_font.getbbox(" ")
        self.space_size = int(right - left)

        px, py = padding
        image_size = (width - 2 * px, height - 2 * py)
        self._image = Image.new("RGBA", image_size, self.background)
        self._draw = ImageDraw.Draw(self._image)

    def on_char_not_found(self, char: str):
        """Invoked when a char cannot be rendered in any of the fonts."""
        print_status(f"Cannot render char '{char}' Name: {char_name(char)} Codepoint: {ord(char)}")

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, image: Image.Image):
        self._image = image
        self._draw = ImageDraw.Draw(self._image)

    @property
    def draw(self) -> ImageDraw.ImageDraw:
        return self._draw

    def draw_text(self, text: str, color: Optional[str] = None):
        # Split into words while keeping the whitespace
        for word in re.split(r"(?=\s)", text):
            # for fragment, font in self.group_by_font(word):
            for fragment, font in group_by_font(word, self.fonts):
                if font.is_bitmap:
                    for emoji in fragment:
                        self.draw_emoji(emoji, font)
                else:
                    self.draw_text_fragment(fragment, font, color)

    def draw_text_fragment(self, fragment: str, font: Font, color: Optional[str]):
        length = font.get_text_length(fragment)
        if self.image.width < self.x + length:
            self.next_line()
        self.draw.text(  # type: ignore
            (self.x, self.y),
            fragment,
            fill=color or self.foreground,
            font=font.image_font,
        )
        self.x += length

    def draw_image(self, image: Image.Image):
        if self.image.width < self.x + image.width:
            self.next_line()

        x = self.x + self.space_size
        y = self.y

        if image.height < self.line_height:
            y += self.line_height - image.height - 2  # baseline align (ish)

        if image.mode != self.image.mode:
            image = image.convert(self.image.mode)

        self.image.alpha_composite(image, (x, y))
        self.x += image.width + self.space_size

    def draw_emoji(self, emoji: str, font: Font):
        source_size = font.get_text_size(emoji)
        source_width, source_height = source_size

        if source_width == 0 or source_height == 0:
            print_status(f"Emoji '{emoji}' not renderable in font {font.name}, skipping")
            return

        aspect_ratio = source_width / source_height
        target_height = self.line_height
        target_width = int(target_height * aspect_ratio)
        target_size = (target_width, target_height)

        if self.image.width < self.x + target_width:
            self.next_line()

        emoji_image = Image.new("RGBA", source_size)
        emoji_draw = ImageDraw.Draw(emoji_image)
        emoji_draw.text((0, 0), emoji, font=font.image_font, embedded_color=True)  # type: ignore

        # TODO: cache this image so we don't do it every time
        resized = emoji_image.resize(target_size)
        self.image.alpha_composite(resized, (self.x + self.space_size, self.y))
        self.x += target_width + self.space_size

    def next_line(self):
        line_spacing = int(self.line_height * 0.2)
        required_height = self.y + self.line_height * 2 + line_spacing
        if self.image.height < required_height:
            self.shift(required_height - self.image.height)

        self.x = 0
        self.y += self.line_height + line_spacing

    def shift(self, dy: int):
        cropped_image = self.image.crop((0, dy, self.image.width, self.image.height))
        shifted_image = Image.new(self.image.mode, self.image.size, color=self.background)
        shifted_image.paste(cropped_image, (0, 0))
        self.image = shifted_image
        self.y -= dy

    def padded_image(self):
        px, py = self.padding
        padded_size = (self.image.width + 2 * px, self.image.height + 2 * py)
        padded_image = Image.new(self.image.mode, padded_size, color=self.background)
        padded_image.paste(self.image, (px, py))
        return padded_image


def generate_video(spec_path: Path, target: Path, overwrite: bool):
    print_status("Generating chat video...")

    command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        spec_path,
        "-fps_mode",
        "vfr",
        "-pix_fmt",
        "yuv420p",
        "-stats",
        "-loglevel",
        "warning",
        target,
        "-y",
    ]

    if overwrite:
        command.append("-y")

    result = subprocess.run(command)
    if result.returncode != 0:
        raise ConsoleError("Joining files failed")

    print_status(f"Saved: {green(target)}")


def download_badge(badge: Badge) -> Optional[Path]:
    # TODO: make badge size configurable?
    url = badge["image1x"]
    return cache.download_cached(url, subdir="badges")


def download_emote(emote: Emote, dark: bool) -> Optional[Path]:
    # TODO: make emote size customizable
    emote_id = emote["emoteID"]
    variant = "dark" if dark else "light"
    url = f"https://static-cdn.jtvnw.net/emoticons/v2/{emote_id}/default/{variant}/1.0"
    return cache.download_cached(url, subdir="emotes")


def group_comments(video_id: str, total_duration: int):
    g1 = generate_comments(video_id)
    g2 = groupby(g1, lambda x: x["contentOffsetSeconds"])
    # Delazify the comments list, without this they are consumed before we get to them
    g3 = ((offset, list(comments)) for offset, comments in g2)
    g4 = iterate_with_next(g3)
    g5 = enumerate(g4)
    # We need to go deeper? ^^;

    for index, ((offset, comments), next_pair) in g5:
        next_offset = next_pair[0] if next_pair else total_duration
        duration = next_offset - offset
        yield index, offset, duration, comments


def generate_comments(video_id: str) -> Generator[Comment, None, None]:
    page = 1
    has_next = True
    cursor = None

    while has_next:
        video = get_comments(video_id, cursor=cursor)
        for comment in video["comments"]["edges"]:
            yield comment["node"]

        has_next = video["comments"]["pageInfo"]["hasNextPage"]
        cursor = video["comments"]["edges"][-1]["cursor"]
        page += 1
