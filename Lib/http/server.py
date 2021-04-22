"HTTP server classes.\n\nNote: BaseHTTPRequestHandler doesn't implement any HTTP request; see\nSimpleHTTPRequestHandler for simple implementations of GET, HEAD and POST,\nand CGIHTTPRequestHandler for CGI scripts.\n\nIt does, however, optionally implement HTTP/1.1 persistent connections,\nas of version 0.3.\n\nNotes on CGIHTTPRequestHandler\n------------------------------\n\nThis class implements GET and POST requests to cgi-bin scripts.\n\nIf the os.fork() function is not present (e.g. on Windows),\nsubprocess.Popen() is used as a fallback, with slightly altered semantics.\n\nIn all cases, the implementation is intentionally naive -- all\nrequests are executed synchronously.\n\nSECURITY WARNING: DON'T USE THIS CODE UNLESS YOU ARE INSIDE A FIREWALL\n-- it may execute arbitrary Python code or external programs.\n\nNote that status code 200 is sent prior to execution of a CGI script, so\nscripts cannot send other status codes such as 302 (redirect).\n\nXXX To do:\n\n- log requests even later (to capture byte count)\n- log user-agent header and other interesting goodies\n- send error log to separate file\n"
__version__ = "0.6"
__all__ = [
    "HTTPServer",
    "ThreadingHTTPServer",
    "BaseHTTPRequestHandler",
    "SimpleHTTPRequestHandler",
    "CGIHTTPRequestHandler",
]
import copy
import datetime
import email.utils
import html
import http.client
import io
import mimetypes
import os
import posixpath
import select
import shutil
import socket
import socketserver
import sys
import time
import urllib.parse
import contextlib
from functools import partial
from http import HTTPStatus

DEFAULT_ERROR_MESSAGE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"\n        "http://www.w3.org/TR/html4/strict.dtd">\n<html>\n    <head>\n        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">\n        <title>Error response</title>\n    </head>\n    <body>\n        <h1>Error response</h1>\n        <p>Error code: %(code)d</p>\n        <p>Message: %(message)s.</p>\n        <p>Error code explanation: %(code)s - %(explain)s.</p>\n    </body>\n</html>\n'
DEFAULT_ERROR_CONTENT_TYPE = "text/html;charset=utf-8"


class HTTPServer(socketserver.TCPServer):
    allow_reuse_address = 1

    def server_bind(self):
        "Override server_bind to store the server name."
        socketserver.TCPServer.server_bind(self)
        (host, port) = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class BaseHTTPRequestHandler(socketserver.StreamRequestHandler):
    'HTTP request handler base class.\n\n    The following explanation of HTTP serves to guide you through the\n    code as well as to expose any misunderstandings I may have about\n    HTTP (so you don\'t need to read the code to figure out I\'m wrong\n    :-).\n\n    HTTP (HyperText Transfer Protocol) is an extensible protocol on\n    top of a reliable stream transport (e.g. TCP/IP).  The protocol\n    recognizes three parts to a request:\n\n    1. One line identifying the request type and path\n    2. An optional set of RFC-822-style headers\n    3. An optional data part\n\n    The headers and data are separated by a blank line.\n\n    The first line of the request has the form\n\n    <command> <path> <version>\n\n    where <command> is a (case-sensitive) keyword such as GET or POST,\n    <path> is a string containing path information for the request,\n    and <version> should be the string "HTTP/1.0" or "HTTP/1.1".\n    <path> is encoded using the URL encoding scheme (using %xx to signify\n    the ASCII character with hex code xx).\n\n    The specification specifies that lines are separated by CRLF but\n    for compatibility with the widest range of clients recommends\n    servers also handle LF.  Similarly, whitespace in the request line\n    is treated sensibly (allowing multiple spaces between components\n    and allowing trailing whitespace).\n\n    Similarly, for output, lines ought to be separated by CRLF pairs\n    but most clients grok LF characters just fine.\n\n    If the first line of the request has the form\n\n    <command> <path>\n\n    (i.e. <version> is left out) then this is assumed to be an HTTP\n    0.9 request; this form has no optional headers and data part and\n    the reply consists of just the data.\n\n    The reply form of the HTTP 1.x protocol again has three parts:\n\n    1. One line giving the response code\n    2. An optional set of RFC-822-style headers\n    3. The data\n\n    Again, the headers and data are separated by a blank line.\n\n    The response code line has the form\n\n    <version> <responsecode> <responsestring>\n\n    where <version> is the protocol version ("HTTP/1.0" or "HTTP/1.1"),\n    <responsecode> is a 3-digit response code indicating success or\n    failure of the request, and <responsestring> is an optional\n    human-readable string explaining what the response code means.\n\n    This server parses the request and the headers, and then calls a\n    function specific to the request type (<command>).  Specifically,\n    a request SPAM will be handled by a method do_SPAM().  If no\n    such method exists the server sends an error response to the\n    client.  If it exists, it is called with no arguments:\n\n    do_SPAM()\n\n    Note that the request name is case sensitive (i.e. SPAM and spam\n    are different requests).\n\n    The various request details are stored in instance variables:\n\n    - client_address is the client IP address in the form (host,\n    port);\n\n    - command, path and version are the broken-down request line;\n\n    - headers is an instance of email.message.Message (or a derived\n    class) containing the header information;\n\n    - rfile is a file object open for reading positioned at the\n    start of the optional input data part;\n\n    - wfile is a file object open for writing.\n\n    IT IS IMPORTANT TO ADHERE TO THE PROTOCOL FOR WRITING!\n\n    The first thing to be written must be the response line.  Then\n    follow 0 or more header lines, then a blank line, and then the\n    actual data (if any).  The meaning of the header lines depends on\n    the command executed by the server; in most cases, when data is\n    returned, there should be at least one header line of the form\n\n    Content-type: <type>/<subtype>\n\n    where <type> and <subtype> should be registered MIME types,\n    e.g. "text/html" or "text/plain".\n\n    '
    sys_version = "Python/" + sys.version.split()[0]
    server_version = "BaseHTTP/" + __version__
    error_message_format = DEFAULT_ERROR_MESSAGE
    error_content_type = DEFAULT_ERROR_CONTENT_TYPE
    default_request_version = "HTTP/0.9"

    def parse_request(self):
        "Parse a request (internal).\n\n        The request should be stored in self.raw_requestline; the results\n        are in self.command, self.path, self.request_version and\n        self.headers.\n\n        Return True for success, False for failure; on failure, any relevant\n        error response has already been sent back.\n\n        "
        self.command = None
        self.request_version = version = self.default_request_version
        self.close_connection = True
        requestline = str(self.raw_requestline, "iso-8859-1")
        requestline = requestline.rstrip("\r\n")
        self.requestline = requestline
        words = requestline.split()
        if len(words) == 0:
            return False
        if len(words) >= 3:
            version = words[(-1)]
            try:
                if not version.startswith("HTTP/"):
                    raise ValueError
                base_version_number = version.split("/", 1)[1]
                version_number = base_version_number.split(".")
                if len(version_number) != 2:
                    raise ValueError
                version_number = (int(version_number[0]), int(version_number[1]))
            except (ValueError, IndexError):
                self.send_error(
                    HTTPStatus.BAD_REQUEST, ("Bad request version (%r)" % version)
                )
                return False
            if (version_number >= (1, 1)) and (self.protocol_version >= "HTTP/1.1"):
                self.close_connection = False
            if version_number >= (2, 0):
                self.send_error(
                    HTTPStatus.HTTP_VERSION_NOT_SUPPORTED,
                    ("Invalid HTTP version (%s)" % base_version_number),
                )
                return False
            self.request_version = version
        if not (2 <= len(words) <= 3):
            self.send_error(
                HTTPStatus.BAD_REQUEST, ("Bad request syntax (%r)" % requestline)
            )
            return False
        (command, path) = words[:2]
        if len(words) == 2:
            self.close_connection = True
            if command != "GET":
                self.send_error(
                    HTTPStatus.BAD_REQUEST, ("Bad HTTP/0.9 request type (%r)" % command)
                )
                return False
        (self.command, self.path) = (command, path)
        try:
            self.headers = http.client.parse_headers(
                self.rfile, _class=self.MessageClass
            )
        except http.client.LineTooLong as err:
            self.send_error(
                HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Line too long", str(err)
            )
            return False
        except http.client.HTTPException as err:
            self.send_error(
                HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Too many headers", str(err)
            )
            return False
        conntype = self.headers.get("Connection", "")
        if conntype.lower() == "close":
            self.close_connection = True
        elif (conntype.lower() == "keep-alive") and (
            self.protocol_version >= "HTTP/1.1"
        ):
            self.close_connection = False
        expect = self.headers.get("Expect", "")
        if (
            (expect.lower() == "100-continue")
            and (self.protocol_version >= "HTTP/1.1")
            and (self.request_version >= "HTTP/1.1")
        ):
            if not self.handle_expect_100():
                return False
        return True

    def handle_expect_100(self):
        'Decide what to do with an "Expect: 100-continue" header.\n\n        If the client is expecting a 100 Continue response, we must\n        respond with either a 100 Continue or a final response before\n        waiting for the request body. The default is to always respond\n        with a 100 Continue. You can behave differently (for example,\n        reject unauthorized requests) by overriding this method.\n\n        This method should either return True (possibly after sending\n        a 100 Continue response) or send an error response and return\n        False.\n\n        '
        self.send_response_only(HTTPStatus.CONTINUE)
        self.end_headers()
        return True

    def handle_one_request(self):
        "Handle a single HTTP request.\n\n        You normally don't need to override this method; see the class\n        __doc__ string for information on how to handle specific HTTP\n        commands such as GET and POST.\n\n        "
        try:
            self.raw_requestline = self.rfile.readline(65537)
            if len(self.raw_requestline) > 65536:
                self.requestline = ""
                self.request_version = ""
                self.command = ""
                self.send_error(HTTPStatus.REQUEST_URI_TOO_LONG)
                return
            if not self.raw_requestline:
                self.close_connection = True
                return
            if not self.parse_request():
                return
            mname = "do_" + self.command
            if not hasattr(self, mname):
                self.send_error(
                    HTTPStatus.NOT_IMPLEMENTED,
                    ("Unsupported method (%r)" % self.command),
                )
                return
            method = getattr(self, mname)
            method()
            self.wfile.flush()
        except TimeoutError as e:
            self.log_error("Request timed out: %r", e)
            self.close_connection = True
            return

    def handle(self):
        "Handle multiple requests if necessary."
        self.close_connection = True
        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

    def send_error(self, code, message=None, explain=None):
        "Send and log an error reply.\n\n        Arguments are\n        * code:    an HTTP error code\n                   3 digits\n        * message: a simple optional 1 line reason phrase.\n                   *( HTAB / SP / VCHAR / %x80-FF )\n                   defaults to short entry matching the response code\n        * explain: a detailed message defaults to the long entry\n                   matching the response code.\n\n        This sends an error response (so it must be called before any\n        output has been generated), logs the error, and finally sends\n        a piece of HTML explaining the error to the user.\n\n        "
        try:
            (shortmsg, longmsg) = self.responses[code]
        except KeyError:
            (shortmsg, longmsg) = ("???", "???")
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        self.log_error("code %d, message %s", code, message)
        self.send_response(code, message)
        self.send_header("Connection", "close")
        body = None
        if (code >= 200) and (
            code
            not in (
                HTTPStatus.NO_CONTENT,
                HTTPStatus.RESET_CONTENT,
                HTTPStatus.NOT_MODIFIED,
            )
        ):
            content = self.error_message_format % {
                "code": code,
                "message": html.escape(message, quote=False),
                "explain": html.escape(explain, quote=False),
            }
            body = content.encode("UTF-8", "replace")
            self.send_header("Content-Type", self.error_content_type)
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if (self.command != "HEAD") and body:
            self.wfile.write(body)

    def send_response(self, code, message=None):
        "Add the response header to the headers buffer and log the\n        response code.\n\n        Also send two standard headers with the server software\n        version and the current date.\n\n        "
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header("Server", self.version_string())
        self.send_header("Date", self.date_time_string())

    def send_response_only(self, code, message=None):
        "Send the response header only."
        if self.request_version != "HTTP/0.9":
            if message is None:
                if code in self.responses:
                    message = self.responses[code][0]
                else:
                    message = ""
            if not hasattr(self, "_headers_buffer"):
                self._headers_buffer = []
            self._headers_buffer.append(
                ("%s %d %s\r\n" % (self.protocol_version, code, message)).encode(
                    "latin-1", "strict"
                )
            )

    def send_header(self, keyword, value):
        "Send a MIME header to the headers buffer."
        if self.request_version != "HTTP/0.9":
            if not hasattr(self, "_headers_buffer"):
                self._headers_buffer = []
            self._headers_buffer.append(
                ("%s: %s\r\n" % (keyword, value)).encode("latin-1", "strict")
            )
        if keyword.lower() == "connection":
            if value.lower() == "close":
                self.close_connection = True
            elif value.lower() == "keep-alive":
                self.close_connection = False

    def end_headers(self):
        "Send the blank line ending the MIME headers."
        if self.request_version != "HTTP/0.9":
            self._headers_buffer.append(b"\r\n")
            self.flush_headers()

    def flush_headers(self):
        if hasattr(self, "_headers_buffer"):
            self.wfile.write(b"".join(self._headers_buffer))
            self._headers_buffer = []

    def log_request(self, code="-", size="-"):
        "Log an accepted request.\n\n        This is called by send_response().\n\n        "
        if isinstance(code, HTTPStatus):
            code = code.value
        self.log_message('"%s" %s %s', self.requestline, str(code), str(size))

    def log_error(self, format, *args):
        "Log an error.\n\n        This is called when a request cannot be fulfilled.  By\n        default it passes the message on to log_message().\n\n        Arguments are the same as for log_message().\n\n        XXX This should go to the separate error log.\n\n        "
        self.log_message(format, *args)

    def log_message(self, format, *args):
        "Log an arbitrary message.\n\n        This is used by all other logging functions.  Override\n        it if you have specific logging wishes.\n\n        The first argument, FORMAT, is a format string for the\n        message to be logged.  If the format string contains\n        any % escapes requiring parameters, they should be\n        specified as subsequent arguments (it's just like\n        printf!).\n\n        The client ip and current date/time are prefixed to\n        every message.\n\n        "
        sys.stderr.write(
            (
                "%s - - [%s] %s\n"
                % (self.address_string(), self.log_date_time_string(), (format % args))
            )
        )

    def version_string(self):
        "Return the server software version string."
        return (self.server_version + " ") + self.sys_version

    def date_time_string(self, timestamp=None):
        "Return the current date and time formatted for a message header."
        if timestamp is None:
            timestamp = time.time()
        return email.utils.formatdate(timestamp, usegmt=True)

    def log_date_time_string(self):
        "Return the current time formatted for logging."
        now = time.time()
        (year, month, day, hh, mm, ss, x, y, z) = time.localtime(now)
        s = "%02d/%3s/%04d %02d:%02d:%02d" % (
            day,
            self.monthname[month],
            year,
            hh,
            mm,
            ss,
        )
        return s

    weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    monthname = [
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

    def address_string(self):
        "Return the client address."
        return self.client_address[0]

    protocol_version = "HTTP/1.0"
    MessageClass = http.client.HTTPMessage
    responses = {v: (v.phrase, v.description) for v in HTTPStatus.__members__.values()}


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    "Simple HTTP request handler with GET and HEAD commands.\n\n    This serves files from the current directory and any of its\n    subdirectories.  The MIME type for files is determined by\n    calling the .guess_type() method.\n\n    The GET and HEAD requests are identical except that the HEAD\n    request omits the actual contents of the file.\n\n    "
    server_version = "SimpleHTTP/" + __version__
    extensions_map = _encodings_map_default = {
        ".gz": "application/gzip",
        ".Z": "application/octet-stream",
        ".bz2": "application/x-bzip2",
        ".xz": "application/x-xz",
    }

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd()
        self.directory = os.fspath(directory)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        "Serve a GET request."
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        "Serve a HEAD request."
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        "Common code for GET and HEAD commands.\n\n        This sends the response code and MIME headers.\n\n        Return value is either a file object (which has to be copied\n        to the outputfile by the caller unless the command was HEAD,\n        and must be closed by the caller under all circumstances), or\n        None, in which case the caller has nothing further to do.\n\n        "
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], (parts[2] + "/"), parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in ("index.html", "index.htm"):
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            f = open(path, "rb")
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            fs = os.fstat(f.fileno())
            if ("If-Modified-Since" in self.headers) and (
                "If-None-Match" not in self.headers
            ):
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"]
                    )
                except (TypeError, IndexError, OverflowError, ValueError):
                    pass
                else:
                    if ims.tzinfo is None:
                        ims = ims.replace(tzinfo=datetime.timezone.utc)
                    if ims.tzinfo is datetime.timezone.utc:
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc
                        )
                        last_modif = last_modif.replace(microsecond=0)
                        if last_modif <= ims:
                            self.send_response(HTTPStatus.NOT_MODIFIED)
                            self.end_headers()
                            f.close()
                            return None
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def list_directory(self, path):
        "Helper to produce a directory listing (absent index.html).\n\n        Return value is either a file object, or None (indicating an\n        error).  In either case, the headers are sent, making the\n        interface the same as for send_head().\n\n        "
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "No permission to list directory")
            return None
        list.sort(key=(lambda a: a.lower()))
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path, errors="surrogatepass")
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = "Directory listing for %s" % displaypath
        r.append(
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
        )
        r.append("<html>\n<head>")
        r.append(
            ('<meta http-equiv="Content-Type" content="text/html; charset=%s">' % enc)
        )
        r.append(("<title>%s</title>\n</head>" % title))
        r.append(("<body>\n<h1>%s</h1>" % title))
        r.append("<hr>\n<ul>")
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
            r.append(
                (
                    '<li><a href="%s">%s</a></li>'
                    % (
                        urllib.parse.quote(linkname, errors="surrogatepass"),
                        html.escape(displayname, quote=False),
                    )
                )
            )
        r.append("</ul>\n<hr>\n</body>\n</html>\n")
        encoded = "\n".join(r).encode(enc, "surrogateescape")
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", ("text/html; charset=%s" % enc))
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def translate_path(self, path):
        "Translate a /-separated PATH to the local filename syntax.\n\n        Components that mean special things to the local file system\n        (e.g. drive or directory names) are ignored.  (XXX They should\n        probably be diagnosed.)\n\n        "
        path = path.split("?", 1)[0]
        path = path.split("#", 1)[0]
        trailing_slash = path.rstrip().endswith("/")
        try:
            path = urllib.parse.unquote(path, errors="surrogatepass")
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        words = path.split("/")
        words = filter(None, words)
        path = self.directory
        for word in words:
            if os.path.dirname(word) or (word in (os.curdir, os.pardir)):
                continue
            path = os.path.join(path, word)
        if trailing_slash:
            path += "/"
        return path

    def copyfile(self, source, outputfile):
        "Copy all data between two file objects.\n\n        The SOURCE argument is a file object open for reading\n        (or anything with a read() method) and the DESTINATION\n        argument is a file object open for writing (or\n        anything with a write() method).\n\n        The only reason for overriding this would be to change\n        the block size or perhaps to replace newlines by CRLF\n        -- note however that this the default server uses this\n        to copy binary data as well.\n\n        "
        shutil.copyfileobj(source, outputfile)

    def guess_type(self, path):
        "Guess the type of a file.\n\n        Argument is a PATH (a filename).\n\n        Return value is a string of the form type/subtype,\n        usable for a MIME Content-type header.\n\n        The default implementation looks the file's extension\n        up in the table self.extensions_map, using application/octet-stream\n        as a default; however it would be permissible (if\n        slow) to look inside the data to make a better guess.\n\n        "
        (base, ext) = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        (guess, _) = mimetypes.guess_type(path)
        if guess:
            return guess
        return "application/octet-stream"


def _url_collapse_path(path):
    "\n    Given a URL path, remove extra '/'s and '.' path elements and collapse\n    any '..' references and returns a collapsed path.\n\n    Implements something akin to RFC-2396 5.2 step 6 to parse relative paths.\n    The utility of this function is limited to is_cgi method and helps\n    preventing some security attacks.\n\n    Returns: The reconstituted URL, which will always start with a '/'.\n\n    Raises: IndexError if too many '..' occur within the path.\n\n    "
    (path, _, query) = path.partition("?")
    path = urllib.parse.unquote(path)
    path_parts = path.split("/")
    head_parts = []
    for part in path_parts[:(-1)]:
        if part == "..":
            head_parts.pop()
        elif part and (part != "."):
            head_parts.append(part)
    if path_parts:
        tail_part = path_parts.pop()
        if tail_part:
            if tail_part == "..":
                head_parts.pop()
                tail_part = ""
            elif tail_part == ".":
                tail_part = ""
    else:
        tail_part = ""
    if query:
        tail_part = "?".join((tail_part, query))
    splitpath = (("/" + "/".join(head_parts)), tail_part)
    collapsed_path = "/".join(splitpath)
    return collapsed_path


nobody = None


def nobody_uid():
    "Internal routine to get nobody's uid"
    global nobody
    if nobody:
        return nobody
    try:
        import pwd
    except ImportError:
        return -1
    try:
        nobody = pwd.getpwnam("nobody")[2]
    except KeyError:
        nobody = 1 + max((x[2] for x in pwd.getpwall()))
    return nobody


def executable(path):
    "Test for executable file."
    return os.access(path, os.X_OK)


class CGIHTTPRequestHandler(SimpleHTTPRequestHandler):
    "Complete HTTP server with GET, HEAD and POST commands.\n\n    GET and HEAD also support running CGI scripts.\n\n    The POST command is *only* implemented for CGI scripts.\n\n    "
    have_fork = hasattr(os, "fork")
    rbufsize = 0

    def do_POST(self):
        "Serve a POST request.\n\n        This is only implemented for CGI scripts.\n\n        "
        if self.is_cgi():
            self.run_cgi()
        else:
            self.send_error(HTTPStatus.NOT_IMPLEMENTED, "Can only POST to CGI scripts")

    def send_head(self):
        "Version of send_head that support CGI scripts"
        if self.is_cgi():
            return self.run_cgi()
        else:
            return SimpleHTTPRequestHandler.send_head(self)

    def is_cgi(self):
        "Test whether self.path corresponds to a CGI script.\n\n        Returns True and updates the cgi_info attribute to the tuple\n        (dir, rest) if self.path requires running a CGI script.\n        Returns False otherwise.\n\n        If any exception is raised, the caller should assume that\n        self.path was rejected as invalid and act accordingly.\n\n        The default implementation tests whether the normalized url\n        path begins with one of the strings in self.cgi_directories\n        (and the next character is a '/' or the end of the string).\n\n        "
        collapsed_path = _url_collapse_path(self.path)
        dir_sep = collapsed_path.find("/", 1)
        while (dir_sep > 0) and (
            not (collapsed_path[:dir_sep] in self.cgi_directories)
        ):
            dir_sep = collapsed_path.find("/", (dir_sep + 1))
        if dir_sep > 0:
            (head, tail) = (collapsed_path[:dir_sep], collapsed_path[(dir_sep + 1) :])
            self.cgi_info = (head, tail)
            return True
        return False

    cgi_directories = ["/cgi-bin", "/htbin"]

    def is_executable(self, path):
        "Test whether argument path is an executable file."
        return executable(path)

    def is_python(self, path):
        "Test whether argument path is a Python script."
        (head, tail) = os.path.splitext(path)
        return tail.lower() in (".py", ".pyw")

    def run_cgi(self):
        "Execute a CGI script."
        (dir, rest) = self.cgi_info
        path = (dir + "/") + rest
        i = path.find("/", (len(dir) + 1))
        while i >= 0:
            nextdir = path[:i]
            nextrest = path[(i + 1) :]
            scriptdir = self.translate_path(nextdir)
            if os.path.isdir(scriptdir):
                (dir, rest) = (nextdir, nextrest)
                i = path.find("/", (len(dir) + 1))
            else:
                break
        (rest, _, query) = rest.partition("?")
        i = rest.find("/")
        if i >= 0:
            (script, rest) = (rest[:i], rest[i:])
        else:
            (script, rest) = (rest, "")
        scriptname = (dir + "/") + script
        scriptfile = self.translate_path(scriptname)
        if not os.path.exists(scriptfile):
            self.send_error(
                HTTPStatus.NOT_FOUND, ("No such CGI script (%r)" % scriptname)
            )
            return
        if not os.path.isfile(scriptfile):
            self.send_error(
                HTTPStatus.FORBIDDEN,
                ("CGI script is not a plain file (%r)" % scriptname),
            )
            return
        ispy = self.is_python(scriptname)
        if self.have_fork or (not ispy):
            if not self.is_executable(scriptfile):
                self.send_error(
                    HTTPStatus.FORBIDDEN,
                    ("CGI script is not executable (%r)" % scriptname),
                )
                return
        env = copy.deepcopy(os.environ)
        env["SERVER_SOFTWARE"] = self.version_string()
        env["SERVER_NAME"] = self.server.server_name
        env["GATEWAY_INTERFACE"] = "CGI/1.1"
        env["SERVER_PROTOCOL"] = self.protocol_version
        env["SERVER_PORT"] = str(self.server.server_port)
        env["REQUEST_METHOD"] = self.command
        uqrest = urllib.parse.unquote(rest)
        env["PATH_INFO"] = uqrest
        env["PATH_TRANSLATED"] = self.translate_path(uqrest)
        env["SCRIPT_NAME"] = scriptname
        env["QUERY_STRING"] = query
        env["REMOTE_ADDR"] = self.client_address[0]
        authorization = self.headers.get("authorization")
        if authorization:
            authorization = authorization.split()
            if len(authorization) == 2:
                import base64, binascii

                env["AUTH_TYPE"] = authorization[0]
                if authorization[0].lower() == "basic":
                    try:
                        authorization = authorization[1].encode("ascii")
                        authorization = base64.decodebytes(authorization).decode(
                            "ascii"
                        )
                    except (binascii.Error, UnicodeError):
                        pass
                    else:
                        authorization = authorization.split(":")
                        if len(authorization) == 2:
                            env["REMOTE_USER"] = authorization[0]
        if self.headers.get("content-type") is None:
            env["CONTENT_TYPE"] = self.headers.get_content_type()
        else:
            env["CONTENT_TYPE"] = self.headers["content-type"]
        length = self.headers.get("content-length")
        if length:
            env["CONTENT_LENGTH"] = length
        referer = self.headers.get("referer")
        if referer:
            env["HTTP_REFERER"] = referer
        accept = self.headers.get_all("accept", ())
        env["HTTP_ACCEPT"] = ",".join(accept)
        ua = self.headers.get("user-agent")
        if ua:
            env["HTTP_USER_AGENT"] = ua
        co = filter(None, self.headers.get_all("cookie", []))
        cookie_str = ", ".join(co)
        if cookie_str:
            env["HTTP_COOKIE"] = cookie_str
        for k in (
            "QUERY_STRING",
            "REMOTE_HOST",
            "CONTENT_LENGTH",
            "HTTP_USER_AGENT",
            "HTTP_COOKIE",
            "HTTP_REFERER",
        ):
            env.setdefault(k, "")
        self.send_response(HTTPStatus.OK, "Script output follows")
        self.flush_headers()
        decoded_query = query.replace("+", " ")
        if self.have_fork:
            args = [script]
            if "=" not in decoded_query:
                args.append(decoded_query)
            nobody = nobody_uid()
            self.wfile.flush()
            pid = os.fork()
            if pid != 0:
                (pid, sts) = os.waitpid(pid, 0)
                while select.select([self.rfile], [], [], 0)[0]:
                    if not self.rfile.read(1):
                        break
                exitcode = os.waitstatus_to_exitcode(sts)
                if exitcode:
                    self.log_error(f"CGI script exit code {exitcode}")
                return
            try:
                try:
                    os.setuid(nobody)
                except OSError:
                    pass
                os.dup2(self.rfile.fileno(), 0)
                os.dup2(self.wfile.fileno(), 1)
                os.execve(scriptfile, args, env)
            except:
                self.server.handle_error(self.request, self.client_address)
                os._exit(127)
        else:
            import subprocess

            cmdline = [scriptfile]
            if self.is_python(scriptfile):
                interp = sys.executable
                if interp.lower().endswith("w.exe"):
                    interp = interp[:(-5)] + interp[(-4):]
                cmdline = [interp, "-u"] + cmdline
            if "=" not in query:
                cmdline.append(query)
            self.log_message("command: %s", subprocess.list2cmdline(cmdline))
            try:
                nbytes = int(length)
            except (TypeError, ValueError):
                nbytes = 0
            p = subprocess.Popen(
                cmdline,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            if (self.command.lower() == "post") and (nbytes > 0):
                data = self.rfile.read(nbytes)
            else:
                data = None
            while select.select([self.rfile._sock], [], [], 0)[0]:
                if not self.rfile._sock.recv(1):
                    break
            (stdout, stderr) = p.communicate(data)
            self.wfile.write(stdout)
            if stderr:
                self.log_error("%s", stderr)
            p.stderr.close()
            p.stdout.close()
            status = p.returncode
            if status:
                self.log_error("CGI script exit status %#x", status)
            else:
                self.log_message("CGI script exited OK")


def _get_best_family(*address):
    infos = socket.getaddrinfo(
        *address, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE
    )
    (family, type, proto, canonname, sockaddr) = next(iter(infos))
    return (family, sockaddr)


def test(
    HandlerClass=BaseHTTPRequestHandler,
    ServerClass=ThreadingHTTPServer,
    protocol="HTTP/1.0",
    port=8000,
    bind=None,
):
    "Test the HTTP request handler class.\n\n    This runs an HTTP server on port 8000 (or the port argument).\n\n    "
    (ServerClass.address_family, addr) = _get_best_family(bind, port)
    HandlerClass.protocol_version = protocol
    with ServerClass(addr, HandlerClass) as httpd:
        (host, port) = httpd.socket.getsockname()[:2]
        url_host = f"[{host}]" if (":" in host) else host
        print(f"Serving HTTP on {host} port {port} (http://{url_host}:{port}/) ...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--cgi", action="store_true", help="Run as CGI Server")
    parser.add_argument(
        "--bind",
        "-b",
        metavar="ADDRESS",
        help="Specify alternate bind address [default: all interfaces]",
    )
    parser.add_argument(
        "--directory",
        "-d",
        default=os.getcwd(),
        help="Specify alternative directory [default:current directory]",
    )
    parser.add_argument(
        "port",
        action="store",
        default=8000,
        type=int,
        nargs="?",
        help="Specify alternate port [default: 8000]",
    )
    args = parser.parse_args()
    if args.cgi:
        handler_class = CGIHTTPRequestHandler
    else:
        handler_class = partial(SimpleHTTPRequestHandler, directory=args.directory)

    class DualStackServer(ThreadingHTTPServer):
        def server_bind(self):
            with contextlib.suppress(Exception):
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            return super().server_bind()

    test(
        HandlerClass=handler_class,
        ServerClass=DualStackServer,
        port=args.port,
        bind=args.bind,
    )
