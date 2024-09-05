from functools import lru_cache
import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Generator, Iterable, List, Optional, Set, Tuple

from fontTools.ttLib import TTFont, TTLibFileIsCollectionError  # type: ignore
from fontTools.ttLib.ttCollection import TTCollection  # type: ignore
from PIL import ImageFont

from twitchdl.cache import get_cache_dir
from twitchdl.output import print_log, print_status


@dataclass
class Font:
    path: Path
    image_font: ImageFont.FreeTypeFont
    codepoints: Set[int]
    is_bitmap: bool
    size: int

    @property
    def name(self) -> Optional[str]:
        return self.image_font.getname()[0]

    @property
    def height(self) -> int:
        ascent, descent = self.image_font.getmetrics()
        return ascent + descent

    def get_text_length(self, text: str) -> int:
        return math.ceil(self.image_font.getlength(text))  # type: ignore

    def get_text_size(self, text: str) -> Tuple[int, int]:
        left, top, right, bottom = self.image_font.getbbox(text)
        width = int(right - left)
        height = int(bottom - top)
        return width, height

    @property
    def variations(self) -> List[str]:
        try:
            return [v.decode() for v in self.image_font.get_variation_names()]
        except OSError:
            return []


def get_codepoints(path: Path) -> Set[int]:
    def gen() -> Generator[Iterable[int], None, None]:
        for font in tt_fonts(path):
            for subtable in font["cmap"].tables:  # type: ignore
                if subtable.isUnicode():  # type: ignore
                    yield subtable.cmap.keys()  # type: ignore

    empty_set: Set[int] = set()
    return empty_set.union(*gen())


def get_codepoints_cached(path: Path) -> Set[int]:
    # Cache codepoints, since it's slow to extract them
    hash = hashlib.md5(str(path).encode()).hexdigest()
    filename = f"{path.name}.{hash}.json"
    codepoints_path = get_cache_dir("fonts") / filename

    if codepoints_path.exists():
        try:
            with open(codepoints_path, "r") as f:
                return set(json.load(f))
        except Exception:
            pass

    print_log("Extracting supported codepoints...")
    codepoints = get_codepoints(path)

    print_log(f"Saving codepoints cache to: {codepoints_path}")
    with open(codepoints_path, "w") as f:
        json.dump(list(codepoints), f)

    return get_codepoints(path)


def tt_fonts(path: Path) -> Generator[TTFont, None, None]:
    try:
        with TTFont(path) as font:
            yield font
    except TTLibFileIsCollectionError:
        with TTCollection(path) as collection:
            for font in collection.fonts:  # type: ignore
                yield font


def load_font(path: Path, is_bitmap: bool, size: int):
    return Font(
        path=path,
        image_font=ImageFont.truetype(path, size),
        codepoints=get_codepoints_cached(path),
        is_bitmap=is_bitmap,
        size=size,
    )


def char_name(char: str):
    try:
        return unicodedata.name(char)
    except ValueError:
        return "NO NAME"


def dump_codepoints(path: Path):
    for codepoint in sorted(get_codepoints(path)):
        try:
            name = unicodedata.name(chr(codepoint))
        except ValueError:
            name = "???"

        print(f"{codepoint}\t{chr(codepoint)}\t{name}")


def make_group_by_font(
    fonts: List[Font],
    on_char_not_found: Callable[[str], None],
) -> Callable[[str], Generator[Tuple[str, Font], None, None]]:

    @lru_cache
    def get_font(char: str) -> Optional[Font]:
        for font in fonts:
            if ord(char) in font.codepoints:
                return font

    def group_by_font(text: str):
        """Split given text into chunks which can be rendered by the same font."""
        if not text:
            return

        buffer = ""
        font = None

        for char in text:
            char_font = get_font(char)
            if not char_font:
                on_char_not_found(char)
                continue

            if not font:
                font = char_font

            if font == char_font:
                buffer += char
            else:
                yield buffer, font
                font = char_font
                buffer = char

        if buffer and font:
            yield buffer, font

    return group_by_font
