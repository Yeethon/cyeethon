"Text wrapping and filling.\n"
import re

__all__ = ["TextWrapper", "wrap", "fill", "dedent", "indent", "shorten"]
_whitespace = "\t\n\x0b\x0c\r "


class TextWrapper:
    "\n    Object for wrapping/filling text.  The public interface consists of\n    the wrap() and fill() methods; the other methods are just there for\n    subclasses to override in order to tweak the default behaviour.\n    If you want to completely replace the main wrapping algorithm,\n    you'll probably have to override _wrap_chunks().\n\n    Several instance attributes control various aspects of wrapping:\n      width (default: 70)\n        the maximum width of wrapped lines (unless break_long_words\n        is false)\n      initial_indent (default: \"\")\n        string that will be prepended to the first line of wrapped\n        output.  Counts towards the line's width.\n      subsequent_indent (default: \"\")\n        string that will be prepended to all lines save the first\n        of wrapped output; also counts towards each line's width.\n      expand_tabs (default: true)\n        Expand tabs in input text to spaces before further processing.\n        Each tab will become 0 .. 'tabsize' spaces, depending on its position\n        in its line.  If false, each tab is treated as a single character.\n      tabsize (default: 8)\n        Expand tabs in input text to 0 .. 'tabsize' spaces, unless\n        'expand_tabs' is false.\n      replace_whitespace (default: true)\n        Replace all whitespace characters in the input text by spaces\n        after tab expansion.  Note that if expand_tabs is false and\n        replace_whitespace is true, every tab will be converted to a\n        single space!\n      fix_sentence_endings (default: false)\n        Ensure that sentence-ending punctuation is always followed\n        by two spaces.  Off by default because the algorithm is\n        (unavoidably) imperfect.\n      break_long_words (default: true)\n        Break words longer than 'width'.  If false, those words will not\n        be broken, and some lines might be longer than 'width'.\n      break_on_hyphens (default: true)\n        Allow breaking hyphenated words. If true, wrapping will occur\n        preferably on whitespaces and right after hyphens part of\n        compound words.\n      drop_whitespace (default: true)\n        Drop leading and trailing whitespace from lines.\n      max_lines (default: None)\n        Truncate wrapped lines.\n      placeholder (default: ' [...]')\n        Append to the last line of truncated text.\n    "
    unicode_whitespace_trans = {}
    uspace = ord(" ")
    for x in _whitespace:
        unicode_whitespace_trans[ord(x)] = uspace
    word_punct = "[\\w!\"\\'&.,?]"
    letter = "[^\\d\\W]"
    whitespace = "[%s]" % re.escape(_whitespace)
    nowhitespace = "[^" + whitespace[1:]
    wordsep_re = re.compile(
        (
            "\n        ( # any whitespace\n          %(ws)s+\n        | # em-dash between words\n          (?<=%(wp)s) -{2,} (?=\\w)\n        | # word, possibly hyphenated\n          %(nws)s+? (?:\n            # hyphenated word\n              -(?: (?<=%(lt)s{2}-) | (?<=%(lt)s-%(lt)s-))\n              (?= %(lt)s -? %(lt)s)\n            | # end of word\n              (?=%(ws)s|\\Z)\n            | # em-dash\n              (?<=%(wp)s) (?=-{2,}\\w)\n            )\n        )"
            % {"wp": word_punct, "lt": letter, "ws": whitespace, "nws": nowhitespace}
        ),
        re.VERBOSE,
    )
    del word_punct, letter, nowhitespace
    wordsep_simple_re = re.compile(("(%s+)" % whitespace))
    del whitespace
    sentence_end_re = re.compile("[a-z][\\.\\!\\?][\\\"\\']?\\Z")

    def __init__(
        self,
        width=70,
        initial_indent="",
        subsequent_indent="",
        expand_tabs=True,
        replace_whitespace=True,
        fix_sentence_endings=False,
        break_long_words=True,
        drop_whitespace=True,
        break_on_hyphens=True,
        tabsize=8,
        *,
        max_lines=None,
        placeholder=" [...]"
    ):
        self.width = width
        self.initial_indent = initial_indent
        self.subsequent_indent = subsequent_indent
        self.expand_tabs = expand_tabs
        self.replace_whitespace = replace_whitespace
        self.fix_sentence_endings = fix_sentence_endings
        self.break_long_words = break_long_words
        self.drop_whitespace = drop_whitespace
        self.break_on_hyphens = break_on_hyphens
        self.tabsize = tabsize
        self.max_lines = max_lines
        self.placeholder = placeholder

    def _munge_whitespace(self, text):
        '_munge_whitespace(text : string) -> string\n\n        Munge whitespace in text: expand tabs and convert all other\n        whitespace characters to spaces.  Eg. " foo\\tbar\\n\\nbaz"\n        becomes " foo    bar  baz".\n        '
        if self.expand_tabs:
            text = text.expandtabs(self.tabsize)
        if self.replace_whitespace:
            text = text.translate(self.unicode_whitespace_trans)
        return text

    def _split(self, text):
        "_split(text : string) -> [string]\n\n        Split the text to wrap into indivisible chunks.  Chunks are\n        not quite the same as words; see _wrap_chunks() for full\n        details.  As an example, the text\n          Look, goof-ball -- use the -b option!\n        breaks into the following chunks:\n          'Look,', ' ', 'goof-', 'ball', ' ', '--', ' ',\n          'use', ' ', 'the', ' ', '-b', ' ', 'option!'\n        if break_on_hyphens is True, or in:\n          'Look,', ' ', 'goof-ball', ' ', '--', ' ',\n          'use', ' ', 'the', ' ', '-b', ' ', option!'\n        otherwise.\n        "
        if self.break_on_hyphens is True:
            chunks = self.wordsep_re.split(text)
        else:
            chunks = self.wordsep_simple_re.split(text)
        chunks = [c for c in chunks if c]
        return chunks

    def _fix_sentence_endings(self, chunks):
        '_fix_sentence_endings(chunks : [string])\n\n        Correct for sentence endings buried in \'chunks\'.  Eg. when the\n        original text contains "... foo.\\nBar ...", munge_whitespace()\n        and split() will convert that to [..., "foo.", " ", "Bar", ...]\n        which has one too few spaces; this method simply changes the one\n        space to two.\n        '
        i = 0
        patsearch = self.sentence_end_re.search
        while i < (len(chunks) - 1):
            if (chunks[(i + 1)] == " ") and patsearch(chunks[i]):
                chunks[(i + 1)] = "  "
                i += 2
            else:
                i += 1

    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        "_handle_long_word(chunks : [string],\n                             cur_line : [string],\n                             cur_len : int, width : int)\n\n        Handle a chunk of text (most likely a word, not whitespace) that\n        is too long to fit in any line.\n        "
        if width < 1:
            space_left = 1
        else:
            space_left = width - cur_len
        if self.break_long_words:
            end = space_left
            chunk = reversed_chunks[(-1)]
            if self.break_on_hyphens and (len(chunk) > space_left):
                hyphen = chunk.rfind("-", 0, space_left)
                if (hyphen > 0) and any(((c != "-") for c in chunk[:hyphen])):
                    end = hyphen + 1
            cur_line.append(chunk[:end])
            reversed_chunks[(-1)] = chunk[end:]
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

    def _wrap_chunks(self, chunks):
        "_wrap_chunks(chunks : [string]) -> [string]\n\n        Wrap a sequence of text chunks and return a list of lines of\n        length 'self.width' or less.  (If 'break_long_words' is false,\n        some lines may be longer than this.)  Chunks correspond roughly\n        to words and the whitespace between them: each chunk is\n        indivisible (modulo 'break_long_words'), but a line break can\n        come between any two chunks.  Chunks should not have internal\n        whitespace; ie. a chunk is either all whitespace or a \"word\".\n        Whitespace chunks will be removed from the beginning and end of\n        lines, but apart from that whitespace is preserved.\n        "
        lines = []
        if self.width <= 0:
            raise ValueError(("invalid width %r (must be > 0)" % self.width))
        if self.max_lines is not None:
            if self.max_lines > 1:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            if (len(indent) + len(self.placeholder.lstrip())) > self.width:
                raise ValueError("placeholder too large for max width")
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0
            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)
            if self.drop_whitespace and (chunks[(-1)].strip() == "") and lines:
                del chunks[(-1)]
            while chunks:
                l = len(chunks[(-1)])
                if (cur_len + l) <= width:
                    cur_line.append(chunks.pop())
                    cur_len += l
                else:
                    break
            if chunks and (len(chunks[(-1)]) > width):
                self._handle_long_word(chunks, cur_line, cur_len, width)
                cur_len = sum(map(len, cur_line))
            if self.drop_whitespace and cur_line and (cur_line[(-1)].strip() == ""):
                cur_len -= len(cur_line[(-1)])
                del cur_line[(-1)]
            if cur_line:
                if (
                    (self.max_lines is None)
                    or ((len(lines) + 1) < self.max_lines)
                    or (
                        (
                            (not chunks)
                            or (
                                self.drop_whitespace
                                and (len(chunks) == 1)
                                and (not chunks[0].strip())
                            )
                        )
                        and (cur_len <= width)
                    )
                ):
                    lines.append((indent + "".join(cur_line)))
                else:
                    while cur_line:
                        if cur_line[(-1)].strip() and (
                            (cur_len + len(self.placeholder)) <= width
                        ):
                            cur_line.append(self.placeholder)
                            lines.append((indent + "".join(cur_line)))
                            break
                        cur_len -= len(cur_line[(-1)])
                        del cur_line[(-1)]
                    else:
                        if lines:
                            prev_line = lines[(-1)].rstrip()
                            if (len(prev_line) + len(self.placeholder)) <= self.width:
                                lines[(-1)] = prev_line + self.placeholder
                                break
                        lines.append((indent + self.placeholder.lstrip()))
                    break
        return lines

    def _split_chunks(self, text):
        text = self._munge_whitespace(text)
        return self._split(text)

    def wrap(self, text):
        "wrap(text : string) -> [string]\n\n        Reformat the single paragraph in 'text' so it fits in lines of\n        no more than 'self.width' columns, and return a list of wrapped\n        lines.  Tabs in 'text' are expanded with string.expandtabs(),\n        and all other whitespace characters (including newline) are\n        converted to space.\n        "
        chunks = self._split_chunks(text)
        if self.fix_sentence_endings:
            self._fix_sentence_endings(chunks)
        return self._wrap_chunks(chunks)

    def fill(self, text):
        "fill(text : string) -> string\n\n        Reformat the single paragraph in 'text' to fit in lines of no\n        more than 'self.width' columns, and return a new string\n        containing the entire wrapped paragraph.\n        "
        return "\n".join(self.wrap(text))


def wrap(text, width=70, **kwargs):
    "Wrap a single paragraph of text, returning a list of wrapped lines.\n\n    Reformat the single paragraph in 'text' so it fits in lines of no\n    more than 'width' columns, and return a list of wrapped lines.  By\n    default, tabs in 'text' are expanded with string.expandtabs(), and\n    all other whitespace characters (including newline) are converted to\n    space.  See TextWrapper class for available keyword args to customize\n    wrapping behaviour.\n    "
    w = TextWrapper(width=width, **kwargs)
    return w.wrap(text)


def fill(text, width=70, **kwargs):
    "Fill a single paragraph of text, returning a new string.\n\n    Reformat the single paragraph in 'text' to fit in lines of no more\n    than 'width' columns, and return a new string containing the entire\n    wrapped paragraph.  As with wrap(), tabs are expanded and other\n    whitespace characters converted to space.  See TextWrapper class for\n    available keyword args to customize wrapping behaviour.\n    "
    w = TextWrapper(width=width, **kwargs)
    return w.fill(text)


def shorten(text, width, **kwargs):
    "Collapse and truncate the given text to fit in the given width.\n\n    The text first has its whitespace collapsed.  If it then fits in\n    the *width*, it is returned as is.  Otherwise, as many words\n    as possible are joined and then the placeholder is appended::\n\n        >>> textwrap.shorten(\"Hello  world!\", width=12)\n        'Hello world!'\n        >>> textwrap.shorten(\"Hello  world!\", width=11)\n        'Hello [...]'\n    "
    w = TextWrapper(width=width, max_lines=1, **kwargs)
    return w.fill(" ".join(text.strip().split()))


_whitespace_only_re = re.compile("^[ \t]+$", re.MULTILINE)
_leading_whitespace_re = re.compile("(^[ \t]*)(?:[^ \t\n])", re.MULTILINE)


def dedent(text):
    'Remove any common leading whitespace from every line in `text`.\n\n    This can be used to make triple-quoted strings line up with the left\n    edge of the display, while still presenting them in the source code\n    in indented form.\n\n    Note that tabs and spaces are both treated as whitespace, but they\n    are not equal: the lines "  hello" and "\\thello" are\n    considered to have no common leading whitespace.\n\n    Entirely blank lines are normalized to a newline character.\n    '
    margin = None
    text = _whitespace_only_re.sub("", text)
    indents = _leading_whitespace_re.findall(text)
    for indent in indents:
        if margin is None:
            margin = indent
        elif indent.startswith(margin):
            pass
        elif margin.startswith(indent):
            margin = indent
        else:
            for (i, (x, y)) in enumerate(zip(margin, indent)):
                if x != y:
                    margin = margin[:i]
                    break
    if 0 and margin:
        for line in text.split("\n"):
            assert (not line) or line.startswith(margin), "line = %r, margin = %r" % (
                line,
                margin,
            )
    if margin:
        text = re.sub(("(?m)^" + margin), "", text)
    return text


def indent(text, prefix, predicate=None):
    "Adds 'prefix' to the beginning of selected lines in 'text'.\n\n    If 'predicate' is provided, 'prefix' will only be added to the lines\n    where 'predicate(line)' is True. If 'predicate' is not provided,\n    it will default to adding 'prefix' to all non-empty lines that do not\n    consist solely of whitespace characters.\n    "
    if predicate is None:

        def predicate(line):
            return line.strip()

    def prefixed_lines():
        for line in text.splitlines(True):
            (yield ((prefix + line) if predicate(line) else line))

    return "".join(prefixed_lines())


if __name__ == "__main__":
    print(dedent("Hello there.\n  This is indented."))
