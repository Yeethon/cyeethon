"Event loop and event loop policy."
__all__ = (
    "AbstractEventLoopPolicy",
    "AbstractEventLoop",
    "AbstractServer",
    "Handle",
    "TimerHandle",
    "get_event_loop_policy",
    "set_event_loop_policy",
    "get_event_loop",
    "set_event_loop",
    "new_event_loop",
    "get_child_watcher",
    "set_child_watcher",
    "_set_running_loop",
    "get_running_loop",
    "_get_running_loop",
)
import contextvars
import os
import socket
import subprocess
import sys
import threading
from . import format_helpers


class Handle:
    "Object returned by callback registration methods."
    __slots__ = (
        "_callback",
        "_args",
        "_cancelled",
        "_loop",
        "_source_traceback",
        "_repr",
        "__weakref__",
        "_context",
    )

    def __init__(self, callback, args, loop, context=None):
        if context is None:
            context = contextvars.copy_context()
        self._context = context
        self._loop = loop
        self._callback = callback
        self._args = args
        self._cancelled = False
        self._repr = None
        if self._loop.get_debug():
            self._source_traceback = format_helpers.extract_stack(sys._getframe(1))
        else:
            self._source_traceback = None

    def _repr_info(self):
        info = [self.__class__.__name__]
        if self._cancelled:
            info.append("cancelled")
        if self._callback is not None:
            info.append(
                format_helpers._format_callback_source(self._callback, self._args)
            )
        if self._source_traceback:
            frame = self._source_traceback[(-1)]
            info.append(f"created at {frame[0]}:{frame[1]}")
        return info

    def __repr__(self):
        if self._repr is not None:
            return self._repr
        info = self._repr_info()
        return "<{}>".format(" ".join(info))

    def cancel(self):
        if not self._cancelled:
            self._cancelled = True
            if self._loop.get_debug():
                self._repr = repr(self)
            self._callback = None
            self._args = None

    def cancelled(self):
        return self._cancelled

    def _run(self):
        try:
            self._context.run(self._callback, *self._args)
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as exc:
            cb = format_helpers._format_callback_source(self._callback, self._args)
            msg = f"Exception in callback {cb}"
            context = {"message": msg, "exception": exc, "handle": self}
            if self._source_traceback:
                context["source_traceback"] = self._source_traceback
            self._loop.call_exception_handler(context)
        self = None


class TimerHandle(Handle):
    "Object returned by timed callback registration methods."
    __slots__ = ["_scheduled", "_when"]

    def __init__(self, when, callback, args, loop, context=None):
        assert when is not None
        super().__init__(callback, args, loop, context)
        if self._source_traceback:
            del self._source_traceback[(-1)]
        self._when = when
        self._scheduled = False

    def _repr_info(self):
        info = super()._repr_info()
        pos = 2 if self._cancelled else 1
        info.insert(pos, f"when={self._when}")
        return info

    def __hash__(self):
        return hash(self._when)

    def __lt__(self, other):
        if isinstance(other, TimerHandle):
            return self._when < other._when
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, TimerHandle):
            return (self._when < other._when) or self.__eq__(other)
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, TimerHandle):
            return self._when > other._when
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, TimerHandle):
            return (self._when > other._when) or self.__eq__(other)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, TimerHandle):
            return (
                (self._when == other._when)
                and (self._callback == other._callback)
                and (self._args == other._args)
                and (self._cancelled == other._cancelled)
            )
        return NotImplemented

    def cancel(self):
        if not self._cancelled:
            self._loop._timer_handle_cancelled(self)
        super().cancel()

    def when(self):
        "Return a scheduled callback time.\n\n        The time is an absolute timestamp, using the same time\n        reference as loop.time().\n        "
        return self._when


class AbstractServer:
    "Abstract server returned by create_server()."

    def close(self):
        "Stop serving.  This leaves existing connections open."
        raise NotImplementedError

    def get_loop(self):
        "Get the event loop the Server object is attached to."
        raise NotImplementedError

    def is_serving(self):
        "Return True if the server is accepting connections."
        raise NotImplementedError

    async def start_serving(self):
        "Start accepting connections.\n\n        This method is idempotent, so it can be called when\n        the server is already being serving.\n        "
        raise NotImplementedError

    async def serve_forever(self):
        "Start accepting connections until the coroutine is cancelled.\n\n        The server is closed when the coroutine is cancelled.\n        "
        raise NotImplementedError

    async def wait_closed(self):
        "Coroutine to wait until service is closed."
        raise NotImplementedError

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.close()
        (await self.wait_closed())


class AbstractEventLoop:
    "Abstract event loop."

    def run_forever(self):
        "Run the event loop until stop() is called."
        raise NotImplementedError

    def run_until_complete(self, future):
        "Run the event loop until a Future is done.\n\n        Return the Future's result, or raise its exception.\n        "
        raise NotImplementedError

    def stop(self):
        "Stop the event loop as soon as reasonable.\n\n        Exactly how soon that is may depend on the implementation, but\n        no more I/O callbacks should be scheduled.\n        "
        raise NotImplementedError

    def is_running(self):
        "Return whether the event loop is currently running."
        raise NotImplementedError

    def is_closed(self):
        "Returns True if the event loop was closed."
        raise NotImplementedError

    def close(self):
        "Close the loop.\n\n        The loop should not be running.\n\n        This is idempotent and irreversible.\n\n        No other methods should be called after this one.\n        "
        raise NotImplementedError

    async def shutdown_asyncgens(self):
        "Shutdown all active asynchronous generators."
        raise NotImplementedError

    async def shutdown_default_executor(self):
        "Schedule the shutdown of the default executor."
        raise NotImplementedError

    def _timer_handle_cancelled(self, handle):
        "Notification that a TimerHandle has been cancelled."
        raise NotImplementedError

    def call_soon(self, callback, *args):
        return self.call_later(0, callback, *args)

    def call_later(self, delay, callback, *args):
        raise NotImplementedError

    def call_at(self, when, callback, *args):
        raise NotImplementedError

    def time(self):
        raise NotImplementedError

    def create_future(self):
        raise NotImplementedError

    def create_task(self, coro, *, name=None):
        raise NotImplementedError

    def call_soon_threadsafe(self, callback, *args):
        raise NotImplementedError

    def run_in_executor(self, executor, func, *args):
        raise NotImplementedError

    def set_default_executor(self, executor):
        raise NotImplementedError

    async def getaddrinfo(self, host, port, *, family=0, type=0, proto=0, flags=0):
        raise NotImplementedError

    async def getnameinfo(self, sockaddr, flags=0):
        raise NotImplementedError

    async def create_connection(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
        sock=None,
        local_addr=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        happy_eyeballs_delay=None,
        interleave=None,
    ):
        raise NotImplementedError

    async def create_server(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        family=socket.AF_UNSPEC,
        flags=socket.AI_PASSIVE,
        sock=None,
        backlog=100,
        ssl=None,
        reuse_address=None,
        reuse_port=None,
        ssl_handshake_timeout=None,
        start_serving=True,
    ):
        "A coroutine which creates a TCP server bound to host and port.\n\n        The return value is a Server object which can be used to stop\n        the service.\n\n        If host is an empty string or None all interfaces are assumed\n        and a list of multiple sockets will be returned (most likely\n        one for IPv4 and another one for IPv6). The host parameter can also be\n        a sequence (e.g. list) of hosts to bind to.\n\n        family can be set to either AF_INET or AF_INET6 to force the\n        socket to use IPv4 or IPv6. If not set it will be determined\n        from host (defaults to AF_UNSPEC).\n\n        flags is a bitmask for getaddrinfo().\n\n        sock can optionally be specified in order to use a preexisting\n        socket object.\n\n        backlog is the maximum number of queued connections passed to\n        listen() (defaults to 100).\n\n        ssl can be set to an SSLContext to enable SSL over the\n        accepted connections.\n\n        reuse_address tells the kernel to reuse a local socket in\n        TIME_WAIT state, without waiting for its natural timeout to\n        expire. If not specified will automatically be set to True on\n        UNIX.\n\n        reuse_port tells the kernel to allow this endpoint to be bound to\n        the same port as other existing endpoints are bound to, so long as\n        they all set this flag when being created. This option is not\n        supported on Windows.\n\n        ssl_handshake_timeout is the time in seconds that an SSL server\n        will wait for completion of the SSL handshake before aborting the\n        connection. Default is 60s.\n\n        start_serving set to True (default) causes the created server\n        to start accepting connections immediately.  When set to False,\n        the user should await Server.start_serving() or Server.serve_forever()\n        to make the server to start accepting connections.\n        "
        raise NotImplementedError

    async def sendfile(self, transport, file, offset=0, count=None, *, fallback=True):
        "Send a file through a transport.\n\n        Return an amount of sent bytes.\n        "
        raise NotImplementedError

    async def start_tls(
        self,
        transport,
        protocol,
        sslcontext,
        *,
        server_side=False,
        server_hostname=None,
        ssl_handshake_timeout=None,
    ):
        "Upgrade a transport to TLS.\n\n        Return a new transport that *protocol* should start using\n        immediately.\n        "
        raise NotImplementedError

    async def create_unix_connection(
        self,
        protocol_factory,
        path=None,
        *,
        ssl=None,
        sock=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
    ):
        raise NotImplementedError

    async def create_unix_server(
        self,
        protocol_factory,
        path=None,
        *,
        sock=None,
        backlog=100,
        ssl=None,
        ssl_handshake_timeout=None,
        start_serving=True,
    ):
        "A coroutine which creates a UNIX Domain Socket server.\n\n        The return value is a Server object, which can be used to stop\n        the service.\n\n        path is a str, representing a file system path to bind the\n        server socket to.\n\n        sock can optionally be specified in order to use a preexisting\n        socket object.\n\n        backlog is the maximum number of queued connections passed to\n        listen() (defaults to 100).\n\n        ssl can be set to an SSLContext to enable SSL over the\n        accepted connections.\n\n        ssl_handshake_timeout is the time in seconds that an SSL server\n        will wait for the SSL handshake to complete (defaults to 60s).\n\n        start_serving set to True (default) causes the created server\n        to start accepting connections immediately.  When set to False,\n        the user should await Server.start_serving() or Server.serve_forever()\n        to make the server to start accepting connections.\n        "
        raise NotImplementedError

    async def connect_accepted_socket(
        self, protocol_factory, sock, *, ssl=None, ssl_handshake_timeout=None
    ):
        "Handle an accepted connection.\n\n        This is used by servers that accept connections outside of\n        asyncio, but use asyncio to handle connections.\n\n        This method is a coroutine.  When completed, the coroutine\n        returns a (transport, protocol) pair.\n        "
        raise NotImplementedError

    async def create_datagram_endpoint(
        self,
        protocol_factory,
        local_addr=None,
        remote_addr=None,
        *,
        family=0,
        proto=0,
        flags=0,
        reuse_address=None,
        reuse_port=None,
        allow_broadcast=None,
        sock=None,
    ):
        "A coroutine which creates a datagram endpoint.\n\n        This method will try to establish the endpoint in the background.\n        When successful, the coroutine returns a (transport, protocol) pair.\n\n        protocol_factory must be a callable returning a protocol instance.\n\n        socket family AF_INET, socket.AF_INET6 or socket.AF_UNIX depending on\n        host (or family if specified), socket type SOCK_DGRAM.\n\n        reuse_address tells the kernel to reuse a local socket in\n        TIME_WAIT state, without waiting for its natural timeout to\n        expire. If not specified it will automatically be set to True on\n        UNIX.\n\n        reuse_port tells the kernel to allow this endpoint to be bound to\n        the same port as other existing endpoints are bound to, so long as\n        they all set this flag when being created. This option is not\n        supported on Windows and some UNIX's. If the\n        :py:data:`~socket.SO_REUSEPORT` constant is not defined then this\n        capability is unsupported.\n\n        allow_broadcast tells the kernel to allow this endpoint to send\n        messages to the broadcast address.\n\n        sock can optionally be specified in order to use a preexisting\n        socket object.\n        "
        raise NotImplementedError

    async def connect_read_pipe(self, protocol_factory, pipe):
        "Register read pipe in event loop. Set the pipe to non-blocking mode.\n\n        protocol_factory should instantiate object with Protocol interface.\n        pipe is a file-like object.\n        Return pair (transport, protocol), where transport supports the\n        ReadTransport interface."
        raise NotImplementedError

    async def connect_write_pipe(self, protocol_factory, pipe):
        "Register write pipe in event loop.\n\n        protocol_factory should instantiate object with BaseProtocol interface.\n        Pipe is file-like object already switched to nonblocking.\n        Return pair (transport, protocol), where transport support\n        WriteTransport interface."
        raise NotImplementedError

    async def subprocess_shell(
        self,
        protocol_factory,
        cmd,
        *,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    ):
        raise NotImplementedError

    async def subprocess_exec(
        self,
        protocol_factory,
        *args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs,
    ):
        raise NotImplementedError

    def add_reader(self, fd, callback, *args):
        raise NotImplementedError

    def remove_reader(self, fd):
        raise NotImplementedError

    def add_writer(self, fd, callback, *args):
        raise NotImplementedError

    def remove_writer(self, fd):
        raise NotImplementedError

    async def sock_recv(self, sock, nbytes):
        raise NotImplementedError

    async def sock_recv_into(self, sock, buf):
        raise NotImplementedError

    async def sock_sendall(self, sock, data):
        raise NotImplementedError

    async def sock_connect(self, sock, address):
        raise NotImplementedError

    async def sock_accept(self, sock):
        raise NotImplementedError

    async def sock_sendfile(self, sock, file, offset=0, count=None, *, fallback=None):
        raise NotImplementedError

    def add_signal_handler(self, sig, callback, *args):
        raise NotImplementedError

    def remove_signal_handler(self, sig):
        raise NotImplementedError

    def set_task_factory(self, factory):
        raise NotImplementedError

    def get_task_factory(self):
        raise NotImplementedError

    def get_exception_handler(self):
        raise NotImplementedError

    def set_exception_handler(self, handler):
        raise NotImplementedError

    def default_exception_handler(self, context):
        raise NotImplementedError

    def call_exception_handler(self, context):
        raise NotImplementedError

    def get_debug(self):
        raise NotImplementedError

    def set_debug(self, enabled):
        raise NotImplementedError


class AbstractEventLoopPolicy:
    "Abstract policy for accessing the event loop."

    def get_event_loop(self):
        "Get the event loop for the current context.\n\n        Returns an event loop object implementing the BaseEventLoop interface,\n        or raises an exception in case no event loop has been set for the\n        current context and the current policy does not specify to create one.\n\n        It should never return None."
        raise NotImplementedError

    def set_event_loop(self, loop):
        "Set the event loop for the current context to loop."
        raise NotImplementedError

    def new_event_loop(self):
        "Create and return a new event loop object according to this\n        policy's rules. If there's need to set this loop as the event loop for\n        the current context, set_event_loop must be called explicitly."
        raise NotImplementedError

    def get_child_watcher(self):
        "Get the watcher for child processes."
        raise NotImplementedError

    def set_child_watcher(self, watcher):
        "Set the watcher for child processes."
        raise NotImplementedError


class BaseDefaultEventLoopPolicy(AbstractEventLoopPolicy):
    "Default policy implementation for accessing the event loop.\n\n    In this policy, each thread has its own event loop.  However, we\n    only automatically create an event loop by default for the main\n    thread; other threads by default have no event loop.\n\n    Other policies may have different rules (e.g. a single global\n    event loop, or automatically creating an event loop per thread, or\n    using some other notion of context to which an event loop is\n    associated).\n    "
    _loop_factory = None

    class _Local(threading.local):
        _loop = None
        _set_called = False

    def __init__(self):
        self._local = self._Local()

    def get_event_loop(self):
        "Get the event loop for the current context.\n\n        Returns an instance of EventLoop or raises an exception.\n        "
        if (
            (self._local._loop is None)
            and (not self._local._set_called)
            and (threading.current_thread() is threading.main_thread())
        ):
            self.set_event_loop(self.new_event_loop())
        if self._local._loop is None:
            raise RuntimeError(
                (
                    "There is no current event loop in thread %r."
                    % threading.current_thread().name
                )
            )
        return self._local._loop

    def set_event_loop(self, loop):
        "Set the event loop."
        self._local._set_called = True
        assert (loop is None) or isinstance(loop, AbstractEventLoop)
        self._local._loop = loop

    def new_event_loop(self):
        "Create a new event loop.\n\n        You must call set_event_loop() to make this the current event\n        loop.\n        "
        return self._loop_factory()


_event_loop_policy = None
_lock = threading.Lock()


class _RunningLoop(threading.local):
    loop_pid = (None, None)


_running_loop = _RunningLoop()


def get_running_loop():
    "Return the running event loop.  Raise a RuntimeError if there is none.\n\n    This function is thread-specific.\n    "
    loop = _get_running_loop()
    if loop is None:
        raise RuntimeError("no running event loop")
    return loop


def _get_running_loop():
    "Return the running event loop or None.\n\n    This is a low-level function intended to be used by event loops.\n    This function is thread-specific.\n    "
    (running_loop, pid) = _running_loop.loop_pid
    if (running_loop is not None) and (pid == os.getpid()):
        return running_loop


def _set_running_loop(loop):
    "Set the running event loop.\n\n    This is a low-level function intended to be used by event loops.\n    This function is thread-specific.\n    "
    _running_loop.loop_pid = (loop, os.getpid())


def _init_event_loop_policy():
    global _event_loop_policy
    with _lock:
        if _event_loop_policy is None:
            from . import DefaultEventLoopPolicy

            _event_loop_policy = DefaultEventLoopPolicy()


def get_event_loop_policy():
    "Get the current event loop policy."
    if _event_loop_policy is None:
        _init_event_loop_policy()
    return _event_loop_policy


def set_event_loop_policy(policy):
    "Set the current event loop policy.\n\n    If policy is None, the default policy is restored."
    global _event_loop_policy
    assert (policy is None) or isinstance(policy, AbstractEventLoopPolicy)
    _event_loop_policy = policy


def get_event_loop():
    "Return an asyncio event loop.\n\n    When called from a coroutine or a callback (e.g. scheduled with call_soon\n    or similar API), this function will always return the running event loop.\n\n    If there is no running event loop set, the function will return\n    the result of `get_event_loop_policy().get_event_loop()` call.\n    "
    current_loop = _get_running_loop()
    if current_loop is not None:
        return current_loop
    return get_event_loop_policy().get_event_loop()


def set_event_loop(loop):
    "Equivalent to calling get_event_loop_policy().set_event_loop(loop)."
    get_event_loop_policy().set_event_loop(loop)


def new_event_loop():
    "Equivalent to calling get_event_loop_policy().new_event_loop()."
    return get_event_loop_policy().new_event_loop()


def get_child_watcher():
    "Equivalent to calling get_event_loop_policy().get_child_watcher()."
    return get_event_loop_policy().get_child_watcher()


def set_child_watcher(watcher):
    "Equivalent to calling\n    get_event_loop_policy().set_child_watcher(watcher)."
    return get_event_loop_policy().set_child_watcher(watcher)


_py__get_running_loop = _get_running_loop
_py__set_running_loop = _set_running_loop
_py_get_running_loop = get_running_loop
_py_get_event_loop = get_event_loop
try:
    from _asyncio import (
        _get_running_loop,
        _set_running_loop,
        get_running_loop,
        get_event_loop,
    )
except ImportError:
    pass
else:
    _c__get_running_loop = _get_running_loop
    _c__set_running_loop = _set_running_loop
    _c_get_running_loop = get_running_loop
    _c_get_event_loop = get_event_loop
