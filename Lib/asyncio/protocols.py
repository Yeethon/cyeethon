"Abstract Protocol base classes."
__all__ = (
    "BaseProtocol",
    "Protocol",
    "DatagramProtocol",
    "SubprocessProtocol",
    "BufferedProtocol",
)


class BaseProtocol:
    "Common base class for protocol interfaces.\n\n    Usually user implements protocols that derived from BaseProtocol\n    like Protocol or ProcessProtocol.\n\n    The only case when BaseProtocol should be implemented directly is\n    write-only transport like write pipe\n    "
    __slots__ = ()

    def connection_made(self, transport):
        "Called when a connection is made.\n\n        The argument is the transport representing the pipe connection.\n        To receive data, wait for data_received() calls.\n        When the connection is closed, connection_lost() is called.\n        "

    def connection_lost(self, exc):
        "Called when the connection is lost or closed.\n\n        The argument is an exception object or None (the latter\n        meaning a regular EOF is received or the connection was\n        aborted or closed).\n        "

    def pause_writing(self):
        "Called when the transport's buffer goes over the high-water mark.\n\n        Pause and resume calls are paired -- pause_writing() is called\n        once when the buffer goes strictly over the high-water mark\n        (even if subsequent writes increases the buffer size even\n        more), and eventually resume_writing() is called once when the\n        buffer size reaches the low-water mark.\n\n        Note that if the buffer size equals the high-water mark,\n        pause_writing() is not called -- it must go strictly over.\n        Conversely, resume_writing() is called when the buffer size is\n        equal or lower than the low-water mark.  These end conditions\n        are important to ensure that things go as expected when either\n        mark is zero.\n\n        NOTE: This is the only Protocol callback that is not called\n        through EventLoop.call_soon() -- if it were, it would have no\n        effect when it's most needed (when the app keeps writing\n        without yielding until pause_writing() is called).\n        "

    def resume_writing(self):
        "Called when the transport's buffer drains below the low-water mark.\n\n        See pause_writing() for details.\n        "


class Protocol(BaseProtocol):
    "Interface for stream protocol.\n\n    The user should implement this interface.  They can inherit from\n    this class but don't need to.  The implementations here do\n    nothing (they don't raise exceptions).\n\n    When the user wants to requests a transport, they pass a protocol\n    factory to a utility function (e.g., EventLoop.create_connection()).\n\n    When the connection is made successfully, connection_made() is\n    called with a suitable transport object.  Then data_received()\n    will be called 0 or more times with data (bytes) received from the\n    transport; finally, connection_lost() will be called exactly once\n    with either an exception object or None as an argument.\n\n    State machine of calls:\n\n      start -> CM [-> DR*] [-> ER?] -> CL -> end\n\n    * CM: connection_made()\n    * DR: data_received()\n    * ER: eof_received()\n    * CL: connection_lost()\n    "
    __slots__ = ()

    def data_received(self, data):
        "Called when some data is received.\n\n        The argument is a bytes object.\n        "

    def eof_received(self):
        "Called when the other end calls write_eof() or equivalent.\n\n        If this returns a false value (including None), the transport\n        will close itself.  If it returns a true value, closing the\n        transport is up to the protocol.\n        "


class BufferedProtocol(BaseProtocol):
    "Interface for stream protocol with manual buffer control.\n\n    Important: this has been added to asyncio in Python 3.7\n    *on a provisional basis*!  Consider it as an experimental API that\n    might be changed or removed in Python 3.8.\n\n    Event methods, such as `create_server` and `create_connection`,\n    accept factories that return protocols that implement this interface.\n\n    The idea of BufferedProtocol is that it allows to manually allocate\n    and control the receive buffer.  Event loops can then use the buffer\n    provided by the protocol to avoid unnecessary data copies.  This\n    can result in noticeable performance improvement for protocols that\n    receive big amounts of data.  Sophisticated protocols can allocate\n    the buffer only once at creation time.\n\n    State machine of calls:\n\n      start -> CM [-> GB [-> BU?]]* [-> ER?] -> CL -> end\n\n    * CM: connection_made()\n    * GB: get_buffer()\n    * BU: buffer_updated()\n    * ER: eof_received()\n    * CL: connection_lost()\n    "
    __slots__ = ()

    def get_buffer(self, sizehint):
        "Called to allocate a new receive buffer.\n\n        *sizehint* is a recommended minimal size for the returned\n        buffer.  When set to -1, the buffer size can be arbitrary.\n\n        Must return an object that implements the\n        :ref:`buffer protocol <bufferobjects>`.\n        It is an error to return a zero-sized buffer.\n        "

    def buffer_updated(self, nbytes):
        "Called when the buffer was updated with the received data.\n\n        *nbytes* is the total number of bytes that were written to\n        the buffer.\n        "

    def eof_received(self):
        "Called when the other end calls write_eof() or equivalent.\n\n        If this returns a false value (including None), the transport\n        will close itself.  If it returns a true value, closing the\n        transport is up to the protocol.\n        "


class DatagramProtocol(BaseProtocol):
    "Interface for datagram protocol."
    __slots__ = ()

    def datagram_received(self, data, addr):
        "Called when some datagram is received."

    def error_received(self, exc):
        "Called when a send or receive operation raises an OSError.\n\n        (Other than BlockingIOError or InterruptedError.)\n        "


class SubprocessProtocol(BaseProtocol):
    "Interface for protocol for subprocess calls."
    __slots__ = ()

    def pipe_data_received(self, fd, data):
        "Called when the subprocess writes data into stdout/stderr pipe.\n\n        fd is int file descriptor.\n        data is bytes object.\n        "

    def pipe_connection_lost(self, fd, exc):
        "Called when a file descriptor associated with the child process is\n        closed.\n\n        fd is the int file descriptor that was closed.\n        "

    def process_exited(self):
        "Called when subprocess has exited."


def _feed_data_to_buffered_proto(proto, data):
    data_len = len(data)
    while data_len:
        buf = proto.get_buffer(data_len)
        buf_len = len(buf)
        if not buf_len:
            raise RuntimeError("get_buffer() returned an empty buffer")
        if buf_len >= data_len:
            buf[:data_len] = data
            proto.buffer_updated(data_len)
            return
        else:
            buf[:buf_len] = data[:buf_len]
            proto.buffer_updated(buf_len)
            data = data[buf_len:]
            data_len = len(data)
