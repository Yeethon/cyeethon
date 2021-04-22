"An NNTP client class based on:\n- RFC 977: Network News Transfer Protocol\n- RFC 2980: Common NNTP Extensions\n- RFC 3977: Network News Transfer Protocol (version 2)\n\nExample:\n\n>>> from nntplib import NNTP\n>>> s = NNTP('news')\n>>> resp, count, first, last, name = s.group('comp.lang.python')\n>>> print('Group', name, 'has', count, 'articles, range', first, 'to', last)\nGroup comp.lang.python has 51 articles, range 5770 to 5821\n>>> resp, subs = s.xhdr('subject', '{0}-{1}'.format(first, last))\n>>> resp = s.quit()\n>>>\n\nHere 'resp' is the server response line.\nError responses are turned into exceptions.\n\nTo post an article from a file:\n>>> f = open(filename, 'rb') # file containing article, including header\n>>> resp = s.post(f)\n>>>\n\nFor descriptions of all methods, read the comments in the code below.\nNote that all arguments and return values representing article numbers\nare strings, not numbers, since they are rarely used for calculations.\n"
import re
import socket
import collections
import datetime
import sys

try:
    import ssl
except ImportError:
    _have_ssl = False
else:
    _have_ssl = True
from email.header import decode_header as _email_decode_header
from socket import _GLOBAL_DEFAULT_TIMEOUT

__all__ = [
    "NNTP",
    "NNTPError",
    "NNTPReplyError",
    "NNTPTemporaryError",
    "NNTPPermanentError",
    "NNTPProtocolError",
    "NNTPDataError",
    "decode_header",
]
_MAXLINE = 2048


class NNTPError(Exception):
    "Base class for all nntplib exceptions"

    def __init__(self, *args):
        Exception.__init__(self, *args)
        try:
            self.response = args[0]
        except IndexError:
            self.response = "No response given"


class NNTPReplyError(NNTPError):
    "Unexpected [123]xx reply"
    pass


class NNTPTemporaryError(NNTPError):
    "4xx errors"
    pass


class NNTPPermanentError(NNTPError):
    "5xx errors"
    pass


class NNTPProtocolError(NNTPError):
    "Response does not begin with [1-5]"
    pass


class NNTPDataError(NNTPError):
    "Error in response data"
    pass


NNTP_PORT = 119
NNTP_SSL_PORT = 563
_LONGRESP = {
    "100",
    "101",
    "211",
    "215",
    "220",
    "221",
    "222",
    "224",
    "225",
    "230",
    "231",
    "282",
}
_DEFAULT_OVERVIEW_FMT = [
    "subject",
    "from",
    "date",
    "message-id",
    "references",
    ":bytes",
    ":lines",
]
_OVERVIEW_FMT_ALTERNATIVES = {"bytes": ":bytes", "lines": ":lines"}
_CRLF = b"\r\n"
GroupInfo = collections.namedtuple("GroupInfo", ["group", "last", "first", "flag"])
ArticleInfo = collections.namedtuple("ArticleInfo", ["number", "message_id", "lines"])


def decode_header(header_str):
    "Takes a unicode string representing a munged header value\n    and decodes it as a (possibly non-ASCII) readable value."
    parts = []
    for (v, enc) in _email_decode_header(header_str):
        if isinstance(v, bytes):
            parts.append(v.decode((enc or "ascii")))
        else:
            parts.append(v)
    return "".join(parts)


def _parse_overview_fmt(lines):
    "Parse a list of string representing the response to LIST OVERVIEW.FMT\n    and return a list of header/metadata names.\n    Raises NNTPDataError if the response is not compliant\n    (cf. RFC 3977, section 8.4)."
    fmt = []
    for line in lines:
        if line[0] == ":":
            (name, _, suffix) = line[1:].partition(":")
            name = ":" + name
        else:
            (name, _, suffix) = line.partition(":")
        name = name.lower()
        name = _OVERVIEW_FMT_ALTERNATIVES.get(name, name)
        fmt.append(name)
    defaults = _DEFAULT_OVERVIEW_FMT
    if len(fmt) < len(defaults):
        raise NNTPDataError("LIST OVERVIEW.FMT response too short")
    if fmt[: len(defaults)] != defaults:
        raise NNTPDataError("LIST OVERVIEW.FMT redefines default fields")
    return fmt


def _parse_overview(lines, fmt, data_process_func=None):
    "Parse the response to an OVER or XOVER command according to the\n    overview format `fmt`."
    n_defaults = len(_DEFAULT_OVERVIEW_FMT)
    overview = []
    for line in lines:
        fields = {}
        (article_number, *tokens) = line.split("\t")
        article_number = int(article_number)
        for (i, token) in enumerate(tokens):
            if i >= len(fmt):
                continue
            field_name = fmt[i]
            is_metadata = field_name.startswith(":")
            if (i >= n_defaults) and (not is_metadata):
                h = field_name + ": "
                if token and (token[: len(h)].lower() != h):
                    raise NNTPDataError(
                        "OVER/XOVER response doesn't include names of additional headers"
                    )
                token = token[len(h) :] if token else None
            fields[fmt[i]] = token
        overview.append((article_number, fields))
    return overview


def _parse_datetime(date_str, time_str=None):
    "Parse a pair of (date, time) strings, and return a datetime object.\n    If only the date is given, it is assumed to be date and time\n    concatenated together (e.g. response to the DATE command).\n    "
    if time_str is None:
        time_str = date_str[(-6):]
        date_str = date_str[:(-6)]
    hours = int(time_str[:2])
    minutes = int(time_str[2:4])
    seconds = int(time_str[4:])
    year = int(date_str[:(-4)])
    month = int(date_str[(-4):(-2)])
    day = int(date_str[(-2):])
    if year < 70:
        year += 2000
    elif year < 100:
        year += 1900
    return datetime.datetime(year, month, day, hours, minutes, seconds)


def _unparse_datetime(dt, legacy=False):
    "Format a date or datetime object as a pair of (date, time) strings\n    in the format required by the NEWNEWS and NEWGROUPS commands.  If a\n    date object is passed, the time is assumed to be midnight (00h00).\n\n    The returned representation depends on the legacy flag:\n    * if legacy is False (the default):\n      date has the YYYYMMDD format and time the HHMMSS format\n    * if legacy is True:\n      date has the YYMMDD format and time the HHMMSS format.\n    RFC 3977 compliant servers should understand both formats; therefore,\n    legacy is only needed when talking to old servers.\n    "
    if not isinstance(dt, datetime.datetime):
        time_str = "000000"
    else:
        time_str = "{0.hour:02d}{0.minute:02d}{0.second:02d}".format(dt)
    y = dt.year
    if legacy:
        y = y % 100
        date_str = "{0:02d}{1.month:02d}{1.day:02d}".format(y, dt)
    else:
        date_str = "{0:04d}{1.month:02d}{1.day:02d}".format(y, dt)
    return (date_str, time_str)


if _have_ssl:

    def _encrypt_on(sock, context, hostname):
        "Wrap a socket in SSL/TLS. Arguments:\n        - sock: Socket to wrap\n        - context: SSL context to use for the encrypted connection\n        Returns:\n        - sock: New, encrypted socket.\n        "
        if context is None:
            context = ssl._create_stdlib_context()
        return context.wrap_socket(sock, server_hostname=hostname)


class NNTP:
    encoding = "utf-8"
    errors = "surrogateescape"

    def __init__(
        self,
        host,
        port=NNTP_PORT,
        user=None,
        password=None,
        readermode=None,
        usenetrc=False,
        timeout=_GLOBAL_DEFAULT_TIMEOUT,
    ):
        "Initialize an instance.  Arguments:\n        - host: hostname to connect to\n        - port: port to connect to (default the standard NNTP port)\n        - user: username to authenticate with\n        - password: password to use with username\n        - readermode: if true, send 'mode reader' command after\n                      connecting.\n        - usenetrc: allow loading username and password from ~/.netrc file\n                    if not specified explicitly\n        - timeout: timeout (in seconds) used for socket connections\n\n        readermode is sometimes necessary if you are connecting to an\n        NNTP server on the local machine and intend to call\n        reader-specific commands, such as `group'.  If you get\n        unexpected NNTPPermanentErrors, you might need to set\n        readermode.\n        "
        self.host = host
        self.port = port
        self.sock = self._create_socket(timeout)
        self.file = None
        try:
            self.file = self.sock.makefile("rwb")
            self._base_init(readermode)
            if user or usenetrc:
                self.login(user, password, usenetrc)
        except:
            if self.file:
                self.file.close()
            self.sock.close()
            raise

    def _base_init(self, readermode):
        "Partial initialization for the NNTP protocol.\n        This instance method is extracted for supporting the test code.\n        "
        self.debugging = 0
        self.welcome = self._getresp()
        self._caps = None
        self.getcapabilities()
        self.readermode_afterauth = False
        if readermode and ("READER" not in self._caps):
            self._setreadermode()
            if not self.readermode_afterauth:
                self._caps = None
                self.getcapabilities()
        self.tls_on = False
        self.authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        is_connected = lambda: hasattr(self, "file")
        if is_connected():
            try:
                self.quit()
            except (OSError, EOFError):
                pass
            finally:
                if is_connected():
                    self._close()

    def _create_socket(self, timeout):
        if (timeout is not None) and (not timeout):
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        sys.audit("nntplib.connect", self, self.host, self.port)
        return socket.create_connection((self.host, self.port), timeout)

    def getwelcome(self):
        "Get the welcome message from the server\n        (this is read and squirreled away by __init__()).\n        If the response code is 200, posting is allowed;\n        if it 201, posting is not allowed."
        if self.debugging:
            print("*welcome*", repr(self.welcome))
        return self.welcome

    def getcapabilities(self):
        "Get the server capabilities, as read by __init__().\n        If the CAPABILITIES command is not supported, an empty dict is\n        returned."
        if self._caps is None:
            self.nntp_version = 1
            self.nntp_implementation = None
            try:
                (resp, caps) = self.capabilities()
            except (NNTPPermanentError, NNTPTemporaryError):
                self._caps = {}
            else:
                self._caps = caps
                if "VERSION" in caps:
                    self.nntp_version = max(map(int, caps["VERSION"]))
                if "IMPLEMENTATION" in caps:
                    self.nntp_implementation = " ".join(caps["IMPLEMENTATION"])
        return self._caps

    def set_debuglevel(self, level):
        "Set the debugging level.  Argument 'level' means:\n        0: no debugging output (default)\n        1: print commands and responses but not body text etc.\n        2: also print raw lines read and sent before stripping CR/LF"
        self.debugging = level

    debug = set_debuglevel

    def _putline(self, line):
        "Internal: send one line to the server, appending CRLF.\n        The `line` must be a bytes-like object."
        sys.audit("nntplib.putline", self, line)
        line = line + _CRLF
        if self.debugging > 1:
            print("*put*", repr(line))
        self.file.write(line)
        self.file.flush()

    def _putcmd(self, line):
        "Internal: send one command to the server (through _putline()).\n        The `line` must be a unicode string."
        if self.debugging:
            print("*cmd*", repr(line))
        line = line.encode(self.encoding, self.errors)
        self._putline(line)

    def _getline(self, strip_crlf=True):
        "Internal: return one line from the server, stripping _CRLF.\n        Raise EOFError if the connection is closed.\n        Returns a bytes object."
        line = self.file.readline((_MAXLINE + 1))
        if len(line) > _MAXLINE:
            raise NNTPDataError("line too long")
        if self.debugging > 1:
            print("*get*", repr(line))
        if not line:
            raise EOFError
        if strip_crlf:
            if line[(-2):] == _CRLF:
                line = line[:(-2)]
            elif line[(-1):] in _CRLF:
                line = line[:(-1)]
        return line

    def _getresp(self):
        "Internal: get a response from the server.\n        Raise various errors if the response indicates an error.\n        Returns a unicode string."
        resp = self._getline()
        if self.debugging:
            print("*resp*", repr(resp))
        resp = resp.decode(self.encoding, self.errors)
        c = resp[:1]
        if c == "4":
            raise NNTPTemporaryError(resp)
        if c == "5":
            raise NNTPPermanentError(resp)
        if c not in "123":
            raise NNTPProtocolError(resp)
        return resp

    def _getlongresp(self, file=None):
        "Internal: get a response plus following text from the server.\n        Raise various errors if the response indicates an error.\n\n        Returns a (response, lines) tuple where `response` is a unicode\n        string and `lines` is a list of bytes objects.\n        If `file` is a file-like object, it must be open in binary mode.\n        "
        openedFile = None
        try:
            if isinstance(file, (str, bytes)):
                openedFile = file = open(file, "wb")
            resp = self._getresp()
            if resp[:3] not in _LONGRESP:
                raise NNTPReplyError(resp)
            lines = []
            if file is not None:
                terminators = ((b"." + _CRLF), b".\n")
                while 1:
                    line = self._getline(False)
                    if line in terminators:
                        break
                    if line.startswith(b".."):
                        line = line[1:]
                    file.write(line)
            else:
                terminator = b"."
                while 1:
                    line = self._getline()
                    if line == terminator:
                        break
                    if line.startswith(b".."):
                        line = line[1:]
                    lines.append(line)
        finally:
            if openedFile:
                openedFile.close()
        return (resp, lines)

    def _shortcmd(self, line):
        "Internal: send a command and get the response.\n        Same return value as _getresp()."
        self._putcmd(line)
        return self._getresp()

    def _longcmd(self, line, file=None):
        "Internal: send a command and get the response plus following text.\n        Same return value as _getlongresp()."
        self._putcmd(line)
        return self._getlongresp(file)

    def _longcmdstring(self, line, file=None):
        "Internal: send a command and get the response plus following text.\n        Same as _longcmd() and _getlongresp(), except that the returned `lines`\n        are unicode strings rather than bytes objects.\n        "
        self._putcmd(line)
        (resp, list) = self._getlongresp(file)
        return (resp, [line.decode(self.encoding, self.errors) for line in list])

    def _getoverviewfmt(self):
        "Internal: get the overview format. Queries the server if not\n        already done, else returns the cached value."
        try:
            return self._cachedoverviewfmt
        except AttributeError:
            pass
        try:
            (resp, lines) = self._longcmdstring("LIST OVERVIEW.FMT")
        except NNTPPermanentError:
            fmt = _DEFAULT_OVERVIEW_FMT[:]
        else:
            fmt = _parse_overview_fmt(lines)
        self._cachedoverviewfmt = fmt
        return fmt

    def _grouplist(self, lines):
        return [GroupInfo(*line.split()) for line in lines]

    def capabilities(self):
        "Process a CAPABILITIES command.  Not supported by all servers.\n        Return:\n        - resp: server response if successful\n        - caps: a dictionary mapping capability names to lists of tokens\n        (for example {'VERSION': ['2'], 'OVER': [], LIST: ['ACTIVE', 'HEADERS'] })\n        "
        caps = {}
        (resp, lines) = self._longcmdstring("CAPABILITIES")
        for line in lines:
            (name, *tokens) = line.split()
            caps[name] = tokens
        return (resp, caps)

    def newgroups(self, date, *, file=None):
        "Process a NEWGROUPS command.  Arguments:\n        - date: a date or datetime object\n        Return:\n        - resp: server response if successful\n        - list: list of newsgroup names\n        "
        if not isinstance(date, (datetime.date, datetime.date)):
            raise TypeError(
                "the date parameter must be a date or datetime object, not '{:40}'".format(
                    date.__class__.__name__
                )
            )
        (date_str, time_str) = _unparse_datetime(date, (self.nntp_version < 2))
        cmd = "NEWGROUPS {0} {1}".format(date_str, time_str)
        (resp, lines) = self._longcmdstring(cmd, file)
        return (resp, self._grouplist(lines))

    def newnews(self, group, date, *, file=None):
        "Process a NEWNEWS command.  Arguments:\n        - group: group name or '*'\n        - date: a date or datetime object\n        Return:\n        - resp: server response if successful\n        - list: list of message ids\n        "
        if not isinstance(date, (datetime.date, datetime.date)):
            raise TypeError(
                "the date parameter must be a date or datetime object, not '{:40}'".format(
                    date.__class__.__name__
                )
            )
        (date_str, time_str) = _unparse_datetime(date, (self.nntp_version < 2))
        cmd = "NEWNEWS {0} {1} {2}".format(group, date_str, time_str)
        return self._longcmdstring(cmd, file)

    def list(self, group_pattern=None, *, file=None):
        "Process a LIST or LIST ACTIVE command. Arguments:\n        - group_pattern: a pattern indicating which groups to query\n        - file: Filename string or file object to store the result in\n        Returns:\n        - resp: server response if successful\n        - list: list of (group, last, first, flag) (strings)\n        "
        if group_pattern is not None:
            command = "LIST ACTIVE " + group_pattern
        else:
            command = "LIST"
        (resp, lines) = self._longcmdstring(command, file)
        return (resp, self._grouplist(lines))

    def _getdescriptions(self, group_pattern, return_all):
        line_pat = re.compile("^(?P<group>[^ \t]+)[ \t]+(.*)$")
        (resp, lines) = self._longcmdstring(("LIST NEWSGROUPS " + group_pattern))
        if not resp.startswith("215"):
            (resp, lines) = self._longcmdstring(("XGTITLE " + group_pattern))
        groups = {}
        for raw_line in lines:
            match = line_pat.search(raw_line.strip())
            if match:
                (name, desc) = match.group(1, 2)
                if not return_all:
                    return desc
                groups[name] = desc
        if return_all:
            return (resp, groups)
        else:
            return ""

    def description(self, group):
        "Get a description for a single group.  If more than one\n        group matches ('group' is a pattern), return the first.  If no\n        group matches, return an empty string.\n\n        This elides the response code from the server, since it can\n        only be '215' or '285' (for xgtitle) anyway.  If the response\n        code is needed, use the 'descriptions' method.\n\n        NOTE: This neither checks for a wildcard in 'group' nor does\n        it check whether the group actually exists."
        return self._getdescriptions(group, False)

    def descriptions(self, group_pattern):
        "Get descriptions for a range of groups."
        return self._getdescriptions(group_pattern, True)

    def group(self, name):
        "Process a GROUP command.  Argument:\n        - group: the group name\n        Returns:\n        - resp: server response if successful\n        - count: number of articles\n        - first: first article number\n        - last: last article number\n        - name: the group name\n        "
        resp = self._shortcmd(("GROUP " + name))
        if not resp.startswith("211"):
            raise NNTPReplyError(resp)
        words = resp.split()
        count = first = last = 0
        n = len(words)
        if n > 1:
            count = words[1]
            if n > 2:
                first = words[2]
                if n > 3:
                    last = words[3]
                    if n > 4:
                        name = words[4].lower()
        return (resp, int(count), int(first), int(last), name)

    def help(self, *, file=None):
        "Process a HELP command. Argument:\n        - file: Filename string or file object to store the result in\n        Returns:\n        - resp: server response if successful\n        - list: list of strings returned by the server in response to the\n                HELP command\n        "
        return self._longcmdstring("HELP", file)

    def _statparse(self, resp):
        "Internal: parse the response line of a STAT, NEXT, LAST,\n        ARTICLE, HEAD or BODY command."
        if not resp.startswith("22"):
            raise NNTPReplyError(resp)
        words = resp.split()
        art_num = int(words[1])
        message_id = words[2]
        return (resp, art_num, message_id)

    def _statcmd(self, line):
        "Internal: process a STAT, NEXT or LAST command."
        resp = self._shortcmd(line)
        return self._statparse(resp)

    def stat(self, message_spec=None):
        "Process a STAT command.  Argument:\n        - message_spec: article number or message id (if not specified,\n          the current article is selected)\n        Returns:\n        - resp: server response if successful\n        - art_num: the article number\n        - message_id: the message id\n        "
        if message_spec:
            return self._statcmd("STAT {0}".format(message_spec))
        else:
            return self._statcmd("STAT")

    def next(self):
        "Process a NEXT command.  No arguments.  Return as for STAT."
        return self._statcmd("NEXT")

    def last(self):
        "Process a LAST command.  No arguments.  Return as for STAT."
        return self._statcmd("LAST")

    def _artcmd(self, line, file=None):
        "Internal: process a HEAD, BODY or ARTICLE command."
        (resp, lines) = self._longcmd(line, file)
        (resp, art_num, message_id) = self._statparse(resp)
        return (resp, ArticleInfo(art_num, message_id, lines))

    def head(self, message_spec=None, *, file=None):
        "Process a HEAD command.  Argument:\n        - message_spec: article number or message id\n        - file: filename string or file object to store the headers in\n        Returns:\n        - resp: server response if successful\n        - ArticleInfo: (article number, message id, list of header lines)\n        "
        if message_spec is not None:
            cmd = "HEAD {0}".format(message_spec)
        else:
            cmd = "HEAD"
        return self._artcmd(cmd, file)

    def body(self, message_spec=None, *, file=None):
        "Process a BODY command.  Argument:\n        - message_spec: article number or message id\n        - file: filename string or file object to store the body in\n        Returns:\n        - resp: server response if successful\n        - ArticleInfo: (article number, message id, list of body lines)\n        "
        if message_spec is not None:
            cmd = "BODY {0}".format(message_spec)
        else:
            cmd = "BODY"
        return self._artcmd(cmd, file)

    def article(self, message_spec=None, *, file=None):
        "Process an ARTICLE command.  Argument:\n        - message_spec: article number or message id\n        - file: filename string or file object to store the article in\n        Returns:\n        - resp: server response if successful\n        - ArticleInfo: (article number, message id, list of article lines)\n        "
        if message_spec is not None:
            cmd = "ARTICLE {0}".format(message_spec)
        else:
            cmd = "ARTICLE"
        return self._artcmd(cmd, file)

    def slave(self):
        "Process a SLAVE command.  Returns:\n        - resp: server response if successful\n        "
        return self._shortcmd("SLAVE")

    def xhdr(self, hdr, str, *, file=None):
        "Process an XHDR command (optional server extension).  Arguments:\n        - hdr: the header type (e.g. 'subject')\n        - str: an article nr, a message id, or a range nr1-nr2\n        - file: Filename string or file object to store the result in\n        Returns:\n        - resp: server response if successful\n        - list: list of (nr, value) strings\n        "
        pat = re.compile("^([0-9]+) ?(.*)\n?")
        (resp, lines) = self._longcmdstring("XHDR {0} {1}".format(hdr, str), file)

        def remove_number(line):
            m = pat.match(line)
            return m.group(1, 2) if m else line

        return (resp, [remove_number(line) for line in lines])

    def xover(self, start, end, *, file=None):
        "Process an XOVER command (optional server extension) Arguments:\n        - start: start of range\n        - end: end of range\n        - file: Filename string or file object to store the result in\n        Returns:\n        - resp: server response if successful\n        - list: list of dicts containing the response fields\n        "
        (resp, lines) = self._longcmdstring("XOVER {0}-{1}".format(start, end), file)
        fmt = self._getoverviewfmt()
        return (resp, _parse_overview(lines, fmt))

    def over(self, message_spec, *, file=None):
        "Process an OVER command.  If the command isn't supported, fall\n        back to XOVER. Arguments:\n        - message_spec:\n            - either a message id, indicating the article to fetch\n              information about\n            - or a (start, end) tuple, indicating a range of article numbers;\n              if end is None, information up to the newest message will be\n              retrieved\n            - or None, indicating the current article number must be used\n        - file: Filename string or file object to store the result in\n        Returns:\n        - resp: server response if successful\n        - list: list of dicts containing the response fields\n\n        NOTE: the \"message id\" form isn't supported by XOVER\n        "
        cmd = "OVER" if ("OVER" in self._caps) else "XOVER"
        if isinstance(message_spec, (tuple, list)):
            (start, end) = message_spec
            cmd += " {0}-{1}".format(start, (end or ""))
        elif message_spec is not None:
            cmd = (cmd + " ") + message_spec
        (resp, lines) = self._longcmdstring(cmd, file)
        fmt = self._getoverviewfmt()
        return (resp, _parse_overview(lines, fmt))

    def date(self):
        "Process the DATE command.\n        Returns:\n        - resp: server response if successful\n        - date: datetime object\n        "
        resp = self._shortcmd("DATE")
        if not resp.startswith("111"):
            raise NNTPReplyError(resp)
        elem = resp.split()
        if len(elem) != 2:
            raise NNTPDataError(resp)
        date = elem[1]
        if len(date) != 14:
            raise NNTPDataError(resp)
        return (resp, _parse_datetime(date, None))

    def _post(self, command, f):
        resp = self._shortcmd(command)
        if not resp.startswith("3"):
            raise NNTPReplyError(resp)
        if isinstance(f, (bytes, bytearray)):
            f = f.splitlines()
        for line in f:
            if not line.endswith(_CRLF):
                line = line.rstrip(b"\r\n") + _CRLF
            if line.startswith(b"."):
                line = b"." + line
            self.file.write(line)
        self.file.write(b".\r\n")
        self.file.flush()
        return self._getresp()

    def post(self, data):
        "Process a POST command.  Arguments:\n        - data: bytes object, iterable or file containing the article\n        Returns:\n        - resp: server response if successful"
        return self._post("POST", data)

    def ihave(self, message_id, data):
        "Process an IHAVE command.  Arguments:\n        - message_id: message-id of the article\n        - data: file containing the article\n        Returns:\n        - resp: server response if successful\n        Note that if the server refuses the article an exception is raised."
        return self._post("IHAVE {0}".format(message_id), data)

    def _close(self):
        try:
            if self.file:
                self.file.close()
                del self.file
        finally:
            self.sock.close()

    def quit(self):
        "Process a QUIT command and close the socket.  Returns:\n        - resp: server response if successful"
        try:
            resp = self._shortcmd("QUIT")
        finally:
            self._close()
        return resp

    def login(self, user=None, password=None, usenetrc=True):
        if self.authenticated:
            raise ValueError("Already logged in.")
        if (not user) and (not usenetrc):
            raise ValueError("At least one of `user` and `usenetrc` must be specified")
        try:
            if usenetrc and (not user):
                import netrc

                credentials = netrc.netrc()
                auth = credentials.authenticators(self.host)
                if auth:
                    user = auth[0]
                    password = auth[2]
        except OSError:
            pass
        if not user:
            return
        resp = self._shortcmd(("authinfo user " + user))
        if resp.startswith("381"):
            if not password:
                raise NNTPReplyError(resp)
            else:
                resp = self._shortcmd(("authinfo pass " + password))
                if not resp.startswith("281"):
                    raise NNTPPermanentError(resp)
        self._caps = None
        self.getcapabilities()
        if self.readermode_afterauth and ("READER" not in self._caps):
            self._setreadermode()
            self._caps = None
            self.getcapabilities()

    def _setreadermode(self):
        try:
            self.welcome = self._shortcmd("mode reader")
        except NNTPPermanentError:
            pass
        except NNTPTemporaryError as e:
            if e.response.startswith("480"):
                self.readermode_afterauth = True
            else:
                raise

    if _have_ssl:

        def starttls(self, context=None):
            "Process a STARTTLS command. Arguments:\n            - context: SSL context to use for the encrypted connection\n            "
            if self.tls_on:
                raise ValueError("TLS is already enabled.")
            if self.authenticated:
                raise ValueError("TLS cannot be started after authentication.")
            resp = self._shortcmd("STARTTLS")
            if resp.startswith("382"):
                self.file.close()
                self.sock = _encrypt_on(self.sock, context, self.host)
                self.file = self.sock.makefile("rwb")
                self.tls_on = True
                self._caps = None
                self.getcapabilities()
            else:
                raise NNTPError("TLS failed to start.")


if _have_ssl:

    class NNTP_SSL(NNTP):
        def __init__(
            self,
            host,
            port=NNTP_SSL_PORT,
            user=None,
            password=None,
            ssl_context=None,
            readermode=None,
            usenetrc=False,
            timeout=_GLOBAL_DEFAULT_TIMEOUT,
        ):
            "This works identically to NNTP.__init__, except for the change\n            in default port and the `ssl_context` argument for SSL connections.\n            "
            self.ssl_context = ssl_context
            super().__init__(host, port, user, password, readermode, usenetrc, timeout)

        def _create_socket(self, timeout):
            sock = super()._create_socket(timeout)
            try:
                sock = _encrypt_on(sock, self.ssl_context, self.host)
            except:
                sock.close()
                raise
            else:
                return sock

    __all__.append("NNTP_SSL")
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="        nntplib built-in demo - display the latest articles in a newsgroup"
    )
    parser.add_argument(
        "-g",
        "--group",
        default="gmane.comp.python.general",
        help="group to fetch messages from (default: %(default)s)",
    )
    parser.add_argument(
        "-s",
        "--server",
        default="news.gmane.io",
        help="NNTP server hostname (default: %(default)s)",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=(-1),
        type=int,
        help=("NNTP port number (default: %s / %s)" % (NNTP_PORT, NNTP_SSL_PORT)),
    )
    parser.add_argument(
        "-n",
        "--nb-articles",
        default=10,
        type=int,
        help="number of articles to fetch (default: %(default)s)",
    )
    parser.add_argument(
        "-S", "--ssl", action="store_true", default=False, help="use NNTP over SSL"
    )
    args = parser.parse_args()
    port = args.port
    if not args.ssl:
        if port == (-1):
            port = NNTP_PORT
        s = NNTP(host=args.server, port=port)
    else:
        if port == (-1):
            port = NNTP_SSL_PORT
        s = NNTP_SSL(host=args.server, port=port)
    caps = s.getcapabilities()
    if "STARTTLS" in caps:
        s.starttls()
    (resp, count, first, last, name) = s.group(args.group)
    print("Group", name, "has", count, "articles, range", first, "to", last)

    def cut(s, lim):
        if len(s) > lim:
            s = s[: (lim - 4)] + "..."
        return s

    first = str(((int(last) - args.nb_articles) + 1))
    (resp, overviews) = s.xover(first, last)
    for (artnum, over) in overviews:
        author = decode_header(over["from"]).split("<", 1)[0]
        subject = decode_header(over["subject"])
        lines = int(over[":lines"])
        print(
            "{:7} {:20} {:42} ({})".format(
                artnum, cut(author, 20), cut(subject, 42), lines
            )
        )
    s.quit()
