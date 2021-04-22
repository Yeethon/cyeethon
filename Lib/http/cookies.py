'\nHere\'s a sample session to show how to use this module.\nAt the moment, this is the only documentation.\n\nThe Basics\n----------\n\nImporting is easy...\n\n   >>> from http import cookies\n\nMost of the time you start by creating a cookie.\n\n   >>> C = cookies.SimpleCookie()\n\nOnce you\'ve created your Cookie, you can add values just as if it were\na dictionary.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C["fig"] = "newton"\n   >>> C["sugar"] = "wafer"\n   >>> C.output()\n   \'Set-Cookie: fig=newton\\r\\nSet-Cookie: sugar=wafer\'\n\nNotice that the printable representation of a Cookie is the\nappropriate format for a Set-Cookie: header.  This is the\ndefault behavior.  You can change the header and printed\nattributes by using the .output() function\n\n   >>> C = cookies.SimpleCookie()\n   >>> C["rocky"] = "road"\n   >>> C["rocky"]["path"] = "/cookie"\n   >>> print(C.output(header="Cookie:"))\n   Cookie: rocky=road; Path=/cookie\n   >>> print(C.output(attrs=[], header="Cookie:"))\n   Cookie: rocky=road\n\nThe load() method of a Cookie extracts cookies from a string.  In a\nCGI script, you would use this method to extract the cookies from the\nHTTP_COOKIE environment variable.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C.load("chips=ahoy; vienna=finger")\n   >>> C.output()\n   \'Set-Cookie: chips=ahoy\\r\\nSet-Cookie: vienna=finger\'\n\nThe load() method is darn-tootin smart about identifying cookies\nwithin a string.  Escaped quotation marks, nested semicolons, and other\nsuch trickeries do not confuse it.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C.load(\'keebler="E=everybody; L=\\\\"Loves\\\\"; fudge=\\\\012;";\')\n   >>> print(C)\n   Set-Cookie: keebler="E=everybody; L=\\"Loves\\"; fudge=\\012;"\n\nEach element of the Cookie also supports all of the RFC 2109\nCookie attributes.  Here\'s an example which sets the Path\nattribute.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C["oreo"] = "doublestuff"\n   >>> C["oreo"]["path"] = "/"\n   >>> print(C)\n   Set-Cookie: oreo=doublestuff; Path=/\n\nEach dictionary element has a \'value\' attribute, which gives you\nback the value associated with the key.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C["twix"] = "none for you"\n   >>> C["twix"].value\n   \'none for you\'\n\nThe SimpleCookie expects that all values should be standard strings.\nJust to be sure, SimpleCookie invokes the str() builtin to convert\nthe value to a string, when the values are set dictionary-style.\n\n   >>> C = cookies.SimpleCookie()\n   >>> C["number"] = 7\n   >>> C["string"] = "seven"\n   >>> C["number"].value\n   \'7\'\n   >>> C["string"].value\n   \'seven\'\n   >>> C.output()\n   \'Set-Cookie: number=7\\r\\nSet-Cookie: string=seven\'\n\nFinis.\n'
import re
import string
import types

__all__ = ["CookieError", "BaseCookie", "SimpleCookie"]
_nulljoin = "".join
_semispacejoin = "; ".join
_spacejoin = " ".join


class CookieError(Exception):
    pass


_LegalChars = (string.ascii_letters + string.digits) + "!#$%&'*+-.^_`|~:"
_UnescapedChars = _LegalChars + " ()/<=>?@[]{}"
_Translator = {
    n: ("\\%03o" % n) for n in (set(range(256)) - set(map(ord, _UnescapedChars)))
}
_Translator.update({ord('"'): '\\"', ord("\\"): "\\\\"})
_is_legal_key = re.compile(("[%s]+" % re.escape(_LegalChars))).fullmatch


def _quote(str):
    "Quote a string for use in a cookie header.\n\n    If the string does not need to be double-quoted, then just return the\n    string.  Otherwise, surround the string in doublequotes and quote\n    (with a \\) special characters.\n    "
    if (str is None) or _is_legal_key(str):
        return str
    else:
        return ('"' + str.translate(_Translator)) + '"'


_OctalPatt = re.compile("\\\\[0-3][0-7][0-7]")
_QuotePatt = re.compile("[\\\\].")


def _unquote(str):
    if (str is None) or (len(str) < 2):
        return str
    if (str[0] != '"') or (str[(-1)] != '"'):
        return str
    str = str[1:(-1)]
    i = 0
    n = len(str)
    res = []
    while 0 <= i < n:
        o_match = _OctalPatt.search(str, i)
        q_match = _QuotePatt.search(str, i)
        if (not o_match) and (not q_match):
            res.append(str[i:])
            break
        j = k = -1
        if o_match:
            j = o_match.start(0)
        if q_match:
            k = q_match.start(0)
        if q_match and ((not o_match) or (k < j)):
            res.append(str[i:k])
            res.append(str[(k + 1)])
            i = k + 2
        else:
            res.append(str[i:j])
            res.append(chr(int(str[(j + 1) : (j + 4)], 8)))
            i = j + 4
    return _nulljoin(res)


_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [
    None,
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


def _getdate(future=0, weekdayname=_weekdayname, monthname=_monthname):
    from time import gmtime, time

    now = time()
    (year, month, day, hh, mm, ss, wd, y, z) = gmtime((now + future))
    return "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        weekdayname[wd],
        day,
        monthname[month],
        year,
        hh,
        mm,
        ss,
    )


class Morsel(dict):
    "A class to hold ONE (key, value) pair.\n\n    In a cookie, each such pair may have several attributes, so this class is\n    used to keep the attributes associated with the appropriate key,value pair.\n    This class also includes a coded_value attribute, which is used to hold\n    the network representation of the value.\n    "
    _reserved = {
        "expires": "expires",
        "path": "Path",
        "comment": "Comment",
        "domain": "Domain",
        "max-age": "Max-Age",
        "secure": "Secure",
        "httponly": "HttpOnly",
        "version": "Version",
        "samesite": "SameSite",
    }
    _flags = {"secure", "httponly"}

    def __init__(self):
        self._key = self._value = self._coded_value = None
        for key in self._reserved:
            dict.__setitem__(self, key, "")

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value

    @property
    def coded_value(self):
        return self._coded_value

    def __setitem__(self, K, V):
        K = K.lower()
        if not (K in self._reserved):
            raise CookieError(("Invalid attribute %r" % (K,)))
        dict.__setitem__(self, K, V)

    def setdefault(self, key, val=None):
        key = key.lower()
        if key not in self._reserved:
            raise CookieError(("Invalid attribute %r" % (key,)))
        return dict.setdefault(self, key, val)

    def __eq__(self, morsel):
        if not isinstance(morsel, Morsel):
            return NotImplemented
        return (
            dict.__eq__(self, morsel)
            and (self._value == morsel._value)
            and (self._key == morsel._key)
            and (self._coded_value == morsel._coded_value)
        )

    __ne__ = object.__ne__

    def copy(self):
        morsel = Morsel()
        dict.update(morsel, self)
        morsel.__dict__.update(self.__dict__)
        return morsel

    def update(self, values):
        data = {}
        for (key, val) in dict(values).items():
            key = key.lower()
            if key not in self._reserved:
                raise CookieError(("Invalid attribute %r" % (key,)))
            data[key] = val
        dict.update(self, data)

    def isReservedKey(self, K):
        return K.lower() in self._reserved

    def set(self, key, val, coded_val):
        if key.lower() in self._reserved:
            raise CookieError(("Attempt to set a reserved key %r" % (key,)))
        if not _is_legal_key(key):
            raise CookieError(("Illegal key %r" % (key,)))
        self._key = key
        self._value = val
        self._coded_value = coded_val

    def __getstate__(self):
        return {
            "key": self._key,
            "value": self._value,
            "coded_value": self._coded_value,
        }

    def __setstate__(self, state):
        self._key = state["key"]
        self._value = state["value"]
        self._coded_value = state["coded_value"]

    def output(self, attrs=None, header="Set-Cookie:"):
        return "%s %s" % (header, self.OutputString(attrs))

    __str__ = output

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.OutputString())

    def js_output(self, attrs=None):
        return '\n        <script type="text/javascript">\n        <!-- begin hiding\n        document.cookie = "%s";\n        // end hiding -->\n        </script>\n        ' % self.OutputString(
            attrs
        ).replace(
            '"', '\\"'
        )

    def OutputString(self, attrs=None):
        result = []
        append = result.append
        append(("%s=%s" % (self.key, self.coded_value)))
        if attrs is None:
            attrs = self._reserved
        items = sorted(self.items())
        for (key, value) in items:
            if value == "":
                continue
            if key not in attrs:
                continue
            if (key == "expires") and isinstance(value, int):
                append(("%s=%s" % (self._reserved[key], _getdate(value))))
            elif (key == "max-age") and isinstance(value, int):
                append(("%s=%d" % (self._reserved[key], value)))
            elif (key == "comment") and isinstance(value, str):
                append(("%s=%s" % (self._reserved[key], _quote(value))))
            elif key in self._flags:
                if value:
                    append(str(self._reserved[key]))
            else:
                append(("%s=%s" % (self._reserved[key], value)))
        return _semispacejoin(result)

    __class_getitem__ = classmethod(types.GenericAlias)


_LegalKeyChars = "\\w\\d!#%&'~_`><@,:/\\$\\*\\+\\-\\.\\^\\|\\)\\(\\?\\}\\{\\="
_LegalValueChars = _LegalKeyChars + "\\[\\]"
_CookiePattern = re.compile(
    (
        (
            (
                (
                    "\n    \\s*                            # Optional whitespace at start of cookie\n    (?P<key>                       # Start of group 'key'\n    ["
                    + _LegalKeyChars
                )
                + ']+?   # Any word of at least one letter\n    )                              # End of group \'key\'\n    (                              # Optional group: there may not be a value.\n    \\s*=\\s*                          # Equal Sign\n    (?P<val>                         # Start of group \'val\'\n    "(?:[^\\\\"]|\\\\.)*"                  # Any doublequoted string\n    |                                  # or\n    \\w{3},\\s[\\w\\d\\s-]{9,11}\\s[\\d:]{8}\\sGMT  # Special case for "expires" attr\n    |                                  # or\n    ['
            )
            + _LegalValueChars
        )
        + "]*      # Any word or empty string\n    )                                # End of group 'val'\n    )?                             # End of optional value group\n    \\s*                            # Any number of spaces.\n    (\\s+|;|$)                      # Ending either at space, semicolon, or EOS.\n    "
    ),
    (re.ASCII | re.VERBOSE),
)


class BaseCookie(dict):
    "A container class for a set of Morsels."

    def value_decode(self, val):
        "real_value, coded_value = value_decode(STRING)\n        Called prior to setting a cookie's value from the network\n        representation.  The VALUE is the value read from HTTP\n        header.\n        Override this function to modify the behavior of cookies.\n        "
        return (val, val)

    def value_encode(self, val):
        "real_value, coded_value = value_encode(VALUE)\n        Called prior to setting a cookie's value from the dictionary\n        representation.  The VALUE is the value being assigned.\n        Override this function to modify the behavior of cookies.\n        "
        strval = str(val)
        return (strval, strval)

    def __init__(self, input=None):
        if input:
            self.load(input)

    def __set(self, key, real_value, coded_value):
        "Private method for setting a cookie's value"
        M = self.get(key, Morsel())
        M.set(key, real_value, coded_value)
        dict.__setitem__(self, key, M)

    def __setitem__(self, key, value):
        "Dictionary style assignment."
        if isinstance(value, Morsel):
            dict.__setitem__(self, key, value)
        else:
            (rval, cval) = self.value_encode(value)
            self.__set(key, rval, cval)

    def output(self, attrs=None, header="Set-Cookie:", sep="\r\n"):
        "Return a string suitable for HTTP."
        result = []
        items = sorted(self.items())
        for (key, value) in items:
            result.append(value.output(attrs, header))
        return sep.join(result)

    __str__ = output

    def __repr__(self):
        l = []
        items = sorted(self.items())
        for (key, value) in items:
            l.append(("%s=%s" % (key, repr(value.value))))
        return "<%s: %s>" % (self.__class__.__name__, _spacejoin(l))

    def js_output(self, attrs=None):
        "Return a string suitable for JavaScript."
        result = []
        items = sorted(self.items())
        for (key, value) in items:
            result.append(value.js_output(attrs))
        return _nulljoin(result)

    def load(self, rawdata):
        "Load cookies from a string (presumably HTTP_COOKIE) or\n        from a dictionary.  Loading cookies from a dictionary 'd'\n        is equivalent to calling:\n            map(Cookie.__setitem__, d.keys(), d.values())\n        "
        if isinstance(rawdata, str):
            self.__parse_string(rawdata)
        else:
            for (key, value) in rawdata.items():
                self[key] = value
        return

    def __parse_string(self, str, patt=_CookiePattern):
        i = 0
        n = len(str)
        parsed_items = []
        morsel_seen = False
        TYPE_ATTRIBUTE = 1
        TYPE_KEYVALUE = 2
        while 0 <= i < n:
            match = patt.match(str, i)
            if not match:
                break
            (key, value) = (match.group("key"), match.group("val"))
            i = match.end(0)
            if key[0] == "$":
                if not morsel_seen:
                    continue
                parsed_items.append((TYPE_ATTRIBUTE, key[1:], value))
            elif key.lower() in Morsel._reserved:
                if not morsel_seen:
                    return
                if value is None:
                    if key.lower() in Morsel._flags:
                        parsed_items.append((TYPE_ATTRIBUTE, key, True))
                    else:
                        return
                else:
                    parsed_items.append((TYPE_ATTRIBUTE, key, _unquote(value)))
            elif value is not None:
                parsed_items.append((TYPE_KEYVALUE, key, self.value_decode(value)))
                morsel_seen = True
            else:
                return
        M = None
        for (tp, key, value) in parsed_items:
            if tp == TYPE_ATTRIBUTE:
                assert M is not None
                M[key] = value
            else:
                assert tp == TYPE_KEYVALUE
                (rval, cval) = value
                self.__set(key, rval, cval)
                M = self[key]


class SimpleCookie(BaseCookie):
    "\n    SimpleCookie supports strings as cookie values.  When setting\n    the value using the dictionary assignment notation, SimpleCookie\n    calls the builtin str() to convert the value to a string.  Values\n    received from HTTP are kept as strings.\n    "

    def value_decode(self, val):
        return (_unquote(val), val)

    def value_encode(self, val):
        strval = str(val)
        return (strval, _quote(strval))
