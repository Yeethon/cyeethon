"HTTP cookie handling for web clients.\n\nThis module has (now fairly distant) origins in Gisle Aas' Perl module\nHTTP::Cookies, from the libwww-perl library.\n\nDocstrings, comments and debug strings in this code refer to the\nattributes of the HTTP cookie system as cookie-attributes, to distinguish\nthem clearly from Python attributes.\n\nClass diagram (note that BSDDBCookieJar and the MSIE* classes are not\ndistributed with the Python standard library, but are available from\nhttp://wwwsearch.sf.net/):\n\n                        CookieJar____\n                        /     \\      \\\n            FileCookieJar      \\      \\\n             /    |   \\         \\      \\\n MozillaCookieJar | LWPCookieJar \\      \\\n                  |               |      \\\n                  |   ---MSIEBase |       \\\n                  |  /      |     |        \\\n                  | /   MSIEDBCookieJar BSDDBCookieJar\n                  |/\n               MSIECookieJar\n\n"
__all__ = [
    "Cookie",
    "CookieJar",
    "CookiePolicy",
    "DefaultCookiePolicy",
    "FileCookieJar",
    "LWPCookieJar",
    "LoadError",
    "MozillaCookieJar",
]
import os
import copy
import datetime
import re
import time
import urllib.parse, urllib.request
import threading as _threading
import http.client
from calendar import timegm

debug = False
logger = None


def _debug(*args):
    if not debug:
        return
    global logger
    if not logger:
        import logging

        logger = logging.getLogger("http.cookiejar")
    return logger.debug(*args)


HTTPONLY_ATTR = "HTTPOnly"
HTTPONLY_PREFIX = "#HttpOnly_"
DEFAULT_HTTP_PORT = str(http.client.HTTP_PORT)
NETSCAPE_MAGIC_RGX = re.compile("#( Netscape)? HTTP Cookie File")
MISSING_FILENAME_TEXT = (
    "a filename was not supplied (nor was the CookieJar instance initialised with one)"
)
NETSCAPE_HEADER_TEXT = "# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file!  Do not edit.\n\n"


def _warn_unhandled_exception():
    import io, warnings, traceback

    f = io.StringIO()
    traceback.print_exc(None, f)
    msg = f.getvalue()
    warnings.warn(("http.cookiejar bug!\n%s" % msg), stacklevel=2)


EPOCH_YEAR = 1970


def _timegm(tt):
    (year, month, mday, hour, min, sec) = tt[:6]
    if (
        (year >= EPOCH_YEAR)
        and (1 <= month <= 12)
        and (1 <= mday <= 31)
        and (0 <= hour <= 24)
        and (0 <= min <= 59)
        and (0 <= sec <= 61)
    ):
        return timegm(tt)
    else:
        return None


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = [
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
MONTHS_LOWER = []
for month in MONTHS:
    MONTHS_LOWER.append(month.lower())


def time2isoz(t=None):
    'Return a string representing time in seconds since epoch, t.\n\n    If the function is called without an argument, it will use the current\n    time.\n\n    The format of the returned string is like "YYYY-MM-DD hh:mm:ssZ",\n    representing Universal Time (UTC, aka GMT).  An example of this format is:\n\n    1994-11-24 08:49:37Z\n\n    '
    if t is None:
        dt = datetime.datetime.utcnow()
    else:
        dt = datetime.datetime.utcfromtimestamp(t)
    return "%04d-%02d-%02d %02d:%02d:%02dZ" % (
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
    )


def time2netscape(t=None):
    "Return a string representing time in seconds since epoch, t.\n\n    If the function is called without an argument, it will use the current\n    time.\n\n    The format of the returned string is like this:\n\n    Wed, DD-Mon-YYYY HH:MM:SS GMT\n\n    "
    if t is None:
        dt = datetime.datetime.utcnow()
    else:
        dt = datetime.datetime.utcfromtimestamp(t)
    return "%s, %02d-%s-%04d %02d:%02d:%02d GMT" % (
        DAYS[dt.weekday()],
        dt.day,
        MONTHS[(dt.month - 1)],
        dt.year,
        dt.hour,
        dt.minute,
        dt.second,
    )


UTC_ZONES = {"GMT": None, "UTC": None, "UT": None, "Z": None}
TIMEZONE_RE = re.compile("^([-+])?(\\d\\d?):?(\\d\\d)?$", re.ASCII)


def offset_from_tz_string(tz):
    offset = None
    if tz in UTC_ZONES:
        offset = 0
    else:
        m = TIMEZONE_RE.search(tz)
        if m:
            offset = 3600 * int(m.group(2))
            if m.group(3):
                offset = offset + (60 * int(m.group(3)))
            if m.group(1) == "-":
                offset = -offset
    return offset


def _str2time(day, mon, yr, hr, min, sec, tz):
    yr = int(yr)
    if yr > datetime.MAXYEAR:
        return None
    try:
        mon = MONTHS_LOWER.index(mon.lower()) + 1
    except ValueError:
        try:
            imon = int(mon)
        except ValueError:
            return None
        if 1 <= imon <= 12:
            mon = imon
        else:
            return None
    if hr is None:
        hr = 0
    if min is None:
        min = 0
    if sec is None:
        sec = 0
    day = int(day)
    hr = int(hr)
    min = int(min)
    sec = int(sec)
    if yr < 1000:
        cur_yr = time.localtime(time.time())[0]
        m = cur_yr % 100
        tmp = yr
        yr = (yr + cur_yr) - m
        m = m - tmp
        if abs(m) > 50:
            if m > 0:
                yr = yr + 100
            else:
                yr = yr - 100
    t = _timegm((yr, mon, day, hr, min, sec, tz))
    if t is not None:
        if tz is None:
            tz = "UTC"
        tz = tz.upper()
        offset = offset_from_tz_string(tz)
        if offset is None:
            return None
        t = t - offset
    return t


STRICT_DATE_RE = re.compile(
    "^[SMTWF][a-z][a-z], (\\d\\d) ([JFMASOND][a-z][a-z]) (\\d\\d\\d\\d) (\\d\\d):(\\d\\d):(\\d\\d) GMT$",
    re.ASCII,
)
WEEKDAY_RE = re.compile(
    "^(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)[a-z]*,?\\s*", (re.I | re.ASCII)
)
LOOSE_HTTP_DATE_RE = re.compile(
    "^\n    (\\d\\d?)            # day\n       (?:\\s+|[-\\/])\n    (\\w+)              # month\n        (?:\\s+|[-\\/])\n    (\\d+)              # year\n    (?:\n          (?:\\s+|:)    # separator before clock\n       (\\d\\d?):(\\d\\d)  # hour:min\n       (?::(\\d\\d))?    # optional seconds\n    )?                 # optional clock\n       \\s*\n    (?:\n       ([-+]?\\d{2,4}|(?![APap][Mm]\\b)[A-Za-z]+) # timezone\n       \\s*\n    )?\n    (?:\n       \\(\\w+\\)         # ASCII representation of timezone in parens.\n       \\s*\n    )?$",
    (re.X | re.ASCII),
)


def http2time(text):
    'Returns time in seconds since epoch of time represented by a string.\n\n    Return value is an integer.\n\n    None is returned if the format of str is unrecognized, the time is outside\n    the representable range, or the timezone string is not recognized.  If the\n    string contains no timezone, UTC is assumed.\n\n    The timezone in the string may be numerical (like "-0800" or "+0100") or a\n    string timezone (like "UTC", "GMT", "BST" or "EST").  Currently, only the\n    timezone strings equivalent to UTC (zero offset) are known to the function.\n\n    The function loosely parses the following formats:\n\n    Wed, 09 Feb 1994 22:23:32 GMT       -- HTTP format\n    Tuesday, 08-Feb-94 14:15:29 GMT     -- old rfc850 HTTP format\n    Tuesday, 08-Feb-1994 14:15:29 GMT   -- broken rfc850 HTTP format\n    09 Feb 1994 22:23:32 GMT            -- HTTP format (no weekday)\n    08-Feb-94 14:15:29 GMT              -- rfc850 format (no weekday)\n    08-Feb-1994 14:15:29 GMT            -- broken rfc850 format (no weekday)\n\n    The parser ignores leading and trailing whitespace.  The time may be\n    absent.\n\n    If the year is given with only 2 digits, the function will select the\n    century that makes the year closest to the current date.\n\n    '
    m = STRICT_DATE_RE.search(text)
    if m:
        g = m.groups()
        mon = MONTHS_LOWER.index(g[1].lower()) + 1
        tt = (int(g[2]), mon, int(g[0]), int(g[3]), int(g[4]), float(g[5]))
        return _timegm(tt)
    text = text.lstrip()
    text = WEEKDAY_RE.sub("", text, 1)
    (day, mon, yr, hr, min, sec, tz) = [None] * 7
    m = LOOSE_HTTP_DATE_RE.search(text)
    if m is not None:
        (day, mon, yr, hr, min, sec, tz) = m.groups()
    else:
        return None
    return _str2time(day, mon, yr, hr, min, sec, tz)


ISO_DATE_RE = re.compile(
    '^\n    (\\d{4})              # year\n       [-\\/]?\n    (\\d\\d?)              # numerical month\n       [-\\/]?\n    (\\d\\d?)              # day\n   (?:\n         (?:\\s+|[-:Tt])  # separator before clock\n      (\\d\\d?):?(\\d\\d)    # hour:min\n      (?::?(\\d\\d(?:\\.\\d*)?))?  # optional seconds (and fractional)\n   )?                    # optional clock\n      \\s*\n   (?:\n      ([-+]?\\d\\d?:?(:?\\d\\d)?\n       |Z|z)             # timezone  (Z is "zero meridian", i.e. GMT)\n      \\s*\n   )?$',
    (re.X | re.ASCII),
)


def iso2time(text):
    "\n    As for http2time, but parses the ISO 8601 formats:\n\n    1994-02-03 14:15:29 -0100    -- ISO 8601 format\n    1994-02-03 14:15:29          -- zone is optional\n    1994-02-03                   -- only date\n    1994-02-03T14:15:29          -- Use T as separator\n    19940203T141529Z             -- ISO 8601 compact format\n    19940203                     -- only date\n\n    "
    text = text.lstrip()
    (day, mon, yr, hr, min, sec, tz) = [None] * 7
    m = ISO_DATE_RE.search(text)
    if m is not None:
        (yr, mon, day, hr, min, sec, tz, _) = m.groups()
    else:
        return None
    return _str2time(day, mon, yr, hr, min, sec, tz)


def unmatched(match):
    "Return unmatched part of re.Match object."
    (start, end) = match.span(0)
    return match.string[:start] + match.string[end:]


HEADER_TOKEN_RE = re.compile("^\\s*([^=\\s;,]+)")
HEADER_QUOTED_VALUE_RE = re.compile(
    '^\\s*=\\s*\\"([^\\"\\\\]*(?:\\\\.[^\\"\\\\]*)*)\\"'
)
HEADER_VALUE_RE = re.compile("^\\s*=\\s*([^\\s;,]*)")
HEADER_ESCAPE_RE = re.compile("\\\\(.)")


def split_header_words(header_values):
    'Parse header values into a list of lists containing key,value pairs.\n\n    The function knows how to deal with ",", ";" and "=" as well as quoted\n    values after "=".  A list of space separated tokens are parsed as if they\n    were separated by ";".\n\n    If the header_values passed as argument contains multiple values, then they\n    are treated as if they were a single value separated by comma ",".\n\n    This means that this function is useful for parsing header fields that\n    follow this syntax (BNF as from the HTTP/1.1 specification, but we relax\n    the requirement for tokens).\n\n      headers           = #header\n      header            = (token | parameter) *( [";"] (token | parameter))\n\n      token             = 1*<any CHAR except CTLs or separators>\n      separators        = "(" | ")" | "<" | ">" | "@"\n                        | "," | ";" | ":" | "\\" | <">\n                        | "/" | "[" | "]" | "?" | "="\n                        | "{" | "}" | SP | HT\n\n      quoted-string     = ( <"> *(qdtext | quoted-pair ) <"> )\n      qdtext            = <any TEXT except <">>\n      quoted-pair       = "\\" CHAR\n\n      parameter         = attribute "=" value\n      attribute         = token\n      value             = token | quoted-string\n\n    Each header is represented by a list of key/value pairs.  The value for a\n    simple token (not part of a parameter) is None.  Syntactically incorrect\n    headers will not necessarily be parsed as you would want.\n\n    This is easier to describe with some examples:\n\n    >>> split_header_words([\'foo="bar"; port="80,81"; discard, bar=baz\'])\n    [[(\'foo\', \'bar\'), (\'port\', \'80,81\'), (\'discard\', None)], [(\'bar\', \'baz\')]]\n    >>> split_header_words([\'text/html; charset="iso-8859-1"\'])\n    [[(\'text/html\', None), (\'charset\', \'iso-8859-1\')]]\n    >>> split_header_words([r\'Basic realm="\\"foo\\bar\\""\'])\n    [[(\'Basic\', None), (\'realm\', \'"foobar"\')]]\n\n    '
    assert not isinstance(header_values, str)
    result = []
    for text in header_values:
        orig_text = text
        pairs = []
        while text:
            m = HEADER_TOKEN_RE.search(text)
            if m:
                text = unmatched(m)
                name = m.group(1)
                m = HEADER_QUOTED_VALUE_RE.search(text)
                if m:
                    text = unmatched(m)
                    value = m.group(1)
                    value = HEADER_ESCAPE_RE.sub("\\1", value)
                else:
                    m = HEADER_VALUE_RE.search(text)
                    if m:
                        text = unmatched(m)
                        value = m.group(1)
                        value = value.rstrip()
                    else:
                        value = None
                pairs.append((name, value))
            elif text.lstrip().startswith(","):
                text = text.lstrip()[1:]
                if pairs:
                    result.append(pairs)
                pairs = []
            else:
                (non_junk, nr_junk_chars) = re.subn("^[=\\s;]*", "", text)
                assert nr_junk_chars > 0, "split_header_words bug: '%s', '%s', %s" % (
                    orig_text,
                    text,
                    pairs,
                )
                text = non_junk
        if pairs:
            result.append(pairs)
    return result


HEADER_JOIN_ESCAPE_RE = re.compile('([\\"\\\\])')


def join_header_words(lists):
    'Do the inverse (almost) of the conversion done by split_header_words.\n\n    Takes a list of lists of (key, value) pairs and produces a single header\n    value.  Attribute values are quoted if needed.\n\n    >>> join_header_words([[("text/plain", None), ("charset", "iso-8859-1")]])\n    \'text/plain; charset="iso-8859-1"\'\n    >>> join_header_words([[("text/plain", None)], [("charset", "iso-8859-1")]])\n    \'text/plain, charset="iso-8859-1"\'\n\n    '
    headers = []
    for pairs in lists:
        attr = []
        for (k, v) in pairs:
            if v is not None:
                if not re.search("^\\w+$", v):
                    v = HEADER_JOIN_ESCAPE_RE.sub("\\\\\\1", v)
                    v = '"%s"' % v
                k = "%s=%s" % (k, v)
            attr.append(k)
        if attr:
            headers.append("; ".join(attr))
    return ", ".join(headers)


def strip_quotes(text):
    if text.startswith('"'):
        text = text[1:]
    if text.endswith('"'):
        text = text[:(-1)]
    return text


def parse_ns_headers(ns_headers):
    'Ad-hoc parser for Netscape protocol cookie-attributes.\n\n    The old Netscape cookie format for Set-Cookie can for instance contain\n    an unquoted "," in the expires field, so we have to use this ad-hoc\n    parser instead of split_header_words.\n\n    XXX This may not make the best possible effort to parse all the crap\n    that Netscape Cookie headers contain.  Ronald Tschalar\'s HTTPClient\n    parser is probably better, so could do worse than following that if\n    this ever gives any trouble.\n\n    Currently, this is also used for parsing RFC 2109 cookies.\n\n    '
    known_attrs = ("expires", "domain", "path", "secure", "version", "port", "max-age")
    result = []
    for ns_header in ns_headers:
        pairs = []
        version_set = False
        for (ii, param) in enumerate(ns_header.split(";")):
            param = param.strip()
            (key, sep, val) = param.partition("=")
            key = key.strip()
            if not key:
                if ii == 0:
                    break
                else:
                    continue
            val = val.strip() if sep else None
            if ii != 0:
                lc = key.lower()
                if lc in known_attrs:
                    key = lc
                if key == "version":
                    if val is not None:
                        val = strip_quotes(val)
                    version_set = True
                elif key == "expires":
                    if val is not None:
                        val = http2time(strip_quotes(val))
            pairs.append((key, val))
        if pairs:
            if not version_set:
                pairs.append(("version", "0"))
            result.append(pairs)
    return result


IPV4_RE = re.compile("\\.\\d+$", re.ASCII)


def is_HDN(text):
    "Return True if text is a host domain name."
    if IPV4_RE.search(text):
        return False
    if text == "":
        return False
    if (text[0] == ".") or (text[(-1)] == "."):
        return False
    return True


def domain_match(A, B):
    "Return True if domain A domain-matches domain B, according to RFC 2965.\n\n    A and B may be host domain names or IP addresses.\n\n    RFC 2965, section 1:\n\n    Host names can be specified either as an IP address or a HDN string.\n    Sometimes we compare one host name with another.  (Such comparisons SHALL\n    be case-insensitive.)  Host A's name domain-matches host B's if\n\n         *  their host name strings string-compare equal; or\n\n         * A is a HDN string and has the form NB, where N is a non-empty\n            name string, B has the form .B', and B' is a HDN string.  (So,\n            x.y.com domain-matches .Y.com but not Y.com.)\n\n    Note that domain-match is not a commutative operation: a.b.c.com\n    domain-matches .c.com, but not the reverse.\n\n    "
    A = A.lower()
    B = B.lower()
    if A == B:
        return True
    if not is_HDN(A):
        return False
    i = A.rfind(B)
    if (i == (-1)) or (i == 0):
        return False
    if not B.startswith("."):
        return False
    if not is_HDN(B[1:]):
        return False
    return True


def liberal_is_HDN(text):
    "Return True if text is a sort-of-like a host domain name.\n\n    For accepting/blocking domains.\n\n    "
    if IPV4_RE.search(text):
        return False
    return True


def user_domain_match(A, B):
    "For blocking/accepting domains.\n\n    A and B may be host domain names or IP addresses.\n\n    "
    A = A.lower()
    B = B.lower()
    if not (liberal_is_HDN(A) and liberal_is_HDN(B)):
        if A == B:
            return True
        return False
    initial_dot = B.startswith(".")
    if initial_dot and A.endswith(B):
        return True
    if (not initial_dot) and (A == B):
        return True
    return False


cut_port_re = re.compile(":\\d+$", re.ASCII)


def request_host(request):
    "Return request-host, as defined by RFC 2965.\n\n    Variation from RFC: returned value is lowercased, for convenient\n    comparison.\n\n    "
    url = request.get_full_url()
    host = urllib.parse.urlparse(url)[1]
    if host == "":
        host = request.get_header("Host", "")
    host = cut_port_re.sub("", host, 1)
    return host.lower()


def eff_request_host(request):
    "Return a tuple (request-host, effective request-host name).\n\n    As defined by RFC 2965, except both are lowercased.\n\n    "
    erhn = req_host = request_host(request)
    if (req_host.find(".") == (-1)) and (not IPV4_RE.search(req_host)):
        erhn = req_host + ".local"
    return (req_host, erhn)


def request_path(request):
    "Path component of request-URI, as defined by RFC 2965."
    url = request.get_full_url()
    parts = urllib.parse.urlsplit(url)
    path = escape_path(parts.path)
    if not path.startswith("/"):
        path = "/" + path
    return path


def request_port(request):
    host = request.host
    i = host.find(":")
    if i >= 0:
        port = host[(i + 1) :]
        try:
            int(port)
        except ValueError:
            _debug("nonnumeric port: '%s'", port)
            return None
    else:
        port = DEFAULT_HTTP_PORT
    return port


HTTP_PATH_SAFE = "%/;:@&=+$,!~*'()"
ESCAPED_CHAR_RE = re.compile("%([0-9a-fA-F][0-9a-fA-F])")


def uppercase_escaped_char(match):
    return "%%%s" % match.group(1).upper()


def escape_path(path):
    "Escape any invalid characters in HTTP URL, and uppercase all escapes."
    path = urllib.parse.quote(path, HTTP_PATH_SAFE)
    path = ESCAPED_CHAR_RE.sub(uppercase_escaped_char, path)
    return path


def reach(h):
    'Return reach of host h, as defined by RFC 2965, section 1.\n\n    The reach R of a host name H is defined as follows:\n\n       *  If\n\n          -  H is the host domain name of a host; and,\n\n          -  H has the form A.B; and\n\n          -  A has no embedded (that is, interior) dots; and\n\n          -  B has at least one embedded dot, or B is the string "local".\n             then the reach of H is .B.\n\n       *  Otherwise, the reach of H is H.\n\n    >>> reach("www.acme.com")\n    \'.acme.com\'\n    >>> reach("acme.com")\n    \'acme.com\'\n    >>> reach("acme.local")\n    \'.local\'\n\n    '
    i = h.find(".")
    if i >= 0:
        b = h[(i + 1) :]
        i = b.find(".")
        if is_HDN(h) and ((i >= 0) or (b == "local")):
            return "." + b
    return h


def is_third_party(request):
    "\n\n    RFC 2965, section 3.3.6:\n\n        An unverifiable transaction is to a third-party host if its request-\n        host U does not domain-match the reach R of the request-host O in the\n        origin transaction.\n\n    "
    req_host = request_host(request)
    if not domain_match(req_host, reach(request.origin_req_host)):
        return True
    else:
        return False


class Cookie:
    'HTTP Cookie.\n\n    This class represents both Netscape and RFC 2965 cookies.\n\n    This is deliberately a very simple class.  It just holds attributes.  It\'s\n    possible to construct Cookie instances that don\'t comply with the cookie\n    standards.  CookieJar.make_cookies is the factory function for Cookie\n    objects -- it deals with cookie parsing, supplying defaults, and\n    normalising to the representation used in this class.  CookiePolicy is\n    responsible for checking them to see whether they should be accepted from\n    and returned to the server.\n\n    Note that the port may be present in the headers, but unspecified ("Port"\n    rather than"Port=80", for example); if this is the case, port is None.\n\n    '

    def __init__(
        self,
        version,
        name,
        value,
        port,
        port_specified,
        domain,
        domain_specified,
        domain_initial_dot,
        path,
        path_specified,
        secure,
        expires,
        discard,
        comment,
        comment_url,
        rest,
        rfc2109=False,
    ):
        if version is not None:
            version = int(version)
        if expires is not None:
            expires = int(float(expires))
        if (port is None) and (port_specified is True):
            raise ValueError("if port is None, port_specified must be false")
        self.version = version
        self.name = name
        self.value = value
        self.port = port
        self.port_specified = port_specified
        self.domain = domain.lower()
        self.domain_specified = domain_specified
        self.domain_initial_dot = domain_initial_dot
        self.path = path
        self.path_specified = path_specified
        self.secure = secure
        self.expires = expires
        self.discard = discard
        self.comment = comment
        self.comment_url = comment_url
        self.rfc2109 = rfc2109
        self._rest = copy.copy(rest)

    def has_nonstandard_attr(self, name):
        return name in self._rest

    def get_nonstandard_attr(self, name, default=None):
        return self._rest.get(name, default)

    def set_nonstandard_attr(self, name, value):
        self._rest[name] = value

    def is_expired(self, now=None):
        if now is None:
            now = time.time()
        if (self.expires is not None) and (self.expires <= now):
            return True
        return False

    def __str__(self):
        if self.port is None:
            p = ""
        else:
            p = ":" + self.port
        limit = (self.domain + p) + self.path
        if self.value is not None:
            namevalue = "%s=%s" % (self.name, self.value)
        else:
            namevalue = self.name
        return "<Cookie %s for %s>" % (namevalue, limit)

    def __repr__(self):
        args = []
        for name in (
            "version",
            "name",
            "value",
            "port",
            "port_specified",
            "domain",
            "domain_specified",
            "domain_initial_dot",
            "path",
            "path_specified",
            "secure",
            "expires",
            "discard",
            "comment",
            "comment_url",
        ):
            attr = getattr(self, name)
            args.append(("%s=%s" % (name, repr(attr))))
        args.append(("rest=%s" % repr(self._rest)))
        args.append(("rfc2109=%s" % repr(self.rfc2109)))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(args))


class CookiePolicy:
    "Defines which cookies get accepted from and returned to server.\n\n    May also modify cookies, though this is probably a bad idea.\n\n    The subclass DefaultCookiePolicy defines the standard rules for Netscape\n    and RFC 2965 cookies -- override that if you want a customized policy.\n\n    "

    def set_ok(self, cookie, request):
        "Return true if (and only if) cookie should be accepted from server.\n\n        Currently, pre-expired cookies never get this far -- the CookieJar\n        class deletes such cookies itself.\n\n        "
        raise NotImplementedError()

    def return_ok(self, cookie, request):
        "Return true if (and only if) cookie should be returned to server."
        raise NotImplementedError()

    def domain_return_ok(self, domain, request):
        "Return false if cookies should not be returned, given cookie domain.\n        "
        return True

    def path_return_ok(self, path, request):
        "Return false if cookies should not be returned, given cookie path.\n        "
        return True


class DefaultCookiePolicy(CookiePolicy):
    "Implements the standard rules for accepting and returning cookies."
    DomainStrictNoDots = 1
    DomainStrictNonDomain = 2
    DomainRFC2965Match = 4
    DomainLiberal = 0
    DomainStrict = DomainStrictNoDots | DomainStrictNonDomain

    def __init__(
        self,
        blocked_domains=None,
        allowed_domains=None,
        netscape=True,
        rfc2965=False,
        rfc2109_as_netscape=None,
        hide_cookie2=False,
        strict_domain=False,
        strict_rfc2965_unverifiable=True,
        strict_ns_unverifiable=False,
        strict_ns_domain=DomainLiberal,
        strict_ns_set_initial_dollar=False,
        strict_ns_set_path=False,
        secure_protocols=("https", "wss"),
    ):
        "Constructor arguments should be passed as keyword arguments only."
        self.netscape = netscape
        self.rfc2965 = rfc2965
        self.rfc2109_as_netscape = rfc2109_as_netscape
        self.hide_cookie2 = hide_cookie2
        self.strict_domain = strict_domain
        self.strict_rfc2965_unverifiable = strict_rfc2965_unverifiable
        self.strict_ns_unverifiable = strict_ns_unverifiable
        self.strict_ns_domain = strict_ns_domain
        self.strict_ns_set_initial_dollar = strict_ns_set_initial_dollar
        self.strict_ns_set_path = strict_ns_set_path
        self.secure_protocols = secure_protocols
        if blocked_domains is not None:
            self._blocked_domains = tuple(blocked_domains)
        else:
            self._blocked_domains = ()
        if allowed_domains is not None:
            allowed_domains = tuple(allowed_domains)
        self._allowed_domains = allowed_domains

    def blocked_domains(self):
        "Return the sequence of blocked domains (as a tuple)."
        return self._blocked_domains

    def set_blocked_domains(self, blocked_domains):
        "Set the sequence of blocked domains."
        self._blocked_domains = tuple(blocked_domains)

    def is_blocked(self, domain):
        for blocked_domain in self._blocked_domains:
            if user_domain_match(domain, blocked_domain):
                return True
        return False

    def allowed_domains(self):
        "Return None, or the sequence of allowed domains (as a tuple)."
        return self._allowed_domains

    def set_allowed_domains(self, allowed_domains):
        "Set the sequence of allowed domains, or None."
        if allowed_domains is not None:
            allowed_domains = tuple(allowed_domains)
        self._allowed_domains = allowed_domains

    def is_not_allowed(self, domain):
        if self._allowed_domains is None:
            return False
        for allowed_domain in self._allowed_domains:
            if user_domain_match(domain, allowed_domain):
                return False
        return True

    def set_ok(self, cookie, request):
        "\n        If you override .set_ok(), be sure to call this method.  If it returns\n        false, so should your subclass (assuming your subclass wants to be more\n        strict about which cookies to accept).\n\n        "
        _debug(" - checking cookie %s=%s", cookie.name, cookie.value)
        assert cookie.name is not None
        for n in ("version", "verifiability", "name", "path", "domain", "port"):
            fn_name = "set_ok_" + n
            fn = getattr(self, fn_name)
            if not fn(cookie, request):
                return False
        return True

    def set_ok_version(self, cookie, request):
        if cookie.version is None:
            _debug(
                "   Set-Cookie2 without version attribute (%s=%s)",
                cookie.name,
                cookie.value,
            )
            return False
        if (cookie.version > 0) and (not self.rfc2965):
            _debug("   RFC 2965 cookies are switched off")
            return False
        elif (cookie.version == 0) and (not self.netscape):
            _debug("   Netscape cookies are switched off")
            return False
        return True

    def set_ok_verifiability(self, cookie, request):
        if request.unverifiable and is_third_party(request):
            if (cookie.version > 0) and self.strict_rfc2965_unverifiable:
                _debug("   third-party RFC 2965 cookie during unverifiable transaction")
                return False
            elif (cookie.version == 0) and self.strict_ns_unverifiable:
                _debug("   third-party Netscape cookie during unverifiable transaction")
                return False
        return True

    def set_ok_name(self, cookie, request):
        if (
            (cookie.version == 0)
            and self.strict_ns_set_initial_dollar
            and cookie.name.startswith("$")
        ):
            _debug("   illegal name (starts with '$'): '%s'", cookie.name)
            return False
        return True

    def set_ok_path(self, cookie, request):
        if cookie.path_specified:
            req_path = request_path(request)
            if (
                (cookie.version > 0)
                or ((cookie.version == 0) and self.strict_ns_set_path)
            ) and (not self.path_return_ok(cookie.path, request)):
                _debug(
                    "   path attribute %s is not a prefix of request path %s",
                    cookie.path,
                    req_path,
                )
                return False
        return True

    def set_ok_domain(self, cookie, request):
        if self.is_blocked(cookie.domain):
            _debug("   domain %s is in user block-list", cookie.domain)
            return False
        if self.is_not_allowed(cookie.domain):
            _debug("   domain %s is not in user allow-list", cookie.domain)
            return False
        if cookie.domain_specified:
            (req_host, erhn) = eff_request_host(request)
            domain = cookie.domain
            if self.strict_domain and (domain.count(".") >= 2):
                i = domain.rfind(".")
                j = domain.rfind(".", 0, i)
                if j == 0:
                    tld = domain[(i + 1) :]
                    sld = domain[(j + 1) : i]
                    if (
                        sld.lower()
                        in (
                            "co",
                            "ac",
                            "com",
                            "edu",
                            "org",
                            "net",
                            "gov",
                            "mil",
                            "int",
                            "aero",
                            "biz",
                            "cat",
                            "coop",
                            "info",
                            "jobs",
                            "mobi",
                            "museum",
                            "name",
                            "pro",
                            "travel",
                            "eu",
                        )
                    ) and (len(tld) == 2):
                        _debug("   country-code second level domain %s", domain)
                        return False
            if domain.startswith("."):
                undotted_domain = domain[1:]
            else:
                undotted_domain = domain
            embedded_dots = undotted_domain.find(".") >= 0
            if (not embedded_dots) and (domain != ".local"):
                _debug("   non-local domain %s contains no embedded dot", domain)
                return False
            if cookie.version == 0:
                if (not erhn.endswith(domain)) and (
                    (not erhn.startswith(".")) and (not ("." + erhn).endswith(domain))
                ):
                    _debug(
                        "   effective request-host %s (even with added initial dot) does not end with %s",
                        erhn,
                        domain,
                    )
                    return False
            if (cookie.version > 0) or (
                self.strict_ns_domain & self.DomainRFC2965Match
            ):
                if not domain_match(erhn, domain):
                    _debug(
                        "   effective request-host %s does not domain-match %s",
                        erhn,
                        domain,
                    )
                    return False
            if (cookie.version > 0) or (
                self.strict_ns_domain & self.DomainStrictNoDots
            ):
                host_prefix = req_host[: (-len(domain))]
                if (host_prefix.find(".") >= 0) and (not IPV4_RE.search(req_host)):
                    _debug(
                        "   host prefix %s for domain %s contains a dot",
                        host_prefix,
                        domain,
                    )
                    return False
        return True

    def set_ok_port(self, cookie, request):
        if cookie.port_specified:
            req_port = request_port(request)
            if req_port is None:
                req_port = "80"
            else:
                req_port = str(req_port)
            for p in cookie.port.split(","):
                try:
                    int(p)
                except ValueError:
                    _debug("   bad port %s (not numeric)", p)
                    return False
                if p == req_port:
                    break
            else:
                _debug("   request port (%s) not found in %s", req_port, cookie.port)
                return False
        return True

    def return_ok(self, cookie, request):
        "\n        If you override .return_ok(), be sure to call this method.  If it\n        returns false, so should your subclass (assuming your subclass wants to\n        be more strict about which cookies to return).\n\n        "
        _debug(" - checking cookie %s=%s", cookie.name, cookie.value)
        for n in ("version", "verifiability", "secure", "expires", "port", "domain"):
            fn_name = "return_ok_" + n
            fn = getattr(self, fn_name)
            if not fn(cookie, request):
                return False
        return True

    def return_ok_version(self, cookie, request):
        if (cookie.version > 0) and (not self.rfc2965):
            _debug("   RFC 2965 cookies are switched off")
            return False
        elif (cookie.version == 0) and (not self.netscape):
            _debug("   Netscape cookies are switched off")
            return False
        return True

    def return_ok_verifiability(self, cookie, request):
        if request.unverifiable and is_third_party(request):
            if (cookie.version > 0) and self.strict_rfc2965_unverifiable:
                _debug("   third-party RFC 2965 cookie during unverifiable transaction")
                return False
            elif (cookie.version == 0) and self.strict_ns_unverifiable:
                _debug("   third-party Netscape cookie during unverifiable transaction")
                return False
        return True

    def return_ok_secure(self, cookie, request):
        if cookie.secure and (request.type not in self.secure_protocols):
            _debug("   secure cookie with non-secure request")
            return False
        return True

    def return_ok_expires(self, cookie, request):
        if cookie.is_expired(self._now):
            _debug("   cookie expired")
            return False
        return True

    def return_ok_port(self, cookie, request):
        if cookie.port:
            req_port = request_port(request)
            if req_port is None:
                req_port = "80"
            for p in cookie.port.split(","):
                if p == req_port:
                    break
            else:
                _debug(
                    "   request port %s does not match cookie port %s",
                    req_port,
                    cookie.port,
                )
                return False
        return True

    def return_ok_domain(self, cookie, request):
        (req_host, erhn) = eff_request_host(request)
        domain = cookie.domain
        if domain and (not domain.startswith(".")):
            dotdomain = "." + domain
        else:
            dotdomain = domain
        if (
            (cookie.version == 0)
            and (self.strict_ns_domain & self.DomainStrictNonDomain)
            and (not cookie.domain_specified)
            and (domain != erhn)
        ):
            _debug(
                "   cookie with unspecified domain does not string-compare equal to request domain"
            )
            return False
        if (cookie.version > 0) and (not domain_match(erhn, domain)):
            _debug(
                "   effective request-host name %s does not domain-match RFC 2965 cookie domain %s",
                erhn,
                domain,
            )
            return False
        if (cookie.version == 0) and (not ("." + erhn).endswith(dotdomain)):
            _debug(
                "   request-host %s does not match Netscape cookie domain %s",
                req_host,
                domain,
            )
            return False
        return True

    def domain_return_ok(self, domain, request):
        (req_host, erhn) = eff_request_host(request)
        if not req_host.startswith("."):
            req_host = "." + req_host
        if not erhn.startswith("."):
            erhn = "." + erhn
        if domain and (not domain.startswith(".")):
            dotdomain = "." + domain
        else:
            dotdomain = domain
        if not (req_host.endswith(dotdomain) or erhn.endswith(dotdomain)):
            return False
        if self.is_blocked(domain):
            _debug("   domain %s is in user block-list", domain)
            return False
        if self.is_not_allowed(domain):
            _debug("   domain %s is not in user allow-list", domain)
            return False
        return True

    def path_return_ok(self, path, request):
        _debug("- checking cookie path=%s", path)
        req_path = request_path(request)
        pathlen = len(path)
        if req_path == path:
            return True
        elif req_path.startswith(path) and (
            path.endswith("/") or (req_path[pathlen : (pathlen + 1)] == "/")
        ):
            return True
        _debug("  %s does not path-match %s", req_path, path)
        return False


def vals_sorted_by_key(adict):
    keys = sorted(adict.keys())
    return map(adict.get, keys)


def deepvalues(mapping):
    "Iterates over nested mapping, depth-first, in sorted order by key."
    values = vals_sorted_by_key(mapping)
    for obj in values:
        mapping = False
        try:
            obj.items
        except AttributeError:
            pass
        else:
            mapping = True
            (yield from deepvalues(obj))
        if not mapping:
            (yield obj)


class Absent:
    pass


class CookieJar:
    "Collection of HTTP cookies.\n\n    You may not need to know about this class: try\n    urllib.request.build_opener(HTTPCookieProcessor).open(url).\n    "
    non_word_re = re.compile("\\W")
    quote_re = re.compile('([\\"\\\\])')
    strict_domain_re = re.compile("\\.?[^.]*")
    domain_re = re.compile("[^.]*")
    dots_re = re.compile("^\\.+")
    magic_re = re.compile("^\\#LWP-Cookies-(\\d+\\.\\d+)", re.ASCII)

    def __init__(self, policy=None):
        if policy is None:
            policy = DefaultCookiePolicy()
        self._policy = policy
        self._cookies_lock = _threading.RLock()
        self._cookies = {}

    def set_policy(self, policy):
        self._policy = policy

    def _cookies_for_domain(self, domain, request):
        cookies = []
        if not self._policy.domain_return_ok(domain, request):
            return []
        _debug("Checking %s for cookies to return", domain)
        cookies_by_path = self._cookies[domain]
        for path in cookies_by_path.keys():
            if not self._policy.path_return_ok(path, request):
                continue
            cookies_by_name = cookies_by_path[path]
            for cookie in cookies_by_name.values():
                if not self._policy.return_ok(cookie, request):
                    _debug("   not returning cookie")
                    continue
                _debug("   it's a match")
                cookies.append(cookie)
        return cookies

    def _cookies_for_request(self, request):
        "Return a list of cookies to be returned to server."
        cookies = []
        for domain in self._cookies.keys():
            cookies.extend(self._cookies_for_domain(domain, request))
        return cookies

    def _cookie_attrs(self, cookies):
        'Return a list of cookie-attributes to be returned to server.\n\n        like [\'foo="bar"; $Path="/"\', ...]\n\n        The $Version attribute is also added when appropriate (currently only\n        once per request).\n\n        '
        cookies.sort(key=(lambda a: len(a.path)), reverse=True)
        version_set = False
        attrs = []
        for cookie in cookies:
            version = cookie.version
            if not version_set:
                version_set = True
                if version > 0:
                    attrs.append(("$Version=%s" % version))
            if (
                (cookie.value is not None)
                and self.non_word_re.search(cookie.value)
                and (version > 0)
            ):
                value = self.quote_re.sub("\\\\\\1", cookie.value)
            else:
                value = cookie.value
            if cookie.value is None:
                attrs.append(cookie.name)
            else:
                attrs.append(("%s=%s" % (cookie.name, value)))
            if version > 0:
                if cookie.path_specified:
                    attrs.append(('$Path="%s"' % cookie.path))
                if cookie.domain.startswith("."):
                    domain = cookie.domain
                    if (not cookie.domain_initial_dot) and domain.startswith("."):
                        domain = domain[1:]
                    attrs.append(('$Domain="%s"' % domain))
                if cookie.port is not None:
                    p = "$Port"
                    if cookie.port_specified:
                        p = p + ('="%s"' % cookie.port)
                    attrs.append(p)
        return attrs

    def add_cookie_header(self, request):
        "Add correct Cookie: header to request (urllib.request.Request object).\n\n        The Cookie2 header is also added unless policy.hide_cookie2 is true.\n\n        "
        _debug("add_cookie_header")
        self._cookies_lock.acquire()
        try:
            self._policy._now = self._now = int(time.time())
            cookies = self._cookies_for_request(request)
            attrs = self._cookie_attrs(cookies)
            if attrs:
                if not request.has_header("Cookie"):
                    request.add_unredirected_header("Cookie", "; ".join(attrs))
            if (
                self._policy.rfc2965
                and (not self._policy.hide_cookie2)
                and (not request.has_header("Cookie2"))
            ):
                for cookie in cookies:
                    if cookie.version != 1:
                        request.add_unredirected_header("Cookie2", '$Version="1"')
                        break
        finally:
            self._cookies_lock.release()
        self.clear_expired_cookies()

    def _normalized_cookie_tuples(self, attrs_set):
        "Return list of tuples containing normalised cookie information.\n\n        attrs_set is the list of lists of key,value pairs extracted from\n        the Set-Cookie or Set-Cookie2 headers.\n\n        Tuples are name, value, standard, rest, where name and value are the\n        cookie name and value, standard is a dictionary containing the standard\n        cookie-attributes (discard, secure, version, expires or max-age,\n        domain, path and port) and rest is a dictionary containing the rest of\n        the cookie-attributes.\n\n        "
        cookie_tuples = []
        boolean_attrs = ("discard", "secure")
        value_attrs = (
            "version",
            "expires",
            "max-age",
            "domain",
            "path",
            "port",
            "comment",
            "commenturl",
        )
        for cookie_attrs in attrs_set:
            (name, value) = cookie_attrs[0]
            max_age_set = False
            bad_cookie = False
            standard = {}
            rest = {}
            for (k, v) in cookie_attrs[1:]:
                lc = k.lower()
                if (lc in value_attrs) or (lc in boolean_attrs):
                    k = lc
                if (k in boolean_attrs) and (v is None):
                    v = True
                if k in standard:
                    continue
                if k == "domain":
                    if v is None:
                        _debug("   missing value for domain attribute")
                        bad_cookie = True
                        break
                    v = v.lower()
                if k == "expires":
                    if max_age_set:
                        continue
                    if v is None:
                        _debug(
                            "   missing or invalid value for expires attribute: treating as session cookie"
                        )
                        continue
                if k == "max-age":
                    max_age_set = True
                    try:
                        v = int(v)
                    except ValueError:
                        _debug(
                            "   missing or invalid (non-numeric) value for max-age attribute"
                        )
                        bad_cookie = True
                        break
                    k = "expires"
                    v = self._now + v
                if (k in value_attrs) or (k in boolean_attrs):
                    if (v is None) and (k not in ("port", "comment", "commenturl")):
                        _debug(("   missing value for %s attribute" % k))
                        bad_cookie = True
                        break
                    standard[k] = v
                else:
                    rest[k] = v
            if bad_cookie:
                continue
            cookie_tuples.append((name, value, standard, rest))
        return cookie_tuples

    def _cookie_from_cookie_tuple(self, tup, request):
        (name, value, standard, rest) = tup
        domain = standard.get("domain", Absent)
        path = standard.get("path", Absent)
        port = standard.get("port", Absent)
        expires = standard.get("expires", Absent)
        version = standard.get("version", None)
        if version is not None:
            try:
                version = int(version)
            except ValueError:
                return None
        secure = standard.get("secure", False)
        discard = standard.get("discard", False)
        comment = standard.get("comment", None)
        comment_url = standard.get("commenturl", None)
        if (path is not Absent) and (path != ""):
            path_specified = True
            path = escape_path(path)
        else:
            path_specified = False
            path = request_path(request)
            i = path.rfind("/")
            if i != (-1):
                if version == 0:
                    path = path[:i]
                else:
                    path = path[: (i + 1)]
            if len(path) == 0:
                path = "/"
        domain_specified = domain is not Absent
        domain_initial_dot = False
        if domain_specified:
            domain_initial_dot = bool(domain.startswith("."))
        if domain is Absent:
            (req_host, erhn) = eff_request_host(request)
            domain = erhn
        elif not domain.startswith("."):
            domain = "." + domain
        port_specified = False
        if port is not Absent:
            if port is None:
                port = request_port(request)
            else:
                port_specified = True
                port = re.sub("\\s+", "", port)
        else:
            port = None
        if expires is Absent:
            expires = None
            discard = True
        elif expires <= self._now:
            try:
                self.clear(domain, path, name)
            except KeyError:
                pass
            _debug(
                "Expiring cookie, domain='%s', path='%s', name='%s'", domain, path, name
            )
            return None
        return Cookie(
            version,
            name,
            value,
            port,
            port_specified,
            domain,
            domain_specified,
            domain_initial_dot,
            path,
            path_specified,
            secure,
            expires,
            discard,
            comment,
            comment_url,
            rest,
        )

    def _cookies_from_attrs_set(self, attrs_set, request):
        cookie_tuples = self._normalized_cookie_tuples(attrs_set)
        cookies = []
        for tup in cookie_tuples:
            cookie = self._cookie_from_cookie_tuple(tup, request)
            if cookie:
                cookies.append(cookie)
        return cookies

    def _process_rfc2109_cookies(self, cookies):
        rfc2109_as_ns = getattr(self._policy, "rfc2109_as_netscape", None)
        if rfc2109_as_ns is None:
            rfc2109_as_ns = not self._policy.rfc2965
        for cookie in cookies:
            if cookie.version == 1:
                cookie.rfc2109 = True
                if rfc2109_as_ns:
                    cookie.version = 0

    def make_cookies(self, response, request):
        "Return sequence of Cookie objects extracted from response object."
        headers = response.info()
        rfc2965_hdrs = headers.get_all("Set-Cookie2", [])
        ns_hdrs = headers.get_all("Set-Cookie", [])
        self._policy._now = self._now = int(time.time())
        rfc2965 = self._policy.rfc2965
        netscape = self._policy.netscape
        if (
            ((not rfc2965_hdrs) and (not ns_hdrs))
            or ((not ns_hdrs) and (not rfc2965))
            or ((not rfc2965_hdrs) and (not netscape))
            or ((not netscape) and (not rfc2965))
        ):
            return []
        try:
            cookies = self._cookies_from_attrs_set(
                split_header_words(rfc2965_hdrs), request
            )
        except Exception:
            _warn_unhandled_exception()
            cookies = []
        if ns_hdrs and netscape:
            try:
                ns_cookies = self._cookies_from_attrs_set(
                    parse_ns_headers(ns_hdrs), request
                )
            except Exception:
                _warn_unhandled_exception()
                ns_cookies = []
            self._process_rfc2109_cookies(ns_cookies)
            if rfc2965:
                lookup = {}
                for cookie in cookies:
                    lookup[(cookie.domain, cookie.path, cookie.name)] = None

                def no_matching_rfc2965(ns_cookie, lookup=lookup):
                    key = (ns_cookie.domain, ns_cookie.path, ns_cookie.name)
                    return key not in lookup

                ns_cookies = filter(no_matching_rfc2965, ns_cookies)
            if ns_cookies:
                cookies.extend(ns_cookies)
        return cookies

    def set_cookie_if_ok(self, cookie, request):
        "Set a cookie if policy says it's OK to do so."
        self._cookies_lock.acquire()
        try:
            self._policy._now = self._now = int(time.time())
            if self._policy.set_ok(cookie, request):
                self.set_cookie(cookie)
        finally:
            self._cookies_lock.release()

    def set_cookie(self, cookie):
        "Set a cookie, without checking whether or not it should be set."
        c = self._cookies
        self._cookies_lock.acquire()
        try:
            if cookie.domain not in c:
                c[cookie.domain] = {}
            c2 = c[cookie.domain]
            if cookie.path not in c2:
                c2[cookie.path] = {}
            c3 = c2[cookie.path]
            c3[cookie.name] = cookie
        finally:
            self._cookies_lock.release()

    def extract_cookies(self, response, request):
        "Extract cookies from response, where allowable given the request."
        _debug("extract_cookies: %s", response.info())
        self._cookies_lock.acquire()
        try:
            for cookie in self.make_cookies(response, request):
                if self._policy.set_ok(cookie, request):
                    _debug(" setting cookie: %s", cookie)
                    self.set_cookie(cookie)
        finally:
            self._cookies_lock.release()

    def clear(self, domain=None, path=None, name=None):
        "Clear some cookies.\n\n        Invoking this method without arguments will clear all cookies.  If\n        given a single argument, only cookies belonging to that domain will be\n        removed.  If given two arguments, cookies belonging to the specified\n        path within that domain are removed.  If given three arguments, then\n        the cookie with the specified name, path and domain is removed.\n\n        Raises KeyError if no matching cookie exists.\n\n        "
        if name is not None:
            if (domain is None) or (path is None):
                raise ValueError(
                    "domain and path must be given to remove a cookie by name"
                )
            del self._cookies[domain][path][name]
        elif path is not None:
            if domain is None:
                raise ValueError("domain must be given to remove cookies by path")
            del self._cookies[domain][path]
        elif domain is not None:
            del self._cookies[domain]
        else:
            self._cookies = {}

    def clear_session_cookies(self):
        "Discard all session cookies.\n\n        Note that the .save() method won't save session cookies anyway, unless\n        you ask otherwise by passing a true ignore_discard argument.\n\n        "
        self._cookies_lock.acquire()
        try:
            for cookie in self:
                if cookie.discard:
                    self.clear(cookie.domain, cookie.path, cookie.name)
        finally:
            self._cookies_lock.release()

    def clear_expired_cookies(self):
        "Discard all expired cookies.\n\n        You probably don't need to call this method: expired cookies are never\n        sent back to the server (provided you're using DefaultCookiePolicy),\n        this method is called by CookieJar itself every so often, and the\n        .save() method won't save expired cookies anyway (unless you ask\n        otherwise by passing a true ignore_expires argument).\n\n        "
        self._cookies_lock.acquire()
        try:
            now = time.time()
            for cookie in self:
                if cookie.is_expired(now):
                    self.clear(cookie.domain, cookie.path, cookie.name)
        finally:
            self._cookies_lock.release()

    def __iter__(self):
        return deepvalues(self._cookies)

    def __len__(self):
        "Return number of contained cookies."
        i = 0
        for cookie in self:
            i = i + 1
        return i

    def __repr__(self):
        r = []
        for cookie in self:
            r.append(repr(cookie))
        return "<%s[%s]>" % (self.__class__.__name__, ", ".join(r))

    def __str__(self):
        r = []
        for cookie in self:
            r.append(str(cookie))
        return "<%s[%s]>" % (self.__class__.__name__, ", ".join(r))


class LoadError(OSError):
    pass


class FileCookieJar(CookieJar):
    "CookieJar that can be loaded from and saved to a file."

    def __init__(self, filename=None, delayload=False, policy=None):
        "\n        Cookies are NOT loaded from the named file until either the .load() or\n        .revert() method is called.\n\n        "
        CookieJar.__init__(self, policy)
        if filename is not None:
            filename = os.fspath(filename)
        self.filename = filename
        self.delayload = bool(delayload)

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        "Save cookies to a file."
        raise NotImplementedError()

    def load(self, filename=None, ignore_discard=False, ignore_expires=False):
        "Load cookies from a file."
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(MISSING_FILENAME_TEXT)
        with open(filename) as f:
            self._really_load(f, filename, ignore_discard, ignore_expires)

    def revert(self, filename=None, ignore_discard=False, ignore_expires=False):
        "Clear all cookies and reload cookies from a saved file.\n\n        Raises LoadError (or OSError) if reversion is not successful; the\n        object's state will not be altered if this happens.\n\n        "
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(MISSING_FILENAME_TEXT)
        self._cookies_lock.acquire()
        try:
            old_state = copy.deepcopy(self._cookies)
            self._cookies = {}
            try:
                self.load(filename, ignore_discard, ignore_expires)
            except OSError:
                self._cookies = old_state
                raise
        finally:
            self._cookies_lock.release()


def lwp_cookie_str(cookie):
    "Return string representation of Cookie in the LWP cookie file format.\n\n    Actually, the format is extended a bit -- see module docstring.\n\n    "
    h = [(cookie.name, cookie.value), ("path", cookie.path), ("domain", cookie.domain)]
    if cookie.port is not None:
        h.append(("port", cookie.port))
    if cookie.path_specified:
        h.append(("path_spec", None))
    if cookie.port_specified:
        h.append(("port_spec", None))
    if cookie.domain_initial_dot:
        h.append(("domain_dot", None))
    if cookie.secure:
        h.append(("secure", None))
    if cookie.expires:
        h.append(("expires", time2isoz(float(cookie.expires))))
    if cookie.discard:
        h.append(("discard", None))
    if cookie.comment:
        h.append(("comment", cookie.comment))
    if cookie.comment_url:
        h.append(("commenturl", cookie.comment_url))
    keys = sorted(cookie._rest.keys())
    for k in keys:
        h.append((k, str(cookie._rest[k])))
    h.append(("version", str(cookie.version)))
    return join_header_words([h])


class LWPCookieJar(FileCookieJar):
    '\n    The LWPCookieJar saves a sequence of "Set-Cookie3" lines.\n    "Set-Cookie3" is the format used by the libwww-perl library, not known\n    to be compatible with any browser, but which is easy to read and\n    doesn\'t lose information about RFC 2965 cookies.\n\n    Additional methods\n\n    as_lwp_str(ignore_discard=True, ignore_expired=True)\n\n    '

    def as_lwp_str(self, ignore_discard=True, ignore_expires=True):
        'Return cookies as a string of "\\n"-separated "Set-Cookie3" headers.\n\n        ignore_discard and ignore_expires: see docstring for FileCookieJar.save\n\n        '
        now = time.time()
        r = []
        for cookie in self:
            if (not ignore_discard) and cookie.discard:
                continue
            if (not ignore_expires) and cookie.is_expired(now):
                continue
            r.append(("Set-Cookie3: %s" % lwp_cookie_str(cookie)))
        return "\n".join((r + [""]))

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(MISSING_FILENAME_TEXT)
        with open(filename, "w") as f:
            f.write("#LWP-Cookies-2.0\n")
            f.write(self.as_lwp_str(ignore_discard, ignore_expires))

    def _really_load(self, f, filename, ignore_discard, ignore_expires):
        magic = f.readline()
        if not self.magic_re.search(magic):
            msg = "%r does not look like a Set-Cookie3 (LWP) format file" % filename
            raise LoadError(msg)
        now = time.time()
        header = "Set-Cookie3:"
        boolean_attrs = ("port_spec", "path_spec", "domain_dot", "secure", "discard")
        value_attrs = (
            "version",
            "port",
            "path",
            "domain",
            "expires",
            "comment",
            "commenturl",
        )
        try:
            while 1:
                line = f.readline()
                if line == "":
                    break
                if not line.startswith(header):
                    continue
                line = line[len(header) :].strip()
                for data in split_header_words([line]):
                    (name, value) = data[0]
                    standard = {}
                    rest = {}
                    for k in boolean_attrs:
                        standard[k] = False
                    for (k, v) in data[1:]:
                        if k is not None:
                            lc = k.lower()
                        else:
                            lc = None
                        if (lc in value_attrs) or (lc in boolean_attrs):
                            k = lc
                        if k in boolean_attrs:
                            if v is None:
                                v = True
                            standard[k] = v
                        elif k in value_attrs:
                            standard[k] = v
                        else:
                            rest[k] = v
                    h = standard.get
                    expires = h("expires")
                    discard = h("discard")
                    if expires is not None:
                        expires = iso2time(expires)
                    if expires is None:
                        discard = True
                    domain = h("domain")
                    domain_specified = domain.startswith(".")
                    c = Cookie(
                        h("version"),
                        name,
                        value,
                        h("port"),
                        h("port_spec"),
                        domain,
                        domain_specified,
                        h("domain_dot"),
                        h("path"),
                        h("path_spec"),
                        h("secure"),
                        expires,
                        discard,
                        h("comment"),
                        h("commenturl"),
                        rest,
                    )
                    if (not ignore_discard) and c.discard:
                        continue
                    if (not ignore_expires) and c.is_expired(now):
                        continue
                    self.set_cookie(c)
        except OSError:
            raise
        except Exception:
            _warn_unhandled_exception()
            raise LoadError(
                ("invalid Set-Cookie3 format file %r: %r" % (filename, line))
            )


class MozillaCookieJar(FileCookieJar):
    "\n\n    WARNING: you may want to backup your browser's cookies file if you use\n    this class to save cookies.  I *think* it works, but there have been\n    bugs in the past!\n\n    This class differs from CookieJar only in the format it uses to save and\n    load cookies to and from a file.  This class uses the Mozilla/Netscape\n    `cookies.txt' format.  lynx uses this file format, too.\n\n    Don't expect cookies saved while the browser is running to be noticed by\n    the browser (in fact, Mozilla on unix will overwrite your saved cookies if\n    you change them on disk while it's running; on Windows, you probably can't\n    save at all while the browser is running).\n\n    Note that the Mozilla/Netscape format will downgrade RFC2965 cookies to\n    Netscape cookies on saving.\n\n    In particular, the cookie version and port number information is lost,\n    together with information about whether or not Path, Port and Discard were\n    specified by the Set-Cookie2 (or Set-Cookie) header, and whether or not the\n    domain as set in the HTTP header started with a dot (yes, I'm aware some\n    domains in Netscape files start with a dot and some don't -- trust me, you\n    really don't want to know any more about this).\n\n    Note that though Mozilla and Netscape use the same format, they use\n    slightly different headers.  The class saves cookies using the Netscape\n    header by default (Mozilla can cope with that).\n\n    "

    def _really_load(self, f, filename, ignore_discard, ignore_expires):
        now = time.time()
        if not NETSCAPE_MAGIC_RGX.match(f.readline()):
            raise LoadError(
                ("%r does not look like a Netscape format cookies file" % filename)
            )
        try:
            while 1:
                line = f.readline()
                rest = {}
                if line == "":
                    break
                if line.startswith(HTTPONLY_PREFIX):
                    rest[HTTPONLY_ATTR] = ""
                    line = line[len(HTTPONLY_PREFIX) :]
                if line.endswith("\n"):
                    line = line[:(-1)]
                if line.strip().startswith(("#", "$")) or (line.strip() == ""):
                    continue
                (
                    domain,
                    domain_specified,
                    path,
                    secure,
                    expires,
                    name,
                    value,
                ) = line.split("\t")
                secure = secure == "TRUE"
                domain_specified = domain_specified == "TRUE"
                if name == "":
                    name = value
                    value = None
                initial_dot = domain.startswith(".")
                assert domain_specified == initial_dot
                discard = False
                if expires == "":
                    expires = None
                    discard = True
                c = Cookie(
                    0,
                    name,
                    value,
                    None,
                    False,
                    domain,
                    domain_specified,
                    initial_dot,
                    path,
                    False,
                    secure,
                    expires,
                    discard,
                    None,
                    None,
                    rest,
                )
                if (not ignore_discard) and c.discard:
                    continue
                if (not ignore_expires) and c.is_expired(now):
                    continue
                self.set_cookie(c)
        except OSError:
            raise
        except Exception:
            _warn_unhandled_exception()
            raise LoadError(
                ("invalid Netscape format cookies file %r: %r" % (filename, line))
            )

    def save(self, filename=None, ignore_discard=False, ignore_expires=False):
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                raise ValueError(MISSING_FILENAME_TEXT)
        with open(filename, "w") as f:
            f.write(NETSCAPE_HEADER_TEXT)
            now = time.time()
            for cookie in self:
                domain = cookie.domain
                if (not ignore_discard) and cookie.discard:
                    continue
                if (not ignore_expires) and cookie.is_expired(now):
                    continue
                if cookie.secure:
                    secure = "TRUE"
                else:
                    secure = "FALSE"
                if domain.startswith("."):
                    initial_dot = "TRUE"
                else:
                    initial_dot = "FALSE"
                if cookie.expires is not None:
                    expires = str(cookie.expires)
                else:
                    expires = ""
                if cookie.value is None:
                    name = ""
                    value = cookie.name
                else:
                    name = cookie.name
                    value = cookie.value
                if cookie.has_nonstandard_attr(HTTPONLY_ATTR):
                    domain = HTTPONLY_PREFIX + domain
                f.write(
                    (
                        "\t".join(
                            [
                                domain,
                                initial_dot,
                                cookie.path,
                                secure,
                                expires,
                                name,
                                value,
                            ]
                        )
                        + "\n"
                    )
                )
