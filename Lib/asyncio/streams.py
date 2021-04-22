__all__ = (
    "StreamReader",
    "StreamWriter",
    "StreamReaderProtocol",
    "open_connection",
    "start_server",
)
import socket
import sys
import warnings
import weakref

if hasattr(socket, "AF_UNIX"):
    __all__ += ("open_unix_connection", "start_unix_server")
from . import coroutines
from . import events
from . import exceptions
from . import format_helpers
from . import protocols
from .log import logger
from .tasks import sleep

_DEFAULT_LIMIT = 2 ** 16


async def open_connection(host=None, port=None, *, limit=_DEFAULT_LIMIT, **kwds):
    "A wrapper for create_connection() returning a (reader, writer) pair.\n\n    The reader returned is a StreamReader instance; the writer is a\n    StreamWriter instance.\n\n    The arguments are all the usual arguments to create_connection()\n    except protocol_factory; most common are positional host and port,\n    with various optional keyword arguments following.\n\n    Additional optional keyword arguments are loop (to set the event loop\n    instance to use) and limit (to set the buffer limit passed to the\n    StreamReader).\n\n    (If you want to customize the StreamReader and/or\n    StreamReaderProtocol classes, just copy the code -- there's\n    really nothing special here except some convenience.)\n    "
    loop = events.get_running_loop()
    reader = StreamReader(limit=limit, loop=loop)
    protocol = StreamReaderProtocol(reader, loop=loop)
    (transport, _) = await loop.create_connection(
        (lambda: protocol), host, port, **kwds
    )
    writer = StreamWriter(transport, protocol, reader, loop)
    return (reader, writer)


async def start_server(
    client_connected_cb, host=None, port=None, *, limit=_DEFAULT_LIMIT, **kwds
):
    "Start a socket server, call back for each client connected.\n\n    The first parameter, `client_connected_cb`, takes two parameters:\n    client_reader, client_writer.  client_reader is a StreamReader\n    object, while client_writer is a StreamWriter object.  This\n    parameter can either be a plain callback function or a coroutine;\n    if it is a coroutine, it will be automatically converted into a\n    Task.\n\n    The rest of the arguments are all the usual arguments to\n    loop.create_server() except protocol_factory; most common are\n    positional host and port, with various optional keyword arguments\n    following.  The return value is the same as loop.create_server().\n\n    Additional optional keyword arguments are loop (to set the event loop\n    instance to use) and limit (to set the buffer limit passed to the\n    StreamReader).\n\n    The return value is the same as loop.create_server(), i.e. a\n    Server object which can be used to stop the service.\n    "
    loop = events.get_running_loop()

    def factory():
        reader = StreamReader(limit=limit, loop=loop)
        protocol = StreamReaderProtocol(reader, client_connected_cb, loop=loop)
        return protocol

    return await loop.create_server(factory, host, port, **kwds)


if hasattr(socket, "AF_UNIX"):

    async def open_unix_connection(path=None, *, limit=_DEFAULT_LIMIT, **kwds):
        "Similar to `open_connection` but works with UNIX Domain Sockets."
        loop = events.get_running_loop()
        reader = StreamReader(limit=limit, loop=loop)
        protocol = StreamReaderProtocol(reader, loop=loop)
        (transport, _) = await loop.create_unix_connection(
            (lambda: protocol), path, **kwds
        )
        writer = StreamWriter(transport, protocol, reader, loop)
        return (reader, writer)

    async def start_unix_server(
        client_connected_cb, path=None, *, limit=_DEFAULT_LIMIT, **kwds
    ):
        "Similar to `start_server` but works with UNIX Domain Sockets."
        loop = events.get_running_loop()

        def factory():
            reader = StreamReader(limit=limit, loop=loop)
            protocol = StreamReaderProtocol(reader, client_connected_cb, loop=loop)
            return protocol

        return await loop.create_unix_server(factory, path, **kwds)


class FlowControlMixin(protocols.Protocol):
    "Reusable flow control logic for StreamWriter.drain().\n\n    This implements the protocol methods pause_writing(),\n    resume_writing() and connection_lost().  If the subclass overrides\n    these it must call the super methods.\n\n    StreamWriter.drain() must wait for _drain_helper() coroutine.\n    "

    def __init__(self, loop=None):
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
        self._paused = False
        self._drain_waiter = None
        self._connection_lost = False

    def pause_writing(self):
        assert not self._paused
        self._paused = True
        if self._loop.get_debug():
            logger.debug("%r pauses writing", self)

    def resume_writing(self):
        assert self._paused
        self._paused = False
        if self._loop.get_debug():
            logger.debug("%r resumes writing", self)
        waiter = self._drain_waiter
        if waiter is not None:
            self._drain_waiter = None
            if not waiter.done():
                waiter.set_result(None)

    def connection_lost(self, exc):
        self._connection_lost = True
        if not self._paused:
            return
        waiter = self._drain_waiter
        if waiter is None:
            return
        self._drain_waiter = None
        if waiter.done():
            return
        if exc is None:
            waiter.set_result(None)
        else:
            waiter.set_exception(exc)

    async def _drain_helper(self):
        if self._connection_lost:
            raise ConnectionResetError("Connection lost")
        if not self._paused:
            return
        waiter = self._drain_waiter
        assert (waiter is None) or waiter.cancelled()
        waiter = self._loop.create_future()
        self._drain_waiter = waiter
        (await waiter)

    def _get_close_waiter(self, stream):
        raise NotImplementedError


class StreamReaderProtocol(FlowControlMixin, protocols.Protocol):
    "Helper class to adapt between Protocol and StreamReader.\n\n    (This is a helper class instead of making StreamReader itself a\n    Protocol subclass, because the StreamReader has other potential\n    uses, and to prevent the user of the StreamReader to accidentally\n    call inappropriate methods of the protocol.)\n    "
    _source_traceback = None

    def __init__(self, stream_reader, client_connected_cb=None, loop=None):
        super().__init__(loop=loop)
        if stream_reader is not None:
            self._stream_reader_wr = weakref.ref(stream_reader)
            self._source_traceback = stream_reader._source_traceback
        else:
            self._stream_reader_wr = None
        if client_connected_cb is not None:
            self._strong_reader = stream_reader
        self._reject_connection = False
        self._stream_writer = None
        self._transport = None
        self._client_connected_cb = client_connected_cb
        self._over_ssl = False
        self._closed = self._loop.create_future()

    @property
    def _stream_reader(self):
        if self._stream_reader_wr is None:
            return None
        return self._stream_reader_wr()

    def connection_made(self, transport):
        if self._reject_connection:
            context = {
                "message": 'An open stream was garbage collected prior to establishing network connection; call "stream.close()" explicitly.'
            }
            if self._source_traceback:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)
            transport.abort()
            return
        self._transport = transport
        reader = self._stream_reader
        if reader is not None:
            reader.set_transport(transport)
        self._over_ssl = transport.get_extra_info("sslcontext") is not None
        if self._client_connected_cb is not None:
            self._stream_writer = StreamWriter(transport, self, reader, self._loop)
            res = self._client_connected_cb(reader, self._stream_writer)
            if coroutines.iscoroutine(res):
                self._loop.create_task(res)
            self._strong_reader = None

    def connection_lost(self, exc):
        reader = self._stream_reader
        if reader is not None:
            if exc is None:
                reader.feed_eof()
            else:
                reader.set_exception(exc)
        if not self._closed.done():
            if exc is None:
                self._closed.set_result(None)
            else:
                self._closed.set_exception(exc)
        super().connection_lost(exc)
        self._stream_reader_wr = None
        self._stream_writer = None
        self._transport = None

    def data_received(self, data):
        reader = self._stream_reader
        if reader is not None:
            reader.feed_data(data)

    def eof_received(self):
        reader = self._stream_reader
        if reader is not None:
            reader.feed_eof()
        if self._over_ssl:
            return False
        return True

    def _get_close_waiter(self, stream):
        return self._closed

    def __del__(self):
        closed = self._closed
        if closed.done() and (not closed.cancelled()):
            closed.exception()


class StreamWriter:
    "Wraps a Transport.\n\n    This exposes write(), writelines(), [can_]write_eof(),\n    get_extra_info() and close().  It adds drain() which returns an\n    optional Future on which you can wait for flow control.  It also\n    adds a transport property which references the Transport\n    directly.\n    "

    def __init__(self, transport, protocol, reader, loop):
        self._transport = transport
        self._protocol = protocol
        assert (reader is None) or isinstance(reader, StreamReader)
        self._reader = reader
        self._loop = loop
        self._complete_fut = self._loop.create_future()
        self._complete_fut.set_result(None)

    def __repr__(self):
        info = [self.__class__.__name__, f"transport={self._transport!r}"]
        if self._reader is not None:
            info.append(f"reader={self._reader!r}")
        return "<{}>".format(" ".join(info))

    @property
    def transport(self):
        return self._transport

    def write(self, data):
        self._transport.write(data)

    def writelines(self, data):
        self._transport.writelines(data)

    def write_eof(self):
        return self._transport.write_eof()

    def can_write_eof(self):
        return self._transport.can_write_eof()

    def close(self):
        return self._transport.close()

    def is_closing(self):
        return self._transport.is_closing()

    async def wait_closed(self):
        (await self._protocol._get_close_waiter(self))

    def get_extra_info(self, name, default=None):
        return self._transport.get_extra_info(name, default)

    async def drain(self):
        "Flush the write buffer.\n\n        The intended use is to write\n\n          w.write(data)\n          await w.drain()\n        "
        if self._reader is not None:
            exc = self._reader.exception()
            if exc is not None:
                raise exc
        if self._transport.is_closing():
            (await sleep(0))
        (await self._protocol._drain_helper())


class StreamReader:
    _source_traceback = None

    def __init__(self, limit=_DEFAULT_LIMIT, loop=None):
        if limit <= 0:
            raise ValueError("Limit cannot be <= 0")
        self._limit = limit
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
        self._buffer = bytearray()
        self._eof = False
        self._waiter = None
        self._exception = None
        self._transport = None
        self._paused = False
        if self._loop.get_debug():
            self._source_traceback = format_helpers.extract_stack(sys._getframe(1))

    def __repr__(self):
        info = ["StreamReader"]
        if self._buffer:
            info.append(f"{len(self._buffer)} bytes")
        if self._eof:
            info.append("eof")
        if self._limit != _DEFAULT_LIMIT:
            info.append(f"limit={self._limit}")
        if self._waiter:
            info.append(f"waiter={self._waiter!r}")
        if self._exception:
            info.append(f"exception={self._exception!r}")
        if self._transport:
            info.append(f"transport={self._transport!r}")
        if self._paused:
            info.append("paused")
        return "<{}>".format(" ".join(info))

    def exception(self):
        return self._exception

    def set_exception(self, exc):
        self._exception = exc
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_exception(exc)

    def _wakeup_waiter(self):
        "Wakeup read*() functions waiting for data or EOF."
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_result(None)

    def set_transport(self, transport):
        assert self._transport is None, "Transport already set"
        self._transport = transport

    def _maybe_resume_transport(self):
        if self._paused and (len(self._buffer) <= self._limit):
            self._paused = False
            self._transport.resume_reading()

    def feed_eof(self):
        self._eof = True
        self._wakeup_waiter()

    def at_eof(self):
        "Return True if the buffer is empty and 'feed_eof' was called."
        return self._eof and (not self._buffer)

    def feed_data(self, data):
        assert not self._eof, "feed_data after feed_eof"
        if not data:
            return
        self._buffer.extend(data)
        self._wakeup_waiter()
        if (
            (self._transport is not None)
            and (not self._paused)
            and (len(self._buffer) > (2 * self._limit))
        ):
            try:
                self._transport.pause_reading()
            except NotImplementedError:
                self._transport = None
            else:
                self._paused = True

    async def _wait_for_data(self, func_name):
        "Wait until feed_data() or feed_eof() is called.\n\n        If stream was paused, automatically resume it.\n        "
        if self._waiter is not None:
            raise RuntimeError(
                f"{func_name}() called while another coroutine is already waiting for incoming data"
            )
        assert not self._eof, "_wait_for_data after EOF"
        if self._paused:
            self._paused = False
            self._transport.resume_reading()
        self._waiter = self._loop.create_future()
        try:
            (await self._waiter)
        finally:
            self._waiter = None

    async def readline(self):
        "Read chunk of data from the stream until newline (b'\n') is found.\n\n        On success, return chunk that ends with newline. If only partial\n        line can be read due to EOF, return incomplete line without\n        terminating newline. When EOF was reached while no bytes read, empty\n        bytes object is returned.\n\n        If limit is reached, ValueError will be raised. In that case, if\n        newline was found, complete line including newline will be removed\n        from internal buffer. Else, internal buffer will be cleared. Limit is\n        compared against part of the line without newline.\n\n        If stream was paused, this function will automatically resume it if\n        needed.\n        "
        sep = b"\n"
        seplen = len(sep)
        try:
            line = await self.readuntil(sep)
        except exceptions.IncompleteReadError as e:
            return e.partial
        except exceptions.LimitOverrunError as e:
            if self._buffer.startswith(sep, e.consumed):
                del self._buffer[: (e.consumed + seplen)]
            else:
                self._buffer.clear()
            self._maybe_resume_transport()
            raise ValueError(e.args[0])
        return line

    async def readuntil(self, separator=b"\n"):
        "Read data from the stream until ``separator`` is found.\n\n        On success, the data and separator will be removed from the\n        internal buffer (consumed). Returned data will include the\n        separator at the end.\n\n        Configured stream limit is used to check result. Limit sets the\n        maximal length of data that can be returned, not counting the\n        separator.\n\n        If an EOF occurs and the complete separator is still not found,\n        an IncompleteReadError exception will be raised, and the internal\n        buffer will be reset.  The IncompleteReadError.partial attribute\n        may contain the separator partially.\n\n        If the data cannot be read because of over limit, a\n        LimitOverrunError exception  will be raised, and the data\n        will be left in the internal buffer, so it can be read again.\n        "
        seplen = len(separator)
        if seplen == 0:
            raise ValueError("Separator should be at least one-byte string")
        if self._exception is not None:
            raise self._exception
        offset = 0
        while True:
            buflen = len(self._buffer)
            if (buflen - offset) >= seplen:
                isep = self._buffer.find(separator, offset)
                if isep != (-1):
                    break
                offset = (buflen + 1) - seplen
                if offset > self._limit:
                    raise exceptions.LimitOverrunError(
                        "Separator is not found, and chunk exceed the limit", offset
                    )
            if self._eof:
                chunk = bytes(self._buffer)
                self._buffer.clear()
                raise exceptions.IncompleteReadError(chunk, None)
            (await self._wait_for_data("readuntil"))
        if isep > self._limit:
            raise exceptions.LimitOverrunError(
                "Separator is found, but chunk is longer than limit", isep
            )
        chunk = self._buffer[: (isep + seplen)]
        del self._buffer[: (isep + seplen)]
        self._maybe_resume_transport()
        return bytes(chunk)

    async def read(self, n=(-1)):
        "Read up to `n` bytes from the stream.\n\n        If n is not provided, or set to -1, read until EOF and return all read\n        bytes. If the EOF was received and the internal buffer is empty, return\n        an empty bytes object.\n\n        If n is zero, return empty bytes object immediately.\n\n        If n is positive, this function try to read `n` bytes, and may return\n        less or equal bytes than requested, but at least one byte. If EOF was\n        received before any byte is read, this function returns empty byte\n        object.\n\n        Returned value is not limited with limit, configured at stream\n        creation.\n\n        If stream was paused, this function will automatically resume it if\n        needed.\n        "
        if self._exception is not None:
            raise self._exception
        if n == 0:
            return b""
        if n < 0:
            blocks = []
            while True:
                block = await self.read(self._limit)
                if not block:
                    break
                blocks.append(block)
            return b"".join(blocks)
        if (not self._buffer) and (not self._eof):
            (await self._wait_for_data("read"))
        data = bytes(self._buffer[:n])
        del self._buffer[:n]
        self._maybe_resume_transport()
        return data

    async def readexactly(self, n):
        "Read exactly `n` bytes.\n\n        Raise an IncompleteReadError if EOF is reached before `n` bytes can be\n        read. The IncompleteReadError.partial attribute of the exception will\n        contain the partial read bytes.\n\n        if n is zero, return empty bytes object.\n\n        Returned value is not limited with limit, configured at stream\n        creation.\n\n        If stream was paused, this function will automatically resume it if\n        needed.\n        "
        if n < 0:
            raise ValueError("readexactly size can not be less than zero")
        if self._exception is not None:
            raise self._exception
        if n == 0:
            return b""
        while len(self._buffer) < n:
            if self._eof:
                incomplete = bytes(self._buffer)
                self._buffer.clear()
                raise exceptions.IncompleteReadError(incomplete, n)
            (await self._wait_for_data("readexactly"))
        if len(self._buffer) == n:
            data = bytes(self._buffer)
            self._buffer.clear()
        else:
            data = bytes(self._buffer[:n])
            del self._buffer[:n]
        self._maybe_resume_transport()
        return data

    def __aiter__(self):
        return self

    async def __anext__(self):
        val = await self.readline()
        if val == b"":
            raise StopAsyncIteration
        return val
