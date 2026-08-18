"""html2text: Turn HTML into equivalent Markdown-structured text."""

import html.entities
import html.parser
import string
import urllib.parse as urlparse
from textwrap import wrap
from typing import Dict, List, Optional, Tuple, Union



class AnchorElement:
    __slots__ = ["attrs", "count", "outcount"]

    def __init__(self, attrs: Dict[str, Optional[str]], count: int, outcount: int):
        self.attrs = attrs
        self.count = count
        self.outcount = outcount


class ListElement:
    __slots__ = ["name", "num"]

    def __init__(self, name: str, num: int):
        self.name = name
        self.num = num

# TODO:
# Support decoded entities with UNIFIABLE.

import re

# Use Unicode characters instead of their ascii pseudo-replacements
UNICODE_SNOB = False

# Marker to use for marking tables for padding post processing
TABLE_MARKER_FOR_PAD = "special_marker_for_table_padding"
# Escape all special characters.  Output is less readable, but avoids
# corner case formatting issues.
ESCAPE_SNOB = False

# Put the links after each paragraph instead of at the end.
LINKS_EACH_PARAGRAPH = False

# Wrap long lines at position. 0 for no wrapping.
BODY_WIDTH = 78

# Don't show internal links (href="#local-anchor") -- corresponding link
# targets won't be visible in the plain text file anyway.
SKIP_INTERNAL_LINKS = True

# Use inline, rather than reference, formatting for images and links
INLINE_LINKS = True

# Protect links from line breaks surrounding them with angle brackets (in
# addition to their square brackets)
PROTECT_LINKS = False
# WRAP_LINKS = True
WRAP_LINKS = True

# Wrap list items.
WRAP_LIST_ITEMS = False

# Wrap tables
WRAP_TABLES = False

# Number of pixels Google indents nested lists
GOOGLE_LIST_INDENT = 36

# Values Google and others may use to indicate bold text
BOLD_TEXT_STYLE_VALUES = ("bold", "700", "800", "900")

IGNORE_ANCHORS = False
IGNORE_MAILTO_LINKS = False
IGNORE_IMAGES = False
IMAGES_AS_HTML = False
IMAGES_TO_ALT = False
IMAGES_WITH_SIZE = False
IGNORE_EMPHASIS = False
MARK_CODE = False
BACKQUOTE_CODE_STYLE = False
DECODE_ERRORS = "strict"
DEFAULT_IMAGE_ALT = ""
PAD_TABLES = False

# Convert links with same href and text to <href> format
# if they are absolute links
USE_AUTOMATIC_LINKS = True

# For checking space-only lines on line 771
RE_SPACE = re.compile(r"\s\+")

RE_ORDERED_LIST_MATCHER = re.compile(r"\d+\.\s")
RE_UNORDERED_LIST_MATCHER = re.compile(r"[-\*\+]\s")
RE_MD_CHARS_MATCHER = re.compile(r"([\\\[\]\(\)])")
RE_MD_CHARS_MATCHER_ALL = re.compile(r"([`\*_{}\[\]\(\)#!])")

# to find links in the text
RE_LINK = re.compile(r"(\[.*?\] ?\(.*?\))|(\[.*?\]:.*?)")

# to find table separators
RE_TABLE = re.compile(r" \| ")

RE_MD_DOT_MATCHER = re.compile(
    r"""
    ^             # start of line
    (\s*\d+)      # optional whitespace and a number
    (\.)          # dot
    (?=\s)        # lookahead assert whitespace
    """,
    re.MULTILINE | re.VERBOSE,
)
RE_MD_PLUS_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    (\+)
    (?=\s)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
RE_MD_DASH_MATCHER = re.compile(
    r"""
    ^
    (\s*)
    (-)
    (?=\s|\-)     # followed by whitespace (bullet list, or spaced out hr)
                  # or another dash (header or hr)
    """,
    flags=re.MULTILINE | re.VERBOSE,
)
RE_SLASH_CHARS = r"\`*_{}[]()#+-.!"
RE_MD_BACKSLASH_MATCHER = re.compile(
    r"""
    (\\)          # match one slash
    (?=[%s])      # followed by a char that requires escaping
    """
    % re.escape(RE_SLASH_CHARS),
    flags=re.VERBOSE,
)

UNIFIABLE = {
    "rsquo": "'",
    "lsquo": "'",
    "rdquo": '"',
    "ldquo": '"',
    "copy": "(C)",
    "mdash": "--",
    "nbsp": " ",
    "rarr": "->",
    "larr": "<-",
    "middot": "*",
    "ndash": "-",
    "oelig": "oe",
    "aelig": "ae",
    "agrave": "a",
    "aacute": "a",
    "acirc": "a",
    "atilde": "a",
    "auml": "a",
    "aring": "a",
    "egrave": "e",
    "eacute": "e",
    "ecirc": "e",
    "euml": "e",
    "igrave": "i",
    "iacute": "i",
    "icirc": "i",
    "iuml": "i",
    "ograve": "o",
    "oacute": "o",
    "ocirc": "o",
    "otilde": "o",
    "ouml": "o",
    "ugrave": "u",
    "uacute": "u",
    "ucirc": "u",
    "uuml": "u",
    "lrm": "",
    "rlm": "",
}

# Format tables in HTML rather than Markdown syntax
BYPASS_TABLES = False
# Ignore table-related tags (table, th, td, tr) while keeping rows
IGNORE_TABLES = False


# Use a single line break after a block element rather than two line breaks.
# NOTE: Requires body width setting to be 0.
SINGLE_LINE_BREAK = False


# Use double quotation marks when converting the <q> tag.
OPEN_QUOTE = '"'
CLOSE_QUOTE = '"'

# Include the <sup> and <sub> tags
INCLUDE_SUP_SUB = False

class OutCallback:
    def __call__(self, s: str) -> None: ...


import html.entities


unifiable_n = {
    html.entities.name2codepoint[k]: v
    for k, v in UNIFIABLE.items()
    if k != "nbsp"
}

# https://html.spec.whatwg.org/multipage/parsing.html#character-reference-code
control_character_replacements = {
    0x80: 0x20AC,  # EURO SIGN (€)
    0x82: 0x201A,  # SINGLE LOW-9 QUOTATION MARK (‚)
    0x83: 0x0192,  # LATIN SMALL LETTER F WITH HOOK (ƒ)
    0x84: 0x201E,  # DOUBLE LOW-9 QUOTATION MARK („)
    0x85: 0x2026,  # HORIZONTAL ELLIPSIS (…)
    0x86: 0x2020,  # DAGGER (†)
    0x87: 0x2021,  # DOUBLE DAGGER (‡)
    0x88: 0x02C6,  # MODIFIER LETTER CIRCUMFLEX ACCENT (ˆ)
    0x89: 0x2030,  # PER MILLE SIGN (‰)
    0x8A: 0x0160,  # LATIN CAPITAL LETTER S WITH CARON (Š)
    0x8B: 0x2039,  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK (‹)
    0x8C: 0x0152,  # LATIN CAPITAL LIGATURE OE (Œ)
    0x8E: 0x017D,  # LATIN CAPITAL LETTER Z WITH CARON (Ž)
    0x91: 0x2018,  # LEFT SINGLE QUOTATION MARK (‘)
    0x92: 0x2019,  # RIGHT SINGLE QUOTATION MARK (’)
    0x93: 0x201C,  # LEFT DOUBLE QUOTATION MARK (“)
    0x94: 0x201D,  # RIGHT DOUBLE QUOTATION MARK (”)
    0x95: 0x2022,  # BULLET (•)
    0x96: 0x2013,  # EN DASH (–)
    0x97: 0x2014,  # EM DASH (—)
    0x98: 0x02DC,  # SMALL TILDE (˜)
    0x99: 0x2122,  # TRADE MARK SIGN (™)
    0x9A: 0x0161,  # LATIN SMALL LETTER S WITH CARON (š)
    0x9B: 0x203A,  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK (›)
    0x9C: 0x0153,  # LATIN SMALL LIGATURE OE (œ)
    0x9E: 0x017E,  # LATIN SMALL LETTER Z WITH CARON (ž)
    0x9F: 0x0178,  # LATIN CAPITAL LETTER Y WITH DIAERESIS (Ÿ)
}


def hn(tag: str) -> int:
    if tag[0] == "h" and len(tag) == 2:
        n = tag[1]
        if "0" < n <= "9":
            return int(n)
    return 0


def dumb_property_dict(style: str) -> Dict[str, str]:
    """
    :returns: A hash of css attributes
    """
    return {
        x.strip().lower(): y.strip().lower()
        for x, y in [z.split(":", 1) for z in style.split(";") if ":" in z]
    }


def dumb_css_parser(data: str) -> Dict[str, Dict[str, str]]:
    """
    :type data: str

    :returns: A hash of css selectors, each of which contains a hash of
    css attributes.
    :rtype: dict
    """
    # remove @import sentences
    data += ";"
    importIndex = data.find("@import")
    while importIndex != -1:
        data = data[0:importIndex] + data[data.find(";", importIndex) + 1 :]
        importIndex = data.find("@import")

    # parse the css. reverted from dictionary comprehension in order to
    # support older pythons
    pairs = [x.split("{") for x in data.split("}") if "{" in x.strip()]
    try:
        elements = {a.strip(): dumb_property_dict(b) for a, b in pairs}
    except ValueError:
        elements = {}  # not that important

    return elements


def element_style(
    attrs: Dict[str, Optional[str]],
    style_def: Dict[str, Dict[str, str]],
    parent_style: Dict[str, str],
) -> Dict[str, str]:
    """
    :type attrs: dict
    :type style_def: dict
    :type style_def: dict

    :returns: A hash of the 'final' style attributes of the element
    :rtype: dict
    """
    style = parent_style.copy()
    if "class" in attrs:
        assert attrs["class"] is not None
        for css_class in attrs["class"].split():
            css_style = style_def.get("." + css_class, {})
            style.update(css_style)
    if "style" in attrs:
        assert attrs["style"] is not None
        immediate_style = dumb_property_dict(attrs["style"])
        style.update(immediate_style)

    return style


def google_list_style(style: Dict[str, str]) -> str:
    """
    Finds out whether this is an ordered or unordered list

    :type style: dict

    :rtype: str
    """
    if "list-style-type" in style:
        list_style = style["list-style-type"]
        if list_style in ["disc", "circle", "square", "none"]:
            return "ul"

    return "ol"


def google_has_height(style: Dict[str, str]) -> bool:
    """
    Check if the style of the element has the 'height' attribute
    explicitly defined

    :type style: dict

    :rtype: bool
    """
    return "height" in style


def google_text_emphasis(style: Dict[str, str]) -> List[str]:
    """
    :type style: dict

    :returns: A list of all emphasis modifiers of the element
    :rtype: list
    """
    emphasis = []
    if "text-decoration" in style:
        emphasis.append(style["text-decoration"])
    if "font-style" in style:
        emphasis.append(style["font-style"])
    if "font-weight" in style:
        emphasis.append(style["font-weight"])

    return emphasis


def google_fixed_width_font(style: Dict[str, str]) -> bool:
    """
    Check if the css of the current element defines a fixed width font

    :type style: dict

    :rtype: bool
    """
    font_family = ""
    if "font-family" in style:
        font_family = style["font-family"]
    return "courier new" == font_family or "consolas" == font_family


def list_numbering_start(attrs: Dict[str, Optional[str]]) -> int:
    """
    Extract numbering from list element attributes

    :type attrs: dict

    :rtype: int or None
    """
    if "start" in attrs:
        assert attrs["start"] is not None
        try:
            return int(attrs["start"]) - 1
        except ValueError:
            pass

    return 0


def skipwrap(
    para: str, wrap_links: bool, wrap_list_items: bool, wrap_tables: bool
) -> bool:
    # If it appears to contain a link
    # don't wrap
    if not wrap_links and RE_LINK.search(para):
        return True
    # If the text begins with four spaces or one tab, it's a code block;
    # don't wrap
    if para[0:4] == "    " or para[0] == "\t":
        return True

    # If the text begins with only two "--", possibly preceded by
    # whitespace, that's an emdash; so wrap.
    stripped = para.lstrip()
    if stripped[0:2] == "--" and len(stripped) > 2 and stripped[2] != "-":
        return False

    # I'm not sure what this is for; I thought it was to detect lists,
    # but there's a <br>-inside-<span> case in one of the tests that
    # also depends upon it.
    if stripped[0:1] in ("-", "*") and not stripped[0:2] == "**":
        return not wrap_list_items

    # If text contains a pipe character it is likely a table
    if not wrap_tables and RE_TABLE.search(para):
        return True

    # If the text begins with a single -, *, or +, followed by a space,
    # or an integer, followed by a ., followed by a space (in either
    # case optionally proceeded by whitespace), it's a list; don't wrap.
    return bool(
        RE_ORDERED_LIST_MATCHER.match(stripped)
        or RE_UNORDERED_LIST_MATCHER.match(stripped)
    )


def escape_md(text: str) -> str:
    """
    Escapes markdown-sensitive characters within other markdown
    constructs.
    """
    return RE_MD_CHARS_MATCHER.sub(r"\\\1", text)


def escape_md_section(text: str, snob: bool = False) -> str:
    """
    Escapes markdown-sensitive characters across whole document sections.
    """
    text = RE_MD_BACKSLASH_MATCHER.sub(r"\\\1", text)

    if snob:
        text = RE_MD_CHARS_MATCHER_ALL.sub(r"\\\1", text)

    text = RE_MD_DOT_MATCHER.sub(r"\1\\\2", text)
    text = RE_MD_PLUS_MATCHER.sub(r"\1\\\2", text)
    text = RE_MD_DASH_MATCHER.sub(r"\1\\\2", text)

    return text


def reformat_table(lines: List[str], right_margin: int) -> List[str]:
    """
    Given the lines of a table
    padds the cells and returns the new lines
    """
    # find the maximum width of the columns
    max_width = [len(x.rstrip()) + right_margin for x in lines[0].split("|")]
    max_cols = len(max_width)
    for line in lines:
        cols = [x.rstrip() for x in line.split("|")]
        num_cols = len(cols)

        # don't drop any data if colspan attributes result in unequal lengths
        if num_cols < max_cols:
            cols += [""] * (max_cols - num_cols)
        elif max_cols < num_cols:
            max_width += [len(x) + right_margin for x in cols[-(num_cols - max_cols) :]]
            max_cols = num_cols

        max_width = [
            max(len(x) + right_margin, old_len) for x, old_len in zip(cols, max_width)
        ]

    # reformat
    new_lines = []
    for line in lines:
        cols = [x.rstrip() for x in line.split("|")]
        if set(line.strip()) == set("-|"):
            filler = "-"
            new_cols = [
                x.rstrip() + (filler * (M - len(x.rstrip())))
                for x, M in zip(cols, max_width)
            ]
            new_lines.append("|-" + "|".join(new_cols) + "|")
        else:
            filler = " "
            new_cols = [
                x.rstrip() + (filler * (M - len(x.rstrip())))
                for x, M in zip(cols, max_width)
            ]
            new_lines.append("| " + "|".join(new_cols) + "|")
    return new_lines


def pad_tables_in_text(text: str, right_margin: int = 1) -> str:
    """
    Provide padding for tables in the text
    """
    lines = text.split("\n")
    table_buffer = []  # type: List[str]
    table_started = False
    new_lines = []
    for line in lines:
        # Toggle table started
        if TABLE_MARKER_FOR_PAD in line:
            table_started = not table_started
            if not table_started:
                table = reformat_table(table_buffer, right_margin)
                new_lines.extend(table)
                table_buffer = []
                new_lines.append("")
            continue
        # Process lines
        if table_started:
            table_buffer.append(line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines)



class HTML2Text(html.parser.HTMLParser):
    def __init__(
        self,
        out: Optional[OutCallback] = None,
        baseurl: str = "",
        bodywidth: int = BODY_WIDTH,
    ) -> None:
        """
        Input parameters:
            out: possible custom replacement for self.outtextf (which
                 appends lines of text).
            baseurl: base URL of the document we process
        """
        super().__init__(convert_charrefs=False)

        # Config options
        self.split_next_td = False
        self.td_count = 0
        self.table_start = False
        self.unicode_snob = UNICODE_SNOB  # covered in cli
        self.escape_snob = ESCAPE_SNOB  # covered in cli
        self.links_each_paragraph = LINKS_EACH_PARAGRAPH
        self.body_width = bodywidth  # covered in cli
        self.skip_internal_links = SKIP_INTERNAL_LINKS  # covered in cli
        self.inline_links = INLINE_LINKS  # covered in cli
        self.protect_links = PROTECT_LINKS  # covered in cli
        self.google_list_indent = GOOGLE_LIST_INDENT  # covered in cli
        self.ignore_links = IGNORE_ANCHORS  # covered in cli
        self.ignore_mailto_links = IGNORE_MAILTO_LINKS  # covered in cli
        self.ignore_images = IGNORE_IMAGES  # covered in cli
        self.images_as_html = IMAGES_AS_HTML  # covered in cli
        self.images_to_alt = IMAGES_TO_ALT  # covered in cli
        self.images_with_size = IMAGES_WITH_SIZE  # covered in cli
        self.ignore_emphasis = IGNORE_EMPHASIS  # covered in cli
        self.bypass_tables = BYPASS_TABLES  # covered in cli
        self.ignore_tables = IGNORE_TABLES  # covered in cli
        self.google_doc = False  # covered in cli
        self.ul_item_mark = "*"  # covered in cli
        self.emphasis_mark = "_"  # covered in cli
        self.strong_mark = "**"
        self.single_line_break = SINGLE_LINE_BREAK  # covered in cli
        self.use_automatic_links = USE_AUTOMATIC_LINKS  # covered in cli
        self.hide_strikethrough = False  # covered in cli
        self.mark_code = MARK_CODE
        self.backquote_code_style = BACKQUOTE_CODE_STYLE
        self.wrap_list_items = WRAP_LIST_ITEMS  # covered in cli
        self.wrap_links = WRAP_LINKS  # covered in cli
        self.wrap_tables = WRAP_TABLES
        self.pad_tables = PAD_TABLES  # covered in cli
        self.default_image_alt = DEFAULT_IMAGE_ALT  # covered in cli
        self.tag_callback = None
        self.open_quote = OPEN_QUOTE  # covered in cli
        self.close_quote = CLOSE_QUOTE  # covered in cli
        self.include_sup_sub = INCLUDE_SUP_SUB  # covered in cli

        if out is None:
            self.out = self.outtextf
        else:
            self.out = out

        # empty list to store output characters before they are "joined"
        self.outtextlist: List[str] = []

        self.quiet = 0
        self.p_p = 0  # number of newline character to print before next output
        self.outcount = 0
        self.start = True
        self.space = False
        self.a: List[AnchorElement] = []
        self.astack: List[Optional[Dict[str, Optional[str]]]] = []
        self.maybe_automatic_link: Optional[str] = None
        self.empty_link = False
        self.absolute_url_matcher = re.compile(r"^[a-zA-Z+]+://")
        self.acount = 0
        self.list: List[ListElement] = []
        self.blockquote = 0
        self.pre = False
        self.startpre = False
        self.pre_indent = ""
        self.list_code_indent = ""
        self.code = False
        self.quote = False
        self.br_toggle = ""
        self.lastWasNL = False
        self.lastWasList = False
        self.style = 0
        self.style_def: Dict[str, Dict[str, str]] = {}
        self.tag_stack: List[Tuple[str, Dict[str, Optional[str]], Dict[str, str]]] = []
        self.emphasis = 0
        self.drop_white_space = 0
        self.inheader = False
        # Current abbreviation definition
        self.abbr_title: Optional[str] = None
        # Last inner HTML (for abbr being defined)
        self.abbr_data: Optional[str] = None
        # Stack of abbreviations to write later
        self.abbr_list: Dict[str, str] = {}
        self.baseurl = baseurl
        self.stressed = False
        self.preceding_stressed = False
        self.preceding_data = ""
        self.current_tag = ""

        UNIFIABLE["nbsp"] = "&nbsp_place_holder;"

    def feed(self, data: str) -> None:
        data = data.replace("</' + 'script>", "</ignore>")
        super().feed(data)

    def handle(self, data: str) -> str:
        self.start = True
        self.feed(data)
        self.feed("")
        markdown = self.optwrap(self.finish())
        if self.pad_tables:
            return pad_tables_in_text(markdown)
        else:
            return markdown

    def outtextf(self, s: str) -> None:
        self.outtextlist.append(s)
        if s:
            self.lastWasNL = s[-1] == "\n"

    def finish(self) -> str:
        self.close()

        self.pbr()
        self.o("", force="end")

        outtext = "".join(self.outtextlist)

        if self.unicode_snob:
            nbsp = html.entities.html5["nbsp;"]
        else:
            nbsp = " "
        outtext = outtext.replace("&nbsp_place_holder;", nbsp)

        # Clear self.outtextlist to avoid memory leak of its content to
        # the next handling.
        self.outtextlist = []

        return outtext

    def handle_charref(self, c: str) -> None:
        self.handle_data(self.charref(c), True)

    def handle_entityref(self, c: str) -> None:
        ref = self.entityref(c)

        # ref may be an empty string (e.g. for &lrm;/&rlm; markers that should
        # not contribute to the final output).
        # self.handle_data cannot handle a zero-length string right after a
        # stressed tag or mid-text within a stressed tag (text get split and
        # self.stressed/self.preceding_stressed gets switched after the first
        # part of that text).
        if ref:
            self.handle_data(ref, True)

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        self.handle_tag(tag, dict(attrs), start=True)

    def handle_endtag(self, tag: str) -> None:
        self.handle_tag(tag, {}, start=False)

    def previousIndex(self, attrs: Dict[str, Optional[str]]) -> Optional[int]:
        """
        :type attrs: dict

        :returns: The index of certain set of attributes (of a link) in the
        self.a list. If the set of attributes is not found, returns None
        :rtype: int
        """
        if "href" not in attrs:
            return None

        match = False
        for i, a in enumerate(self.a):
            if "href" in a.attrs and a.attrs["href"] == attrs["href"]:
                if "title" in a.attrs or "title" in attrs:
                    if (
                        "title" in a.attrs
                        and "title" in attrs
                        and a.attrs["title"] == attrs["title"]
                    ):
                        match = True
                else:
                    match = True

            if match:
                return i
        return None

    def handle_emphasis(
        self, start: bool, tag_style: Dict[str, str], parent_style: Dict[str, str]
    ) -> None:
        """
        Handles various text emphases
        """
        tag_emphasis = google_text_emphasis(tag_style)
        parent_emphasis = google_text_emphasis(parent_style)

        # handle Google's text emphasis
        strikethrough = "line-through" in tag_emphasis and self.hide_strikethrough

        # google and others may mark a font's weight as `bold` or `700`
        bold = False
        for bold_marker in BOLD_TEXT_STYLE_VALUES:
            bold = bold_marker in tag_emphasis and bold_marker not in parent_emphasis
            if bold:
                break

        italic = "italic" in tag_emphasis and "italic" not in parent_emphasis
        fixed = (
            google_fixed_width_font(tag_style)
            and not google_fixed_width_font(parent_style)
            and not self.pre
        )

        if start:
            # crossed-out text must be handled before other attributes
            # in order not to output qualifiers unnecessarily
            if bold or italic or fixed:
                self.emphasis += 1
            if strikethrough:
                self.quiet += 1
            if italic:
                self.o(self.emphasis_mark)
                self.drop_white_space += 1
            if bold:
                self.o(self.strong_mark)
                self.drop_white_space += 1
            if fixed:
                self.o("`")
                self.drop_white_space += 1
                self.code = True
        else:
            if bold or italic or fixed:
                # there must not be whitespace before closing emphasis mark
                self.emphasis -= 1
                self.space = False
            if fixed:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_white_space -= 1
                else:
                    self.o("`")
                self.code = False
            if bold:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_white_space -= 1
                else:
                    self.o(self.strong_mark)
            if italic:
                if self.drop_white_space:
                    # empty emphasis, drop it
                    self.drop_white_space -= 1
                else:
                    self.o(self.emphasis_mark)
            # space is only allowed after *all* emphasis marks
            if (bold or italic) and not self.emphasis:
                self.o(" ")
            if strikethrough:
                self.quiet -= 1

    def handle_tag(
        self, tag: str, attrs: Dict[str, Optional[str]], start: bool
    ) -> None:
        self.current_tag = tag

        if self.tag_callback is not None:
            if self.tag_callback(self, tag, attrs, start) is True:
                return

        # first thing inside the anchor tag is another tag
        # that produces some output
        if (
            start
            and self.maybe_automatic_link is not None
            and tag not in ["p", "div", "style", "dl", "dt"]
            and (tag != "img" or self.ignore_images)
        ):
            self.o("[")
            self.maybe_automatic_link = None
            self.empty_link = False

        if self.google_doc:
            # the attrs parameter is empty for a closing tag. in addition, we
            # need the attributes of the parent nodes in order to get a
            # complete style description for the current element. we assume
            # that google docs export well formed html.
            parent_style: Dict[str, str] = {}
            if start:
                if self.tag_stack:
                    parent_style = self.tag_stack[-1][2]
                tag_style = element_style(attrs, self.style_def, parent_style)
                self.tag_stack.append((tag, attrs, tag_style))
            else:
                dummy, attrs, tag_style = (
                    self.tag_stack.pop() if self.tag_stack else (None, {}, {})
                )
                if self.tag_stack:
                    parent_style = self.tag_stack[-1][2]

        if hn(tag):
            # check if nh is inside of an 'a' tag (incorrect but found in the wild)
            if self.astack:
                if start:
                    self.inheader = True
                    # are inside link name, so only add '#' if it can appear before '['
                    if self.outtextlist and self.outtextlist[-1] == "[":
                        self.outtextlist.pop()
                        self.space = False
                        self.o(hn(tag) * "#" + " ")
                        self.o("[")
                else:
                    self.p_p = 0  # don't break up link name
                    self.inheader = False
                    return  # prevent redundant emphasis marks on headers
            else:
                self.p()
                if start:
                    self.inheader = True
                    self.o(hn(tag) * "#" + " ")
                else:
                    self.inheader = False
                    return  # prevent redundant emphasis marks on headers

        if tag in ["p", "div"]:
            if self.google_doc:
                if start and google_has_height(tag_style):
                    self.p()
                else:
                    self.soft_br()
            elif self.astack:
                pass
            elif self.split_next_td:
                pass
            else:
                self.p()

        if tag == "br" and start:
            if self.blockquote > 0:
                self.o("  \n> ")
            else:
                self.o("  \n")

        if tag == "hr" and start:
            self.p()
            self.o("* * *")
            self.p()

        if tag in ["head", "style", "script"]:
            if start:
                self.quiet += 1
            else:
                self.quiet -= 1

        if tag == "style":
            if start:
                self.style += 1
            else:
                self.style -= 1

        if tag in ["body"]:
            self.quiet = 0  # sites like 9rules.com never close <head>

        if tag == "blockquote":
            if start:
                self.p()
                self.o("> ", force=True)
                self.start = True
                self.blockquote += 1
            else:
                self.blockquote -= 1
                self.p()

        if tag in ["em", "i", "u"] and not self.ignore_emphasis:
            # Separate with a space if we immediately follow an alphanumeric
            # character, since otherwise Markdown won't render the emphasis
            # marks, and we'll be left with eg 'foo_bar_' visible.
            # (Don't add a space otherwise, though, since there isn't one in the
            # original HTML.)
            if (
                start
                and self.preceding_data
                and self.preceding_data[-1] not in string.whitespace
                and self.preceding_data[-1] not in string.punctuation
            ):
                emphasis = " " + self.emphasis_mark
                self.preceding_data += " "
            else:
                emphasis = self.emphasis_mark

            self.o(emphasis)
            if start:
                self.stressed = True

        if tag in ["strong", "b"] and not self.ignore_emphasis:
            # Separate with space if we immediately follow an * character, since
            # without it, Markdown won't render the resulting *** correctly.
            # (Don't add a space otherwise, though, since there isn't one in the
            # original HTML.)
            if (
                start
                and self.preceding_data
                # When `self.strong_mark` is set to empty, the next condition
                # will cause IndexError since it's trying to match the data
                # with the first character of the `self.strong_mark`.
                and len(self.strong_mark) > 0
                and self.preceding_data[-1] == self.strong_mark[0]
            ):
                strong = " " + self.strong_mark
                self.preceding_data += " "
            else:
                strong = self.strong_mark

            self.o(strong)
            if start:
                self.stressed = True

        if tag in ["del", "strike", "s"]:
            if start and self.preceding_data and self.preceding_data[-1] == "~":
                strike = " ~~"
                self.preceding_data += " "
            else:
                strike = "~~"

            self.o(strike)
            if start:
                self.stressed = True

        if self.google_doc:
            if not self.inheader:
                # handle some font attributes, but leave headers clean
                self.handle_emphasis(start, tag_style, parent_style)

        if tag in ["kbd", "code", "tt"] and not self.pre:
            self.o("`")  # TODO: `` `this` ``
            self.code = not self.code

        if tag == "abbr":
            if start:
                self.abbr_title = None
                self.abbr_data = ""
                if "title" in attrs:
                    self.abbr_title = attrs["title"]
            else:
                if self.abbr_title is not None:
                    assert self.abbr_data is not None
                    self.abbr_list[self.abbr_data] = self.abbr_title
                    self.abbr_title = None
                self.abbr_data = None

        if tag == "q":
            if not self.quote:
                self.o(self.open_quote)
            else:
                self.o(self.close_quote)
            self.quote = not self.quote

        def link_url(self: HTML2Text, link: str, title: str = "") -> None:
            url = urlparse.urljoin(self.baseurl, link)
            title = ' "{}"'.format(title) if title.strip() else ""
            self.o("]({url}{title})".format(url=escape_md(url), title=title))

        if tag == "a" and not self.ignore_links:
            if start:
                if (
                    "href" in attrs
                    and attrs["href"] is not None
                    and not (self.skip_internal_links and attrs["href"].startswith("#"))
                    and not (
                        self.ignore_mailto_links and attrs["href"].startswith("mailto:")
                    )
                ):
                    self.astack.append(attrs)
                    self.maybe_automatic_link = attrs["href"]
                    self.empty_link = True
                    if self.protect_links:
                        attrs["href"] = "<" + attrs["href"] + ">"
                else:
                    self.astack.append(None)
            else:
                if self.astack:
                    a = self.astack.pop()
                    if self.maybe_automatic_link and not self.empty_link:
                        self.maybe_automatic_link = None
                    elif a:
                        assert a["href"] is not None
                        if self.empty_link:
                            self.o("[")
                            self.empty_link = False
                            self.maybe_automatic_link = None
                        if self.inline_links:
                            self.p_p = 0
                            title = a.get("title") or ""
                            title = escape_md(title)
                            link_url(self, a["href"], title)
                        else:
                            i = self.previousIndex(a)
                            if i is not None:
                                a_props = self.a[i]
                            else:
                                self.acount += 1
                                a_props = AnchorElement(a, self.acount, self.outcount)
                                self.a.append(a_props)
                            self.o("][" + str(a_props.count) + "]")

        if tag == "img" and start and not self.ignore_images:
            if "src" in attrs and attrs["src"] is not None:
                if not self.images_to_alt:
                    attrs["href"] = attrs["src"]
                alt = attrs.get("alt") or self.default_image_alt

                # If we have images_with_size, write raw html including width,
                # height, and alt attributes
                if self.images_as_html or (
                    self.images_with_size and ("width" in attrs or "height" in attrs)
                ):
                    self.o("<img src='" + attrs["src"] + "' ")
                    if "width" in attrs and attrs["width"] is not None:
                        self.o("width='" + attrs["width"] + "' ")
                    if "height" in attrs and attrs["height"] is not None:
                        self.o("height='" + attrs["height"] + "' ")
                    if alt:
                        self.o("alt='" + alt + "' ")
                    self.o("/>")
                    return

                # If we have a link to create, output the start
                if self.maybe_automatic_link is not None:
                    href = self.maybe_automatic_link
                    if (
                        self.images_to_alt
                        and escape_md(alt) == href
                        and self.absolute_url_matcher.match(href)
                    ):
                        self.o("<" + escape_md(alt) + ">")
                        self.empty_link = False
                        return
                    else:
                        self.o("[")
                        self.maybe_automatic_link = None
                        self.empty_link = False

                # If we have images_to_alt, we discard the image itself,
                # considering only the alt text.
                if self.images_to_alt:
                    self.o(escape_md(alt))
                else:
                    self.o("![" + escape_md(alt) + "]")
                    if self.inline_links:
                        href = attrs.get("href") or ""
                        self.o(
                            "(" + escape_md(urlparse.urljoin(self.baseurl, href)) + ")"
                        )
                    else:
                        i = self.previousIndex(attrs)
                        if i is not None:
                            a_props = self.a[i]
                        else:
                            self.acount += 1
                            a_props = AnchorElement(attrs, self.acount, self.outcount)
                            self.a.append(a_props)
                        self.o("[" + str(a_props.count) + "]")

        if tag == "dl" and start:
            self.p()
        if tag == "dt" and not start:
            self.pbr()
        if tag == "dd" and start:
            self.o("    ")
        if tag == "dd" and not start:
            self.pbr()

        if tag in ["ol", "ul"]:
            # Google Docs create sub lists as top level lists
            if not self.list and not self.lastWasList:
                self.p()
            if start:
                if self.google_doc:
                    list_style = google_list_style(tag_style)
                else:
                    list_style = tag
                numbering_start = list_numbering_start(attrs)
                self.list.append(ListElement(list_style, numbering_start))
            else:
                if self.list:
                    self.list.pop()
                    if not self.google_doc and not self.list:
                        self.o("\n")
            self.lastWasList = True
        else:
            self.lastWasList = False

        if tag == "li":
            self.list_code_indent = ""
            self.pbr()
            if start:
                if self.list:
                    li = self.list[-1]
                else:
                    li = ListElement("ul", 0)
                if self.google_doc:
                    self.o("  " * self.google_nest_count(tag_style))
                else:
                    # Indent two spaces per list, except use three spaces for an
                    # unordered list inside an ordered list.
                    # https://spec.commonmark.org/0.28/#motivation
                    # TODO: line up <ol><li>s > 9 correctly.
                    parent_list = None
                    for list in self.list:
                        self.list_code_indent += "   " if parent_list == "ol" else "  "
                        parent_list = list.name
                    self.o(self.list_code_indent)

                if li.name == "ul":
                    self.list_code_indent += "  "
                    self.o(self.ul_item_mark + " ")
                elif li.name == "ol":
                    li.num += 1
                    self.list_code_indent += "   "
                    self.o(str(li.num) + ". ")
                self.start = True

        if tag in ["table", "tr", "td", "th"]:
            if self.ignore_tables:
                if tag == "tr":
                    if start:
                        pass
                    else:
                        self.soft_br()
                else:
                    pass

            elif self.bypass_tables:
                if start:
                    self.soft_br()
                if tag in ["td", "th"]:
                    if start:
                        self.o("<{}>\n\n".format(tag))
                    else:
                        self.o("\n</{}>".format(tag))
                else:
                    if start:
                        self.o("<{}>".format(tag))
                    else:
                        self.o("</{}>".format(tag))

            else:
                if tag == "table":
                    if start:
                        self.table_start = True
                        if self.pad_tables:
                            self.o("<" + TABLE_MARKER_FOR_PAD + ">")
                            self.o("  \n")
                    else:
                        if self.pad_tables:
                            # add break in case the table is empty or its 1 row table
                            self.soft_br()
                            self.o("</" + TABLE_MARKER_FOR_PAD + ">")
                            self.o("  \n")
                if tag in ["td", "th"] and start:
                    if self.split_next_td:
                        self.o("| ")
                    self.split_next_td = True

                if tag == "tr" and start:
                    self.td_count = 0
                if tag == "tr" and not start:
                    self.split_next_td = False
                    self.soft_br()
                if tag == "tr" and not start and self.table_start:
                    # Underline table header
                    self.o("|".join(["---"] * self.td_count))
                    self.soft_br()
                    self.table_start = False
                if tag in ["td", "th"] and start:
                    self.td_count += 1

        if tag == "pre":
            if start:
                self.startpre = True
                self.pre = True
                self.pre_indent = ""
            else:
                self.pre = False
                if self.backquote_code_style:
                    self.out("\n" + self.pre_indent + "```")
                if self.mark_code:
                    self.out("\n[/code]")
            self.p()

        if tag in ["sup", "sub"] and self.include_sup_sub:
            if start:
                self.o("<{}>".format(tag))
            else:
                self.o("</{}>".format(tag))

    # TODO: Add docstring for these one letter functions
    def pbr(self) -> None:
        "Pretty print has a line break"
        if self.p_p == 0:
            self.p_p = 1

    def p(self) -> None:
        "Set pretty print to 1 or 2 lines"
        self.p_p = 1 if self.single_line_break else 2

    def soft_br(self) -> None:
        "Soft breaks"
        self.pbr()
        self.br_toggle = "  "

    def o(
        self, data: str, puredata: bool = False, force: Union[bool, str] = False
    ) -> None:
        """
        Deal with indentation and whitespace
        """
        if self.abbr_data is not None:
            self.abbr_data += data

        if not self.quiet:
            if self.google_doc:
                # prevent white space immediately after 'begin emphasis'
                # marks ('**' and '_')
                lstripped_data = data.lstrip()
                if self.drop_white_space and not (self.pre or self.code):
                    data = lstripped_data
                if lstripped_data != "":
                    self.drop_white_space = 0

            if puredata and not self.pre:
                # This is a very dangerous call ... it could mess up
                # all handling of &nbsp; when not handled properly
                # (see entityref)
                data = re.sub(r"\s+", r" ", data)
                if data and data[0] == " ":
                    self.space = True
                    data = data[1:]
            if not data and not force:
                return

            if self.startpre:
                # self.out(" :") #TODO: not output when already one there
                if not data.startswith("\n") and not data.startswith("\r\n"):
                    # <pre>stuff...
                    data = "\n" + data
                if self.mark_code:
                    self.out("\n[code]")
                    self.p_p = 0

            bq = ">" * self.blockquote
            if not (force and data and data[0] == ">") and self.blockquote:
                bq += " "

            if self.pre:
                if self.list:
                    bq += self.list_code_indent

                if not self.backquote_code_style:
                    bq += "    "

                data = data.replace("\n", "\n" + bq)
                self.pre_indent = bq

            if self.startpre:
                self.startpre = False
                if self.backquote_code_style:
                    self.out("\n" + self.pre_indent + "```")
                    self.p_p = 0
                elif self.list:
                    # use existing initial indentation
                    data = data.lstrip("\n" + self.pre_indent)

            if self.start:
                self.space = False
                self.p_p = 0
                self.start = False

            if force == "end":
                # It's the end.
                self.p_p = 0
                self.out("\n")
                self.space = False

            if self.p_p:
                self.out((self.br_toggle + "\n" + bq) * self.p_p)
                self.space = False
                self.br_toggle = ""

            if self.space:
                if not self.lastWasNL:
                    self.out(" ")
                self.space = False

            if self.a and (
                (self.p_p == 2 and self.links_each_paragraph) or force == "end"
            ):
                if force == "end":
                    self.out("\n")

                newa = []
                for link in self.a:
                    if self.outcount > link.outcount:
                        self.out(
                            "   ["
                            + str(link.count)
                            + "]: "
                            + urlparse.urljoin(self.baseurl, link.attrs["href"])
                        )
                        if "title" in link.attrs and link.attrs["title"] is not None:
                            self.out(" (" + link.attrs["title"] + ")")
                        self.out("\n")
                    else:
                        newa.append(link)

                # Don't need an extra line when nothing was done.
                if self.a != newa:
                    self.out("\n")

                self.a = newa

            if self.abbr_list and force == "end":
                for abbr, definition in self.abbr_list.items():
                    self.out("  *[" + abbr + "]: " + definition + "\n")

            self.p_p = 0
            self.out(data)
            self.outcount += 1

    def handle_data(self, data: str, entity_char: bool = False) -> None:
        if not data:
            # Data may be empty for some HTML entities. For example,
            # LEFT-TO-RIGHT MARK.
            return

        if self.stressed:
            data = data.strip()
            self.stressed = False
            self.preceding_stressed = True
        elif self.preceding_stressed:
            if (
                re.match(r"[^][(){}\s.!?]", data[0])
                and not hn(self.current_tag)
                and self.current_tag not in ["a", "code", "pre"]
            ):
                # should match a letter or common punctuation
                data = " " + data
            self.preceding_stressed = False

        if self.style:
            self.style_def.update(dumb_css_parser(data))

        if self.maybe_automatic_link is not None:
            href = self.maybe_automatic_link
            if (
                href == data
                and self.absolute_url_matcher.match(href)
                and self.use_automatic_links
            ):
                self.o("<" + data + ">")
                self.empty_link = False
                return
            else:
                self.o("[")
                self.maybe_automatic_link = None
                self.empty_link = False

        if not self.code and not self.pre and not entity_char:
            data = escape_md_section(data, snob=self.escape_snob)
        self.preceding_data = data
        self.o(data, puredata=True)

    def charref(self, name: str) -> str:
        if name[0] in ["x", "X"]:
            c = int(name[1:], 16)
        else:
            c = int(name)

        if not 0 < c < 0x110000 or 0xD800 <= c < 0xE000:  # invalid or surrogate
            c = 0xFFFD  # REPLACEMENT CHARACTER
        c = control_character_replacements.get(c, c)

        if not self.unicode_snob and c in unifiable_n:
            return unifiable_n[c]
        else:
            return chr(c)

    def entityref(self, c: str) -> str:
        if not self.unicode_snob and c in UNIFIABLE:
            return UNIFIABLE[c]
        try:
            ch = html.entities.html5[c + ";"]
        except KeyError:
            return "&" + c + ";"
        return UNIFIABLE[c] if c == "nbsp" else ch

    def google_nest_count(self, style: Dict[str, str]) -> int:
        """
        Calculate the nesting count of google doc lists

        :type style: dict

        :rtype: int
        """
        nest_count = 0
        if "margin-left" in style:
            nest_count = int(style["margin-left"][:-2]) // self.google_list_indent

        return nest_count

    def optwrap(self, text: str) -> str:
        """
        Wrap all paragraphs in the provided text.

        :type text: str

        :rtype: str
        """
        if not self.body_width:
            return text

        result = ""
        newlines = 0
        # I cannot think of a better solution for now.
        # To avoid the non-wrap behaviour for entire paras
        # because of the presence of a link in it
        if not self.wrap_links:
            self.inline_links = False
        start_code = False
        for para in text.split("\n"):
            # If the text is between tri-backquote pairs, it's a code block;
            # don't wrap
            if self.backquote_code_style and para.lstrip().startswith("```"):
                start_code = not start_code
            if start_code:
                result += para + "\n"
            elif len(para) > 0:
                if not skipwrap(
                    para, self.wrap_links, self.wrap_list_items, self.wrap_tables
                ):
                    indent = ""
                    if para.startswith("  " + self.ul_item_mark):
                        # list item continuation: add a double indent to the
                        # new lines
                        indent = "    "
                    elif para.startswith("> "):
                        # blockquote continuation: add the greater than symbol
                        # to the new lines
                        indent = "> "
                    wrapped = wrap(
                        para,
                        self.body_width,
                        break_long_words=False,
                        subsequent_indent=indent,
                    )
                    result += "\n".join(wrapped)
                    if para.endswith("  "):
                        result += "  \n"
                        newlines = 1
                    elif indent:
                        result += "\n"
                        newlines = 1
                    else:
                        result += "\n\n"
                        newlines = 2
                else:
                    # Warning for the tempted!!!
                    # Be aware that obvious replacement of this with
                    # line.isspace()
                    # DOES NOT work! Explanations are welcome.
                    if not RE_SPACE.match(para):
                        result += para + "\n"
                        newlines = 1
            else:
                if newlines < 2:
                    result += "\n"
                    newlines += 1
        return result


def html2text(html: str, baseurl: str = "", bodywidth: Optional[int] = None) -> str:
    if bodywidth is None:
        bodywidth = BODY_WIDTH
    h = HTML2Text(baseurl=baseurl, bodywidth=bodywidth)

    return h.handle(html)
