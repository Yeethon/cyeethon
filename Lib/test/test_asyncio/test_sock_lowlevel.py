import socket
import time
import asyncio
import sys
import unittest
from asyncio import proactor_events
from itertools import cycle, islice
from test.test_asyncio import utils as test_utils
from test import support
from test.support import socket_helper


class MyProto(asyncio.Protocol):
    connected = None
    done = None

    def __init__(self, loop=None):
        self.transport = None
        self.state = "INITIAL"
        self.nbytes = 0
        if loop is not None:
            self.connected = loop.create_future()
            self.done = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        assert self.state == "INITIAL", self.state
        self.state = "CONNECTED"
        if self.connected:
            self.connected.set_result(None)
        transport.write(b"GET / HTTP/1.0\r\nHost: example.com\r\n\r\n")

    def data_received(self, data):
        assert self.state == "CONNECTED", self.state
        self.nbytes += len(data)

    def eof_received(self):
        assert self.state == "CONNECTED", self.state
        self.state = "EOF"

    def connection_lost(self, exc):
        assert self.state in ("CONNECTED", "EOF"), self.state
        self.state = "CLOSED"
        if self.done:
            self.done.set_result(None)


class BaseSockTestsMixin:
    def create_event_loop(self):
        raise NotImplementedError

    def setUp(self):
        self.loop = self.create_event_loop()
        self.set_event_loop(self.loop)
        super().setUp()

    def tearDown(self):
        if not self.loop.is_closed():
            test_utils.run_briefly(self.loop)
        self.doCleanups()
        support.gc_collect()
        super().tearDown()

    def _basetest_sock_client_ops(self, httpd, sock):
        if not isinstance(self.loop, proactor_events.BaseProactorEventLoop):
            self.loop.set_debug(True)
            sock.setblocking(True)
            with self.assertRaises(ValueError):
                self.loop.run_until_complete(
                    self.loop.sock_connect(sock, httpd.address)
                )
            with self.assertRaises(ValueError):
                self.loop.run_until_complete(
                    self.loop.sock_sendall(sock, b"GET / HTTP/1.0\r\n\r\n")
                )
            with self.assertRaises(ValueError):
                self.loop.run_until_complete(self.loop.sock_recv(sock, 1024))
            with self.assertRaises(ValueError):
                self.loop.run_until_complete(
                    self.loop.sock_recv_into(sock, bytearray())
                )
            with self.assertRaises(ValueError):
                self.loop.run_until_complete(self.loop.sock_accept(sock))
        sock.setblocking(False)
        self.loop.run_until_complete(self.loop.sock_connect(sock, httpd.address))
        self.loop.run_until_complete(
            self.loop.sock_sendall(sock, b"GET / HTTP/1.0\r\n\r\n")
        )
        data = self.loop.run_until_complete(self.loop.sock_recv(sock, 1024))
        self.loop.run_until_complete(self.loop.sock_recv(sock, 1024))
        sock.close()
        self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))

    def _basetest_sock_recv_into(self, httpd, sock):
        sock.setblocking(False)
        self.loop.run_until_complete(self.loop.sock_connect(sock, httpd.address))
        self.loop.run_until_complete(
            self.loop.sock_sendall(sock, b"GET / HTTP/1.0\r\n\r\n")
        )
        data = bytearray(1024)
        with memoryview(data) as buf:
            nbytes = self.loop.run_until_complete(
                self.loop.sock_recv_into(sock, buf[:1024])
            )
            self.loop.run_until_complete(self.loop.sock_recv_into(sock, buf[nbytes:]))
        sock.close()
        self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))

    def test_sock_client_ops(self):
        with test_utils.run_test_server() as httpd:
            sock = socket.socket()
            self._basetest_sock_client_ops(httpd, sock)
            sock = socket.socket()
            self._basetest_sock_recv_into(httpd, sock)

    async def _basetest_sock_recv_racing(self, httpd, sock):
        sock.setblocking(False)
        (await self.loop.sock_connect(sock, httpd.address))
        task = asyncio.create_task(self.loop.sock_recv(sock, 1024))
        (await asyncio.sleep(0))
        task.cancel()
        asyncio.create_task(self.loop.sock_sendall(sock, b"GET / HTTP/1.0\r\n\r\n"))
        data = await self.loop.sock_recv(sock, 1024)
        (await self.loop.sock_recv(sock, 1024))
        self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))

    async def _basetest_sock_recv_into_racing(self, httpd, sock):
        sock.setblocking(False)
        (await self.loop.sock_connect(sock, httpd.address))
        data = bytearray(1024)
        with memoryview(data) as buf:
            task = asyncio.create_task(self.loop.sock_recv_into(sock, buf[:1024]))
            (await asyncio.sleep(0))
            task.cancel()
            task = asyncio.create_task(
                self.loop.sock_sendall(sock, b"GET / HTTP/1.0\r\n\r\n")
            )
            nbytes = await self.loop.sock_recv_into(sock, buf[:1024])
            (await self.loop.sock_recv_into(sock, buf[nbytes:]))
            self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))
        (await task)

    async def _basetest_sock_send_racing(self, listener, sock):
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        sock.setblocking(False)
        task = asyncio.create_task(self.loop.sock_connect(sock, listener.getsockname()))
        (await asyncio.sleep(0))
        server = listener.accept()[0]
        server.setblocking(False)
        with server:
            (await task)
            size = 8192
            while size >= 4:
                with self.assertRaises(BlockingIOError):
                    while True:
                        sock.send((b" " * size))
                size = int((size / 2))
            task = asyncio.create_task(self.loop.sock_sendall(sock, b"hello"))
            (await asyncio.sleep(0))
            task.cancel()

            async def recv_all():
                rv = b""
                while True:
                    buf = await self.loop.sock_recv(server, 8192)
                    if not buf:
                        return rv
                    rv += buf.strip()

            task = asyncio.create_task(recv_all())
            (await self.loop.sock_sendall(sock, b"world"))
            sock.shutdown(socket.SHUT_WR)
            data = await task
            self.assertTrue(data.endswith(b"world"))

    async def _basetest_sock_connect_racing(self, listener, sock):
        listener.bind(("127.0.0.1", 0))
        addr = listener.getsockname()
        sock.setblocking(False)
        task = asyncio.create_task(self.loop.sock_connect(sock, addr))
        (await asyncio.sleep(0))
        task.cancel()
        listener.listen(1)
        skip_reason = "Max retries reached"
        for i in range(128):
            try:
                (await self.loop.sock_connect(sock, addr))
            except ConnectionRefusedError as e:
                skip_reason = e
            except OSError as e:
                skip_reason = e
                if getattr(e, "winerror", 0) != 10022:
                    break
            else:
                return
        self.skipTest(skip_reason)

    def test_sock_client_racing(self):
        with test_utils.run_test_server() as httpd:
            sock = socket.socket()
            with sock:
                self.loop.run_until_complete(
                    asyncio.wait_for(self._basetest_sock_recv_racing(httpd, sock), 10)
                )
            sock = socket.socket()
            with sock:
                self.loop.run_until_complete(
                    asyncio.wait_for(
                        self._basetest_sock_recv_into_racing(httpd, sock), 10
                    )
                )
        listener = socket.socket()
        sock = socket.socket()
        with listener, sock:
            self.loop.run_until_complete(
                asyncio.wait_for(self._basetest_sock_send_racing(listener, sock), 10)
            )

    def test_sock_client_connect_racing(self):
        listener = socket.socket()
        sock = socket.socket()
        with listener, sock:
            self.loop.run_until_complete(
                asyncio.wait_for(self._basetest_sock_connect_racing(listener, sock), 10)
            )

    async def _basetest_huge_content(self, address):
        sock = socket.socket()
        sock.setblocking(False)
        DATA_SIZE = 1000000
        chunk = b"0123456789" * (DATA_SIZE // 10)
        (await self.loop.sock_connect(sock, address))
        (
            await self.loop.sock_sendall(
                sock,
                (
                    (
                        b"POST /loop HTTP/1.0\r\n"
                        + (b"Content-Length: %d\r\n" % DATA_SIZE)
                    )
                    + b"\r\n"
                ),
            )
        )
        task = asyncio.create_task(self.loop.sock_sendall(sock, chunk))
        data = await self.loop.sock_recv(sock, DATA_SIZE)
        self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))
        while data.find(b"\r\n\r\n") == (-1):
            data += await self.loop.sock_recv(sock, DATA_SIZE)
        headers = data[: (data.index(b"\r\n\r\n") + 4)]
        data = data[len(headers) :]
        size = DATA_SIZE
        checker = cycle(b"0123456789")
        expected = bytes(islice(checker, len(data)))
        self.assertEqual(data, expected)
        size -= len(data)
        while True:
            data = await self.loop.sock_recv(sock, DATA_SIZE)
            if not data:
                break
            expected = bytes(islice(checker, len(data)))
            self.assertEqual(data, expected)
            size -= len(data)
        self.assertEqual(size, 0)
        (await task)
        sock.close()

    def test_huge_content(self):
        with test_utils.run_test_server() as httpd:
            self.loop.run_until_complete(self._basetest_huge_content(httpd.address))

    async def _basetest_huge_content_recvinto(self, address):
        sock = socket.socket()
        sock.setblocking(False)
        DATA_SIZE = 1000000
        chunk = b"0123456789" * (DATA_SIZE // 10)
        (await self.loop.sock_connect(sock, address))
        (
            await self.loop.sock_sendall(
                sock,
                (
                    (
                        b"POST /loop HTTP/1.0\r\n"
                        + (b"Content-Length: %d\r\n" % DATA_SIZE)
                    )
                    + b"\r\n"
                ),
            )
        )
        task = asyncio.create_task(self.loop.sock_sendall(sock, chunk))
        array = bytearray(DATA_SIZE)
        buf = memoryview(array)
        nbytes = await self.loop.sock_recv_into(sock, buf)
        data = bytes(buf[:nbytes])
        self.assertTrue(data.startswith(b"HTTP/1.0 200 OK"))
        while data.find(b"\r\n\r\n") == (-1):
            nbytes = await self.loop.sock_recv_into(sock, buf)
            data = bytes(buf[:nbytes])
        headers = data[: (data.index(b"\r\n\r\n") + 4)]
        data = data[len(headers) :]
        size = DATA_SIZE
        checker = cycle(b"0123456789")
        expected = bytes(islice(checker, len(data)))
        self.assertEqual(data, expected)
        size -= len(data)
        while True:
            nbytes = await self.loop.sock_recv_into(sock, buf)
            data = buf[:nbytes]
            if not data:
                break
            expected = bytes(islice(checker, len(data)))
            self.assertEqual(data, expected)
            size -= len(data)
        self.assertEqual(size, 0)
        (await task)
        sock.close()

    def test_huge_content_recvinto(self):
        with test_utils.run_test_server() as httpd:
            self.loop.run_until_complete(
                self._basetest_huge_content_recvinto(httpd.address)
            )

    @socket_helper.skip_unless_bind_unix_socket
    def test_unix_sock_client_ops(self):
        with test_utils.run_test_unix_server() as httpd:
            sock = socket.socket(socket.AF_UNIX)
            self._basetest_sock_client_ops(httpd, sock)
            sock = socket.socket(socket.AF_UNIX)
            self._basetest_sock_recv_into(httpd, sock)

    def test_sock_client_fail(self):
        address = None
        try:
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            address = s.getsockname()
        finally:
            s.close()
        sock = socket.socket()
        sock.setblocking(False)
        with self.assertRaises(ConnectionRefusedError):
            self.loop.run_until_complete(self.loop.sock_connect(sock, address))
        sock.close()

    def test_sock_accept(self):
        listener = socket.socket()
        listener.setblocking(False)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.socket()
        client.connect(listener.getsockname())
        f = self.loop.sock_accept(listener)
        (conn, addr) = self.loop.run_until_complete(f)
        self.assertEqual(conn.gettimeout(), 0)
        self.assertEqual(addr, client.getsockname())
        self.assertEqual(client.getpeername(), listener.getsockname())
        client.close()
        conn.close()
        listener.close()

    def test_cancel_sock_accept(self):
        listener = socket.socket()
        listener.setblocking(False)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        sockaddr = listener.getsockname()
        f = asyncio.wait_for(self.loop.sock_accept(listener), 0.1)
        with self.assertRaises(asyncio.TimeoutError):
            self.loop.run_until_complete(f)
        listener.close()
        client = socket.socket()
        client.setblocking(False)
        f = self.loop.sock_connect(client, sockaddr)
        with self.assertRaises(ConnectionRefusedError):
            self.loop.run_until_complete(f)
        client.close()

    def test_create_connection_sock(self):
        with test_utils.run_test_server() as httpd:
            sock = None
            infos = self.loop.run_until_complete(
                self.loop.getaddrinfo(*httpd.address, type=socket.SOCK_STREAM)
            )
            for (family, type, proto, cname, address) in infos:
                try:
                    sock = socket.socket(family=family, type=type, proto=proto)
                    sock.setblocking(False)
                    self.loop.run_until_complete(self.loop.sock_connect(sock, address))
                except BaseException:
                    pass
                else:
                    break
            else:
                assert False, "Can not create socket."
            f = self.loop.create_connection(
                (lambda: MyProto(loop=self.loop)), sock=sock
            )
            (tr, pr) = self.loop.run_until_complete(f)
            self.assertIsInstance(tr, asyncio.Transport)
            self.assertIsInstance(pr, asyncio.Protocol)
            self.loop.run_until_complete(pr.done)
            self.assertGreater(pr.nbytes, 0)
            tr.close()


if sys.platform == "win32":

    class SelectEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
        def create_event_loop(self):
            return asyncio.SelectorEventLoop()

    class ProactorEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
        def create_event_loop(self):
            return asyncio.ProactorEventLoop()


else:
    import selectors

    if hasattr(selectors, "KqueueSelector"):

        class KqueueEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
            def create_event_loop(self):
                return asyncio.SelectorEventLoop(selectors.KqueueSelector())

    if hasattr(selectors, "EpollSelector"):

        class EPollEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
            def create_event_loop(self):
                return asyncio.SelectorEventLoop(selectors.EpollSelector())

    if hasattr(selectors, "PollSelector"):

        class PollEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
            def create_event_loop(self):
                return asyncio.SelectorEventLoop(selectors.PollSelector())

    class SelectEventLoopTests(BaseSockTestsMixin, test_utils.TestCase):
        def create_event_loop(self):
            return asyncio.SelectorEventLoop(selectors.SelectSelector())
