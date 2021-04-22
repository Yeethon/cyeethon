" Routines for manipulating RFC2047 encoded words.\n\nThis is currently a package-private API, but will be considered for promotion\nto a public API if there is demand.\n\n"
import re
import base64
import binascii
import functools
from string import ascii_letters, digits
from email import errors

__all__ = [
    "decode_q",
    "encode_q",
    "decode_b",
    "encode_b",
    "len_q",
    "len_b",
    "decode",
    "encode",
]
_q_byte_subber = functools.partial(
    re.compile(b"=([a-fA-F0-9]{2})").sub, (lambda m: bytes.fromhex(m.group(1).decode()))
)


def decode_q(encoded):
    encoded = encoded.replace(b"_", b" ")
    return (_q_byte_subber(encoded), [])


class _QByteMap(dict):
    safe = (b"-!*+/" + ascii_letters.encode("ascii")) + digits.encode("ascii")

    def __missing__(self, key):
        if key in self.safe:
            self[key] = chr(key)
        else:
            self[key] = "={:02X}".format(key)
        return self[key]


_q_byte_map = _QByteMap()
_q_byte_map[ord(" ")] = "_"


def encode_q(bstring):
    return "".join((_q_byte_map[x] for x in bstring))


def len_q(bstring):
    return sum((len(_q_byte_map[x]) for x in bstring))


def decode_b(encoded):
    pad_err = len(encoded) % 4
    missing_padding = b"==="[: (4 - pad_err)] if pad_err else b""
    try:
        return (
            base64.b64decode((encoded + missing_padding), validate=True),
            ([errors.InvalidBase64PaddingDefect()] if pad_err else []),
        )
    except binascii.Error:
        try:
            return (
                base64.b64decode(encoded, validate=False),
                [errors.InvalidBase64CharactersDefect()],
            )
        except binascii.Error:
            try:
                return (
                    base64.b64decode((encoded + b"=="), validate=False),
                    [
                        errors.InvalidBase64CharactersDefect(),
                        errors.InvalidBase64PaddingDefect(),
                    ],
                )
            except binascii.Error:
                return (encoded, [errors.InvalidBase64LengthDefect()])


def encode_b(bstring):
    return base64.b64encode(bstring).decode("ascii")


def len_b(bstring):
    (groups_of_3, leftover) = divmod(len(bstring), 3)
    return (groups_of_3 * 4) + (4 if leftover else 0)


_cte_decoders = {"q": decode_q, "b": decode_b}


def decode(ew):
    "Decode encoded word and return (string, charset, lang, defects) tuple.\n\n    An RFC 2047/2243 encoded word has the form:\n\n        =?charset*lang?cte?encoded_string?=\n\n    where '*lang' may be omitted but the other parts may not be.\n\n    This function expects exactly such a string (that is, it does not check the\n    syntax and may raise errors if the string is not well formed), and returns\n    the encoded_string decoded first from its Content Transfer Encoding and\n    then from the resulting bytes into unicode using the specified charset.  If\n    the cte-decoded string does not successfully decode using the specified\n    character set, a defect is added to the defects list and the unknown octets\n    are replaced by the unicode 'unknown' character \\uFDFF.\n\n    The specified charset and language are returned.  The default for language,\n    which is rarely if ever encountered, is the empty string.\n\n    "
    (_, charset, cte, cte_string, _) = ew.split("?")
    (charset, _, lang) = charset.partition("*")
    cte = cte.lower()
    bstring = cte_string.encode("ascii", "surrogateescape")
    (bstring, defects) = _cte_decoders[cte](bstring)
    try:
        string = bstring.decode(charset)
    except UnicodeError:
        defects.append(
            errors.UndecodableBytesDefect(
                "Encoded word contains bytes not decodable using {} charset".format(
                    charset
                )
            )
        )
        string = bstring.decode(charset, "surrogateescape")
    except LookupError:
        string = bstring.decode("ascii", "surrogateescape")
        if charset.lower() != "unknown-8bit":
            defects.append(
                errors.CharsetError(
                    "Unknown charset {} in encoded word; decoded as unknown bytes".format(
                        charset
                    )
                )
            )
    return (string, charset, lang, defects)


_cte_encoders = {"q": encode_q, "b": encode_b}
_cte_encode_length = {"q": len_q, "b": len_b}


def encode(string, charset="utf-8", encoding=None, lang=""):
    "Encode string using the CTE encoding that produces the shorter result.\n\n    Produces an RFC 2047/2243 encoded word of the form:\n\n        =?charset*lang?cte?encoded_string?=\n\n    where '*lang' is omitted unless the 'lang' parameter is given a value.\n    Optional argument charset (defaults to utf-8) specifies the charset to use\n    to encode the string to binary before CTE encoding it.  Optional argument\n    'encoding' is the cte specifier for the encoding that should be used ('q'\n    or 'b'); if it is None (the default) the encoding which produces the\n    shortest encoded sequence is used, except that 'q' is preferred if it is up\n    to five characters longer.  Optional argument 'lang' (default '') gives the\n    RFC 2243 language string to specify in the encoded word.\n\n    "
    if charset == "unknown-8bit":
        bstring = string.encode("ascii", "surrogateescape")
    else:
        bstring = string.encode(charset)
    if encoding is None:
        qlen = _cte_encode_length["q"](bstring)
        blen = _cte_encode_length["b"](bstring)
        encoding = "q" if ((qlen - blen) < 5) else "b"
    encoded = _cte_encoders[encoding](bstring)
    if lang:
        lang = "*" + lang
    return "=?{}{}?{}?{}?=".format(charset, lang, encoding, encoded)
