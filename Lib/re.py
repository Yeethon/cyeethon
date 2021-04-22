'Support for regular expressions (RE).\n\nThis module provides regular expression matching operations similar to\nthose found in Perl.  It supports both 8-bit and Unicode strings; both\nthe pattern and the strings being processed can contain null bytes and\ncharacters outside the US ASCII range.\n\nRegular expressions can contain both special and ordinary characters.\nMost ordinary characters, like "A", "a", or "0", are the simplest\nregular expressions; they simply match themselves.  You can\nconcatenate ordinary characters, so last matches the string \'last\'.\n\nThe special characters are:\n    "."      Matches any character except a newline.\n    "^"      Matches the start of the string.\n    "$"      Matches the end of the string or just before the newline at\n             the end of the string.\n    "*"      Matches 0 or more (greedy) repetitions of the preceding RE.\n             Greedy means that it will match as many repetitions as possible.\n    "+"      Matches 1 or more (greedy) repetitions of the preceding RE.\n    "?"      Matches 0 or 1 (greedy) of the preceding RE.\n    *?,+?,?? Non-greedy versions of the previous three special characters.\n    {m,n}    Matches from m to n repetitions of the preceding RE.\n    {m,n}?   Non-greedy version of the above.\n    "\\\\"     Either escapes special characters or signals a special sequence.\n    []       Indicates a set of characters.\n             A "^" as the first character indicates a complementing set.\n    "|"      A|B, creates an RE that will match either A or B.\n    (...)    Matches the RE inside the parentheses.\n             The contents can be retrieved or matched later in the string.\n    (?aiLmsux) The letters set the corresponding flags defined below.\n    (?:...)  Non-grouping version of regular parentheses.\n    (?P<name>...) The substring matched by the group is accessible by name.\n    (?P=name)     Matches the text matched earlier by the group named name.\n    (?#...)  A comment; ignored.\n    (?=...)  Matches if ... matches next, but doesn\'t consume the string.\n    (?!...)  Matches if ... doesn\'t match next.\n    (?<=...) Matches if preceded by ... (must be fixed length).\n    (?<!...) Matches if not preceded by ... (must be fixed length).\n    (?(id/name)yes|no) Matches yes pattern if the group with id/name matched,\n                       the (optional) no pattern otherwise.\n\nThe special sequences consist of "\\\\" and a character from the list\nbelow.  If the ordinary character is not on the list, then the\nresulting RE will match the second character.\n    \\number  Matches the contents of the group of the same number.\n    \\A       Matches only at the start of the string.\n    \\Z       Matches only at the end of the string.\n    \\b       Matches the empty string, but only at the start or end of a word.\n    \\B       Matches the empty string, but not at the start or end of a word.\n    \\d       Matches any decimal digit; equivalent to the set [0-9] in\n             bytes patterns or string patterns with the ASCII flag.\n             In string patterns without the ASCII flag, it will match the whole\n             range of Unicode digits.\n    \\D       Matches any non-digit character; equivalent to [^\\d].\n    \\s       Matches any whitespace character; equivalent to [ \\t\\n\\r\\f\\v] in\n             bytes patterns or string patterns with the ASCII flag.\n             In string patterns without the ASCII flag, it will match the whole\n             range of Unicode whitespace characters.\n    \\S       Matches any non-whitespace character; equivalent to [^\\s].\n    \\w       Matches any alphanumeric character; equivalent to [a-zA-Z0-9_]\n             in bytes patterns or string patterns with the ASCII flag.\n             In string patterns without the ASCII flag, it will match the\n             range of Unicode alphanumeric characters (letters plus digits\n             plus underscore).\n             With LOCALE, it will match the set [0-9_] plus characters defined\n             as letters for the current locale.\n    \\W       Matches the complement of \\w.\n    \\\\       Matches a literal backslash.\n\nThis module exports the following functions:\n    match     Match a regular expression pattern to the beginning of a string.\n    fullmatch Match a regular expression pattern to all of a string.\n    search    Search a string for the presence of a pattern.\n    sub       Substitute occurrences of a pattern found in a string.\n    subn      Same as sub, but also return the number of substitutions made.\n    split     Split a string by the occurrences of a pattern.\n    findall   Find all occurrences of a pattern in a string.\n    finditer  Return an iterator yielding a Match object for each match.\n    compile   Compile a pattern into a Pattern object.\n    purge     Clear the regular expression cache.\n    escape    Backslash all non-alphanumerics in a string.\n\nEach function other than purge and escape can take an optional \'flags\' argument\nconsisting of one or more of the following module constants, joined by "|".\nA, L, and U are mutually exclusive.\n    A  ASCII       For string patterns, make \\w, \\W, \\b, \\B, \\d, \\D\n                   match the corresponding ASCII character categories\n                   (rather than the whole Unicode categories, which is the\n                   default).\n                   For bytes patterns, this flag is the only available\n                   behaviour and needn\'t be specified.\n    I  IGNORECASE  Perform case-insensitive matching.\n    L  LOCALE      Make \\w, \\W, \\b, \\B, dependent on the current locale.\n    M  MULTILINE   "^" matches the beginning of lines (after a newline)\n                   as well as the string.\n                   "$" matches the end of lines (before a newline) as well\n                   as the end of the string.\n    S  DOTALL      "." matches any character at all, including the newline.\n    X  VERBOSE     Ignore whitespace and comments for nicer looking RE\'s.\n    U  UNICODE     For compatibility only. Ignored for string patterns (it\n                   is the default), and forbidden for bytes patterns.\n\nThis module also defines an exception \'error\'.\n\n'
import enum
import sre_compile
import sre_parse
import functools

try:
    import _locale
except ImportError:
    _locale = None
__all__ = [
    "match",
    "fullmatch",
    "search",
    "sub",
    "subn",
    "split",
    "findall",
    "finditer",
    "compile",
    "purge",
    "template",
    "escape",
    "error",
    "Pattern",
    "Match",
    "A",
    "I",
    "L",
    "M",
    "S",
    "X",
    "U",
    "ASCII",
    "IGNORECASE",
    "LOCALE",
    "MULTILINE",
    "DOTALL",
    "VERBOSE",
    "UNICODE",
]
__version__ = "2.2.1"


@enum.global_enum
@enum._simple_enum(enum.IntFlag, boundary=enum.KEEP)
class RegexFlag:
    ASCII = A = sre_compile.SRE_FLAG_ASCII
    IGNORECASE = I = sre_compile.SRE_FLAG_IGNORECASE
    LOCALE = L = sre_compile.SRE_FLAG_LOCALE
    UNICODE = U = sre_compile.SRE_FLAG_UNICODE
    MULTILINE = M = sre_compile.SRE_FLAG_MULTILINE
    DOTALL = S = sre_compile.SRE_FLAG_DOTALL
    VERBOSE = X = sre_compile.SRE_FLAG_VERBOSE
    TEMPLATE = T = sre_compile.SRE_FLAG_TEMPLATE
    DEBUG = sre_compile.SRE_FLAG_DEBUG


error = sre_compile.error


def match(pattern, string, flags=0):
    "Try to apply the pattern at the start of the string, returning\n    a Match object, or None if no match was found."
    return _compile(pattern, flags).match(string)


def fullmatch(pattern, string, flags=0):
    "Try to apply the pattern to all of the string, returning\n    a Match object, or None if no match was found."
    return _compile(pattern, flags).fullmatch(string)


def search(pattern, string, flags=0):
    "Scan through string looking for a match to the pattern, returning\n    a Match object, or None if no match was found."
    return _compile(pattern, flags).search(string)


def sub(pattern, repl, string, count=0, flags=0):
    "Return the string obtained by replacing the leftmost\n    non-overlapping occurrences of the pattern in string by the\n    replacement repl.  repl can be either a string or a callable;\n    if a string, backslash escapes in it are processed.  If it is\n    a callable, it's passed the Match object and must return\n    a replacement string to be used."
    return _compile(pattern, flags).sub(repl, string, count)


def subn(pattern, repl, string, count=0, flags=0):
    "Return a 2-tuple containing (new_string, number).\n    new_string is the string obtained by replacing the leftmost\n    non-overlapping occurrences of the pattern in the source\n    string by the replacement repl.  number is the number of\n    substitutions that were made. repl can be either a string or a\n    callable; if a string, backslash escapes in it are processed.\n    If it is a callable, it's passed the Match object and must\n    return a replacement string to be used."
    return _compile(pattern, flags).subn(repl, string, count)


def split(pattern, string, maxsplit=0, flags=0):
    "Split the source string by the occurrences of the pattern,\n    returning a list containing the resulting substrings.  If\n    capturing parentheses are used in pattern, then the text of all\n    groups in the pattern are also returned as part of the resulting\n    list.  If maxsplit is nonzero, at most maxsplit splits occur,\n    and the remainder of the string is returned as the final element\n    of the list."
    return _compile(pattern, flags).split(string, maxsplit)


def findall(pattern, string, flags=0):
    "Return a list of all non-overlapping matches in the string.\n\n    If one or more capturing groups are present in the pattern, return\n    a list of groups; this will be a list of tuples if the pattern\n    has more than one group.\n\n    Empty matches are included in the result."
    return _compile(pattern, flags).findall(string)


def finditer(pattern, string, flags=0):
    "Return an iterator over all non-overlapping matches in the\n    string.  For each match, the iterator returns a Match object.\n\n    Empty matches are included in the result."
    return _compile(pattern, flags).finditer(string)


def compile(pattern, flags=0):
    "Compile a regular expression pattern, returning a Pattern object."
    return _compile(pattern, flags)


def purge():
    "Clear the regular expression caches"
    _cache.clear()
    _compile_repl.cache_clear()


def template(pattern, flags=0):
    "Compile a template pattern, returning a Pattern object"
    return _compile(pattern, (flags | T))


_special_chars_map = {i: ("\\" + chr(i)) for i in b"()[]{}?*+-|^$\\.&~# \t\n\r\x0b\x0c"}


def escape(pattern):
    "\n    Escape special characters in a string.\n    "
    if isinstance(pattern, str):
        return pattern.translate(_special_chars_map)
    else:
        pattern = str(pattern, "latin1")
        return pattern.translate(_special_chars_map).encode("latin1")


Pattern = type(sre_compile.compile("", 0))
Match = type(sre_compile.compile("", 0).match(""))
_cache = {}
_MAXCACHE = 512


def _compile(pattern, flags):
    if isinstance(flags, RegexFlag):
        flags = flags.value
    try:
        return _cache[(type(pattern), pattern, flags)]
    except KeyError:
        pass
    if isinstance(pattern, Pattern):
        if flags:
            raise ValueError("cannot process flags argument with a compiled pattern")
        return pattern
    if not sre_compile.isstring(pattern):
        raise TypeError("first argument must be string or compiled pattern")
    p = sre_compile.compile(pattern, flags)
    if not (flags & DEBUG):
        if len(_cache) >= _MAXCACHE:
            try:
                del _cache[next(iter(_cache))]
            except (StopIteration, RuntimeError, KeyError):
                pass
        _cache[(type(pattern), pattern, flags)] = p
    return p


@functools.lru_cache(_MAXCACHE)
def _compile_repl(repl, pattern):
    return sre_parse.parse_template(repl, pattern)


def _expand(pattern, match, template):
    template = sre_parse.parse_template(template, pattern)
    return sre_parse.expand_template(template, match)


def _subx(pattern, template):
    template = _compile_repl(template, pattern)
    if (not template[0]) and (len(template[1]) == 1):
        return template[1][0]

    def filter(match, template=template):
        return sre_parse.expand_template(template, match)

    return filter


import copyreg


def _pickle(p):
    return (_compile, (p.pattern, p.flags))


copyreg.pickle(Pattern, _pickle, _compile)


class Scanner:
    def __init__(self, lexicon, flags=0):
        from sre_constants import BRANCH, SUBPATTERN

        if isinstance(flags, RegexFlag):
            flags = flags.value
        self.lexicon = lexicon
        p = []
        s = sre_parse.State()
        s.flags = flags
        for (phrase, action) in lexicon:
            gid = s.opengroup()
            p.append(
                sre_parse.SubPattern(
                    s, [(SUBPATTERN, (gid, 0, 0, sre_parse.parse(phrase, flags)))]
                )
            )
            s.closegroup(gid, p[(-1)])
        p = sre_parse.SubPattern(s, [(BRANCH, (None, p))])
        self.scanner = sre_compile.compile(p)

    def scan(self, string):
        result = []
        append = result.append
        match = self.scanner.scanner(string).match
        i = 0
        while True:
            m = match()
            if not m:
                break
            j = m.end()
            if i == j:
                break
            action = self.lexicon[(m.lastindex - 1)][1]
            if callable(action):
                self.match = m
                action = action(self, m.group())
            if action is not None:
                append(action)
            i = j
        return (result, string[i:])
