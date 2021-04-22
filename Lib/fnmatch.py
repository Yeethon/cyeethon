"Filename matching with shell patterns.\n\nfnmatch(FILENAME, PATTERN) matches according to the local convention.\nfnmatchcase(FILENAME, PATTERN) always takes case in account.\n\nThe functions operate by translating the pattern into a regular\nexpression.  They cache the compiled regular expressions for speed.\n\nThe function translate(PATTERN) returns a regular expression\ncorresponding to PATTERN.  (It does not compile it.)\n"
import os
import posixpath
import re
import functools

__all__ = ["filter", "fnmatch", "fnmatchcase", "translate"]
from itertools import count

_nextgroupnum = count().__next__
del count


def fnmatch(name, pat):
    "Test whether FILENAME matches PATTERN.\n\n    Patterns are Unix shell style:\n\n    *       matches everything\n    ?       matches any single character\n    [seq]   matches any character in seq\n    [!seq]  matches any char not in seq\n\n    An initial period in FILENAME is not special.\n    Both FILENAME and PATTERN are first case-normalized\n    if the operating system requires it.\n    If you don't want this, use fnmatchcase(FILENAME, PATTERN).\n    "
    name = os.path.normcase(name)
    pat = os.path.normcase(pat)
    return fnmatchcase(name, pat)


@functools.lru_cache(maxsize=256, typed=True)
def _compile_pattern(pat):
    if isinstance(pat, bytes):
        pat_str = str(pat, "ISO-8859-1")
        res_str = translate(pat_str)
        res = bytes(res_str, "ISO-8859-1")
    else:
        res = translate(pat)
    return re.compile(res).match


def filter(names, pat):
    "Construct a list from those elements of the iterable NAMES that match PAT."
    result = []
    pat = os.path.normcase(pat)
    match = _compile_pattern(pat)
    if os.path is posixpath:
        for name in names:
            if match(name):
                result.append(name)
    else:
        for name in names:
            if match(os.path.normcase(name)):
                result.append(name)
    return result


def fnmatchcase(name, pat):
    "Test whether FILENAME matches PATTERN, including case.\n\n    This is a version of fnmatch() which doesn't case-normalize\n    its arguments.\n    "
    match = _compile_pattern(pat)
    return match(name) is not None


def translate(pat):
    "Translate a shell PATTERN to a regular expression.\n\n    There is no way to quote meta-characters.\n    "
    STAR = object()
    res = []
    add = res.append
    (i, n) = (0, len(pat))
    while i < n:
        c = pat[i]
        i = i + 1
        if c == "*":
            if (not res) or (res[(-1)] is not STAR):
                add(STAR)
        elif c == "?":
            add(".")
        elif c == "[":
            j = i
            if (j < n) and (pat[j] == "!"):
                j = j + 1
            if (j < n) and (pat[j] == "]"):
                j = j + 1
            while (j < n) and (pat[j] != "]"):
                j = j + 1
            if j >= n:
                add("\\[")
            else:
                stuff = pat[i:j]
                if "--" not in stuff:
                    stuff = stuff.replace("\\", "\\\\")
                else:
                    chunks = []
                    k = (i + 2) if (pat[i] == "!") else (i + 1)
                    while True:
                        k = pat.find("-", k, j)
                        if k < 0:
                            break
                        chunks.append(pat[i:k])
                        i = k + 1
                        k = k + 3
                    chunks.append(pat[i:j])
                    stuff = "-".join(
                        (s.replace("\\", "\\\\").replace("-", "\\-") for s in chunks)
                    )
                stuff = re.sub("([&~|])", "\\\\\\1", stuff)
                i = j + 1
                if stuff[0] == "!":
                    stuff = "^" + stuff[1:]
                elif stuff[0] in ("^", "["):
                    stuff = "\\" + stuff
                add(f"[{stuff}]")
        else:
            add(re.escape(c))
    assert i == n
    inp = res
    res = []
    add = res.append
    (i, n) = (0, len(inp))
    while (i < n) and (inp[i] is not STAR):
        add(inp[i])
        i += 1
    while i < n:
        assert inp[i] is STAR
        i += 1
        if i == n:
            add(".*")
            break
        assert inp[i] is not STAR
        fixed = []
        while (i < n) and (inp[i] is not STAR):
            fixed.append(inp[i])
            i += 1
        fixed = "".join(fixed)
        if i == n:
            add(".*")
            add(fixed)
        else:
            groupnum = _nextgroupnum()
            add(f"(?=(?P<g{groupnum}>.*?{fixed}))(?P=g{groupnum})")
    assert i == n
    res = "".join(res)
    return f"(?s:{res})\Z"
