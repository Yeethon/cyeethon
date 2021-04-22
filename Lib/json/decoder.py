"Implementation of JSONDecoder\n"
import re
from json import scanner

try:
    from _json import scanstring as c_scanstring
except ImportError:
    c_scanstring = None
__all__ = ["JSONDecoder", "JSONDecodeError"]
FLAGS = (re.VERBOSE | re.MULTILINE) | re.DOTALL
NaN = float("nan")
PosInf = float("inf")
NegInf = float("-inf")


class JSONDecodeError(ValueError):
    "Subclass of ValueError with the following additional properties:\n\n    msg: The unformatted error message\n    doc: The JSON document being parsed\n    pos: The start index of doc where parsing failed\n    lineno: The line corresponding to pos\n    colno: The column corresponding to pos\n\n    "

    def __init__(self, msg, doc, pos):
        lineno = doc.count("\n", 0, pos) + 1
        colno = pos - doc.rfind("\n", 0, pos)
        errmsg = "%s: line %d column %d (char %d)" % (msg, lineno, colno, pos)
        ValueError.__init__(self, errmsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = lineno
        self.colno = colno

    def __reduce__(self):
        return (self.__class__, (self.msg, self.doc, self.pos))


_CONSTANTS = {"-Infinity": NegInf, "Infinity": PosInf, "NaN": NaN}
STRINGCHUNK = re.compile('(.*?)(["\\\\\\x00-\\x1f])', FLAGS)
BACKSLASH = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "b": "\x08",
    "f": "\x0c",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def _decode_uXXXX(s, pos):
    esc = s[(pos + 1) : (pos + 5)]
    if (len(esc) == 4) and (esc[1] not in "xX"):
        try:
            return int(esc, 16)
        except ValueError:
            pass
    msg = "Invalid \\uXXXX escape"
    raise JSONDecodeError(msg, s, pos)


def py_scanstring(s, end, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    "Scan the string s for a JSON string. End is the index of the\n    character in s after the quote that started the JSON string.\n    Unescapes all valid JSON string escape sequences and raises ValueError\n    on attempt to decode an invalid string. If strict is False then literal\n    control characters are allowed in the string.\n\n    Returns a tuple of the decoded string and the index of the character in s\n    after the end quote."
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise JSONDecodeError("Unterminated string starting at", s, begin)
        end = chunk.end()
        (content, terminator) = chunk.groups()
        if content:
            _append(content)
        if terminator == '"':
            break
        elif terminator != "\\":
            if strict:
                msg = "Invalid control character {0!r} at".format(terminator)
                raise JSONDecodeError(msg, s, end)
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise JSONDecodeError("Unterminated string starting at", s, begin) from None
        if esc != "u":
            try:
                char = _b[esc]
            except KeyError:
                msg = "Invalid \\escape: {0!r}".format(esc)
                raise JSONDecodeError(msg, s, end)
            end += 1
        else:
            uni = _decode_uXXXX(s, end)
            end += 5
            if (55296 <= uni <= 56319) and (s[end : (end + 2)] == "\\u"):
                uni2 = _decode_uXXXX(s, (end + 1))
                if 56320 <= uni2 <= 57343:
                    uni = 65536 + (((uni - 55296) << 10) | (uni2 - 56320))
                    end += 6
            char = chr(uni)
        _append(char)
    return ("".join(chunks), end)


scanstring = c_scanstring or py_scanstring
WHITESPACE = re.compile("[ \\t\\n\\r]*", FLAGS)
WHITESPACE_STR = " \t\n\r"


def JSONObject(
    s_and_end,
    strict,
    scan_once,
    object_hook,
    object_pairs_hook,
    memo=None,
    _w=WHITESPACE.match,
    _ws=WHITESPACE_STR,
):
    (s, end) = s_and_end
    pairs = []
    pairs_append = pairs.append
    if memo is None:
        memo = {}
    memo_get = memo.setdefault
    nextchar = s[end : (end + 1)]
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end : (end + 1)]
        if nextchar == "}":
            if object_pairs_hook is not None:
                result = object_pairs_hook(pairs)
                return (result, (end + 1))
            pairs = {}
            if object_hook is not None:
                pairs = object_hook(pairs)
            return (pairs, (end + 1))
        elif nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes", s, end
            )
    end += 1
    while True:
        (key, end) = scanstring(s, end, strict)
        key = memo_get(key, key)
        if s[end : (end + 1)] != ":":
            end = _w(s, end).end()
            if s[end : (end + 1)] != ":":
                raise JSONDecodeError("Expecting ':' delimiter", s, end)
        end += 1
        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, (end + 1)).end()
        except IndexError:
            pass
        try:
            (value, end) = scan_once(s, end)
        except StopIteration as err:
            raise JSONDecodeError("Expecting value", s, err.value) from None
        pairs_append((key, value))
        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, (end + 1)).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ""
        end += 1
        if nextchar == "}":
            break
        elif nextchar != ",":
            raise JSONDecodeError("Expecting ',' delimiter", s, (end - 1))
        end = _w(s, end).end()
        nextchar = s[end : (end + 1)]
        end += 1
        if nextchar != '"':
            raise JSONDecodeError(
                "Expecting property name enclosed in double quotes", s, (end - 1)
            )
    if object_pairs_hook is not None:
        result = object_pairs_hook(pairs)
        return (result, end)
    pairs = dict(pairs)
    if object_hook is not None:
        pairs = object_hook(pairs)
    return (pairs, end)


def JSONArray(s_and_end, scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    (s, end) = s_and_end
    values = []
    nextchar = s[end : (end + 1)]
    if nextchar in _ws:
        end = _w(s, (end + 1)).end()
        nextchar = s[end : (end + 1)]
    if nextchar == "]":
        return (values, (end + 1))
    _append = values.append
    while True:
        try:
            (value, end) = scan_once(s, end)
        except StopIteration as err:
            raise JSONDecodeError("Expecting value", s, err.value) from None
        _append(value)
        nextchar = s[end : (end + 1)]
        if nextchar in _ws:
            end = _w(s, (end + 1)).end()
            nextchar = s[end : (end + 1)]
        end += 1
        if nextchar == "]":
            break
        elif nextchar != ",":
            raise JSONDecodeError("Expecting ',' delimiter", s, (end - 1))
        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, (end + 1)).end()
        except IndexError:
            pass
    return (values, end)


class JSONDecoder(object):
    "Simple JSON <http://json.org> decoder\n\n    Performs the following translations in decoding by default:\n\n    +---------------+-------------------+\n    | JSON          | Python            |\n    +===============+===================+\n    | object        | dict              |\n    +---------------+-------------------+\n    | array         | list              |\n    +---------------+-------------------+\n    | string        | str               |\n    +---------------+-------------------+\n    | number (int)  | int               |\n    +---------------+-------------------+\n    | number (real) | float             |\n    +---------------+-------------------+\n    | true          | True              |\n    +---------------+-------------------+\n    | false         | False             |\n    +---------------+-------------------+\n    | null          | None              |\n    +---------------+-------------------+\n\n    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as\n    their corresponding ``float`` values, which is outside the JSON spec.\n\n    "

    def __init__(
        self,
        *,
        object_hook=None,
        parse_float=None,
        parse_int=None,
        parse_constant=None,
        strict=True,
        object_pairs_hook=None
    ):
        "``object_hook``, if specified, will be called with the result\n        of every JSON object decoded and its return value will be used in\n        place of the given ``dict``.  This can be used to provide custom\n        deserializations (e.g. to support JSON-RPC class hinting).\n\n        ``object_pairs_hook``, if specified will be called with the result of\n        every JSON object decoded with an ordered list of pairs.  The return\n        value of ``object_pairs_hook`` will be used instead of the ``dict``.\n        This feature can be used to implement custom decoders.\n        If ``object_hook`` is also defined, the ``object_pairs_hook`` takes\n        priority.\n\n        ``parse_float``, if specified, will be called with the string\n        of every JSON float to be decoded. By default this is equivalent to\n        float(num_str). This can be used to use another datatype or parser\n        for JSON floats (e.g. decimal.Decimal).\n\n        ``parse_int``, if specified, will be called with the string\n        of every JSON int to be decoded. By default this is equivalent to\n        int(num_str). This can be used to use another datatype or parser\n        for JSON integers (e.g. float).\n\n        ``parse_constant``, if specified, will be called with one of the\n        following strings: -Infinity, Infinity, NaN.\n        This can be used to raise an exception if invalid JSON numbers\n        are encountered.\n\n        If ``strict`` is false (true is the default), then control\n        characters will be allowed inside strings.  Control characters in\n        this context are those with character codes in the 0-31 range,\n        including ``'\\t'`` (tab), ``'\\n'``, ``'\\r'`` and ``'\\0'``.\n        "
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.object_pairs_hook = object_pairs_hook
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.memo = {}
        self.scan_once = scanner.make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        "Return the Python representation of ``s`` (a ``str`` instance\n        containing a JSON document).\n\n        "
        (obj, end) = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise JSONDecodeError("Extra data", s, end)
        return obj

    def raw_decode(self, s, idx=0):
        "Decode a JSON document from ``s`` (a ``str`` beginning with\n        a JSON document) and return a 2-tuple of the Python\n        representation and the index in ``s`` where the document ended.\n\n        This can be used to decode a JSON document from a string that may\n        have extraneous data at the end.\n\n        "
        try:
            (obj, end) = self.scan_once(s, idx)
        except StopIteration as err:
            raise JSONDecodeError("Expecting value", s, err.value) from None
        return (obj, end)
