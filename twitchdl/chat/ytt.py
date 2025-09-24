"""
Render twitch comments as youtube subs.

Idea from: https://www.twitch.tv/tsoding
Implementation based on: https://github.com/Kam1k4dze/SubChat
"""

import re
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional
from wcwidth import wcswidth  # type: ignore
from xml.etree.ElementTree import Element, ElementTree, SubElement
from xml.etree.ElementTree import Comment as XMLComment
from xml.etree.ElementTree import indent  # type: ignore

from twitchdl.chat.utils import (
    USER_COLORS,
    get_all_comments,
    get_commenter_color,
    get_target_path,
    get_video,
)
from twitchdl.entities import Comment as CommentEntitiy
from twitchdl.entities import Video
from twitchdl.utils import iterate_with_next


class AnchorPoint(Enum):
    TopLeft = "0"
    TopCenter = "1"
    TopRight = "2"
    CenterLeft = "3"
    Center = "4"
    CenterRight = "5"
    BottomLeft = "6"
    BottomCenter = "7"
    BottomRight = "8"


class EdgeType(Enum):
    HardShadow = "1"
    Bevel = "2"
    GlowOutline = "3"
    SoftShadow = "4"


class FontStyle(Enum):
    """Font style (`fs` attribute)"""

    Default = "0"
    """Default font (same as ProportionalSansSerif)."""
    MonospacedSerif = "1"
    """Monospaced Serif (Courier New)"""
    ProportionalSerif = "2"
    """Proportional Serif (Times New Roman)"""
    MonospacedSansSerif = "3"
    """Monospaced Sans-Serif (Lucida Console)"""
    ProportionalSansSerif = "4"
    """Proportional Sans-Serif (Roboto)"""
    Casual = "5"
    """Casual (Comic Sans)"""
    Cursive = "6"
    """Cursive (Monotype Corsiva)"""
    SmallCapitals = "7"
    """Small Capitals (Arial small-caps)"""


class HorizontalAlignment(Enum):
    """Horizontal text alignment (`ju` attribute)"""

    Left = "0"
    Right = "1"
    Center = "2"


class YttOptions(NamedTuple):
    background_color: str
    background_opacity: int
    font_size: int
    font_style: str
    foreground_color: str
    foreground_opacity: int
    horizontal_offset: int
    text_align: str
    text_edge_color: str
    text_edge_type: str
    vertical_offset: int
    vertical_spacing: int
    line_count: int
    line_chars: int


USERNAME_SEPARATOR = ": "


class Line(NamedTuple):
    username: Optional[str]
    username_color: Optional[str]
    text: str


class Comment(NamedTuple):
    start: int
    username: str
    color: str
    lines: List[str]


def render_chat_ytt(id: str, output: str, overwrite: bool, options: YttOptions, pretty: bool):
    format = "ytt"
    video = get_video(id)
    target_path = get_target_path(video, format, output, overwrite)

    all_comments = load_comments(video, options)
    comments_by_start: Dict[int, List[Comment]] = defaultdict(list)
    for comment in all_comments:
        comments_by_start[comment.start].append(comment)

    root = Element("timedtext", attrib={"format": "3"})
    head = SubElement(root, "head")
    body = SubElement(root, "body")

    def add_comment(element: Element, text: str):
        if pretty:
            element.append(XMLComment(text))

    add_comment(head, "Pens")
    pens = add_pens(head, options)

    workspace_id = 1
    add_comment(head, "Default workspace")
    sub_element(head, "ws", id=workspace_id, ju=options.text_align)

    add_comment(head, "Positions")
    for index in range(options.line_count):
        sub_element(
            head,
            "wp",
            id=index,
            ap=AnchorPoint.TopLeft.value,
            ah=options.horizontal_offset,
            av=options.vertical_offset + options.vertical_spacing * index,
        )

    lines: List[Line] = []
    starts = comments_by_start.keys()
    video_end = video["lengthSeconds"] * 1000
    for batch_id, (start, next_start) in enumerate(iterate_with_next(starts)):
        add_comment(body, f"Batch {batch_id}")
        duration = (next_start or video_end) - start
        comments = comments_by_start[start]
        for comment in comments:
            for idx, line in enumerate(comment.lines):
                if idx == 0:
                    lines.append(Line(comment.username, comment.color, line))
                else:
                    lines.append(Line(None, None, line))

        visible_lines = lines[-options.line_count :]
        for position, line in enumerate(visible_lines):
            p = sub_element(body, "p", t=start, d=duration, wp=position, ws=workspace_id, p=0)

            if line.username:
                assert line.username_color is not None
                pen = pens[line.username_color]
                s = sub_element(p, "s", p=pen)
                s.text = line.username + USERNAME_SEPARATOR

                # This is a workaround for a bug with multiple spans, see:
                # https://github.com/Kam1k4dze/SubChat/blob/eb2b399cada48ac7f705fea4f790b30841ff5f65/ytt.ytt#L117-L122
                if line.text:
                    s.tail = "\u200b"

            if line.text:
                s = sub_element(p, "s")
                s.text = line.text

    tree = ElementTree(root)
    if pretty:
        indent(tree)
    tree.write(target_path, xml_declaration=True, encoding="utf-8")


def load_comments(video: Video, params: YttOptions):
    comments = get_all_comments(video)

    return [
        Comment(
            start=comment["contentOffsetSeconds"] * 1000,
            username=comment["commenter"]["displayName"],
            color=get_commenter_color(comment["commenter"]),
            lines=wrap_lines(comment, params),
        )
        for comment in comments
        if comment["commenter"] is not None
    ]


def add_pens(head: Element, options: YttOptions) -> Dict[str, int]:
    # Default pen is 0, colors are 1+
    colors = [options.foreground_color] + USER_COLORS
    pens: Dict[str, int] = {}

    for index, color in enumerate(colors):
        pen_attrs = attrs(
            id=index,
            fc=color,
            fo=options.foreground_opacity,
            bc=options.background_color,
            bo=options.background_opacity,
            ec=options.text_edge_color,
            et=options.text_edge_type,
            fs=options.font_style,
            sz=options.font_size,
        )

        SubElement(head, "pen", pen_attrs)
        pens[color] = index

    return pens


def attrs(**kwargs: Any) -> Dict[str, str]:
    return {k: str(v) for k, v in kwargs.items()}


def sub_element(element: Element, name: str, **attr: Any):
    return SubElement(element, name, attrs(**attr))


def wrap_lines(comment: CommentEntitiy, options: YttOptions) -> List[str]:
    assert comment["commenter"] is not None
    text = "".join(f["text"] for f in comment["message"]["fragments"])
    words: List[str] = re.split(r"\s+", text)

    # First line will contain the username
    username = comment["commenter"]["displayName"]
    line_length = wc_width(username + USERNAME_SEPARATOR)
    line_words: List[str] = []
    lines: List[str] = []

    for word in words:
        word_length = wc_width(word) + 1  # for space
        if line_length + word_length <= options.line_chars:
            line_words.append(word)
            line_length += word_length
        else:
            lines.append(" ".join(line_words))
            line_words = [word]
            line_length = len(word)

    if line_words:
        lines.append(" ".join(line_words))

    return lines


def wc_width(value: str) -> int:
    return wcswidth(value)  # type: ignore
