from __future__ import annotations

from dataclasses import dataclass
import io
from contextlib import suppress
import re
from typing import Generator, Iterable, NamedTuple
from textual.color import Color
from textual.style import Style
from textual.content import Content, Span

from toad._stream_parser import (
    StreamParser,
    ParseResult,
    SeparatorToken,
    StreamRead,
    Token,
    MatchToken,
    PatternToken,
    Pattern,
    PatternCheck,
)

RE_ANSI = r"""
\x1b\[(?:\](.*?)\x1b\\)|  # OSC
\x1b\[(?:([(@-Z\\-_]|\[[0-?]*[ -/]*[@-~]))  # SGR
"""

r"""
For Control Sequence Introducer, or CSI, commands, the ESC\
    [ (written as \e[, \x1b[ or \033[ in several programming languages
      is followed by any number (including none) of "parameter bytes"
      in the range 0x30–0x3F (ASCII 0–9:;<=>?), then by any number of
      "intermediate bytes" in the range 0x20–0x2F (ASCII space and !"#$%&'()*+,-./),
      then finally by a single "final byte" in the range 0x40–0x7E (ASCII @A–Z[\]^_`a–z{|}~).[16]: 5.4 
"""


class CSIPattern(Pattern):
    PARAMETER_BYTES = frozenset([chr(codepoint) for codepoint in range(0x30, 0x3F + 1)])
    INTERMEDIATE_BYTES = frozenset(
        [chr(codepoint) for codepoint in range(0x20, 0x2F + 1)]
    )
    FINAL_BYTE = frozenset([chr(codepoint) for codepoint in range(0x40, 0x7E + 1)])

    class Match(NamedTuple):
        parameter: str
        intermediate: str
        final: str

        @property
        def full(self) -> str:
            return f"\x1b[{self.parameter}{self.intermediate}{self.final}"

    def check(self) -> PatternCheck:
        parameter = io.StringIO()
        intermediate = io.StringIO()

        parameter_bytes = self.PARAMETER_BYTES

        if (yield) != "[":
            return False

        while (character := (yield)) in parameter_bytes:
            parameter.write(character)
        intermediate_bytes = self.INTERMEDIATE_BYTES

        if character in self.FINAL_BYTE:
            return self.Match(parameter.getvalue(), "", character)

        intermediate.write(character)
        while True:
            intermediate.write(character)
            if (character := (yield)) not in intermediate_bytes:
                break

        final_byte = character
        if final_byte not in self.FINAL_BYTE:
            return False

        return self.Match(parameter.getvalue(), intermediate.getvalue(), final_byte)


class OSCPattern(Pattern):
    class Match(NamedTuple):
        code: str

    def check(self) -> PatternCheck:
        if (yield) != "]":
            return False
        return self.Match("]")


# class _AnsiToken(NamedTuple):
#     """Result of ansi tokenized string."""

#     plain: str = ""
#     sgr: Optional[str] = ""
#     osc: Optional[str] = ""


# def _ansi_tokenize(ansi_text: str) -> Iterable[_AnsiToken]:
#     """Tokenize a string in to plain text and ANSI codes.

#     Args:
#         ansi_text (str): A String containing ANSI codes.

#     Yields:
#         AnsiToken: A named tuple of (plain, sgr, osc)
#     """

#     position = 0
#     sgr: Optional[str]
#     osc: Optional[str]
#     for match in re_ansi.finditer(ansi_text):
#         start, end = match.span(0)
#         osc, sgr = match.groups()
#         if start > position:
#             yield _AnsiToken(ansi_text[position:start])
#         if sgr:
#             if sgr == "(":
#                 position = end + 1
#                 continue
#             if sgr.endswith("m"):
#                 yield _AnsiToken("", sgr[1:-1], osc)
#         else:
#             yield _AnsiToken("", sgr, osc)
#         position = end
#     if position < len(ansi_text):
#         yield _AnsiToken(ansi_text[position:])


SGR_STYLE_MAP = {
    1: "bold",
    2: "dim",
    3: "italic",
    4: "underline",
    5: "blink",
    6: "blink2",
    7: "reverse",
    8: "conceal",
    9: "strike",
    21: "underline2",
    22: "not dim not bold",
    23: "not italic",
    24: "not underline",
    25: "not blink",
    26: "not blink2",
    27: "not reverse",
    28: "not conceal",
    29: "not strike",
    30: "ansi_black",
    31: "ansi_red",
    32: "ansi_green",
    33: "ansi_yellow",
    34: "ansi_blue",
    35: "ansi_magenta",
    36: "ansi_cyan",
    37: "ansi_white",
    39: "default",
    40: "on ansi_black",
    41: "on ansi_red",
    42: "on ansi_green",
    43: "on ansi_yellow",
    44: "on ansi_blue",
    45: "on ansi_magenta",
    46: "on ansi_cyan",
    47: "on ansi_white",
    49: "on default",
    51: "frame",
    52: "encircle",
    53: "overline",
    54: "not frame not encircle",
    55: "not overline",
    90: "ansi_bright_black",
    91: "ansi_bright_red",
    92: "ansi_bright_green",
    93: "ansi_bright_yellow",
    94: "ansi_bright_blue",
    95: "ansi_bright_magenta",
    96: "ansi_bright_cyan",
    97: "ansi_bright_white",
    100: "on ansi_bright_black",
    101: "on ansi_bright_red",
    102: "on ansi_bright_green",
    103: "on ansi_bright_yellow",
    104: "on ansi_bright_blue",
    105: "on ansi_bright_magenta",
    106: "on ansi_bright_cyan",
    107: "on ansi_bright_white",
}


@dataclass
class ANSIToken:
    text: str

    def __str__(self) -> str:
        return self.text


class Separator(ANSIToken):
    pass


@dataclass
class CSI(ANSIToken):
    pass


@dataclass
class OSC(ANSIToken):
    pass


class ANSIParser(StreamParser):
    def parse(self) -> Generator[StreamRead | Token | ANSIToken, Token, None]:
        NEW_LINE = "\n"
        CARRIAGE_RETURN = "\r"
        ESCAPE = "\x1b"

        while True:
            token = yield self.read_until(NEW_LINE, CARRIAGE_RETURN, ESCAPE)

            if isinstance(token, SeparatorToken):
                if token.text == ESCAPE:
                    token = yield self.read_patterns(
                        "\x1b", csi=CSIPattern(), osc=OSCPattern()
                    )

                    if isinstance(token, PatternToken):
                        value = token.value

                        if isinstance(value, CSIPattern.Match):
                            yield CSI(value.full)

                        elif isinstance(value, OSCPattern.Match):
                            osc_data: list[str] = []
                            while True:
                                token = yield self.read_until("\x1b", "\0x7")
                                if isinstance(token, SeparatorToken):
                                    if token.text == ESCAPE:
                                        yield self.read(1)
                                    break
                                osc_data.append(token.text)

                            yield OSC("".join(osc_data))
                            continue
                else:
                    yield Separator(token.text)
                continue

            yield ANSIToken(token.text)


EMPTY_LINE = Content()


ANSI_COLORS = [
    "ansi_black",
    "ansi_red",
    "ansi_green",
    "ansi_yellow",
    "ansi_blue",
    "ansi_magenta",
    "ansi_cyan",
    "ansi_white",
    "ansi_bright_black",
    "ansi_bright_red",
    "ansi_bright_green",
    "ansi_bright_yellow",
    "ansi_bright_blue",
    "ansi_bright_magenta",
    "ansi_bright_cyan",
    "ansi_bright_white",
]


class ANSIStream:
    def __init__(self) -> None:
        self.parser = ANSIParser()
        self.cursor_x = 0
        self.cursor_y = 0
        self.line_start = 0
        self.lines: list[list[Content]] = []
        self.style = Style()

    def __rich__(self) -> Content:
        return Content("\n").join(line for line in self)

    @classmethod
    def parse_sgr(cls, sgr: str, style: Style) -> Style:
        codes = [
            min(255, int(_code) if _code else 0)
            for _code in sgr.split(";")
            if _code.isdigit() or _code == ""
        ]
        iter_codes = iter(codes)
        for code in iter_codes:
            if code == 0:
                # reset
                style = Style.null()
            elif code in SGR_STYLE_MAP:
                # styles
                style += Style.parse(SGR_STYLE_MAP[code])
            elif code == 38:
                #  Foreground
                with suppress(StopIteration):
                    color_type = next(iter_codes)
                    if color_type == 5:
                        style += Style.parse(ANSI_COLORS[next(iter_codes)])
                    elif color_type == 2:
                        style += Style(
                            foreground=Color(
                                next(iter_codes),
                                next(iter_codes),
                                next(iter_codes),
                            )
                        )

            elif code == 48:
                # Background
                with suppress(StopIteration):
                    color_type = next(iter_codes)
                    if color_type == 5:
                        style += Style.parse("on " + ANSI_COLORS[next(iter_codes)])
                    elif color_type == 2:
                        style += Style(
                            background=Color(
                                next(iter_codes),
                                next(iter_codes),
                                next(iter_codes),
                            )
                        )
        return style

    def feed(self, text: str) -> None:
        for token in self.parser.feed(text):
            self.on_token(token)

    def on_token(self, token: ANSIToken) -> None:
        if isinstance(token, Separator):
            if token.text == "\n":
                self.cursor_x = 0
                self.cursor_y += 1

        elif isinstance(token, OSC):
            osc = token.text
            osc_parameters = osc.split(";")
            if osc_parameters:
                if osc_parameters[0] == "8":
                    link = osc_parameters[-1]
                    self.style += Style(link=link or None)

        elif isinstance(token, CSI):
            if token.text.endswith("m"):
                self.style = self.parse_sgr(token.text[2:-1], self.style)

        else:
            while self.cursor_y >= len(self.lines):
                self.lines.append([Content()])
            line = self.lines[self.cursor_y]
            if self.style:
                line.append(Content.styled(str(token), self.style))
            else:
                line.append(Content(str(token)))

    def __iter__(self) -> Iterable[Content]:
        for line_no in range(0, len(self.lines)):
            yield self.get_line(line_no + self.line_start).simplify()

    def get_line(self, y: int) -> Content:
        line = self.lines[y]
        if len(line) != 1:
            line[:] = [Content.assemble(*line)]
        return line[0]


if __name__ == "__main__":
    from textual.content import Content

    from rich import print

    content = Content.from_markup(
        "Hello\n[bold magenta]World[/]!\n[ansi_red]This is [i]red\nVisit [link='https://www.willmcgugan.com']My blog[/]."
    )
    # content = Content.from_markup("[link='https://www.willmcgugan.com']My blog[/].")
    ansi_text = "".join(
        segment.style.render(segment.text) if segment.style else segment.text
        for segment in content.render_segments()
    )
    print(content)
    print(repr(ansi_text))

    parser = ANSIStream()
    from itertools import batched

    for batch in batched(ansi_text, 2):
        token = parser.feed("".join(batch))

    print(parser.lines)
    print(parser)

    print(parser.lines)
    # for line in parser.lines:
    #     print(line)
