import collections
import warnings

try:
    import ssl
except ImportError:
    ssl = None
from . import constants
from . import protocols
from . import transports
from .log import logger


def _create_transport_context(server_side, server_hostname):
    if server_side:
        raise ValueError("Server side SSL needs a valid SSLContext")
    sslcontext = ssl.create_default_context()
    if not server_hostname:
        sslcontext.check_hostname = False
    return sslcontext


_UNWRAPPED = "UNWRAPPED"
_DO_HANDSHAKE = "DO_HANDSHAKE"
_WRAPPED = "WRAPPED"
_SHUTDOWN = "SHUTDOWN"


class _SSLPipe(object):
    'An SSL "Pipe".\n\n    An SSL pipe allows you to communicate with an SSL/TLS protocol instance\n    through memory buffers. It can be used to implement a security layer for an\n    existing connection where you don\'t have access to the connection\'s file\n    descriptor, or for some reason you don\'t want to use it.\n\n    An SSL pipe can be in "wrapped" and "unwrapped" mode. In unwrapped mode,\n    data is passed through untransformed. In wrapped mode, application level\n    data is encrypted to SSL record level data and vice versa. The SSL record\n    level is the lowest level in the SSL protocol suite and is what travels\n    as-is over the wire.\n\n    An SslPipe initially is in "unwrapped" mode. To start SSL, call\n    do_handshake(). To shutdown SSL again, call unwrap().\n    '
    max_size = 256 * 1024

    def __init__(self, context, server_side, server_hostname=None):
        "\n        The *context* argument specifies the ssl.SSLContext to use.\n\n        The *server_side* argument indicates whether this is a server side or\n        client side transport.\n\n        The optional *server_hostname* argument can be used to specify the\n        hostname you are connecting to. You may only specify this parameter if\n        the _ssl module supports Server Name Indication (SNI).\n        "
        self._context = context
        self._server_side = server_side
        self._server_hostname = server_hostname
        self._state = _UNWRAPPED
        self._incoming = ssl.MemoryBIO()
        self._outgoing = ssl.MemoryBIO()
        self._sslobj = None
        self._need_ssldata = False
        self._handshake_cb = None
        self._shutdown_cb = None

    @property
    def context(self):
        "The SSL context passed to the constructor."
        return self._context

    @property
    def ssl_object(self):
        "The internal ssl.SSLObject instance.\n\n        Return None if the pipe is not wrapped.\n        "
        return self._sslobj

    @property
    def need_ssldata(self):
        "Whether more record level data is needed to complete a handshake\n        that is currently in progress."
        return self._need_ssldata

    @property
    def wrapped(self):
        "\n        Whether a security layer is currently in effect.\n\n        Return False during handshake.\n        "
        return self._state == _WRAPPED

    def do_handshake(self, callback=None):
        "Start the SSL handshake.\n\n        Return a list of ssldata. A ssldata element is a list of buffers\n\n        The optional *callback* argument can be used to install a callback that\n        will be called when the handshake is complete. The callback will be\n        called with None if successful, else an exception instance.\n        "
        if self._state != _UNWRAPPED:
            raise RuntimeError("handshake in progress or completed")
        self._sslobj = self._context.wrap_bio(
            self._incoming,
            self._outgoing,
            server_side=self._server_side,
            server_hostname=self._server_hostname,
        )
        self._state = _DO_HANDSHAKE
        self._handshake_cb = callback
        (ssldata, appdata) = self.feed_ssldata(b"", only_handshake=True)
        assert len(appdata) == 0
        return ssldata

    def shutdown(self, callback=None):
        "Start the SSL shutdown sequence.\n\n        Return a list of ssldata. A ssldata element is a list of buffers\n\n        The optional *callback* argument can be used to install a callback that\n        will be called when the shutdown is complete. The callback will be\n        called without arguments.\n        "
        if self._state == _UNWRAPPED:
            raise RuntimeError("no security layer present")
        if self._state == _SHUTDOWN:
            raise RuntimeError("shutdown in progress")
        assert self._state in (_WRAPPED, _DO_HANDSHAKE)
        self._state = _SHUTDOWN
        self._shutdown_cb = callback
        (ssldata, appdata) = self.feed_ssldata(b"")
        assert (appdata == []) or (appdata == [b""])
        return ssldata

    def feed_eof(self):
        'Send a potentially "ragged" EOF.\n\n        This method will raise an SSL_ERROR_EOF exception if the EOF is\n        unexpected.\n        '
        self._incoming.write_eof()
        (ssldata, appdata) = self.feed_ssldata(b"")
        assert (appdata == []) or (appdata == [b""])

    def feed_ssldata(self, data, only_handshake=False):
        'Feed SSL record level data into the pipe.\n\n        The data must be a bytes instance. It is OK to send an empty bytes\n        instance. This can be used to get ssldata for a handshake initiated by\n        this endpoint.\n\n        Return a (ssldata, appdata) tuple. The ssldata element is a list of\n        buffers containing SSL data that needs to be sent to the remote SSL.\n\n        The appdata element is a list of buffers containing plaintext data that\n        needs to be forwarded to the application. The appdata list may contain\n        an empty buffer indicating an SSL "close_notify" alert. This alert must\n        be acknowledged by calling shutdown().\n        '
        if self._state == _UNWRAPPED:
            if data:
                appdata = [data]
            else:
                appdata = []
            return ([], appdata)
        self._need_ssldata = False
        if data:
            self._incoming.write(data)
        ssldata = []
        appdata = []
        try:
            if self._state == _DO_HANDSHAKE:
                self._sslobj.do_handshake()
                self._state = _WRAPPED
                if self._handshake_cb:
                    self._handshake_cb(None)
                if only_handshake:
                    return (ssldata, appdata)
            if self._state == _WRAPPED:
                while True:
                    chunk = self._sslobj.read(self.max_size)
                    appdata.append(chunk)
                    if not chunk:
                        break
            elif self._state == _SHUTDOWN:
                self._sslobj.unwrap()
                self._sslobj = None
                self._state = _UNWRAPPED
                if self._shutdown_cb:
                    self._shutdown_cb()
            elif self._state == _UNWRAPPED:
                appdata.append(self._incoming.read())
        except (ssl.SSLError, ssl.CertificateError) as exc:
            exc_errno = getattr(exc, "errno", None)
            if exc_errno not in (
                ssl.SSL_ERROR_WANT_READ,
                ssl.SSL_ERROR_WANT_WRITE,
                ssl.SSL_ERROR_SYSCALL,
            ):
                if (self._state == _DO_HANDSHAKE) and self._handshake_cb:
                    self._handshake_cb(exc)
                raise
            self._need_ssldata = exc_errno == ssl.SSL_ERROR_WANT_READ
        if self._outgoing.pending:
            ssldata.append(self._outgoing.read())
        return (ssldata, appdata)

    def feed_appdata(self, data, offset=0):
        "Feed plaintext data into the pipe.\n\n        Return an (ssldata, offset) tuple. The ssldata element is a list of\n        buffers containing record level data that needs to be sent to the\n        remote SSL instance. The offset is the number of plaintext bytes that\n        were processed, which may be less than the length of data.\n\n        NOTE: In case of short writes, this call MUST be retried with the SAME\n        buffer passed into the *data* argument (i.e. the id() must be the\n        same). This is an OpenSSL requirement. A further particularity is that\n        a short write will always have offset == 0, because the _ssl module\n        does not enable partial writes. And even though the offset is zero,\n        there will still be encrypted data in ssldata.\n        "
        assert 0 <= offset <= len(data)
        if self._state == _UNWRAPPED:
            if offset < len(data):
                ssldata = [data[offset:]]
            else:
                ssldata = []
            return (ssldata, len(data))
        ssldata = []
        view = memoryview(data)
        while True:
            self._need_ssldata = False
            try:
                if offset < len(view):
                    offset += self._sslobj.write(view[offset:])
            except ssl.SSLError as exc:
                exc_errno = getattr(exc, "errno", None)
                if exc.reason == "PROTOCOL_IS_SHUTDOWN":
                    exc_errno = exc.errno = ssl.SSL_ERROR_WANT_READ
                if exc_errno not in (
                    ssl.SSL_ERROR_WANT_READ,
                    ssl.SSL_ERROR_WANT_WRITE,
                    ssl.SSL_ERROR_SYSCALL,
                ):
                    raise
                self._need_ssldata = exc_errno == ssl.SSL_ERROR_WANT_READ
            if self._outgoing.pending:
                ssldata.append(self._outgoing.read())
            if (offset == len(view)) or self._need_ssldata:
                break
        return (ssldata, offset)


class _SSLProtocolTransport(transports._FlowControlMixin, transports.Transport):
    _sendfile_compatible = constants._SendfileMode.FALLBACK

    def __init__(self, loop, ssl_protocol):
        self._loop = loop
        self._ssl_protocol = ssl_protocol
        self._closed = False

    def get_extra_info(self, name, default=None):
        "Get optional transport information."
        return self._ssl_protocol._get_extra_info(name, default)

    def set_protocol(self, protocol):
        self._ssl_protocol._set_app_protocol(protocol)

    def get_protocol(self):
        return self._ssl_protocol._app_protocol

    def is_closing(self):
        return self._closed

    def close(self):
        "Close the transport.\n\n        Buffered data will be flushed asynchronously.  No more data\n        will be received.  After all buffered data is flushed, the\n        protocol's connection_lost() method will (eventually) called\n        with None as its argument.\n        "
        self._closed = True
        self._ssl_protocol._start_shutdown()

    def __del__(self, _warn=warnings.warn):
        if not self._closed:
            _warn(f"unclosed transport {self!r}", ResourceWarning, source=self)
            self.close()

    def is_reading(self):
        tr = self._ssl_protocol._transport
        if tr is None:
            raise RuntimeError("SSL transport has not been initialized yet")
        return tr.is_reading()

    def pause_reading(self):
        "Pause the receiving end.\n\n        No data will be passed to the protocol's data_received()\n        method until resume_reading() is called.\n        "
        self._ssl_protocol._transport.pause_reading()

    def resume_reading(self):
        "Resume the receiving end.\n\n        Data received will once again be passed to the protocol's\n        data_received() method.\n        "
        self._ssl_protocol._transport.resume_reading()

    def set_write_buffer_limits(self, high=None, low=None):
        "Set the high- and low-water limits for write flow control.\n\n        These two values control when to call the protocol's\n        pause_writing() and resume_writing() methods.  If specified,\n        the low-water limit must be less than or equal to the\n        high-water limit.  Neither value can be negative.\n\n        The defaults are implementation-specific.  If only the\n        high-water limit is given, the low-water limit defaults to an\n        implementation-specific value less than or equal to the\n        high-water limit.  Setting high to zero forces low to zero as\n        well, and causes pause_writing() to be called whenever the\n        buffer becomes non-empty.  Setting low to zero causes\n        resume_writing() to be called only once the buffer is empty.\n        Use of zero for either limit is generally sub-optimal as it\n        reduces opportunities for doing I/O and computation\n        concurrently.\n        "
        self._ssl_protocol._transport.set_write_buffer_limits(high, low)

    def get_write_buffer_size(self):
        "Return the current size of the write buffer."
        return self._ssl_protocol._transport.get_write_buffer_size()

    @property
    def _protocol_paused(self):
        return self._ssl_protocol._transport._protocol_paused

    def write(self, data):
        "Write some data bytes to the transport.\n\n        This does not block; it buffers the data and arranges for it\n        to be sent out asynchronously.\n        "
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError(
                f"data: expecting a bytes-like instance, got {type(data).__name__}"
            )
        if not data:
            return
        self._ssl_protocol._write_appdata(data)

    def can_write_eof(self):
        "Return True if this transport supports write_eof(), False if not."
        return False

    def abort(self):
        "Close the transport immediately.\n\n        Buffered data will be lost.  No more data will be received.\n        The protocol's connection_lost() method will (eventually) be\n        called with None as its argument.\n        "
        self._ssl_protocol._abort()
        self._closed = True


class SSLProtocol(protocols.Protocol):
    "SSL protocol.\n\n    Implementation of SSL on top of a socket using incoming and outgoing\n    buffers which are ssl.MemoryBIO objects.\n    "

    def __init__(
        self,
        loop,
        app_protocol,
        sslcontext,
        waiter,
        server_side=False,
        server_hostname=None,
        call_connection_made=True,
        ssl_handshake_timeout=None,
    ):
        if ssl is None:
            raise RuntimeError("stdlib ssl module not available")
        if ssl_handshake_timeout is None:
            ssl_handshake_timeout = constants.SSL_HANDSHAKE_TIMEOUT
        elif ssl_handshake_timeout <= 0:
            raise ValueError(
                f"ssl_handshake_timeout should be a positive number, got {ssl_handshake_timeout}"
            )
        if not sslcontext:
            sslcontext = _create_transport_context(server_side, server_hostname)
        self._server_side = server_side
        if server_hostname and (not server_side):
            self._server_hostname = server_hostname
        else:
            self._server_hostname = None
        self._sslcontext = sslcontext
        self._extra = dict(sslcontext=sslcontext)
        self._write_backlog = collections.deque()
        self._write_buffer_size = 0
        self._waiter = waiter
        self._loop = loop
        self._set_app_protocol(app_protocol)
        self._app_transport = _SSLProtocolTransport(self._loop, self)
        self._sslpipe = None
        self._session_established = False
        self._in_handshake = False
        self._in_shutdown = False
        self._transport = None
        self._call_connection_made = call_connection_made
        self._ssl_handshake_timeout = ssl_handshake_timeout

    def _set_app_protocol(self, app_protocol):
        self._app_protocol = app_protocol
        self._app_protocol_is_buffer = isinstance(
            app_protocol, protocols.BufferedProtocol
        )

    def _wakeup_waiter(self, exc=None):
        if self._waiter is None:
            return
        if not self._waiter.cancelled():
            if exc is not None:
                self._waiter.set_exception(exc)
            else:
                self._waiter.set_result(None)
        self._waiter = None

    def connection_made(self, transport):
        "Called when the low-level connection is made.\n\n        Start the SSL handshake.\n        "
        self._transport = transport
        self._sslpipe = _SSLPipe(
            self._sslcontext, self._server_side, self._server_hostname
        )
        self._start_handshake()

    def connection_lost(self, exc):
        "Called when the low-level connection is lost or closed.\n\n        The argument is an exception object or None (the latter\n        meaning a regular EOF is received or the connection was\n        aborted or closed).\n        "
        if self._session_established:
            self._session_established = False
            self._loop.call_soon(self._app_protocol.connection_lost, exc)
        elif self._app_transport is not None:
            self._app_transport._closed = True
        self._transport = None
        self._app_transport = None
        if getattr(self, "_handshake_timeout_handle", None):
            self._handshake_timeout_handle.cancel()
        self._wakeup_waiter(exc)
        self._app_protocol = None
        self._sslpipe = None

    def pause_writing(self):
        "Called when the low-level transport's buffer goes over\n        the high-water mark.\n        "
        self._app_protocol.pause_writing()

    def resume_writing(self):
        "Called when the low-level transport's buffer drains below\n        the low-water mark.\n        "
        self._app_protocol.resume_writing()

    def data_received(self, data):
        "Called when some SSL data is received.\n\n        The argument is a bytes object.\n        "
        if self._sslpipe is None:
            return
        try:
            (ssldata, appdata) = self._sslpipe.feed_ssldata(data)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._fatal_error(e, "SSL error in data received")
            return
        for chunk in ssldata:
            self._transport.write(chunk)
        for chunk in appdata:
            if chunk:
                try:
                    if self._app_protocol_is_buffer:
                        protocols._feed_data_to_buffered_proto(
                            self._app_protocol, chunk
                        )
                    else:
                        self._app_protocol.data_received(chunk)
                except (SystemExit, KeyboardInterrupt):
                    raise
                except BaseException as ex:
                    self._fatal_error(
                        ex, "application protocol failed to receive SSL data"
                    )
                    return
            else:
                self._start_shutdown()
                break

    def eof_received(self):
        "Called when the other end of the low-level stream\n        is half-closed.\n\n        If this returns a false value (including None), the transport\n        will close itself.  If it returns a true value, closing the\n        transport is up to the protocol.\n        "
        try:
            if self._loop.get_debug():
                logger.debug("%r received EOF", self)
            self._wakeup_waiter(ConnectionResetError)
            if not self._in_handshake:
                keep_open = self._app_protocol.eof_received()
                if keep_open:
                    logger.warning(
                        "returning true from eof_received() has no effect when using ssl"
                    )
        finally:
            self._transport.close()

    def _get_extra_info(self, name, default=None):
        if name in self._extra:
            return self._extra[name]
        elif self._transport is not None:
            return self._transport.get_extra_info(name, default)
        else:
            return default

    def _start_shutdown(self):
        if self._in_shutdown:
            return
        if self._in_handshake:
            self._abort()
        else:
            self._in_shutdown = True
            self._write_appdata(b"")

    def _write_appdata(self, data):
        self._write_backlog.append((data, 0))
        self._write_buffer_size += len(data)
        self._process_write_backlog()

    def _start_handshake(self):
        if self._loop.get_debug():
            logger.debug("%r starts SSL handshake", self)
            self._handshake_start_time = self._loop.time()
        else:
            self._handshake_start_time = None
        self._in_handshake = True
        self._write_backlog.append((b"", 1))
        self._handshake_timeout_handle = self._loop.call_later(
            self._ssl_handshake_timeout, self._check_handshake_timeout
        )
        self._process_write_backlog()

    def _check_handshake_timeout(self):
        if self._in_handshake is True:
            msg = f"SSL handshake is taking longer than {self._ssl_handshake_timeout} seconds: aborting the connection"
            self._fatal_error(ConnectionAbortedError(msg))

    def _on_handshake_complete(self, handshake_exc):
        self._in_handshake = False
        self._handshake_timeout_handle.cancel()
        sslobj = self._sslpipe.ssl_object
        try:
            if handshake_exc is not None:
                raise handshake_exc
            peercert = sslobj.getpeercert()
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            if isinstance(exc, ssl.CertificateError):
                msg = "SSL handshake failed on verifying the certificate"
            else:
                msg = "SSL handshake failed"
            self._fatal_error(exc, msg)
            return
        if self._loop.get_debug():
            dt = self._loop.time() - self._handshake_start_time
            logger.debug("%r: SSL handshake took %.1f ms", self, (dt * 1000.0))
        self._extra.update(
            peercert=peercert,
            cipher=sslobj.cipher(),
            compression=sslobj.compression(),
            ssl_object=sslobj,
        )
        if self._call_connection_made:
            self._app_protocol.connection_made(self._app_transport)
        self._wakeup_waiter()
        self._session_established = True
        self._loop.call_soon(self._process_write_backlog)

    def _process_write_backlog(self):
        if (self._transport is None) or (self._sslpipe is None):
            return
        try:
            for i in range(len(self._write_backlog)):
                (data, offset) = self._write_backlog[0]
                if data:
                    (ssldata, offset) = self._sslpipe.feed_appdata(data, offset)
                elif offset:
                    ssldata = self._sslpipe.do_handshake(self._on_handshake_complete)
                    offset = 1
                else:
                    ssldata = self._sslpipe.shutdown(self._finalize)
                    offset = 1
                for chunk in ssldata:
                    self._transport.write(chunk)
                if offset < len(data):
                    self._write_backlog[0] = (data, offset)
                    assert self._sslpipe.need_ssldata
                    if self._transport._paused:
                        self._transport.resume_reading()
                    break
                del self._write_backlog[0]
                self._write_buffer_size -= len(data)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            if self._in_handshake:
                self._on_handshake_complete(exc)
            else:
                self._fatal_error(exc, "Fatal error on SSL transport")

    def _fatal_error(self, exc, message="Fatal error on transport"):
        if isinstance(exc, OSError):
            if self._loop.get_debug():
                logger.debug("%r: %s", self, message, exc_info=True)
        else:
            self._loop.call_exception_handler(
                {
                    "message": message,
                    "exception": exc,
                    "transport": self._transport,
                    "protocol": self,
                }
            )
        if self._transport:
            self._transport._force_close(exc)

    def _finalize(self):
        self._sslpipe = None
        if self._transport is not None:
            self._transport.close()

    def _abort(self):
        try:
            if self._transport is not None:
                self._transport.abort()
        finally:
            self._finalize()
