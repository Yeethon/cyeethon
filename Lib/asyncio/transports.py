"Abstract Transport class."
__all__ = (
    "BaseTransport",
    "ReadTransport",
    "WriteTransport",
    "Transport",
    "DatagramTransport",
    "SubprocessTransport",
)


class BaseTransport:
    "Base class for transports."
    __slots__ = ("_extra",)

    def __init__(self, extra=None):
        if extra is None:
            extra = {}
        self._extra = extra

    def get_extra_info(self, name, default=None):
        "Get optional transport information."
        return self._extra.get(name, default)

    def is_closing(self):
        "Return True if the transport is closing or closed."
        raise NotImplementedError

    def close(self):
        "Close the transport.\n\n        Buffered data will be flushed asynchronously.  No more data\n        will be received.  After all buffered data is flushed, the\n        protocol's connection_lost() method will (eventually) be\n        called with None as its argument.\n        "
        raise NotImplementedError

    def set_protocol(self, protocol):
        "Set a new protocol."
        raise NotImplementedError

    def get_protocol(self):
        "Return the current protocol."
        raise NotImplementedError


class ReadTransport(BaseTransport):
    "Interface for read-only transports."
    __slots__ = ()

    def is_reading(self):
        "Return True if the transport is receiving."
        raise NotImplementedError

    def pause_reading(self):
        "Pause the receiving end.\n\n        No data will be passed to the protocol's data_received()\n        method until resume_reading() is called.\n        "
        raise NotImplementedError

    def resume_reading(self):
        "Resume the receiving end.\n\n        Data received will once again be passed to the protocol's\n        data_received() method.\n        "
        raise NotImplementedError


class WriteTransport(BaseTransport):
    "Interface for write-only transports."
    __slots__ = ()

    def set_write_buffer_limits(self, high=None, low=None):
        "Set the high- and low-water limits for write flow control.\n\n        These two values control when to call the protocol's\n        pause_writing() and resume_writing() methods.  If specified,\n        the low-water limit must be less than or equal to the\n        high-water limit.  Neither value can be negative.\n\n        The defaults are implementation-specific.  If only the\n        high-water limit is given, the low-water limit defaults to an\n        implementation-specific value less than or equal to the\n        high-water limit.  Setting high to zero forces low to zero as\n        well, and causes pause_writing() to be called whenever the\n        buffer becomes non-empty.  Setting low to zero causes\n        resume_writing() to be called only once the buffer is empty.\n        Use of zero for either limit is generally sub-optimal as it\n        reduces opportunities for doing I/O and computation\n        concurrently.\n        "
        raise NotImplementedError

    def get_write_buffer_size(self):
        "Return the current size of the write buffer."
        raise NotImplementedError

    def write(self, data):
        "Write some data bytes to the transport.\n\n        This does not block; it buffers the data and arranges for it\n        to be sent out asynchronously.\n        "
        raise NotImplementedError

    def writelines(self, list_of_data):
        "Write a list (or any iterable) of data bytes to the transport.\n\n        The default implementation concatenates the arguments and\n        calls write() on the result.\n        "
        data = b"".join(list_of_data)
        self.write(data)

    def write_eof(self):
        "Close the write end after flushing buffered data.\n\n        (This is like typing ^D into a UNIX program reading from stdin.)\n\n        Data may still be received.\n        "
        raise NotImplementedError

    def can_write_eof(self):
        "Return True if this transport supports write_eof(), False if not."
        raise NotImplementedError

    def abort(self):
        "Close the transport immediately.\n\n        Buffered data will be lost.  No more data will be received.\n        The protocol's connection_lost() method will (eventually) be\n        called with None as its argument.\n        "
        raise NotImplementedError


class Transport(ReadTransport, WriteTransport):
    "Interface representing a bidirectional transport.\n\n    There may be several implementations, but typically, the user does\n    not implement new transports; rather, the platform provides some\n    useful transports that are implemented using the platform's best\n    practices.\n\n    The user never instantiates a transport directly; they call a\n    utility function, passing it a protocol factory and other\n    information necessary to create the transport and protocol.  (E.g.\n    EventLoop.create_connection() or EventLoop.create_server().)\n\n    The utility function will asynchronously create a transport and a\n    protocol and hook them up by calling the protocol's\n    connection_made() method, passing it the transport.\n\n    The implementation here raises NotImplemented for every method\n    except writelines(), which calls write() in a loop.\n    "
    __slots__ = ()


class DatagramTransport(BaseTransport):
    "Interface for datagram (UDP) transports."
    __slots__ = ()

    def sendto(self, data, addr=None):
        "Send data to the transport.\n\n        This does not block; it buffers the data and arranges for it\n        to be sent out asynchronously.\n        addr is target socket address.\n        If addr is None use target address pointed on transport creation.\n        "
        raise NotImplementedError

    def abort(self):
        "Close the transport immediately.\n\n        Buffered data will be lost.  No more data will be received.\n        The protocol's connection_lost() method will (eventually) be\n        called with None as its argument.\n        "
        raise NotImplementedError


class SubprocessTransport(BaseTransport):
    __slots__ = ()

    def get_pid(self):
        "Get subprocess id."
        raise NotImplementedError

    def get_returncode(self):
        "Get subprocess returncode.\n\n        See also\n        http://docs.python.org/3/library/subprocess#subprocess.Popen.returncode\n        "
        raise NotImplementedError

    def get_pipe_transport(self, fd):
        "Get transport for pipe with number fd."
        raise NotImplementedError

    def send_signal(self, signal):
        "Send signal to subprocess.\n\n        See also:\n        docs.python.org/3/library/subprocess#subprocess.Popen.send_signal\n        "
        raise NotImplementedError

    def terminate(self):
        "Stop the subprocess.\n\n        Alias for close() method.\n\n        On Posix OSs the method sends SIGTERM to the subprocess.\n        On Windows the Win32 API function TerminateProcess()\n         is called to stop the subprocess.\n\n        See also:\n        http://docs.python.org/3/library/subprocess#subprocess.Popen.terminate\n        "
        raise NotImplementedError

    def kill(self):
        "Kill the subprocess.\n\n        On Posix OSs the function sends SIGKILL to the subprocess.\n        On Windows kill() is an alias for terminate().\n\n        See also:\n        http://docs.python.org/3/library/subprocess#subprocess.Popen.kill\n        "
        raise NotImplementedError


class _FlowControlMixin(Transport):
    "All the logic for (write) flow control in a mix-in base class.\n\n    The subclass must implement get_write_buffer_size().  It must call\n    _maybe_pause_protocol() whenever the write buffer size increases,\n    and _maybe_resume_protocol() whenever it decreases.  It may also\n    override set_write_buffer_limits() (e.g. to specify different\n    defaults).\n\n    The subclass constructor must call super().__init__(extra).  This\n    will call set_write_buffer_limits().\n\n    The user may call set_write_buffer_limits() and\n    get_write_buffer_size(), and their protocol's pause_writing() and\n    resume_writing() may be called.\n    "
    __slots__ = ("_loop", "_protocol_paused", "_high_water", "_low_water")

    def __init__(self, extra=None, loop=None):
        super().__init__(extra)
        assert loop is not None
        self._loop = loop
        self._protocol_paused = False
        self._set_write_buffer_limits()

    def _maybe_pause_protocol(self):
        size = self.get_write_buffer_size()
        if size <= self._high_water:
            return
        if not self._protocol_paused:
            self._protocol_paused = True
            try:
                self._protocol.pause_writing()
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as exc:
                self._loop.call_exception_handler(
                    {
                        "message": "protocol.pause_writing() failed",
                        "exception": exc,
                        "transport": self,
                        "protocol": self._protocol,
                    }
                )

    def _maybe_resume_protocol(self):
        if self._protocol_paused and (self.get_write_buffer_size() <= self._low_water):
            self._protocol_paused = False
            try:
                self._protocol.resume_writing()
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as exc:
                self._loop.call_exception_handler(
                    {
                        "message": "protocol.resume_writing() failed",
                        "exception": exc,
                        "transport": self,
                        "protocol": self._protocol,
                    }
                )

    def get_write_buffer_limits(self):
        return (self._low_water, self._high_water)

    def _set_write_buffer_limits(self, high=None, low=None):
        if high is None:
            if low is None:
                high = 64 * 1024
            else:
                high = 4 * low
        if low is None:
            low = high // 4
        if not (high >= low >= 0):
            raise ValueError(f"high ({high!r}) must be >= low ({low!r}) must be >= 0")
        self._high_water = high
        self._low_water = low

    def set_write_buffer_limits(self, high=None, low=None):
        self._set_write_buffer_limits(high=high, low=low)
        self._maybe_pause_protocol()

    def get_write_buffer_size(self):
        raise NotImplementedError
