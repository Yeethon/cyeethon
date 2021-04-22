"A POP3 client class.\n\nBased on the J. Myers POP3 draft, Jan. 96\n"
import errno
import re
import socket
import sys

try:
    import ssl

    HAVE_SSL = True
except ImportError:
    HAVE_SSL = False
__all__ = ["POP3", "error_proto"]


class error_proto(Exception):
    pass


POP3_PORT = 110
POP3_SSL_PORT = 995
CR = b"\r"
LF = b"\n"
CRLF = CR + LF
_MAXLINE = 2048


class POP3:
    "This class supports both the minimal and optional command sets.\n    Arguments can be strings or integers (where appropriate)\n    (e.g.: retr(1) and retr('1') both work equally well.\n\n    Minimal Command Set:\n            USER name               user(name)\n            PASS string             pass_(string)\n            STAT                    stat()\n            LIST [msg]              list(msg = None)\n            RETR msg                retr(msg)\n            DELE msg                dele(msg)\n            NOOP                    noop()\n            RSET                    rset()\n            QUIT                    quit()\n\n    Optional Commands (some servers support these):\n            RPOP name               rpop(name)\n            APOP name digest        apop(name, digest)\n            TOP msg n               top(msg, n)\n            UIDL [msg]              uidl(msg = None)\n            CAPA                    capa()\n            STLS                    stls()\n            UTF8                    utf8()\n\n    Raises one exception: 'error_proto'.\n\n    Instantiate with:\n            POP3(hostname, port=110)\n\n    NB:     the POP protocol locks the mailbox from user\n            authorization until QUIT, so be sure to get in, suck\n            the messages, and quit, each time you access the\n            mailbox.\n\n            POP is a line-based protocol, which means large mail\n            messages consume lots of python cycles reading them\n            line-by-line.\n\n            If it's available on your mail server, use IMAP4\n            instead, it doesn't suffer from the two problems\n            above.\n    "
    encoding = "UTF-8"

    def __init__(self, host, port=POP3_PORT, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        self.host = host
        self.port = port
        self._tls_established = False
        sys.audit("poplib.connect", self, host, port)
        self.sock = self._create_socket(timeout)
        self.file = self.sock.makefile("rb")
        self._debugging = 0
        self.welcome = self._getresp()

    def _create_socket(self, timeout):
        if (timeout is not None) and (not timeout):
            raise ValueError("Non-blocking socket (timeout=0) is not supported")
        return socket.create_connection((self.host, self.port), timeout)

    def _putline(self, line):
        if self._debugging > 1:
            print("*put*", repr(line))
        sys.audit("poplib.putline", self, line)
        self.sock.sendall((line + CRLF))

    def _putcmd(self, line):
        if self._debugging:
            print("*cmd*", repr(line))
        line = bytes(line, self.encoding)
        self._putline(line)

    def _getline(self):
        line = self.file.readline((_MAXLINE + 1))
        if len(line) > _MAXLINE:
            raise error_proto("line too long")
        if self._debugging > 1:
            print("*get*", repr(line))
        if not line:
            raise error_proto("-ERR EOF")
        octets = len(line)
        if line[(-2):] == CRLF:
            return (line[:(-2)], octets)
        if line[:1] == CR:
            return (line[1:(-1)], octets)
        return (line[:(-1)], octets)

    def _getresp(self):
        (resp, o) = self._getline()
        if self._debugging > 1:
            print("*resp*", repr(resp))
        if not resp.startswith(b"+"):
            raise error_proto(resp)
        return resp

    def _getlongresp(self):
        resp = self._getresp()
        list = []
        octets = 0
        (line, o) = self._getline()
        while line != b".":
            if line.startswith(b".."):
                o = o - 1
                line = line[1:]
            octets = octets + o
            list.append(line)
            (line, o) = self._getline()
        return (resp, list, octets)

    def _shortcmd(self, line):
        self._putcmd(line)
        return self._getresp()

    def _longcmd(self, line):
        self._putcmd(line)
        return self._getlongresp()

    def getwelcome(self):
        return self.welcome

    def set_debuglevel(self, level):
        self._debugging = level

    def user(self, user):
        "Send user name, return response\n\n        (should indicate password required).\n        "
        return self._shortcmd(("USER %s" % user))

    def pass_(self, pswd):
        "Send password, return response\n\n        (response includes message count, mailbox size).\n\n        NB: mailbox is locked by server from here to 'quit()'\n        "
        return self._shortcmd(("PASS %s" % pswd))

    def stat(self):
        "Get mailbox status.\n\n        Result is tuple of 2 ints (message count, mailbox size)\n        "
        retval = self._shortcmd("STAT")
        rets = retval.split()
        if self._debugging:
            print("*stat*", repr(rets))
        numMessages = int(rets[1])
        sizeMessages = int(rets[2])
        return (numMessages, sizeMessages)

    def list(self, which=None):
        "Request listing, return result.\n\n        Result without a message number argument is in form\n        ['response', ['mesg_num octets', ...], octets].\n\n        Result when a message number argument is given is a\n        single response: the \"scan listing\" for that message.\n        "
        if which is not None:
            return self._shortcmd(("LIST %s" % which))
        return self._longcmd("LIST")

    def retr(self, which):
        "Retrieve whole message number 'which'.\n\n        Result is in form ['response', ['line', ...], octets].\n        "
        return self._longcmd(("RETR %s" % which))

    def dele(self, which):
        "Delete message number 'which'.\n\n        Result is 'response'.\n        "
        return self._shortcmd(("DELE %s" % which))

    def noop(self):
        "Does nothing.\n\n        One supposes the response indicates the server is alive.\n        "
        return self._shortcmd("NOOP")

    def rset(self):
        "Unmark all messages marked for deletion."
        return self._shortcmd("RSET")

    def quit(self):
        "Signoff: commit changes on server, unlock mailbox, close connection."
        resp = self._shortcmd("QUIT")
        self.close()
        return resp

    def close(self):
        "Close the connection without assuming anything about it."
        try:
            file = self.file
            self.file = None
            if file is not None:
                file.close()
        finally:
            sock = self.sock
            self.sock = None
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError as exc:
                    if (exc.errno != errno.ENOTCONN) and (
                        getattr(exc, "winerror", 0) != 10022
                    ):
                        raise
                finally:
                    sock.close()

    def rpop(self, user):
        "Not sure what this does."
        return self._shortcmd(("RPOP %s" % user))

    timestamp = re.compile(b"\\+OK.[^<]*(<.*>)")

    def apop(self, user, password):
        "Authorisation\n\n        - only possible if server has supplied a timestamp in initial greeting.\n\n        Args:\n                user     - mailbox user;\n                password - mailbox password.\n\n        NB: mailbox is locked by server from here to 'quit()'\n        "
        secret = bytes(password, self.encoding)
        m = self.timestamp.match(self.welcome)
        if not m:
            raise error_proto("-ERR APOP not supported by server")
        import hashlib

        digest = m.group(1) + secret
        digest = hashlib.md5(digest).hexdigest()
        return self._shortcmd(("APOP %s %s" % (user, digest)))

    def top(self, which, howmuch):
        "Retrieve message header of message number 'which'\n        and first 'howmuch' lines of message body.\n\n        Result is in form ['response', ['line', ...], octets].\n        "
        return self._longcmd(("TOP %s %s" % (which, howmuch)))

    def uidl(self, which=None):
        "Return message digest (unique id) list.\n\n        If 'which', result contains unique id for that message\n        in the form 'response mesgnum uid', otherwise result is\n        the list ['response', ['mesgnum uid', ...], octets]\n        "
        if which is not None:
            return self._shortcmd(("UIDL %s" % which))
        return self._longcmd("UIDL")

    def utf8(self):
        "Try to enter UTF-8 mode (see RFC 6856). Returns server response.\n        "
        return self._shortcmd("UTF8")

    def capa(self):
        "Return server capabilities (RFC 2449) as a dictionary\n        >>> c=poplib.POP3('localhost')\n        >>> c.capa()\n        {'IMPLEMENTATION': ['Cyrus', 'POP3', 'server', 'v2.2.12'],\n         'TOP': [], 'LOGIN-DELAY': ['0'], 'AUTH-RESP-CODE': [],\n         'EXPIRE': ['NEVER'], 'USER': [], 'STLS': [], 'PIPELINING': [],\n         'UIDL': [], 'RESP-CODES': []}\n        >>>\n\n        Really, according to RFC 2449, the cyrus folks should avoid\n        having the implementation split into multiple arguments...\n        "

        def _parsecap(line):
            lst = line.decode("ascii").split()
            return (lst[0], lst[1:])

        caps = {}
        try:
            resp = self._longcmd("CAPA")
            rawcaps = resp[1]
            for capline in rawcaps:
                (capnm, capargs) = _parsecap(capline)
                caps[capnm] = capargs
        except error_proto:
            raise error_proto("-ERR CAPA not supported by server")
        return caps

    def stls(self, context=None):
        "Start a TLS session on the active connection as specified in RFC 2595.\n\n                context - a ssl.SSLContext\n        "
        if not HAVE_SSL:
            raise error_proto("-ERR TLS support missing")
        if self._tls_established:
            raise error_proto("-ERR TLS session already established")
        caps = self.capa()
        if not ("STLS" in caps):
            raise error_proto("-ERR STLS not supported by server")
        if context is None:
            context = ssl._create_stdlib_context()
        resp = self._shortcmd("STLS")
        self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile("rb")
        self._tls_established = True
        return resp


if HAVE_SSL:

    class POP3_SSL(POP3):
        "POP3 client class over SSL connection\n\n        Instantiate with: POP3_SSL(hostname, port=995, keyfile=None, certfile=None,\n                                   context=None)\n\n               hostname - the hostname of the pop3 over ssl server\n               port - port number\n               keyfile - PEM formatted file that contains your private key\n               certfile - PEM formatted certificate chain file\n               context - a ssl.SSLContext\n\n        See the methods of the parent class POP3 for more documentation.\n        "

        def __init__(
            self,
            host,
            port=POP3_SSL_PORT,
            keyfile=None,
            certfile=None,
            timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
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
            POP3.__init__(self, host, port, timeout)

        def _create_socket(self, timeout):
            sock = POP3._create_socket(self, timeout)
            sock = self.context.wrap_socket(sock, server_hostname=self.host)
            return sock

        def stls(self, keyfile=None, certfile=None, context=None):
            "The method unconditionally raises an exception since the\n            STLS command doesn't make any sense on an already established\n            SSL/TLS session.\n            "
            raise error_proto("-ERR TLS session already established")

    __all__.append("POP3_SSL")
if __name__ == "__main__":
    import sys

    a = POP3(sys.argv[1])
    print(a.getwelcome())
    a.user(sys.argv[2])
    a.pass_(sys.argv[3])
    a.list()
    (numMsgs, totalSize) = a.stat()
    for i in range(1, (numMsgs + 1)):
        (header, msg, octets) = a.retr(i)
        print(("Message %d:" % i))
        for line in msg:
            print(("   " + line))
        print("-----------------------")
    a.quit()
