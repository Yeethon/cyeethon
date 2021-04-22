import os.path
import re
from . import common as _common

TOOL = "gcc"
LINE_MARKER_RE = re.compile('^# (\\d+) "([^"]+)"(?: [1234])*$')
PREPROC_DIRECTIVE_RE = re.compile("^\\s*#\\s*(\\w+)\\b.*")
COMPILER_DIRECTIVE_RE = re.compile(
    "\n    ^\n    (.*?)  # <before>\n    (__\\w+__)  # <directive>\n    \\s*\n    [(] [(]\n    (\n        [^()]*\n        (?:\n            [(]\n            [^()]*\n            [)]\n            [^()]*\n         )*\n     )  # <args>\n    ( [)] [)] )?  # <closed>\n",
    re.VERBOSE,
)
POST_ARGS = ("-pthread", "-std=c99", "-E")


def preprocess(filename, incldirs=None, macros=None, samefiles=None):
    text = _common.preprocess(
        TOOL,
        filename,
        incldirs=incldirs,
        macros=macros,
        postargs=POST_ARGS,
        executable=["gcc"],
        compiler="unix",
    )
    return _iter_lines(text, filename, samefiles)


def _iter_lines(text, filename, samefiles, *, raw=False):
    lines = iter(text.splitlines())
    partial = 0
    origfile = None
    for line in lines:
        m = LINE_MARKER_RE.match(line)
        if m:
            (lno, origfile) = m.groups()
            lno = int(lno)
        elif _filter_orig_file(origfile, filename, samefiles):
            if (m := PREPROC_DIRECTIVE_RE.match(line)) :
                (name,) = m.groups()
                if name != "pragma":
                    raise Exception(line)
            else:
                if not raw:
                    (line, partial) = _strip_directives(line, partial=partial)
                (
                    yield _common.SourceLine(
                        _common.FileInfo(filename, lno), "source", (line or ""), None
                    )
                )
            lno += 1


def _strip_directives(line, partial=0):
    while partial > 0:
        if not (m := re.match("[^{}]*([()])", line)):
            return (None, partial)
        (delim,) = m.groups()
        partial += 1 if (delim == "(") else (-1)
        line = line[m.end() :]
    line = re.sub("__extension__", "", line)
    while (m := COMPILER_DIRECTIVE_RE.match(line)) :
        (before, _, _, closed) = m.groups()
        if closed:
            line = f"{before} {line[m.end():]}"
        else:
            (after, partial) = _strip_directives(line[m.end() :], 2)
            line = f"{before} {(after or '')}"
            if partial:
                break
    return (line, partial)


def _filter_orig_file(origfile, current, samefiles):
    if origfile == current:
        return True
    if origfile == "<stdin>":
        return True
    if os.path.isabs(origfile):
        return False
    for filename in samefiles or ():
        if filename.endswith(os.path.sep):
            filename += os.path.basename(current)
        if origfile == filename:
            return True
    return False
