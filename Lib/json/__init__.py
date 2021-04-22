"JSON (JavaScript Object Notation) <http://json.org> is a subset of\nJavaScript syntax (ECMA-262 3rd edition) used as a lightweight data\ninterchange format.\n\n:mod:`json` exposes an API familiar to users of the standard library\n:mod:`marshal` and :mod:`pickle` modules.  It is derived from a\nversion of the externally maintained simplejson library.\n\nEncoding basic Python object hierarchies::\n\n    >>> import json\n    >>> json.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])\n    '[\"foo\", {\"bar\": [\"baz\", null, 1.0, 2]}]'\n    >>> print(json.dumps(\"\\\"foo\\bar\"))\n    \"\\\"foo\\bar\"\n    >>> print(json.dumps('\\u1234'))\n    \"\\u1234\"\n    >>> print(json.dumps('\\\\'))\n    \"\\\\\"\n    >>> print(json.dumps({\"c\": 0, \"b\": 0, \"a\": 0}, sort_keys=True))\n    {\"a\": 0, \"b\": 0, \"c\": 0}\n    >>> from io import StringIO\n    >>> io = StringIO()\n    >>> json.dump(['streaming API'], io)\n    >>> io.getvalue()\n    '[\"streaming API\"]'\n\nCompact encoding::\n\n    >>> import json\n    >>> mydict = {'4': 5, '6': 7}\n    >>> json.dumps([1,2,3,mydict], separators=(',', ':'))\n    '[1,2,3,{\"4\":5,\"6\":7}]'\n\nPretty printing::\n\n    >>> import json\n    >>> print(json.dumps({'4': 5, '6': 7}, sort_keys=True, indent=4))\n    {\n        \"4\": 5,\n        \"6\": 7\n    }\n\nDecoding JSON::\n\n    >>> import json\n    >>> obj = ['foo', {'bar': ['baz', None, 1.0, 2]}]\n    >>> json.loads('[\"foo\", {\"bar\":[\"baz\", null, 1.0, 2]}]') == obj\n    True\n    >>> json.loads('\"\\\\\"foo\\\\bar\"') == '\"foo\\x08ar'\n    True\n    >>> from io import StringIO\n    >>> io = StringIO('[\"streaming API\"]')\n    >>> json.load(io)[0] == 'streaming API'\n    True\n\nSpecializing JSON object decoding::\n\n    >>> import json\n    >>> def as_complex(dct):\n    ...     if '__complex__' in dct:\n    ...         return complex(dct['real'], dct['imag'])\n    ...     return dct\n    ...\n    >>> json.loads('{\"__complex__\": true, \"real\": 1, \"imag\": 2}',\n    ...     object_hook=as_complex)\n    (1+2j)\n    >>> from decimal import Decimal\n    >>> json.loads('1.1', parse_float=Decimal) == Decimal('1.1')\n    True\n\nSpecializing JSON object encoding::\n\n    >>> import json\n    >>> def encode_complex(obj):\n    ...     if isinstance(obj, complex):\n    ...         return [obj.real, obj.imag]\n    ...     raise TypeError(f'Object of type {obj.__class__.__name__} '\n    ...                     f'is not JSON serializable')\n    ...\n    >>> json.dumps(2 + 1j, default=encode_complex)\n    '[2.0, 1.0]'\n    >>> json.JSONEncoder(default=encode_complex).encode(2 + 1j)\n    '[2.0, 1.0]'\n    >>> ''.join(json.JSONEncoder(default=encode_complex).iterencode(2 + 1j))\n    '[2.0, 1.0]'\n\n\nUsing json.tool from the shell to validate and pretty-print::\n\n    $ echo '{\"json\":\"obj\"}' | python -m json.tool\n    {\n        \"json\": \"obj\"\n    }\n    $ echo '{ 1.2:3.4}' | python -m json.tool\n    Expecting property name enclosed in double quotes: line 1 column 3 (char 2)\n"
__version__ = "2.0.9"
__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
    "JSONDecoder",
    "JSONDecodeError",
    "JSONEncoder",
]
__author__ = "Bob Ippolito <bob@redivi.com>"
from .decoder import JSONDecoder, JSONDecodeError
from .encoder import JSONEncoder
import codecs

_default_encoder = JSONEncoder(
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    indent=None,
    separators=None,
    default=None,
)


def dump(
    obj,
    fp,
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    "Serialize ``obj`` as a JSON formatted stream to ``fp`` (a\n    ``.write()``-supporting file-like object).\n\n    If ``skipkeys`` is true then ``dict`` keys that are not basic types\n    (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped\n    instead of raising a ``TypeError``.\n\n    If ``ensure_ascii`` is false, then the strings written to ``fp`` can\n    contain non-ASCII characters if they appear in strings contained in\n    ``obj``. Otherwise, all such characters are escaped in JSON strings.\n\n    If ``check_circular`` is false, then the circular reference check\n    for container types will be skipped and a circular reference will\n    result in an ``OverflowError`` (or worse).\n\n    If ``allow_nan`` is false, then it will be a ``ValueError`` to\n    serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``)\n    in strict compliance of the JSON specification, instead of using the\n    JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).\n\n    If ``indent`` is a non-negative integer, then JSON array elements and\n    object members will be pretty-printed with that indent level. An indent\n    level of 0 will only insert newlines. ``None`` is the most compact\n    representation.\n\n    If specified, ``separators`` should be an ``(item_separator, key_separator)``\n    tuple.  The default is ``(', ', ': ')`` if *indent* is ``None`` and\n    ``(',', ': ')`` otherwise.  To get the most compact JSON representation,\n    you should specify ``(',', ':')`` to eliminate whitespace.\n\n    ``default(obj)`` is a function that should return a serializable version\n    of obj or raise TypeError. The default simply raises TypeError.\n\n    If *sort_keys* is true (default: ``False``), then the output of\n    dictionaries will be sorted by key.\n\n    To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the\n    ``.default()`` method to serialize additional types), specify it with\n    the ``cls`` kwarg; otherwise ``JSONEncoder`` is used.\n\n    "
    if (
        (not skipkeys)
        and ensure_ascii
        and check_circular
        and allow_nan
        and (cls is None)
        and (indent is None)
        and (separators is None)
        and (default is None)
        and (not sort_keys)
        and (not kw)
    ):
        iterable = _default_encoder.iterencode(obj)
    else:
        if cls is None:
            cls = JSONEncoder
        iterable = cls(
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        ).iterencode(obj)
    for chunk in iterable:
        fp.write(chunk)


def dumps(
    obj,
    *,
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    cls=None,
    indent=None,
    separators=None,
    default=None,
    sort_keys=False,
    **kw,
):
    "Serialize ``obj`` to a JSON formatted ``str``.\n\n    If ``skipkeys`` is true then ``dict`` keys that are not basic types\n    (``str``, ``int``, ``float``, ``bool``, ``None``) will be skipped\n    instead of raising a ``TypeError``.\n\n    If ``ensure_ascii`` is false, then the return value can contain non-ASCII\n    characters if they appear in strings contained in ``obj``. Otherwise, all\n    such characters are escaped in JSON strings.\n\n    If ``check_circular`` is false, then the circular reference check\n    for container types will be skipped and a circular reference will\n    result in an ``OverflowError`` (or worse).\n\n    If ``allow_nan`` is false, then it will be a ``ValueError`` to\n    serialize out of range ``float`` values (``nan``, ``inf``, ``-inf``) in\n    strict compliance of the JSON specification, instead of using the\n    JavaScript equivalents (``NaN``, ``Infinity``, ``-Infinity``).\n\n    If ``indent`` is a non-negative integer, then JSON array elements and\n    object members will be pretty-printed with that indent level. An indent\n    level of 0 will only insert newlines. ``None`` is the most compact\n    representation.\n\n    If specified, ``separators`` should be an ``(item_separator, key_separator)``\n    tuple.  The default is ``(', ', ': ')`` if *indent* is ``None`` and\n    ``(',', ': ')`` otherwise.  To get the most compact JSON representation,\n    you should specify ``(',', ':')`` to eliminate whitespace.\n\n    ``default(obj)`` is a function that should return a serializable version\n    of obj or raise TypeError. The default simply raises TypeError.\n\n    If *sort_keys* is true (default: ``False``), then the output of\n    dictionaries will be sorted by key.\n\n    To use a custom ``JSONEncoder`` subclass (e.g. one that overrides the\n    ``.default()`` method to serialize additional types), specify it with\n    the ``cls`` kwarg; otherwise ``JSONEncoder`` is used.\n\n    "
    if (
        (not skipkeys)
        and ensure_ascii
        and check_circular
        and allow_nan
        and (cls is None)
        and (indent is None)
        and (separators is None)
        and (default is None)
        and (not sort_keys)
        and (not kw)
    ):
        return _default_encoder.encode(obj)
    if cls is None:
        cls = JSONEncoder
    return cls(
        skipkeys=skipkeys,
        ensure_ascii=ensure_ascii,
        check_circular=check_circular,
        allow_nan=allow_nan,
        indent=indent,
        separators=separators,
        default=default,
        sort_keys=sort_keys,
        **kw,
    ).encode(obj)


_default_decoder = JSONDecoder(object_hook=None, object_pairs_hook=None)


def detect_encoding(b):
    bstartswith = b.startswith
    if bstartswith((codecs.BOM_UTF32_BE, codecs.BOM_UTF32_LE)):
        return "utf-32"
    if bstartswith((codecs.BOM_UTF16_BE, codecs.BOM_UTF16_LE)):
        return "utf-16"
    if bstartswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if len(b) >= 4:
        if not b[0]:
            return "utf-16-be" if b[1] else "utf-32-be"
        if not b[1]:
            return "utf-16-le" if (b[2] or b[3]) else "utf-32-le"
    elif len(b) == 2:
        if not b[0]:
            return "utf-16-be"
        if not b[1]:
            return "utf-16-le"
    return "utf-8"


def load(
    fp,
    *,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    **kw,
):
    "Deserialize ``fp`` (a ``.read()``-supporting file-like object containing\n    a JSON document) to a Python object.\n\n    ``object_hook`` is an optional function that will be called with the\n    result of any object literal decode (a ``dict``). The return value of\n    ``object_hook`` will be used instead of the ``dict``. This feature\n    can be used to implement custom decoders (e.g. JSON-RPC class hinting).\n\n    ``object_pairs_hook`` is an optional function that will be called with the\n    result of any object literal decoded with an ordered list of pairs.  The\n    return value of ``object_pairs_hook`` will be used instead of the ``dict``.\n    This feature can be used to implement custom decoders.  If ``object_hook``\n    is also defined, the ``object_pairs_hook`` takes priority.\n\n    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``\n    kwarg; otherwise ``JSONDecoder`` is used.\n    "
    return loads(
        fp.read(),
        cls=cls,
        object_hook=object_hook,
        parse_float=parse_float,
        parse_int=parse_int,
        parse_constant=parse_constant,
        object_pairs_hook=object_pairs_hook,
        **kw,
    )


def loads(
    s,
    *,
    cls=None,
    object_hook=None,
    parse_float=None,
    parse_int=None,
    parse_constant=None,
    object_pairs_hook=None,
    **kw,
):
    "Deserialize ``s`` (a ``str``, ``bytes`` or ``bytearray`` instance\n    containing a JSON document) to a Python object.\n\n    ``object_hook`` is an optional function that will be called with the\n    result of any object literal decode (a ``dict``). The return value of\n    ``object_hook`` will be used instead of the ``dict``. This feature\n    can be used to implement custom decoders (e.g. JSON-RPC class hinting).\n\n    ``object_pairs_hook`` is an optional function that will be called with the\n    result of any object literal decoded with an ordered list of pairs.  The\n    return value of ``object_pairs_hook`` will be used instead of the ``dict``.\n    This feature can be used to implement custom decoders.  If ``object_hook``\n    is also defined, the ``object_pairs_hook`` takes priority.\n\n    ``parse_float``, if specified, will be called with the string\n    of every JSON float to be decoded. By default this is equivalent to\n    float(num_str). This can be used to use another datatype or parser\n    for JSON floats (e.g. decimal.Decimal).\n\n    ``parse_int``, if specified, will be called with the string\n    of every JSON int to be decoded. By default this is equivalent to\n    int(num_str). This can be used to use another datatype or parser\n    for JSON integers (e.g. float).\n\n    ``parse_constant``, if specified, will be called with one of the\n    following strings: -Infinity, Infinity, NaN.\n    This can be used to raise an exception if invalid JSON numbers\n    are encountered.\n\n    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``\n    kwarg; otherwise ``JSONDecoder`` is used.\n    "
    if isinstance(s, str):
        if s.startswith("\ufeff"):
            raise JSONDecodeError("Unexpected UTF-8 BOM (decode using utf-8-sig)", s, 0)
    else:
        if not isinstance(s, (bytes, bytearray)):
            raise TypeError(
                f"the JSON object must be str, bytes or bytearray, not {s.__class__.__name__}"
            )
        s = s.decode(detect_encoding(s), "surrogatepass")
    if (
        (cls is None)
        and (object_hook is None)
        and (parse_int is None)
        and (parse_float is None)
        and (parse_constant is None)
        and (object_pairs_hook is None)
        and (not kw)
    ):
        return _default_decoder.decode(s)
    if cls is None:
        cls = JSONDecoder
    if object_hook is not None:
        kw["object_hook"] = object_hook
    if object_pairs_hook is not None:
        kw["object_pairs_hook"] = object_pairs_hook
    if parse_float is not None:
        kw["parse_float"] = parse_float
    if parse_int is not None:
        kw["parse_int"] = parse_int
    if parse_constant is not None:
        kw["parse_constant"] = parse_constant
    return cls(**kw).decode(s)
