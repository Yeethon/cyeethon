'SMTP/ESMTP client class.\n\nThis should follow RFC 821 (SMTP), RFC 1869 (ESMTP), RFC 2554 (SMTP\nAuthentication) and RFC 2487 (Secure SMTP over TLS).\n\nNotes:\n\nPlease remember, when doing ESMTP, that the names of the SMTP service\nextensions are NOT the same thing as the option keywords for the RCPT\nand MAIL commands!\n\nExample:\n\n  >>> import smtplib\n  >>> s=smtplib.SMTP("localhost")\n  >>> print(s.help())\n  This is Sendmail version 8.8.4\n  Topics:\n      HELO    EHLO    MAIL    RCPT    DATA\n      RSET    NOOP    QUIT    HELP    VRFY\n      EXPN    VERB    ETRN    DSN\n  For more info use "HELP <topic>".\n  To report bugs in the implementation send email to\n      sendmail-bugs@sendmail.org.\n  For local information send email to Postmaster at your site.\n  End of HELP info\n  >>> s.putcmd("vrfy","someone@here")\n  >>> s.getreply()\n  (250, "Somebody OverHere <somebody@here.my.org>")\n  >>> s.quit()\n'
import socket
import io
import re
import email.utils
import email.message
import email.generator
import base64
import hmac
import copy
import datetime
import sys
from email.base64mime import body_encode as encode_base64

__all__ = [
    "SMTPException",
    "SMTPNotSupportedError",
    "SMTPServerDisconnected",
    "SMTPResponseException",
    "SMTPSenderRefused",
    "SMTPRecipientsRefused",
    "SMTPDataError",
    "SMTPConnectError",
    "SMTPHeloError",
    "SMTPAuthenticationError",
    "quoteaddr",
    "quotedata",
    "SMTP",
]
SMTP_PORT = 25
SMTP_SSL_PORT = 465
CRLF = "\r\n"
bCRLF = b"\r\n"
_MAXLINE = 8192
_MAXCHALLENGE = 5
OLDSTYLE_AUTH = re.compile("auth=(.*)", re.I)


class SMTPException(OSError):
    "Base class for all exceptions raised by this module."


class SMTPNotSupportedError(SMTPException):
    "The command or option is not supported by the SMTP server.\n\n    This exception is raised when an attempt is made to run a command or a\n    command with an option which is not supported by the server.\n    "


class SMTPServerDisconnected(SMTPException):
    "Not connected to any SMTP server.\n\n    This exception is raised when the server unexpectedly disconnects,\n    or when an attempt is made to use the SMTP instance before\n    connecting it to a server.\n    "


class SMTPResponseException(SMTPException):
    "Base class for all exceptions that include an SMTP error code.\n\n    These exceptions are generated in some instances when the SMTP\n    server returns an error code.  The error code is stored in the\n    `smtp_code' attribute of the error, and the `smtp_error' attribute\n    is set to the error message.\n    "

    def __init__(self, code, msg):
        self.smtp_code = code
        self.smtp_error = msg
        self.args = (code, msg)


class SMTPSenderRefused(SMTPResponseException):
    "Sender address refused.\n\n    In addition to the attributes set by on all SMTPResponseException\n    exceptions, this sets `sender' to the string that the SMTP refused.\n    "

    def __init__(self, code, msg, sender):
        self.smtp_code = code
        self.smtp_error = msg
        self.sender = sender
        self.args = (code, msg, sender)


class SMTPRecipientsRefused(SMTPException):
    "All recipient addresses refused.\n\n    The errors for each recipient are accessible through the attribute\n    'recipients', which is a dictionary of exactly the same sort as\n    SMTP.sendmail() returns.\n    "

    def __init__(self, recipients):
        self.recipients = recipients
        self.args = (recipients,)


class SMTPDataError(SMTPResponseException):
    "The SMTP server didn't accept the data."


class SMTPConnectError(SMTPResponseException):
    "Error during connection establishment."


class SMTPHeloError(SMTPResponseException):
    "The server refused our HELO reply."


class SMTPAuthenticationError(SMTPResponseException):
    "Authentication error.\n\n    Most probably the server didn't accept the username/password\n    combination provided.\n    "


def quoteaddr(addrstring):
    "Quote a subset of the email addresses defined by RFC 821.\n\n    Should be able to handle anything email.utils.parseaddr can handle.\n    "
    (displayname, addr) = email.utils.parseaddr(addrstring)
    if (displayname, addr) == ("", ""):
        if addrstring.strip().startswith("<"):
            return addrstring
        return "<%s>" % addrstring
    return "<%s>" % addr


def _addr_only(addrstring):
    (displayname, addr) = email.utils.parseaddr(addrstring)
    if (displayname, addr) == ("", ""):
        return addrstring
    return addr


def quotedata(data):
    "Quote data for email.\n\n    Double leading '.', and change Unix newline '\\n', or Mac '\\r' into\n    Internet CRLF end-of-line.\n    "
    return re.sub("(?m)^\\.", "..", re.sub("(?:\\r\\n|\\n|\\r(?!\\n))", CRLF, data))


def _quote_periods(bindata):
    return re.sub(b"(?m)^\\.", b"..", bindata)


def _fix_eols(data):
    return re.sub("(?:\\r\\n|\\n|\\r(?!\\n))", CRLF, data)


try:
    import ssl
except ImportError:
    _have_ssl = False
else:
    _have_ssl = True


class SMTP:
    "This class manages a connection to an SMTP or ESMTP server.\n    SMTP Objects:\n        SMTP objects have the following attributes:\n            helo_resp\n                This is the message given by the server in response to the\n                most recent HELO command.\n\n            ehlo_resp\n                This is the message given by the server in response to the\n                most recent EHLO command. This is usually multiline.\n\n            does_esmtp\n                This is a True value _after you do an EHLO command_, if the\n                server supports ESMTP.\n\n            esmtp_features\n                This is a dictionary, which, if the server supports ESMTP,\n                will _after you do an EHLO command_, contain the names of the\n                SMTP service extensions this server supports, and their\n                parameters (if any).\n\n                Note, all extension names are mapped to lower case in the\n                dictionary.\n\n        See each method's docstrings for details.  In general, there is a\n        method of the same name to perform each SMTP command.  There is also a\n        method called 'sendmail' that will do an entire mail transaction.\n        "
    debuglevel = 0
    sock = None
    file = None
    helo_resp = None
    ehlo_msg = "ehlo"
    ehlo_resp = None
    does_esmtp = False
    default_port = SMTP_PORT

    def __init__(
        self,
        host="",
        port=0,
        local_hostname=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
    ):
        "Initialize a new instance.\n\n        If specified, `host' is the name of the remote host to which to\n        connect.  If specified, `port' specifies the port to which to connect.\n        By default, smtplib.SMTP_PORT is used.  If a host is specified the\n        connect method is called, and if it returns anything other than a\n        success code an SMTPConnectError is raised.  If specified,\n        `local_hostname` is used as the FQDN of the local host in the HELO/EHLO\n        command.  Otherwise, the local hostname is found using\n        socket.getfqdn(). The `source_address` parameter takes a 2-tuple (host,\n        port) for the socket to bind to as its source address before\n        connecting. If the host is '' and port is 0, the OS default behavior\n        will be used.\n\n        "
        self._host = host
        self.timeout = timeout
        self.esmtp_features = {}
        self.command_encoding = "ascii"
        self.source_address = source_address
        self._auth_challenge_count = 0
        if host:
            (code, msg) = self.connect(host, port)
            if code != 220:
                self.close()
                raise SMTPConnectError(code, msg)
        if local_hostname is not None:
            self.local_hostname = local_hostname
        else:
            fqdn = socket.getfqdn()
            if "." in fqdn:
                self.local_hostname = fqdn
            else:
                addr = "127.0.0.1"
                try:
                    addr = socket.gethostbyname(socket.gethostname())
                except socket.gaierror:
                    pass
                self.local_hostname = "[%s]" % addr

    def __enter__(self):
        return self

    def __exit__(self, *args):
        try:
            (code, message) = self.docmd("QUIT")
            if code != 221:
                raise SMTPResponseException(code, message)
        except SMTPServerDisconnected:
            pass
        finally:
            self.close()

    def set_debuglevel(self, debuglevel):
        "Set the debug output level.\n\n        A non-false value results in debug messages for connection and for all\n        messages sent to and received from the server.\n\n        "
        self.debuglevel = debuglevel

    def _print_debug(self, *args):
        if self.debuglevel > 1:
            print(datetime.datetime.now().time(), *args, file=sys.stderr)
        else:
            print(*args, file=sys.stderr)

    def _get_socket(self, host, port, timeout):
        if (timeout is not None) and (not timeout):
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        if self.debuglevel > 0:
            self._print_debug("connect: to", (host, port), self.source_address)
        return socket.create_connection((host, port), timeout, self.source_address)

    def connect(self, host="localhost", port=0, source_address=None):
        "Connect to a host on a given port.\n\n        If the hostname ends with a colon (`:') followed by a number, and\n        there is no port specified, that suffix will be stripped off and the\n        number interpreted as the port number to use.\n\n        Note: This method is automatically invoked by __init__, if a host is\n        specified during instantiation.\n\n        "
        if source_address:
            self.source_address = source_address
        if (not port) and (host.find(":") == host.rfind(":")):
            i = host.rfind(":")
            if i >= 0:
                (host, port) = (host[:i], host[(i + 1) :])
                try:
                    port = int(port)
                except ValueError:
                    raise OSError("nonnumeric port")
        if not port:
            port = self.default_port
        sys.audit("smtplib.connect", self, host, port)
        self.sock = self._get_socket(host, port, self.timeout)
        self.file = None
        (code, msg) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug("connect:", repr(msg))
        return (code, msg)

    def send(self, s):
        "Send `s' to the server."
        if self.debuglevel > 0:
            self._print_debug("send:", repr(s))
        if self.sock:
            if isinstance(s, str):
                s = s.encode(self.command_encoding)
            sys.audit("smtplib.send", self, s)
            try:
                self.sock.sendall(s)
            except OSError:
                self.close()
                raise SMTPServerDisconnected("Server not connected")
        else:
            raise SMTPServerDisconnected("please run connect() first")

    def putcmd(self, cmd, args=""):
        "Send a command to the server."
        if args == "":
            str = "%s%s" % (cmd, CRLF)
        else:
            str = "%s %s%s" % (cmd, args, CRLF)
        self.send(str)

    def getreply(self):
        "Get a reply from the server.\n\n        Returns a tuple consisting of:\n\n          - server response code (e.g. '250', or such, if all goes well)\n            Note: returns -1 if it can't read response code.\n\n          - server response string corresponding to response code (multiline\n            responses are converted to a single, multiline string).\n\n        Raises SMTPServerDisconnected if end-of-file is reached.\n        "
        resp = []
        if self.file is None:
            self.file = self.sock.makefile("rb")
        while 1:
            try:
                line = self.file.readline((_MAXLINE + 1))
            except OSError as e:
                self.close()
                raise SMTPServerDisconnected(
                    ("Connection unexpectedly closed: " + str(e))
                )
            if not line:
                self.close()
                raise SMTPServerDisconnected("Connection unexpectedly closed")
            if self.debuglevel > 0:
                self._print_debug("reply:", repr(line))
            if len(line) > _MAXLINE:
                self.close()
                raise SMTPResponseException(500, "Line too long.")
            resp.append(line[4:].strip(b" \t\r\n"))
            code = line[:3]
            try:
                errcode = int(code)
            except ValueError:
                errcode = -1
                break
            if line[3:4] != b"-":
                break
        errmsg = b"\n".join(resp)
        if self.debuglevel > 0:
            self._print_debug(("reply: retcode (%s); Msg: %a" % (errcode, errmsg)))
        return (errcode, errmsg)

    def docmd(self, cmd, args=""):
        "Send a command, and return its response code."
        self.putcmd(cmd, args)
        return self.getreply()

    def helo(self, name=""):
        "SMTP 'helo' command.\n        Hostname to send for this command defaults to the FQDN of the local\n        host.\n        "
        self.putcmd("helo", (name or self.local_hostname))
        (code, msg) = self.getreply()
        self.helo_resp = msg
        return (code, msg)

    def ehlo(self, name=""):
        " SMTP 'ehlo' command.\n        Hostname to send for this command defaults to the FQDN of the local\n        host.\n        "
        self.esmtp_features = {}
        self.putcmd(self.ehlo_msg, (name or self.local_hostname))
        (code, msg) = self.getreply()
        if (code == (-1)) and (len(msg) == 0):
            self.close()
            raise SMTPServerDisconnected("Server not connected")
        self.ehlo_resp = msg
        if code != 250:
            return (code, msg)
        self.does_esmtp = True
        assert isinstance(self.ehlo_resp, bytes), repr(self.ehlo_resp)
        resp = self.ehlo_resp.decode("latin-1").split("\n")
        del resp[0]
        for each in resp:
            auth_match = OLDSTYLE_AUTH.match(each)
            if auth_match:
                self.esmtp_features["auth"] = (
                    self.esmtp_features.get("auth", "") + " "
                ) + auth_match.groups(0)[0]
                continue
            m = re.match("(?P<feature>[A-Za-z0-9][A-Za-z0-9\\-]*) ?", each)
            if m:
                feature = m.group("feature").lower()
                params = m.string[m.end("feature") :].strip()
                if feature == "auth":
                    self.esmtp_features[feature] = (
                        self.esmtp_features.get(feature, "") + " "
                    ) + params
                else:
                    self.esmtp_features[feature] = params
        return (code, msg)

    def has_extn(self, opt):
        "Does the server support a given SMTP service extension?"
        return opt.lower() in self.esmtp_features

    def help(self, args=""):
        "SMTP 'help' command.\n        Returns help text from server."
        self.putcmd("help", args)
        return self.getreply()[1]

    def rset(self):
        "SMTP 'rset' command -- resets session."
        self.command_encoding = "ascii"
        return self.docmd("rset")

    def _rset(self):
        "Internal 'rset' command which ignores any SMTPServerDisconnected error.\n\n        Used internally in the library, since the server disconnected error\n        should appear to the application when the *next* command is issued, if\n        we are doing an internal \"safety\" reset.\n        "
        try:
            self.rset()
        except SMTPServerDisconnected:
            pass

    def noop(self):
        "SMTP 'noop' command -- doesn't do anything :>"
        return self.docmd("noop")

    def mail(self, sender, options=()):
        "SMTP 'mail' command -- begins mail xfer session.\n\n        This method may raise the following exceptions:\n\n         SMTPNotSupportedError  The options parameter includes 'SMTPUTF8'\n                                but the SMTPUTF8 extension is not supported by\n                                the server.\n        "
        optionlist = ""
        if options and self.does_esmtp:
            if any(((x.lower() == "smtputf8") for x in options)):
                if self.has_extn("smtputf8"):
                    self.command_encoding = "utf-8"
                else:
                    raise SMTPNotSupportedError("SMTPUTF8 not supported by server")
            optionlist = " " + " ".join(options)
        self.putcmd("mail", ("FROM:%s%s" % (quoteaddr(sender), optionlist)))
        return self.getreply()

    def rcpt(self, recip, options=()):
        "SMTP 'rcpt' command -- indicates 1 recipient for this mail."
        optionlist = ""
        if options and self.does_esmtp:
            optionlist = " " + " ".join(options)
        self.putcmd("rcpt", ("TO:%s%s" % (quoteaddr(recip), optionlist)))
        return self.getreply()

    def data(self, msg):
        "SMTP 'DATA' command -- sends message data to server.\n\n        Automatically quotes lines beginning with a period per rfc821.\n        Raises SMTPDataError if there is an unexpected reply to the\n        DATA command; the return value from this method is the final\n        response code received when the all data is sent.  If msg\n        is a string, lone '\\r' and '\\n' characters are converted to\n        '\\r\\n' characters.  If msg is bytes, it is transmitted as is.\n        "
        self.putcmd("data")
        (code, repl) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug("data:", (code, repl))
        if code != 354:
            raise SMTPDataError(code, repl)
        else:
            if isinstance(msg, str):
                msg = _fix_eols(msg).encode("ascii")
            q = _quote_periods(msg)
            if q[(-2):] != bCRLF:
                q = q + bCRLF
            q = (q + b".") + bCRLF
            self.send(q)
            (code, msg) = self.getreply()
            if self.debuglevel > 0:
                self._print_debug("data:", (code, msg))
            return (code, msg)

    def verify(self, address):
        "SMTP 'verify' command -- checks for address validity."
        self.putcmd("vrfy", _addr_only(address))
        return self.getreply()

    vrfy = verify

    def expn(self, address):
        "SMTP 'expn' command -- expands a mailing list."
        self.putcmd("expn", _addr_only(address))
        return self.getreply()

    def ehlo_or_helo_if_needed(self):
        "Call self.ehlo() and/or self.helo() if needed.\n\n        If there has been no previous EHLO or HELO command this session, this\n        method tries ESMTP EHLO first.\n\n        This method may raise the following exceptions:\n\n         SMTPHeloError            The server didn't reply properly to\n                                  the helo greeting.\n        "
        if (self.helo_resp is None) and (self.ehlo_resp is None):
            if not (200 <= self.ehlo()[0] <= 299):
                (code, resp) = self.helo()
                if not (200 <= code <= 299):
                    raise SMTPHeloError(code, resp)

    def auth(self, mechanism, authobject, *, initial_response_ok=True):
        "Authentication command - requires response processing.\n\n        'mechanism' specifies which authentication mechanism is to\n        be used - the valid values are those listed in the 'auth'\n        element of 'esmtp_features'.\n\n        'authobject' must be a callable object taking a single argument:\n\n                data = authobject(challenge)\n\n        It will be called to process the server's challenge response; the\n        challenge argument it is passed will be a bytes.  It should return\n        an ASCII string that will be base64 encoded and sent to the server.\n\n        Keyword arguments:\n            - initial_response_ok: Allow sending the RFC 4954 initial-response\n              to the AUTH command, if the authentication methods supports it.\n        "
        mechanism = mechanism.upper()
        initial_response = authobject() if initial_response_ok else None
        if initial_response is not None:
            response = encode_base64(initial_response.encode("ascii"), eol="")
            (code, resp) = self.docmd("AUTH", ((mechanism + " ") + response))
            self._auth_challenge_count = 1
        else:
            (code, resp) = self.docmd("AUTH", mechanism)
            self._auth_challenge_count = 0
        while code == 334:
            self._auth_challenge_count += 1
            challenge = base64.decodebytes(resp)
            response = encode_base64(authobject(challenge).encode("ascii"), eol="")
            (code, resp) = self.docmd(response)
            if self._auth_challenge_count > _MAXCHALLENGE:
                raise SMTPException(
                    (
                        "Server AUTH mechanism infinite loop. Last response: "
                        + repr((code, resp))
                    )
                )
        if code in (235, 503):
            return (code, resp)
        raise SMTPAuthenticationError(code, resp)

    def auth_cram_md5(self, challenge=None):
        " Authobject to use with CRAM-MD5 authentication. Requires self.user\n        and self.password to be set."
        if challenge is None:
            return None
        return (self.user + " ") + hmac.HMAC(
            self.password.encode("ascii"), challenge, "md5"
        ).hexdigest()

    def auth_plain(self, challenge=None):
        " Authobject to use with PLAIN authentication. Requires self.user and\n        self.password to be set."
        return "\x00%s\x00%s" % (self.user, self.password)

    def auth_login(self, challenge=None):
        " Authobject to use with LOGIN authentication. Requires self.user and\n        self.password to be set."
        if (challenge is None) or (self._auth_challenge_count < 2):
            return self.user
        else:
            return self.password

    def login(self, user, password, *, initial_response_ok=True):
        "Log in on an SMTP server that requires authentication.\n\n        The arguments are:\n            - user:         The user name to authenticate with.\n            - password:     The password for the authentication.\n\n        Keyword arguments:\n            - initial_response_ok: Allow sending the RFC 4954 initial-response\n              to the AUTH command, if the authentication methods supports it.\n\n        If there has been no previous EHLO or HELO command this session, this\n        method tries ESMTP EHLO first.\n\n        This method will return normally if the authentication was successful.\n\n        This method may raise the following exceptions:\n\n         SMTPHeloError            The server didn't reply properly to\n                                  the helo greeting.\n         SMTPAuthenticationError  The server didn't accept the username/\n                                  password combination.\n         SMTPNotSupportedError    The AUTH command is not supported by the\n                                  server.\n         SMTPException            No suitable authentication method was\n                                  found.\n        "
        self.ehlo_or_helo_if_needed()
        if not self.has_extn("auth"):
            raise SMTPNotSupportedError("SMTP AUTH extension not supported by server.")
        advertised_authlist = self.esmtp_features["auth"].split()
        preferred_auths = ["CRAM-MD5", "PLAIN", "LOGIN"]
        authlist = [auth for auth in preferred_auths if (auth in advertised_authlist)]
        if not authlist:
            raise SMTPException("No suitable authentication method found.")
        (self.user, self.password) = (user, password)
        for authmethod in authlist:
            method_name = "auth_" + authmethod.lower().replace("-", "_")
            try:
                (code, resp) = self.auth(
                    authmethod,
                    getattr(self, method_name),
                    initial_response_ok=initial_response_ok,
                )
                if code in (235, 503):
                    return (code, resp)
            except SMTPAuthenticationError as e:
                last_exception = e
        raise last_exception

    def starttls(self, keyfile=None, certfile=None, context=None):
        "Puts the connection to the SMTP server into TLS mode.\n\n        If there has been no previous EHLO or HELO command this session, this\n        method tries ESMTP EHLO first.\n\n        If the server supports TLS, this will encrypt the rest of the SMTP\n        session. If you provide the keyfile and certfile parameters,\n        the identity of the SMTP server and client can be checked. This,\n        however, depends on whether the socket module really checks the\n        certificates.\n\n        This method may raise the following exceptions:\n\n         SMTPHeloError            The server didn't reply properly to\n                                  the helo greeting.\n        "
        self.ehlo_or_helo_if_needed()
        if not self.has_extn("starttls"):
            raise SMTPNotSupportedError("STARTTLS extension not supported by server.")
        (resp, reply) = self.docmd("STARTTLS")
        if resp == 220:
            if not _have_ssl:
                raise RuntimeError("No SSL support included in this Python")
            if (context is not None) and (keyfile is not None):
                raise ValueError("context and keyfile arguments are mutually exclusive")
            if (context is not None) and (certfile is not None):
                raise ValueError(
                    "context and certfile arguments are mutually exclusive"
                )
            if (keyfile is not None) or (certfile is not None):
                import warnings

                warnings.warn(
                    "keyfile and certfile are deprecated, use a custom context instead",
                    DeprecationWarning,
                    2,
                )
            if context is None:
                context = ssl._create_stdlib_context(certfile=certfile, keyfile=keyfile)
            self.sock = context.wrap_socket(self.sock, server_hostname=self._host)
            self.file = None
            self.helo_resp = None
            self.ehlo_resp = None
            self.esmtp_features = {}
            self.does_esmtp = False
        else:
            raise SMTPResponseException(resp, reply)
        return (resp, reply)

    def sendmail(self, from_addr, to_addrs, msg, mail_options=(), rcpt_options=()):
        'This command performs an entire mail transaction.\n\n        The arguments are:\n            - from_addr    : The address sending this mail.\n            - to_addrs     : A list of addresses to send this mail to.  A bare\n                             string will be treated as a list with 1 address.\n            - msg          : The message to send.\n            - mail_options : List of ESMTP options (such as 8bitmime) for the\n                             mail command.\n            - rcpt_options : List of ESMTP options (such as DSN commands) for\n                             all the rcpt commands.\n\n        msg may be a string containing characters in the ASCII range, or a byte\n        string.  A string is encoded to bytes using the ascii codec, and lone\n        \\r and \\n characters are converted to \\r\\n characters.\n\n        If there has been no previous EHLO or HELO command this session, this\n        method tries ESMTP EHLO first.  If the server does ESMTP, message size\n        and each of the specified options will be passed to it.  If EHLO\n        fails, HELO will be tried and ESMTP options suppressed.\n\n        This method will return normally if the mail is accepted for at least\n        one recipient.  It returns a dictionary, with one entry for each\n        recipient that was refused.  Each entry contains a tuple of the SMTP\n        error code and the accompanying error message sent by the server.\n\n        This method may raise the following exceptions:\n\n         SMTPHeloError          The server didn\'t reply properly to\n                                the helo greeting.\n         SMTPRecipientsRefused  The server rejected ALL recipients\n                                (no mail was sent).\n         SMTPSenderRefused      The server didn\'t accept the from_addr.\n         SMTPDataError          The server replied with an unexpected\n                                error code (other than a refusal of\n                                a recipient).\n         SMTPNotSupportedError  The mail_options parameter includes \'SMTPUTF8\'\n                                but the SMTPUTF8 extension is not supported by\n                                the server.\n\n        Note: the connection will be open even after an exception is raised.\n\n        Example:\n\n         >>> import smtplib\n         >>> s=smtplib.SMTP("localhost")\n         >>> tolist=["one@one.org","two@two.org","three@three.org","four@four.org"]\n         >>> msg = \'\'\'\\\n         ... From: Me@my.org\n         ... Subject: testin\'...\n         ...\n         ... This is a test \'\'\'\n         >>> s.sendmail("me@my.org",tolist,msg)\n         { "three@three.org" : ( 550 ,"User unknown" ) }\n         >>> s.quit()\n\n        In the above example, the message was accepted for delivery to three\n        of the four addresses, and one was rejected, with the error code\n        550.  If all addresses are accepted, then the method will return an\n        empty dictionary.\n\n        '
        self.ehlo_or_helo_if_needed()
        esmtp_opts = []
        if isinstance(msg, str):
            msg = _fix_eols(msg).encode("ascii")
        if self.does_esmtp:
            if self.has_extn("size"):
                esmtp_opts.append(("size=%d" % len(msg)))
            for option in mail_options:
                esmtp_opts.append(option)
        (code, resp) = self.mail(from_addr, esmtp_opts)
        if code != 250:
            if code == 421:
                self.close()
            else:
                self._rset()
            raise SMTPSenderRefused(code, resp, from_addr)
        senderrs = {}
        if isinstance(to_addrs, str):
            to_addrs = [to_addrs]
        for each in to_addrs:
            (code, resp) = self.rcpt(each, rcpt_options)
            if (code != 250) and (code != 251):
                senderrs[each] = (code, resp)
            if code == 421:
                self.close()
                raise SMTPRecipientsRefused(senderrs)
        if len(senderrs) == len(to_addrs):
            self._rset()
            raise SMTPRecipientsRefused(senderrs)
        (code, resp) = self.data(msg)
        if code != 250:
            if code == 421:
                self.close()
            else:
                self._rset()
            raise SMTPDataError(code, resp)
        return senderrs

    def send_message(
        self, msg, from_addr=None, to_addrs=None, mail_options=(), rcpt_options=()
    ):
        "Converts message to a bytestring and passes it to sendmail.\n\n        The arguments are as for sendmail, except that msg is an\n        email.message.Message object.  If from_addr is None or to_addrs is\n        None, these arguments are taken from the headers of the Message as\n        described in RFC 2822 (a ValueError is raised if there is more than\n        one set of 'Resent-' headers).  Regardless of the values of from_addr and\n        to_addr, any Bcc field (or Resent-Bcc field, when the Message is a\n        resent) of the Message object won't be transmitted.  The Message\n        object is then serialized using email.generator.BytesGenerator and\n        sendmail is called to transmit the message.  If the sender or any of\n        the recipient addresses contain non-ASCII and the server advertises the\n        SMTPUTF8 capability, the policy is cloned with utf8 set to True for the\n        serialization, and SMTPUTF8 and BODY=8BITMIME are asserted on the send.\n        If the server does not support SMTPUTF8, an SMTPNotSupported error is\n        raised.  Otherwise the generator is called without modifying the\n        policy.\n\n        "
        self.ehlo_or_helo_if_needed()
        resent = msg.get_all("Resent-Date")
        if resent is None:
            header_prefix = ""
        elif len(resent) == 1:
            header_prefix = "Resent-"
        else:
            raise ValueError("message has more than one 'Resent-' header block")
        if from_addr is None:
            from_addr = (
                msg[(header_prefix + "Sender")]
                if ((header_prefix + "Sender") in msg)
                else msg[(header_prefix + "From")]
            )
            from_addr = email.utils.getaddresses([from_addr])[0][1]
        if to_addrs is None:
            addr_fields = [
                f
                for f in (
                    msg[(header_prefix + "To")],
                    msg[(header_prefix + "Bcc")],
                    msg[(header_prefix + "Cc")],
                )
                if (f is not None)
            ]
            to_addrs = [a[1] for a in email.utils.getaddresses(addr_fields)]
        msg_copy = copy.copy(msg)
        del msg_copy["Bcc"]
        del msg_copy["Resent-Bcc"]
        international = False
        try:
            "".join([from_addr, *to_addrs]).encode("ascii")
        except UnicodeEncodeError:
            if not self.has_extn("smtputf8"):
                raise SMTPNotSupportedError(
                    "One or more source or delivery addresses require internationalized email support, but the server does not advertise the required SMTPUTF8 capability"
                )
            international = True
        with io.BytesIO() as bytesmsg:
            if international:
                g = email.generator.BytesGenerator(
                    bytesmsg, policy=msg.policy.clone(utf8=True)
                )
                mail_options = (*mail_options, "SMTPUTF8", "BODY=8BITMIME")
            else:
                g = email.generator.BytesGenerator(bytesmsg)
            g.flatten(msg_copy, linesep="\r\n")
            flatmsg = bytesmsg.getvalue()
        return self.sendmail(from_addr, to_addrs, flatmsg, mail_options, rcpt_options)

    def close(self):
        "Close the connection to the SMTP server."
        try:
            file = self.file
            self.file = None
            if file:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock:
                sock.close()

    def quit(self):
        "Terminate the SMTP session."
        res = self.docmd("quit")
        self.ehlo_resp = self.helo_resp = None
        self.esmtp_features = {}
        self.does_esmtp = False
        self.close()
        return res


if _have_ssl:

    class SMTP_SSL(SMTP):
        " This is a subclass derived from SMTP that connects over an SSL\n        encrypted socket (to use this class you need a socket module that was\n        compiled with SSL support). If host is not specified, '' (the local\n        host) is used. If port is omitted, the standard SMTP-over-SSL port\n        (465) is used.  local_hostname and source_address have the same meaning\n        as they do in the SMTP class.  keyfile and certfile are also optional -\n        they can contain a PEM formatted private key and certificate chain file\n        for the SSL connection. context also optional, can contain a\n        SSLContext, and is an alternative to keyfile and certfile; If it is\n        specified both keyfile and certfile must be None.\n\n        "
        default_port = SMTP_SSL_PORT

        def __init__(
            self,
            host="",
            port=0,
            local_hostname=None,
            keyfile=None,
            certfile=None,
            timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
            source_address=None,
            context=None,
        ):
            if (context is not None) and (keyfile is not None):
                raise ValueError("context and keyfile arguments are mutually exclusive")
            if (context is not None) and (certfile is not None):
                raise ValueError(
                    "context and certfile arguments are mutually exclusive"
                )
            if (keyfile is not None) or (certfile is not None):
                import warnings

                warnings.warn(
                    "keyfile and certfile are deprecated, use a custom context instead",
                    DeprecationWarning,
                    2,
                )
            self.keyfile = keyfile
            self.certfile = certfile
            if context is None:
                context = ssl._create_stdlib_context(certfile=certfile, keyfile=keyfile)
            self.context = context
            SMTP.__init__(self, host, port, local_hostname, timeout, source_address)

        def _get_socket(self, host, port, timeout):
            if self.debuglevel > 0:
                self._print_debug("connect:", (host, port))
            new_socket = super()._get_socket(host, port, timeout)
            new_socket = self.context.wrap_socket(
                new_socket, server_hostname=self._host
            )
            return new_socket

    __all__.append("SMTP_SSL")
LMTP_PORT = 2003


class LMTP(SMTP):
    "LMTP - Local Mail Transfer Protocol\n\n    The LMTP protocol, which is very similar to ESMTP, is heavily based\n    on the standard SMTP client. It's common to use Unix sockets for\n    LMTP, so our connect() method must support that as well as a regular\n    host:port server.  local_hostname and source_address have the same\n    meaning as they do in the SMTP class.  To specify a Unix socket,\n    you must use an absolute path as the host, starting with a '/'.\n\n    Authentication is supported, using the regular SMTP mechanism. When\n    using a Unix socket, LMTP generally don't support or require any\n    authentication, but your mileage might vary."
    ehlo_msg = "lhlo"

    def __init__(
        self,
        host="",
        port=LMTP_PORT,
        local_hostname=None,
        source_address=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
    ):
        "Initialize a new instance."
        super().__init__(
            host,
            port,
            local_hostname=local_hostname,
            source_address=source_address,
            timeout=timeout,
        )

    def connect(self, host="localhost", port=0, source_address=None):
        "Connect to the LMTP daemon, on either a Unix or a TCP socket."
        if host[0] != "/":
            return super().connect(host, port, source_address=source_address)
        if (self.timeout is not None) and (not self.timeout):
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            if self.timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                self.sock.settimeout(self.timeout)
            self.file = None
            self.sock.connect(host)
        except OSError:
            if self.debuglevel > 0:
                self._print_debug("connect fail:", host)
            if self.sock:
                self.sock.close()
            self.sock = None
            raise
        (code, msg) = self.getreply()
        if self.debuglevel > 0:
            self._print_debug("connect:", msg)
        return (code, msg)


if __name__ == "__main__":

    def prompt(prompt):
        sys.stdout.write((prompt + ": "))
        sys.stdout.flush()
        return sys.stdin.readline().strip()

    fromaddr = prompt("From")
    toaddrs = prompt("To").split(",")
    print("Enter message, end with ^D:")
    msg = ""
    while 1:
        line = sys.stdin.readline()
        if not line:
            break
        msg = msg + line
    print(("Message length is %d" % len(msg)))
    server = SMTP("localhost")
    server.set_debuglevel(1)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
