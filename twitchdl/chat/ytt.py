import re
from collections import defaultdict
from enum import Enum
from itertools import chain, islice, tee
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Tuple,
    TypeVar,
)
from xml.etree.ElementTree import Element, ElementTree, SubElement

from wcwidth import wcswidth  # type: ignore

from twitchdl.chat.utils import USER_COLORS, get_commenter_color
from twitchdl.entities import Comment as CommentEntitiy
from twitchdl.entities import Video


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


# Parametrize
FOREGROUND_COLOR = "#FEFEFE"
FOREGROUND_OPACITY = "254"
BACKGROUND_COLOR = "#FEFEFE"
BACKGROUND_OPACITY = "0"
TEXT_EDGE_COLOR = "#000000"
TEXT_EDGE_TYPE = EdgeType.SoftShadow.value
FONT_STYLE = FontStyle.MonospacedSansSerif.value
FONT_SIZE_PERCENT = 0
TEXT_ALIGNMENT = HorizontalAlignment.Left.value

HORIZONTAL_MARGIN = 70
VERTICAL_MARGIN = 0
VERTICAL_SPACING = 5
TOTAL_DISPLAY_LINES = 19
MAX_CHARS_PER_LINE = 30
USERNAME_SEPARATOR = ": "


class Batch(NamedTuple):
    comments: List[Any]
    start: int
    duration: int


class Line(NamedTuple):
    username: Optional[str]
    username_color: Optional[str]
    text: str


class Span(NamedTuple):
    text: str
    color: str = FOREGROUND_COLOR


class Comment(NamedTuple):
    start: int
    username: str
    color: str
    lines: List[str]


def generate_chat_ytt(video: Video, target_path: Path):
    all_comments = load_comments(video)
    comments_by_start: Dict[int, List[Comment]] = defaultdict(list)
    for comment in all_comments:
        comments_by_start[comment.start].append(comment)

    root = Element("timedtext", attrib={"format": "3"})
    head = SubElement(root, "head")
    body = SubElement(root, "body")

    add_comment(head, "Pens")
    pens = add_pens(head)

    workspace_id = 1
    add_comment(head, "Default workspace")
    sub_element(head, "ws", id=workspace_id, ju=TEXT_ALIGNMENT)

    add_comment(head, "Positions")
    for index in range(TOTAL_DISPLAY_LINES):
        sub_element(
            head,
            "wp",
            id=index,
            ap=AnchorPoint.TopLeft.value,
            ah=HORIZONTAL_MARGIN,
            av=VERTICAL_SPACING * index,
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

        visible_lines = lines[-TOTAL_DISPLAY_LINES:]
        for position, line in enumerate(visible_lines):
            p = sub_element(body, "p", t=start, d=duration, wp=position, ws=workspace_id, p=0)

            if line.username:
                assert line.username_color is not None
                pen = pens[line.username_color]
                s = sub_element(p, "s", p=pen)
                s.text = line.username + USERNAME_SEPARATOR

            s = sub_element(p, "s")
            s.text = line.text

    tree = ElementTree(root)
    tree.write(target_path, xml_declaration=True, encoding="utf-8")


def load_comments(video: Video):
    from twitchdl.chat.json import load_comments

    comments = load_comments(video)
    return [
        Comment(
            start=comment["contentOffsetSeconds"] * 1000,
            username=comment["commenter"]["displayName"],
            color=get_commenter_color(comment["commenter"]),
            lines=wrap_lines(comment),
        )
        for comment in comments
        if comment["commenter"] is not None
    ]


def add_pens(head: Element) -> Dict[str, int]:
    # Default pen is 0, colors are 1+
    colors = [FOREGROUND_COLOR] + USER_COLORS
    pens: Dict[str, int] = {}

    for index, color in enumerate(colors):
        pen_attrs = attrs(
            id=index,
            fc=color,
            fo=FOREGROUND_OPACITY,
            bc=BACKGROUND_COLOR,
            bo=BACKGROUND_OPACITY,
            ec=TEXT_EDGE_COLOR,
            et=TEXT_EDGE_TYPE,
            fs=FONT_STYLE,
            sz=FONT_SIZE_PERCENT,
        )

        SubElement(head, "pen", pen_attrs)
        pens[color] = index

    return pens


def attrs(**kwargs: Any) -> Dict[str, str]:
    return {k: str(v) for k, v in kwargs.items()}


def sub_element(element: Element, name: str, **attr: Any):
    return SubElement(element, name, attrs(**attr))


def add_comment(element: Element, text: str):
    from xml.etree.ElementTree import Comment

    element.append(Comment(text))


def wrap_lines(comment: CommentEntitiy) -> List[str]:
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
        if line_length + word_length <= MAX_CHARS_PER_LINE:
            line_words.append(word)
            line_length += word_length
        else:
            lines.append(" ".join(line_words))
            line_words = []
            line_length = 0

    if line_words:
        lines.append(" ".join(line_words))

    return lines


def wc_width(value: str) -> int:
    return wcswidth(value)  # type: ignore


T = TypeVar("T")


def iterate_with_next(iterable: Iterable[T]) -> Iterator[Tuple[T, Optional[T]]]:
    """
    Creates an iterator which provides previous, current and next item.
    """
    items, nexts = tee(iterable, 2)
    nexts = chain(islice(nexts, 1, None), [None])
    return zip(items, nexts)
