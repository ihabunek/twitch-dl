import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Optional, Set, Tuple

from fontTools.ttLib import TTFont, TTLibFileIsCollectionError  # type: ignore
from fontTools.ttLib.ttCollection import TTCollection  # type: ignore
from PIL import ImageFont

# TODO:
# * ImageFont.truetype attempts to locate fonts on the system (lin/win/mac)


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

    def get_length(self, text: str) -> int:
        return math.ceil(self.image_font.getlength(text))

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


def get_codepoints(font: TTFont) -> Set[int]:
    return set().union(*(table.cmap.keys() for table in font["cmap"].tables))  # type: ignore


def extract_codepoints(path: Path) -> Set[int]:
    def gen() -> Generator[int, None, None]:
        for font in tt_fonts(path):
            for table in font["cmap"].tables:
                yield table.cmap.keys()

    return set().union(*gen())


def tt_fonts(path: Path) -> Generator[TTFont, None, None]:
    try:
        with TTFont(path) as font:
            yield font
    except TTLibFileIsCollectionError:
        with TTCollection(path) as collection:
            for font in collection.fonts:  # type: ignore
                yield font


def load_font(path: Path, is_bitmap: bool, size: int):
    image_font = ImageFont.truetype(path, size)

    return Font(
        path=path,
        image_font=image_font,
        codepoints=extract_codepoints(path),
        is_bitmap=is_bitmap,
        size=size,
    )


def char_name(char: str):
    try:
        return unicodedata.name(char)
    except ValueError:
        return "NO NAME"


def dump_codepoints(path: Path):
    for codepoint in sorted(extract_codepoints(path)):
        try:
            name = unicodedata.name(chr(codepoint))
        except ValueError:
            name = "???"

        print(f"{codepoint}\t{chr(codepoint)}\t{name}")


def get_font_for_char(fonts: List[Font], char: str) -> Optional[Font]:
    for font in fonts:
        if ord(char) in font.codepoints:
            return font
    return None


def group_by_font(text: str, fonts: List[Font]) -> Generator[Tuple[str, Font], None, None]:
    if not text:
        return

    buffer = ""
    font = None

    for char in text:
        char_font = get_font_for_char(fonts, char)
        if not char_font:
            print(f"Cannot render char: {char} {char_name(char)} {ord(char)}")
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
