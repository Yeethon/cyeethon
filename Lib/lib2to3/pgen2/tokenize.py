'Tokenization help for Python programs.\n\ngenerate_tokens(readline) is a generator that breaks a stream of\ntext into Python tokens.  It accepts a readline-like method which is called\nrepeatedly to get the next line of input (or "" for EOF).  It generates\n5-tuples with these members:\n\n    the token type (see token.py)\n    the token (a string)\n    the starting (row, column) indices of the token (a 2-tuple of ints)\n    the ending (row, column) indices of the token (a 2-tuple of ints)\n    the original line (string)\n\nIt is designed to match the working of the Python tokenizer exactly, except\nthat it produces COMMENT tokens for comments and gives type OP for all\noperators\n\nOlder entry points\n    tokenize_loop(readline, tokeneater)\n    tokenize(readline, tokeneater=printtoken)\nare the same, except instead of generating tokens, tokeneater is a callback\nfunction to which the 5 fields described above are passed as 5 arguments,\neach time a new token is found.'
__author__ = "Ka-Ping Yee <ping@lfw.org>"
__credits__ = "GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, Skip Montanaro"
import string, re
from codecs import BOM_UTF8, lookup
from lib2to3.pgen2.token import *
from . import token

__all__ = [x for x in dir(token) if (x[0] != "_")] + [
    "tokenize",
    "generate_tokens",
    "untokenize",
]
del token
try:
    bytes
except NameError:
    bytes = str


def group(*choices):
    return ("(" + "|".join(choices)) + ")"


def any(*choices):
    return group(*choices) + "*"


def maybe(*choices):
    return group(*choices) + "?"


def _combinations(*l):
    return set(
        ((x + y) for x in l for y in (l + ("",)) if (x.casefold() != y.casefold()))
    )


Whitespace = "[ \\f\\t]*"
Comment = "#[^\\r\\n]*"
Ignore = (Whitespace + any(("\\\\\\r?\\n" + Whitespace))) + maybe(Comment)
Name = "\\w+"
Binnumber = "0[bB]_?[01]+(?:_[01]+)*"
Hexnumber = "0[xX]_?[\\da-fA-F]+(?:_[\\da-fA-F]+)*[lL]?"
Octnumber = "0[oO]?_?[0-7]+(?:_[0-7]+)*[lL]?"
Decnumber = group("[1-9]\\d*(?:_\\d+)*[lL]?", "0[lL]?")
Intnumber = group(Binnumber, Hexnumber, Octnumber, Decnumber)
Exponent = "[eE][-+]?\\d+(?:_\\d+)*"
Pointfloat = group("\\d+(?:_\\d+)*\\.(?:\\d+(?:_\\d+)*)?", "\\.\\d+(?:_\\d+)*") + maybe(
    Exponent
)
Expfloat = "\\d+(?:_\\d+)*" + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Imagnumber = group("\\d+(?:_\\d+)*[jJ]", (Floatnumber + "[jJ]"))
Number = group(Imagnumber, Floatnumber, Intnumber)
Single = "[^'\\\\]*(?:\\\\.[^'\\\\]*)*'"
Double = '[^"\\\\]*(?:\\\\.[^"\\\\]*)*"'
Single3 = "[^'\\\\]*(?:(?:\\\\.|'(?!''))[^'\\\\]*)*'''"
Double3 = '[^"\\\\]*(?:(?:\\\\.|"(?!""))[^"\\\\]*)*"""'
_litprefix = "(?:[uUrRbBfF]|[rR][fFbB]|[fFbBuU][rR])?"
Triple = group((_litprefix + "'''"), (_litprefix + '"""'))
String = group(
    (_litprefix + "'[^\\n'\\\\]*(?:\\\\.[^\\n'\\\\]*)*'"),
    (_litprefix + '"[^\\n"\\\\]*(?:\\\\.[^\\n"\\\\]*)*"'),
)
Operator = group(
    "\\*\\*=?", ">>=?", "<<=?", "<>", "!=", "//=?", "->", "[+\\-*/%&@|^=<>]=?", "~"
)
Bracket = "[][(){}]"
Special = group("\\r?\\n", ":=", "[:;.,`@]")
Funny = group(Operator, Bracket, Special)
PlainToken = group(Number, Funny, String, Name)
Token = Ignore + PlainToken
ContStr = group(
    ((_litprefix + "'[^\\n'\\\\]*(?:\\\\.[^\\n'\\\\]*)*") + group("'", "\\\\\\r?\\n")),
    ((_litprefix + '"[^\\n"\\\\]*(?:\\\\.[^\\n"\\\\]*)*') + group('"', "\\\\\\r?\\n")),
)
PseudoExtras = group("\\\\\\r?\\n", Comment, Triple)
PseudoToken = Whitespace + group(PseudoExtras, Number, Funny, ContStr, Name)
(tokenprog, pseudoprog, single3prog, double3prog) = map(
    re.compile, (Token, PseudoToken, Single3, Double3)
)
_strprefixes = (
    _combinations("r", "R", "f", "F") | _combinations("r", "R", "b", "B")
) | {"u", "U", "ur", "uR", "Ur", "UR"}
endprogs = {
    "'": re.compile(Single),
    '"': re.compile(Double),
    "'''": single3prog,
    '"""': double3prog,
    **{f"{prefix}'''": single3prog for prefix in _strprefixes},
    **{f'{prefix}"""': double3prog for prefix in _strprefixes},
    **{prefix: None for prefix in _strprefixes},
}
triple_quoted = ({"'''", '"""'} | {f"{prefix}'''" for prefix in _strprefixes}) | {
    f'{prefix}"""' for prefix in _strprefixes
}
single_quoted = ({"'", '"'} | {f"{prefix}'" for prefix in _strprefixes}) | {
    f'{prefix}"' for prefix in _strprefixes
}
tabsize = 8


class TokenError(Exception):
    pass


class StopTokenizing(Exception):
    pass


def printtoken(type, token, xxx_todo_changeme, xxx_todo_changeme1, line):
    (srow, scol) = xxx_todo_changeme
    (erow, ecol) = xxx_todo_changeme1
    print(
        ("%d,%d-%d,%d:\t%s\t%s" % (srow, scol, erow, ecol, tok_name[type], repr(token)))
    )


def tokenize(readline, tokeneater=printtoken):
    "\n    The tokenize() function accepts two parameters: one representing the\n    input stream, and one providing an output mechanism for tokenize().\n\n    The first parameter, readline, must be a callable object which provides\n    the same interface as the readline() method of built-in file objects.\n    Each call to the function should return one line of input as a string.\n\n    The second parameter, tokeneater, must also be a callable object. It is\n    called once for each token, with five arguments, corresponding to the\n    tuples generated by generate_tokens().\n    "
    try:
        tokenize_loop(readline, tokeneater)
    except StopTokenizing:
        pass


def tokenize_loop(readline, tokeneater):
    for token_info in generate_tokens(readline):
        tokeneater(*token_info)


class Untokenizer:
    def __init__(self):
        self.tokens = []
        self.prev_row = 1
        self.prev_col = 0

    def add_whitespace(self, start):
        (row, col) = start
        assert row <= self.prev_row
        col_offset = col - self.prev_col
        if col_offset:
            self.tokens.append((" " * col_offset))

    def untokenize(self, iterable):
        for t in iterable:
            if len(t) == 2:
                self.compat(t, iterable)
                break
            (tok_type, token, start, end, line) = t
            self.add_whitespace(start)
            self.tokens.append(token)
            (self.prev_row, self.prev_col) = end
            if tok_type in (NEWLINE, NL):
                self.prev_row += 1
                self.prev_col = 0
        return "".join(self.tokens)

    def compat(self, token, iterable):
        startline = False
        indents = []
        toks_append = self.tokens.append
        (toknum, tokval) = token
        if toknum in (NAME, NUMBER):
            tokval += " "
        if toknum in (NEWLINE, NL):
            startline = True
        for tok in iterable:
            (toknum, tokval) = tok[:2]
            if toknum in (NAME, NUMBER, ASYNC, AWAIT):
                tokval += " "
            if toknum == INDENT:
                indents.append(tokval)
                continue
            elif toknum == DEDENT:
                indents.pop()
                continue
            elif toknum in (NEWLINE, NL):
                startline = True
            elif startline and indents:
                toks_append(indents[(-1)])
                startline = False
            toks_append(tokval)


cookie_re = re.compile("^[ \\t\\f]*#.*?coding[:=][ \\t]*([-\\w.]+)", re.ASCII)
blank_re = re.compile(b"^[ \\t\\f]*(?:[#\\r\\n]|$)", re.ASCII)


def _get_normal_name(orig_enc):
    "Imitates get_normal_name in tokenizer.c."
    enc = orig_enc[:12].lower().replace("_", "-")
    if (enc == "utf-8") or enc.startswith("utf-8-"):
        return "utf-8"
    if (enc in ("latin-1", "iso-8859-1", "iso-latin-1")) or enc.startswith(
        ("latin-1-", "iso-8859-1-", "iso-latin-1-")
    ):
        return "iso-8859-1"
    return orig_enc


def detect_encoding(readline):
    "\n    The detect_encoding() function is used to detect the encoding that should\n    be used to decode a Python source file. It requires one argument, readline,\n    in the same way as the tokenize() generator.\n\n    It will call readline a maximum of twice, and return the encoding used\n    (as a string) and a list of any lines (left as bytes) it has read\n    in.\n\n    It detects the encoding from the presence of a utf-8 bom or an encoding\n    cookie as specified in pep-0263. If both a bom and a cookie are present, but\n    disagree, a SyntaxError will be raised. If the encoding cookie is an invalid\n    charset, raise a SyntaxError.  Note that if a utf-8 bom is found,\n    'utf-8-sig' is returned.\n\n    If no encoding is specified, then the default of 'utf-8' will be returned.\n    "
    bom_found = False
    encoding = None
    default = "utf-8"

    def read_or_stop():
        try:
            return readline()
        except StopIteration:
            return bytes()

    def find_cookie(line):
        try:
            line_string = line.decode("ascii")
        except UnicodeDecodeError:
            return None
        match = cookie_re.match(line_string)
        if not match:
            return None
        encoding = _get_normal_name(match.group(1))
        try:
            codec = lookup(encoding)
        except LookupError:
            raise SyntaxError(("unknown encoding: " + encoding))
        if bom_found:
            if codec.name != "utf-8":
                raise SyntaxError("encoding problem: utf-8")
            encoding += "-sig"
        return encoding

    first = read_or_stop()
    if first.startswith(BOM_UTF8):
        bom_found = True
        first = first[3:]
        default = "utf-8-sig"
    if not first:
        return (default, [])
    encoding = find_cookie(first)
    if encoding:
        return (encoding, [first])
    if not blank_re.match(first):
        return (default, [first])
    second = read_or_stop()
    if not second:
        return (default, [first])
    encoding = find_cookie(second)
    if encoding:
        return (encoding, [first, second])
    return (default, [first, second])


def untokenize(iterable):
    "Transform tokens back into Python source code.\n\n    Each element returned by the iterable must be a token sequence\n    with at least two elements, a token number and token value.  If\n    only two tokens are passed, the resulting output is poor.\n\n    Round-trip invariant for full input:\n        Untokenized source will match input source exactly\n\n    Round-trip invariant for limited input:\n        # Output text will tokenize the back to the input\n        t1 = [tok[:2] for tok in generate_tokens(f.readline)]\n        newcode = untokenize(t1)\n        readline = iter(newcode.splitlines(1)).next\n        t2 = [tok[:2] for tokin generate_tokens(readline)]\n        assert t1 == t2\n    "
    ut = Untokenizer()
    return ut.untokenize(iterable)


def generate_tokens(readline):
    "\n    The generate_tokens() generator requires one argument, readline, which\n    must be a callable object which provides the same interface as the\n    readline() method of built-in file objects. Each call to the function\n    should return one line of input as a string.  Alternately, readline\n    can be a callable function terminating with StopIteration:\n        readline = open(myfile).next    # Example of alternate readline\n\n    The generator produces 5-tuples with these members: the token type; the\n    token string; a 2-tuple (srow, scol) of ints specifying the row and\n    column where the token begins in the source; a 2-tuple (erow, ecol) of\n    ints specifying the row and column where the token ends in the source;\n    and the line on which the token was found. The line passed is the\n    physical line.\n    "
    lnum = parenlev = continued = 0
    (contstr, needcont) = ("", 0)
    contline = None
    indents = [0]
    stashed = None
    async_def = False
    async_def_indent = 0
    async_def_nl = False
    while 1:
        try:
            line = readline()
        except StopIteration:
            line = ""
        lnum = lnum + 1
        (pos, max) = (0, len(line))
        if contstr:
            if not line:
                raise TokenError("EOF in multi-line string", strstart)
            endmatch = endprog.match(line)
            if endmatch:
                pos = end = endmatch.end(0)
                (
                    yield (
                        STRING,
                        (contstr + line[:end]),
                        strstart,
                        (lnum, end),
                        (contline + line),
                    )
                )
                (contstr, needcont) = ("", 0)
                contline = None
            elif needcont and (line[(-2):] != "\\\n") and (line[(-3):] != "\\\r\n"):
                (
                    yield (
                        ERRORTOKEN,
                        (contstr + line),
                        strstart,
                        (lnum, len(line)),
                        contline,
                    )
                )
                contstr = ""
                contline = None
                continue
            else:
                contstr = contstr + line
                contline = contline + line
                continue
        elif (parenlev == 0) and (not continued):
            if not line:
                break
            column = 0
            while pos < max:
                if line[pos] == " ":
                    column = column + 1
                elif line[pos] == "\t":
                    column = ((column // tabsize) + 1) * tabsize
                elif line[pos] == "\x0c":
                    column = 0
                else:
                    break
                pos = pos + 1
            if pos == max:
                break
            if stashed:
                (yield stashed)
                stashed = None
            if line[pos] in "#\r\n":
                if line[pos] == "#":
                    comment_token = line[pos:].rstrip("\r\n")
                    nl_pos = pos + len(comment_token)
                    (
                        yield (
                            COMMENT,
                            comment_token,
                            (lnum, pos),
                            (lnum, (pos + len(comment_token))),
                            line,
                        )
                    )
                    (yield (NL, line[nl_pos:], (lnum, nl_pos), (lnum, len(line)), line))
                else:
                    (
                        yield (
                            (NL, COMMENT)[(line[pos] == "#")],
                            line[pos:],
                            (lnum, pos),
                            (lnum, len(line)),
                            line,
                        )
                    )
                continue
            if column > indents[(-1)]:
                indents.append(column)
                (yield (INDENT, line[:pos], (lnum, 0), (lnum, pos), line))
            while column < indents[(-1)]:
                if column not in indents:
                    raise IndentationError(
                        "unindent does not match any outer indentation level",
                        ("<tokenize>", lnum, pos, line),
                    )
                indents = indents[:(-1)]
                if async_def and (async_def_indent >= indents[(-1)]):
                    async_def = False
                    async_def_nl = False
                    async_def_indent = 0
                (yield (DEDENT, "", (lnum, pos), (lnum, pos), line))
            if async_def and async_def_nl and (async_def_indent >= indents[(-1)]):
                async_def = False
                async_def_nl = False
                async_def_indent = 0
        else:
            if not line:
                raise TokenError("EOF in multi-line statement", (lnum, 0))
            continued = 0
        while pos < max:
            pseudomatch = pseudoprog.match(line, pos)
            if pseudomatch:
                (start, end) = pseudomatch.span(1)
                (spos, epos, pos) = ((lnum, start), (lnum, end), end)
                (token, initial) = (line[start:end], line[start])
                if (initial in string.digits) or ((initial == ".") and (token != ".")):
                    (yield (NUMBER, token, spos, epos, line))
                elif initial in "\r\n":
                    newline = NEWLINE
                    if parenlev > 0:
                        newline = NL
                    elif async_def:
                        async_def_nl = True
                    if stashed:
                        (yield stashed)
                        stashed = None
                    (yield (newline, token, spos, epos, line))
                elif initial == "#":
                    assert not token.endswith("\n")
                    if stashed:
                        (yield stashed)
                        stashed = None
                    (yield (COMMENT, token, spos, epos, line))
                elif token in triple_quoted:
                    endprog = endprogs[token]
                    endmatch = endprog.match(line, pos)
                    if endmatch:
                        pos = endmatch.end(0)
                        token = line[start:pos]
                        if stashed:
                            (yield stashed)
                            stashed = None
                        (yield (STRING, token, spos, (lnum, pos), line))
                    else:
                        strstart = (lnum, start)
                        contstr = line[start:]
                        contline = line
                        break
                elif (
                    (initial in single_quoted)
                    or (token[:2] in single_quoted)
                    or (token[:3] in single_quoted)
                ):
                    if token[(-1)] == "\n":
                        strstart = (lnum, start)
                        endprog = (
                            endprogs[initial]
                            or endprogs[token[1]]
                            or endprogs[token[2]]
                        )
                        (contstr, needcont) = (line[start:], 1)
                        contline = line
                        break
                    else:
                        if stashed:
                            (yield stashed)
                            stashed = None
                        (yield (STRING, token, spos, epos, line))
                elif initial.isidentifier():
                    if token in ("async", "await"):
                        if async_def:
                            (
                                yield (
                                    (ASYNC if (token == "async") else AWAIT),
                                    token,
                                    spos,
                                    epos,
                                    line,
                                )
                            )
                            continue
                    tok = (NAME, token, spos, epos, line)
                    if (token == "async") and (not stashed):
                        stashed = tok
                        continue
                    if token == "def":
                        if stashed and (stashed[0] == NAME) and (stashed[1] == "async"):
                            async_def = True
                            async_def_indent = indents[(-1)]
                            (
                                yield (
                                    ASYNC,
                                    stashed[1],
                                    stashed[2],
                                    stashed[3],
                                    stashed[4],
                                )
                            )
                            stashed = None
                    if stashed:
                        (yield stashed)
                        stashed = None
                    (yield tok)
                elif initial == "\\":
                    if stashed:
                        (yield stashed)
                        stashed = None
                    (yield (NL, token, spos, (lnum, pos), line))
                    continued = 1
                else:
                    if initial in "([{":
                        parenlev = parenlev + 1
                    elif initial in ")]}":
                        parenlev = parenlev - 1
                    if stashed:
                        (yield stashed)
                        stashed = None
                    (yield (OP, token, spos, epos, line))
            else:
                (yield (ERRORTOKEN, line[pos], (lnum, pos), (lnum, (pos + 1)), line))
                pos = pos + 1
    if stashed:
        (yield stashed)
        stashed = None
    for indent in indents[1:]:
        (yield (DEDENT, "", (lnum, 0), (lnum, 0), ""))
    (yield (ENDMARKER, "", (lnum, 0), (lnum, 0), ""))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        tokenize(open(sys.argv[1]).readline)
    else:
        tokenize(sys.stdin.readline)
